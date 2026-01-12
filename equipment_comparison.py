"""
장비 비교 분석 모듈
Equipment Comparison Analysis Module
품질엔지니어가 장비 간 성능 차이를 비교하고 문제 장비를 식별
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def create_equipment_comparison_table(df, lsl=None, usl=None, target=None):
    """
    장비별 통계 테이블 생성
    
    Args:
        df: DataFrame with equipment data (single Check Item assumed)
        lsl: Lower Spec Limit
        usl: Upper Spec Limit
        target: Target value
    
    Returns:
        DataFrame: Equipment statistics table
    """
    if '장비명' not in df.columns or 'Value' not in df.columns:
        return None
    
    equipment_stats = []
    
    for equip_name, equip_df in df.groupby('장비명'):
        measurements = equip_df['Value'].dropna()
        
        if len(measurements) == 0:
            continue
        
        mean = measurements.mean()
        std = measurements.std()
        min_val = measurements.min()
        max_val = measurements.max()
        count = len(measurements)
        
        # Cpk 계산
        cpk = None
        if lsl is not None and usl is not None and std > 0:
            cpu = (usl - mean) / (3 * std)
            cpl = (mean - lsl) / (3 * std)
            cpk = min(cpu, cpl)
        
        # 불량률
        defect_count = 0
        defect_rate = 0
        if lsl is not None and usl is not None:
            defect_count = ((measurements < lsl) | (measurements > usl)).sum()
            defect_rate = (defect_count / count) * 100
        
        equipment_stats.append({
            '장비명': equip_name,
            '평균': mean,
            '표준편차': std,
            'Min': min_val,
            'Max': max_val,
            '데이터 수': count,
            'Cpk': cpk,
            '불량 개수': int(defect_count),
            '불량률(%)': defect_rate
        })
    
    if len(equipment_stats) == 0:
        return None
    
    # DataFrame 생성
    df_stats = pd.DataFrame(equipment_stats)
    
    # Cpk 기준으로 정렬
    if df_stats['Cpk'].notna().any():
        df_stats = df_stats.sort_values('Cpk', ascending=False, na_position='last')
        df_stats['순위'] = range(1, len(df_stats) + 1)
        
        # 순위 아이콘
        def get_rank_icon(rank, total):
            if rank == 1:
                return "🥇"
            elif rank == 2:
                return "🥈"
            elif rank == 3:
                return "🥉"
            elif rank >= total - 2 and total > 3:
                return "🔴"
            else:
                return ""
        
        df_stats[''] = df_stats['순위'].apply(
            lambda r: get_rank_icon(r, len(df_stats))
        )
        
        # 컬럼 순서
        cols = ['', '순위', '장비명', '평균', '표준편차', 'Cpk', 
                '데이터 수', '불량 개수', '불량률(%)', 'Min', 'Max']
        df_stats = df_stats[[c for c in cols if c in df_stats.columns]]
    
    return df_stats


def create_equipment_boxplot(df, lsl=None, usl=None, target=None, unit=''):
    """
    장비별 Box Plot 생성
    
    Args:
        df: DataFrame with equipment data
        lsl, usl, target: Spec limits
        unit: Measurement unit
    
    Returns:
        plotly Figure
    """
    if '장비명' not in df.columns or 'Value' not in df.columns:
        return None
    
    fig = px.box(
        df,
        x='장비명',
        y='Value',
        points='outliers',
        hover_data=['종료일'] if '종료일' in df.columns else None
    )
    
    # 스펙 라인
    if lsl is not None:
        fig.add_hline(
            y=lsl,
            line_color='red',
            line_width=2,
            line_dash='dash',
            annotation_text=f'LSL: {lsl}{unit}',
            annotation_position='right'
        )
    
    if target is not None:
        fig.add_hline(
            y=target,
            line_color='green',
            line_width=2,
            line_dash='dot',
            annotation_text=f'Target: {target}{unit}',
            annotation_position='right'
        )
    
    if usl is not None:
        fig.add_hline(
            y=usl,
            line_color='red',
            line_width=2,
            line_dash='dash',
            annotation_text=f'USL: {usl}{unit}',
            annotation_position='right'
        )
    
    fig.update_layout(
        yaxis_title=f"측정값 ({unit})" if unit else "측정값",
        xaxis_title="장비명",
        height=500,
        showlegend=False
    )
    
    return fig


def detect_outlier_equipments(df, df_stats):
    """
    아웃라이어 장비 감지
    
    Args:
        df: Original DataFrame
        df_stats: Equipment statistics DataFrame
    
    Returns:
        list: Outlier equipment information
    """
    if 'Value' not in df.columns or df_stats is None or df_stats.empty:
        return []
    
    overall_mean = df['Value'].mean()
    overall_std = df['Value'].std()
    
    upper_threshold = overall_mean + 2 * overall_std
    lower_threshold = overall_mean - 2 * overall_std
    
    outliers = []
    
    for _, row in df_stats.iterrows():
        equip_mean = row['평균']
        if equip_mean > upper_threshold or equip_mean < lower_threshold:
            outliers.append({
                '장비명': row['장비명'],
                '평균': equip_mean,
                '차이': equip_mean - overall_mean,
                '차이율(%)': ((equip_mean - overall_mean) / overall_mean) * 100 if overall_mean != 0 else 0
            })
    
    return outliers, overall_mean, overall_std, lower_threshold, upper_threshold
