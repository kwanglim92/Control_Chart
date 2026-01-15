"""
전체 데이터 조회 탭
Data Explorer Tab

기존 app.py의 render_data_explorer 함수를 래핑
"""

import streamlit as st


def render_data_explorer_tab():
    """전체 데이터 조회 탭 렌더링 - app.py의 기존 함수를 import하여 사용"""
    #  순환 import 방지를 위해 지연 import 사용
    from app import render_data_explorer
    render_data_explorer()
