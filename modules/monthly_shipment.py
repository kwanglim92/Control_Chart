"""
Monthly Shipment Analysis Module
월별 출하 현황 분석 모듈
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from .utils import RESEARCH_MODELS, INDUSTRIAL_MODELS


def aggregate_monthly_shipments(df_equipments):
    """
    월별 출하 대수 집계
    
    Args:
        df_equipments: Equipment DataFrame with 'date' and 'model' columns
    
    Returns:
        DataFrame: year_month, 연구용, 산업용, 합계
    """
    if df_equipments.empty or 'date' not in df_equipments.columns:
        return pd.DataFrame()
    
    # DataFrame 복사
    df = df_equipments.copy()
    
    # 날짜를 연-월로 변환
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    
    if df.empty:
        return pd.DataFrame()
    
    df['year_month'] = df['date'].dt.strftime('%Y-%m')  # 년-월 형식 강제 (YYYY-MM)
    
    # 연구용/산업용 분류
    def classify_type(model):
        if pd.isna(model):
            return '기타'
        if model in RESEARCH_MODELS:
            return '연구용'
        elif model in INDUSTRIAL_MODELS:
            return '산업용'
        else:
            return '기타'
    
    df['category'] = df['model'].apply(classify_type)
    
    # 월별 + 카테고리별 집계
    monthly_stats = df.groupby(['year_month', 'category']).size().unstack(fill_value=0)
    
    # 컬럼 정리
    if '연구용' not in monthly_stats.columns:
        monthly_stats['연구용'] = 0
    if '산업용' not in monthly_stats.columns:
        monthly_stats['산업용'] = 0
    
    monthly_stats = monthly_stats.reset_index()
    monthly_stats = monthly_stats[['year_month', '연구용', '산업용']]
    monthly_stats['합계'] = monthly_stats['연구용'] + monthly_stats['산업용']
    
    # 날짜순 정렬
    monthly_stats = monthly_stats.sort_values('year_month')
    
    return monthly_stats


def create_monthly_shipment_chart(monthly_stats):
    """
    월별 출하 현황 막대 그래프 (클릭 가능)
    
    Args:
        monthly_stats: DataFrame from aggregate_monthly_shipments
    
    Returns:
        plotly Figure
    """
    if monthly_stats.empty:
        # 빈 차트 반환
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 없습니다",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    fig = go.Figure()
    
    # 연구용 막대
    fig.add_trace(go.Bar(
        name='연구용',
        x=monthly_stats['year_month'],
        y=monthly_stats['연구용'],
        marker_color='#4A90E2',  # 파란색
        customdata=monthly_stats['year_month'],  # 클릭 이벤트용
        hovertemplate='<b>%{x}</b><br>연구용: %{y}대<extra></extra>',
        text=monthly_stats['연구용'],  # 막대 위 숫자 표시
        textposition='inside',  # 막대 안쪽에 표시
        textangle=0,  # 텍스트 수평 유지
        textfont=dict(color='white', size=13)  # 텍스트 크기 증가
    ))
    
    # 산업용 막대
    fig.add_trace(go.Bar(
        name='산업용',
        x=monthly_stats['year_month'],
        y=monthly_stats['산업용'],
        marker_color='#50C878',  # 초록색
        customdata=monthly_stats['year_month'],
        hovertemplate='<b>%{x}</b><br>산업용: %{y}대<extra></extra>',
        text=monthly_stats['산업용'],  # 막대 위 숫자 표시
        textposition='inside',  # 막대 안쪽에 표시
        textangle=0,  # 텍스트 수평 유지
        textfont=dict(color='white', size=13)  # 텍스트 크기 증가
    ))
    
    # X축에 표시할 월 선택 (1, 3, 6, 9, 12월만)
    tick_vals = []
    tick_texts = []
    for month in monthly_stats['year_month']:
        month_num = int(month.split('-')[1])
        if month_num in [1, 3, 6, 9, 12]:
            tick_vals.append(month)
            tick_texts.append(month)
    
    fig.update_layout(
        title={
            'text': '📊 월별 장비 출하 현황',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='출하 월',
        yaxis_title='출하 대수',
        barmode='stack',
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # X축 틱 커스터마이징
    if tick_vals:
        fig.update_xaxes(
            tickmode='array',
            tickvals=tick_vals,
            ticktext=tick_texts,
            tickangle=-45
        )
    
    return fig


def create_summary_pie_chart(research_count, industrial_count):
    """
    연구용/산업용 비율 파이 차트
    
    Args:
        research_count: 연구용 대수
        industrial_count: 산업용 대수
    
    Returns:
        plotly Figure
    """
    fig = go.Figure(data=[go.Pie(
        labels=['연구용', '산업용'],
        values=[research_count, industrial_count],
        marker_colors=['#4A90E2', '#50C878'],
        hole=0.4,  # 도넛 차트
        textinfo='label+value+percent',  # 라벨 + 값 + 비율 표시
        textfont=dict(size=13),
        hovertemplate='<b>%{label}</b><br>%{value}대 (%{percent})<extra></extra>'
    )])
    
    fig.update_layout(
        title={
            'text': '📊 타입별 비율',
            'x': 0.5,
            'xanchor': 'center'
        },
        height=380,  # 높이 증가하여 짤림 방지
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,  # 범례 위치 조정
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=10, r=10, t=60, b=80)  # 하단 마진 증가
    )
    
    return fig


def show_shipment_stats(df_equipments):
    """
    출하 현황 통계 카드 + 파이 차트 표시 (트렌드 중심)
    
    Args:
        df_equipments: Equipment DataFrame
    """
    if df_equipments.empty:
        st.info("데이터가 없습니다.")
        return
    
    # 날짜 처리
    df = df_equipments.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    
    if df.empty:
        st.info("유효한 날짜 데이터가 없습니다.")
        return
    
    # 연구용/산업용 분류
    def classify_type(model):
        if pd.isna(model):
            return '기타'
        if model in RESEARCH_MODELS:
            return '연구용'
        elif model in INDUSTRIAL_MODELS:
            return '산업용'
        else:
            return '기타'
    
    df['category'] = df['model'].apply(classify_type)
    
    # === 트렌드 중심 메트릭 계산 ===
    from datetime import datetime, timedelta
    
    # 1. 총 출하
    total_count = len(df)
    
    # 2. 최근 30일
    now = datetime.now()
    recent_30d = df[df['date'] >= now - timedelta(days=30)]
    recent_count = len(recent_30d)
    
    # 3. 전월 대비
    current_month = now.replace(day=1)
    last_month_start = (current_month - timedelta(days=1)).replace(day=1)
    
    current_month_count = len(df[df['date'] >= current_month])
    last_month_count = len(df[(df['date'] >= last_month_start) & (df['date'] < current_month)])
    
    if last_month_count > 0:
        mom_change_pct = ((current_month_count - last_month_count) / last_month_count) * 100
    else:
        mom_change_pct = 0
    
    # 4. 평균 월 출하
    months = df['date'].dt.to_period('M').nunique()
    avg_per_month = total_count / months if months > 0 else 0
    
    # 5. 연구용/산업용 개수
    research_count = len(df[df['category'] == '연구용'])
    industrial_count = len(df[df['category'] == '산업용'])
    
    # === 2구역 레이아웃 ===
    col_stats, col_chart = st.columns([11, 9])
    
    with col_stats:
        # === 1행: 총 출하, 연구용, 산업용 ===
        row1_col1, row1_col2, row1_col3 = st.columns(3)
        
        with row1_col1:
            st.metric(
                "총 출하",
                f"{total_count:,}대"
            )
        
        with row1_col2:
            st.metric(
                "연구용 장비 대수",
                f"{research_count:,}대"
            )
        
        with row1_col3:
            st.metric(
                "산업용 장비 대수",
                f"{industrial_count:,}대"
            )
        
        # === 2행: 최근 30일, 전월 대비, 평균 월 출하 ===
        row2_col1, row2_col2, row2_col3 = st.columns(3)
        
        with row2_col1:
            st.metric(
                "최근 30일",
                f"{recent_count}대"
            )
        
        with row2_col2:
            delta_icon = "↑" if mom_change_pct > 0 else ("↓" if mom_change_pct < 0 else "→")
            st.metric(
                "전월 대비",
                f"{abs(mom_change_pct):.1f}%",
                delta=f"{delta_icon} {current_month_count}대"
            )
        
        with row2_col3:
            st.metric(
                "평균 월 출하",
                f"{avg_per_month:.1f}대"
            )
    
    with col_chart:
        # 파이 차트 표시
        if research_count > 0 or industrial_count > 0:
            fig = create_summary_pie_chart(research_count, industrial_count)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("표시할 데이터가 없습니다.")
