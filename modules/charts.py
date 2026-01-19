"""
Control Chart Plotly 시각화 함수
"""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from .utils import calculate_stats, detect_rule_of_seven, detect_trend_violations, RESEARCH_MODELS, INDUSTRIAL_MODELS

def create_control_chart(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = 'Value',
    date_col: str = '종료일',
    equipment_col: str = '장비명',
    show_violations: bool = True,
    use_dual_axis: bool = False,
    specs: Dict[str, float] = None
) -> go.Figure:
    """
    관리도 생성 (Combined Chart)
    specs dict keys: 'lsl', 'usl', 'target'
    """
    
    # 그룹별로 데이터 분리
    groups = df.groupby(group_col)
    
    # 색상 팔레트
    colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    
    # 이중 축 여부 결정
    group_keys = list(groups.groups.keys())
    num_groups = len(group_keys)
    
    if use_dual_axis and num_groups == 2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
        use_dual_axis = False
    
    # Spec Lines (USL, LSL, Target) - Draw these first or last?
    # If we draw them first, they might be behind data.
    # Since specs are usually per-model, but here we might have mixed models if group_col is not Model.
    # However, usually we analyze one Check Item.
    # If specs are provided, we assume they apply to the current view (or at least one of the groups).
    # For simplicity, if specs are passed, we draw them as horizontal lines across the whole chart.
    
    if specs:
        # Target Line (Green)
        if specs.get('target') is not None:
            fig.add_hline(
                y=specs['target'], 
                line_dash="dot", 
                line_color="green", 
                line_width=2,
                annotation_text=f"Target: {specs['target']}", 
                annotation_position="bottom right"
            )
            
        # USL Line (Red)
        if specs.get('usl') is not None:
            fig.add_hline(
                y=specs['usl'], 
                line_dash="solid", 
                line_color="red", 
                line_width=2,
                annotation_text=f"USL: {specs['usl']}", 
                annotation_position="top right"
            )
            
        # LSL Line (Red)
        if specs.get('lsl') is not None:
            fig.add_hline(
                y=specs['lsl'], 
                line_dash="solid", 
                line_color="red", 
                line_width=2,
                annotation_text=f"LSL: {specs['lsl']}", 
                annotation_position="bottom right"
            )

    # 각 그룹별로 처리
    for idx, (group_name, group_data) in enumerate(groups):
        # 기본 색상 (그룹별)
        base_color = colors[idx % len(colors)]
        
        # 날짜순 정렬
        group_data = group_data.sort_values(date_col)
        
        dates = group_data[date_col]
        values = group_data[value_col].values
        equip_names = group_data[equipment_col].values if equipment_col in group_data.columns else [''] * len(dates)
        check_items = group_data['Check Items'].values if 'Check Items' in group_data.columns else [''] * len(dates)
        models = group_data['Model'].values if 'Model' in group_data.columns else [''] * len(dates)
        
        # Marker Colors based on Model Type (Research vs Industrial)
        marker_symbols = []
        
        for m in models:
            if m in RESEARCH_MODELS:
                marker_symbols.append('diamond')
            elif m in INDUSTRIAL_MODELS:
                marker_symbols.append('circle')
            else:
                marker_symbols.append('circle')
        
        # 통계 계산
        stats = calculate_stats(values)
        avg, ucl, lcl = stats['avg'], stats['ucl'], stats['lcl']
        
        # Y축 인덱스 결정
        secondary_y = (use_dual_axis and idx == 1)
        
        # 산점도 추가
        scatter = go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name=str(group_name),
            line=dict(color=base_color, width=1),
            marker=dict(
                color=base_color, 
                size=8, 
                symbol=marker_symbols
            ),
            customdata=np.stack((equip_names, check_items, models), axis=-1),
            hovertemplate=(
                '<b>%{customdata[1]}</b><br>' +  # Check Item
                '장비명: %{customdata[0]} (%{customdata[2]})<br>' + # Equip (Model)
                '출고일: %{x|%Y-%m-%d}<br>' +      # Date
                'Value: %{y:.3f}<br>' +           # Value
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
            line=dict(color=base_color, width=1.5, dash='dash'),
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
            line=dict(color=base_color, width=1.5),
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
            line=dict(color=base_color, width=1.5),
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
                    # Customdata for violations needs to be sliced too
                    run_customdata = np.stack((
                        equip_names[run], 
                        check_items[run],
                        models[run]
                    ), axis=-1)
                    
                    violation_trace = go.Scatter(
                        x=run_dates,
                        y=run_values,
                        mode='lines+markers',
                        name='Trend Violation' if run_idx == 0 else None,
                        line=dict(color='red', width=2),
                        marker=dict(color='red', size=10, symbol='x'),
                        customdata=run_customdata,
                        showlegend=(run_idx == 0),
                        hovertemplate=(
                            '<b>위반!</b><br>' +
                            '<b>%{customdata[1]}</b><br>' +
                            '장비명: %{customdata[0]}<br>' +
                            '출고일: %{x|%Y-%m-%d}<br>' +
                            'Value: %{y:.3f}<br>' +
                            '<extra></extra>'
                        )
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
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1),
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
    show_violations: bool = True,
    specs: Dict[str, float] = None
) -> go.Figure:
    """
    개별 그룹의 관리도 생성
    """
    # 날짜순 정렬
    group_data = group_data.sort_values(date_col)
    
    dates = group_data[date_col]
    values = group_data[value_col].values
    equip_names = group_data[equipment_col].values if equipment_col in group_data.columns else [''] * len(dates)
    check_items = group_data['Check Items'].values if 'Check Items' in group_data.columns else [''] * len(dates)
    models = group_data['Model'].values if 'Model' in group_data.columns else [''] * len(dates)
    
    # Marker Symbols
    marker_symbols = []
    for m in models:
        if m in RESEARCH_MODELS:
            marker_symbols.append('diamond')
        elif m in INDUSTRIAL_MODELS:
            marker_symbols.append('circle')
        else:
            marker_symbols.append('circle')
            
    # 통계 계산
    stats = calculate_stats(values)
    avg, ucl, lcl = stats['avg'], stats['ucl'], stats['lcl']
    
    fig = go.Figure()
    
    # Spec Lines (USL, LSL, Target)
    if specs:
        if specs.get('target') is not None:
            fig.add_hline(y=specs['target'], line_dash="dot", line_color="green", line_width=2, annotation_text="Target")
        if specs.get('usl') is not None:
            fig.add_hline(y=specs['usl'], line_dash="solid", line_color="red", line_width=2, annotation_text="USL")
        if specs.get('lsl') is not None:
            fig.add_hline(y=specs['lsl'], line_dash="solid", line_color="red", line_width=2, annotation_text="LSL")
    
    # 산점도
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines+markers',
        name=str(group_name),
        line=dict(color='blue', width=1),
        marker=dict(
            color='blue', 
            size=8,
            symbol=marker_symbols
        ),
        customdata=np.stack((equip_names, check_items, models), axis=-1),
        hovertemplate=(
            '<b>%{customdata[1]}</b><br>' +
            '장비명: %{customdata[0]} (%{customdata[2]})<br>' +
            '출고일: %{x|%Y-%m-%d}<br>' +
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
                run_customdata = np.stack((
                    equip_names[run], 
                    check_items[run],
                    models[run]
                ), axis=-1)
                
                fig.add_trace(go.Scatter(
                    x=run_dates,
                    y=run_values,
                    mode='lines+markers',
                    name='Trend Violation' if run_idx == 0 else None,
                    line=dict(color='red', width=2),
                    marker=dict(color='red', size=10, symbol='x'),
                    customdata=run_customdata,
                    showlegend=(run_idx == 0),
                    hovertemplate=(
                        '<b>위반!</b><br>' +
                        '<b>%{customdata[1]}</b><br>' +
                        '장비명: %{customdata[0]}<br>' +
                        '출고일: %{x|%Y-%m-%d}<br>' +
                        'Value: %{y:.3f}<br>' +
                        '<extra></extra>'
                    )
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
    df = df.copy()
    if 'count' not in df.columns:
        df['count'] = 1
        
    # 데이터 전처리: Path 컬럼의 결측치/빈 문자열 처리
    # Sunburst는 빈 문자열이나 NaN이 섞여 있으면 계층 구조 해석에 실패할 수 있음
    for col in path:
        if col in df.columns:
            df[col] = df[col].fillna('미지정').astype(str)
            df[col] = df[col].replace('', '미지정')
            df[col] = df[col].replace('nan', '미지정') # str 변환 후 'nan' 문자열 처리
        
    fig = px.sunburst(
        df,
        path=path,
        values='count',
        title=f'장비 분포 ({", ".join(path)})'
    )
    
    fig.update_traces(textinfo="label+value+percent parent")
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
    
    return fig

def create_model_bar_chart(df: pd.DataFrame, color_seq: list = None) -> go.Figure:
    """Create a horizontal bar chart for model counts."""
    # Count by model
    model_counts = df['model'].value_counts().reset_index()
    model_counts.columns = ['model', 'count']
    model_counts = model_counts.sort_values('count', ascending=True) # Sort for bar chart
    
    fig = px.bar(
        model_counts,
        x='count',
        y='model',
        orientation='h',
        text='count',
        color_discrete_sequence=color_seq if color_seq else px.colors.qualitative.Plotly
    )
    
    fig.update_traces(textposition='outside')
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False,
        height=300, # Fixed height
        clickmode='event+select'
    )
    
    return fig
