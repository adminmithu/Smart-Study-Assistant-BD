from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

import config

def get_user_main_reply_keyboard(user_id: int = None):
    """Persistent Reply Keyboard for main bottom Telegram keyboard menu"""
    keyboard = [
        [
            KeyboardButton("🟢 📥 PDF/TXT আপলোড", api_kwargs={"style": "success"}),
            KeyboardButton("🔵 🎯 MCQ কুইজ", api_kwargs={"style": "primary"})
        ],
        [
            KeyboardButton("📚 লিখিত সাজেশন", api_kwargs={"style": "primary"}),
            KeyboardButton("⚡ সারসংক্ষেপ & রুটিন", api_kwargs={"style": "primary"})
        ],
        [
            KeyboardButton("📐 গাণিতিক সমস্যা", api_kwargs={"style": "primary"}),
            KeyboardButton("🌐 ইংলিশ গ্রামার & সাজেশন", api_kwargs={"style": "primary"})
        ],
        [
            KeyboardButton("📊 আমার স্ট্যাটস", api_kwargs={"style": "primary"}),
            KeyboardButton("ℹ️ সাহায্য ও নিয়মাবলী", api_kwargs={"style": "primary"})
        ]
    ]

    # Show Admin Panel button ONLY if user is an Admin
    if user_id and user_id in config.ADMIN_IDS:
        keyboard.append([
            KeyboardButton("⚙️ 🛠️ এডমিন প্যানেল", api_kwargs={"style": "danger"})
        ])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_main_menu_keyboard(user_id: int = None):
    """Inline Keyboard for clean main user menu with categories"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 📥 PDF / TXT আপলোড করুন", callback_data="btn_upload_pdf", api_kwargs={"style": "success"})
        ],
        [
            InlineKeyboardButton("🔵 🎯 MCQ কুইজ পরীক্ষা", callback_data="btn_start_mcq", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("📚 লিখিত সাজেশন ও প্রশ্ন", callback_data="menu_written_category", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("⚡ সারসংক্ষেপ ও রুটিন", callback_data="menu_summary_category", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("📐 গাণিতিক সমস্যা ও সূত্র", callback_data="menu_math_category", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🌐 ইংলিশ গ্রামার ও সাজেশন", callback_data="menu_english_category", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("📊 আমার স্ট্যাটস", callback_data="btn_user_stats", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("❓ প্রশ্ন করার নিয়ম", callback_data="btn_ask_help", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("ℹ️ সাহায্য ও নিয়মাবলী", callback_data="btn_help", api_kwargs={"style": "primary"})
        ]
    ]

    # Show Admin Panel button ONLY if user is an Admin
    if user_id and user_id in config.ADMIN_IDS:
        keyboard.append([
            InlineKeyboardButton("⚙️ 🛠️ এডমিন কন্ট্রোল প্যানেল", callback_data="admin_main_menu", api_kwargs={"style": "danger"})
        ])

    return InlineKeyboardMarkup(keyboard)

def get_post_upload_keyboard():
    """Inline Keyboard popped up immediately after file upload success"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 এখনই MCQ কুইজ শুরু করুন", callback_data="btn_start_mcq", api_kwargs={"style": "success"})
        ],
        [
            InlineKeyboardButton("📚 লিখিত সাজেশন ও প্রশ্ন", callback_data="menu_written_category", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⚡ সারসংক্ষেপ ও রুটিন", callback_data="menu_summary_category", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📐 গাণিতিক সমস্যা ও সূত্র", callback_data="menu_math_category", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🌐 ইংলিশ গ্রামার ও সাজেশন", callback_data="menu_english_category", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("❓ প্রশ্ন জিজ্ঞেস করুন", callback_data="btn_ask_help", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("📂 মূল মেনু", callback_data="btn_main_menu", api_kwargs={"style": "primary"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- SUB-MENUS ---

def get_written_category_keyboard():
    """Sub-menu for Written Questions & Suggestions"""
    keyboard = [
        [
            InlineKeyboardButton("📝 সংক্ষিপ্ত প্রশ্ন ও উত্তর (ক-খ)", callback_data="btn_gen_written_pdf", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📚 রচনামূলক প্রশ্ন ও সমাধান (গ-ঘ)", callback_data="btn_gen_essay_pdf", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🔙 মূল মেনুতে ফিরে যান", callback_data="btn_main_menu", api_kwargs={"style": "primary"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_summary_category_keyboard():
    """Sub-menu for Summary, Routine, Flashcards & Topic Importance"""
    keyboard = [
        [
            InlineKeyboardButton("⚡ ১-ক্লিকে সারসংক্ষেপ (Summary)", callback_data="btn_gen_summary", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📊 টপিক গুরুত্ব ও নম্বর মিটার", callback_data="btn_topic_importance", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📅 ১৫ দিনের স্মার্ট স্টাডি রুটিন", callback_data="btn_gen_routine", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🎴 শব্দকোষ (Flashcards)", callback_data="btn_gen_flashcards", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🔙 মূল মেনুতে ফিরে যান", callback_data="btn_main_menu", api_kwargs={"style": "primary"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_english_category_keyboard():
    """Sub-menu for English Learning, SSC/HSC/BCS Vocabulary, Grammar & Writing"""
    keyboard = [
        [
            InlineKeyboardButton("🔤 Vocabulary, Synonyms & Antonyms", callback_data="btn_gen_vocab", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("✍️ Grammar Rules & Corrections Sheet", callback_data="btn_gen_grammar_rules", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📝 Paragraph, Writing & Translation Suggestions", callback_data="btn_gen_english_writing", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📜 Writing Rules & Formats (Letter, Email, Essay)", callback_data="btn_gen_writing_formats", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("📖 BCS English Literature & Authors Notes", callback_data="btn_gen_bcs_lit", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🔙 মূল মেনুতে ফিরে যান", callback_data="btn_main_menu", api_kwargs={"style": "primary"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_mcq_options_keyboard(q_index: int, options: dict, selected_option: str = None, correct_option: str = None):
    """Generates 2x2 grid buttons for (ক), (খ), (গ), (ঘ)"""
    buttons = []
    keys = list(options.keys()) # ['ক', 'খ', 'গ', 'ঘ']
    
    row1 = []
    row2 = []
    
    for i, opt_key in enumerate(keys):
        opt_val = options[opt_key]
        label = f"({opt_key}) {opt_val}"
        b_style = "primary"
        
        # If user answered, show checkmark or cross mark
        if selected_option:
            if opt_key == correct_option:
                label = f"✅ ({opt_key}) {opt_val}"
                b_style = "success"
            elif opt_key == selected_option:
                label = f"❌ ({opt_key}) {opt_val}"
                b_style = "danger"
                
        btn = InlineKeyboardButton(label, callback_data=f"mcq_ans_{q_index}_{opt_key}", api_kwargs={"style": b_style})
        if i < 2:
            row1.append(btn)
        else:
            row2.append(btn)
            
    buttons.append(row1)
    if row2:
        buttons.append(row2)
        
    return InlineKeyboardMarkup(buttons)

def get_wrong_answer_keyboard(q_index: int):
    """Keyboard shown when user selects a wrong answer"""
    keyboard = [
        [
            InlineKeyboardButton("💡 হ্যাঁ, উত্তর বলে দাও", callback_data=f"show_exp_{q_index}", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⏭️ পরবর্তী প্রশ্ন", callback_data=f"next_q_{q_index}", api_kwargs={"style": "success"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_next_question_keyboard(q_index: int):
    """Keyboard shown after correct answer or explanation revealed"""
    keyboard = [
        [
            InlineKeyboardButton("⏭️ পরবর্তী প্রশ্ন ➡️", callback_data=f"next_q_{q_index}", api_kwargs={"style": "success"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_star_rating_keyboard():
    """Inline Keyboard for 1-5 Star Ratings"""
    keyboard = [
        [
            InlineKeyboardButton("⭐ 1", callback_data="review_star_1", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⭐⭐ 2", callback_data="review_star_2", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⭐⭐⭐ 3", callback_data="review_star_3", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⭐⭐⭐⭐ 4", callback_data="review_star_4", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("⭐⭐⭐⭐⭐ 5", callback_data="review_star_5", api_kwargs={"style": "success"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard():
    """Inline Keyboard for Admin Management Panel"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 🔑 API Keys তালিকা", callback_data="admin_list_keys", api_kwargs={"style": "success"}),
            InlineKeyboardButton("🔵 ➕ নতুন API Key যোগ করুন", callback_data="admin_add_key_menu", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🟡 🔄 Rate Limit কি রিসেট", callback_data="admin_reset_keys", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🩵 📊 সার্বিক স্ট্যাটস", callback_data="admin_system_stats", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🟣 💬 ইউজার রিভিউ ও ফিডব্যাক ইনবক্স", callback_data="admin_view_reviews", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🔴 📢 সকল ইউজারকে ব্রডকাস্ট করুন", callback_data="admin_broadcast_prompt", api_kwargs={"style": "danger"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_key_provider_keyboard():
    """Inline Keyboard to select provider when adding a key"""
    keyboard = [
        [
            InlineKeyboardButton("🔵 🟦 Google Gemini Key", callback_data="add_provider_gemini", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🟠 🟧 Groq Key (Llama 3)", callback_data="add_provider_groq", api_kwargs={"style": "primary"})
        ],
        [
            InlineKeyboardButton("🔙 ⚙️ এডমিন মূল মেনু", callback_data="admin_main_menu", api_kwargs={"style": "danger"})
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
