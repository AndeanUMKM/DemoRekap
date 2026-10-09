import logging
import re
import hashlib
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from config import config
from core.models import TenantProfile
from core.github_db import storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation States
NAMA_TOKO, USERNAME, PASSWORD, CONTOH_FORMAT = range(4)

def create_tenant_slug(nama: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", nama.lower().strip())
    return slug.strip("_") or "toko_umkm"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for onboarding conversation."""
    user = update.effective_user
    
    # Check if already registered
    existing = storage.get_tenant_by_telegram_id(user.id)
    if existing:
        await update.message.reply_text(
            f"Halo Kak {user.first_name}! Toko Anda **{existing.nama_toko}** sudah terdaftar.\n\n"
            f"👤 **Username Web**: `{existing.username}`\n"
            f"📁 **ID Tenant**: `{existing.tenant_id}`\n\n"
            f"Silakan buka **Bot Rekap Pesanan** kami untuk mulai mencatat pesanan!",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Halo Kak {user.first_name}! Selamat datang di **Sistem Rekap PO UMKM Otomatis** 🎉\n\n"
        "Saya akan memandu Anda membuat database rekap pesanan untuk toko Anda.\n\n"
        "👉 Silakan ketik **Nama Toko / Usaha Anda** (contoh: *Dapur Mama Berkah*):",
        parse_mode="Markdown"
    )
    return NAMA_TOKO

async def nama_toko_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nama = update.message.text.strip()
    context.user_data["nama_toko"] = nama
    context.user_data["tenant_id"] = create_tenant_slug(nama)

    await update.message.reply_text(
        f"Nama Toko: **{nama}** ✅\n\n"
        "👉 Sekarang buat **Username** untuk login ke Web Dashboard Anda (huruf/angka tanpa spasi, contoh: *dapurberkah*):",
        parse_mode="Markdown"
    )
    return USERNAME

async def username_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip().lower()
    
    # Check if username already taken
    existing = storage.get_tenant_by_username(username)
    if existing and existing.telegram_user_id != update.effective_user.id:
        await update.message.reply_text(
            "⚠️ Username tersebut sudah digunakan toko lain. Silakan pilih username lain:"
        )
        return USERNAME

    context.user_data["username"] = username
    await update.message.reply_text(
        f"Username: `{username}` ✅\n\n"
        "👉 Sekarang ketik **Password** untuk login ke Web Dashboard Anda:",
        parse_mode="Markdown"
    )
    return PASSWORD

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    context.user_data["password_hash"] = hash_password(password)

    await update.message.reply_text(
        "Password tersimpan dengan aman 🔒\n\n"
        "👉 Terakhir, kirimkan **1 contoh teks chat pesanan PO** yang biasa dikirim pembeli ke WA Anda "
        "(Ini digunakan agar AI mengenali format pesanan toko Anda dengan akurat):"
    )
    return CONTOH_FORMAT

async def contoh_format_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contoh_format = update.message.text.strip()
    user = update.effective_user

    tenant = TenantProfile(
        tenant_id=context.user_data["tenant_id"],
        nama_toko=context.user_data["nama_toko"],
        telegram_user_id=user.id,
        username=context.user_data["username"],
        password_hash=context.user_data["password_hash"],
        contoh_format_po=contoh_format
    )

    # Save to storage (GitHub & Local)
    storage.register_tenant(tenant)

    await update.message.reply_text(
        f"🎉 **Selamat! Toko Anda Berhasil Didaftarkan** 🎉\n\n"
        f"🏪 **Toko**: {tenant.nama_toko}\n"
        f"👤 **Username Web**: `{tenant.username}`\n"
        f"🗂️ **Database**: `tenants/{tenant.tenant_id}/rekap_pesanan.xlsx`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Cara Menggunakan Rekap PO:**\n"
        f"1. Buka **Bot Rekap Pesanan**.\n"
        f"2. Copy chat pesanan pembeli di WA, lalu kirim/paste ke Bot Rekap.\n"
        f"3. AI akan otomatis mengekstrak & mencatatnya ke file Excel Anda!\n"
        f"4. Buka Web Dashboard untuk melihat ringkasan pesanan & download Excel.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Pendaftaran dibatalkan. Ketik /daftar jika ingin memulai kembali.")
    return ConversationHandler.END

def build_onboarding_app(token: str):
    app = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_handler),
            CommandHandler("daftar", start_handler),
        ],
        states={
            NAMA_TOKO: [MessageHandler(filters.TEXT & ~filters.COMMAND, nama_toko_handler)],
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
            CONTOH_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, contoh_format_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )

    app.add_handler(conv_handler)
    return app

if __name__ == "__main__":
    token = config.TELEGRAM_ONBOARDING_TOKEN
    if not token:
        print("Error: TELEGRAM_ONBOARDING_TOKEN belum diisi di .env")
    else:
        print("Menjalankan Bot Onboarding Telegram...")
        app = build_onboarding_app(token)
        app.run_polling()
