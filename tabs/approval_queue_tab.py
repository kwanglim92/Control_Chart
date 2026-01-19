"""
승인 대기 탭
Approval Queue Tab
"""
import streamlit as st
from modules import database as db

def render_approval_queue_tab():
    """승인 대기 탭 렌더링"""
    st.subheader("⏳ 승인 대기 목록")
    
    # DB에서 대기 중인 장비 목록 조회
    df_pending = db.get_pending_equipments()
    
    if df_pending.empty:
        st.info("현재 대기 중인 데이터가 없습니다.")
    else:
        st.markdown(f"총 **{len(df_pending)}**건의 대기 데이터가 있습니다.")
        
        for idx, row in df_pending.iterrows():
            # Expander Title: [Date] EquipmentName (SID) - Model
            title = f"[{row['uploaded_at']}] {row['equipment_name']} ({row['sid']}) - {row['model']}"
            
            with st.expander(title):
                c1, c2, c3 = st.columns([2, 1, 1])
                
                with c1:
                    st.write(f"**SID**: {row['sid']}")
                    st.write(f"**Date**: {row['date']}")
                    st.write(f"**R/I**: {row['ri']}")
                    if 'xy_scanner' in row and row['xy_scanner']:
                         st.write(f"**Scanner**: {row['xy_scanner']}")
                
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
