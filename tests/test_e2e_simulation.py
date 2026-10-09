import os
import shutil
import tempfile
from core.github_db import StorageEngine
from core.models import TenantProfile, OrderRecord
from core.ai_parser import fallback_chat_parser

def test_full_e2e_flow():
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Initialize isolated engine
        engine = StorageEngine(local_root=temp_dir, use_local_fallback=True)

        # 2. Simulate Onboarding Registration
        tenant = TenantProfile(
            tenant_id="dapur_mama_berkah",
            nama_toko="Dapur Mama Berkah",
            telegram_user_id=987654321,
            username="dapurmama",
            password_hash="hashed_pw_test",
            contoh_format_po="Nama:\nPesanan:\nAlamat:",
            created_at="2026-10-09"
        )
        assert engine.register_tenant(tenant) is True

        # 3. Simulate Incoming WhatsApp Chat Copy-Pasted
        raw_chat = """
        Halo kak pesan:
        - Pempek Kapal Selam 4 pcs
        - Pempek Lenjer 6 pcs
        Atas nama: Hendra
        No HP: 081399887766
        Alamat: Cluster Anggrek No 5, Bintaro
        """
        parsed_orders = fallback_chat_parser(raw_chat)
        assert len(parsed_orders) >= 1
        first_order = parsed_orders[0]
        assert len(first_order.items) >= 2

        # 4. Save to Tenant's Excel Database
        save_success = engine.append_order("dapur_mama_berkah", first_order)
        assert save_success is True

        # 5. Verify Streamlit Data Reading
        df = engine.read_orders_dataframe("dapur_mama_berkah")
        assert len(df) == 1
        assert df.iloc[0]["ID Pesanan"] == first_order.id_pesanan
        assert df.iloc[0]["Status Pesanan"] == "Baru"

        # 6. Verify Status Update in Dashboard
        update_success = engine.update_order_status("dapur_mama_berkah", first_order.id_pesanan, "Diproses")
        assert update_success is True

        df_updated = engine.read_orders_dataframe("dapur_mama_berkah")
        assert df_updated.iloc[0]["Status Pesanan"] == "Diproses"

    finally:
        shutil.rmtree(temp_dir)
