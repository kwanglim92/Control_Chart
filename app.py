"""
Control Chart Streamlit Web Application
장비별 Performance 데이터 관리도 비교 분석 프로그램 (DB 연동 버전)
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, date

# DB 모듈 임포트
import database as db

from utils import (
    load_data, clean_data, normalize_check_items_column,
    add_date_columns, build_display_map, normalize_key,
    calculate_stats
)
import charts  # 전체 모듈 임포트 (charts.plot_sunburst_chart 사용 위함)
from charts import create_control_chart, create_individual_chart

# 페이지 설정
st.set_page_config(
    page_title="Control Chart 분석 (DB)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 초기화
if 'db_initialized' not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

# 세션 상태 초기화
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'analysis_triggered' not in st.session_state:
    st.session_state.analysis_triggered = False


def sync_data_from_excel():
    """로컬 Excel 파일에서 데이터를 읽어 DB에 저장"""
    data_file_path = os.path.join(os.path.dirname(__file__), 'data.xlsx')
    if not os.path.exists(data_file_path):
        st.error("⚠️ 'data.xlsx' 파일을 찾을 수 없습니다.")
        return

    try:
        df = pd.read_excel(data_file_path)
        df = clean_data(df)
        df = normalize_check_items_column(df)
        
        # 기존 데이터 삭제 후 새로 입력 (또는 append 선택 가능)
        # 여기서는 중복 방지를 위해 전체 삭제 후 재입력 방식을 사용하거나,
        # 실무에서는 날짜 기준으로 append 하는 것이 좋음.
        # 편의상 '전체 덮어쓰기' 모드로 구현 (사용자 선택 가능하게 할 수도 있음)
        
        # 기존 데이터 및 테이블 초기화 (스키마 변경 대응)
        db.recreate_tables()
        counts = db.import_data_from_df(df)
        st.success(f"✅ 동기화 완료! 장비 {counts['equipments']}대, 측정값 {counts['measurements']}건 저장됨.")
        
    except Exception as e:
        st.error(f"❌ 동기화 실패: {str(e)}")

def render_explorer_tab():
    """Tab 1: Equipment Explorer"""
    st.header("📊 장비 탐색 (Equipment Explorer)")
    
    # 1. Dashboard Metrics
    stats = db.get_equipment_stats()
    col1, col2 = st.columns(2)
    col1.metric(label="등록된 장비 수", value=f"{stats['total_equipments']:,} 대")
    col2.metric(label="측정 데이터 수", value=f"{stats['total_measurements']:,} 건")
    
    st.divider()
    
    # 2. Dynamic Sunburst & List
    df_equip = db.get_all_equipments()
    
    if not df_equip.empty:
        # Hierarchy Selection
        st.markdown("##### 📊 분석 기준 설정")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            time_unit = st.selectbox(
                "📅 시간 단위 (최상위 분류)",
                options=['None', 'Year', 'YearQuarter', 'YearMonth'],
                format_func=lambda x: {'None': '선택 안함', 'Year': '연도별', 'YearQuarter': '분기별', 'YearMonth': '월별'}.get(x, x),
                index=0
            )
            
        with c2:
            cat_options = ['ri', 'model', 'head_type', 'xy_scanner', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
            cat_labels = {
                'ri': 'R/I (용도)', 'model': 'Model', 
                'head_type': 'Head Type', 'xy_scanner': 'XY Scanner',
                'mod_vit': 'MOD/VIT', 'sliding_stage': 'Sliding Stage',
                'sample_chuck': 'Sample Chuck', 'ae': 'AE'
            }
            selected_cats = st.multiselect(
                "📂 상세 분류 (순서대로 하위 계층이 됩니다)",
                options=cat_options,
                default=['ri', 'model'],
                format_func=lambda x: cat_labels.get(x, x)
            )
            
        # Construct Path
        final_path = []
        if time_unit != 'None':
            final_path.append(time_unit)
        final_path.extend(selected_cats)
        
        if final_path:
            fig_sunburst = charts.plot_sunburst_chart(df_equip, path=final_path)
            st.plotly_chart(fig_sunburst, use_container_width=True)
            
            # List & Card View
            st.markdown("### 📋 장비 목록 및 상세 정보")
            col_list, col_detail = st.columns([1, 1])
            
            with col_list:
                st.caption("아래 목록에서 장비를 선택하면 상세 정보를 볼 수 있습니다.")
                df_display = df_equip.sort_values('date', ascending=False)
                
                selected_equip_name = st.selectbox(
                    "장비 선택",
                    options=df_display['equipment_name'].unique(),
                    index=0
                )
                
                # Dynamic columns for display
                base_cols = ['equipment_name', 'model', 'date']
                extra_cols = [c for c in final_path if c in df_display.columns and c not in base_cols]
                st.dataframe(df_display[base_cols + extra_cols], use_container_width=True, hide_index=True)
                
            with col_detail:
                if selected_equip_name:
                    equip_info = df_equip[df_equip['equipment_name'] == selected_equip_name].iloc[0]
                    with st.container(border=True):
                        st.markdown(f"#### 🏷️ {equip_info['equipment_name']}")
                        st.caption(f"Model: **{equip_info['model']}** | Date: {equip_info['date'].strftime('%Y-%m-%d')}")
                        st.divider()
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**기본 사양**")
                            st.write(f"- R/I: {equip_info['ri']}")
                            st.write(f"- Head: {equip_info['head_type']}")
                            st.write(f"- Scanner: {equip_info['xy_scanner']}")
                        with c2:
                            st.markdown("**옵션 사양**")
                            st.write(f"- Stage: {equip_info['sliding_stage']}")
                            st.write(f"- Chuck: {equip_info['sample_chuck']}")
                            st.write(f"- AE: {equip_info['ae']}")
                            st.write(f"- Mod/Vit: {equip_info['mod_vit']}")
    else:
        st.info("데이터가 없습니다. 데이터 관리 탭에서 동기화를 실행해주세요.")

def render_analysis_tab():
    """Tab 2: Quality Analysis"""
    st.header("📈 품질 분석 (Quality Analysis)")
    
    if not st.session_state.analysis_triggered:
        st.info("👈 왼쪽 사이드바에서 필터를 선택하고 **'🚀 분석 시작'** 버튼을 눌러주세요.")
        return

    display_df = st.session_state.filtered_data
    
    if display_df is None or display_df.empty:
        st.warning("조건에 맞는 데이터가 없습니다.")
        return
        
    # --- Local Date Range Filter ---
    st.markdown("##### 📅 분석 기간 설정")
    
    min_date = display_df['종료일'].min().date()
    max_date = display_df['종료일'].max().date()
    
    # Ensure min <= max
    if min_date > max_date:
        min_date, max_date = max_date, min_date
        
    c_filter1, c_filter2 = st.columns([1, 3])
    with c_filter1:
        date_range = st.date_input(
            "기간 선택",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key='analysis_date_range'
        )
        
    # Apply Filter
    if len(date_range) == 2:
        start_d, end_d = date_range
        mask = (display_df['종료일'].dt.date >= start_d) & (display_df['종료일'].dt.date <= end_d)
        display_df = display_df.loc[mask]
        
    if display_df.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return
        
    st.caption(f"선택 기간: {date_range[0]} ~ {date_range[1] if len(date_range)>1 else date_range[0]} | 데이터 수: {len(display_df)}건")
    st.divider()
    # -------------------------------
        
    # Tabs for Analysis Sub-views
    tab1, tab2, tab3, tab4 = st.tabs(["종합 차트", "개별 차트", "통계 요약", "데이터"])
    
    # Simplified Grouping Options (Time-based only)
    # 'None' means no grouping (single series), effectively grouping by nothing or just showing all data.
    # However, create_control_chart expects a column to group by.
    # If 'None' is selected, we can create a dummy column 'All' or group by 'Check Items' if multiple.
    # Let's map 'None' to a dummy column for now, or handle it logic.
    
    group_options = ['None', '연도', '분기', '월']
    
    with tab1:
        st.subheader("종합 관리도 (Combined Control Chart)")
        
        c1, c2 = st.columns([1, 3])
        with c1:
            group_by_selection = st.selectbox("그룹화 기준 (시간)", group_options, index=0, key='combined_group')
            show_violations = st.checkbox("Rule of Seven / Trend 표시", value=True, key='combined_viol')
            
        # Logic to determine actual group column
        if group_by_selection == 'None':
            # If multiple check items are selected, we might want to group by Check Items implicitly?
            # Or just show everything as one series.
            # Let's default to 'Check Items' if multiple, else 'All'.
            if display_df['Check Items'].nunique() > 1:
                group_col = 'Check Items'
                st.caption("ℹ️ 'None' 선택 시, 항목(Check Items)별로 구분됩니다.")
            else:
                # Create a dummy column for single group
                display_df['All'] = 'All Data'
                group_col = 'All'
        elif group_by_selection == '연도':
            group_col = '연도'
        elif group_by_selection == '분기':
            # Ensure Quarter column exists (it should from add_date_columns)
            if '분기' not in display_df.columns:
                 display_df['분기'] = display_df['종료일'].dt.to_period('Q').astype(str)
            group_col = '분기' # Or 'YearQuarter' if available? add_date_columns makes '분기' as 1,2,3,4. 
            # Better to use Year-Quarter for uniqueness if spanning multiple years.
            # Let's check what add_date_columns does. It adds '연도', '분기', '월'.
            # If we group by just '분기' (1-4), it mixes years. We probably want 'Year-Quarter'.
            # Let's construct a composite key on the fly if needed.
            display_df['YearQuarter'] = display_df['연도'] + '-' + display_df['분기'] + 'Q'
            group_col = 'YearQuarter'
        elif group_by_selection == '월':
            display_df['YearMonth'] = display_df['연도'] + '-' + display_df['월']
            group_col = 'YearMonth'
            
        # 이중 축 로직 (Check Items가 2개일 때)
        use_dual_axis = False
        if group_col == 'Check Items' and display_df['Check Items'].nunique() == 2:
            use_dual_axis = st.checkbox("이중 Y축 사용", value=True, key='combined_dual')
            
        try:
            fig_combined = create_control_chart(
                display_df, 
                group_col=group_col,
                equipment_col='장비명', # Pass equipment column for hover
                show_violations=show_violations,
                use_dual_axis=use_dual_axis
            )
            st.plotly_chart(fig_combined, use_container_width=True)
        except Exception as e:
            st.error(f"차트 생성 오류: {e}")
        
    with tab2:
        st.subheader("개별 관리도 (Individual Charts)")
        
        c1, c2 = st.columns([1, 3])
        with c1:
            group_by_ind_sel = st.selectbox("그룹화 기준 (개별)", group_options, index=0, key='ind_group')
            
        # Logic for individual charts grouping
        if group_by_ind_sel == 'None':
            if display_df['Check Items'].nunique() > 1:
                group_col_ind = 'Check Items'
            else:
                display_df['All'] = 'All Data'
                group_col_ind = 'All'
        elif group_by_ind_sel == '연도':
            group_col_ind = '연도'
        elif group_by_ind_sel == '분기':
            display_df['YearQuarter'] = display_df['연도'] + '-' + display_df['분기'] + 'Q'
            group_col_ind = 'YearQuarter'
        elif group_by_ind_sel == '월':
            display_df['YearMonth'] = display_df['연도'] + '-' + display_df['월']
            group_col_ind = 'YearMonth'
        
        # 그룹별 반복
        unique_groups = display_df[group_col_ind].unique()
        # Sort groups naturally
        try:
            unique_groups = sorted(unique_groups)
        except:
            pass
            
        if len(unique_groups) > 20:
            st.warning(f"⚠️ 그룹 수가 너무 많습니다 ({len(unique_groups)}개). 상위 20개만 표시합니다.")
            unique_groups = unique_groups[:20]
            
        for name in unique_groups:
            group_data = display_df[display_df[group_col_ind] == name]
            if group_data.empty: continue
            
            st.markdown(f"**{name}**")
            try:
                fig_individual = create_individual_chart(
                    group_data, 
                    group_name=str(name),
                    equipment_col='장비명',
                    show_violations=True
                )
                st.plotly_chart(fig_individual, use_container_width=True)
            except Exception as e:
                st.error(f"차트 생성 실패 ({name}): {e}")
        
    with tab3:
        st.subheader("통계 요약 (Statistics)")
        
        # Use same logic for stats? Or allow different?
        # Let's use the same options for consistency.
        c1, c2 = st.columns([1, 3])
        with c1:
            group_by_stat_sel = st.selectbox("그룹화 기준 (통계)", group_options, index=0, key='stat_group')
            
        if group_by_stat_sel == 'None':
            if display_df['Check Items'].nunique() > 1:
                group_col_stat = 'Check Items'
            else:
                display_df['All'] = 'All Data'
                group_col_stat = 'All'
        elif group_by_stat_sel == '연도':
            group_col_stat = '연도'
        elif group_by_stat_sel == '분기':
            display_df['YearQuarter'] = display_df['연도'] + '-' + display_df['분기'] + 'Q'
            group_col_stat = 'YearQuarter'
        elif group_by_stat_sel == '월':
            display_df['YearMonth'] = display_df['연도'] + '-' + display_df['월']
            group_col_stat = 'YearMonth'
            
        stats_list = []
        for name, group in display_df.groupby(group_col_stat):
            s = calculate_stats(group['Value'].values)
            stats_list.append({
                '그룹': name,
                'Count': s['count'],
                'AVG': round(s['avg'], 3),
                'STD': round(s['std'], 3),
                'UCL': round(s['ucl'], 3),
                'LCL': round(s['lcl'], 3),
                'Min': round(s['min'], 3),
                'Max': round(s['max'], 3)
            })
            
        if stats_list:
            st.dataframe(pd.DataFrame(stats_list), use_container_width=True)
        else:
            st.info("통계 데이터가 없습니다.")
        
    with tab4:
        st.subheader("필터링된 원본 데이터")
        st.dataframe(display_df, use_container_width=True)

def render_data_tab():
    """Tab 3: Data Management"""
    st.header("💾 데이터 관리 (Data Management)")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📂 Excel 데이터 동기화")
        st.info("로컬 폴더의 'data.xlsx' 내용을 DB로 가져옵니다.")
        if st.button("🔄 DB 동기화 실행", key='sync_btn_tab', use_container_width=True):
            with st.spinner("데이터 동기화 중..."):
                sync_data_from_excel()
                st.rerun()
                
    with c2:
        st.subheader("📝 데이터 직접 입력")
        with st.form("data_entry_form_tab"):
            input_date = st.date_input("날짜", value=date.today())
            input_model = st.text_input("Model")
            input_item = st.text_input("Check Item")
            input_value = st.number_input("Value", step=0.01)
            input_equip = st.text_input("장비명")
            input_ri = st.selectbox("R/I", ["", "R", "I"])
            
            if st.form_submit_button("💾 저장"):
                if not input_model or not input_item:
                    st.error("Model과 Check Item은 필수입니다.")
                else:
                    record = {
                        'date': input_date.strftime('%Y-%m-%d'),
                        'model': input_model,
                        'check_item': input_item,
                        'value': input_value,
                        'equipment_name': input_equip,
                        'ri': input_ri
                    }
                    try:
                        db.insert_single_record(record)
                        st.success("저장되었습니다!")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")


def main():
    st.title("📊 Control Chart 분석 시스템")
    
    # Sidebar (Analysis Filters)
    with st.sidebar:
        st.header("🔍 분석 필터")
        models = db.get_unique_values('model')
        sel_models = st.multiselect("Model", models)
        
        items = db.get_unique_values('check_item')
        sel_items = st.multiselect("Check Items", items, help="최대 2개 권장")
        
        ris = db.get_unique_values('ri')
        sel_ris = st.multiselect("R/I", ris)
        
        use_date = st.checkbox("날짜 범위 적용")
        date_range = []
        if use_date:
            d_start = st.date_input("시작일", value=date(2024, 1, 1))
            d_end = st.date_input("종료일", value=date.today())
            date_range = [d_start, d_end]
            
        st.markdown("---")
        if st.button("🚀 분석 시작", type="primary", use_container_width=True):
            st.session_state.analysis_triggered = True
            filters = {}
            if sel_models: filters['model'] = sel_models
            if sel_items: filters['check_item'] = sel_items
            if sel_ris: filters['ri'] = sel_ris
            if use_date: filters['date_range'] = date_range
            
            with st.spinner("데이터 조회 및 분석 중..."):
                df = db.fetch_filtered_data(filters)
                if not df.empty:
                    df = add_date_columns(df)
                st.session_state.filtered_data = df
    
    # Main Tabs
    tab_explorer, tab_analysis, tab_data = st.tabs([
        "📊 장비 탐색", "📈 품질 분석", "💾 데이터 관리"
    ])
    
    with tab_explorer:
        render_explorer_tab()
        
    with tab_analysis:
        render_analysis_tab()
        
    with tab_data:
        render_data_tab()

if __name__ == "__main__":
    main()
