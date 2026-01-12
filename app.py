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
# DB 모듈 임포트
import database as db
import importlib
importlib.reload(db) # Force reload to apply changes

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
    
    # 앱 시작 시 자동으로 로컬 data.xlsx 로드 시도
    data_file_path = os.path.join(os.path.dirname(__file__), 'data.xlsx')
    if os.path.exists(data_file_path):
        try:
            # Read all 3 sheets
            df_equip = pd.read_excel(data_file_path, sheet_name='Equipments')
            df_meas = pd.read_excel(data_file_path, sheet_name='Measurements')
            try:
                df_specs = pd.read_excel(data_file_path, sheet_name='Specs')
            except:
                df_specs = None
            
            # Use sync_relational_data which sets status='approved' by default
            result = db.sync_relational_data(df_equip, df_meas, df_specs)
            st.session_state.auto_load_msg = f"✅ 로컬 데이터 자동 로드 완료 (장비: {result['equipments']}대, 측정값: {result['measurements']}건)"
        except Exception as e:
            st.session_state.auto_load_msg = f"⚠️ 자동 로드 실패: {str(e)}"

# 세션 상태 초기화
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'analysis_triggered' not in st.session_state:
    st.session_state.analysis_triggered = False

# Equipment Options (From Tkinter App)
EQUIPMENT_OPTIONS = {
    'xy_scanner': {
        'Single': ['10µm', '100µm', '150µm'],
        'Dual': ['Dual 10µm(50µm)', 'Dual 100µm(10µm)', 'Dual 100µm(150µm)', 'Dual 100µm(300mm)']
    },
    'head_type': {
        'Standard': ['Standard', 'Auto Align Standard'],
        'Long': ['Long', 'Auto Align Long'],
        'FX': ['FX Standard'],
        'NX-Hivac': ['NX-Hivac Auto Align'],
        'TSH': ['TSH 50µm', 'TSH 100µm']
    },
    'mod_vit': {
        'N/A': ['N/A'],
        'Accurion': ['Accurion i4', 'Accurion i4 medium', 'Accurion Nano30', 'Accurion Vario(6units)', 'Accurion Vario(8units)'],
        'Dual MOD': ['Dual MOD 4 units', 'Dual MOD 6 units', 'Dual MOD 7 units', 'Dual MOD 8 units'],
        'Single MOD': ['Single MOD 2 units', 'Single MOD 6 units'],
        'Mini450F': ['Mini450F'],
        'Minus-K': ['Minus-K']
    },
    'sliding_stage': {
        'None': ['N/A'],
        'Stage': ['10mm', '50mm']
    },
    'sample_chuck': {
        'N/A': ['N/A'],
        'AL': ['AL Bar type chuck'],
        'SiC': ['SiC Anti-warpage chuck', 'SiC Bar type chuck', 'SiC Flat type chuck', 
                'SiC Fork type chuck', 'SiC Pin Bar type chuck'],
        'Vacuum': ['Vacuum Sample Chuck'],
        'Mask': ['Mask'],
        'Coreflow': ['Coreflow customized']
    },
    'ae': {
        'Research': ['N/A', 'AE101', 'AE201', 'AE202', 'AE203', 'AE204', 'AE401', 'AE402', 
                     'FX200 AE', 'FX40 AE', 'Glove Box', 'Chamber'],
        'Industrial': ['N/A', 'Double Walled', 'Isolated']
    }
}


# Helper functions to get flattened options for SelectboxColumn
def get_xy_scanner_options():
    """Get all XY Scanner options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['xy_scanner'].items():
        options.extend(values)
    return options

def get_head_type_options():
    """Get all Head Type options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['head_type'].items():
        options.extend(values)
    return options

def get_mod_vit_options():
    """Get all MOD/VIT options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['mod_vit'].items():
        options.extend(values)
    return options

def get_sliding_stage_options():
    """Get all Sliding Stage options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['sliding_stage'].items():
        options.extend(values)
    return options

def get_sample_chuck_options():
    """Get all Sample Chuck options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['sample_chuck'].items():
        options.extend(values)
    return options

def get_ae_options():
    """Get all AE options (flattened)"""
    options = []
    for category, values in EQUIPMENT_OPTIONS['ae'].items():
        options.extend(values)
    return options


def sync_data_from_local():
    """로컬 Excel 파일(data.xlsx)에서 데이터를 읽어 DB에 저장 (승인 상태로)"""
    data_file_path = os.path.join(os.path.dirname(__file__), 'data.xlsx')
    if not os.path.exists(data_file_path):
        st.error("⚠️ 'data.xlsx' 파일을 찾을 수 없습니다.")
        st.info("프로젝트 루트에 'data.xlsx' 파일을 배치해주세요.")
        return False

    try:
        # Read all 3 sheets
        df_equip = pd.read_excel(data_file_path, sheet_name='Equipments')
        df_meas = pd.read_excel(data_file_path, sheet_name='Measurements')
        try:
            df_specs = pd.read_excel(data_file_path, sheet_name='Specs')
        except:
            df_specs = None
        
        # Use sync_relational_data (sets status='approved' by default)
        result = db.sync_relational_data(df_equip, df_meas, df_specs)
        
        msg = f"✅ 로컬 데이터 동기화 완료! 장비 {result['equipments']}대, 측정값 {result['measurements']}건 저장됨."
        if df_specs is not None:
            msg += " + 규격(Specs) 동기화 완료"
        st.success(msg)
        return True
        
    except Exception as e:
        st.error(f"❌ 동기화 실패: {str(e)}")
        return False

def extract_equipment_info_from_last_sheet(excel_file):
    """
    Last 시트에서 장비 기본 정보 자동 추출
    
    Args:
        excel_file: UploadedFile 또는 파일 경로
    
    Returns:
        dict: 추출된 장비 정보
    """
    try:
        df = pd.read_excel(excel_file, sheet_name='Last', header=None)
        
        info = {}
        
        # Product Model (Row 21, Column 11)
        if len(df) > 21 and len(df.columns) > 11 and pd.notna(df.iloc[21, 11]):
            info['model'] = str(df.iloc[21, 11]).strip()
        
        # SID Number (Row 24, Column 11)
        if len(df) > 24 and len(df.columns) > 11 and pd.notna(df.iloc[24, 11]):
            info['sid'] = str(df.iloc[24, 11]).strip()
        
        # Reference Document (Row 27, Column 11)
        if len(df) > 27 and len(df.columns) > 11 and pd.notna(df.iloc[27, 11]):
            info['reference_doc'] = str(df.iloc[27, 11]).strip()
        
        # Date of Final Test (Row 30, Column 11)
        if len(df) > 30 and len(df.columns) > 11 and pd.notna(df.iloc[30, 11]):
            date_val = df.iloc[30, 11]
            if isinstance(date_val, datetime):
                info['date'] = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, pd.Timestamp):
                info['date'] = date_val.strftime('%Y-%m-%d')
            else:
                info['date'] = str(date_val)
        
        # End User (Row 33, Column 11)
        if len(df) > 33 and len(df.columns) > 11 and pd.notna(df.iloc[33, 11]):
            info['end_user'] = str(df.iloc[33, 11]).strip()
        
        # Manufacturing Engineer (Row 36, Column 11)
        if len(df) > 36 and len(df.columns) > 11 and pd.notna(df.iloc[36, 11]):
            info['mfg_engineer'] = str(df.iloc[36, 11]).strip()
        
        # Production QC Engineer (Row 39, Column 11)
        if len(df) > 39 and len(df.columns) > 11 and pd.notna(df.iloc[39, 11]):
            info['qc_engineer'] = str(df.iloc[39, 11]).strip()
        
        # Auto-detect R/I based on model
        if 'model' in info:
            info['ri'] = 'Industrial' if info['model'] in INDUSTRIAL_MODELS else 'Research'
        
        return info
        
    except Exception as e:
        # Log error to console for debugging
        print(f"❌ Last 시트 추출 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

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
                        c_head, c_body = st.columns([1, 3])
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
                            
                        with c_body:
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.markdown("**기본 사양**")
                                st.write(f"Head: `{equip_info['head_type']}`")
                                st.write(f"Scanner: `{equip_info['xy_scanner']}`")
                            with c2:
                                st.markdown("**옵션 사양**")
                                st.write(f"Sliding Stage: `{equip_info['sliding_stage']}`")
                                st.write(f"Chuck: `{equip_info['sample_chuck']}`")
                            with c3:
                                st.markdown("**기타**")
                                st.write(f"AE: `{equip_info['ae']}`")
                                st.write(f"Mod/Vit: `{equip_info['mod_vit']}`")
                        
                        # 상세 측정 데이터 (Full Data View)
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
                    st.markdown("####  사양 비교")
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

def analyze_current_data_context(df):
    """
    현재 필터링된 데이터의 컨텍스트 분석
    품질엔지니어가 데이터를 이해하고 신뢰할 수 있도록 핵심 정보 추출
    
    Returns:
        dict: 데이터 요약 정보
    """
    if df is None or df.empty:
        return None
    
    context = {
        # 기본 정보
        'check_items': df['Check Items'].unique().tolist() if 'Check Items' in df.columns else [],
        'models': df['Model'].unique().tolist() if 'Model' in df.columns else [],
        'equipments': df['장비명'].unique().tolist() if '장비명' in df.columns else [],
        'n_equipments': df['장비명'].nunique() if '장비명' in df.columns else 0,
        'n_measurements': len(df),
        
        # 기간
        'date_start': df['종료일'].min() if '종료일' in df.columns else None,
        'date_end': df['종료일'].max() if '종료일' in df.columns else None,
        'date_range_days': 0,
        
        # 구성 분포
        'scanner_dist': {},
        'head_dist': {},
        'mod_vit_dist': {},
        
        # 핵심 지표 (단일 Check Item인 경우만)
        'cpk': None,
        'cp': None,
        'defect_rate': None,
        'spec_margin': None,
        'mean': None,
        'std': None,
        'n_out_of_spec': 0
    }
    
    # 기간 계산
    if context['date_start'] and context['date_end']:
        context['date_range_days'] = (context['date_end'] - context['date_start']).days
    
    # 구성 분포
    if 'XY Scanner' in df.columns:
        context['scanner_dist'] = df['XY Scanner'].replace('', None).dropna().value_counts().to_dict()
    if 'Head Type' in df.columns:
        context['head_dist'] = df['Head Type'].replace('', None).dropna().value_counts().to_dict()
    if 'MOD/VIT' in df.columns:
        context['mod_vit_dist'] = df['MOD/VIT'].replace('', None).dropna().value_counts().to_dict()
    
    # 단일 Check Item인 경우 Cpk 및 스펙 분석
    if len(context['check_items']) == 1 and 'Value' in df.columns:
        try:
            item = context['check_items'][0]
            
            # 측정값 추출
            measurements = df['Value'].dropna()
            
            if len(measurements) > 0:
                mean = measurements.mean()
                std = measurements.std()
                
                context['mean'] = mean
                context['std'] = std
                
                # 스펙 정보 추출 시도
                # measurements 테이블에는 스펙 정보 없으므로, specs 테이블에서 조회
                # 임시로 데이터에서 model 확인
                if len(context['models']) == 1:
                    model = context['models'][0]
                    # specs 조회
                    specs = db.get_spec_for_item(model, item)
                    
                    if specs and specs.get('lsl') is not None and specs.get('usl') is not None:
                        lsl = specs['lsl']
                        usl = specs['usl']
                        
                        # Cp 계산 (공정 능력)
                        if std > 0:
                            context['cp'] = (usl - lsl) / (6 * std)
                        
                        # Cpk 계산 (공정 능력 지수)
                        if std > 0:
                            cpu = (usl - mean) / (3 * std)
                            cpl = (mean - lsl) / (3 * std)
                            context['cpk'] = min(cpu, cpl)
                        
                        # 불량률 계산
                        out_of_spec = ((measurements < lsl) | (measurements > usl)).sum()
                        context['n_out_of_spec'] = int(out_of_spec)
                        context['defect_rate'] = (out_of_spec / len(measurements)) * 100
                        
                        # 스펙 여유도 계산
                        spec_range = usl - lsl
                        process_range = 6 * std
                        context['spec_margin'] = ((spec_range - process_range) / spec_range) * 100
        except Exception as e:
            # 계산 중 오류 발생 시 무시 (지표는 None으로 유지)
            pass
    
    return context




def render_data_context_card(df):
    """
    데이터 컨텍스트를 명확한 카드 형식으로 표시
    품질엔지니어가 현재 분석 중인 데이터를 즉시 이해하고 신뢰할 수 있게 함
    """
    context = analyze_current_data_context(df)
    
    if context is None:
        st.warning("⚠️ 데이터가 없습니다.")
        return
    
    # 카드 스타일
    with st.container(border=True):
        st.markdown("### 📊 현재 분석 중인 데이터")
        
        # 2열 레이아웃: 왼쪽(정보), 오른쪽(지표)
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.markdown("#### 데이터 범위")
            
            # Check Items
            if len(context['check_items']) == 1:
                st.markdown(f"✓ **Check Item**: {context['check_items'][0]}")
            elif len(context['check_items']) > 1:
                st.markdown(f"✓ **Check Items**: {len(context['check_items'])}개 항목")
                with st.expander("📋 항목 목록 보기"):
                    for item in context['check_items']:
                        st.markdown(f"- {item}")
            
            # Model & 장비 수
            if len(context['models']) == 1:
                st.markdown(f"✓ **Model**: {context['models'][0]} ({context['n_equipments']}대 장비)")
            elif len(context['models']) > 1:
                st.markdown(f"✓ **Models**: {len(context['models'])}개 모델, 총 {context['n_equipments']}대 장비")
                with st.expander("📋 모델 목록 보기"):
                    model_counts = {}
                    for idx, row in df.iterrows():
                        model = row.get('Model')
                        equip = row.get('장비명')
                        if model and equip:
                            if model not in model_counts:
                                model_counts[model] = set()
                            model_counts[model].add(equip)
                    for model, equips in model_counts.items():
                        st.markdown(f"- {model}: {len(equips)}대")
            
            # 기간
            if context['date_start'] and context['date_end']:
                st.markdown(
                    f"✓ **기간**: {context['date_start'].strftime('%Y-%m-%d')} ~ "
                    f"{context['date_end'].strftime('%Y-%m-%d')} ({context['date_range_days']}일)"
                )
            
            # 측정값 수
            st.markdown(f"✓ **총 측정값**: {context['n_measurements']:,}개")
            
            # 구성 분포 (상위 3개만)
            config_shown = False
            if context['scanner_dist']:
                scanner_items = list(context['scanner_dist'].items())[:3]
                scanner_str = ", ".join([f"{k} ({v}대)" for k, v in scanner_items])
                st.markdown(f"✓ **Scanner**: {scanner_str}")
                config_shown = True
            
            if context['head_dist'] and not config_shown:
                head_items = list(context['head_dist'].items())[:3]
                head_str = ", ".join([f"{k} ({v}대)" for k, v in head_items])
                st.markdown(f"✓ **Head**: {head_str}")
        
        with col_right:
            # 핵심 지표 (단일 Check Item이고 스펙이 있는 경우)
            if context['cpk'] is not None:
                st.markdown("#### 핵심 지표")
                
                # Cpk
                cpk_val = context['cpk']
                if cpk_val >= 1.67:
                    cpk_delta = "🟢 매우우수"
                    cpk_color = "normal"
                elif cpk_val >= 1.33:
                    cpk_delta = "🟢 우수"
                    cpk_color = "normal"
                elif cpk_val >= 1.0:
                    cpk_delta = "🟡 양호"
                    cpk_color = "off"
                else:
                    cpk_delta = "🔴 부적합"
                    cpk_color = "inverse"
                
                st.metric(
                    "Cpk (공정능력)",
                    f"{cpk_val:.2f}",
                    delta=cpk_delta,
                    delta_color=cpk_color
                )
                
                # 불량률
                defect_val = context['defect_rate']
                if defect_val == 0:
                    st.metric("불량률", "0.0%", delta="✅ 모두 스펙 내", delta_color="normal")
                elif defect_val < 0.3:
                    st.metric(
                        "불량률",
                        f"{defect_val:.2f}%",
                        delta=f"{context['n_out_of_spec']}개",
                        delta_color="off"
                    )
                else:
                    st.metric(
                        "불량률",
                        f"{defect_val:.1f}%",
                        delta=f"⚠️ {context['n_out_of_spec']}개",
                        delta_color="inverse"
                    )
                
                # 스펙 여유도
                margin_val = context['spec_margin']
                if margin_val is not None:
                    if margin_val > 40:
                        margin_delta = "🔵 여유 많음"
                        margin_color = "normal"
                    elif margin_val > 20:
                        margin_delta = "✅ 적정"
                        margin_color = "normal"
                    elif margin_val > 10:
                        margin_delta = "⚠️ 주의"
                        margin_color = "off"
                    else:
                        margin_delta = "🔴 부족"
                        margin_color = "inverse"
                    
                    st.metric(
                        "스펙 여유도",
                        f"{margin_val:.1f}%",
                        delta=margin_delta,
                        delta_color=margin_color
                    )
            else:
                # 지표가 없는 경우
                st.markdown("#### 💡 안내")
                if len(context['check_items']) != 1:
                    st.info("**Check Item을 1개만** 선택하면\\n핵심 지표가 표시됩니다.")
                elif len(context['models']) != 1:
                    st.info("**Model을 1개만** 선택하면\\n핵심 지표가 표시됩니다.")
                else:
                    st.info("스펙 정보가 없어\\n핵심 지표를 계산할 수 없습니다.")
        
        # 구분선
        st.divider()
        
        # 한 문장 요약
        summary_parts = []
        summary_parts.append(f"**{context['n_equipments']}대 장비**에서 측정한")
        summary_parts.append(f"**{context['n_measurements']:,}개 데이터**")
        
        if context['defect_rate'] is not None:
            if context['defect_rate'] == 0:
                summary_parts.append("— **모든 측정값이 스펙 내에 있습니다** ✅")
            elif context['defect_rate'] < 1:
                summary_parts.append(f"— **{context['n_out_of_spec']}개**가 스펙 외부에 있습니다 ⚠️")
            else:
                summary_parts.append(f"— **불량률 {context['defect_rate']:.1f}%** 조치 필요 🔴")
        
        st.markdown(" ".join(summary_parts))


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
    
    # ========== 데이터 컨텍스트 카드 (Phase 0) ==========
    render_data_context_card(display_df)
    st.divider()
    # ==================================================
    
    # ========== 상세 필터 (Phase 1) ==========
    st.markdown("### 🔍 상세 필터")
    st.caption("💡 아래 필터를 사용하여 데이터를 세밀하게 탐색할 수 있습니다. 차트만 업데이트됩니다.")
    
    with st.container(border=True):
        # 2행 3열 레이아웃
        filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)
        filter_row2_col1, filter_row2_col2, filter_row2_col3 = st.columns(3)
        
        # Row 1
        with filter_row1_col1:
            st.markdown("**📋 Check Items**")
            available_items = sorted(display_df['Check Items'].unique().tolist()) if 'Check Items' in display_df.columns else []
            selected_items = st.multiselect(
                "항목 선택",
                options=available_items,
                default=available_items,
                key='filter_check_items',
                label_visibility='collapsed',
                help="분석할 Check Items를 선택하세요"
            )
        
        with filter_row1_col2:
            st.markdown("**🔎 장비명 검색**")
            equipment_search = st.text_input(
                "장비명 입력",
                placeholder="Samsung, LG, WD...",
                key='filter_equipment_search',
                label_visibility='collapsed',
                help="장비명의 일부를 입력하여 필터링"
            )
        
        with filter_row1_col3:
            st.markdown("**📦 Model**")
            available_models = sorted(display_df['Model'].unique().tolist()) if 'Model' in display_df.columns else []
            selected_models = st.multiselect(
                "모델 선택",
                options=available_models,
                default=available_models,
                key='filter_models',
                label_visibility='collapsed',
                help="분석할 모델을 선택하세요"
            )
        
        # Row 2
        with filter_row2_col1:
            st.markdown("**🔬 XY Scanner**")
            available_scanners = sorted(display_df['XY Scanner'].dropna().unique().tolist()) if 'XY Scanner' in display_df.columns else []
            # 빈 문자열 제거
            available_scanners = [s for s in available_scanners if s and str(s).strip()]
            selected_scanners = st.multiselect(
                "Scanner 선택",
                options=available_scanners,
                default=available_scanners,
                key='filter_scanners',
                label_visibility='collapsed',
                help="Scanner 타입별 필터링"
            )
        
        with filter_row2_col2:
            st.markdown("**🎯 Head Type**")
            available_heads = sorted(display_df['Head Type'].dropna().unique().tolist()) if 'Head Type' in display_df.columns else []
            # 빈 문자열 제거
            available_heads = [h for h in available_heads if h and str(h).strip()]
            selected_heads = st.multiselect(
                "Head 선택",
                options=available_heads,
                default=available_heads,
                key='filter_heads',
                label_visibility='collapsed',
                help="Head 타입별 필터링"
            )
        
        with filter_row2_col3:
            # 필터 제어
            st.markdown("**⚙️ 필터 제어**")
            col_reset, col_info = st.columns([1, 1])
            with col_reset:
                if st.button("🔄 초기화", use_container_width=True, help="모든 필터를 기본값으로 복원"):
                    # Session state 초기화
                    for key in ['filter_check_items', 'filter_equipment_search', 
                               'filter_models', 'filter_scanners', 'filter_heads']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            with col_info:
                # 필터 상태 표시
                active_filters = 0
                if selected_items and len(selected_items) < len(available_items):
                    active_filters += 1
                if equipment_search and equipment_search.strip():
                    active_filters += 1
                if selected_models and len(selected_models) < len(available_models):
                    active_filters += 1
                if selected_scanners and len(selected_scanners) < len(available_scanners):
                    active_filters += 1
                if selected_heads and len(selected_heads) < len(available_heads):
                    active_filters += 1
                
                if active_filters > 0:
                    st.metric("활성 필터", f"{active_filters}개", delta="필터링 중", delta_color="off")
                else:
                    st.info("전체\n데이터")
    
    st.divider()
    # =========================================
    
    # ========== 필터 적용 로직 (Task 1.2) ==========
    filtered_df = display_df.copy()
    
    # 1. Check Items 필터
    if selected_items:
        filtered_df = filtered_df[filtered_df['Check Items'].isin(selected_items)]
    
    # 2. 장비명 검색 필터 (대소문자 무시, 부분 일치)
    if equipment_search and equipment_search.strip():
        filtered_df = filtered_df[
            filtered_df['장비명'].str.contains(equipment_search, case=False, na=False, regex=False)
        ]
    
    # 3. Model 필터
    if selected_models:
        filtered_df = filtered_df[filtered_df['Model'].isin(selected_models)]
    
    # 4. Scanner 필터
    if selected_scanners:
        filtered_df = filtered_df[filtered_df['XY Scanner'].isin(selected_scanners)]
    
    # 5. Head 필터
    if selected_heads:
        filtered_df = filtered_df[filtered_df['Head Type'].isin(selected_heads)]
    
    # 필터 결과 표시
    if filtered_df.empty:
        st.warning("⚠️ 선택한 조건에 맞는 데이터가 없습니다. 필터를 조정해주세요.")
        # 필터 초기화 제안
        if st.button("🔄 필터 초기화하기"):
            for key in ['filter_check_items', 'filter_equipment_search', 
                       'filter_models', 'filter_scanners', 'filter_heads']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        return
    
    # 데이터 변경 안내 (필터 적용됨)
    if len(filtered_df) < len(display_df):
        col_filter_info1, col_filter_info2 = st.columns([3, 1])
        with col_filter_info1:
            st.success(
                f"📋 필터 적용 완료: **{len(filtered_df):,}개** 데이터 "
                f"({len(filtered_df['장비명'].unique())}개 장비)"
            )
        with col_filter_info2:
            reduction = (1 - len(filtered_df) / len(display_df)) * 100
            st.metric("필터율", f"{reduction:.1f}%", delta=f"-{len(display_df) - len(filtered_df)}개")
    
    # 필터링된 데이터를 display_df로 교체
    display_df = filtered_df
    # ===============================================
    
    # ========== 현재 필터 조건 표시 (Task 1.3) ==========
    with st.expander("📋 현재 필터 조건", expanded=False):
        filter_summary = []
        
        # 기본 미터릭
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            st.metric("적용 필터", f"{active_filters}개")
        with col_metric2:
            st.metric("최종 데이터", f"{len(display_df)}개")
        with col_metric3:
            st.metric("장비 수", f"{display_df['장비명'].nunique()}대")
        
        st.divider()
        
        # 상세 조건
        if selected_items and len(selected_items) < len(available_items):
            selected_str = ", ".join(selected_items[:5])
            if len(selected_items) > 5:
                selected_str += f" 외 {len(selected_items) - 5}개"
            filter_summary.append(f"**Check Items**: {selected_str}")
        
        if equipment_search and equipment_search.strip():
            filter_summary.append(f"**장비명 검색**: '{equipment_search}'")
        
        if selected_models and len(selected_models) < len(available_models):
            models_str = ", ".join(selected_models)
            filter_summary.append(f"**Model**: {models_str}")
        
        if selected_scanners and len(selected_scanners) < len(available_scanners):
            scanner_str = ", ".join(selected_scanners[:3])
            if len(selected_scanners) > 3:
                scanner_str += f" 외 {len(selected_scanners) - 3}개"
            filter_summary.append(f"**XY Scanner**: {scanner_str}")
        
        if selected_heads and len(selected_heads) < len(available_heads):
            heads_str = ", ".join(selected_heads[:3])
            if len(selected_heads) > 3:
                heads_str += f" 외 {len(selected_heads) - 3}개"
            filter_summary.append(f"**Head Type**: {heads_str}")
        
        if filter_summary:
            st.markdown("적용 중인 필터:")
            for item in filter_summary:
                st.markdown(f"- {item}")
        else:
            st.info("구모든 필터가 기본 상태입니다. (전체 데이터 표시)")
    # ===============================================
        
    # Tabs for Analysis Sub-views
    tab1, tab_spec, tab_equip, tab3, tab4 = st.tabs([
        "📈 Trend 분석", 
        "📊SPEC 분석", 
        "🏭 장비 비교", 
        "📉 통계 요약", 
        "💾 데이터"
    ])
    
    # Simplified Grouping Options (Time-based only)
    # 'None' means no grouping (single series), effectively grouping by nothing or just showing all data.
    # However, create_control_chart expects a column to group by.
    # If 'None' is selected, we can create a dummy column 'All' or group by 'Check Items' if multiple.
    # Let's map 'None' to a dummy column for now, or handle it logic.
    
    group_options = ['None', '연도', '분기', '월']
    
    with tab1:
        st.subheader("📈 Trend 분석 (시계열 Control Chart)")
        
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
    
    # ========== 스펙 분석 탭 (Phase 2 - NEW) ==========
    with tab_spec:
        st.subheader("📊 스펙 분석 (Spec Analysis with Cpk)")
        st.caption("💡 공정 능력 지수(Cpk)를 자동 계산하고, 스펙 적정성을 평가합니다.")
        
        # Import spec_analysis module
        from spec_analysis import (
            prepare_spec_data,
            calculate_process_capability,
            create_histogram_with_specs,
            generate_insights
        )
        
        # Check Item 선택
        unique_items = display_df['Check Items'].unique().tolist() if 'Check Items' in display_df.columns else []
        
        if len(unique_items) == 0:
            st.warning("⚠️ Check Item이 없습니다.")
        elif len(unique_items) == 1:
            selected_spec_item = unique_items[0]
            st.info(f"분석 항목: **{selected_spec_item}**")
        else:
            selected_spec_item = st.selectbox(
                "분석 항목 선택",
                unique_items,
                key='spec_analysis_item',
                help="Cpk를 계산할 Check Item을 선택하세요"
            )
        
        if len(unique_items) > 0:
            item_df = display_df[display_df['Check Items'] == selected_spec_item]
            
            # 1. 데이터 준비
            data = prepare_spec_data(item_df)
            
            if data is None or len(data['measurements']) == 0:
                st.warning("⚠️ 선택한 항목에 측정 데이터가 없습니다.")
            else:
                # 2. 통계 계산
                stats = calculate_process_capability(data, data['lsl'], data['usl'])
                
                # 3. 핵심 지표 표시
                st.markdown("#### 📈 핵심 공정 지표")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if stats['cpk'] is not None:
                        cpk_val = stats['cpk']
                        if cpk_val >= 1.67:
                            delta_text = "🞢 매우우수"
                            delta_color = "normal"
                        elif cpk_val >= 1.33:
                            delta_text = "🞢 우수"
                            delta_color = "normal"
                        elif cpk_val >= 1.0:
                            delta_text = "🞡 양호"
                            delta_color = "off"
                        else:
                            delta_text = "🔴 부적합"
                            delta_color = "inverse"
                        
                        st.metric(
                            "Cpk (공정능력)",
                            f"{cpk_val:.2f}",
                            delta=delta_text,
                            delta_color=delta_color,
                            help="Cpk >= 1.33: 우수, >= 1.0: 양호, < 1.0: 부적합"
                        )
                    else:
                        st.metric("Cpk", "N/A", help="스펙 정보 없음")
                
                with col2:
                    if stats['mean'] is not None:
                        st.metric(
                            "평균",
                            f"{stats['mean']:.2f} {data['unit']}",
                            help=f"측정값 평균 ({stats['n']}개 데이터)"
                        )
                    else:
                        st.metric("평균", "N/A")
                
                with col3:
                    if stats['std'] is not None:
                        st.metric(
                            "표준편차 (σ)",
                            f"{stats['std']:.2f} {data['unit']}",
                            help="공정 변동성 지표"
                        )
                    else:
                        st.metric("표준편차", "N/A")
                
                with col4:
                    if stats['margin'] is not None:
                        margin = stats['margin']
                        if margin > 40:
                            delta_text = "🔵 여유 많음"
                            delta_color = "normal"
                        elif margin > 20:
                            delta_text = "✅ 적정"
                            delta_color = "normal"
                        elif margin > 10:
                            delta_text = "⚠️ 주의"
                            delta_color = "off"
                        else:
                            delta_text = "🔴 부족"
                            delta_color = "inverse"
                        
                        st.metric(
                            "스펙 여유도",
                            f"{margin:.1f}%",
                            delta=delta_text,
                            delta_color=delta_color,
                            help="스펙 대비 공정 변동 여유 공간"
                        )
                    else:
                        st.metric("스펙 여유도", "N/A")
                
                st.divider()
                
                # 4. 히스토그램 + 스펙 라인
                st.markdown("#### 📊 측정값 분포")
                
                fig = create_histogram_with_specs(data, stats)
                st.plotly_chart(fig, use_container_width=True)
                
                # 5. 인사이트
                st.markdown("#### 💡 분석 결과 및 권장사항")
                
                insights = generate_insights(data, stats)
                for insight in insights:
                    st.markdown(f"- {insight}")
                
                # 6. 상세 통계 (Expander)
                with st.expander("📋 상세 통계", expanded=False):
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        st.markdown("**스펙 정보**")
                        st.json({
                            'Check Item': data['item'],
                            'LSL (Min)': data['lsl'],
                            'Target (Criteria)': data['target'],
                            'USL (Max)': data['usl'],
                            'Unit': data['unit']
                        })
                    
                    with col_detail2:
                        st.markdown("**공정 통계**")
                        st.json({
                            '평균': round(stats['mean'], 4) if stats['mean'] else None,
                            '표준편차': round(stats['std'], 4) if stats['std'] else None,
                            'Cp': round(stats['cp'], 3) if stats['cp'] else None,
                            'Cpk': round(stats['cpk'], 3) if stats['cpk'] else None,
                            'CPU': round(stats['cpu'], 3) if stats['cpu'] else None,
                            'CPL': round(stats['cpl'], 3) if stats['cpl'] else None,
                            '스펙 여유도 (%)': round(stats['margin'], 2) if stats['margin'] else None,
                            '불량률 (%)': round(stats['defect_rate'], 2) if stats['defect_rate'] else None,
                            '스펙 외부 개수': stats['n_out_of_spec'],
                            '데이터 수': stats['n'],
                            '장비 수': data['n_equipments']
                        })
    # =================================================
        
    with tab_equip:
        st.subheader("🏭 장비 비교 (Equipment Comparison)")
        st.caption("💡 장비 간 성능 차이를 분석하고, 문제 장비를 자동으로 식별합니다.")
        
        # Check Item 선택
        unique_items_equip = display_df['Check Items'].unique().tolist() if 'Check Items' in display_df.columns else []
        
        if len(unique_items_equip) == 0:
            st.warning("⚠️ Check Item이 없습니다.")
        elif len(unique_items_equip) == 1:
            selected_equip_item = unique_items_equip[0]
            st.info(f"뵄교 항목: **{selected_equip_item}**")
        else:
            selected_equip_item = st.selectbox(
                "비교 항목 선택",
                unique_items_equip,
                key='equip_comparison_item',
                help="장비 간 비교할 Check Item을 선택하세요"
            )
        
        if len(unique_items_equip) > 0:
            from equipment_tab_renderer import render_equipment_comparison_content
            render_equipment_comparison_content(display_df, selected_equip_item) 
        
    with tab3:
        st.subheader("📉 통계 요약 (UCL/LCL 기반)")
        
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
        st.subheader("💾 필터링된 원본 데이터")
        st.dataframe(display_df, use_container_width=True)

def render_data_tab():
    """Tab 3: Data Upload - Checklist Excel Parser"""
    from upload_tab import render_upload_tab
    render_upload_tab(
        extract_func=extract_equipment_info_from_last_sheet,
        insert_func=db.insert_equipment_from_excel,
        sync_func=sync_data_from_local,
        equipment_options=EQUIPMENT_OPTIONS,
        industrial_models=INDUSTRIAL_MODELS,
        check_status_func=db.get_equipment_status,
        log_history_func=db.log_approval_history
    )


def check_admin_login():
    """Returns True if admin is logged in."""
    st.header("🔒 관리자 모드 (Admin)")
    
    def check_password():
        """Returns `True` if the user had the correct password."""
        def password_entered():
            """Checks whether a password entered by the user is correct."""
            import os
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
    
    if not check_password():
        return False
    
    st.success("로그인 성공! 관리자 권한으로 접속되었습니다.")
    return True


def render_approval_queue():
    """Tab 4-1: Approval Queue (Original Admin Logic)"""
    # Login check is handled by parent function
    
    # Import approval utilities
    from approval_utils import create_original_excel, create_modified_excel, compare_dataframes, compare_dicts
    
    # 승인 대기 검증 시스템
    st.subheader("📋 승인 대기 검증")
    
    df_pending = db.get_pending_equipments()
    
    if df_pending.empty:
        st.info("현재 대기 중인 데이터가 없습니다.")
        return
    
    st.markdown(f"총 **{len(df_pending)}**건의 대기 데이터가 있습니다.")
    
    # Step 1: SID 선택
    st.markdown("### 🔍 Step 1: 검증할 장비 선택")
    
    # SID 옵션 생성 (날짜 + SID + 장비명 + Model)
    sid_options = {}
    for idx, row in df_pending.iterrows():
        label = f"[{row['uploaded_at']}] {row['equipment_name']} ({row['sid']}) - {row['model']}"
        sid_options[label] = row['id']
    
    selected_label = st.selectbox(
        "SID 선택",
        options=list(sid_options.keys()),
        key="selected_sid_label"
    )
    
    if not selected_label:
        return
    
    equipment_id = sid_options[selected_label]
    
    # 선택된 장비 정보 로딩
    selected_row = df_pending[df_pending['id'] == equipment_id].iloc[0]
    
    # Equipment 데이터 로딩 (딕셔너리 형태)
    equipment_data = {
        'id': selected_row['id'],
        'SID': selected_row['sid'],
        '장비명': selected_row['equipment_name'],
        '종료일': selected_row['date'],
        'R/I': selected_row['ri'],
        'Model': selected_row['model'],
        'XY Scanner': selected_row['xy_scanner'],
        'Head Type': selected_row['head_type'],
        'MOD/VIT': selected_row['mod_vit'],
        'Sliding Stage': selected_row['sliding_stage'],
        'Sample Chuck': selected_row['sample_chuck'],
        'AE': selected_row['ae'],
        'End User': selected_row['end_user'],
        'Mfg Engineer': selected_row['mfg_engineer'],
        'QC Engineer': selected_row['qc_engineer'],
        'Reference Doc': selected_row['reference_doc']
    }
    
    # Measurements 데이터 로딩
    # 1. 먼저 Staging 테이블(pending_measurements)에서 조회 (Full Columns)
    measurements_data = db.get_pending_measurements(selected_row['sid'])
    
    # 2. 없으면 기존 방식(measurements 테이블)으로 조회 (Legacy Support)
    # 2. 없으면 기존 방식(measurements 테이블)으로 조회 (Legacy Support)
    if measurements_data.empty:
        measurements_data = db.get_measurements_by_sid(selected_row['sid'], status='pending')
    else:
        # 컬럼 순서 재배치 (UI 일관성: 업로드 탭과 유사하게)
        # Category, Check Items, Min, Criteria, Max, Measurement, Unit, PASS/FAIL, Trend, Remark
        desired_order = [
            'Category', 'Check Items', 'Min', 'Criteria', 'Max', 
            'Measurement', 'Unit', 'PASS/FAIL', 'Trend', 'Remark', 
            'status', 'sid', 'equipment_name', 'id' # 숨겨진 컬럼들
        ]
        # 존재하는 컬럼만 선택하여 순서 적용
        existing_cols = [col for col in desired_order if col in measurements_data.columns]
        # 나머지 컬럼들도 뒤에 붙임
        remaining_cols = [col for col in measurements_data.columns if col not in existing_cols]
        measurements_data = measurements_data[existing_cols + remaining_cols]
    
    # 이전 반려 이력 확인
    previous_rejections = db.check_previous_rejections(selected_row['sid'])
    
    if not previous_rejections.empty:
        # 재제출 여부 확인
        if db.is_resubmitted(selected_row['sid']):
            st.info(f"🔄 **재제출됨**: 이 장비는 반려 후 수정되어 다시 제출되었습니다.")
            
        st.warning(f"⚠️ 이 장비({selected_row['sid']})는 **{len(previous_rejections)}번** 반려된 이력이 있습니다!")
        
        with st.expander("📜 이전 반려 이력 보기"):
            for idx, row in previous_rejections.iterrows():
                admin_str = f"관리자: {row['admin_name']}" if pd.notna(row['admin_name']) and row['admin_name'] else "관리자: 미기록"
                st.markdown(f"""
                **{idx + 1}. [{row['timestamp']}] 반려**
                - {admin_str}
                - 사유: {row['reason'] if pd.notna(row['reason']) else '(사유 없음)'}
                - 수정 항목: {row['modification_count']}건
                """)
    
    st.divider()
    
    # Step 2: 데이터 검증 및 수정
    st.markdown("### ✏️ Step 2: 데이터 검증 및 수정")
    
    tab1, tab_raw, tab3, tab4 = st.tabs([
        "ℹ️ 장비 정보", 
        "� 원본 데이터 (Raw)", 
        "�📊 측정 데이터 (Trend)", 
        "📝 수정 사항"
    ])
    
    with tab1:
        st.markdown("**장비 정보 (편집 가능)**")
        st.caption("🔒 SID, Model, 종료일은 수정할 수 없습니다.")
        
        # DataFrame으로 변환(편집용)
        df_equipment = pd.DataFrame([equipment_data])
        
        # Equipment 편집기
        edited_equipment_df = st.data_editor(
            df_equipment,
            disabled=['id', 'SID', 'Model', '종료일'],  # 읽기 전용
            column_config={
                'id': None,  # 숨김
                'SID': st.column_config.TextColumn('SID', disabled=True),
                '장비명': st.column_config.TextColumn('장비명'),
                '종료일': st.column_config.TextColumn('종료일', disabled=True),
                'R/I': st.column_config.SelectboxColumn(
                    'R/I',
                    options=['Research', 'Industrial'],
                    required=True
                ),
                'Model': st.column_config.TextColumn('Model', disabled=True),
                'XY Scanner': st.column_config.SelectboxColumn(
                    'XY Scanner',
                    options=get_xy_scanner_options(),
                    required=True
                ),
                'Head Type': st.column_config.SelectboxColumn(
                    'Head Type',
                    options=get_head_type_options(),
                    required=True
                ),
                'MOD/VIT': st.column_config.SelectboxColumn(
                    'MOD/VIT',
                    options=get_mod_vit_options(),
                    required=True
                ),
                'Sliding Stage': st.column_config.SelectboxColumn(
                    'Sliding Stage',
                    options=get_sliding_stage_options(),
                    required=True
                ),
                'Sample Chuck': st.column_config.SelectboxColumn(
                    'Sample Chuck',
                    options=get_sample_chuck_options(),
                    required=True
                ),
                'AE': st.column_config.SelectboxColumn(
                    'AE',
                    options=get_ae_options(),
                    required=True
                ),
                'End User': st.column_config.TextColumn('End User'),
                'Mfg Engineer': st.column_config.TextColumn('Mfg Engineer'),
                'QC Engineer': st.column_config.TextColumn('QC Engineer'),
                'Reference Doc': st.column_config.TextColumn('Reference Doc'),
            },
            use_container_width=True,
            hide_index=True,
            key=f"equipment_editor_{equipment_id}"
        )
        
        # 수정된 데이터를 딕셔너리로 변환
        edited_equipment_data = edited_equipment_df.iloc[0].to_dict()
    
    with tab_raw:
        st.markdown("**원본 데이터 (Read-only)**")
        st.caption("💡 업로드된 엑셀의 모든 컬럼 정보입니다. 이력 관리를 위해 보존됩니다.")
        
        # Get full measurements data from pending_measurements table
        full_raw_data = db.get_full_measurements(selected_row['sid'])
        
        if not full_raw_data.empty:
            st.markdown("##### 📄 엑셀 원본 데이터 (업로드 시 형태 그대로)")
            st.dataframe(
                full_raw_data,
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    "#": st.column_config.NumberColumn("#", width="small", help="행 번호"),
                    "Module": st.column_config.TextColumn("Module", width="medium"),
                    "Check Items": st.column_config.TextColumn("Check Items", width="large"),
                    "Min": st.column_config.TextColumn("Min", width="small"),
                    "Criteria": st.column_config.TextColumn("Criteria", width="small"),
                    "Max": st.column_config.TextColumn("Max", width="small"),
                    "Measurement": st.column_config.TextColumn("Measurement", width="medium"),
                    "Unit": st.column_config.TextColumn("Unit", width="small"),
                    "PASS/FAIL": st.column_config.TextColumn("PASS/FAIL", width="small"),
                    "Category": st.column_config.TextColumn("Category", width="medium"),
                    "Trend": st.column_config.TextColumn("Trend", width="small"),
                    "Remark": st.column_config.TextColumn("Remark", width="large"),
                }
            )
            st.info(f"📊 총 **{len(full_raw_data)}개** 항목 (Trend 대상 및 비대상 모두 포함)")
        else:
            st.warning("⚠️ 원본 데이터가 보관되어 있지 않습니다. (이전 데이터는 상세 정보가 없을 수 있습니다)")
    
    with tab3:
        st.markdown("**측정 데이터 (Value 편집 가능)**")
        st.caption("⚠️ 측정값 수정은 신중히 진행하세요. 원본 엑셀 파일과 크로스체크 필요합니다.")
        
        # 초기화 카운터 초기화
        if f'reset_counter_{equipment_id}' not in st.session_state:
            st.session_state[f'reset_counter_{equipment_id}'] = 0
        
        # Measurements 편집기 (동적 key 사용)
        edited_measurements = st.data_editor(
            measurements_data,
            disabled=['sid', 'check_items', 'equipment_name', 'Category', 'Check Items', 'Min', 'Criteria', 'Max', 'Unit', 'PASS/FAIL', 'Trend', 'Remark'],  # Measurement 제외하고 모두 읽기 전용
            column_config={
                'id': None,
                'sid': None,
                'equipment_name': None,
                'status': None,
                'Category': st.column_config.TextColumn('Category', disabled=True),
                'Check Items': st.column_config.TextColumn('Check Items', disabled=True),
                'Min': st.column_config.NumberColumn('Min', disabled=True, format="%.4f"),
                'Criteria': st.column_config.NumberColumn('Criteria', disabled=True, format="%.4f"),
                'Max': st.column_config.NumberColumn('Max', disabled=True, format="%.4f"),
                'Measurement': st.column_config.NumberColumn(
                    'Measurement',
                    help="측정값 (편집 가능)",
                    format="%.4f",
                    required=True
                ),
                'Unit': st.column_config.TextColumn('Unit', disabled=True),
                'PASS/FAIL': st.column_config.TextColumn('PASS/FAIL', disabled=True),
                'Trend': st.column_config.TextColumn('Trend', disabled=True),
                'Remark': st.column_config.TextColumn('Remark', disabled=True),
                
                # Legacy compatibility (for old data)
                'check_items': st.column_config.TextColumn('Check Items', disabled=True),
                'value': st.column_config.NumberColumn('Measurement', format="%.4f", required=True),
            },
            use_container_width=True,
            height=400,
            key=f"measurements_editor_{equipment_id}_{st.session_state[f'reset_counter_{equipment_id}']}"
        )
        
        # 하단 정보 및 초기화 버튼 (병렬 배치)
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.info(f"📊 총 **{len(edited_measurements)}개** 측정 항목")
        with col_btn:
            if st.button("🔄 원본으로 초기화", key=f"reset_btn_{equipment_id}", use_container_width=True):
                st.session_state[f'reset_counter_{equipment_id}'] += 1
                st.rerun()
    
    with tab4:
        st.markdown("**변경 사항 요약**")
        
        # Equipment 변경사항
        eq_changes = compare_dicts(equipment_data, edited_equipment_data)
        
        # Measurements 변경사항
        meas_changes = compare_dataframes(measurements_data, edited_measurements)
        
        total_changes = len(eq_changes) + len(meas_changes)
        
        if total_changes == 0:
            st.success("✅ 변경된 항목이 없습니다.")
        else:
            st.warning(f"⚠️ 총 **{total_changes}**개 항목이 수정되었습니다!")
            
            if eq_changes:
                st.markdown("**📄 장비 정보 변경사항:**")
                df_eq_changes = pd.DataFrame(eq_changes)
                st.dataframe(df_eq_changes, use_container_width=True)
            
            if meas_changes:
                st.markdown("**📊 측정 데이터 변경사항:**")
                df_meas_changes = pd.DataFrame(meas_changes)
                st.dataframe(df_meas_changes, use_container_width=True)
    
    st.divider()
    
    # Step 3: 최종 확인 및 조치
    st.markdown("### ✅ Step 3: 최종 확인 및 조치")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**� 엑셀 다운로드**")
        
        # 원본 데이터 다운로드
        original_excel = create_original_excel(equipment_data, measurements_data)
        st.download_button(
            label="📥 원본 데이터 다운로드",
            data=original_excel,
            file_name=f"original_{selected_row['sid']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        # 수정본 다운로드 (변경사항이 있을 때만)
        if total_changes > 0:
            modified_excel = create_modified_excel(
                equipment_data, edited_equipment_data,
                measurements_data, edited_measurements
            )
            st.download_button(
                label="📥 수정본 다운로드 (변경 이력 포함) ⭐",
                data=modified_excel,
                file_name=f"modified_{selected_row['sid']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
    
    with col2:
        st.markdown("**👤 관리자 정보 (선택사항)**")
        admin_name = st.text_input("관리자 이름", placeholder="예: 홍길동", key=f"admin_name_{equipment_id}")
    
    st.divider()
    
    # 승인/반려 버튼
    col_approve, col_reject = st.columns(2)
    
    with col_approve:
        if st.button("✅ 승인 (수정사항 반영)", type="primary", use_container_width=True, key=f"approve_{equipment_id}"):
            # 수정된 데이터로 DB 업데이트
            # Equipment 업데이트
            update_data = {
                'equipment_name': edited_equipment_data['장비명'],
                'ri': edited_equipment_data['R/I'],
                'xy_scanner': edited_equipment_data['XY Scanner'],
                'head_type': edited_equipment_data['Head Type'],
                'mod_vit': edited_equipment_data['MOD/VIT'],
                'sliding_stage': edited_equipment_data['Sliding Stage'],
                'sample_chuck': edited_equipment_data['Sample Chuck'],
                'ae': edited_equipment_data['AE'],
                'end_user': edited_equipment_data['End User'],
                'mfg_engineer': edited_equipment_data['Mfg Engineer'],
                'qc_engineer': edited_equipment_data['QC Engineer'],
                'reference_doc': edited_equipment_data['Reference Doc']
            }
            
            # DB 업데이트
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Equipment 업데이트
            cursor.execute("""
                UPDATE equipments
                SET equipment_name=?, ri=?, xy_scanner=?, head_type=?, mod_vit=?,
                    sliding_stage=?, sample_chuck=?, ae=?, end_user=?,
                    mfg_engineer=?, qc_engineer=?, reference_doc=?, status='approved'
                WHERE id=?
            """, (
                update_data['equipment_name'], update_data['ri'], update_data['xy_scanner'],
                update_data['head_type'], update_data['mod_vit'], update_data['sliding_stage'],
                update_data['sample_chuck'], update_data['ae'], update_data['end_user'],
                update_data['mfg_engineer'], update_data['qc_engineer'], update_data['reference_doc'],
                equipment_id
            ))
            
            # Measurements 업데이트
            for idx, row in edited_measurements.iterrows():
                # 컬럼명 호환성 처리
                val = row.get('Measurement') if 'Measurement' in row else row.get('value')
                check_item = row.get('Check Items') if 'Check Items' in row else row.get('check_items')
                
                # 1. pending_measurements 업데이트 (Staging)
                cursor.execute("""
                    UPDATE pending_measurements
                    SET value=?, status='approved'
                    WHERE sid=? AND check_items=? AND status='pending'
                """, (val, selected_row['sid'], check_item))
                
                # 2. measurements 테이블 업데이트 (Production)
                cursor.execute("""
                    UPDATE measurements
                    SET value=?, status='approved'
                    WHERE sid=? AND check_items=? AND status='pending'
                """, (val, selected_row['sid'], check_item))
            
            conn.commit()
            conn.close()
            
            # 승인 이력 기록
            db.log_approval_history(
                sid=selected_row['sid'],
                equipment_id=equipment_id,
                action='approved',
                admin_name=admin_name if admin_name else None,
                reason=f"승인 완료 (수정 {total_changes}건)" if total_changes > 0 else "승인 완료",
                previous_status='pending',
                new_status='approved',
                modification_count=total_changes
            )
            
            st.success(f"✅ {selected_row['sid']} 승인 완료! (수정사항 {total_changes}건 반영)")
            st.balloons()
            st.rerun()
    
    with col_reject:
        with st.expander("❌ 반려하기"):
            st.caption("반려 사유를 입력하고 '반려 확정' 버튼을 클릭하세요.")
            reject_reason = st.text_area(
                "반려 사유 (필수)",
                placeholder="예: Z Detector offset 측정값 이상 (예상 범위: 200±20, 실측: 81.2938)\n재측정 후 재제출 요청",
                key=f"reject_reason_{equipment_id}"
            )
            
            if st.button("❌ 반려 확정", type="secondary", use_container_width=True, key=f"reject_confirm_{equipment_id}"):
                if not reject_reason or reject_reason.strip() == "":
                    st.error("⚠️ 반려 사유를 입력해주세요!")
                else:
                    # 반려 처리 (상태 변경)
                    db.reject_equipment(equipment_id, reason=reject_reason, admin_name=admin_name)
                    
                    # 반려 이력 기록
                    db.log_approval_history(
                        sid=selected_row['sid'],
                        equipment_id=equipment_id,
                        action='rejected',
                        admin_name=admin_name if admin_name else None,
                        reason=reject_reason,
                        previous_status='pending',
                        new_status='rejected',
                        modification_count=total_changes
                    )
                    
                    st.warning(f"❌ {selected_row['sid']} 반려 완료.\n\n**사유**: {reject_reason}")
                    st.rerun()


def render_data_explorer():
    """Tab 4-2: Data Explorer with Right Sidebar Filter"""
    st.subheader("🗄️ 전체 데이터 조회 (Data Explorer)")
    
    # Layout: Main (75%) | Filter (25%)
    c_main, c_filter = st.columns([3, 1])
    
    # --- Right Sidebar Filter ---
    with c_filter:
        st.markdown("### 🔍 필터 (Filter)")
        with st.container(border=True):
            # 1. Search
            search_term = st.text_input("검색 (SID, 장비명)", placeholder="키워드 입력...")
            
            # 2. Status
            status_opts = ['approved', 'pending', 'rejected']
            sel_status = st.multiselect("상태 (Status)", status_opts, default=['approved', 'pending'])
            
            # 3. Model
            all_models = db.get_unique_values('model')
            sel_models = st.multiselect("모델 (Model)", all_models)
            
            # 4. Date Range
            use_date = st.checkbox("날짜 범위 적용", key="admin_date_check")
            date_range = []
            if use_date:
                d_start = st.date_input("시작일", value=date(2024, 1, 1), key="admin_d_start")
                d_end = st.date_input("종료일", value=date.today(), key="admin_d_end")
                date_range = [d_start, d_end]
                
            st.caption("필터 조건을 변경하면 자동으로 갱신됩니다.")
            
    # Fetch Data based on filters
    filters = {
        'search': search_term,
        'status': sel_status,
        'model': sel_models,
        'date_range': date_range if use_date else None
    }
    
    df_equipments = db.get_all_equipments(filters)
    
    # --- Main Content ---
    with c_main:
        if df_equipments.empty:
            st.info("조건에 맞는 데이터가 없습니다.")
        else:
            st.markdown(f"총 **{len(df_equipments)}**건의 데이터가 검색되었습니다.")
            
            # 장비 선택 (Selectbox)
            # Label format: [STATUS] EquipmentName (SID)
            equip_options = {
                f"[{row['status'].upper()}] {row['equipment_name']} ({row['sid']})": row['sid'] 
                for _, row in df_equipments.iterrows()
            }
            
            selected_equip_label = st.selectbox("장비 선택", list(equip_options.keys()))
            
            if selected_equip_label:
                selected_sid = equip_options[selected_equip_label]
                
                # 상세 정보 표시
                st.divider()
                st.markdown(f"### 📄 상세 데이터: `{selected_sid}`")
                
                # 장비 기본 정보 (Expander)
                with st.expander("ℹ️ 장비 기본 정보", expanded=False):
                    filtered_equip = df_equipments[df_equipments['sid'] == selected_sid]
                    if not filtered_equip.empty:
                        equip_info = filtered_equip.iloc[0]
                        st.json(equip_info.to_dict())
                    else:
                        st.warning("⚠️ 장비 정보를 찾을 수 없습니다.")
                
                # 원본 데이터 (Expander)
                with st.expander("📄 원본 데이터 (Raw) - 엑셀 업로드 시 형태 그대로", expanded=False):
                    full_data = db.get_full_measurements(selected_sid)
                    if not full_data.empty:
                        st.dataframe(
                            full_data, 
                            use_container_width=True,
                            height=400,
                            hide_index=True,
                            column_config={
                                "#": st.column_config.NumberColumn("#", width="small", help="행 번호"),
                                "Module": st.column_config.TextColumn("Module", width="medium"),
                                "Check Items": st.column_config.TextColumn("Check Items", width="large"),
                                "Min": st.column_config.TextColumn("Min", width="small"),
                                "Criteria": st.column_config.TextColumn("Criteria", width="small"),
                                "Max": st.column_config.TextColumn("Max", width="small"),
                                "Measurement": st.column_config.TextColumn("Measurement", width="medium"),
                                "Unit": st.column_config.TextColumn("Unit", width="small"),
                                "PASS/FAIL": st.column_config.TextColumn("PASS/FAIL", width="small"),
                                "Category": st.column_config.TextColumn("Category", width="medium"),
                                "Trend": st.column_config.TextColumn("Trend", width="small"),
                                "Remark": st.column_config.TextColumn("Remark", width="large"),
                            }
                        )
                        st.info(f"📊 총 **{len(full_data)}개** 항목 (Trend 대상 및 비대상 모두 포함)")
                    else:
                        st.warning("상세 측정 데이터가 없습니다.")
                
                # 측정 데이터 (Expander)
                with st.expander("📊 측정 데이터 (Trend) - 트렌드 분석 대상만 필터링", expanded=True):
                    trend_data = db.get_pending_measurements(selected_sid)
                    if not trend_data.empty:
                        # Add row number
                        trend_data_with_num = trend_data.copy()
                        trend_data_with_num.insert(0, '#', range(1, len(trend_data_with_num) + 1))
                        
                        st.dataframe(
                            trend_data_with_num,
                            use_container_width=True,
                            height=400,
                            hide_index=True,
                            column_config={
                                "#": st.column_config.NumberColumn("#", width="small", help="행 번호"),
                                "id": None,
                                "sid": None,
                                "equipment_name": None,
                                "status": None,
                                "Category": st.column_config.TextColumn("Category", width="medium"),
                                "Check Items": st.column_config.TextColumn("Check Items", width="large"),
                                "Min": st.column_config.NumberColumn("Min", format="%.4f"),
                                "Criteria": st.column_config.NumberColumn("Criteria", format="%.4f"),
                                "Max": st.column_config.NumberColumn("Max", format="%.4f"),
                                "Measurement": st.column_config.NumberColumn("Measurement", format="%.4f"),
                                "Unit": st.column_config.TextColumn("Unit", width="small"),
                                "PASS/FAIL": st.column_config.TextColumn("PASS/FAIL", width="small"),
                                "Trend": st.column_config.TextColumn("Trend", width="small"),
                                "Remark": st.column_config.TextColumn("Remark", width="large"),
                            }
                        )
                        st.info(f"📊 총 **{len(trend_data)}개** Trend 분석 대상 항목")
                    else:
                        st.warning("Trend 분석 대상 데이터가 없습니다.")


def render_admin_tab():
    """Tab 4: Admin (Manager) - Main Entry Point"""
    if not check_admin_login():
        return
        
    tab1, tab2 = st.tabs(["✅ 승인 대기", "🗄️ 전체 데이터 조회"])
    
    with tab1:
        render_approval_queue()
        
    with tab2:
        render_data_explorer()



def render_guide_tab():
    """Tab 4: User Guide"""
    st.header("사용 가이드 (User Guide)")
    
    st.markdown("""
    ### 1. 데이터 업로드 (Excel Upload)
    본 시스템은 **사내 서버**에서 독립적으로 운영되며, 엑셀 파일 업로드 방식으로 데이터를 관리합니다.
    
    **[엔지니어]**
    1. **[데이터 업로드]** 탭으로 이동합니다.
    2. 작업 완료 후 생성된 엑셀 파일(.xlsx)을 업로드합니다.
    3. **[데이터 제출하기]** 버튼을 클릭합니다.
    4. 관리자 승인을 기다립니다.
    
    **[관리자]**
    1. **[관리자]** 탭으로 이동합니다.
    2. 관리자 비밀번호를 입력합니다.
    3. 대기 중인 데이터를 검토하고 [승인] 또는 [반려]합니다.
    4. 승인된 데이터만 대시보드에 표시됩니다.
    
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


def main():
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
    tab_explorer, tab_analysis, tab_data, tab_admin, tab_guide = st.tabs([
        "📊 장비 현황", "📈 Control Chart", "� 데이터 업로드", "🔒 관리자", "📖 사용 가이드"
    ])
    
    with tab_explorer:
        render_explorer_tab()
        
    with tab_analysis:
        render_analysis_tab()
        
    with tab_data:
        render_data_tab()
    
    with tab_admin:
        render_admin_tab()

    with tab_guide:
        render_guide_tab()

if __name__ == "__main__":
    main()
