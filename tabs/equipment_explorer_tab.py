"""
장비 현황 탐색 탭
Equipment Explorer Tab

Features:
- 장비 통계 대시보드
- 날짜 필터
- Sunburst 차트
- R/I 분할 뷰
- 모델별 분포 차트
- 장비 목록 및 상세 정보
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from modules import database as db
from modules import charts


def render_equipment_explorer_tab():
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
                
                # SID Display Logic
                # If SID is missing, display as empty string
                df_list['display_sid'] = df_list['sid'].fillna('')
                
                event = st.dataframe(
                    df_list[['display_sid', 'equipment_name', 'model', 'date']],
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=f"list_{ri_type}",
                    height=300,
                    column_config={
                        "display_sid": st.column_config.TextColumn("SID"),
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
                        # Layout: Header (Left) and Body (Right-ish)
                        c_head, c_body = st.columns([1, 3])
                        
                        # --- HEADER SECTION (Title) ---
                        with c_head:
                            st.markdown(f"## 🏷️")
                            # SID Display
                            sid_val = equip_info.get('sid')
                            sid_str = str(sid_val) if pd.notna(sid_val) and str(sid_val).strip() != '' else ''
                            if sid_str:
                                st.caption(f"**SID: {sid_str}**")
                                
                            st.markdown(f"**{equip_info['equipment_name']}**")
                            st.caption(f"{equip_info['ri']} | {equip_info['model']}")
                            st.caption(f"📅 {equip_info['date'].strftime('%Y-%m-%d')}")

                        # --- BODY SECTION (Specs) ---
                        with c_body:
                            # === VIEW MODE (Read-only) ===
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("**기본 사양**")
                                st.write(f"Head: `{equip_info['head_type']}`")
                                st.write(f"Scanner: `{equip_info['xy_scanner']}`")
                            with c2:
                                st.markdown("**옵션 사양**")
                                st.write(f"Sliding Stage: `{equip_info['sliding_stage']}`")
                                st.write(f"Chuck: `{equip_info['sample_chuck']}`")
                                st.write(f"AE: `{equip_info['ae']}`")
                                st.write(f"Mod/Vit: `{equip_info['mod_vit']}`")
                            
                            st.markdown("---")
                            # Additional Project Info
                            c4, c5, c6, c7 = st.columns(4)
                            with c4:
                                st.markdown("**Customer**")
                                st.write(f"{equip_info.get('end_user') or '-'}")
                            with c5:
                                st.markdown("**Mfg Engineer**")
                                st.write(f"{equip_info.get('mfg_engineer') or '-'}")
                            with c6:
                                st.markdown("**QC Engineer**")
                                st.write(f"{equip_info.get('qc_engineer') or '-'}")
                            with c7:
                                st.markdown("**Checklist**")
                                st.write(f"{equip_info.get('reference_doc') or '-'}")
                        
                        # Full Data View (Below header/body split)
                        st.divider()
                        with st.expander("📋 상세 측정 데이터 (Full Data View)", expanded=False):
                            if sid_str:
                                full_data = db.get_full_measurements(sid_str)
                                if not full_data.empty:
                                    st.caption("💡 업로드된 원본 상세 데이터입니다. (Category, Remark 등 포함)")
                                    st.dataframe(
                                        full_data, 
                                        use_container_width=True, 
                                        hide_index=True,
                                        column_config={
                                            "status": st.column_config.TextColumn("Status", help="데이터 상태 (pending/approved/rejected)")
                                        }
                                    )
                                else:
                                    st.info("ℹ️ 상세 데이터가 보관되어 있지 않습니다. (이전 데이터는 상세 정보가 없을 수 있습니다)")
                            else:
                                st.warning("⚠️ SID 정보가 없어 데이터를 조회할 수 없습니다.")
            
            # Render Comparison Tab
            if len(all_selected) > 1:
                with tabs[-1]:
                    st.markdown("#### 📊 사양 비교")
                    # Prepare Comparison Data
                    comp_data = df_equip[df_equip['equipment_name'].isin(all_selected)].set_index('equipment_name')
                    
                    # Format date to YYYY-MM-DD string for display
                    if 'date' in comp_data.columns:
                        comp_data['date'] = comp_data['date'].dt.strftime('%Y-%m-%d')
                        
                    # Transpose for side-by-side view
                    cols_to_compare = ['sid', 'ri', 'model', 'date', 'head_type', 'xy_scanner', 'sliding_stage', 'sample_chuck', 'ae', 'mod_vit']
                    df_comp = comp_data[cols_to_compare].T
                    st.dataframe(df_comp, use_container_width=True)
                    
        else:
            st.info("👆 위 목록에서 장비를 선택(체크박스)하면 상세 정보 탭이 생성됩니다. (최대 5개)")
            
    else:
        st.info("데이터가 없습니다. 데이터 관리 탭에서 동기화를 실행해주세요.")
