"""
월별 출하 현황 대시보드 탭
Monthly Dashboard Tab

Features:
- 출하 현황 요약 (통계 + 파이 차트)
- 월별 차트 (년도 필터 포함)
- 월 선택 시 상세 정보 (타입별 차트 + 장비 목록)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from monthly_shipment import (
    aggregate_monthly_shipments,
    create_monthly_shipment_chart,
    show_shipment_stats
)
from utils import RESEARCH_MODELS, INDUSTRIAL_MODELS
import database as db


def render_monthly_dashboard_tab():
    """월별 출하 현황 탭 렌더링"""
    st.subheader("📊 월별 출하 현황 (Monthly Dashboard)")
    
    # === 1. 출하 현황 요약 ===
    st.caption("총 출하 수, 연구용, 산업용 통계 및 트렌드를 표시합니다")
    
    df_equipments = db.get_all_equipments()
    
    if df_equipments.empty:
        st.info("데이터가 없습니다.")
        return
    
    show_shipment_stats(df_equipments)
    
    st.divider()
    
    # === 2. 월별 차트 ===
    st.caption("💡 막대를 클릭하여 해당 월의 장비만 필터링할 수 있습니다")
    
    # 날짜 데이터 준비
    df_for_chart = df_equipments.copy()
    df_for_chart['date'] = pd.to_datetime(df_for_chart['date'], errors='coerce')
    df_for_chart = df_for_chart.dropna(subset=['date'])
    
    if df_for_chart.empty:
        st.warning("유효한 날짜 데이터가 없습니다.")
        return
    
    # 년도 필터
    available_years = sorted(df_for_chart['date'].dt.year.unique(), reverse=True)
    
    col_filter, col_space = st.columns([2, 3])
    with col_filter:
        selected_years = st.multiselect(
            "🗓️ 년도 선택",
            options=available_years,
            default=available_years,
            key="monthly_year_filter",
            help="특정 년도만 표시하려면 선택하세요"
        )
    
    # 년도 필터링
    if selected_years:
        df_filtered_by_year = df_for_chart[
            df_for_chart['date'].dt.year.isin(selected_years)
        ]
        monthly_stats = aggregate_monthly_shipments(df_filtered_by_year)
    else:
        monthly_stats = aggregate_monthly_shipments(df_for_chart)
    
    if monthly_stats.empty:
        st.info("선택한 년도에 데이터가 없습니다.")
        return
    
    # 차트 표시
    fig = create_monthly_shipment_chart(monthly_stats)
    
    chart_event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key="monthly_chart"
    )
    
    # 클릭 이벤트 처리
    if chart_event and chart_event.selection.points:
        clicked_point = chart_event.selection.points[0]
        
        # 월 정보 추출
        if 'customdata' in clicked_point:
            clicked_month = clicked_point['customdata']
        elif 'x' in clicked_point:
            x_val = clicked_point['x']
            clicked_month = x_val[:7] if isinstance(x_val, str) and len(x_val) >= 7 else x_val
        else:
            clicked_month = None
        
        if clicked_month:
            # 세션 상태 초기화
            if 'monthly_selected_month' not in st.session_state:
                st.session_state.monthly_selected_month = None
            
            # 토글
            if st.session_state.monthly_selected_month == clicked_month:
                st.session_state.monthly_selected_month = None
            else:
                st.session_state.monthly_selected_month = clicked_month
    
    # 선택된 월 표시
    if st.session_state.get('monthly_selected_month'):
        selected_month = st.session_state.monthly_selected_month
        st.success(f"📌 **{selected_month}** 선택됨 (같은 월 다시 클릭 시 해제)")
    
    st.divider()
    
    # === 3. 선택된 월 상세 정보 ===
    selected_month = st.session_state.get('monthly_selected_month', None)
    
    if selected_month:
        # 필터링
        df_filtered = df_for_chart[
            df_for_chart['date'].dt.to_period('M').astype(str) == selected_month
        ].copy()
        
        if not df_filtered.empty:
            st.success(f"✅ {selected_month} 출하 장비: {len(df_filtered)}대")
            
            # 2구역 레이아웃: 왼쪽(파이 차트) | 오른쪽(장비 목록)
            col_chart, col_list = st.columns([1, 2])
            
            with col_chart:
                st.markdown("#### 📊 타입별 출하 현황")
                
                # 연구용/산업용 개수 집계
                research_count = len(df_filtered[df_filtered['model'].isin(RESEARCH_MODELS)])
                industrial_count = len(df_filtered[df_filtered['model'].isin(INDUSTRIAL_MODELS)])
                
                # 파이 차트
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
                    height=400,
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
                    if not df_research.empty:
                        df_display = df_research.sort_values('date', ascending=False)
                        st.dataframe(
                            df_display[['sid', 'equipment_name', 'model', 'date']],
                            use_container_width=True,
                            height=300
                        )
                    else:
                        st.info("연구용 장비가 없습니다.")
                
                with tab_industrial:
                    df_industrial = df_filtered[df_filtered['model'].isin(INDUSTRIAL_MODELS)]
                    st.caption(f"산업용 {len(df_industrial)}대")
                    if not df_industrial.empty:
                        df_display = df_industrial.sort_values('date', ascending=False)
                        st.dataframe(
                            df_display[['sid', 'equipment_name', 'model', 'date']],
                            use_container_width=True,
                            height=300
                        )
                    else:
                        st.info("산업용 장비가 없습니다.")
        else:
            st.warning(f"⚠️ {selected_month}에 출하된 장비가 없습니다.")
    else:
        st.info("💡 차트에서 월을 선택하면 해당 월의 상세 정보가 표시됩니다.")
