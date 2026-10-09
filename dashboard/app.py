import streamlit as st
import pandas as pd
import io
import hashlib
import json
import os
from datetime import datetime, date
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from core.github_db import storage, EXCEL_COLUMNS
from core.models import TenantProfile, OrderRecord, OrderItem
from core.ai_parser import parse_order_chat
from config import config

# Page Configuration
st.set_page_config(
    page_title="Rekap PO UMKM - Multi-Tenant AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom UI Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-title {
        font-size: 1.9rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }
    .main-subtitle {
        font-size: 0.95rem;
        color: #64748B;
        margin-bottom: 24px;
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .kpi-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748B;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 700;
        color: #0F172A;
        margin-top: 4px;
    }
    .order-box {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_pw(input_password: str, hashed_password: str) -> bool:
    return hash_pw(input_password) == hashed_password

# ------------------ Session Authentication ------------------ #

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.tenant = None

if "extracted_orders" not in st.session_state:
    st.session_state.extracted_orders = []

def auth_view():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.8, 1])

    with c2:
        st.markdown("<h2 style='text-align: center; margin-bottom: 2px;'>📦 Rekap PO UMKM</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748B;'>Sistem Rekapitulasi Pesanan Chat WhatsApp Otomatis</p>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Masuk / Login", "✨ Daftar Toko Baru"])

        # TAB 1: LOGIN
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username Toko", placeholder="contoh: dapurberkah").strip().lower()
                password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
                btn_login = st.form_submit_button("Masuk ke Dashboard 🚀", use_container_width=True)

                if btn_login:
                    if not username or not password:
                        st.error("Silakan masukkan username dan password.")
                    else:
                        tenant = storage.get_tenant_by_username(username)
                        if tenant and verify_pw(password, tenant.password_hash):
                            st.session_state.authenticated = True
                            st.session_state.tenant = tenant
                            st.success(f"Selamat datang, {tenant.nama_toko}!")
                            st.rerun()
                        else:
                            st.error("Username atau password salah. Pastikan Anda sudah mendaftarkan toko Anda.")

        # TAB 2: REGISTER
        with tab_register:
            with st.form("register_form"):
                nama_toko = st.text_input("Nama Toko / Usaha", placeholder="contoh: Dapur Mama Berkah").strip()
                reg_username = st.text_input("Buat Username Login", placeholder="huruf kecil tanpa spasi, contoh: dapurmama").strip().lower()
                reg_password = st.text_input("Buat Password Login", type="password", placeholder="Minimal 6 karakter")
                contoh_format = st.text_area(
                    "Contoh Format Chat Pesanan (Opsional)",
                    placeholder="Contoh:\nNama:\nPesanan:\nNo WA:\nAlamat:",
                    height=90,
                    help="AI akan menggunakan contoh ini untuk mengenali gaya chat pelanggan Anda."
                )
                btn_register = st.form_submit_button("Daftarkan Toko Sekarang ✨", use_container_width=True)

                if btn_register:
                    if not nama_toko or not reg_username or not reg_password:
                        st.error("Nama Toko, Username, dan Password wajib diisi.")
                    else:
                        existing = storage.get_tenant_by_username(reg_username)
                        if existing:
                            st.error(f"Username '{reg_username}' sudah dipakai toko lain. Silakan gunakan username lain.")
                        else:
                            slug = "".join([c if c.isalnum() or c == "_" else "_" for c in reg_username]).strip("_")
                            new_tenant = TenantProfile(
                                tenant_id=slug,
                                nama_toko=nama_toko,
                                telegram_user_id=0,
                                username=reg_username,
                                password_hash=hash_pw(reg_password),
                                contoh_format_po=contoh_format,
                                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            storage.register_tenant(new_tenant)
                            st.success(f"🎉 Toko '{nama_toko}' berhasil didaftarkan! Silakan login di tab sebelah.")

def main_dashboard():
    tenant: TenantProfile = st.session_state.tenant

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"### 🏪 {tenant.nama_toko}")
        st.caption(f"ID: `{tenant.tenant_id}` | User: `{tenant.username}`")
        
        # Engine status
        if config.GEMINI_API_KEY:
            st.success("🤖 **Gemini AI Active**")
        else:
            st.info("⚙️ **Smart Parser Active**")

        st.divider()

        st.subheader("🔍 Filter Data")
        status_filter = st.selectbox(
            "Status Pesanan",
            ["Semua Status", "Baru", "Diproses", "Dikirim", "Selesai", "Dibatalkan"]
        )
        search_query = st.text_input("Cari Pemesan / No HP / Alamat", placeholder="Ketik kata kunci...")

        st.divider()
        if st.button("🚪 Logout / Keluar", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.tenant = None
            st.session_state.extracted_orders = []
            st.rerun()

    # --- Header ---
    st.markdown(f"<div class='main-title'>Rekap Pesanan PO — {tenant.nama_toko}</div>", unsafe_allow_html=True)
    st.markdown("<div class='main-subtitle'>Ekstraksi otomatis chat WhatsApp pelanggan (single / batch pesanan) langsung ke Database Excel</div>", unsafe_allow_html=True)

    # ------------------ SECTION 1: QUICK PASTE AI EXTRACTOR ------------------ #
    with st.expander("⚡ **Input Cepat Chat WhatsApp (Ekstraksi Otomatis dengan AI)**", expanded=True):
        st.markdown("<p style='font-size:0.9rem; color:#475569;'>Tempel teks chat pesanan dari WhatsApp pembeli di bawah ini (bisa 1 pesanan atau beberapa pesanan sekaligus). Sistem akan membaca nama pemesan, nomor WA, daftar item, harga, dan alamat secara otomatis.</p>", unsafe_allow_html=True)

        chat_input = st.text_area(
            "Teks Chat Pesanan dari WhatsApp",
            placeholder="Contoh:\nNama : Alivia Shifa\nNo tlp : 081316982390\nAlamat : Jl. Melati no 5 Depok\nOrderan :\n- ayam kampung lengkuas 2\n- lele (5 ekor) 1",
            height=140,
            key="chat_paste_box"
        )

        col_act1, col_act2 = st.columns([2, 5])
        with col_act1:
            btn_extract = st.button("🚀 Ekstrak Pesanan dengan AI", use_container_width=True, type="primary")

        if btn_extract:
            if not chat_input.strip():
                st.warning("Silakan tempel teks chat pesanan terlebih dahulu.")
            else:
                with st.spinner("🤖 Sedang membaca & mengekstrak pesanan..."):
                    extracted_list = parse_order_chat(chat_input, contoh_format=tenant.contoh_format_po)
                    st.session_state.extracted_orders = extracted_list
                    if extracted_list:
                        st.success(f"🎯 Berhasil mendeteksi **{len(extracted_list)} pesanan**!")
                    else:
                        st.error("Tidak ada pesanan valid yang terdeteksi dari teks di atas.")

        # Preview Result Boxes if Extracted
        if st.session_state.extracted_orders:
            orders_to_show = st.session_state.extracted_orders
            st.markdown("---")
            st.markdown(f"#### 🎯 Hasil Ekstraksi ({len(orders_to_show)} Pesanan Terdeteksi):")

            for idx, ext in enumerate(orders_to_show):
                with st.container():
                    st.markdown(f"**Pesanan #{idx + 1} — ID: `{ext.id_pesanan}`**")
                    p_col1, p_col2, p_col3 = st.columns([1.2, 1.8, 1.5])
                    with p_col1:
                        ext.nama_pemesan = st.text_input("Nama Pemesan", value=ext.nama_pemesan, key=f"edit_nama_{idx}")
                        ext.no_hp = st.text_input("No HP / WhatsApp", value=ext.no_hp, key=f"edit_hp_{idx}")
                    with p_col2:
                        items_summary = ", ".join([f"{it.nama_item} (x{it.qty})" for it in ext.items])
                        st.text_input("Rincian Items", value=items_summary, key=f"edit_items_{idx}")
                        ext.total_harga = st.number_input("Total Harga (Rp)", value=float(ext.total_harga), step=1000.0, key=f"edit_total_{idx}")
                    with p_col3:
                        ext.alamat_pengiriman = st.text_area("Alamat Pengiriman", value=ext.alamat_pengiriman, height=80, key=f"edit_alamat_{idx}")
                    st.divider()

            c_save1, c_save2 = st.columns([2.5, 5])
            with c_save1:
                if st.button(f"✅ Simpan Semua Pesanan ({len(orders_to_show)}) ke Excel", use_container_width=True, type="primary"):
                    saved_count = 0
                    for ord_item in orders_to_show:
                        if storage.append_order(tenant.tenant_id, ord_item):
                            saved_count += 1
                    if saved_count > 0:
                        st.success(f"🎉 Berhasil menyimpan {saved_count} pesanan ke database Excel!")
                        st.session_state.extracted_orders = []
                        st.rerun()
                    else:
                        st.error("Gagal menyimpan pesanan.")
            with c_save2:
                if st.button("Batal / Reset", use_container_width=False):
                    st.session_state.extracted_orders = []
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------ SECTION 2: METRICS & TABLE ------------------ #
    df = storage.read_orders_dataframe(tenant.tenant_id)

    if df.empty:
        st.info("👋 Belum ada data pesanan tersimpan. Silakan gunakan kotak input di atas untuk memasukkan pesanan pertama Anda!")
        return

    # Filter Logic
    filtered_df = df.copy()
    if status_filter != "Semua Status" and "Status Pesanan" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Status Pesanan"] == status_filter]

    if search_query:
        mask = (
            filtered_df["Nama Pemesan"].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df["No HP"].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df["Alamat Pengiriman"].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df["ID Pesanan"].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # Metrics
    total_pesanan = len(df)
    total_omset = df["Total Harga"].sum() if "Total Harga" in df.columns else 0
    pesanan_baru = len(df[df["Status Pesanan"] == "Baru"]) if "Status Pesanan" in df.columns else 0
    total_items = df["Total Qty"].sum() if "Total Qty" in df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Pesanan</div><div class='kpi-value'>{total_pesanan}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Estimasi Omset</div><div class='kpi-value'>Rp {total_omset:,.0f}</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Pesanan Baru</div><div class='kpi-value'>{pesanan_baru}</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Item Terjual</div><div class='kpi-value'>{total_items}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Orders Table
    st.subheader(f"📋 Tabel Rekap Pesanan ({len(filtered_df)} Data)")
    display_cols = [
        "ID Pesanan", "Tanggal Masuk", "Nama Pemesan", "No HP",
        "Daftar Item", "Total Qty", "Total Harga", "Status Pesanan", "Alamat Pengiriman"
    ]
    available_cols = [c for c in display_cols if c in filtered_df.columns]

    st.dataframe(
        filtered_df[available_cols],
        use_container_width=True,
        hide_index=True
    )

    # Update Status Section
    with st.expander("✏️ **Ubah Status Pesanan**"):
        col_id, col_status, col_btn = st.columns([2, 2, 1])
        with col_id:
            order_ids = filtered_df["ID Pesanan"].tolist() if "ID Pesanan" in filtered_df.columns else []
            selected_order = st.selectbox("Pilih ID Pesanan", order_ids) if order_ids else None
        with col_status:
            new_status = st.selectbox("Pilih Status Baru", ["Baru", "Diproses", "Dikirim", "Selesai", "Dibatalkan"])
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Update Status 🔄", use_container_width=True) and selected_order:
                updated = storage.update_order_status(tenant.tenant_id, selected_order, new_status)
                if updated:
                    st.success(f"Status pesanan `{selected_order}` berhasil diubah ke **{new_status}**!")
                    st.rerun()

    # Download Excel Action
    st.markdown("<br>", unsafe_allow_html=True)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_data = excel_buffer.getvalue()

    st.download_button(
        label="📥 Download File Database Excel (.xlsx)",
        data=excel_data,
        file_name=f"rekap_po_{tenant.tenant_id}_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ------------------ App Router ------------------ #
if not st.session_state.authenticated:
    auth_view()
else:
    main_dashboard()
