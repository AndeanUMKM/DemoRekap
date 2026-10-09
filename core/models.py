from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class OrderItem(BaseModel):
    nama_item: str = Field(description="Nama produk / menu makanan / barang yang dipesan")
    qty: int = Field(default=1, description="Jumlah kuantiti barang")
    harga_satuan: float = Field(default=0.0, description="Harga satuan barang jika ada")
    subtotal: float = Field(default=0.0, description="Total harga item (qty * harga_satuan)")
    catatan: Optional[str] = Field(default="", description="Catatan spesifik item (misal: pedas, level 2)")

class OrderRecord(BaseModel):
    id_pesanan: str = Field(default="", description="ID Unik Pesanan (misal: PO-20261009-001)")
    tanggal_masuk: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"), description="Waktu pesanan dicatat")
    nama_pemesan: str = Field(default="Pelanggan", description="Nama pemesan / pembeli")
    no_hp: str = Field(default="", description="Nomor WhatsApp / telepon pembeli")
    alamat_pengiriman: str = Field(default="", description="Alamat lengkap atau catatan tempat pengiriman")
    items: List[OrderItem] = Field(default_factory=list, description="Daftar item pesanan")
    total_harga: float = Field(default=0.0, description="Total keseluruhan pesanan")
    metode_pembayaran: str = Field(default="Belum Bayar", description="Metode / status pembayaran (misal: Transfer, COD, Lunas)")
    status_pesanan: str = Field(default="Baru", description="Status PO: Baru, Diproses, Dikirim, Selesai, Dibatalkan")
    raw_chat: str = Field(default="", description="Isi teks chat asli yang di-copy-paste")

class BatchOrderExtraction(BaseModel):
    pesanan_list: List[OrderRecord] = Field(default_factory=list, description="Daftar seluruh pesanan PO yang ditemukan di dalam teks chat")

class TenantProfile(BaseModel):
    tenant_id: str = Field(description="Slug unik tenant (misal: toko_berkah)")
    nama_toko: str = Field(description="Nama resmi toko / UMKM")
    telegram_user_id: int = Field(default=0, description="ID Akun Telegram pemilik jika ada")
    username: str = Field(description="Username untuk login web dashboard")
    password_hash: str = Field(description="Hash password untuk login web")
    contoh_format_po: str = Field(default="", description="Contoh format teks chat PO yang biasa digunakan pembeli")
    created_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
