# 📦 Rekap PO UMKM - All-in-One Streamlit & AI

Aplikasi rekapitulasi pesanan Pre-Order (PO) otomatis untuk UMKM berbasis **Streamlit Multi-Tenant Dashboard**, **Google Gemini AI Extractor**, dan **GitHub Storage Database (`.xlsx`)**.

---

## 🌟 Fitur Utama (All-in-One Streamlit)

1. **Tanpa Perlu Bot Server / 100% Gratis di Cloud**:
   - Cukup 1 kali deploy ke **Streamlit Community Cloud**.
   - Tidak perlu setup bot Telegram atau server VPS terpisah.
2. **Multi-Tenant Onboarding & Login**:
   - Pendaftaran toko langsung di halaman web (**Tab: Daftar Toko Baru**).
   - Setiap toko memiliki file database `rekap_pesanan.xlsx` sendiri yang terisolasi.
3. **⚡ Input Cepat Chat WhatsApp (Gemini AI Extractor)**:
   - Pedagang cukup **Copy-Paste chat pesanan pembeli dari WhatsApp** ke kotak input di web.
   - Klik **"🚀 Ekstrak Pesanan dengan AI"**.
   - Gemini AI otomatis membaca Nama Pemesan, Nomor WA, Daftar Item & Qty, Alamat Pengiriman, dan Estimasi Total.
   - Preview hasil ekstraksi dapat diedit sebelum disimpan ke database Excel.
4. **Metrik & Analitik Real-Time**:
   - Total Pesanan Masuk, Estimasi Total Omset, Pesanan Baru/Pending, dan Total Qty Item Terjual.
5. **Manajemen Status & Ekspor Data**:
   - Update status pesanan langsung (*Baru ➡️ Diproses ➡️ Dikirim ➡️ Selesai*).
   - Tombol download file Excel `.xlsx` langsung ke HP/Laptop.

---

## 📁 Struktur Direktori

```text
Rekap UMKM/
├── config.py                   # Centralized configuration loader
├── requirements.txt            # Python dependencies
├── .env.example                # Template variabel lingkungan
├── core/
│   ├── models.py               # Schema Pydantic (Tenant, OrderItem, OrderRecord)
│   ├── ai_parser.py            # Gemini AI parser & Regex fallback
│   └── github_db.py            # Multi-tenant GitHub / Local Excel storage engine
├── dashboard/
│   └── app.py                  # Streamlit All-in-One Multi-Tenant Web App
└── tests/
    ├── test_config.py
    ├── test_models.py
    ├── test_ai_parser.py
    ├── test_github_db.py
    └── test_e2e_simulation.py
```

---

## 🚀 Cara Menjalankan Secara Lokal

1. **Aktifkan Virtual Environment**:
   ```bash
   source venv/bin/activate
   ```
2. **Jalankan Aplikasi Streamlit**:
   ```bash
   streamlit run dashboard/app.py
   ```

---

## ☁️ Cara Deploy ke Streamlit Community Cloud (Gratis Selamanya)

1. **Push project ini ke repository GitHub Anda**:
   ```bash
   git add .
   git commit -m "feat: rekap umkm all-in-one streamlit app"
   git push origin main
   ```
2. **Buka [share.streamlit.io](https://share.streamlit.io)** dan klik **New App**.
3. **Pilih Repository**, set Main file path: `dashboard/app.py`.
4. **Masukkan Secrets di Streamlit Cloud Settings (Opsional untuk Sync GitHub Repo & Gemini)**:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   GITHUB_TOKEN = "ghp_..."
   GITHUB_REPO = "username/rekap-database-repo"
   GITHUB_BRANCH = "main"
   SECRET_KEY = "kunci-rahasia-anda"
   ```
5. Klik **Deploy** — Web app langsung aktif dan bisa diakses via browser HP/Laptop seluruh pedagang!
