import re
import json
import uuid
from datetime import datetime
from typing import Optional
from core.models import OrderRecord, OrderItem
from config import config

def generate_order_id() -> str:
    """Generate a clean readable order ID, e.g., PO-20261009-A1B2"""
    date_str = datetime.now().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:4].upper()
    return f"PO-{date_str}-{unique_suffix}"

def fallback_chat_parser(chat_text: str) -> OrderRecord:
    """Heuristic / Regex fallback parser for Indonesian WhatsApp order messages."""
    lines = [line.strip() for line in chat_text.splitlines() if line.strip()]
    nama = "Pelanggan (Tanpa Nama)"
    no_hp = ""
    alamat = ""
    items = []
    total_harga = 0.0

    # Extract common Indonesian PO patterns
    for line in lines:
        line_lower = line.lower()
        # Extract name
        if any(key in line_lower for key in ["nama:", "nama pemesan:", "an:", "a/n:", "atas nama:"]):
            parts = re.split(r":|an\s|a/n\s", line, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[-1].strip():
                nama = parts[-1].strip()
        # Extract phone
        elif any(key in line_lower for key in ["no hp:", "wa:", "telepon:", "no:"]):
            nums = re.findall(r"(\+?62\d+|08\d+)", line)
            if nums:
                no_hp = nums[0]
        # Extract address
        elif any(key in line_lower for key in ["alamat:", "kirim ke:", "tujuan:", "lokasi:"]):
            parts = re.split(r":|kirim ke", line, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[-1].strip():
                alamat = parts[-1].strip()
        # Extract items (lines with numbers or bullet points)
        elif line.startswith(("-", "*", "•")) or re.search(r"\d+\s*(pcs|porsi|box|biji|bungkus|buah|pack|kg|gr|x)", line_lower):
            clean_item = re.sub(r"^[-*•]\s*", "", line)
            # detect qty
            qty_match = re.search(r"(\d+)\s*(pcs|porsi|box|biji|bungkus|buah|pack|kg|gr|x)?", clean_item, flags=re.IGNORECASE)
            qty = int(qty_match.group(1)) if qty_match else 1
            item_name = re.sub(r"(\d+)\s*(pcs|porsi|box|biji|bungkus|buah|pack|kg|gr|x)?", "", clean_item, flags=re.IGNORECASE).strip()
            if not item_name:
                item_name = clean_item
            items.append(OrderItem(nama_item=item_name, qty=qty, harga_satuan=0.0, subtotal=0.0))

    if not items:
        # Default fallback item from main text
        items.append(OrderItem(nama_item="Pesanan Chat", qty=1, harga_satuan=0.0, subtotal=0.0))

    return OrderRecord(
        id_pesanan=generate_order_id(),
        tanggal_masuk=datetime.now().strftime("%Y-%m-%d %H:%M"),
        nama_pemesan=nama,
        no_hp=no_hp,
        alamat_pengiriman=alamat,
        items=items,
        total_harga=total_harga,
        status_pesanan="Baru",
        raw_chat=chat_text
    )

def parse_order_chat(chat_text: str, api_key: Optional[str] = None, contoh_format: str = "") -> OrderRecord:
    """Parse raw chat text into an OrderRecord using Gemini AI with fallback to regex heuristics."""
    active_key = api_key or config.GEMINI_API_KEY

    if not active_key:
        return fallback_chat_parser(chat_text)

    try:
        # Attempt Gemini 1.5/2.0 API call
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=active_key)
        
        system_instruction = (
            "Kamu adalah asisten AI ekstraktor pesanan PO (Pre-Order) untuk UMKM Indonesia.\n"
            "Tugasmu adalah membaca teks chat WhatsApp pesanan dari pembeli dan mengekstraknya "
            "menjadi format JSON terstruktur yang valid.\n"
            "Pastikan kamu mengekstrak: nama_pemesan, no_hp, alamat_pengiriman, daftar items (nama_item, qty, harga_satuan, subtotal), total_harga, catatan.\n"
            "Jika informasi nama tidak ditemukan, gunakan 'Pelanggan'. Jika harga tidak tertera, isi 0."
        )

        prompt = f"Teks Chat Masuk:\n\"\"\"\n{chat_text}\n\"\"\"\n"
        if contoh_format:
            prompt += f"\nContoh Format Toko Ini Sebagai Referensi:\n\"\"\"\n{contoh_format}\n\"\"\"\n"

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=OrderRecord,
                temperature=0.1,
            )
        )

        if response and response.text:
            data = json.loads(response.text)
            if not data.get("id_pesanan"):
                data["id_pesanan"] = generate_order_id()
            if not data.get("tanggal_masuk"):
                data["tanggal_masuk"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            data["raw_chat"] = chat_text
            return OrderRecord(**data)

    except Exception as e:
        # Fallback to local heuristic parser if API call fails or library unavailable
        pass

    return fallback_chat_parser(chat_text)
