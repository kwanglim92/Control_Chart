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
from modules import database as db
import importlib
importlib.reload(db) # Force reload to apply changes

from modules.utils import (
    load_data, clean_data, normalize_check_items_column,
    add_date_columns, build_display_map, normalize_key,
    calculate_stats, RESEARCH_MODELS, INDUSTRIAL_MODELS
)
from modules import charts  # 전체 모듈 임포트 (charts.plot_sunburst_chart 사용 위함)
from modules.charts import create_control_chart, create_individual_chart
from modules.monthly_shipment import (
    aggregate_monthly_shipments,
    create_monthly_shipment_chart,
    show_shipment_stats
)

# === Config ===
from config import (
    EQUIPMENT_OPTIONS,
    get_xy_scanner_options,
    get_head_type_options,
    get_mod_vit_options,
    get_sliding_stage_options,
    get_sample_chuck_options,
    get_ae_options
)

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
    data_file_path = os.path.join(os.path.dirname(__file__), 'data', 'data.xlsx')
    if os.path.exists(data_file_path):
        try:
            # Read all 3 sheets
            df_equip = pd.read_excel(data_file_path, sheet_name='Equipments')
            df_meas = pd.read_excel(data_file_path, sheet_name='Measurements')
            try:
                df_specs = pd.read_excel(data_file_path, sheet_name='Specs')
            except:
                df_specs = None
            
            # Check if DB is already populated to avoid overwriting pending data
            if db.get_equipment_count() == 0:
                # Use sync_relational_data which sets status='approved' by default
                result = db.sync_relational_data(df_equip, df_meas, df_specs)
                st.session_state.auto_load_msg = f"✅ 로컬 데이터 자동 로드 완료 (장비: {result['equipments']}대, 측정값: {result['measurements']}건)"
            else:
                st.session_state.auto_load_msg = "✅ 기존 데이터베이스 유지됨 (초기화 건너뜀)"
        except Exception as e:
            st.session_state.auto_load_msg = f"⚠️ 자동 로드 실패: {str(e)}"

# 세션 상태 초기화
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'analysis_triggered' not in st.session_state:
    st.session_state.analysis_triggered = False



def sync_data_from_local():
    """로컬 Excel 파일(data.xlsx)에서 데이터를 읽어 DB에 저장 (승인 상태로)"""
    data_file_path = os.path.join(os.path.dirname(__file__), 'data', 'data.xlsx')
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
        
    


def render_data_explorer():
    """Tab 4-3: Data Explorer with Right Sidebar Filter"""
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
    # --- Main Content ---
    with c_main:
        if df_equipments.empty:
            st.info("조건에 맞는 데이터가 없습니다.")
        else:
            st.markdown(f"총 **{len(df_equipments)}**건의 데이터가 검색되었습니다.")
            
            # 장비 선택 (Selectbox)
            equip_options = {
                f"[{row['status'].upper()}] {row['equipment_name']} ({row['sid']})": row['sid'] 
                for _, row in df_equipments.iterrows()
            }
            
            equip_keys = list(equip_options.keys())
            selected_equip_label = st.selectbox(
                "장비 선택", 
                equip_keys,
                index=0 if equip_keys else None
            )
            
            if not selected_equip_label:
                st.warning("장비를 선택해주세요.")
                return
            
            
            selected_sid = equip_options.get(selected_equip_label)
            
            st.divider()
            if selected_sid:
                st.markdown(f"### 📄 상세 데이터: `{selected_sid}`")
            else:
                st.markdown(f"### 📄 상세 데이터: `{selected_equip_label}`")
                st.warning("⚠️ 이 장비는 SID가 할당되지 않았습니다. '정보 수정' 버튼을 눌러 SID를 입력하세요.")
            
            
            # 장비 기본 정보
            with st.expander("ℹ️ 장비 기본 정보 (편집 가능)", expanded=False):
                # SID가 있으면 SID로 필터링, 없으면 선택한 label의 장비명으로 찾기
                if selected_sid:
                    filtered_equip = df_equipments[df_equipments['sid'] == selected_sid]
                else:
                    # Extract equipment name from label (format: "[STATUS] Equipment Name (SID)")
                    # When SID is None, format is "[STATUS] Equipment Name (None)"
                    import re
                    match = re.search(r'\] (.+) \(', selected_equip_label)
                    if match:
                        equip_name = match.group(1)
                        filtered_equip = df_equipments[df_equipments['equipment_name'] == equip_name]
                    else:
                        filtered_equip = pd.DataFrame()
                
                if not filtered_equip.empty:
                    equip_info = filtered_equip.iloc[0].to_dict()
                    
                    # 편집 모드 토글
                    edit_eq_key = f"edit_eq_{equip_info['id']}"
                    if edit_eq_key not in st.session_state:
                        st.session_state[edit_eq_key] = False
                        
                    c_title, c_edit = st.columns([4, 1])
                    with c_title:
                        st.subheader(f"{equip_info['equipment_name']}")
                    with c_edit:
                        if st.button("✏️ 정보 수정", key=f"btn_eq_{equip_info['id']}"):
                            st.session_state[edit_eq_key] = not st.session_state[edit_eq_key]
                    
                    if st.session_state[edit_eq_key]:
                        # --- EDIT MODE ---
                        st.info("⚠️ SID 변경 시 주의: 기존 측정 데이터와의 연결이 끊어질 수 있습니다.")
                        new_sid = st.text_input("SID (장비 고유 번호)", equip_info.get('sid') or "", key=f"in_eq_sid_{equip_info['id']}")
                        
                        # 확장된 필드들 제공
                        new_eq_name = st.text_input("장비명", equip_info['equipment_name'], key=f"in_eq_name_{equip_info['id']}")
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            new_ri = st.selectbox("R/I", ['Research', 'Industrial'], index=0 if equip_info['ri'] == 'Research' else 1, key=f"in_eq_ri_{equip_info['id']}")
                            new_scanner = st.selectbox("XY Scanner", get_xy_scanner_options(), index=0 if not equip_info['xy_scanner'] else None, key=f"in_eq_sc_{equip_info['id']}")
                            new_head = st.selectbox("Head Type", get_head_type_options(), index=0 if not equip_info['head_type'] else None, key=f"in_eq_hd_{equip_info['id']}")
                        
                        with col_e2:
                            new_mod = st.selectbox("MOD/VIT", get_mod_vit_options(), index=0 if not equip_info['mod_vit'] else None, key=f"in_eq_mv_{equip_info['id']}")
                            new_stage = st.selectbox("Sliding Stage", get_sliding_stage_options(), key=f"in_eq_ss_{equip_info['id']}")
                            new_chuck = st.selectbox("Sample Chuck", get_sample_chuck_options(), key=f"in_eq_sc2_{equip_info['id']}")
                        
                        new_ae = st.selectbox("AE", get_ae_options(), key=f"in_eq_ae_{equip_info['id']}")
                        
                        st.markdown("---")
                        st.markdown("**추가 정보**")
                        col_a1, col_a2 = st.columns(2)
                        with col_a1:
                            new_end_user = st.text_input("End User", equip_info.get('end_user') or "", key=f"in_eq_eu_{equip_info['id']}")
                            new_mfg = st.text_input("Mfg Engineer", equip_info.get('mfg_engineer') or "", key=f"in_eq_mfg_{equip_info['id']}")
                        with col_a2:
                            new_qc = st.text_input("QC Engineer", equip_info.get('qc_engineer') or "", key=f"in_eq_qc_{equip_info['id']}")
                            new_ref = st.text_input("Ref Doc", equip_info.get('reference_doc') or "", key=f"in_eq_ref_{equip_info['id']}")

                        if st.button("💾 저장", key=f"save_eq_{equip_info['id']}"):
                            updates = {
                                'sid': new_sid,
                                'equipment_name': new_eq_name,
                                'ri': new_ri,
                                'xy_scanner': new_scanner,
                                'head_type': new_head,
                                'mod_vit': new_mod,
                                'sliding_stage': new_stage,
                                'sample_chuck': new_chuck,
                                'ae': new_ae,
                                'end_user': new_end_user,
                                'mfg_engineer': new_mfg,
                                'qc_engineer': new_qc,
                                'reference_doc': new_ref
                            }
                            db.update_equipment(equip_info['id'], updates)
                            st.success("저장되었습니다.")
                            st.session_state[edit_eq_key] = False
                            st.rerun()
                    else:
                        # --- VIEW MODE ---
                        st.json(equip_info)

            # 측정 데이터
            with st.expander("📊 측정 데이터 (값 수정 가능)", expanded=True):
                # Status에 따라 다른 테이블 조회
                if equip_info.get('status') == 'pending':
                    # Pending 상태면 pending_measurements 테이블 조회
                    # SID가 없으면 장비명으로 조회
                    if selected_sid:
                        raw_data = db.get_pending_measurements(selected_sid)
                    else:
                        # Fallback: query by equipment name
                        conn = db.get_connection()
                        query = "SELECT * FROM pending_measurements WHERE equipment_name = ?"
                        raw_data = pd.read_sql_query(query, conn, params=(equip_info['equipment_name'],))
                        conn.close()
                    
                    if not raw_data.empty:
                        st.info("💡 승인 대기 중인 데이터입니다. (pending_measurements 테이블)")
                        
                        edited_pending = st.data_editor(
                            raw_data,
                            column_config={
                                "check_items": st.column_config.TextColumn("Check Item", disabled=True),
                                "value": st.column_config.NumberColumn("Value", required=True)
                            },
                            disabled=["id", "sid", "equipment_name", "category", "check_items", "min_value", "criteria", "max_value", "unit", "pass_fail", "trend", "remark", "status"],
                            use_container_width=True,
                            hide_index=True,
                            key=f"pending_editor_{equip_info['id']}"
                        )
                        
                        if not raw_data.equals(edited_pending):
                            if st.button("💾 변경사항 저장 (대기 데이터)", type="primary", key=f"save_pending_{equip_info['id']}"):
                                conn = db.get_connection()
                                cur = conn.cursor()
                                for idx, row in edited_pending.iterrows():
                                    if row['value'] != raw_data.iloc[idx]['value']:
                                        cur.execute(
                                            "UPDATE pending_measurements SET value = ? WHERE id = ?", 
                                            (row['value'], row['id'])
                                        )
                                conn.commit()
                                conn.close()
                                st.success("저장되었습니다.")
                                st.rerun()
                    else:
                        st.info("데이터가 없습니다.")
                else:
                    # Approved data
                    # Query measurements by equipment_id (equipment_name is NULL in DB)
                    conn = db.get_connection()
                    equip_id = equip_info.get('id')
                    if equip_id:
                        query = "SELECT * FROM measurements WHERE equipment_id = ?"
                        raw_data = pd.read_sql_query(query, conn, params=(equip_id,))
                    elif selected_sid:
                        # Fallback: try by SID
                        query = "SELECT * FROM measurements WHERE sid = ?"
                        raw_data = pd.read_sql_query(query, conn, params=(selected_sid,))
                    else:
                        raw_data = pd.DataFrame()
                    conn.close()
                    
                    if not raw_data.empty:
                        edited_df = st.data_editor(
                            raw_data,
                            key=f"data_editor_{equip_info['id']}_approved",
                            column_config={
                                "value": st.column_config.NumberColumn("Value", help="측정값 수정"),
                                "check_item": st.column_config.TextColumn("Check Item", disabled=True),
                            },
                            disabled=["id", "sid", "equipment_name", "status"],
                            hide_index=True, 
                            use_container_width=True
                        )
                        
                        if st.button("💾 측정 데이터 저장", key=f"save_meas_{equip_info['id']}"):
                             conn = db.get_connection()
                             c = conn.cursor()
                             for idx, row in edited_df.iterrows():
                                 c.execute("UPDATE measurements SET value = ? WHERE id = ?", (row['value'], row['id']))
                             conn.commit()
                             conn.close()
                             st.success("저장되었습니다.")
                    else:
                        st.info("데이터가 없습니다.")

def render_data_maintenance():
    """Tab 4-4: Data Maintenance and Migration Tools"""
    st.subheader("🔧 데이터 관리")
    
    st.info("이 탭에서는 데이터베이스 일관성을 관리하고 레거시 데이터를 정리할 수 있습니다.")
    
    # Get current migration status
    status = db.get_migration_status()
    
    # Display status cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 측정 데이터", f"{status['total_measurements']:,}건")
    
    with col2:
        if status['null_equipment_name'] > 0:
            st.metric("누락된 장비명", f"{status['null_equipment_name']:,}건", delta="수정 필요", delta_color="inverse")
        else:
            st.metric("누락된 장비명", "0건 ✓")
    
    with col3:
        if status['null_sid'] > 0:
            st.metric("누락된 SID", f"{status['null_sid']:,}건", delta="수정 필요", delta_color="inverse")
        else:
            st.metric("누락된 SID", "0건 ✓")
    
    with col4:
        if status['mismatched_status'] > 0:
            st.metric("상태 불일치", f"{status['mismatched_status']:,}건", delta="수정 필요", delta_color="inverse")
        else:
            st.metric("상태 불일치", "0건 ✓")
    
    st.divider()
    
    # Migration actions
    st.subheader("📦 데이터 마이그레이션")
    
    total_issues = status['null_equipment_name'] + status['null_sid'] + status['mismatched_status']
    
    if total_issues > 0:
        st.warning(f"⚠️ 총 {total_issues:,}건의 데이터 불일치가 발견되었습니다.")
        
        with st.expander("📋 상세 정보", expanded=False):
            st.markdown(f"""
**문제 유형:**
- **장비명 누락**: {status['null_equipment_name']:,}건 - `measurements.equipment_name`이 NULL
- **SID 누락**: {status['null_sid']:,}건 - `measurements.sid`가 NULL  
- **상태 불일치**: {status['mismatched_status']:,}건 - 승인된 장비의 측정 데이터가 여전히 'pending' 상태

**해결 방법:**
아래 "데이터 동기화 실행" 버튼을 클릭하면 `equipments` 테이블의 값을 기준으로 `measurements` 테이블을 업데이트합니다.
            """)
        
        if st.button("🔄 데이터 동기화 실행", type="primary", key="run_migration"):
            with st.spinner("데이터 동기화 중..."):
                result = db.sync_denormalized_columns()
            
            st.success(f"""
✅ 동기화 완료!
- 장비명 업데이트: {result['equipment_name']:,}건
- SID 업데이트: {result['sid']:,}건
- 상태 업데이트: {result['status']:,}건
            """)
            st.rerun()
    else:
        st.success("✅ 모든 데이터가 일관성 있게 유지되고 있습니다.")
    
    st.divider()
    
    # SID 없는 장비 조회
    st.subheader("🔍 SID 미할당 장비 조회")
    
    conn = db.get_connection()
    no_sid_equip = pd.read_sql_query("""
        SELECT id, equipment_name, model, status, uploaded_at 
        FROM equipments 
        WHERE sid IS NULL OR sid = ''
        ORDER BY uploaded_at DESC
    """, conn)
    conn.close()
    
    if not no_sid_equip.empty:
        st.warning(f"⚠️ SID가 없는 장비: {len(no_sid_equip)}건")
        st.dataframe(no_sid_equip, use_container_width=True, hide_index=True)
        st.info("💡 '전체 데이터 조회' 탭에서 개별 장비의 SID를 수정할 수 있습니다.")
    else:
        st.success("✅ 모든 장비에 SID가 할당되어 있습니다.")


def render_admin_tab():
    """Tab 4: Admin Mode - Main Entry Point"""
    from modules.auth import render_admin_login
    
    if not render_admin_login():
        return
    
    # Import modular tab renderers
    from tabs.monthly_dashboard_tab import render_monthly_dashboard_tab
    from tabs.approval_queue_tab import render_approval_queue_tab
    
    # 4개 탭으로 분리
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 승인 대기",
        "📊 월별 출하 현황",
        "🗄️ 전체 데이터 조회",
        "🔧 데이터 관리"
    ])
    
    with tab1:
        render_approval_queue_tab()
    
    with tab2:
        render_monthly_dashboard_tab()
        
    with tab3:
        render_data_explorer()
    
    with tab4:
        render_data_maintenance()



def main():
    # Import modular tab renderers
    from tabs import (
        render_guide_tab, 
        render_upload_tab, 
        render_equipment_explorer_tab,
        render_quality_analysis_tab
    )
    
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
        render_equipment_explorer_tab()
        
    with tab_analysis:
        render_quality_analysis_tab()
        
    with tab_data:
        render_upload_tab(
            extract_func=extract_equipment_info_from_last_sheet,
            insert_func=db.insert_equipment_from_excel,
            sync_func=sync_data_from_local,
            equipment_options=EQUIPMENT_OPTIONS,
            industrial_models=INDUSTRIAL_MODELS,
            check_status_func=db.get_equipment_status,
            log_history_func=db.log_approval_history
        )
    
    with tab_admin:
        render_admin_tab()

    with tab_guide:
        render_guide_tab()

if __name__ == "__main__":
    main()
