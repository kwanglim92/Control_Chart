"""
Control Chart Plotly 시각화 함수
"""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from utils import calculate_stats, detect_rule_of_seven, detect_trend_violations


def create_control_chart(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = 'Value',
    date_col: str = '종료일',
    equipment_col: str = '장비명',
    show_violations: bool = True,
    use_dual_axis: bool = False
) -> go.Figure:
    """
    관리도 생성 (Combined Chart)
    
    Parameters:
    - df: 데이터프레임
    - group_col: 그룹화 기준 컬럼
    - value_col: 값 컬럼
    - date_col: 날짜 컬럼
    - equipment_col: 장비명 컬럼 (Hover 표시용)
    - show_violations: Rule of Seven / Trend 위반 표시 여부
    - use_dual_axis: 이중 축 사용 여부 (Check Items가 2개일 때)
    """
    
    # 그룹별로 데이터 분리
    groups = df.groupby(group_col)
    
    # 색상 팔레트 (C# 코드와 동일)
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#393b79', '#5254a3', '#6b6ecf', '#9c9ede', '#637939',
        '#8ca252', '#b5cf6b', '#cedb9c', '#8c6d31', '#bd9e39'
    ]
    
    # 이중 축 여부 결정
    group_keys = list(groups.groups.keys())
    num_groups = len(group_keys)
    
    if use_dual_axis and num_groups == 2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
        use_dual_axis = False
    
    # 각 그룹별로 처리
    for idx, (group_name, group_data) in enumerate(groups):
        color = colors[idx % len(colors)]
        
        # 날짜순 정렬
        group_data = group_data.sort_values(date_col)
        
        dates = group_data[date_col]
        values = group_data[value_col].values
        equip_names = group_data[equipment_col].values if equipment_col in group_data.columns else [''] * len(dates)
        
        # 통계 계산
        stats = calculate_stats(values)
        avg, ucl, lcl = stats['avg'], stats['ucl'], stats['lcl']
        
        # Y축 인덱스 결정
        if use_dual_axis:
            secondary_y = (idx == 1)
        else:
            secondary_y = False
        
        # 산점도 추가
        scatter = go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name=str(group_name),
            line=dict(color=color, width=1),
            marker=dict(color=color, size=6),
            customdata=equip_names,
            hovertemplate=(
                f'<b>{group_name}</b><br>' +
                '날짜: %{x|%Y-%m-%d}<br>' +
                '장비명: %{customdata}<br>' +
                'Value: %{y:.3f}<br>' +
                '<extra></extra>'
            )
        )
        
        if use_dual_axis:
            fig.add_trace(scatter, secondary_y=secondary_y)
        else:
            fig.add_trace(scatter)
        
        # 평균선 (점선)
        avg_line = go.Scatter(
            x=dates,
            y=[avg] * len(dates),
            mode='lines',
            name=f'{group_name} AVG',
            line=dict(color=color, width=1.5, dash='dash'),
            hovertemplate=f'AVG: {avg:.3f}<extra></extra>'
        )
        
        if use_dual_axis:
            fig.add_trace(avg_line, secondary_y=secondary_y)
        else:
            fig.add_trace(avg_line)
        
        # UCL 선
        ucl_line = go.Scatter(
            x=dates,
            y=[ucl] * len(dates),
            mode='lines',
            name=f'{group_name} UCL',
            line=dict(color=color, width=1.5),
            hovertemplate=f'UCL: {ucl:.3f}<extra></extra>'
        )
        
        if use_dual_axis:
            fig.add_trace(ucl_line, secondary_y=secondary_y)
        else:
            fig.add_trace(ucl_line)
        
        # LCL 선
        lcl_line = go.Scatter(
            x=dates,
            y=[lcl] * len(dates),
            mode='lines',
            name=f'{group_name} LCL',
            line=dict(color=color, width=1.5),
            hovertemplate=f'LCL: {lcl:.3f}<extra></extra>'
        )
        
        if use_dual_axis:
            fig.add_trace(lcl_line, secondary_y=secondary_y)
        else:
            fig.add_trace(lcl_line)
        
        # Rule of Seven & Trend 위반 표시
        if show_violations:
            rule7_indices = detect_rule_of_seven(values, avg)
            trend_indices = detect_trend_violations(values)
            violation_indices = sorted(set(rule7_indices + trend_indices))
            
            if violation_indices:
                # 연속된 구간으로 분할
                runs = []
                current_run = [violation_indices[0]]
                
                for i in range(1, len(violation_indices)):
                    if violation_indices[i] == violation_indices[i-1] + 1:
                        current_run.append(violation_indices[i])
                    else:
                        runs.append(current_run)
                        current_run = [violation_indices[i]]
                runs.append(current_run)
                
                # 각 구간을 빨간선으로 표시
                for run_idx, run in enumerate(runs):
                    run_dates = dates.iloc[run].values
                    run_values = values[run]
                    run_equips = equip_names[run]
                    
                    violation_trace = go.Scatter(
                        x=run_dates,
                        y=run_values,
                        mode='lines+markers',
                        name='Trend Violation' if run_idx == 0 else None,
                        line=dict(color='red', width=2),
                        marker=dict(color='red', size=7),
                        customdata=run_equips,
                        showlegend=(run_idx == 0),
                        hovertemplate='위반!<br>장비명: %{customdata}<br>Value: %{y:.3f}<extra></extra>'
                    )
                    
                    if use_dual_axis:
                        fig.add_trace(violation_trace, secondary_y=secondary_y)
                    else:
                        fig.add_trace(violation_trace)
    
    # 레이아웃 설정
    fig.update_layout(
        title=f'Control Chart - {group_col}별 비교',
        xaxis_title='날짜',
        yaxis_title='Value',
        hovermode='closest',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1
        ),
        height=600
    )
    
    if use_dual_axis:
        fig.update_yaxes(title_text=group_keys[0], secondary_y=False)
        fig.update_yaxes(title_text=group_keys[1], secondary_y=True)
    
    return fig


def create_individual_chart(
    group_data: pd.DataFrame,
    group_name: str,
    value_col: str = 'Value',
    date_col: str = '종료일',
    equipment_col: str = '장비명',
    show_violations: bool = True
) -> go.Figure:
    """
    개별 그룹의 관리도 생성
    """
    # 날짜순 정렬
    group_data = group_data.sort_values(date_col)
    
    dates = group_data[date_col]
    values = group_data[value_col].values
    equip_names = group_data[equipment_col].values if equipment_col in group_data.columns else [''] * len(dates)
    
    # 통계 계산
    stats = calculate_stats(values)
    avg, ucl, lcl = stats['avg'], stats['ucl'], stats['lcl']
    
    fig = go.Figure()
    
    # 산점도
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines+markers',
        name=str(group_name),
        line=dict(color='blue', width=1),
        marker=dict(color='blue', size=6),
        customdata=equip_names,
        hovertemplate=(
            '날짜: %{x|%Y-%m-%d}<br>' +
            '장비명: %{customdata}<br>' +
            'Value: %{y:.3f}<br>' +
            '<extra></extra>'
        )
    ))
    
    # 평균선
    fig.add_trace(go.Scatter(
        x=dates,
        y=[avg] * len(dates),
        mode='lines',
        name='AVG',
        line=dict(color='black', width=1.5, dash='dash'),
        hovertemplate=f'AVG: {avg:.3f}<extra></extra>'
    ))
    
    # UCL
    fig.add_trace(go.Scatter(
        x=dates,
        y=[ucl] * len(dates),
        mode='lines',
        name='UCL',
        line=dict(color='blue', width=1.5),
        hovertemplate=f'UCL: {ucl:.3f}<extra></extra>'
    ))
    
    # LCL
    fig.add_trace(go.Scatter(
        x=dates,
        y=[lcl] * len(dates),
        mode='lines',
        name='LCL',
        line=dict(color='blue', width=1.5),
        hovertemplate=f'LCL: {lcl:.3f}<extra></extra>'
    ))
    
    # 위반 표시
    if show_violations:
        rule7_indices = detect_rule_of_seven(values, avg)
        trend_indices = detect_trend_violations(values)
        violation_indices = sorted(set(rule7_indices + trend_indices))
        
        if violation_indices:
            runs = []
            current_run = [violation_indices[0]]
            
            for i in range(1, len(violation_indices)):
                if violation_indices[i] == violation_indices[i-1] + 1:
                    current_run.append(violation_indices[i])
                else:
                    runs.append(current_run)
                    current_run = [violation_indices[i]]
            runs.append(current_run)
            
            for run_idx, run in enumerate(runs):
                run_dates = dates.iloc[run].values
                run_values = values[run]
                run_equips = equip_names[run]
                
                fig.add_trace(go.Scatter(
                    x=run_dates,
                    y=run_values,
                    mode='lines+markers',
                    name='Trend Violation' if run_idx == 0 else None,
                    line=dict(color='red', width=2),
                    marker=dict(color='red', size=7),
                    customdata=run_equips,
                    showlegend=(run_idx == 0),
                    hovertemplate='위반!<br>장비명: %{customdata}<br>Value: %{y:.3f}<extra></extra>'
                ))
    
    fig.update_layout(
        title=f'Group: {group_name}',
        xaxis_title='날짜',
        yaxis_title='Value',
        hovermode='closest',
        height=400
    )
    
    return fig

def plot_sunburst_chart(df: pd.DataFrame, path: List[str] = None) -> go.Figure:
    """
    계층형 Sunburst 차트 생성
    """
    # 데이터가 없으면 빈 차트 반환
    if df.empty:
        return go.Figure()
        
    if path is None:
        path = ['ri', 'model']
        
    # Sunburst 차트 생성
    # path: 계층 구조 (예: ['Year', 'ri', 'model'])
    # values: 크기 (count) - 이미 집계된 데이터가 아니라면 count가 1인 컬럼을 추가해서 써야 함
    
    # 데이터프레임에 'count' 컬럼이 없다면 1로 채움 (개별 row가 1개 장비)
    if 'count' not in df.columns:
        df = df.copy()
        df['count'] = 1
        
    fig = px.sunburst(
        df,
        path=path,
        values='count',
        title=f'장비 분포 ({", ".join(path)})'
    )
    
    fig.update_traces(textinfo="label+value+percent parent")
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
    
    return fig
