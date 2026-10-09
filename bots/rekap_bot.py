import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import config
from core.models import OrderRecord
from core.ai_parser import parse_order_chat
from core.github_db import storage

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tenant = storage.get_tenant_by_telegram_id(user.id)

    if not tenant:
        await update.message.reply_text(
            f"Halo Kak {user.first_name}! 👋\n\n"
            "Akun Telegram Anda belum terdaftar di toko manapun.\n"
            "👉 Silakan lakukan pendaftaran toko terlebih dahulu melalui **Bot Onboarding**.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"Halo Kak {user.first_name} (**{tenant.nama_toko}**)! 👋\n\n"
        "🤖 **Bot Rekap Pesanan PO Siap Digunakan.**\n\n"
        "📌 **Cara Menggunakan:**\n"
        "Cukup copy-paste atau ketik chat pesanan pembeli dari WhatsApp langsung ke sini. "
        "AI akan otomatis mengekstrak rincian pesanan dan mencatatnya ke database Excel Anda!",
        parse_mode="Markdown"
    )

async def rekap_summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View quick summary stats for tenant."""
    user = update.effective_user
    tenant = storage.get_tenant_by_telegram_id(user.id)

    if not tenant:
        await update.message.reply_text("Silakan daftar terlebih dahulu di Bot Onboarding.")
        return

    df = storage.read_orders_dataframe(tenant.tenant_id)
    total_orders = len(df)
    total_revenue = df["Total Harga"].sum() if not df.empty and "Total Harga" in df.columns else 0

    await update.message.reply_text(
        f"📊 **Ringkasan Rekap PO - {tenant.nama_toko}**\n\n"
        f"📦 **Total Pesanan Masuk**: {total_orders} pesanan\n"
        f"💰 **Total Omset**: Rp {total_revenue:,.0f}\n\n"
        f"Gunakan Web Dashboard Streamlit untuk melihat detail dan download file Excel!",
        parse_mode="Markdown"
    )

async def order_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming forwarded / pasted order text."""
    user = update.effective_user
    chat_text = update.message.text.strip()

    tenant = storage.get_tenant_by_telegram_id(user.id)
    if not tenant:
        await update.message.reply_text(
            "⚠️ Akun Anda belum terdaftar. Silakan daftar dulu melalui **Bot Onboarding**.",
            parse_mode="Markdown"
        )
        return

    # Temporary reaction / status
    status_msg = await update.message.reply_text("⏳ *Membaca dan mengekstrak rincian pesanan...*", parse_mode="Markdown")

    try:
        # Extract orders using AI/Smart Engine
        res = parse_order_chat(chat_text, contoh_format=tenant.contoh_format_po)
        if isinstance(res, tuple) and len(res) == 2:
            extracted_orders, engine_used = res
        elif isinstance(res, tuple) and len(res) >= 1:
            extracted_orders, engine_used = res[0], "AI Engine"
        else:
            extracted_orders, engine_used = res, "AI Engine"

        if not isinstance(extracted_orders, list):
            extracted_orders = [extracted_orders] if extracted_orders else []

        if not extracted_orders:
            await status_msg.edit_text("⚠️ Tidak ada data pesanan yang berhasil diekstrak dari teks tersebut.")
            return

        saved_count = 0
        cards = []
        for order in extracted_orders:
            if storage.append_order(tenant.tenant_id, order):
                saved_count += 1
                items_text = "\n".join([f"  • {item.nama_item} (x{item.qty})" + (f" - Rp {item.subtotal:,.0f}" if item.subtotal > 0 else "") for item in order.items])
                cards.append(
                    f"🆔 **ID**: `{order.id_pesanan}`\n"
                    f"👤 **Pemesan**: **{order.nama_pemesan}**\n"
                    f"📞 **No HP**: {order.no_hp or '-'}\n"
                    f"📍 **Alamat**: {order.alamat_pengiriman or '-'}\n"
                    f"📦 **Items**:\n{items_text}\n"
                    f"💰 **Total**: Rp {order.total_harga:,.0f}"
                )

        if saved_count > 0:
            summary = (
                f"✅ **{saved_count} Pesanan Berhasil Direkap!** ({engine_used})\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n" +
                "\n\n━━━━━━━━━━━━━━━━━━━━━\n".join(cards) +
                f"\n\n📂 Tersimpan di: `tenants/{tenant.tenant_id}/rekap_pesanan.xlsx`"
            )
            await status_msg.edit_text(summary, parse_mode="Markdown")
        else:
            await status_msg.edit_text("❌ Gagal menyimpan pesanan ke database Excel.")

    except Exception as e:
        logger.error(f"Error processing order chat: {e}", exc_info=True)
        await status_msg.edit_text(f"⚠️ Terjadi kendala saat memproses pesanan: {str(e)}")
        logger.error(f"Error processing order chat: {e}", exc_info=True)
        await status_msg.edit_text(f"⚠️ Terjadi kendala saat memproses pesanan: {str(e)}")

def build_rekap_app(token: str):
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("rekap", rekap_summary_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, order_chat_handler))

    return app

if __name__ == "__main__":
    token = config.TELEGRAM_REKAP_TOKEN
    if not token:
        print("Error: TELEGRAM_REKAP_TOKEN belum diisi di .env")
    else:
        print("Menjalankan Bot Rekap Pesanan Telegram...")
        app = build_rekap_app(token)
        app.run_polling()
