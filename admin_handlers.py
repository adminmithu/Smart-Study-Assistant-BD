import logging
from telegram import Update
from telegram.ext import ContextTypes

import config
import database
import keyboards

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ **আপনার এই নির্দেশ ব্যবহারের অনুমতি নেই।** (Admin Only)")
        return

    admin_text = """
🛠️ **এডমিন কন্ট্রোল প্যানেল (Admin Panel)**

এখান থেকে আপনি বোটের সকল **API Keys ম্যানেজ, ডায়নামিক কী এড, কি স্ট্যাটাস রিসেট এবং সার্বিক স্ট্যাটস** দেখতে পারবেন।
"""
    await update.message.reply_text(
        admin_text,
        reply_markup=keyboards.get_admin_panel_keyboard(),
        parse_mode="Markdown"
    )

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not is_admin(user_id):
        await query.message.reply_text("⛔ অননুমোদিত এক্সেস।")
        return

    if data == "admin_main_menu":
        await query.message.edit_text(
            "🛠️ **এডমিন কন্ট্রোল প্যানেল (Admin Panel)**",
            reply_markup=keyboards.get_admin_panel_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "admin_list_keys":
        keys = database.get_all_api_keys()
        if not keys:
            text = "🔑 **ডাটাবেসে কোনো API Key নেই!**\nনিচের বাটন থেকে নতুন Key যোগ করুন।"
        else:
            text = "🔑 **API Key পুলের তালিকা:**\n\n"
            for k in keys:
                masked_key = k['key_value'][:6] + "..." + k['key_value'][-4:] if len(k['key_value']) > 10 else "***"
                status_icon = "🟢" if k['status'] == 'active' else ("🟡" if k['status'] == 'rate_limited' else "🔴")
                text += f"{status_icon} **ID {k['id']}** | [{k['provider'].upper()}] `{masked_key}`\n"
                text += f"   └ Status: `{k['status']}` | Usage: `{k['usage_count']}` calls\n"
                text += f"   └ ডিলিট করতে লিখুন: `/delkey_{k['id']}`\n\n"

        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "admin_add_key_menu":
        await query.message.edit_text(
            "➕ **কোন সার্ভিসের API Key যোগ করতে চান সিলেক্ট করুন:**",
            reply_markup=keyboards.get_key_provider_keyboard()
        )

    elif data in ["add_provider_gemini", "add_provider_groq"]:
        provider = "gemini" if data == "add_provider_gemini" else "groq"
        context.user_data["awaiting_api_key_provider"] = provider
        
        provider_name = "Google Gemini" if provider == "gemini" else "Groq Llama 3"
        await query.message.reply_text(
            f"🔑 **{provider_name} API Key পাঠান:**\n\nচ্যাটে আপনার API Key-টি পেস্ট করে সেন্ড করুন।",
            parse_mode="Markdown"
        )

    elif data == "admin_reset_keys":
        database.reset_rate_limited_keys()
        await query.message.reply_text("✅ **সকল Rate-Limited API Keys সক্রিয় (Active) করা হয়েছে!**")

    elif data == "admin_system_stats":
        user_count = database.get_user_count()
        keys = database.get_all_api_keys()
        active_keys_count = len([k for k in keys if k['status'] == 'active'])
        rate_limited_count = len([k for k in keys if k['status'] == 'rate_limited'])

        stats_text = f"""
📊 **সার্বিক বোট সিস্টেম স্ট্যাটস:**

👥 **মোট ইউজার:** `{user_count}` জন
🔑 **মোট API Keys:** `{len(keys)}` টি
🟢 **সক্রিয় (Active) Keys:** `{active_keys_count}` টি
🟡 **Rate Limited Keys:** `{rate_limited_count}` টি
"""
        await query.message.reply_text(stats_text, parse_mode="Markdown")

    elif data == "admin_view_reviews":
        reviews = database.get_all_reviews()
        if not reviews:
            await query.message.reply_text("💬 **এখনো কোনো ইউজার রিভিউ বা ফিডব্যাক পাঠায়নি।**")
        else:
            text = f"💬 **ইউজারদের লাইভ রিভিউ ও নতুন ফিডব্যাক (মোট: {len(reviews)} টি):**\n\n"
            for r in reviews[:15]: # Show latest 15 reviews
                stars = "⭐" * r['rating']
                user_str = f"@{r['username']}" if r['username'] else f"User {r['user_id']}"
                date_str = r['created_at'][:16].replace("T", " ")
                text += f"{stars} ({r['rating']}/5) | **{user_str}**\n"
                text += f"📝 `{r['feedback_text']}`\n"
                text += f"📅 {date_str}\n"
                text += "-----------------------------------\n"
            await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "admin_broadcast_prompt":
        context.user_data["awaiting_broadcast_msg"] = True
        await query.message.reply_text("📢 **ব্রডকাস্ট মেসেজ পাঠাতে:**\n\nমেসেজটি লিখে চ্যাটে সেন্ড করুন। সকল ইউজারের কাছে চলে যাবে।")

async def handle_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handles admin text input when expecting an API Key or Broadcast message"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return False

    text = update.message.text.strip()

    # Handle delete key command e.g. /delkey_2
    if text.startswith("/delkey_"):
        try:
            key_id = int(text.split("_")[1])
            success = database.remove_api_key(key_id)
            if success:
                await update.message.reply_text(f"✅ Key ID `{key_id}` সফলভাবে ডিলিট করা হয়েছে।", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⚠️ Key ID `{key_id}` পাওয়া যায়নি।")
            return True
        except Exception as e:
            await update.message.reply_text("⚠️ সঠিক ফরম্যাটে লিকুন: `/delkey_ID`")
            return True

    # Handle API Key Addition
    if "awaiting_api_key_provider" in context.user_data:
        provider = context.user_data.pop("awaiting_api_key_provider")
        success, msg = database.add_api_key(provider, text)
        await update.message.reply_text(msg)
        return True

    # Handle Broadcast Message
    if context.user_data.get("awaiting_broadcast_msg"):
        context.user_data.pop("awaiting_broadcast_msg")
        user_ids = database.get_all_user_ids()
        sent_count = 0
        
        status_msg = await update.message.reply_text("📢 ব্রডকাস্ট পাঠানো শুরু হয়েছে...")
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent_count += 1
            except Exception:
                pass
        
        await status_msg.edit_text(f"✅ **ব্রডকাস্ট সম্পন্ন!**\nমোট `{sent_count}` জন ইউজারের কাছে মেসেজ পৌঁছেছে।", parse_mode="Markdown")
        return True

    return False
