import os
import logging
from telegram import Update
from telegram.ext import ContextTypes

import config
import database
import ai_engine
import keyboards

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    database.register_user(user.id, user.username, user.first_name)
    
    welcome_text = f"""
👋 **আসসালামু আলাইকুম, {user.first_name}!**

আমি আপনার **Smart Study Assistant BD** (@SmartStudyBDBot)। 📚🤖

**আমার মাধ্যমে যা যা করতে পারবেন:**
১. যেকোনো **PDF বা TXT ফাইল** আপলোড করতে পারবেন।
২. যেকোনো ফাইল থেকে **বাংলা বা ইংরেজিতে প্রশ্ন** করলে সাথে সাথে উত্তর পাবেন।
３. আপলোড করা পড়া থেকে ইন্টারেক্টিভ **🎯 MCQ কুইজ পরীক্ষা** দিতে পারবেন।

👇 নিচের কিবোর্ড মেনু থেকে অপশন সিলেক্ট করুন অথবা সরাসরি আপনার ফাইল পাঠান:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboards.get_user_main_reply_keyboard(user.id),
        parse_mode="Markdown"
    )

async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "btn_upload_pdf":
        await query.message.reply_text(
            "📥 **আপনার ফাইল বা ছবি পাঠান:**\n\nআপনি `.pdf`, `.txt` ফাইল অথবা বই/নোটের স্পষ্ট ছবি (Photo) পাঠাতে পারেন।"
        )
    
    elif data == "btn_main_menu":
        await query.message.edit_text(
            "🏠 **প্রধান মেনু:**\n\nনিচের যেকোনো ক্যাটাগরি সিলেক্ট করুন:",
            reply_markup=keyboards.get_user_main_menu_keyboard(user_id),
            parse_mode="Markdown"
        )

    elif data == "menu_written_category":
        await query.message.edit_text(
            "📚 **লিখিত সাজেশন ও প্রশ্ন সেকশন:**\n\nনিচের অপশন থেকে সংক্ষিপ্ত বা রচনামূলক সাজেশন বেছে নিন:",
            reply_markup=keyboards.get_written_category_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_summary_category":
        await query.message.edit_text(
            "⚡ **সারসংক্ষেপ, রুটিন ও ফ্ল্যাশকার্ড সেকশন:**\n\nনিচের অপশন থেকে আপনার পছন্দের সার্ভিস বেছে নিন:",
            reply_markup=keyboards.get_summary_category_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_english_category":
        await query.message.edit_text(
            "🌐 **ইংলিশ গ্রামার, ভোকাবুলারি ও রাইটিং সেকশন:**\n\nনিচের অপশন থেকে আপনার প্রয়োজনীয় সার্ভিসটি সিলেক্ট করুন:",
            reply_markup=keyboards.get_english_category_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "btn_gen_vocab":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া থেকে ১৫টি গুরুত্বপূর্ণ English Vocabulary, Synonyms & Antonyms তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_vocab_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **Vocabulary ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"🔤_{doc_info['file_name']}_English_Vocab.txt",
                    caption=f"🔤 **{doc_info['file_name']}**-এর জন্য গুরুত্বপূর্ণ English Vocabulary, Synonyms & Antonyms Sheet।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_english_writing":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া থেকে গুরুত্বপূর্ণ English Paragraph & Formal Letter সাজেশন তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_english_writing_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **Writing Suggestions ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📝_{doc_info['file_name']}_English_Writing.txt",
                    caption=f"📝 **{doc_info['file_name']}**-এর জন্য English Paragraph & Formal Letter Suggestions।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_grammar_rules":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **SSC, HSC ও BCS পরীক্ষার জন্য গুরুত্বপূর্ণ Grammar Rules & Corrections তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_grammar_rules_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **Grammar Rules ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"✍️_{doc_info['file_name']}_Grammar_Rules.txt",
                    caption=f"✍️ **{doc_info['file_name']}**-এর জন্য গুরুত্বপূর্ণ English Grammar Rules & Corrections Sheet।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_bcs_lit":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **BCS & Admission English Literature Quick Notes তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_bcs_lit_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **English Literature Notes ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📖_{doc_info['file_name']}_BCS_Literature.txt",
                    caption=f"📖 **{doc_info['file_name']}**-এর জন্য BCS English Literature & Authors Quick Notes।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_writing_formats":
        status_msg = await query.message.reply_text("⏳ **SSC & HSC English Writing Rules & Formats ফাইল তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_writing_formats_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **Writing Rules & Formats ফাইল পাঠানো হচ্ছে...**")
            doc_info = database.get_user_document(user_id)
            doc_name = doc_info['file_name'] if doc_info else "English"
            
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📜_{doc_name}_Writing_Formats_and_Rules.txt",
                    caption=f"📜 **SSC & HSC English Writing Rules & Formats Sheet**\n\n💡 **Pro Tip:** যেকোনো নির্দিষ্ট টপিকের ওপর Paragraph, Letter, Email বা Essay পেতে চ্যাটে সরাসরি লিখুন:\n• `Write a formal letter to the Principal for a testimonial`\n• `Write a paragraph on Tree Plantation for HSC`"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_english_translate_help":
        trans_help_text = """
✍️ **Bangla to English Translation & Grammar Helper:**

আপনার চ্যাটে যেকোনো বাংলা বাক্য লিখলে এআই সেটিকে **সঠিক ইংরেজি অনুবাদ** করে দেবে এবং এর গ্রামাটিক্যাল রুলস বুঝিয়ে দেবে!

উদাহরণ:
- `আমি ৫ বছর ধরে ঢাকায় বাস করছি এটি ইংরেজিতে কী হবে?`
- `He has came home - এই বাক্যে কী ভুল আছে?`
"""
        await query.message.reply_text(trans_help_text, parse_mode="Markdown")

    elif data == "btn_gen_written_pdf":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text(
                "⚠️ **কোনো পড়ার ফাইল বা ছবি পাওয়া যায়নি!**\n\nলিখিত সাজেশন পেতে আগে একটি PDF, TXT বা ছবির নোট আপলোড করুন।"
            )
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া বিশ্লেষণ করে ৫টি সেরা লিখিত প্রশ্ন ও উত্তর সংবলিত ফাইল তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_written_suggestions_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **সাজেশন ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📝_{doc_info['file_name']}_লিখিত_সাজেশন.txt",
                    caption=f"📚 **{doc_info['file_name']}**-এর জন্য গুরুত্বপূর্ণ লিখিত প্রশ্ন ও উত্তর সংবলিত সাজেশন ফাইল।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_essay_pdf":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text(
                "⚠️ **কোনো পড়ার ফাইল বা ছবি পাওয়া যায়নি!**\n\nরচনামূলক প্রশ্ন পেতে আগে একটি PDF, TXT বা ছবির নোট আপলোড করুন।"
            )
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া বিশ্লেষণ করে সবচেয়ে গুরুত্বপূর্ণ রচনামূলক/সৃজনশীল প্রশ্ন ও সমাধান তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_essay_suggestions_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **রচনামূলক প্রশ্ন ও সমাধান ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📚_{doc_info['file_name']}_রচনামূলক_প্রশ্ন_ও_সমাধান.txt",
                    caption=f"📚 **{doc_info['file_name']}**-এর জন্য গুরুত্বপূর্ণ রচনামূলক/সৃজনশীল প্রশ্ন ও পূর্ণাঙ্গ উত্তর সংবলিত ফাইল।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_summary":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল বা ছবি পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া থেকে ১ পৃষ্ঠার সারসংক্ষেপ তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_summary_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **সারসংক্ষেপ ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"⚡_{doc_info['file_name']}_সারসংক্ষেপ.txt",
                    caption=f"⚡ **{doc_info['file_name']}**-এর ১ পৃষ্ঠার ফাস্ট সারসংক্ষেপ (Fast Revision Summary)।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_topic_importance":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া বিশ্লেষণ করে টপিক গুরুত্ব ও নম্বর মিটার (Probability Chart) তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_topic_importance_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **টপিক গুরুত্ব মিটার ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📊_{doc_info['file_name']}_টপিক_গুরুত্ব_মিটার.txt",
                    caption=f"📊 **{doc_info['file_name']}**-এর জন্য পরীক্ষার টপিক গুরুত্ব ও নম্বর মিটার (Probability Chart)।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_gen_flashcards":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল বা ছবি পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **গুরুত্বপূর্ণ শব্দকোষ ও ফ্ল্যাশকার্ড তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_flashcards_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **ফ্ল্যাশকার্ড ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"🎴_{doc_info['file_name']}_শব্দকোষ.txt",
                    caption=f"🎴 **{doc_info['file_name']}**-এর গুরুত্বপূর্ণ শব্দকোষ ও ফ্ল্যাশকার্ড তালিকা।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_math_solver":
        math_instructions = """
📐 **গাণিতিক সমস্যা ও সমীকরণ সমাধান মোড:**

আপনার বই বা নোটের যেকোনো অংক, পদার্থবিজ্ঞানের গাণিতিক সমস্যা বা রসায়নের সমীকরণ চ্যাটে লিখে পাঠান।

উদাহরণ:
- `v = u + at সমীকরণ ব্যবহার করে ত্বরণ নির্ণয় করো যদি v=20, u=5, t=3 হয়`
- `২x + ৫ = ১৫ হলে x এর মান কত?`

এআই সাথে সাথে **ধাপ ১, ধাপ ২, ধাপ ৩** করে লাইন-বাই-লাইন নিখুঁত সমাধান বুঝিয়ে দেবে!
"""
        await query.message.reply_text(math_instructions, parse_mode="Markdown")

    elif data == "btn_gen_routine":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **আপনার পড়া বিশ্লেষণ করে ১৫ দিনের স্মার্ট রিভিশন রুটিন তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_study_routine_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **রুটিন ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"📅_{doc_info['file_name']}_১৫দিনের_স্টাডি_রুটিন.txt",
                    caption=f"📅 **{doc_info['file_name']}**-এর জন্য ১৫ দিনের স্মার্ট রিভিশন রুটিন।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_formula_quiz":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text("⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**")
            return

        status_msg = await query.message.reply_text("⏳ **গুরুত্বপূর্ণ সূত্র, সমীকরণ ও সংজ্ঞা টেস্ট তৈরি করা হচ্ছে...**")
        success, file_path, msg_text = ai_engine.generate_formula_quiz_file(user_id)

        if success and os.path.exists(file_path):
            await status_msg.edit_text("📤 **টেস্ট ফাইল পাঠানো হচ্ছে...**")
            with open(file_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=doc_file,
                    filename=f"💡_{doc_info['file_name']}_সূত্র_ও_সংজ্ঞা_টেস্ট.txt",
                    caption=f"💡 **{doc_info['file_name']}**-এর গুরুত্বপূর্ণ সূত্র, সমীকরণ ও সংজ্ঞার্থ টেস্ট শিট।"
                )
            await status_msg.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            await status_msg.edit_text(msg_text)

    elif data == "btn_start_mcq":
        doc_info = database.get_user_document(user_id)
        if not doc_info:
            await query.message.reply_text(
                "⚠️ **কোনো পড়ার ফাইল বা ছবি পাওয়া যায়নি!**\n\nMCQ কুইজ শুরু করার আগে দয়া করে একটি PDF, TXT বা ছবির নোট আপলোড করুন।"
            )
            return

        msg = await query.message.reply_text("⏳ **আপনার পড়া থেকে ৫টি ইন্টারেক্টিভ MCQ তৈরি করা হচ্ছে...**")
        success, quiz_list, text_msg = ai_engine.generate_structured_quiz_json(user_id)
        
        if not success or not quiz_list:
            await msg.edit_text(text_msg)
            return

        # Store quiz in user state
        context.user_data["quiz_questions"] = quiz_list
        context.user_data["quiz_index"] = 0
        context.user_data["quiz_score"] = 0

        await msg.delete()
        await send_quiz_question(query.message.chat_id, context, 0)

    elif data.startswith("mcq_ans_"):
        # Handle user selecting option (e.g., mcq_ans_0_খ)
        parts = data.split("_")
        q_idx = int(parts[2])
        selected_opt = parts[3]
        
        # Increment total MCQ count in database
        database.increment_user_mcq(user_id)

        quiz_list = context.user_data.get("quiz_questions", [])
        if q_idx >= len(quiz_list):
            return

        q_data = quiz_list[q_idx]
        correct_opt = q_data["correct"]
        correct_val = q_data["options"].get(correct_opt, "")

        if selected_opt == correct_opt:
            context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + 1
            encourage_text = f"🎉 **চমৎকার! আপনার উত্তর সঠিক হয়েছে!** 👏\n\n**প্রশ্ন:** {q_data['question']}\n\n✅ **সঠিক উত্তর:** ({correct_opt}) {correct_val}"
            
            await query.message.edit_text(
                encourage_text,
                reply_markup=keyboards.get_next_question_keyboard(q_idx),
                parse_mode="Markdown"
            )
        else:
            wrong_text = f"অফসোস! উত্তরটি সঠিক হয়নি, তবে হতাশ হবেন না! 💪\n\n**আমি কি সঠিক উত্তর বলে দেবো?**"
            await query.message.edit_text(
                wrong_text,
                reply_markup=keyboards.get_wrong_answer_keyboard(q_idx),
                parse_mode="Markdown"
            )

    elif data.startswith("show_exp_"):
        q_idx = int(data.split("_")[2])
        quiz_list = context.user_data.get("quiz_questions", [])
        if q_idx < len(quiz_list):
            q_data = quiz_list[q_idx]
            correct_opt = q_data["correct"]
            correct_val = q_data["options"].get(correct_opt, "")
            exp = q_data.get("explanation", "")

            exp_text = f"❓ **প্রশ্ন:** {q_data['question']}\n\n✅ **সঠিক উত্তর:** ({correct_opt}) {correct_val}\n💡 **ব্যাখ্যা:** {exp}\n\n👇 পরবর্তী প্রশ্ন পেতে নিচের বাটনে ক্লিক করুন:"
            await query.message.edit_text(
                exp_text,
                reply_markup=keyboards.get_next_question_keyboard(q_idx),
                parse_mode="Markdown"
            )

    elif data.startswith("next_q_"):
        q_idx = int(data.split("_")[2])
        next_idx = q_idx + 1
        quiz_list = context.user_data.get("quiz_questions", [])

        if next_idx < len(quiz_list):
            context.user_data["quiz_index"] = next_idx
            await send_quiz_question(query.message.chat_id, context, next_idx)
        else:
            score = context.user_data.get("quiz_score", 0)
            total = len(quiz_list)
            
            mcq_stats = database.get_user_mcq_stats(user_id)
            if mcq_stats["mcqs_played"] >= 10 and mcq_stats["reviewed"] == 0:
                review_prompt = f"""
🏆 **কুইজ পরীক্ষা সম্পন্ন হয়েছে!** (স্কোর: `{score} / {total}`)

⭐ **অভিনন্দন! আপনি ১০টি+ MCQ সমাধান করেছেন!**
আমাদের বোটটি আপনার কেমন লেগেছে? দয়া করে ৫-স্টার রিভিউ দিন এবং নতুন কী ফিচার চান লিখে জানান:
"""
                await query.message.edit_text(
                    review_prompt,
                    reply_markup=keyboards.get_star_rating_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                doc_info = database.get_user_document(user_id)
                doc_name = doc_info["file_name"] if doc_info else "Study_Notes"
                user_name = query.from_user.first_name

                if score == total:
                    cert_text = ai_engine.generate_quiz_certificate_text(user_name, doc_name, score, total)
                    await query.message.edit_text(
                        cert_text,
                        reply_markup=keyboards.get_user_main_menu_keyboard(user_id),
                        parse_mode="Markdown"
                    )
                else:
                    finish_text = f"""
🏆 **কুইজ পরীক্ষা সম্পন্ন হয়েছে!**

📊 **আপনার স্কোর:** `{score} / {total}`

{ "🎉 চমৎকার পারফরম্যান্স! আপনি খুব সুন্দর উত্তর দিয়েছেন!" if score >= 3 else "💪 ভালো চেষ্টা ছিল! আরেকটু রিভিশন দিয়ে আবার চেষ্টা করুন।" }
"""
                    await query.message.edit_text(
                        finish_text,
                        reply_markup=keyboards.get_user_main_menu_keyboard(user_id),
                        parse_mode="Markdown"
                    )

    elif data.startswith("review_star_"):
        rating = int(data.split("_")[2])
        context.user_data["pending_rating"] = rating
        context.user_data["awaiting_feedback_text"] = True

        stars_display = "⭐" * rating
        await query.message.edit_text(
            f"ধন্যবাদ! আপনি **{stars_display}** রেটিং দিয়েছেন! 🌟\n\nবোটে আর নতুন কী ফিচার চান বা কোনো পরামর্শ থাকলে তা চ্যাটে লিখে সেন্ড করুন (অথবা এড়াতে `/skip` টাইপ করুন):",
            parse_mode="Markdown"
        )

    elif data == "btn_user_stats":
        doc_info = database.get_user_document(user_id)
        if doc_info:
            stats_text = f"""
📊 **আপনার অ্যাকাউন্ট স্ট্যাটস:**

📄 **বর্তমান সক্রিয় ফাইল:** `{doc_info['file_name']}`
🧩 **মোট চ্যাংক স্লাইস:** `{doc_info['chunk_count']}` টি
📅 **আপলোডের তারিখ:** `{doc_info['uploaded_at'][:10]}`
"""
        else:
            stats_text = "📊 **আপনার কোনো সক্রিয় পড়া আপলোড করা নেই।**"
        await query.message.reply_text(stats_text, parse_mode="Markdown")

    elif data == "btn_ask_help":
        await query.message.reply_text(
            "💡 **প্রশ্ন করার নিয়ম:**\n\nফাইল বা ছবি পাঠানোর পর চ্যাটে প্রশ্ন লিখে পাঠালে এআই সাথে সাথে উত্তর জানিয়ে দেবে।"
        )

    elif data == "btn_help":
        help_text = """
ℹ️ **সহায়িকা ও কিভাবে কাজ করে:**
১. PDF, TXT বা ছবির নোট পাঠালে বোট সেটি প্রসেস করে রাখে।
২. 🎯 MCQ কুইজ অপশনে ক্লিক করলে সাথে সাথে ইন্টারেক্টিভ কুইজ শুরু হয়।
"""
        await query.message.reply_text(help_text, parse_mode="Markdown")

async def send_quiz_question(chat_id: int, context: ContextTypes.DEFAULT_TYPE, q_index: int):
    quiz_list = context.user_data.get("quiz_questions", [])
    if q_index >= len(quiz_list):
        return

    q_data = quiz_list[q_index]
    opts = q_data["options"]

    question_formatted_text = f"""
❓ **প্রশ্ন {q_index + 1}:** {q_data['question']}

(ক) {opts.get('ক', '')} \t (খ) {opts.get('খ', '')}
(গ) {opts.get('গ', '')} \t (ঘ) {opts.get('ঘ', '')}
"""
    await context.bot.send_message(
        chat_id=chat_id,
        text=question_formatted_text,
        reply_markup=keyboards.get_mcq_options_keyboard(q_index, opts),
        parse_mode="Markdown"
    )

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    document = update.message.document
    file_name = document.file_name.lower()

    if not (file_name.endswith('.pdf') or file_name.endswith('.txt')):
        await update.message.reply_text("⚠️ শুধুমাত্র `.pdf` এবং `.txt` ফাইল সাপোর্ট করে।")
        return

    max_size_bytes = config.MAX_PDF_SIZE_MB * 1024 * 1024
    if document.file_size and document.file_size > max_size_bytes:
        await update.message.reply_text(
            f"⚠️ **ফাইল সাইজ লিমিট অতিক্রম করেছে!** (সর্বোচ্চ **{config.MAX_PDF_SIZE_MB} MB**)"
        )
        return

    status_msg = await update.message.reply_text("⏳ **ফাইল ডাউনলোড ও প্রসেস করা হচ্ছে...**")

    try:
        file_path = os.path.join(config.TEMP_PDF_DIR, f"{user.id}_{document.file_name}")
        telegram_file = await context.bot.get_file(document.file_id)
        await telegram_file.download_to_drive(file_path)

        if file_name.endswith('.pdf'):
            success, message, _ = ai_engine.process_pdf(file_path, user.id, document.file_name)
        else:
            success, message, _ = ai_engine.process_txt(file_path, user.id, document.file_name)

        if os.path.exists(file_path):
            os.remove(file_path)

        if success:
            await status_msg.edit_text(
                f"{message}\n\n🎉 **আপনার পড়া প্রস্তুত!** নিচের অপশন থেকে এখনই পরীক্ষা দিন বা লিখিত সাজেশন ফাইল ডাউনলোড করুন:",
                reply_markup=keyboards.get_post_upload_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text(message)

    except Exception as e:
        logger.error(f"Error in document upload: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ ফাইল প্রসেস করতে সমস্যা: {str(e)}")

async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ **ছবি আপলোড ফিচারটি সাময়িকভাবে বন্ধ আছে।**\n\nদ্রুত প্রসেসিং ও সার্ভার স্পিড ঠিক রাখতে বোটটিতে শুধুমাত্র `.pdf` এবং `.txt` ফাইল সাপোর্ট করে। দয়া করে আপনার বই বা নোটের PDF/TXT ফাইল পাঠান।"
    )

async def handle_text_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_query = update.message.text.strip()

    database.register_user(user.id, user.username, user.first_name)

    # Handle Feedback Text input
    if context.user_data.get("awaiting_feedback_text"):
        context.user_data["awaiting_feedback_text"] = False
        rating = context.user_data.pop("pending_rating", 5)
        
        feedback_text = "কোনো লিখিত পরামর্শ নেই" if user_query == "/skip" else user_query
        database.save_user_review(user.id, user.username or user.first_name, rating, feedback_text)
        database.mark_user_reviewed(user.id)

        stars_display = "⭐" * rating
        await update.message.reply_text(
            f"🎉 **ধন্যবাদ!** আপনার **{stars_display}** রিভিউ এবং মূল্যবান ফিডব্যাক এডমিন প্যানেলে পাঠানো হয়েছে!",
            reply_markup=keyboards.get_user_main_menu_keyboard(user.id)
        )
        return

    if user_query.startswith('/'):
        return

    # --- HANDLE PERSISTENT REPLY KEYBOARD BUTTON TAPS ---
    if user_query in ["🟢 📥 PDF/TXT আপলোড", "📥 PDF/TXT আপলোড"]:
        await update.message.reply_text(
            "📥 **আপনার ফাইল পাঠান:**\n\nআপনি `.pdf` বা `.txt` ফাইল পাঠাতে পারেন। (সর্বোচ্চ ২০ MB / ১৫০ পৃষ্ঠা)"
        )
        return

    elif user_query in ["🔵 🎯 MCQ কুইজ", "🎯 MCQ কুইজ"]:
        doc_info = database.get_user_document(user.id)
        if not doc_info:
            await update.message.reply_text(
                "⚠️ **কোনো পড়ার ফাইল পাওয়া যায়নি!**\n\nMCQ কুইজ শুরু করার আগে দয়া করে একটি PDF বা TXT ফাইল আপলোড করুন।"
            )
            return

        msg = await update.message.reply_text("⏳ **আপনার পড়া থেকে ৫টি ইন্টারেক্টিভ MCQ তৈরি করা হচ্ছে...**")
        success, quiz_list, text_msg = ai_engine.generate_structured_quiz_json(user.id)
        
        if not success or not quiz_list:
            await msg.edit_text(text_msg)
            return

        context.user_data["quiz_questions"] = quiz_list
        context.user_data["quiz_index"] = 0
        context.user_data["quiz_score"] = 0

        await msg.delete()
        await send_quiz_question(update.effective_chat.id, context, 0)
        return

    elif user_query == "📚 লিখিত সাজেশন":
        await update.message.reply_text(
            "📚 **লিখিত সাজেশন ও প্রশ্ন সেকশন:**\n\nনিচের ইনলাইন অপশন থেকে আপনার প্রয়োজনীয় সাজেশন বেছে নিন:",
            reply_markup=keyboards.get_written_category_keyboard(),
            parse_mode="Markdown"
        )
        return

    elif user_query == "⚡ সারসংক্ষেপ & রুটিন":
        await update.message.reply_text(
            "⚡ **সারসংক্ষেপ, রুটিন ও ফ্ল্যাশকার্ড সেকশন:**\n\nনিচের ইনলাইন অপশন থেকে সার্ভিস বেছে নিন:",
            reply_markup=keyboards.get_summary_category_keyboard(),
            parse_mode="Markdown"
        )
        return

    elif user_query == "📐 গাণিতিক সমস্যা":
        math_instructions = """
📐 **গাণিতিক সমস্যা ও সমীকরণ সমাধান মোড:**

আপনার বই বা নোটের যেকোনো অংক, পদার্থবিজ্ঞানের গাণিতিক সমস্যা বা রসায়নের সমীকরণ চ্যাটে লিখে পাঠান।

উদাহরণ:
- `v = u + at সমীকরণ ব্যবহার করে ত্বরণ নির্ণয় করো যদি v=20, u=5, t=3 হয়`
- `২x + ৫ = ১৫ হলে x এর মান কত?`

এআই সাথে সাথে **ধাপ ১, ধাপ ২, ধাপ ৩** করে লাইন-বাই-লাইন নিখুঁত সমাধান বুঝিয়ে দেবে!
"""
        await update.message.reply_text(math_instructions, parse_mode="Markdown")
        return

    elif user_query == "🌐 ইংলিশ গ্রামার & সাজেশন":
        await update.message.reply_text(
            "🌐 **ইংলিশ গ্রামার, ভোকাবুলারি ও রাইটিং সেকশন:**\n\nনিচের ইনলাইন অপশন থেকে সার্ভিসটি সিলেক্ট করুন:",
            reply_markup=keyboards.get_english_category_keyboard(),
            parse_mode="Markdown"
        )
        return

    elif user_query == "📊 আমার স্ট্যাটস":
        doc_info = database.get_user_document(user.id)
        if doc_info:
            stats_text = f"""
📊 **আপনার অ্যাকাউন্ট স্ট্যাটস:**

📄 **বর্তমান সক্রিয় ফাইল:** `{doc_info['file_name']}`
🧩 **মোট চ্যাংক স্লাইস:** `{doc_info['chunk_count']}` টি
📅 **আপলোডের তারিখ:** `{doc_info['uploaded_at'][:10]}`
"""
        else:
            stats_text = "📊 **আপনার কোনো সক্রিয় পড়া আপলোড করা নেই।**"
        await update.message.reply_text(stats_text, parse_mode="Markdown")
        return

    elif user_query == "ℹ️ সাহায্য ও নিয়মাবলী":
        help_text = """
ℹ️ **সহায়িকা ও কিভাবে কাজ করে:**
১. PDF বা TXT ফাইল পাঠালে বোট সেটি প্রসেস করে রাখে।
২. 🎯 MCQ কুইজ বাটনে ক্লিক করলে সাথে সাথে ইন্টারেক্টিভ কুইজ শুরু হয়।
৩. চ্যাটে যেকোনো পড়া সংক্রান্ত প্রশ্ন করলে এআই ফাইল থেকে নির্ভুল উত্তর দেয়।
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
        return

    elif user_query in ["⚙️ 🛠️ এডমিন প্যানেল", "🛠️ এডমিন প্যানেল"]:
        if user.id in config.ADMIN_IDS:
            await update.message.reply_text(
                "🛠️ **এডমিন কন্ট্রোল প্যানেল:**",
                reply_markup=keyboards.get_admin_panel_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ আপনার এই সেকশনে এক্সেস নেই।")
        return

    # --- REGULAR RAG TEXT QUESTION HANDLER ---
    doc_info = database.get_user_document(user.id)
    if not doc_info:
        await update.message.reply_text(
            "⚠️ **আপনার কোনো সক্রিয় বই/নোট পাওয়া যায়নি!**\n\nপ্রশ্ন করার আগে দয়া করে একটি PDF বা TXT ফাইল আপলোড করুন।",
            reply_markup=keyboards.get_user_main_reply_keyboard(user.id)
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("🔎 **পড়া অনুসন্ধান করে উত্তর তৈরি করা হচ্ছে...**")

    relevant_chunks = ai_engine.search_relevant_chunks(user.id, user_query, top_k=4)
    ai_response = ai_engine.generate_ai_response(user_query, context_chunks=relevant_chunks)

    await status_msg.edit_text(ai_response)
