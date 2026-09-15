import os
import uuid
import logging
from typing import List, Dict, Optional, Tuple
from pypdf import PdfReader
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

import config
import database

logger = logging.getLogger(__name__)

# Set environment variables for minimal CPU RAM footprint
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# Initialize ChromaDB persistent client
chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

_embedding_model = None

def get_embedding_model():
    """Lazy loads SentenceTransformer embedding model to minimize RAM consumption."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading local embedding model: {config.EMBEDDING_MODEL_NAME}...")
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _embedding_model

# --- 1. FILE & IMAGE TEXT EXTRACTION ---

def process_txt(txt_path: str, user_id: int, file_name: str) -> Tuple[bool, str, int]:
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            full_text = f.read()

        if not full_text.strip():
            return False, "⚠️ TXT ফাইলটি খালি।", 0

        return _index_text_chunks(full_text, user_id, file_name)
    except Exception as e:
        return False, f"❌ TXT ফাইল প্রসেস করতে সমস্যা: {str(e)}", 0

def process_image(image_path: str, user_id: int, file_name: str) -> Tuple[bool, str, int]:
    """Uses Gemini API to perform OCR on photos of books/notes."""
    try:
        active_keys = database.get_active_keys("gemini")
        if not active_keys:
            gemini_env = os.getenv("GEMINI_API_KEY")
            if gemini_env:
                active_keys.append({"id": -1, "key_value": gemini_env})

        if not active_keys:
            return False, "⚠️ ছবি থেকে টেক্সট পড়ার জন্য সক্রিয় Gemini API Key প্রয়োজন। দয়া করে এডমিন প্যানেলে Key যুক্ত করুন।", 0

        from google import genai
        from google.genai import types
        from PIL import Image

        img = Image.open(image_path)
        client = genai.Client(api_key=active_keys[0]["key_value"])

        prompt = "এই ছবিতে যা লেখা আছে (বই বা নোটের বাংলা ও ইংরেজি টেক্সট), তা হুবহু নিখুঁতভাবে টাইপ করে বের করে দাও। কোনো অতিরিক্ত ব্যাখ্যা দিও না।"
        
        response = client.models.generate_content(
            model=config.DEFAULT_GEMINI_MODEL,
            contents=[img, prompt]
        )
        extracted_text = response.text

        if not extracted_text.strip():
            return False, "⚠️ ছবি থেকে কোনো স্পষ্ট টেক্সট পড়া যায়নি।", 0

        return _index_text_chunks(extracted_text, user_id, file_name)

    except Exception as e:
        return False, f"❌ ছবি থেকে টেক্সট এক্সট্র্যাক্ট করতে সমস্যা: {str(e)}", 0

def _index_text_chunks(full_text: str, user_id: int, file_name: str) -> Tuple[bool, str, int]:
    chunks = chunk_text(full_text, chunk_size=800, overlap=150)
    if not chunks:
        return False, "⚠️ টেক্সট চ্যাংক তৈরি করতে ব্যর্থ হয়েছে।", 0

    doc_id = str(uuid.uuid4())[:8]
    collection_name = f"user_{user_id}"

    try:
        chroma_client.delete_collection(name=collection_name)
    except Exception:
        pass

    collection = chroma_client.create_collection(name=collection_name)

    embeddings = get_embedding_model().encode(chunks).tolist()
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"chunk_index": i, "source": file_name} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    database.set_user_document(user_id, doc_id, file_name, len(chunks))
    msg = f"✅ `{file_name}` থেকে মোট `{len(chunks)}` টি টেক্সট ব্লকে সফলভাবে পড়া হয়েছে!"
    return True, msg, len(chunks)


def process_pdf(pdf_path: str, user_id: int, file_name: str) -> Tuple[bool, str, int]:
    """
    Extracts text from PDF, splits into chunks, computes local embeddings,
    and stores in ChromaDB collection for the user.
    """
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, config.MAX_PDF_PAGES)
        
        full_text = ""
        for i in range(pages_to_read):
            text = reader.pages[i].extract_text()
            if text:
                full_text += f"\n--- Page {i+1} ---\n" + text

        if not full_text.strip():
            return False, "⚠️ আপলোডকৃত PDF-টিতে কোনো পঠনযোগ্য টেক্সট পাওয়া যায়নি (হতে পারে এটি স্ক্যান করা ছবি)।", 0

        # Chunk text (800 chars with 150 overlap)
        chunks = chunk_text(full_text, chunk_size=800, overlap=150)
        if not chunks:
            return False, "⚠️ PDF থেকে টেক্সট চ্যাংক তৈরি করতে ব্যর্থ হয়েছে।", 0

        # Create/Get user vector collection
        doc_id = str(uuid.uuid4())[:8]
        collection_name = f"user_{user_id}"
        
        # Reset existing collection for user if any
        try:
            chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

        collection = chroma_client.create_collection(name=collection_name)

        # Generate embeddings locally
        embeddings = get_embedding_model().encode(chunks).tolist()
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"chunk_index": i, "source": file_name} for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        # Save document metadata to database
        database.set_user_document(user_id, doc_id, file_name, len(chunks))

        page_note = f"প্রথম {pages_to_read} টি পেজ" if total_pages > config.MAX_PDF_PAGES else f"সবকটি ({total_pages} টি) পেজ"
        msg = f"✅ PDF `{file_name}` সফলভাবে বিশ্লেষণ করা হয়েছে!\n({page_note} থেকে মোট `{len(chunks)}` টি টেক্সট ব্লকে বিভক্ত করা হয়েছে)।"

        return True, msg, len(chunks)

    except Exception as e:
        logger.error(f"Error processing PDF for user {user_id}: {e}", exc_info=True)
        return False, f"❌ Error processing PDF: {str(e)}", 0

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks

def cleanup_inactive_memories(max_inactive_hours: int = 2):
    """Deletes ChromaDB vector collections and document metadata for users inactive for > 2 hours."""
    try:
        inactive_uids = database.get_inactive_user_ids(max_inactive_hours)
        for uid in inactive_uids:
            col_name = f"user_{uid}"
            try:
                chroma_client.delete_collection(name=col_name)
            except Exception:
                pass
            database.delete_user_document(uid)
            logger.info(f"🧹 Auto-cleared inactive memory for user {uid} (no activity for {max_inactive_hours} hours).")
    except Exception as e:
        logger.error(f"Memory cleanup error: {e}")

# --- 2. VECTOR SEARCH ---

def search_relevant_chunks(user_id: int, query: str, top_k: int = 4) -> List[str]:
    # Run auto-cleanup for inactive users
    cleanup_inactive_memories(max_inactive_hours=2)

    collection_name = f"user_{user_id}"
    try:
        collection = chroma_client.get_collection(name=collection_name)
        query_embedding = get_embedding_model().encode([query]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count())
        )
        if results and results.get("documents"):
            return results["documents"][0]
    except Exception as e:
        logger.warning(f"ChromaDB search warning for user {user_id}: {e}")
    return []

# --- 3. MULTI-KEY ROTATION & LLM GENERATION ---

def generate_ai_response(prompt: str, context_chunks: Optional[List[str]] = None) -> str:
    """
    Sends prompt to LLM using Multi-Key Pool & Fallback mechanism.
    Supports Gemini and Groq with automatic retry on Rate Limit (429).
    """
    context_text = "\n\n".join(context_chunks) if context_chunks else ""
    
    full_prompt = f"""
আপনি একজন অভিজ্ঞ ও সুনির্দিষ্ট শিক্ষামূলক সহকারী। আপনাকে যে তথ্য (Context) দেওয়া হয়েছে, তা থেকে সরাসরি ও নির্ভুল উত্তর দিন।

--- CONTEXT DATA ---
{context_text}
--- END CONTEXT DATA ---

ইউজারের নির্দেশ বা প্রশ্ন:
{prompt}

কঠোর নির্দেশনা:
১. ইউজার যা জানতে চেয়েছে ঠিক সেই টু-দ্য-পয়েন্ট উত্তরটি দিন। অতিরিক্ত কোনো ভূমিকা, অনাবশ্যক ভুমিকা বা ফাও কথাবার্তা বলবেন না।
২. উত্তর সবসময় সহজ, পরিষ্কার বাংলা ভাষায় দিন (প্রয়োজনে ইংরেজি পরিভাষা রাখতে পারেন)।
৩. যদি উত্তরটি Context-এ না থাকে, তবে বিনীতভাবে বলুন যে প্রদত্ত ডকুমেন্টে এই প্রশ্নের তথ্য পাওয়া যায়নি।
৪. উত্তরের কোনো স্থানে "Powered by AI", "Generated by Gemini/Groq", বা যেকোনো AI ব্র্যান্ডিং/ওয়াটারমার্ক সম্পূর্ণ নিষিদ্ধ।
"""

    # Fetch active API keys from Database
    active_keys = database.get_active_keys()

    # If DB has no active keys, check environment variables as fallback
    if not active_keys:
        gemini_env = os.getenv("GEMINI_API_KEY")
        if gemini_env:
            active_keys.append({"id": -1, "provider": "gemini", "key_value": gemini_env, "usage_count": 0})
        groq_env = os.getenv("GROQ_API_KEY")
        if groq_env:
            active_keys.append({"id": -2, "provider": "groq", "key_value": groq_env, "usage_count": 0})

    if not active_keys:
        return "⚠️ কোনো সক্রিয় AI API Key পাওয়া যায়নি! দয়া করে এডমিন প্যানেলে (`/admin`) নতুন Gemini বা Groq API Key যুক্ত করুন।"

    # Try each key in sequence
    for key_info in active_keys:
        key_id = key_info["id"]
        provider = key_info["provider"].lower()
        key_value = key_info["key_value"]

        try:
            if provider == "gemini":
                response_text = _call_gemini_api(key_value, full_prompt)
            elif provider == "groq":
                response_text = _call_groq_api(key_value, full_prompt)
            else:
                continue

            if response_text:
                if key_id > 0:
                    database.update_key_usage(key_id)
                return response_text

        except Exception as e:
            error_str = str(e).lower()
            logger.warning(f"API Error with key {key_id} ({provider}): {e}")
            
            # Check for Rate Limit / Quota Exceeded (429)
            if "429" in error_str or "quota" in error_str or "rate limit" in error_str or "resource_exhausted" in error_str:
                if key_id > 0:
                    database.mark_key_status(key_id, "rate_limited")
                    logger.info(f"Key {key_id} marked as rate_limited. Switching to next key...")
                continue # Try next key seamlessly!
            
            # Invalid Key
            if "invalid" in error_str or "unauthorized" in error_str or "api_key" in error_str:
                if key_id > 0:
                    database.mark_key_status(key_id, "invalid")
                continue

    return "⚠️ দুঃখিত, এই মুহূর্তে সবকটি API Key লিমিট হয়ে আছে। দয়া করে ১ মিনিট পর আবার চেষ্টা করুন অথবা এডমিনকে ফ্রেস API Key এড করতে বলুন।"

def _call_gemini_api(api_key: str, prompt: str) -> str:
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=config.DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return response.text
    except Exception as e:
        raise e

def _call_groq_api(api_key: str, prompt: str) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=config.DEFAULT_GROQ_MODEL,
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        raise e

import json
import re

def generate_structured_quiz_json(user_id: int) -> Tuple[bool, List[Dict], str]:
    chunks = search_relevant_chunks(user_id, "important main points summary topics concepts", top_k=5)
    if not chunks:
        return False, [], "⚠️ কোনো একটি PDF, TXT বা ছবির নোট আপলোড করার পর MCQ কুইজ শুরু করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context থেকে ৫টি গুরুত্বপূর্ণ মাল্টিপল চয়েস প্রশ্ন (MCQ Quiz) তৈরি করুন।
আউটপুট অবশ্যই শুধুমাত্র একটি ভ্যালিড JSON Array হতে হবে। কোনো অতিরিক্ত টেক্সট বা markdown ফেন্সিং (```json) দিও না।

JSON ফরম্যাট উদাহরণ:
[
  {
    "id": 1,
    "question": "কোষের শক্তিঘর (Powerhouse) কাকে বলা হয়?",
    "options": {
      "ক": "রাইবোজোম",
      "খ": "মাইটোকন্ড্রিয়া",
      "গ": "গলজি বস্তু",
      "ঘ": "লাইসোজোম"
    },
    "correct": "খ",
    "explanation": "মাইটোকন্ড্রিয়ায় কোষের শ্বসন প্রক্রিয়ার মাধ্যমে শক্তি উৎপাদিত হয়।"
  }
]
"""
    raw_response = generate_ai_response(prompt, context_chunks=chunks)
    
    # Clean JSON output if LLM returns markdown fences
    cleaned = re.sub(r'```json\s*|\s*```', '', raw_response).strip()
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            return True, data, "✅ কুইজ প্রস্তুত!"
    except Exception as e:
        logger.error(f"Error parsing Quiz JSON: {e}, raw text: {raw_response}")

def generate_written_suggestions_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "important questions answers key points concepts summary", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি PDF, TXT বা ছবির নোট আপলোড করার পর সাজেশন জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context বিশ্লেষণ করে পরীক্ষার জন্য অত্যন্ত সম্ভাব্য ৫টি লিখিত প্রশ্ন (জ্ঞানমূলক ও অনুধাবনমূলক) এবং সেগুলোর মানসম্মত উত্তর তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📝 বিষয়/টপিক: গুরুত্বপূর্ণ লিখিত প্রশ্ন ও সাজেশন
=====================================================

📌 প্রশ্ন ১: [প্রশ্নটির বিবরণ]
উত্তর: [পয়েন্ট ভিত্তিক বিস্তারিত ও নিখুঁত উত্তর]

-----------------------------------------------------

📌 প্রশ্ন ২: [প্রশ্নটির বিবরণ]
উত্তর: [পয়েন্ট ভিত্তিক বিস্তারিত ও নিখুঁত উত্তর]

=====================================================
💡 পরীক্ষার জন্য বিশেষ পরামর্শ: [গুরুত্বপূর্ণ ১-২ লাইনের স্টাডি টিপস]
=====================================================
"""
    suggestion_text = generate_ai_response(prompt, context_chunks=chunks)

    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Written_Suggestions_{user_id}.txt")
    
    header = f"=====================================================\n📚 {doc_title} - পরীক্ষার লিখিত সাজেশন ও উত্তর\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + suggestion_text)

    return True, output_file_path, "✅ আপনার পড়া থেকে সংক্ষিপ্ত প্রশ্ন ও সাজেশনের ফাইল তৈরি সম্পন্ন হয়েছে!"

def generate_essay_suggestions_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "main theory broad concepts essay analysis explanation proof problem solving", top_k=7)
    if not chunks:
        return False, "", "⚠️ কোনো একটি PDF, TXT বা ছবির নোট আপলোড করার পর ব্রড/রচনামূলক প্রশ্ন জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context বিশ্লেষণ করে পরীক্ষার জন্য সবচেয়ে গুরুত্বপূর্ণ ৩টি রচনামূলক/সৃজনশীল (গ ও ঘ নম্বর বা বড় লিখিত) প্রশ্ন এবং সেগুলোর পয়েন্ট, চিত্র/সমীকরণ নির্দেশনা ও উদাহরণ সহ পূর্ণাঙ্গ সমাধান তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📚 বিষয়/টপিক: গুরুত্বপূর্ণ রচনামূলক প্রশ্ন ও সমাধান
=====================================================

📌 রচনামূলক প্রশ্ন ১: [প্রশ্নটির বড় বিবরণ]
গ) [প্রয়োগমূলক অংশ ও বিস্তৃত উত্তর]
ঘ) [উচ্চতর দক্ষতার অংশ ও বিশ্লেষণী উত্তর]

-----------------------------------------------------

📌 রচনামূলক প্রশ্ন ২: [প্রশ্নটির বিবরণ]
গ) [বিস্তারিত সমাধান]
ঘ) [বিস্তারিত মূল্যায়ণ/বিশ্লেষণ]

=====================================================
💡 রচনামূলক পরীক্ষার উত্তর লেখার মূল কৌশল ও টিপস
=====================================================
"""
    essay_text = generate_ai_response(prompt, context_chunks=chunks)

    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Essay_Suggestions_{user_id}.txt")
    
    header = f"=====================================================\n📚 {doc_title} - পরীক্ষার রচনামূলক প্রশ্ন ও পূর্ণাঙ্গ সমাধান\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + essay_text)

    return True, output_file_path, "✅ আপনার পড়া থেকে রচনামূলক প্রশ্নের সাজেশন ও সমাধান ফাইল তৈরি সম্পন্ন হয়েছে!"

def generate_summary_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "main topic core summary conclusion intro formulas points", top_k=7)
    if not chunks:
        return False, "", "⚠️ কোনো একটি PDF, TXT বা ছবির নোট আপলোড করার পর সারসংক্ষেপ জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context থেকে ১ পৃষ্ঠার একটি অত্যন্ত নিখুঁত ও চমৎকার অধ্যায়ভিত্তিক সারসংক্ষেপ তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
⚡ ১-ক্লিকে বই/অধ্যায়ের সারসংক্ষেপ (Fast Revision Summary)
=====================================================

📌 প্রধান বিষয়বস্তু: [১ লাইনে মূল থিম]

🔑 মূল তত্ত্ব ও সূত্রসমূহ:
- [পয়েন্ট ১]
- [পয়েন্ট ২]

📝 অধ্যায়ভিত্তিক সংক্ষিপ্ত সারসংক্ষেপ:
১. [বিষয় ১ এর বিস্তারিত সারসংক্ষেপ]
২. [বিষয় ২ এর বিস্তারিত সারসংক্ষেপ]

💡 পরীক্ষার আগের রাতের বিশেষ টেকঅ্যাওয়ে:
- [গুরুত্বপূর্ণ ১-২ লাইনের পরামর্শ]
"""
    summary_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Fast_Summary_{user_id}.txt")
    header = f"=====================================================\n⚡ {doc_title} - ১-ক্লিকে ফাস্ট সারসংক্ষেপ\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + summary_text)

    return True, output_file_path, summary_text

def generate_flashcards_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "definitions key terms formulas dates scientist names concepts", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর শব্দকোষ ও ফ্ল্যাশকার্ড তৈরি করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context থেকে ১০টি অত্যন্ত গুরুত্বপূর্ণ শব্দকোষ, সংজ্ঞার্থ, বিজ্ঞানীদের নাম, তারিখ বা সূত্রসমূহ ফ্ল্যাশকার্ড ফরম্যাটে তৈরি করুন।

ফরম্যাট উদাহরণ:
🎴 [টার্ম ১ / শব্দ ১] ➔ সংজ্ঞা/ব্যাখ্যা: [১ লাইনের সহজ বিবরণ]
🎴 [টার্ম ২ / শব্দ ২] ➔ সংজ্ঞা/ব্যাখ্যা: [১ লাইনের সহজ বিবরণ]
"""
    flashcard_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Flashcards_{user_id}.txt")
    header = f"=====================================================\n🎴 {doc_title} - গুরুত্বপূর্ণ শব্দকোষ ও ফ্ল্যাশকার্ড\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + flashcard_text)

    return True, output_file_path, flashcard_text

def generate_study_routine_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "main topics chapters outline structure concepts syllabus", top_k=7)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর ১৫ দিনের স্টাডি রুটিন জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context বা বিষয়বস্তু পড়ার জন্য একটি ১৫ দিনের পরীক্ষার সেরা রিভিশন ও স্টাডি রুটিন তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📅 ১৫ দিনের পরীক্ষার স্মার্ট রিভিশন রুটিন
=====================================================

📌 ১ম - ৩য় দিন: [১ম টপিক/অধ্যায় রিভিশন ও প্রধান পয়েন্ট]
📌 ৪র্থ - ৬ষ্ঠ দিন: [২য় টপিক/অধ্যায় রিভিশন ও প্রধান পয়েন্ট]
📌 ৭ম - ৯ম দিন: [৩য় টপিক/অধ্যায় রিভিশন ও সমীকরণ]
📌 ১০ম - ১২শ দিন: [কুইজ ও সংক্ষিপ্ত প্রশ্ন রিভিশন]
📌 ১৩শ - ১৫শ দিন: [মডেল টেস্ট ও চূড়ান্ত রিভিশন]

=====================================================
💡 রুটিন মেনে পড়ার বিশেষ টিপস: [২-৩ লাইনের স্টাডি পরামর্শ]
=====================================================
"""
    routine_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Study_Routine_{user_id}.txt")
    header = f"=====================================================\n📅 {doc_title} - ১৫ দিনের পরীক্ষার স্মার্ট রিভিশন রুটিন\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + routine_text)

    return True, output_file_path, routine_text

def generate_formula_quiz_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "formulas equations definitions units laws rules principles", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর সূত্র ও সংজ্ঞা টেস্ট ফাইল জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context থেকে ১০টি অত্যন্ত গুরুত্বপূর্ণ সূত্র, গাণিতিক সমীকরণ, একক (Units) এবং সংজ্ঞা টেস্ট শিট আকারে তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
💡 সূত্র, সমীকরণ ও সংজ্ঞার্থ টেস্ট শিট
=====================================================

📌 ১. [সংজ্ঞা বা সূত্রের প্রশ্ন]
   👉 উত্তর/সমীকরণ: [নিখুঁত সমাধান ও একক]

-----------------------------------------------------

📌 ২. [সংজ্ঞা বা সূত্রের প্রশ্ন]
   👉 উত্তর/সমীকরণ: [নিখুঁত সমাধান ও একক]
"""
    formula_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Formula_Quiz_{user_id}.txt")
    header = f"=====================================================\n💡 {doc_title} - সূত্র, সমীকরণ ও সংজ্ঞার্থ টেস্ট শিট\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + formula_text)

    return True, output_file_path, formula_text

def generate_vocab_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "english words vocabulary terms definitions meanings grammar", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর English Vocabulary জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context থেকে ১৫টি গুরুত্বপূর্ণ ইংরেজি শব্দ (English Vocabulary) নির্বাচন করে সেগুলোর বাংলা অর্থ, Synonyms (সমার্থ শব্দ), Antonyms (বিপরীত শব্দ) এবং ১টি করে সহজ ইংরেজি বাক্য তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
🔤 English Vocabulary, Synonyms & Antonyms Sheet
=====================================================

📌 Word 1: [English Word]
   • Meaning (বাংলা অর্থ): [বাংলা অর্থ]
   • Synonym: [সমার্থ শব্দ]
   • Antonym: [বিপরীত শব্দ]
   • Example Sentence: [ইংরেজিতে সহজ বাক্য]

-----------------------------------------------------

📌 Word 2: [English Word]
   • Meaning (বাংলা অর্থ): [বাংলা অর্থ]
   • Synonym: [সমার্থ শব্দ]
   • Antonym: [বিপরীত শব্দ]
   • Example Sentence: [ইংরেজিতে সহজ বাক্য]
"""
    vocab_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"English_Vocab_{user_id}.txt")
    header = f"=====================================================\n🔤 {doc_title} - English Vocabulary & Synonyms Sheet\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + vocab_text)

    return True, output_file_path, vocab_text

def generate_english_writing_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "main topic theme english writing composition paragraph essay letter", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর English Writing Suggestions জেনারেট করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context বা বিষয়বস্তু অনুযায়ী পরীক্ষার জন্য অত্যন্ত সম্ভাবনাময় ২টি English Paragraph / Short Essay এবং ১টি Formal Letter/Email সাজেশন ও মডেল উত্তর বাংলায় অনুবাদসহ তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📝 English Writing Suggestions & Model Answers
=====================================================

📌 Paragraph Suggestion 1: [Paragraph Title]
[ইংরেজিতে মানসম্মত প্যারাগ্রাফের মডেল উত্তর]
(বাংলা অনুবাদ: [প্যারাগ্রাফের সহজ বাংলা অনুবাদ])

-----------------------------------------------------

📌 Formal Letter / Email: [Subject]
[ইংরেজিতে ফরমাল লেটার/ইমেইলের মডেল উত্তর]
"""
    writing_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"English_Writing_{user_id}.txt")
    header = f"=====================================================\n📝 {doc_title} - English Writing Suggestions & Model Answers\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + writing_text)

    return True, output_file_path, writing_text

def generate_grammar_rules_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "grammar rules prepositions right form of verbs voice narration sentence correction modifiers", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর Grammar Rules জেনারেট করতে পারবেন।"

    prompt = """
SSC, HSC ও BCS পরীক্ষার জন্য উপযোগী ১০টি অত্যন্ত গুরুত্বপূর্ণ English Grammar Rules & Corrections (Right form of verbs, Prepositions, Modifiers, Voice, Narration & Correction) সহজ বাংলায় সমাধান ও উদাহরণসহ তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
✍️ SSC, HSC & BCS English Grammar Rules & Corrections
=====================================================

📌 Rule 1: [Grammar Rule Title]
   • রুলস ব্যাখ্যা: [সহজ নিয়ম ও কারণ]
   • Wrong: [ভুল বাক্য]
   • Correct: [সঠিক বাক্য]

-----------------------------------------------------

📌 Rule 2: [Grammar Rule Title]
   • রুলস ব্যাখ্যা: [সহজ নিয়ম ও কারণ]
   • Wrong: [ভুল বাক্য]
   • Correct: [সঠিক বাক্য]
"""
    grammar_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Grammar_Rules_{user_id}.txt")
    header = f"=====================================================\n✍️ {doc_title} - English Grammar Rules & Corrections Sheet\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + grammar_text)

    return True, output_file_path, grammar_text

def generate_bcs_lit_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "english literature authors plays poems famous quotes periods shakespeare milton wordsworth", top_k=6)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর BCS English Literature Notes জেনারেট করতে পারবেন।"

    prompt = """
BCS ও বিশ্ববিদ্যালয় ভর্তি পরীক্ষার জন্য ১০টি অত্যন্ত গুরুত্বপূর্ণ English Literature Quick Notes (বিখ্যাত লেখক, নাটক, কাব্যগ্রন্থ, সাহিত্যিক যুগ ও বিখ্যাত Quotations) সহজ বাংলা নোট আকারে তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📖 BCS English Literature & Authors Quick Notes
=====================================================

📌 Author / Literary Figure: [Author Name]
   • Famous Works (বিখ্যাত গ্রন্থ/নাটক): [নামসমূহ]
   • Famous Quotation (বিখ্যাত উক্তি): [উক্তি ও অর্থ]
   • Literary Period: [যুগ/সময়কাল]

-----------------------------------------------------

📌 Author / Literary Figure: [Author Name]
   • Famous Works: [নামসমূহ]
   • Famous Quotation: [উক্তি ও অর্থ]
   • Literary Period: [যুগ/সময়কাল]
"""
    lit_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"BCS_Lit_{user_id}.txt")
    header = f"=====================================================\n📖 {doc_title} - BCS English Literature & Authors Quick Notes\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + lit_text)

    return True, output_file_path, lit_text

def generate_writing_formats_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "english writing format rules application letter email paragraph essay rules layout", top_k=6)
    
    prompt = """
SSC ও HSC পরীক্ষার জন্য মানসম্মত English Writing Rules & Formats (Formal Letter, Application, Email, Informal Letter, Paragraph & Composition) তৈরির সঠিক নিয়ম ও টেমপ্লেট সহজ ভাষায় তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📜 SSC & HSC English Writing Rules, Formats & Guidelines
=====================================================

📌 1. Formal Letter / Application Format Rules:
   - Date: [Correct Date Format]
   - Receiver: To the Principal / Chairman, [Institution]
   - Subject: Application for [Topic]
   - Salutation: Sir/Madam,
   - Main Body Rules: [1st paragraph intro, 2nd paragraph details, 3rd paragraph prayer]
   - Subscription: Yours obediently, [Name]

-----------------------------------------------------

📌 2. E-mail / Informal Letter Format Rules:
   - From: [Email ID]
   - To: [Email ID]
   - Sent: [Day, Date, Time]
   - Subject: [Short Subject]
   - Salutation: Dear [Friend's Name],
   - Body & Closing Rules

-----------------------------------------------------

📌 3. Paragraph & Essay Writing Rules:
   - Topic Sentence, Supporting Ideas & Conclusion layout
   - Important Linking Words (However, Furthermore, Therefore, Consequently)
"""
    formats_text = generate_ai_response(prompt, context_chunks=chunks if chunks else None)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    return True, output_file_path, formats_text

def generate_topic_importance_file(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "important topics chapter mark distribution weightage board questions probability", top_k=7)
    if not chunks:
        return False, "", "⚠️ কোনো একটি পড়া আপলোড করার পর টপিক গুরুত্ব ও নম্বর মিটার তৈরি করতে পারবেন।"

    prompt = """
উপরে দেওয়া Context বিশ্লেষণ করে পরীক্ষার জন্য টপিকভিত্তিক গুরুত্ব (Probability Meter) এবং মার্কস ওয়েটেজ চার্ট তৈরি করুন।

ফরম্যাট উদাহরণ:
=====================================================
📊 পরীক্ষার টপিক গুরুত্ব ও নম্বর মিটার (Probability Meter)
=====================================================

🔥 ৯৯% নিশ্চিত আসার মতো টপিক (Top Priority):
   • [টপিক ১] ➔ সম্ভাব্য প্রশ্ন টাইপ: [সৃজনশীল গ/ঘ বা MCQ]
   • [টপিক ২] ➔ সম্ভাব্য প্রশ্ন টাইপ: [জ্ঞানমূলক/অনুধাবন]

⚡ ৮০% গুরুত্বপূর্ণ টপিক (Medium Priority):
   • [টপিক ৩] ➔ সম্ভাব্য প্রশ্ন টাইপ: [সংক্ষিপ্ত প্রশ্ন]
   • [টপিক ৪] ➔ সম্ভাব্য প্রশ্ন টাইপ: [MCQ]

📌 কম গুরুত্বপূর্ণ টপিক (Low Priority / Quick Review):
   • [টপিক ৫]
=====================================================
"""
    importance_text = generate_ai_response(prompt, context_chunks=chunks)
    doc_info = database.get_user_document(user_id)
    doc_title = doc_info["file_name"] if doc_info else "Study_Notes"

    output_file_path = os.path.join(config.TEMP_PDF_DIR, f"Topic_Importance_{user_id}.txt")
    header = f"=====================================================\n📊 {doc_title} - পরীক্ষার টপিক গুরুত্ব ও নম্বর মিটার\n=====================================================\n\n"
    
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(header + importance_text)

    return True, output_file_path, importance_text

def generate_quiz_certificate_text(user_name: str, doc_name: str, score: int, total: int) -> str:
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    cert_text = f"""
🏆 **DIGITAL QUIZ ACHIEVEMENT CERTIFICATE** 🏆
=====================================================
🎓 **কুইজ মাস্টার সার্টিফিকেট অফ অ্যাচিভমেন্ট**

👤 **শিক্ষার্থীর নাম:** `{user_name}`
🌟 **উপাধি:** `QUIZ MASTER & TOP PERFORMER` 🥇
📄 **পঠিত বিষয়/ফাইল:** `{doc_name}`
📊 **অর্জিত ফলাফল:** `{score} / {total}` (১০০% পারফেক্ট স্কোর!)
📅 **তারিখ:** `{today}`

=====================================================
🎉 **অভিনন্দন! আপনি পড়াটিতে অসামান্য পারফরম্যান্স প্রদর্শন করেছেন!**
(আপনার এই কৃতিত্বের স্ক্রিনশট নিয়ে বন্ধুদের সাথে শেয়ার করুন!)
=====================================================
"""
    return cert_text

def generate_audio_summary(user_id: int) -> Tuple[bool, str, str]:
    chunks = search_relevant_chunks(user_id, "main topic summary core explanation intro", top_k=4)
    if not chunks:
        return False, "", "⚠️ অডিও লেকচার শুনতে আগে একটি বই বা নোট আপলোড করুন।"

    prompt = "উপরে দেওয়া Context থেকে ৩-৪ বাক্যের একটি অত্যন্ত সহজ ও প্রাঞ্জল বাংলা সামারি তৈরি করুন যা পড়ে শুনানো যাবে।"
    short_summary = generate_ai_response(prompt, context_chunks=chunks)

    # Convert text to audio MP3 using gTTS
    audio_path = os.path.join(config.TEMP_PDF_DIR, f"Audio_Summary_{user_id}.mp3")
    try:
        from gtts import gTTS
        tts = gTTS(text=short_summary, lang='bn', slow=False)
        tts.save(audio_path)
        return True, audio_path, short_summary
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        return False, "", f"❌ অডিও ভয়েস নোট তৈরি করতে সমস্যা: {str(e)}"




