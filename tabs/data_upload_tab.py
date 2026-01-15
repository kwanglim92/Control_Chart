"""
Excel Upload Tab - Checklist Parser UI
체크리스트 엑셀 파일 업로드 및 파싱 UI
"""
import streamlit as st
import pandas as pd
from datetime import datetime

# This function will be imported in app.py
def render_upload_tab(extract_func, insert_func, sync_func, equipment_options, industrial_models, check_status_func=None, log_history_func=None):
    """
    Render the upload tab with 4-step process
    
    Args:
        extract_func: extract_equipment_info_from_last_sheet function
        insert_func: db.insert_equipment_from_excel function
        sync_func: sync_data_from_local function
        equipment_options: EQUIPMENT_OPTIONS dict
        industrial_models: INDUSTRIAL_MODELS list
        check_status_func: db.get_equipment_status function (optional)
        log_history_func: db.log_approval_history function (optional)
    """
    st.header("📤 체크리스트 업로드 (Checklist Upload)")
    
    # Auto-load message
    if 'auto_load_msg' in st.session_state:
        if '✅' in st.session_state.auto_load_msg:
            st.success(st.session_state.auto_load_msg)
        else:
            st.warning(st.session_state.auto_load_msg)
        del st.session_state.auto_load_msg
    
    st.markdown("""
    **현장 엔지니어 전용**  
    작업 완료 후 체크리스트 엑셀 파일을 업로드해주세요.  
    장비 기본 정보는 **Last 시트에서 자동 추출**되며, 추가 사양만 입력하시면 됩니다.
    """)
    
    st.divider()
    
    # Step 1: File Upload
    st.subheader("📁 Step 1: 파일 업로드")
    uploaded_file = st.file_uploader("체크리스트 엑셀 파일 선택 (.xlsx)", type=['xlsx'], key='checklist_upload')
    
    if uploaded_file is not None:
        # Step 2: Auto-extract from Last sheet
        st.divider()
        st.subheader("✨ Step 2: 장비 정보 자동 추출")
        
        with st.spinner("Last 시트에서 정보 추출 중..."):
            auto_info = extract_func(uploaded_file)
        
        if auto_info:
            # Display extracted information
            col1, col2 = st.columns(2)
            with col1:
                st.success("✅ **자동 추출 완료!**")
                st.write(f"**Model**: {auto_info.get('model', 'N/A')}")
                st.write(f"**SID**: {auto_info.get('sid', 'N/A')}")
                st.write(f"**R/I**: {auto_info.get('ri', 'N/A')} (자동 판별)")
                st.write(f"**출고일**: {auto_info.get('date', 'N/A')}")
            with col2:
                st.info("ℹ️ **추가 정보**")
                st.write(f"**고객사**: {auto_info.get('end_user', 'N/A')}")
                st.write(f"**제조 담당**: {auto_info.get('mfg_engineer', 'N/A')}")
                st.write(f"**QC 담당**: {auto_info.get('qc_engineer', 'N/A')}")
                st.write(f"**체크리스트**: {auto_info.get('reference_doc', 'N/A')}")
            
            # Step 3: Select sheet with measurement data
            st.divider()
            st.subheader("📊 Step 3: 측정 데이터 시트 선택")
            
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file.sheet_names
                
                # Filter out non-data sheets
                excluded_sheets = ['표지', 'Last', '사용설명서', 'v3.21.1']  # Common info sheets
                data_sheets = [s for s in sheet_names if s not in excluded_sheets]
                
                if not data_sheets:
                    st.warning("측정 데이터 시트를 찾을 수 없습니다. 모든 시트를 표시합니다.")
                    data_sheets = sheet_names
                
                selected_sheet = st.radio(
                    "측정 데이터가 있는 시트를 선택하세요:",
                    data_sheets,
                    help="보통 모델명으로 된 시트입니다 (예: NX-Wafer)")
                
                if selected_sheet:
                    # Preview with scroll
                    with st.expander(f"📋 {selected_sheet} 시트 미리보기 (전체)"):
                        df_preview = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                        
                        # Remove Unnamed columns (empty columns in Excel)
                        unnamed_cols = [col for col in df_preview.columns if col.startswith('Unnamed')]
                        df_preview_clean = df_preview.drop(columns=unnamed_cols)
                        
                        st.dataframe(df_preview_clean, use_container_width=True, height=400)
                    
                    # Show filtered data
                    with st.expander(f"📊 필터링된 측정 데이터 (Trend & Measurement 존재)"):
                        filtered_preview = df_preview[
                            (df_preview['Trend'].notna()) & 
                            (df_preview['Measurement'].notna())
                        ]
                        if not filtered_preview.empty:
                            # Show key columns only (in logical order)
                            display_cols = ['Check Items', 'Trend', 'Measurement']
                            if 'Unit' in filtered_preview.columns:
                                display_cols.append('Unit')
                            if 'Category' in filtered_preview.columns:
                                display_cols.insert(0, 'Category')  # Add at beginning
                            if 'Remark' in filtered_preview.columns:
                                display_cols.append('Remark')
                            
                            st.dataframe(filtered_preview[display_cols], use_container_width=True, height=400)
                            st.success(f"✅ 총 **{len(filtered_preview)}**건의 측정 데이터가 추출됩니다.")
                        else:
                            st.warning("⚠️ 필터링된 데이터가 없습니다.")
                    
                    # Step 4: Required specifications
                    st.divider()
                    st.subheader("🔧 Step 4: 장비 사양 입력 (필수)")
                    
                    st.markdown("**모든 사양을 선택해주세요 (필수 항목):**")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # XY Scanner - 2-level
                        st.markdown("**XY Scanner**")
                        xy_category = st.selectbox(
                            "타입 선택",
                            list(equipment_options['xy_scanner'].keys()),
                            key='xy_cat'
                        )
                        xy_scanner = st.selectbox(
                            "상세 선택",
                            equipment_options['xy_scanner'][xy_category],
                            key='xy_detail'
                        )
                        
                        # Head Type - 2-level
                        st.markdown("**Head Type**")
                        head_category = st.selectbox(
                            "타입 선택",
                            list(equipment_options['head_type'].keys()),
                            key='head_cat'
                        )
                        head_type = st.selectbox(
                            "상세 선택",
                            equipment_options['head_type'][head_category],
                            key='head_detail'
                        )
                        
                        # MOD/VIT - 2-level
                        st.markdown("**MOD/VIT**")
                        mod_category = st.selectbox(
                            "타입 선택",
                            list(equipment_options['mod_vit'].keys()),
                            key='mod_cat'
                        )
                        mod_vit = st.selectbox(
                            "상세 선택",
                            equipment_options['mod_vit'][mod_category],
                            key='mod_detail'
                        )
                    
                    with col2:
                        # Sliding Stage - Simple (only 2 categories)
                        st.markdown("**Sliding Stage**")
                        stage_category = st.selectbox(
                            "타입 선택",
                            list(equipment_options['sliding_stage'].keys()),
                            key='stage_cat'
                        )
                        sliding_stage = st.selectbox(
                            "상세 선택",
                            equipment_options['sliding_stage'][stage_category],
                            key='stage_detail'
                        )
                        
                        # Sample Chuck - 2-level
                        st.markdown("**Sample Chuck**")
                        chuck_category = st.selectbox(
                            "타입 선택",
                            list(equipment_options['sample_chuck'].keys()),
                            key='chuck_cat'
                        )
                        sample_chuck = st.selectbox(
                            "상세 선택",
                            equipment_options['sample_chuck'][chuck_category],
                            key='chuck_detail'
                        )
                        
                        # AE Type - Based on R/I
                        st.markdown("**AE Type**")
                        ri_type = auto_info.get('ri', 'Research')
                        ae_options = equipment_options['ae'].get(ri_type, equipment_options['ae']['Research'])
                        ae = st.selectbox(f"AE Type ({ri_type})", ae_options, key='ae_detail')
                    
                    
                    # Equipment name - auto-fill with end user, editable
                    default_equipment_name = auto_info.get('end_user', '')
                    if not default_equipment_name:
                        # Fallback to model + SID if no end_user
                        default_equipment_name = f"{auto_info.get('model', '')} #{auto_info.get('sid', '')[-6:]}" if auto_info.get('sid') else ""
                    
                    equipment_name = st.text_input(
                        "장비명 (필요시 수정)", 
                        value=default_equipment_name,
                        help="고객사명이 자동으로 입력됩니다. 필요시 수정하세요."
                    )
                    
                    st.divider()
                    
                    # Validation and Submit
                    if st.button("✅ 데이터 추출 및 제출", type="primary", use_container_width=True):
                        # Validate equipment name (required field)
                        if not equipment_name or equipment_name.strip() == "":
                            st.error("⚠️ 장비명을 입력해주세요!")
                        else:
                            # --- Status Check Logic ---
                            can_proceed = True
                            sid_to_check = auto_info.get('sid', '')
                            
                            if check_status_func and sid_to_check:
                                current_status = check_status_func(sid_to_check)
                                
                                if current_status == 'approved':
                                    st.error(f"⛔ **업로드 불가**: SID '{sid_to_check}' 장비는 이미 승인 완료되었습니다. 수정이 필요하면 관리자에게 문의하세요.")
                                    can_proceed = False
                                    
                                elif current_status == 'rejected':
                                    st.info(f"🔄 **재제출**: 반려된 장비('{sid_to_check}')의 수정 데이터입니다. 재제출 이력이 기록됩니다.")
                                    if log_history_func:
                                        log_history_func(
                                            sid=sid_to_check, 
                                            action='resubmitted', 
                                            reason='User re-uploaded corrected data',
                                            previous_status='rejected',
                                            new_status='pending'
                                        )
                                        
                                elif current_status == 'pending':
                                    st.warning(f"⚠️ **덮어쓰기**: SID '{sid_to_check}' 장비는 이미 대기 중입니다. 기존 데이터를 덮어쓰고 갱신합니다.")
                            
                            if can_proceed:
                                # Process data
                                with st.spinner("데이터 추출 및 저장 중..."):
                                    try:
                                        # Read measurement data
                                        df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
                                        
                                        # Filter: Trend and Measurement both present
                                        filtered = df[
                                            (df['Trend'].notna()) & 
                                            (df['Measurement'].notna())
                                        ].copy()
                                    
                                        if filtered.empty:
                                            st.error("❌ Trend와 Measurement가 모두 있는 데이터가 없습니다.")
                                        else:
                                            # Create Equipment DataFrame (1 row)
                                            df_equipment = pd.DataFrame([{
                                                'SID': auto_info.get('sid', ''),
                                                '장비명': equipment_name,
                                                '종료일': auto_info.get('date', ''),
                                                'R/I': auto_info.get('ri', ''),
                                                'Model': auto_info.get('model', ''),
                                                'XY Scanner': xy_scanner,
                                                'Head Type': head_type,
                                                'MOD/VIT': mod_vit,
                                                'Sliding Stage': sliding_stage,
                                                'Sample Chuck': sample_chuck,
                                                'AE': ae,
                                                'End User': auto_info.get('end_user', ''),
                                                'Mfg Engineer': auto_info.get('mfg_engineer', ''),
                                                'QC Engineer': auto_info.get('qc_engineer', ''),
                                                'Reference Doc': auto_info.get('reference_doc', '')
                                            }])
                                            
                                            # Create Measurements DataFrame (N rows)
                                            # Pass ALL rows (including non-Trend rows) to pending_measurements
                                            # measurements table will filter automatically in insert_equipment_from_excel
                                            df_measurements = df.copy()  # Use complete data, not filtered
                                            df_measurements['SID'] = auto_info.get('sid', '')
                                            df_measurements['장비명'] = equipment_name
                                            # Ensure required columns for legacy support
                                            if 'Check Items' not in df_measurements.columns and 'check_items' in df_measurements.columns:
                                                df_measurements['Check Items'] = df_measurements['check_items']
                                            if 'Value' not in df_measurements.columns and 'Measurement' in df_measurements.columns:
                                                df_measurements['Value'] = df_measurements['Measurement']
                                            
                                            # Insert to DB with status='pending'
                                            counts = insert_func(df_equipment, df_measurements)
                                            
                                            st.success(f"""
                                            ✅ **제출 완료!**
                                            
                                            - 장비: {counts['equipments']}대
                                            - 측정값: {counts['measurements']}건
                                            - SID: {auto_info.get('sid', '')}
                                            
                                            관리자 승인 대기 목록에 추가되었습니다.
                                            """)
                                            
                                            # Clear the uploader (requires page refresh)
                                            st.info("새로운 파일을 업로드하려면 페이지를 새로고침하세요.")
                                    
                                    except Exception as e:
                                        st.error(f"❌ 처리 실패: {str(e)}")
                                        import traceback
                                        st.code(traceback.format_exc())
            
            except Exception as e:
                st.error(f"엑셀 파일 읽기 실패: {str(e)}")
        else:
            st.error("⚠️ Last 시트에서 정보를 추출할 수 없습니다.")
            
            # Show diagnostic information
            with st.expander("🔍 진단 정보 (디버깅용)"):
                try:
                    excel_file = pd.ExcelFile(uploaded_file)
                    st.write("**파일 내 시트 목록:**")
                    st.write(excel_file.sheet_names)
                    
                    if 'Last' in excel_file.sheet_names:
                        st.write("**Last 시트가 존재합니다!**")
                        df_last = pd.read_excel(uploaded_file, sheet_name='Last', header=None)
                        st.write(f"Last 시트 크기: {df_last.shape}")
                        st.write("**Last 시트 내용 (처음 40행):**")
                        st.dataframe(df_last.head(40))
                        
                        # Check specific rows
                        st.write("**확인된 데이터:**")
                        if len(df_last) > 21:
                            st.write(f"Row 21 (Model): {df_last.iloc[21].tolist()}")
                        if len(df_last) > 24:
                            st.write(f"Row 24 (SID): {df_last.iloc[24].tolist()}")
                    else:
                        st.error("❌ Last 시트가 없습니다!")
                        st.write("파일에 'Last' 시트를 추가해주세요.")
                except Exception as diag_e:
                    st.error(f"진단 실패: {str(diag_e)}")
    
    # Section for local file sync (for admin)
    with st.expander("🔧 관리자: 로컬 파일 동기화"):
        st.info("""
        **관리자 전용**  
        프로젝트 루트의 `data.xlsx` 파일을 읽어 데이터를 갱신합니다.  
        이 방식으로 로드된 데이터는 **즉시 승인 상태**로 대시보드에 표시됩니다.
        """)
        
        if st.button("🔄 로컬 데이터 동기화 실행", use_container_width=True, key='local_sync'):
            with st.spinner("data.xlsx 파일 읽는 중..."):
                sync_func()
