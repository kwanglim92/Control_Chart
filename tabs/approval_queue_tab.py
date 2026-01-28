"""
승인 대기 탭
Approval Queue Tab
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from modules import database as db
from modules import utils
from config import (
    EQUIPMENT_OPTIONS, 
    get_xy_scanner_options, 
    get_head_type_options, 
    get_mod_vit_options, 
    get_sliding_stage_options, 
    get_sample_chuck_options, 
    get_ae_options
)

def render_approval_queue_tab():
    """승인 대기 탭 렌더링"""
    st.subheader("📋 승인 대기 검증")
    
    # DB에서 대기 중인 장비 목록 조회
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
        # UTC to KST conversion (UTC+9)
        try:
            utc_time = pd.to_datetime(row['uploaded_at'])
            kst_time = utc_time + pd.Timedelta(hours=9)
            time_str = kst_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            time_str = str(row['uploaded_at'])
            
        label = f"[{time_str}] {row['equipment_name']} ({row['sid']}) - {row['model']}"
        sid_options[label] = row['id']
    
    selected_label = st.selectbox(
        "SID 선택",
        options=list(sid_options.keys()),
        key="selected_sid_label_queue"
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
    # 1. 먼저 Staging 테이블(pending_measurements)에서 조회
    measurements_data = db.get_pending_measurements(selected_row['sid'])
    
    # 2. 없으면 기존 방식(measurements 테이블)으로 조회 (Legacy Support)
    if measurements_data.empty:
        measurements_data = db.get_measurements_by_sid(selected_row['sid'], status='pending')
    else:
        # 컬럼 순서 재배치 (UI 일관성)
        desired_order = [
            'Category', 'Check Items', 'Min', 'Criteria', 'Max', 
            'Measurement', 'Unit', 'PASS/FAIL', 'Trend', 'Remark', 
            'status', 'sid', 'equipment_name', 'id'
        ]
        existing_cols = [col for col in desired_order if col in measurements_data.columns]
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
        "📄 원본 데이터 (Raw)", 
        "📊 측정 데이터 (Trend)", 
        "📝 수정 사항"
    ])
    
    # --- Tab 1: Equipment Info ---
    with tab1:
        st.markdown("**장비 정보 (편집 가능)**")
        st.caption("🔒 SID, Model, 종료일은 수정할 수 없습니다.")
        
        df_equipment = pd.DataFrame([equipment_data])
        
        edited_equipment_df = st.data_editor(
            df_equipment,
            disabled=['id', 'SID', 'Model', '종료일'],
            column_config={
                'id': None,
                'SID': st.column_config.TextColumn('SID', disabled=True),
                '장비명': st.column_config.TextColumn('장비명'),
                '종료일': st.column_config.TextColumn('종료일', disabled=True),
                'R/I': st.column_config.SelectboxColumn(
                    'R/I', options=['Research', 'Industrial'], required=True
                ),
                'Model': st.column_config.TextColumn('Model', disabled=True),
                'XY Scanner': st.column_config.SelectboxColumn(
                    'XY Scanner', options=get_xy_scanner_options(), required=True
                ),
                'Head Type': st.column_config.SelectboxColumn(
                    'Head Type', options=get_head_type_options(), required=True
                ),
                'MOD/VIT': st.column_config.SelectboxColumn(
                    'MOD/VIT', options=get_mod_vit_options(), required=True
                ),
                'Sliding Stage': st.column_config.SelectboxColumn(
                    'Sliding Stage', options=get_sliding_stage_options(), required=True
                ),
                'Sample Chuck': st.column_config.SelectboxColumn(
                    'Sample Chuck', options=get_sample_chuck_options(), required=True
                ),
                'AE': st.column_config.SelectboxColumn(
                    'AE', options=get_ae_options(), required=True
                ),
                'End User': st.column_config.TextColumn('고객사 (End User)'),
                'Mfg Engineer': st.column_config.TextColumn('제조 담당'),
                'QC Engineer': st.column_config.TextColumn('QC 담당'),
                'Reference Doc': st.column_config.TextColumn('참조 문서 (Checklist)'),
            },
            use_container_width=True,
            hide_index=True,
            key=f"equipment_editor_{equipment_id}"
        )
        
        edited_equipment_data = edited_equipment_df.iloc[0].to_dict()
    
    # --- Tab 2: Raw Data ---
    with tab_raw:
        st.markdown("**원본 데이터 (Read-only)**")
        st.caption("💡 업로드된 엑셀의 모든 컬럼 정보입니다.")
        
        full_raw_data = db.get_full_measurements(selected_row['sid'])
        
        if not full_raw_data.empty:
            st.dataframe(
                full_raw_data,
                use_container_width=True,
                height=500,
                hide_index=True,
                column_config={
                    "Measurement": st.column_config.TextColumn("Measurement", width="medium"),
                    "Remark": st.column_config.TextColumn("Remark", width="large"),
                }
            )
        else:
            st.warning("⚠️ 원본 데이터가 보관되어 있지 않습니다.")
            
    # --- Tab 3: Measurements ---
    with tab3:
        st.markdown("**측정 데이터 (Value 편집 가능)**")
        st.caption("⚠️ 측정값 수정은 신중히 진행하세요.")
        
        # Reset Counter
        if f'reset_counter_{equipment_id}' not in st.session_state:
            st.session_state[f'reset_counter_{equipment_id}'] = 0
        
        edited_measurements = st.data_editor(
            measurements_data,
            disabled=['sid', 'check_items', 'equipment_name', 'Category', 'Check Items', 'Min', 'Criteria', 'Max', 'Unit', 'PASS/FAIL', 'Trend', 'Remark'],
            column_config={
                'id': None, 'sid': None, 'equipment_name': None, 'status': None,
                'Category': st.column_config.TextColumn('Category', disabled=True),
                'Check Items': st.column_config.TextColumn('Check Items', disabled=True),
                'Measurement': st.column_config.NumberColumn(
                    'Measurement', help="측정값 (편집 가능)", format="%.4f", required=True
                ),
                # Legacy compatibility
                'value': st.column_config.NumberColumn('Measurement', format="%.4f", required=True),
            },
            use_container_width=True,
            height=400,
            key=f"measurements_editor_{equipment_id}_{st.session_state[f'reset_counter_{equipment_id}']}"
        )
        
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.info(f"📊 총 **{len(edited_measurements)}개** 측정 항목")
        with col_btn:
            if st.button("🔄 원본으로 초기화", key=f"reset_btn_{equipment_id}", use_container_width=True):
                st.session_state[f'reset_counter_{equipment_id}'] += 1
                st.rerun()
                
    # --- Tab 4: Changes ---
    with tab4:
        st.markdown("**변경 사항 요약**")
        
        eq_changes = utils.compare_dicts(equipment_data, edited_equipment_data)
        meas_changes = utils.compare_dataframes(measurements_data, edited_measurements)
        
        total_changes = len(eq_changes) + len(meas_changes)
        
        if total_changes == 0:
            st.success("✅ 변경된 항목이 없습니다.")
        else:
            st.warning(f"⚠️ 총 **{total_changes}**개 항목이 수정되었습니다!")
            
            if eq_changes:
                st.markdown("**📄 장비 정보 변경사항:**")
                st.dataframe(pd.DataFrame(eq_changes), use_container_width=True)
            
            if meas_changes:
                st.markdown("**📊 측정 데이터 변경사항:**")
                st.dataframe(pd.DataFrame(meas_changes), use_container_width=True)
                
    st.divider()
    
    # Step 3: Action Buttons
    st.markdown("### ✅ Step 3: 최종 확인 및 조치")
    
    col1, col2 = st.columns(2)
    with col1:
        # Excel Download
        original_excel = utils.create_original_excel(equipment_data, measurements_data)
        st.download_button(
            label="📥 원본 데이터 다운로드",
            data=original_excel,
            file_name=f"original_{selected_row['sid']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        if total_changes > 0:
            modified_excel = utils.create_modified_excel(
                equipment_data, edited_equipment_data,
                measurements_data, edited_measurements
            )
            st.download_button(
                label="📥 수정본 다운로드 (변경 이력 포함) ⭐",
                data=modified_excel,
                file_name=f"modified_{selected_row['sid']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )
            
    with col2:
        admin_name = st.text_input("관리자 이름", placeholder="예: 홍길동", key=f"admin_name_{equipment_id}")
        
    st.divider()
    
    col_approve, col_reject = st.columns(2)
    
    with col_approve:
        if st.button("✅ 승인 (수정사항 반영)", type="primary", use_container_width=True, key=f"approve_{equipment_id}"):
            # DB 업데이트
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Equipment Update
            cursor.execute("""
                UPDATE equipments
                SET equipment_name=?, ri=?, xy_scanner=?, head_type=?, mod_vit=?,
                    sliding_stage=?, sample_chuck=?, ae=?, end_user=?,
                    mfg_engineer=?, qc_engineer=?, reference_doc=?, status='approved'
                WHERE id=?
            """, (
                edited_equipment_data['장비명'], edited_equipment_data['R/I'], 
                edited_equipment_data['XY Scanner'], edited_equipment_data['Head Type'], 
                edited_equipment_data['MOD/VIT'], edited_equipment_data['Sliding Stage'],
                edited_equipment_data['Sample Chuck'], edited_equipment_data['AE'], 
                edited_equipment_data['End User'], edited_equipment_data['Mfg Engineer'], 
                edited_equipment_data['QC Engineer'], edited_equipment_data['Reference Doc'],
                equipment_id
            ))
            
            # Measurements Update
            for idx, row in edited_measurements.iterrows():
                val = row.get('Measurement') if 'Measurement' in row else row.get('value')
                check_item = row.get('Check Items') if 'Check Items' in row else row.get('check_items')
                
                # Update both tables (pending and legacy measurements)
                cursor.execute("""
                    UPDATE pending_measurements SET value=?, status='approved'
                    WHERE sid=? AND check_items=? AND status='pending'
                """, (val, selected_row['sid'], check_item))
                
                cursor.execute("""
                    UPDATE measurements SET value=?, status='approved'
                    WHERE sid=? AND check_items=? AND status='pending'
                """, (val, selected_row['sid'], check_item))
            
            conn.commit()
            conn.close()
            
            # Log History
            db.log_approval_history(
                sid=selected_row['sid'],
                equipment_id=equipment_id,
                action='approved',
                admin_name=admin_name,
                reason=f"승인 완료 (수정 {total_changes}건)" if total_changes > 0 else "승인 완료",
                previous_status='pending',
                new_status='approved',
                modification_count=total_changes
            )
            
            st.success(f"✅ {selected_row['sid']} 승인 완료! (수정 {total_changes}건)")
            st.balloons()
            st.rerun()
            
    with col_reject:
        with st.expander("❌ 반려하기"):
            reject_reason = st.text_area("반려 사유 (필수)", key=f"reject_reason_{equipment_id}")
            if st.button("❌ 반려 확정", type="secondary", use_container_width=True, key=f"reject_confirm_{equipment_id}"):
                if not reject_reason.strip():
                    st.error("사유를 입력해주세요.")
                else:
                    db.reject_equipment(equipment_id, reason=reject_reason, admin_name=admin_name)
                    db.log_approval_history(
                        sid=selected_row['sid'],
                        equipment_id=equipment_id,
                        action='rejected',
                        admin_name=admin_name,
                        reason=reject_reason,
                        previous_status='pending',
                        new_status='rejected',
                        modification_count=total_changes
                    )
                    st.warning("❌ 반려되었습니다.")
                    st.rerun()
