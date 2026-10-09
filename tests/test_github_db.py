import os
import shutil
import tempfile
from pathlib import Path
from core.github_db import StorageEngine
from core.models import TenantProfile, OrderRecord, OrderItem

def test_local_storage_engine_tenant_lifecycle():
    temp_dir = tempfile.mkdtemp()
    try:
        engine = StorageEngine(local_root=temp_dir, use_local_fallback=True)

        tenant = TenantProfile(
            tenant_id="toko_berkah",
            nama_toko="Toko Berkah",
            telegram_user_id=123456,
            username="berkah",
            password_hash="hash_pw",
            contoh_format_po="Nama: ...",
            created_at="2026-10-09"
        )

        # 1. Register Tenant
        success = engine.register_tenant(tenant)
        assert success is True

        # 2. Lookup Tenant by Telegram ID
        found_tenant = engine.get_tenant_by_telegram_id(123456)
        assert found_tenant is not None
        assert found_tenant.nama_toko == "Toko Berkah"

        # 3. Lookup Tenant by Username
        found_by_user = engine.get_tenant_by_username("berkah")
        assert found_by_user is not None
        assert found_by_user.tenant_id == "toko_berkah"

        # 4. Append Order
        order = OrderRecord(
            id_pesanan="PO-TEST-001",
            tanggal_masuk="2026-10-09 13:00",
            nama_pemesan="Budi",
            no_hp="08123456789",
            alamat_pengiriman="Jakarta",
            items=[OrderItem(nama_item="Risol Mayo", qty=5, harga_satuan=5000, subtotal=25000)],
            total_harga=25000,
            status_pesanan="Baru"
        )
        engine.append_order("toko_berkah", order)

        # 5. Read Orders
        orders_df = engine.read_orders_dataframe("toko_berkah")
        assert len(orders_df) == 1
        assert orders_df.iloc[0]["Nama Pemesan"] == "Budi"
        assert orders_df.iloc[0]["ID Pesanan"] == "PO-TEST-001"

    finally:
        shutil.rmtree(temp_dir)
