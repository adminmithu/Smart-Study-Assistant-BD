import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

import config
import database
import user_handlers
import admin_handlers

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def health_check_handler(request):
    """HTTP Health Check endpoint for Render.com and cron-job.org keep-alive pings"""
    return web.Response(
        text="🟢 OK - Smart Study Assistant BD Bot (@SmartStudyBDBot) is alive and running 24/7!",
        status=200
    )

async def start_health_server(application):
    """Starts async HTTP server on $PORT for Render health checks and pre-warms AI embedding model"""
    app = web.Application()
    app.router.add_get('/', health_check_handler)
    app.router.add_get('/health', health_check_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Health Check Web Server started on port {port} (Ready for Render & CronJob pings)")

    # Pre-warm AI embedding model in background so first user upload takes only 1-2 seconds!
    try:
        logger.info("⚡ Pre-warming AI embedding model for instant 1-second file processing...")
        ai_engine.get_embedding_model()
        logger.info("✅ AI model pre-warmed successfully!")
    except Exception as e:
        logger.warning(f"Model pre-warm warning: {e}")

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes incoming text messages to admin inputs or user QA handlers"""
    handled_by_admin = await admin_handlers.handle_admin_text_input(update, context)
    if not handled_by_admin:
        await user_handlers.handle_text_question(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

def main():
    logger.info("Initializing Smart Study Assistant BD Bot...")

    # Ensure database is initialized
    database.init_db()

    # Build bot application with post_init hook for health server
    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(start_health_server).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", user_handlers.start_command))
    app.add_handler(CommandHandler("admin", admin_handlers.admin_command))

    # Callback Query Handlers (User & Admin Menu Buttons)
    app.add_handler(CallbackQueryHandler(admin_handlers.admin_callback_handler, pattern="^admin_|^add_provider_"))
    app.add_handler(CallbackQueryHandler(user_handlers.user_callback_handler))

    # Document Upload Handler (PDFs & TXT)
    app.add_handler(MessageHandler(filters.Document.ALL, user_handlers.handle_document_upload))

    # Photo Upload Handler (Notes / Book Images OCR)
    app.add_handler(MessageHandler(filters.PHOTO, user_handlers.handle_photo_upload))

    # Text Message Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # Register Error Handler
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot is starting polling... Press Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
