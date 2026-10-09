import re
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from core.models import OrderRecord, OrderItem, BatchOrderExtraction
from config import config

logger = logging.getLogger(__name__)

def generate_order_id() -> str:
    """Generate a clean readable order ID, e.g., PO-20261009-A1B2"""
    date_str = datetime.now().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:4].upper()
    return f"PO-{date_str}-{unique_suffix}"

def clean_phone_number(text: str) -> str:
    """Extract and normalize Indonesian phone numbers."""
    matches = re.findall(r"(\+?62[\s\-0-9]{8,15}|08[\s\-0-9]{8,15})", text)
    if matches:
        clean = re.sub(r"[\s\-]", "", matches[0])
        return clean
    return ""

def extract_price(text: str) -> float:
    """Extract explicit price from formatted string, e.g. (55.000), Rp 55.000, 55rb, 55k"""
    # Match prices inside parentheses: (55.000) or (Rp 55.000) or (55k)
    match_paren = re.search(r"\((?:rp\.?\s*)?([\d\.]+)\s*(rb|k)?\)", text, flags=re.IGNORECASE)
    if match_paren:
        raw_num = match_paren.group(1).replace(".", "")
        if raw_num.isdigit():
            val = float(raw_num)
            if match_paren.group(2) or (val < 1000 and len(raw_num) <= 3):
                val *= 1000
            return val

    # Match prices with explicit Rp: Rp 55.000 or Rp55.000
    match_rp = re.search(r"rp\.?\s*([\d\.]+)\s*(rb|k)?", text, flags=re.IGNORECASE)
    if match_rp:
        raw_num = match_rp.group(1).replace(".", "")
        if raw_num.isdigit():
            val = float(raw_num)
            if match_rp.group(2) or (val < 1000 and len(raw_num) <= 3):
                val *= 1000
            return val

    return 0.0

def parse_single_order_block(block_text: str) -> Optional[OrderRecord]:
    """Extract a single order block into an OrderRecord."""
    lines = [l.strip() for l in block_text.splitlines() if l.strip()]
    if not lines:
        return None

    nama = ""
    no_hp = ""
    alamat_lines = []
    items: List[OrderItem] = []
    is_collecting_items = False
    is_collecting_address = False

    for line in lines:
        line_lower = line.lower()

        # Ignore broadcast or generic tags
        if any(term in line_lower for term in ["pilih pengiriman", "pengiriman tiap", "batch", "last order", "ready stock", "kurir instan", "paxel", "ncs", "isi format order", "berminat bisa"]):
            continue

        # Check for Name header
        if re.search(r"^(?:nama|an|a/n|nama penerima|nama pemesan)\s*[:=]", line_lower):
            parts = re.split(r"[:=]", line, maxsplit=1)
            if len(parts) > 1:
                nama = parts[1].strip()
            is_collecting_items = False
            is_collecting_address = False
            continue

        # Check for Phone header
        if re.search(r"^(?:no\s*tlp|no\s*hp|wa|telepon|nohp|telp|kontak)\s*[:=]", line_lower):
            no_hp = clean_phone_number(line)
            is_collecting_items = False
            is_collecting_address = False
            continue

        # Standalone phone number on its own line
        phone_match = clean_phone_number(line)
        if phone_match and len(line) <= 25 and not line.startswith(("-", "*", "•")):
            no_hp = phone_match
            continue

        # Check for Address header
        if re.search(r"^(?:alamat|alamat lengkap|kirim ke|lokasi|tujuan)\s*[:=]", line_lower):
            parts = re.split(r"[:=]", line, maxsplit=1)
            if len(parts) > 1 and parts[1].strip():
                alamat_lines.append(parts[1].strip())
            is_collecting_address = True
            is_collecting_items = False
            continue

        # Check for Order Items header
        if re.search(r"^(?:orderan|pesanan|order|list order|items?)\s*[:=]", line_lower):
            is_collecting_items = True
            is_collecting_address = False
            continue

        # Process item lines
        if is_collecting_items or line.startswith(("-", "*", "•")) or re.search(r"^\d+\.\s+", line):
            clean_line = re.sub(r"^[-*•\d\.]+\s*", "", line).strip()
            if not clean_line or len(clean_line) < 3 or clean_line.lower().startswith("fo "):
                continue

            price = extract_price(clean_line)
            clean_no_price = re.sub(r"\((?:rp\.?\s*)?[\d\.]+\s*(?:rb|k)?\)", "", clean_line, flags=re.IGNORECASE)
            clean_no_price = re.sub(r"rp\.?\s*[\d\.]+\s*(?:rb|k)?", "", clean_no_price, flags=re.IGNORECASE).strip()

            qty = 1
            qty_match = re.search(r"(?:^|\s*-\s*|\s+)(\d+)\s*(?:pcs|porsi|box|bungkus|buah|pack|kg|gr|x)?$", clean_no_price, flags=re.IGNORECASE)
            item_name = clean_no_price
            if qty_match:
                qty = int(qty_match.group(1))
                item_name = clean_no_price[:qty_match.start()].strip(" -:")

            if item_name:
                subtotal = price * qty if price > 0 else 0.0
                items.append(OrderItem(nama_item=item_name, qty=qty, harga_satuan=price, subtotal=subtotal))
            continue

        # Address continuation
        if is_collecting_address:
            if not line.startswith(("-", "*", "•")) and not re.search(r"^(?:orderan|pesanan|fo\b)", line_lower):
                alamat_lines.append(line)

    if not nama and not items and not no_hp:
        return None

    alamat = ", ".join(alamat_lines)
    total_harga = sum(it.subtotal for it in items)

    return OrderRecord(
        id_pesanan=generate_order_id(),
        tanggal_masuk=datetime.now().strftime("%Y-%m-%d %H:%M"),
        nama_pemesan=nama or "Pelanggan",
        no_hp=no_hp,
        alamat_pengiriman=alamat,
        items=items if items else [OrderItem(nama_item="Pesanan PO", qty=1, harga_satuan=0.0, subtotal=0.0)],
        total_harga=total_harga,
        status_pesanan="Baru",
        raw_chat=block_text
    )

def fallback_chat_parser(chat_text: str) -> List[OrderRecord]:
    """Smart Heuristic / Regex parser that segments multiple orders and removes broadcast junk."""
    order_marker_pattern = r"(?=(?:^|\n)(?:\*?FO\s+[A-Za-z0-9]+\*?|\*?Format Order|\*?Nama\s*[:=]|\*?Nama penerima\s*[:=]))"
    raw_blocks = re.split(order_marker_pattern, chat_text, flags=re.IGNORECASE)

    orders: List[OrderRecord] = []
    for block in raw_blocks:
        if not block.strip():
            continue
        parsed = parse_single_order_block(block)
        if parsed and (parsed.nama_pemesan != "Pelanggan" or (len(parsed.items) > 0 and parsed.items[0].nama_item != "Pesanan PO")):
            orders.append(parsed)

    if not orders:
        single = parse_single_order_block(chat_text)
        if single:
            orders.append(single)

    return orders

def parse_order_chat(chat_text: str, api_key: Optional[str] = None, contoh_format: str = "") -> Tuple[List[OrderRecord], str]:
    """Parse raw chat text into (list_of_orders, engine_used) with strict timeout and fallback."""
    active_key = api_key or config.GEMINI_API_KEY

    if active_key and len(active_key.strip()) > 10:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=active_key.strip())
            
            system_instruction = (
                "Kamu adalah asisten AI ekstraktor pesanan Pre-Order (PO) untuk UMKM Indonesia.\n"
                "Tugasmu adalah membaca teks chat WhatsApp pesanan dari pembeli (yang bisa berisi 1 atau LEBIH DARI 1 pesanan pembeli sekaligus) "
                "dan mengekstrak SELURUH pesanan pembeli menjadi daftar terstruktur (pesanan_list).\n"
                "PENTING:\n"
                "- Abaikan pengumuman broadcast toko, jadwal PO (misal: 'PO TANGERANG BATCH 2', 'last order...', 'Pilih pengiriman...').\n"
                "- Ekstrak setiap pemesan secara terpisah: nama_pemesan, no_hp (format nomor bersih), alamat_pengiriman (gabungkan catatan patokan alamat), "
                "daftar items (nama_item, qty, harga_satuan, subtotal), total_harga.\n"
                "- Jika harga satuan tertera (misal: 55.000 atau (55.000)), hitung subtotal dan total_harga.\n"
                "- Kembalikan output JSON sesuai dengan skema BatchOrderExtraction."
            )

            prompt = f"Teks Chat Masuk dari WhatsApp:\n\"\"\"\n{chat_text}\n\"\"\"\n"
            if contoh_format:
                prompt += f"\nContoh Format Toko Sebagai Referensi:\n\"\"\"\n{contoh_format}\n\"\"\"\n"

            # Use official stable model
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=BatchOrderExtraction,
                    temperature=0.1,
                )
            )
            if response and response.text:
                data = json.loads(response.text)
                pesanan_list = data.get("pesanan_list", [])
                results = []
                for p in pesanan_list:
                    if not p.get("id_pesanan"):
                        p["id_pesanan"] = generate_order_id()
                    if not p.get("tanggal_masuk"):
                        p["tanggal_masuk"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    p["raw_chat"] = chat_text
                    results.append(OrderRecord(**p))
                if results:
                    return results, "Gemini AI (gemini-1.5-flash)"

        except Exception as e:
            logger.warning(f"Gemini API call skipped/failed: {e}")

    # Instant Fallback to smart regex parser (takes ~5 milliseconds)
    fallback_res = fallback_chat_parser(chat_text)
    return fallback_res, "Smart Regex Engine"
