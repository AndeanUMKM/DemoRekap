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
    orders = fallback_chat_parser(SAMPLE_CHAT_1)
    assert isinstance(orders, list)
    assert len(orders) >= 1
    assert isinstance(orders[0], OrderRecord)
    assert len(orders[0].items) >= 1

def test_parse_order_chat_without_api_key():
    # When api key is not set, it should safely use fallback
    results, engine = parse_order_chat(SAMPLE_CHAT_1, api_key="", contoh_format="")
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], OrderRecord)
    assert len(results[0].items) >= 1
    assert "Smart Regex Fallback" in engine or "Fallback" in engine
