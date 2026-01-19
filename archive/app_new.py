"""
Control Chart Streamlit Web Application
장비별 Performance 데이터 관리도 비교 분석 프로그램 (DB 연동 버전)
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime, date

# DB 모듈 임포트
import database as db

from utils import (
    load_data, clean_data, normalize_check_items_column,
    add_date_columns, build_display_map, normalize_key,
    calculate_stats, RESEARCH_MODELS, INDUSTRIAL_MODELS
)
import charts
from charts import create_control_chart, create_individual_chart

# 페이지 설정
st.set_page_config(
    page_title="Control Chart Viewer v2.0",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 초기화
if 'db_initialized' not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

# --- Helper Functions ---

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["admin_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "관리자 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "관리자 비밀번호를 입력하세요", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 비밀번호가 틀렸습니다.")
        return False
    else:
        # Password correct.
        return True

def process_uploaded_file(uploaded_file):
    """Process uploaded Excel file and insert into DB as pending."""
    try:
        # Read Excel
        # Assuming the Excel has 'Equipments' and 'Measurements' sheets or similar structure?
        # Or is it a single flat file?
        # Based on previous context, it seems to be a flat file that needs parsing.
        # Let's assume it's the standard format we've been working with.
        
        df = pd.read_excel(uploaded_file)
        
        # Basic Validation
        required_cols = ['SID', 'Check Items', 'Value', 'Model'] # Minimal set
        missing = [c for c in required_cols if c not in df.columns]
        
        # If flat file, we need to separate into Equip/Meas
        # Using existing cleaning logic
        df = clean_data(df)
        df = normalize_check_items_column(df)
        
        # Split into Equipments and Measurements for DB insertion
        # This logic mimics what was in `import_data_from_df` but we need to pass it to `insert_equipment_from_excel`
        
        # Prepare Equipments DataFrame (Unique per SID)
        # We need to extract equipment level columns
        equip_cols = ['SID', '장비명', '종료일', 'R/I', 'Model', 'XY Scanner', 'Head Type', 'MOD/VIT', 'Sliding Stage', 'Sample Chuck', 'AE']
        # Filter only existing columns
        existing_equip_cols = [c for c in equip_cols if c in df.columns]
        
        df_equip = df[existing_equip_cols].drop_duplicates(subset=['SID'])
        
        # Prepare Measurements DataFrame
        meas_cols = ['SID', 'Check Items', 'Value', '장비명'] # 장비명 for fallback
        existing_meas_cols = [c for c in meas_cols if c in df.columns]
        df_meas = df[existing_meas_cols]
        
        # Insert into DB
        counts = db.insert_equipment_from_excel(df_equip, df_meas)
        return True, counts
        
    except Exception as e:
        return False, str(e)


# --- Tab Renderers ---

def render_dashboard_tab():
    """Tab 1: Dashboard (Visualizations)"""
    st.header("📊 Control Chart Dashboard")
    
    # 1. Dashboard Metrics
    stats = db.get_equipment_stats()
    col1, col2 = st.columns(2)
    col1.metric(label="등록된 장비 수 (승인됨)", value=f"{stats['total_equipments']:,} 대")
    col2.metric(label="측정 데이터 수 (승인됨)", value=f"{stats['total_measurements']:,} 건")
    
    st.divider()
    
    # 2. Explorer & Analysis (Combined View)
    # Reusing existing logic but simplified
    
    df_equip = db.get_all_equipments()
    
    if df_equip.empty:
        st.info("표시할 데이터가 없습니다. 데이터를 업로드하고 승인을 기다려주세요.")
        return

    # --- 2.1 Split Layout: Research vs Industrial ---
    st.subheader("장비 탐색")
    col_research, col_industrial = st.columns(2)
    
    # Helper to render column
    def render_ri_column(col, title, ri_type, color_seq):
        with col:
            st.markdown(f"### {title}")
            df_sub = df_equip[df_equip['ri'] == ri_type]
            st.metric(f"등록 장비 수", f"{len(df_sub):,} 대")
            
            if df_sub.empty:
                st.info("데이터가 없습니다.")
                return None
            
            # Bar Chart
            fig = charts.create_model_bar_chart(df_sub, color_seq)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            # List
            st.caption("📋 최신 등록 장비 (상위 10개)")
            df_list = df_sub.sort_values('date', ascending=False).head(10)
            st.dataframe(
                df_list[['sid', 'equipment_name', 'model', 'date']],
                use_container_width=True,
                hide_index=True
            )

    render_ri_column(col_research, "Research (연구용)", "Research", px.colors.qualitative.Bold)
    render_ri_column(col_industrial, "Industrial (산업용)", "Industrial", px.colors.qualitative.Pastel)
    
    st.divider()
    
    # --- 2.2 Control Chart Analysis ---
    st.subheader("📈 Control Chart 분석")
    
    # Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        models = sorted(df_equip['model'].unique())
        sel_model = st.selectbox("모델 선택", models)
    
    # Get Check Items for selected model
    # We need to query measurements for this model
    # For simplicity, let's get all check items first (optimization possible later)
    # Or better, fetch distinct check items for this model from DB
    # But we don't have a direct function for that yet, let's use what we have
    
    # Fetch data for this model to get check items
    filters = {'model': [sel_model]}
    df_analysis = db.fetch_filtered_data(filters)
    
    if df_analysis.empty:
        st.warning("선택한 모델에 대한 측정 데이터가 없습니다.")
    else:
        check_items = sorted(df_analysis['Check Items'].unique())
        with c2:
            sel_item = st.selectbox("측정 항목 선택", check_items)
            
        # Draw Chart
        df_chart = df_analysis[df_analysis['Check Items'] == sel_item]
        
        # Get Specs
        specs = db.get_spec(sel_model, sel_item)
        
        # Chart
        fig = create_control_chart(df_chart, sel_model, sel_item, specs)
        st.plotly_chart(fig, use_container_width=True)


def render_upload_tab():
    """Tab 2: Data Upload (Engineer)"""
    st.header("📤 데이터 업로드")
    st.markdown("""
    **현장 엔지니어 전용**  
    작업 완료 후 엑셀 파일을 이곳에 업로드해주세요.  
    업로드된 데이터는 **관리자 승인 후** 대시보드에 반영됩니다.
    """)
    
    uploaded_file = st.file_uploader("엑셀 파일 선택 (.xlsx)", type=['xlsx'])
    
    if uploaded_file is not None:
        if st.button("데이터 제출하기", type="primary"):
            with st.spinner("데이터 분석 및 저장 중..."):
                success, result = process_uploaded_file(uploaded_file)
                
                if success:
                    st.success(f"""
                    ✅ **제출 완료!**
                    
                    - 장비: {result['equipments']}대
                    - 측정값: {result['measurements']}건
                    
                    관리자 승인 대기 목록에 추가되었습니다.
                    """)
                else:
                    st.error(f"❌ 처리 실패: {result}")

def render_admin_tab():
    """Tab 3: Admin (Manager)"""
    st.header("🔒 관리자 모드")
    
    if not check_password():
        return
    
    st.success("로그인 성공! 관리자 권한으로 접속되었습니다.")
    
    # Pending List
    st.subheader("⏳ 승인 대기 목록")
    
    df_pending = db.get_pending_equipments()
    
    if df_pending.empty:
        st.info("현재 대기 중인 데이터가 없습니다.")
    else:
        st.markdown(f"총 **{len(df_pending)}**건의 대기 데이터가 있습니다.")
        
        for idx, row in df_pending.iterrows():
            with st.expander(f"[{row['uploaded_at']}] {row['equipment_name']} ({row['sid']}) - {row['model']}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.write(f"**SID**: {row['sid']}")
                    st.write(f"**Date**: {row['date']}")
                    st.write(f"**R/I**: {row['ri']}")
                with c2:
                    if st.button("승인 (Approve)", key=f"btn_app_{row['id']}", type="primary"):
                        db.approve_equipment(row['id'])
                        st.success("승인되었습니다.")
                        st.rerun()
                with c3:
                    if st.button("반려/삭제 (Reject)", key=f"btn_rej_{row['id']}", type="secondary"):
                        db.delete_equipment(row['id'])
                        st.warning("삭제되었습니다.")
                        st.rerun()


# --- Main App ---

def main():
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📤 Data Upload", "🔒 Admin"])
    
    with tab1:
        render_dashboard_tab()
    
    with tab2:
        render_upload_tab()
        
    with tab3:
        render_admin_tab()

if __name__ == "__main__":
    main()
