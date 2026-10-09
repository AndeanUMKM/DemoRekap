# Implementation Plan: Rekap Pesanan PO UMKM (Multi-Tenant MVP)

Sistem rekapitulasi pesanan PO berbasis Telegram Bot (Copy-Paste Chat WhatsApp / Screenshot), Gemini AI Parser, GitHub Storage (Database `.xlsx` terisolasi per tenant), dan Streamlit Multi-Tenant Dashboard.

## Proposed System Architecture

```
[ Pelanggan ]
      │ (Chat Pesanan PO di WhatsApp)
      ▼
[ WhatsApp Pedagang ] ─── (Copy-Paste / Kirim Teks) ───► [ Telegram Bot 2: Rekap PO ]
                                                                   │
                                                                   ▼
                                                          [ Gemini AI Parser ]
                                                          (Ekstrak Nama, Item, Qty, Total)
                                                                   │
                                                                   ▼
                                                          [ GitHub Repo Storage ]
                                                          (tenants/{tenant_id}/rekap_pesanan.xlsx)
                                                                   │
                                                                   ▼
                                                          [ Streamlit Dashboard ]
                                                          (Login Multi-Tenant & Rekap PO)
```

---

## File Structure

```text
Rekap UMKM/
├── config.py                   # Centralized configuration & environment loader
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment variables
├── core/
│   ├── __init__.py
│   ├── github_db.py            # GitHub API client for tenants & Excel read/write
│   ├── ai_parser.py            # Gemini AI parser for structured PO extraction
│   └── models.py               # Pydantic schemas (Tenant, OrderItem, OrderRecord)
├── bots/
│   ├── __init__.py
│   ├── onboarding_bot.py       # Telegram Bot 1: Tenant registration & folder setup
│   └── rekap_bot.py            # Telegram Bot 2: Ingest chat copy-paste, parse & save to Excel
├── dashboard/
│   ├── __init__.py
│   ├── app.py                  # Streamlit Multi-Tenant Dashboard
│   └── components.py           # Dashboard widgets (KPIs, Data Table, Excel exporter)
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_ai_parser.py
    ├── test_github_db.py
    └── test_bots.py
```

---

## Execution Plan & Tasks

### Task 1: Project Setup & Environment Configuration
- Create `requirements.txt` with dependencies (`streamlit`, `python-telegram-bot>=20.0`, `google-genai`, `PyGithub`, `pandas`, `openpyxl`, `pydantic`, `pytest`, `python-dotenv`).
- Create `config.py` and `.env.example` with support for:
  - `TELEGRAM_ONBOARDING_TOKEN`
  - `TELEGRAM_REKAP_TOKEN`
  - `GITHUB_TOKEN` & `GITHUB_REPO`
  - `GEMINI_API_KEY`
- Setup automated test runner and test configuration.

### Task 2: Data Models & Gemini AI Parser
- Define Pydantic models in `core/models.py`:
  - `OrderItem` (nama_item, qty, harga_satuan, subtotal)
  - `OrderRecord` (id_pesanan, tanggal_masuk, nama_pemesan, no_hp, alamat, items, total_harga, catatan, status)
  - `TenantProfile` (tenant_id, nama_toko, telegram_user_id, username, password_hash, contoh_format_po)
- Implement `core/ai_parser.py` using `google-genai` structured output mode.
- Add comprehensive test cases in `tests/test_ai_parser.py`.

### Task 3: GitHub Multi-Tenant Database Storage Engine
- Implement `core/github_db.py`:
  - `get_or_create_tenants_index()` -> manage `tenants.json`
  - `register_tenant_workspace(tenant: TenantProfile)` -> creates folder `tenants/{tenant_id}/`, saves `config.json`, initializes `rekap_pesanan.xlsx` with standard headers.
  - `get_tenant_by_telegram_id(telegram_id)` -> lookup tenant
  - `read_tenant_orders(tenant_id)` -> download and parse `rekap_pesanan.xlsx` into DataFrame / list of `OrderRecord`.
  - `append_tenant_order(tenant_id, order: OrderRecord)` -> atomic read-modify-push of `.xlsx` file via GitHub API.
- Add mock unit tests in `tests/test_github_db.py`.

### Task 4: Bot 1 (Onboarding Bot)
- Implement `bots/onboarding_bot.py` using `python-telegram-bot` ConversationHandler:
  - Step 1: `/start` atau `/daftar`
  - Step 2: Input Nama Toko & Username Web
  - Step 3: Input Password Web
  - Step 4: Input Contoh Format Chat PO
  - Step 5: Eksekusi inisialisasi folder GitHub & berikan link Bot Rekap.
- Add unit test suite in `tests/test_bots.py`.

### Task 5: Bot 2 (Rekapitulasi Bot)
- Implement `bots/rekap_bot.py`:
  - Listener pesan teks hasil copy-paste dari WA.
  - Cek validasi tenant berdasarkan Telegram ID.
  - Kirim teks ke Gemini AI untuk ekstraksi data PO terstruktur.
  - Simpan baris pesanan ke file `.xlsx` di folder GitHub tenant.
  - Kirim balasan konfirmasi ringkas & rapi di Telegram.

### Task 6: Streamlit Multi-Tenant Web Dashboard
- Implement `dashboard/app.py`:
  - Halaman Login multi-tenant (verifikasi ke `config.json` di GitHub).
  - KPI Metrics (Total Pesanan, Total Omset, Pesanan Hari Ini, Status PO).
  - Interactive Order Table (Pencarian, Filter Tanggal, Ubah Status).
  - Tombol Download File Excel.

### Task 7: End-to-End Verification & Documentation
- Jalankan seluruh unit test (`pytest`).
- Buat `README.md` panduan instalasi, konfigurasi token, dan cara menjalankan bot + web dashboard.
