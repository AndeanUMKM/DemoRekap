import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if exists
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def get_dynamic_secret(key: str, default: str = "") -> str:
    """Helper to dynamically read from streamlit secrets first, then os.getenv."""
    # 1. Try Streamlit secrets dynamically
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            # Check direct key
            if key in st.secrets:
                return str(st.secrets[key]).strip()
            # Check lowercase
            if key.lower() in st.secrets:
                return str(st.secrets[key.lower()]).strip()
            # Check uppercase
            if key.upper() in st.secrets:
                return str(st.secrets[key.upper()]).strip()
    except Exception:
        pass

    # 2. Try os.getenv (direct, lower, upper)
    val = os.getenv(key) or os.getenv(key.lower()) or os.getenv(key.upper())
    if val is not None:
        return str(val).strip()

    return default

class Config:
    @property
    def GEMINI_API_KEY(self) -> str:
        return (
            get_dynamic_secret("GEMINI_API_KEY") or
            get_dynamic_secret("GOOGLE_API_KEY") or
            get_dynamic_secret("gemini_api_key") or
            get_dynamic_secret("google_api_key")
        )

    @property
    def TELEGRAM_ONBOARDING_TOKEN(self) -> str:
        return get_dynamic_secret("TELEGRAM_ONBOARDING_TOKEN")

    @property
    def TELEGRAM_REKAP_TOKEN(self) -> str:
        return get_dynamic_secret("TELEGRAM_REKAP_TOKEN")

    @property
    def GITHUB_TOKEN(self) -> str:
        return get_dynamic_secret("GITHUB_TOKEN")

    @property
    def GITHUB_REPO(self) -> str:
        return get_dynamic_secret("GITHUB_REPO")

    @property
    def GITHUB_BRANCH(self) -> str:
        return get_dynamic_secret("GITHUB_BRANCH", "main")

    @property
    def SECRET_KEY(self) -> str:
        return get_dynamic_secret("SECRET_KEY", "dev-secret-key-12345")

    def validate(self, check_github: bool = False, check_ai: bool = False) -> dict:
        """Validate required configuration settings."""
        missing = []
        if check_ai and not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if check_github and not (self.GITHUB_TOKEN and self.GITHUB_REPO):
            missing.append("GITHUB_TOKEN or GITHUB_REPO")
        return {"valid": len(missing) == 0, "missing": missing}

config = Config()
