import pytest
from core.ai_parser import parse_order_chat, fallback_chat_parser
from core.models import OrderRecord

SAMPLE_CHAT_1 = """
Halo kak mau pesan:
- Risol Mayo 5 pcs
- Pastel Kari 3 pcs
Total berapa ya?
Atas nama: Siti Rahma
No HP: 081987654321
Kirim ke: Jl. Melati No. 12, Kebon Jeruk
"""

def test_fallback_chat_parser():
    parsed = fallback_chat_parser(SAMPLE_CHAT_1)
    assert isinstance(parsed, OrderRecord)
    assert "Siti Rahma" in parsed.nama_pemesan or parsed.nama_pemesan != ""
    assert len(parsed.items) > 0
    assert parsed.raw_chat == SAMPLE_CHAT_1

def test_parse_order_chat_without_api_key():
    # When api key is not set, it should safely use fallback
    result = parse_order_chat(SAMPLE_CHAT_1, api_key="", contoh_format="")
    assert isinstance(result, OrderRecord)
    assert len(result.items) >= 1
