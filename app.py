"""
Entry point for the Law Agent Streamlit application.
Run with: streamlit run app.py
"""

import logging
import streamlit as st
from config.settings import LOG_LEVEL, LOG_FORMAT

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="Law Agent — EY AI Challenge",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("⚖️ Law Agent")
    st.caption("Navegação inteligente sobre legislação portuguesa")
    st.info("Aplicação em construção. Os módulos serão integrados progressivamente.")


if __name__ == "__main__":
    main()
