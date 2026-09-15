# 📚 Smart Study Assistant BD (@SmartStudyBDBot)

একটি সম্পূর্ণ প্রোডাকশন-রেডি টেলিগ্রাম আরএজি (RAG) বোট। এটি ইউজারদের আপলোড করা PDF রিড করে প্রশ্নের উত্তর দেয়, অটোমেটিক কুইজ তৈরি করে এবং এআই লিমিট প্রবলেম দূর করার জন্য Multi-Key Pool & Fallback সিস্টেম ব্যবহার করে।

---

## ✨ প্রধান ফিচারসমূহ (Features)

1. **📄 PDF Reading & Local Vector Search (RAG):**
   - PDF ডাউনলোড করে চ্যাংক স্লাইস তৈরি করে।
   - **Local Embeddings (`sentence-transformers`):** পিসির লোকাল সিপিইউ-তেই Vector Search প্রসেস হয়, ফলে **০টি API খরচ** হয়।
   - **ChromaDB Vector Database:** প্রতিটি ইউজারের জন্য আলাদা ও দ্রুত ভেক্টর ডাটাবেস।

2. **🤖 Interactive Telegram UI Menu:**
   - 📄 PDF Upload Button
   - 📝 10-Question MCQ Quiz Generator
   - 📊 User Account Stats & PDF info
   - ℹ️ Help & FAQ Menu

3. **🛠️ Admin Panel & Dynamic API Management:**
   - `/admin` কমান্ড দিয়ে সম্পূর্ণ বোট কন্ট্রোল।
   - **Dynamic API Key Pool:** বোট রানিং থাকা অবস্থাতেই যেকোনো সময় চ্যাট থেকে নতুন **Google Gemini API Key** অথবা **Groq (Llama 3) API Key** যোগ/ডিলিট করা যায়।
   - **Auto Rate-Limit Fallback:** কোনো Key 429 Limit হিট করলে বোট সাথে সাথে ব্যাকগ্রাউন্ডে ২য় Key অথবা অন্য AI প্রোভাইডারে সুইচ করে (ইউজার টের পাবে না)।
   - **Broadcasting & System Stats:** সকল ইউজারকে একসাথে মেসেজ পাঠানো ও সার্বিক বোটের ব্যবহারের পরিসংখ্যান দেখা।

---

## 🛠️ প্রজেক্ট ফোল্ডার স্ট্রাকচার (Project Structure)

```
├── bot.py              # মূল Telegram Bot Entry point (Async polling)
├── config.py           # কনফিগারেশন, মডেল ও পাথ সেটিংস
├── database.py         # SQLite Database (Keys, Users, Docs storage)
├── ai_engine.py        # PDF Parser, Local Embeddings, ChromaDB, Key Rotator & Gemini/Groq LLM
├── user_handlers.py    # ইউজার কমান্ড, PDF আপলোড, QA ও কুইজ হ্যান্ডলার
├── admin_handlers.py   # এডমিন প্যানেল, API Key যোগ/ডিলিট, ব্রডকাস্ট ও স্ট্যাটস
├── keyboards.py        # টেলিগ্রাম ইনলাইন কিবোর্ড ইউআই
├── requirements.txt    # পাইথন ডিপেন্ডেন্সি প্যাকেজ
└── .env.example        # এনভায়রনমেন্ট ভ্যারিয়েবল টেমপ্লেট
```

---

## 🚀 সেটআপ ও রান করার নিয়ম (Installation & Run)

### ১. ডিপেন্ডেন্সি ইনস্টল করুন:
```bash
pip install -r requirements.txt
```

### ২. কনফিগারেশন সেটিংস:
`config.py` ফাইলটি ওপেন করুন অথবা একটি `.env` ফাইল বানিয়ে আপনার তথ্যসমূহ দিন:
- **`TELEGRAM_BOT_TOKEN`**: Telegram `@BotFather` থেকে পাওয়া টোকেন।
- **`ADMIN_IDS`**: আপনার টেলিগ্রামের আইডি (যাতে আপনি এডমিন প্যানেল এক্সেস করতে পারেন। আপনার আইডি জানতে টেলিগ্রামে `@userinfobot`-এ মেসেজ দিন)।

### ৩. বোট রান করুন:
```bash
python bot.py
```

---

## 👑 এডমিন প্যানেল ব্যবহার করার নিয়ম (Admin Guide)

১. টেলিগ্রামে আপনার বোটে গিয়ে `/admin` কমান্ড দিন।
২. **`➕ নতুন API Key যোগ করুন`** বাটনে ক্লিক করুন।
৩. প্রোভাইডার সিলেক্ট করুন (`Google Gemini` বা `Groq`) এবং চ্যাটে API Key পাঠিয়ে দিন।
৪. ডাটাবেসে Key যুক্ত হয়ে যাবে এবং বোট অটোমেটিক লোড-ব্যালেন্স করা শুরু করবে!
