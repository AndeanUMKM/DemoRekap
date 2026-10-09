import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if exists
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def get_secret(key: str, default: str = "") -> str:
    """Helper to read from streamlit secrets first (Streamlit Cloud), then fallback to os.getenv."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)

class Config:
    TELEGRAM_ONBOARDING_TOKEN: str = get_secret("TELEGRAM_ONBOARDING_TOKEN", "")
    TELEGRAM_REKAP_TOKEN: str = get_secret("TELEGRAM_REKAP_TOKEN", "")
    GEMINI_API_KEY: str = get_secret("GEMINI_API_KEY", "")
    GITHUB_TOKEN: str = get_secret("GITHUB_TOKEN", "")
    GITHUB_REPO: str = get_secret("GITHUB_REPO", "")
    GITHUB_BRANCH: str = get_secret("GITHUB_BRANCH", "main")
    SECRET_KEY: str = get_secret("SECRET_KEY", "dev-secret-key-12345")

    @classmethod
    def validate(cls, check_github: bool = False, check_ai: bool = False) -> dict:
        """Validate required configuration settings."""
        missing = []
        if check_ai and not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if check_github and not (cls.GITHUB_TOKEN and cls.GITHUB_REPO):
            missing.append("GITHUB_TOKEN or GITHUB_REPO")
        return {"valid": len(missing) == 0, "missing": missing}

config = Config()
