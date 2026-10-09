from core.models import OrderItem, OrderRecord, TenantProfile

def test_order_item_creation():
    item = OrderItem(nama_item="Ayam Bakar", qty=2, harga_satuan=25000, subtotal=50000)
    assert item.nama_item == "Ayam Bakar"
    assert item.qty == 2
    assert item.subtotal == 50000

def test_order_record_creation():
    item = OrderItem(nama_item="Ayam Bakar", qty=2, harga_satuan=25000, subtotal=50000)
    order = OrderRecord(
        id_pesanan="ORD-001",
        tanggal_masuk="2026-10-09 13:00",
        nama_pemesan="Budi Santoso",
        no_hp="08123456789",
        alamat_pengiriman="Jl. Mawar No 10, Jakarta",
        items=[item],
        total_harga=50000,
        status_pesanan="Baru",
        raw_chat="Halo kak pesan Ayam Bakar 2 porsi kirim ke Jl Mawar no 10 Budi 08123456789"
    )
    assert order.id_pesanan == "ORD-001"
    assert len(order.items) == 1
    assert order.total_harga == 50000

def test_tenant_profile_creation():
    tenant = TenantProfile(
        tenant_id="toko_berkah",
        nama_toko="Toko Berkah Snack",
        telegram_user_id=123456789,
        username="berkahadmin",
        password_hash="hashed_pw_123",
        contoh_format_po="Nama: ...\nPesanan: ...",
        created_at="2026-10-09"
    )
    assert tenant.tenant_id == "toko_berkah"
    assert tenant.telegram_user_id == 123456789
