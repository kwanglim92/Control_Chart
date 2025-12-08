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
import charts  # 전체 모듈 임포트 (charts.plot_sunburst_chart 사용 위함)
from charts import create_control_chart, create_individual_chart

# 페이지 설정
st.set_page_config(
    page_title="Control Chart Viewer v1.0",
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
    st.header("출고 장비 등록 현황")
    
    # 1. Dashboard Metrics
    stats = db.get_equipment_stats()
    col1, col2 = st.columns(2)
    col1.metric(label="등록된 장비 수", value=f"{stats['total_equipments']:,} 대")
    col2.metric(label="측정 데이터 수", value=f"{stats['total_measurements']:,} 건")
    
    st.divider()
    
    # 2. Dynamic Sunburst & List
    df_equip = db.get_all_equipments()
    
    if not df_equip.empty:
        # --- Global Date Filter ---
        st.markdown("### 📅 출고 기간 설정")
        min_date = df_equip['date'].min().date()
        max_date = df_equip['date'].max().date()
        if min_date > max_date: min_date, max_date = max_date, min_date
        
        # Initialize session state if not present
        if 'explorer_date_range' not in st.session_state:
            st.session_state['explorer_date_range'] = (min_date, max_date)
            
        c_date, c_btn = st.columns([5, 1])
        
        # Callback for reset
        def reset_date_range():
            st.session_state['explorer_date_range'] = (min_date, max_date)
            
        with c_btn:
            # Use on_click to handle state update before rerun
            st.button("🔄 초기화", use_container_width=True, help="전체 기간으로 초기화", on_click=reset_date_range)

        with c_date:
            date_range = st.date_input(
                "분석 기간 선택",
                # value argument removed to avoid warning with session_state
                min_value=min_date,
                max_value=max_date,
                key='explorer_date_range',
                label_visibility="collapsed"
            )
        
        # Apply Date Filter
        if len(date_range) == 2:
            start_d, end_d = date_range
            mask = (df_equip['date'].dt.date >= start_d) & (df_equip['date'].dt.date <= end_d)
            df_equip = df_equip.loc[mask]
            
        if df_equip.empty:
            st.warning("선택한 기간에 해당하는 장비가 없습니다.")
            return

        st.divider()
        
        # --- 1. Sunburst & Analysis Criteria ---
        with st.expander("상세 탐색", expanded=False):
            c1, c2 = st.columns([1, 2])
            with c1:
                time_unit = st.selectbox(
                    "시간 단위",
                    options=['None', 'Year', 'YearQuarter', 'YearMonth'],
                    format_func=lambda x: {'None': '선택 안함', 'Year': '연도별', 'YearQuarter': '분기별', 'YearMonth': '월별'}.get(x, x),
                    index=0
                )
            with c2:
                cat_options = ['ri', 'model', 'head_type', 'xy_scanner', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
                cat_labels = {
                    'ri': 'R/I (용도)', 'model': 'Model', 'head_type': 'Head Type', 
                    'xy_scanner': 'XY Scanner', 'mod_vit': 'MOD/VIT', 'sliding_stage': 'Sliding Stage',
                    'sample_chuck': 'Sample Chuck', 'ae': 'AE'
                }
                selected_cats = st.multiselect(
                    "상세 분류",
                    options=cat_options,
                    default=['ri', 'model'],
                    format_func=lambda x: cat_labels.get(x, x)
                )
            
            # Construct Path & Plot
            final_path = []
            if time_unit != 'None': final_path.append(time_unit)
            final_path.extend(selected_cats)
            
            if final_path:
                fig_sun = charts.plot_sunburst_chart(df_equip, path=final_path)
                st.plotly_chart(fig_sun, use_container_width=True)
        
        st.divider()
        
        # --- 2. Split Layout: Research vs Industrial ---
        col_research, col_industrial = st.columns(2)
        
        # Helper to render column content
        def render_ri_column(col, title, ri_type, color_seq):
            with col:
                st.markdown(f"### {title}")
                df_sub = df_equip[df_equip['ri'] == ri_type]
                
                # Metric
                st.metric(f"등록 장비 수", f"{len(df_sub):,} 대")
                
                if df_sub.empty:
                    st.info("데이터가 없습니다.")
                    return None
                
                # Bar Chart
                st.caption("📊 모델별 분포 (클릭하여 필터링)")
                fig = charts.create_model_bar_chart(df_sub, color_seq)
                
                # Chart Selection
                # Use a unique key for the chart to avoid conflicts
                chart_event = st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    config={'displayModeBar': False},
                    on_select="rerun",
                    selection_mode="points",
                    key=f"chart_{ri_type}"
                )
                
                # Handle Chart Selection
                if chart_event and chart_event.selection.points:
                    # Horizontal bar chart: y is the category (Model Name)
                    clicked_model = chart_event.selection.points[0]['y']
                    
                    # Update the selectbox state if it's different
                    # We need to initialize the key if it doesn't exist to avoid KeyErrors
                    filter_key = f"filter_{ri_type}"
                    if filter_key not in st.session_state:
                        st.session_state[filter_key] = "All"
                        
                    if st.session_state[filter_key] != clicked_model:
                        st.session_state[filter_key] = clicked_model
                        st.rerun()
                
                # Equipment List
                st.caption("📋 장비 목록 (선택)")
                
                # Model Filter Dropdown
                models = sorted(df_sub['model'].unique())
                sel_model_filter = st.selectbox(
                    f"모델 필터", 
                    ["All"] + list(models), 
                    key=f"filter_{ri_type}", 
                    label_visibility="collapsed"
                )
                
                if sel_model_filter != "All":
                    df_list = df_sub[df_sub['model'] == sel_model_filter]
                else:
                    df_list = df_sub
                
                df_list = df_list.sort_values('date', ascending=False).reset_index(drop=True)
                
                event = st.dataframe(
                    df_list[['equipment_name', 'model', 'date']],
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=f"list_{ri_type}",
                    height=300,
                    column_config={
                        "date": st.column_config.DateColumn(
                            "Date",
                            format="YYYY-MM-DD",
                        ),
                        "equipment_name": st.column_config.TextColumn("Equipment Name"),
                        "model": st.column_config.TextColumn("Model")
                    }
                )
                
                selected_names = []
                if event.selection.rows:
                    selected_names = df_list.iloc[event.selection.rows]['equipment_name'].tolist()
                return selected_names

        # Render Columns
        sel_research = render_ri_column(col_research, "Research (연구용)", "Research", px.colors.qualitative.Bold)
        sel_industrial = render_ri_column(col_industrial, "Industrial (산업용)", "Industrial", px.colors.qualitative.Pastel)
        
        # Aggregate Selections
        all_selected = []
        if sel_research: all_selected.extend(sel_research)
        if sel_industrial: all_selected.extend(sel_industrial)
        
        # Remove duplicates (just in case) and limit to 5
        all_selected = list(dict.fromkeys(all_selected))
        
        if len(all_selected) > 5:
            st.warning(f"⚠️ 최대 5개까지만 비교할 수 있습니다. (현재 {len(all_selected)}개 선택됨) 상위 5개만 표시합니다.")
            all_selected = all_selected[:5]
        
        # --- 3. Detail View (Tabs) ---
        st.divider()
        st.markdown("### 장비 상세 정보 & 비교")
        
        if all_selected:
            # Create Tabs: [Equip 1] [Equip 2] ... [Comparison]
            tab_names = all_selected.copy()
            if len(all_selected) > 1:
                tab_names.append("🆚 비교하기")
                
            tabs = st.tabs(tab_names)
            
            # Render Individual Tabs
            for i, equip_name in enumerate(all_selected):
                with tabs[i]:
                    equip_info = df_equip[df_equip['equipment_name'] == equip_name].iloc[0]
                    with st.container(border=True):
                        c_head, c_body = st.columns([1, 3])
                        with c_head:
                            st.markdown(f"## 🏷️")
                            st.markdown(f"**{equip_info['equipment_name']}**")
                            st.caption(f"{equip_info['ri']} | {equip_info['model']}")
                            st.caption(f"📅 {equip_info['date'].strftime('%Y-%m-%d')}")
                            
                        with c_body:
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("**기본 사양**")
                                st.write(f"Head: `{equip_info['head_type']}`")
                                st.write(f"Scanner: `{equip_info['xy_scanner']}`")
                            with c2:
                                st.markdown("**옵션 사양**")
                                st.write(f"Stage: `{equip_info['sliding_stage']}`")
                                st.write(f"Chuck: `{equip_info['sample_chuck']}`")
                            with c3:
                                st.markdown("**기타**")
                                st.write(f"AE: `{equip_info['ae']}`")
                                st.write(f"Mod/Vit: `{equip_info['mod_vit']}`")
            
            # Render Comparison Tab
            if len(all_selected) > 1:
                with tabs[-1]:
                    st.markdown("####  사양 비교")
                    # Prepare Comparison Data
                    comp_data = df_equip[df_equip['equipment_name'].isin(all_selected)].set_index('equipment_name')
                    
                    # Format date to YYYY-MM-DD string for display
                    if 'date' in comp_data.columns:
                        comp_data['date'] = comp_data['date'].dt.strftime('%Y-%m-%d')
                        
                    # Transpose for side-by-side view
                    cols_to_compare = ['ri', 'model', 'date', 'head_type', 'xy_scanner', 'sliding_stage', 'sample_chuck', 'ae', 'mod_vit']
                    df_comp = comp_data[cols_to_compare].T
                    st.dataframe(df_comp, use_container_width=True)
                    
        else:
            st.info("👆 위 목록에서 장비를 선택(체크박스)하면 상세 정보 탭이 생성됩니다. (최대 5개)")
            
    else:
        st.info("데이터가 없습니다. 데이터 관리 탭에서 동기화를 실행해주세요.")

def render_analysis_tab():
    """Tab 2: Quality Analysis"""
    st.header("📈 Control Chart 분석")
    
    if not st.session_state.analysis_triggered:
        st.info("👈 왼쪽 사이드바에서 필터를 선택하고 **'분석 시작'** 버튼을 눌러주세요.")
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
            # If 'None' is selected, we want to show the Check Item name as the series name.
            # If multiple check items are selected, grouping by 'Check Items' achieves this.
            # If single check item is selected, we want that specific item name to appear.
            
            if display_df['Check Items'].nunique() > 1:
                group_col = 'Check Items'
                st.caption("ℹ️ 'None' 선택 시, 항목(Check Items)별로 구분됩니다.")
            else:
                # Single check item: Create a dummy column with the item name
                # This ensures the legend shows "RMS of Zero..." instead of "All Data"
                item_name = display_df['Check Items'].iloc[0]
                display_df[item_name] = item_name # Create column with item name as value
                group_col = item_name
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
            
        # Spec Fetching Logic (Single Model & Single Item)
        specs = None
        unique_models = display_df['Model'].unique()
        unique_items = display_df['Check Items'].unique()
        
        if len(unique_models) == 1 and len(unique_items) == 1:
            specs = db.get_spec_for_item(unique_models[0], unique_items[0])
            # Check if any spec exists
            if specs and all(v is None for v in specs.values()):
                specs = None
            
        try:
            fig_combined = create_control_chart(
                display_df, 
                group_col=group_col,
                equipment_col='장비명', # Pass equipment column for hover
                show_violations=show_violations,
                use_dual_axis=use_dual_axis,
                specs=specs
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
                # Single check item: Create a dummy column with the item name
                item_name = display_df['Check Items'].iloc[0]
                display_df[item_name] = item_name 
                group_col_ind = item_name
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
                    show_violations=True,
                    specs=specs
                )
                st.plotly_chart(fig_individual, use_container_width=True)
            except Exception as e:
                st.error(f"차트 생성 실패 ({name}): {e}")
        
    with tab3:
        st.subheader("통계 요약 (Statistics)")
        
        c1, c2 = st.columns([1, 3])
        with c1:
            group_by_stat_sel = st.selectbox("그룹화 기준 (통계)", group_options, index=0, key='stat_group')
            
        if group_by_stat_sel == 'None':
            if display_df['Check Items'].nunique() > 1:
                group_col_stat = 'Check Items'
            else:
                # Single check item: Create a dummy column with the item name
                item_name = display_df['Check Items'].iloc[0]
                display_df[item_name] = item_name 
                group_col_stat = item_name
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
    
    # Display Persistent Success Message
    if 'sync_msg' in st.session_state:
        st.success(st.session_state['sync_msg'])
        # Optional: Clear message after showing it once? 
        # If we want it to stay "continuously", we might not clear it immediately, 
        # but usually it's better to clear it on the next interaction.
        # For now, let's keep it until another action replaces it or user leaves.
        del st.session_state['sync_msg']
    
    st.info("ℹ️ 현재 버전은 **Viewer 모드**로 동작하며, 데이터 관리는 **Google Sheets**를 통해서만 가능합니다.")

    st.subheader("📂 데이터 동기화 (Data Sync)")
    
    # Google Sheets Sync
    with st.expander("Google Sheets 동기화", expanded=True):
        st.info("연동된 Google Sheet의 데이터를 DB로 가져옵니다. (기존 데이터는 덮어씌워집니다)")
        if st.button("Google Sheets 동기화 실행", key='sync_btn_gsheets', use_container_width=True):
            try:
                from streamlit_gsheets import GSheetsConnection
                with st.spinner("Google Sheets 데이터 읽는 중..."):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    
                    # Try reading 3 sheets
                    try:
                        df_equip = conn.read(worksheet='Equipments')
                        df_meas = conn.read(worksheet='Measurements')
                        
                        # Specs is optional or might be empty
                        try:
                            df_specs = conn.read(worksheet='Specs')
                        except:
                            df_specs = None
                            
                        st.spinner("DB에 저장 중 (관계형 구조)...")
                        result = db.sync_relational_data(df_equip, df_meas, df_specs)
                        
                        msg = f"Google Sheets 동기화 완료! (장비: {result['equipments']}개, 측정값: {result['measurements']}개)"
                        if df_specs is not None and not df_specs.empty:
                            msg += " + 규격(Specs) 동기화 완료"
                            
                        st.session_state['sync_msg'] = msg
                        st.rerun()
                        
                    except Exception as e_rel:
                        # Fallback to single sheet if relational sheets not found
                        # But user said they updated the sheet, so we should prioritize relational.
                        # If Equipments/Measurements sheets are missing, it throws error.
                        st.warning(f"관계형 시트(Equipments, Measurements)를 찾을 수 없어 기본 시트(1번째)를 읽습니다. 오류: {e_rel}")
                        
                        df_gsheet = conn.read()
                        st.spinner("DB에 저장 중 (기본 구조)...")
                        result = db.sync_from_dataframe(df_gsheet)
                        
                        msg = f"Google Sheets 동기화 완료! (장비: {result['equipments']}개, 측정값: {result['measurements']}개)"
                        st.session_state['sync_msg'] = msg
                        st.rerun()

            except Exception as e:
                st.error(f"Google Sheets 동기화 실패: {e}")
                st.caption("secrets.toml 설정과 시트 이름(Equipments, Measurements)을 확인해주세요.")


def render_guide_tab():
    """Tab 4: User Guide"""
    st.header("사용 가이드 (User Guide)")
    
    st.markdown("""
    ### 1. 데이터 동기화 (Google Sheets)
    본 프로그램은 **Google Sheets**와 연동되어 데이터를 관리합니다.
    
    1. **[데이터 관리]** 탭으로 이동합니다.
    2. **[Google Sheets 동기화 실행]** 버튼을 클릭합니다.
    3. 상단에 초록색 성공 메시지가 뜨면 최신 데이터가 반영된 것입니다.
    
    ---
    
    ### 2. 장비 현황 조회
    전체 장비의 분포와 상세 정보를 탐색하는 메뉴입니다.
    
    - **Sunburst 차트**: `R/I` > `Model` > `장비명` 순서로 계층 구조를 시각화합니다. 안쪽 원을 클릭하면 하위 항목으로 줌인(Zoom-in) 됩니다.
    - **막대 그래프**: 연구용/산업용 장비의 모델별 수량을 보여줍니다. 그래프 막대를 클릭하면 하단 목록이 해당 모델로 필터링됩니다.
    - **상세 보기**: 목록에서 장비를 체크(✅)하면 하단에 상세 정보 탭이 열립니다. 2개 이상 선택 시 **비교표**가 생성됩니다.
    
    ---
    
    ### 3. Control Chart 분석
    시계열 데이터의 트렌드와 이상 징후를 분석합니다.
    
    1. **왼쪽 사이드바**에서 분석 대상을 선택합니다.
       - **R/I**: 용도 선택 (Research / Industrial)
       - **Model**: 모델 선택
       - **Check Items**: 분석할 항목 선택 (최대 2개 권장)
       - **날짜 범위**: 분석 기간 설정 (필요 시)
    2. **[분석 시작]** 버튼을 누릅니다.
    3. **[Control Chart]** 탭에서 결과를 확인합니다.
       - **UCL/LCL**: 관리 상한/하한선 (3 Sigma)
       - **Rule of Seven**: 7점 연속 편향 시 붉은색 표시
       - **Trend**: 7점 연속 상승/하락 시 노란색 표시
    """)


def hide_streamlit_style():
    """Streamlit 기본 스타일 숨기기 (메뉴, 푸터 등)"""
    hide_st_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
    st.markdown(hide_st_style, unsafe_allow_html=True)

def main():
    hide_streamlit_style()
    st.title("Control Chart Viewer v1.0")
    
    # Sidebar (Analysis Filters)
    with st.sidebar:
        st.header("🔍 Control Chart 필터")
        
        # 1. R/I (Research/Industrial)
        ris = db.get_unique_values('ri')
        sel_ris = st.multiselect("R/I", ris)
        
        # 2. Model (Filtered by R/I)
        all_models = db.get_unique_values('model')
        filtered_models = all_models
        
        if sel_ris:
            filtered_models = []
            # If 'Research' or 'R' is selected
            if 'Research' in sel_ris or 'R' in sel_ris:
                filtered_models.extend([m for m in all_models if m in RESEARCH_MODELS])
            # If 'Industrial' or 'I' is selected
            if 'Industrial' in sel_ris or 'I' in sel_ris:
                filtered_models.extend([m for m in all_models if m in INDUSTRIAL_MODELS])
            
            # If user selected something else (e.g. empty string or unclassified), include them?
            # For now, just stick to the known lists.
            # Remove duplicates and sort
            filtered_models = sorted(list(set(filtered_models)))
            
            # If filtered list is empty (e.g. only 'R' selected but no R models in DB), show empty or all?
            # Better to show what matches.
            
        sel_models = st.multiselect("Model", filtered_models)
        
        # 3. Check Items
        items = db.get_unique_values('check_item')
        sel_items = st.multiselect("Check Items", items, help="최대 2개 권장")
        
        # 4. Date Range
        use_date = st.checkbox("날짜 범위 적용")
        date_range = []
        if use_date:
            d_start = st.date_input("시작일", value=date(2024, 1, 1))
            d_end = st.date_input("종료일", value=date.today())
            date_range = [d_start, d_end]
            
        st.markdown("---")
        if st.button("분석 시작", type="primary", use_container_width=True):
            st.session_state.analysis_triggered = True
            filters = {}
            # Order doesn't matter for dict, but logical flow is preserved
            if sel_ris: filters['ri'] = sel_ris
            if sel_models: filters['model'] = sel_models
            if sel_items: filters['check_item'] = sel_items
            if use_date: filters['date_range'] = date_range
            
            with st.spinner("데이터 조회 및 분석 중..."):
                df = db.fetch_filtered_data(filters)
                if not df.empty:
                    df = add_date_columns(df)
                st.session_state.filtered_data = df

        # Developer Info
        st.markdown("---")
        st.markdown("### Information")
        st.markdown("""
        **Contact**
        - **Developer**: Levi.Beak
        - **Team**: Production and Quality Control Team, Manufacturing Dept.
        - **Email**: [levi.beak@parksystems.com](mailto:levi.beak@parksystems.com)
        """)

    # Main Tabs
    tab_explorer, tab_analysis, tab_data, tab_guide = st.tabs([
        "📊 장비 현황", "📈 Control Chart", "💾 데이터 관리", "📖 사용 가이드"
    ])
    
    with tab_explorer:
        render_explorer_tab()
        
    with tab_analysis:
        render_analysis_tab()
        
    with tab_data:
        render_data_tab()

    with tab_guide:
        render_guide_tab()

if __name__ == "__main__":
    main()
