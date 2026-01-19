"""
월별 출하 현황 차트 테스트 앱
이 파일로 먼저 기능을 검증한 후 app.py에 통합합니다.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import database as db

# monthly_shipment 모듈 import
from monthly_shipment import (
    aggregate_monthly_shipments,
    create_monthly_shipment_chart,
    show_shipment_stats
)

st.set_page_config(
    page_title="월별 차트 테스트",
    page_icon="📊",
    layout="wide"
)

st.title("📊 월별 출하 현황 차트 - 기능 테스트")

# DB 초기화
if 'db_initialized' not in st.session_state:
    db.init_db()
    st.session_state.db_initialized = True

st.info("이 페이지는 월별 출하 현황 차트 기능을 독립적으로 테스트하기 위한 페이지입니다.")

# 데이터 가져오기
df_equipments = db.get_all_equipments()

if df_equipments.empty:
    st.warning("⚠️ 데이터가 없습니다. 먼저 데이터를 업로드해주세요.")
else:
    st.success(f"✅ 총 {len(df_equipments)}건의 장비 데이터 로드 완료")
    
    st.divider()
    
    # === 테스트 1: 통계 카드 ===
    st.markdown("### 📊 출하 현황 요약")
    st.caption("총 출하 수, 연구용, 산업용 통계를 표시합니다")
    
    try:
        show_shipment_stats(df_equipments)
        st.success("✅ 통계 카드 렌더링 성공")
    except Exception as e:
        st.error(f"❌ 통계 카드 오류: {e}")
    
    st.divider()
    
    # === 테스트 2: 월별 집계 ===
    st.markdown("### 📊 월별 데이터 집계")
    st.caption("월별로 연구용/산업용 장비 수를 집계합니다")
    
    try:
        monthly_stats = aggregate_monthly_shipments(df_equipments)
        
        if monthly_stats.empty:
            st.warning("월별 통계 데이터가 비어있습니다.")
        else:
            st.success(f"✅ 월별 집계 성공: {len(monthly_stats)}개월 데이터")
            
            # 집계 결과 미리보기
            with st.expander("집계 데이터 미리보기"):
                st.dataframe(monthly_stats, use_container_width=True)
                
    except Exception as e:
        st.error(f"❌ 월별 집계 오류: {e}")
        monthly_stats = pd.DataFrame()
    
    st.divider()
    
    # === 테스트 3: 차트 생성 + 년도 필터 ===
    st.markdown("### 📊 월별 장비 출하 현황 차트")
    st.caption("💡 막대를 클릭하여 해당 월의 장비만 필터링할 수 있습니다")
    
    if not monthly_stats.empty:
        # 년도 필터 UI
        available_years = sorted(df_equipments['date'].dt.year.unique(), reverse=True)
        
        col_filter, col_space = st.columns([2, 3])
        with col_filter:
            selected_years = st.multiselect(
                "🗓️ 년도 선택",
                options=available_years,
                default=available_years,  # 전체 선택
                key="year_filter",
                help="특정 년도만 표시하려면 선택하세요"
            )
        
        # 년도 필터링 적용
        if selected_years:
            df_filtered_by_year = df_equipments[
                df_equipments['date'].dt.year.isin(selected_years)
            ]
            monthly_stats_filtered = aggregate_monthly_shipments(df_filtered_by_year)
        else:
            st.warning("⚠️ 최소 1개 이상의 년도를 선택해주세요.")
            monthly_stats_filtered = monthly_stats
        
        try:
            if not monthly_stats_filtered.empty:
                fig = create_monthly_shipment_chart(monthly_stats_filtered)
                
                # 클릭 가능한 차트
                chart_event = st.plotly_chart(
                    fig,
                    width='stretch',
                    on_select="rerun",
                    selection_mode="points",
                    key="test_monthly_chart"
                )

            
            st.success("✅ 차트 렌더링 성공")
            
            # 디버그: 클릭 이벤트 확인
            if chart_event and chart_event.selection.points:
                with st.expander("🔍 디버그: 클릭 이벤트 정보", expanded=False):
                    st.json(chart_event.selection.points[0])
            
            # 클릭 이벤트 처리 - 심플한 월 선택
            if chart_event and chart_event.selection.points:
                # 클릭한 포인트에서 월 정보 추출
                clicked_point = chart_event.selection.points[0]
                
                # customdata 우선 사용 (년-월 형식: "2023-12")
                if 'customdata' in clicked_point:
                    clicked_month = clicked_point['customdata']
                elif 'x' in clicked_point:
                    # x 값이 "2023-12-01" 형식이면 "2023-12"로 변환
                    x_val = clicked_point['x']
                    if isinstance(x_val, str) and len(x_val) >= 7:
                        clicked_month = x_val[:7]  # "2023-12-01" -> "2023-12"
                    else:
                        clicked_month = x_val
                else:
                    clicked_month = None
                
                if clicked_month:
                    # 세션 상태 초기화
                    if 'test_selected_month' not in st.session_state:
                        st.session_state.test_selected_month = None
                    
                    # 같은 월 클릭 시 토글 (해제)
                    if st.session_state.test_selected_month == clicked_month:
                        st.session_state.test_selected_month = None
                        st.success(f"✅ 월 필터 해제됨")
                    else:
                        # 새로운 월 선택
                        st.session_state.test_selected_month = clicked_month
                        st.success(f"✅ {clicked_month} 선택됨")

            
            # 선택된 월 표시 (간단하게)
            if st.session_state.get('test_selected_month'):
                selected_month = st.session_state.test_selected_month
                st.success(f"📌 **{selected_month}** 선택됨 (같은 월 다시 클릭 시 해제)")
                        
        except Exception as e:
            st.error(f"❌ 차트 생성 오류: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    st.divider()
    
    # === 테스트 4: 필터링 + 탭 레이아웃 ===
    st.markdown("### 📊 월 필터링 + 장비 목록")
    
    selected_month = st.session_state.get('test_selected_month', None)
    
    if selected_month:
        try:
            # 필터링 적용
            df_filtered = df_equipments[
                df_equipments['date'].dt.to_period('M').astype(str) == selected_month
            ].copy()
            
            if not df_filtered.empty:
                st.success(f"✅ {selected_month} 출하 장비: {len(df_filtered)}대")
                
                # 2구역 레이아웃: 왼쪽(차트) | 오른쪽(목록+탭)
                col_chart, col_list = st.columns([1, 2])
                
                with col_chart:
                    st.markdown("#### 📊 타입별 출하 현황")
                    
                    # 연구용/산업용 개수 집계
                    from utils import RESEARCH_MODELS, INDUSTRIAL_MODELS
                    
                    research_count = 0
                    industrial_count = 0
                    
                    for _, row in df_filtered.iterrows():
                        if row['model'] in RESEARCH_MODELS:
                            research_count += 1
                        elif row['model'] in INDUSTRIAL_MODELS:
                            industrial_count += 1
                    
                    # 파이 차트 (도넛 형태)
                    import plotly.graph_objects as go
                    
                    fig_type = go.Figure(data=[go.Pie(
                        labels=['연구용', '산업용'],
                        values=[research_count, industrial_count],
                        marker_colors=['#4A90E2', '#50C878'],
                        hole=0.4,  # 도넛 차트
                        textinfo='label+value+percent',
                        textfont=dict(size=12),
                        hovertemplate='<b>%{label}</b><br>%{value}대 (%{percent})<extra></extra>'
                    )])
                    
                    fig_type.update_layout(
                        title=f"{selected_month} 타입별 출하",
                        height=400,  # 높이 증가
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="middle",
                            y=0.5,
                            xanchor="left",
                            x=1.1
                        )
                    )
                    
                    st.plotly_chart(fig_type, use_container_width=True)
                
                with col_list:
                    st.markdown("#### 📋 필터링된 장비 목록")
                    
                    # 탭으로 구분
                    tab_all, tab_research, tab_industrial = st.tabs(["전체", "연구용", "산업용"])
                    
                    with tab_all:
                        st.caption(f"전체 {len(df_filtered)}대")
                        df_display = df_filtered.sort_values('date', ascending=False)
                        st.dataframe(
                            df_display[['sid', 'equipment_name', 'model', 'date']],
                            use_container_width=True,
                            height=300
                        )
                    
                    with tab_research:
                        df_research = df_filtered[df_filtered['model'].isin(RESEARCH_MODELS)]
                        st.caption(f"연구용 {len(df_research)}대")
                        df_display = df_research.sort_values('date', ascending=False)
                        st.dataframe(
                            df_display[['sid', 'equipment_name', 'model', 'date']],
                            use_container_width=True,
                            height=300
                        )
                    
                    with tab_industrial:
                        df_industrial = df_filtered[df_filtered['model'].isin(INDUSTRIAL_MODELS)]
                        st.caption(f"산업용 {len(df_industrial)}대")
                        df_display = df_industrial.sort_values('date', ascending=False)
                        st.dataframe(
                            df_display[['sid', 'equipment_name', 'model', 'date']],
                            use_container_width=True,
                            height=300
                        )
            else:
                st.warning(f"⚠️ {selected_month}에 출하된 장비가 없습니다.")
                
        except Exception as e:
            st.error(f"❌ 필터링 오류: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("차트에서 월을 선택하면 해당 월의 장비 목록이 표시됩니다.")

st.divider()

# 테스트 결과 요약
st.markdown("### ✅ 테스트 체크리스트")

checklist = """
- [ ] 통계 카드가 정상적으로 표시되는가?
- [ ] 월별 집계가 올바르게 수행되는가?
- [ ] 차트가 정상적으로 렌더링되는가?
- [ ] 차트 막대 클릭 시 이벤트가 발생하는가?
- [ ] 필터링이 정상적으로 작동하는가?
- [ ] 토글(재클릭 시 해제)이 작동하는가?
- [ ] 필터 해제 버튼이 작동하는가?
"""

st.markdown(checklist)

st.info("✅ 모든 테스트 항목이 정상 작동하면 app.py에 통합할 준비가 된 것입니다.")
