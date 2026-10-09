import os
import io
import json
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from config import config
from core.models import TenantProfile, OrderRecord

EXCEL_COLUMNS = [
    "ID Pesanan",
    "Tanggal Masuk",
    "Nama Pemesan",
    "No HP",
    "Alamat Pengiriman",
    "Daftar Item",
    "Total Qty",
    "Total Harga",
    "Metode Pembayaran",
    "Status Pesanan",
    "Catatan",
    "Chat Asli"
]

class StorageEngine:
    """Multi-tenant Storage Engine supporting GitHub API with Local Filesystem Fallback."""

    def __init__(self, local_root: Optional[str] = None, use_local_fallback: bool = False):
        self.use_local = use_local_fallback or not (config.GITHUB_TOKEN and config.GITHUB_REPO)
        self.local_root = Path(local_root or (Path(__file__).resolve().parent.parent / "data_storage"))
        if self.use_local:
            self.local_root.mkdir(parents=True, exist_ok=True)
            (self.local_root / "tenants").mkdir(parents=True, exist_ok=True)
        self.github_repo = None
        if not self.use_local:
            try:
                from github import Github
                g = Github(config.GITHUB_TOKEN)
                self.github_repo = g.get_repo(config.GITHUB_REPO)
            except Exception:
                self.use_local = True

    # ------------------ Tenants Index Management ------------------ #

    def _get_tenants_index(self) -> Dict[str, Any]:
        """Fetch the master tenants index json."""
        if self.use_local:
            index_file = self.local_root / "tenants.json"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        else:
            try:
                content_file = self.github_repo.get_contents("tenants.json", ref=config.GITHUB_BRANCH)
                return json.loads(content_file.decoded_content.decode("utf-8"))
            except Exception:
                return {}

    def _save_tenants_index(self, data: Dict[str, Any]):
        """Save the master tenants index json."""
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if self.use_local:
            index_file = self.local_root / "tenants.json"
            with open(index_file, "w", encoding="utf-8") as f:
                f.write(json_str)
        else:
            try:
                contents = self.github_repo.get_contents("tenants.json", ref=config.GITHUB_BRANCH)
                self.github_repo.update_file(
                    "tenants.json",
                    "Update tenants master index",
                    json_str,
                    contents.sha,
                    branch=config.GITHUB_BRANCH
                )
            except Exception:
                self.github_repo.create_file(
                    "tenants.json",
                    "Initialize tenants master index",
                    json_str,
                    branch=config.GITHUB_BRANCH
                )

    # ------------------ Tenant Registration & Lookup ------------------ #

    def register_tenant(self, tenant: TenantProfile) -> bool:
        """Register a new tenant, create directory and initialize rekap_pesanan.xlsx."""
        index = self._get_tenants_index()
        
        # Check uniqueness of username and telegram ID
        for t_id, meta in index.items():
            if meta.get("telegram_user_id") == tenant.telegram_user_id:
                # Update existing
                pass

        index[tenant.tenant_id] = {
            "tenant_id": tenant.tenant_id,
            "nama_toko": tenant.nama_toko,
            "telegram_user_id": tenant.telegram_user_id,
            "username": tenant.username,
            "created_at": tenant.created_at
        }
        self._save_tenants_index(index)

        # Create tenant config
        config_json = tenant.model_dump_json(indent=2)
        config_path = f"tenants/{tenant.tenant_id}/config.json"
        excel_path = f"tenants/{tenant.tenant_id}/rekap_pesanan.xlsx"

        # Initialize empty DataFrame for Excel
        empty_df = pd.DataFrame(columns=EXCEL_COLUMNS)
        excel_buffer = io.BytesIO()
        empty_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_bytes = excel_buffer.getvalue()

        if self.use_local:
            tenant_dir = self.local_root / "tenants" / tenant.tenant_id
            tenant_dir.mkdir(parents=True, exist_ok=True)
            with open(tenant_dir / "config.json", "w", encoding="utf-8") as f:
                f.write(config_json)
            with open(tenant_dir / "rekap_pesanan.xlsx", "wb") as f:
                f.write(excel_bytes)
        else:
            # Commit config.json to GitHub
            try:
                c = self.github_repo.get_contents(config_path, ref=config.GITHUB_BRANCH)
                self.github_repo.update_file(config_path, f"Update config for {tenant.tenant_id}", config_json, c.sha, branch=config.GITHUB_BRANCH)
            except Exception:
                self.github_repo.create_file(config_path, f"Init config for {tenant.tenant_id}", config_json, branch=config.GITHUB_BRANCH)

            # Commit rekap_pesanan.xlsx to GitHub
            try:
                e = self.github_repo.get_contents(excel_path, ref=config.GITHUB_BRANCH)
                self.github_repo.update_file(excel_path, f"Update excel for {tenant.tenant_id}", excel_bytes, e.sha, branch=config.GITHUB_BRANCH)
            except Exception:
                self.github_repo.create_file(excel_path, f"Init excel for {tenant.tenant_id}", excel_bytes, branch=config.GITHUB_BRANCH)

        return True

    def get_tenant_by_telegram_id(self, telegram_user_id: int) -> Optional[TenantProfile]:
        """Find a tenant by their Telegram User ID."""
        index = self._get_tenants_index()
        for tenant_id, meta in index.items():
            if meta.get("telegram_user_id") == telegram_user_id:
                return self.get_tenant_profile(tenant_id)
        return None

    def get_tenant_by_username(self, username: str) -> Optional[TenantProfile]:
        """Find a tenant by their web dashboard username."""
        index = self._get_tenants_index()
        for tenant_id, meta in index.items():
            if meta.get("username") == username:
                return self.get_tenant_profile(tenant_id)
        return None

    def get_tenant_profile(self, tenant_id: str) -> Optional[TenantProfile]:
        """Get full tenant profile from config.json."""
        config_path = f"tenants/{tenant_id}/config.json"
        if self.use_local:
            target = self.local_root / "tenants" / tenant_id / "config.json"
            if target.exists():
                with open(target, "r", encoding="utf-8") as f:
                    return TenantProfile(**json.load(f))
            return None
        else:
            try:
                c = self.github_repo.get_contents(config_path, ref=config.GITHUB_BRANCH)
                data = json.loads(c.decoded_content.decode("utf-8"))
                return TenantProfile(**data)
            except Exception:
                return None

    # ------------------ Excel Database Operations ------------------ #

    def read_orders_dataframe(self, tenant_id: str) -> pd.DataFrame:
        """Read tenant's rekap_pesanan.xlsx into a Pandas DataFrame."""
        excel_path = f"tenants/{tenant_id}/rekap_pesanan.xlsx"
        if self.use_local:
            target = self.local_root / "tenants" / tenant_id / "rekap_pesanan.xlsx"
            if target.exists():
                return pd.read_excel(target, engine="openpyxl")
            return pd.DataFrame(columns=EXCEL_COLUMNS)
        else:
            try:
                c = self.github_repo.get_contents(excel_path, ref=config.GITHUB_BRANCH)
                return pd.read_excel(io.BytesIO(c.decoded_content), engine="openpyxl")
            except Exception:
                return pd.DataFrame(columns=EXCEL_COLUMNS)

    def append_order(self, tenant_id: str, order: OrderRecord) -> bool:
        """Append a new order row to tenant's rekap_pesanan.xlsx."""
        df = self.read_orders_dataframe(tenant_id)

        # Format items string (e.g. "Risol Mayo x5, Pastel x3")
        items_summary = ", ".join([f"{it.nama_item} (x{it.qty})" for it in order.items])
        total_qty = sum(it.qty for it in order.items)

        new_row = {
            "ID Pesanan": order.id_pesanan,
            "Tanggal Masuk": order.tanggal_masuk,
            "Nama Pemesan": order.nama_pemesan,
            "No HP": order.no_hp,
            "Alamat Pengiriman": order.alamat_pengiriman,
            "Daftar Item": items_summary,
            "Total Qty": total_qty,
            "Total Harga": order.total_harga,
            "Metode Pembayaran": order.metode_pembayaran,
            "Status Pesanan": order.status_pesanan,
            "Catatan": ", ".join([it.catatan for it in order.items if it.catatan]),
            "Chat Asli": order.raw_chat
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Save back to Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_bytes = excel_buffer.getvalue()

        excel_path = f"tenants/{tenant_id}/rekap_pesanan.xlsx"
        if self.use_local:
            target = self.local_root / "tenants" / tenant_id / "rekap_pesanan.xlsx"
            with open(target, "wb") as f:
                f.write(excel_bytes)
            return True
        else:
            try:
                c = self.github_repo.get_contents(excel_path, ref=config.GITHUB_BRANCH)
                self.github_repo.update_file(
                    excel_path,
                    f"Append order {order.id_pesanan} for {tenant_id}",
                    excel_bytes,
                    c.sha,
                    branch=config.GITHUB_BRANCH
                )
                return True
            except Exception as e:
                return False

    def update_order_status(self, tenant_id: str, order_id: str, new_status: str) -> bool:
        """Update the status of an existing order."""
        df = self.read_orders_dataframe(tenant_id)
        if "ID Pesanan" not in df.columns:
            return False

        mask = df["ID Pesanan"] == order_id
        if not df[mask].empty:
            df.loc[mask, "Status Pesanan"] = new_status
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine="openpyxl")
            excel_bytes = excel_buffer.getvalue()

            excel_path = f"tenants/{tenant_id}/rekap_pesanan.xlsx"
            if self.use_local:
                target = self.local_root / "tenants" / tenant_id / "rekap_pesanan.xlsx"
                with open(target, "wb") as f:
                    f.write(excel_bytes)
                return True
            else:
                try:
                    c = self.github_repo.get_contents(excel_path, ref=config.GITHUB_BRANCH)
                    self.github_repo.update_file(
                        excel_path,
                        f"Update order {order_id} status to {new_status}",
                        excel_bytes,
                        c.sha,
                        branch=config.GITHUB_BRANCH
                    )
                    return True
                except Exception:
                    return False
        return False

# Global storage engine instance
storage = StorageEngine()
