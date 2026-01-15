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
from monthly_shipment import (
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
                    
                    st.warning(f"❌ {selected_row['sid']} 반려 완료.\\n\\n**사유**: {reject_reason}")
                    st.rerun()


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
            
            selected_equip_label = st.selectbox("장비 선택", list(equip_options.keys()))
            
            if selected_equip_label:
                selected_sid = equip_options[selected_equip_label]
                
                st.divider()
                st.markdown(f"### 📄 상세 데이터: `{selected_sid}`")
                
                # 장비 기본 정보
                with st.expander("ℹ️ 장비 기본 정보", expanded=False):
                    filtered_equip = df_equipments[df_equipments['sid'] == selected_sid]
                    if not filtered_equip.empty:
                        equip_info = filtered_equip.iloc[0]
                        st.json(equip_info.to_dict())
                
                # 측정 데이터
                with st.expander("📊 측정 데이터", expanded=True):
                    trend_data = db.get_pending_measurements(selected_sid)
                    if not trend_data.empty:
                        st.dataframe(trend_data, use_container_width=True, hide_index=True)
                        st.info(f"📊 총 **{len(trend_data)}개** 항목")


def render_admin_tab():
    """Tab 4: Admin Mode - Main Entry Point"""
    from modules.auth import render_admin_login
    
    if not render_admin_login():
        return
    
    # Import modular tab renderers
    from tabs.monthly_dashboard_tab import render_monthly_dashboard_tab
    from tabs.approval_queue_tab import render_approval_queue_tab
    
    # 3개 탭으로 분리
    tab1, tab2, tab3 = st.tabs([
        "📋 승인 대기",
        "📊 월별 출하 현황",
        "🗄️ 전체 데이터 조회"
    ])
    
    with tab1:
        render_approval_queue_tab()
    
    with tab2:
        render_monthly_dashboard_tab()
        
    with tab3:
        render_data_explorer()



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
