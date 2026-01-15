"""
승인 대기 탭
Approval Queue Tab

기존 app.py의 render_approval_queue 함수를 래핑
"""

import streamlit as st


# app.py에서 import하여 재사용
# 나중에 완전히 분리할 수 있지만, 현재는 기존 코드를 그대로 활용
def render_approval_queue_tab():
    """승인 대기 탭 렌더링 - app.py의 기존 함수를 import하여 사용"""
    # 이 함수는 app.py에서 호출되므로 app.py의 render_approval_queue를 직접 호출
    # 순환 import 방지를 위해 지연 import 사용
    from app import render_approval_queue
    render_approval_queue()
