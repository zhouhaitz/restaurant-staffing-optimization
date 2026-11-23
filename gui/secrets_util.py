"""Look up API keys without ever hard-coding them.

Order: process environment (incl. a local, git-ignored .env) -> Streamlit secrets
(.streamlit/secrets.toml locally, or Settings > Secrets on Streamlit Community Cloud).
"""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def get_openai_key() -> Optional[str]:
    """Return OPENAI_API_KEY from the environment or st.secrets, or None if unset."""
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("OPENAI_API_KEY")  # raises if no secrets file exists
    except Exception:
        return None
