"""
Authentication Module
관리자 인증 모듈

관리자 로그인 및 비밀번호 검증 기능을 제공합니다.
"""

import streamlit as st
import os


def check_admin_password():
    """
    Returns `True` if the user had the correct password.
    Handles password verification logic.
    """
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if admin_password is None:
            try:
                admin_password = st.secrets["admin_password"]
            except (FileNotFoundError, KeyError):
                admin_password = "admin123"  # Default password
        
        if st.session_state["password"] == admin_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "관리자 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "관리자 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 비밀번호가 틀렸습니다.")
        return False
    else:
        return True


def render_admin_login():
    """
    Renders admin login UI and validates password.
    Returns True if admin is logged in.
    """
    st.header("🔒 관리자 모드 (Admin)")
    
    if not check_admin_password():
        return False
    
    st.success("로그인 성공! 관리자 권한으로 접속되었습니다.")
    return True
