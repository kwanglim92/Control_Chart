"""
Configuration Analysis Module (Phase 4-Lite)
구성 요소별 성능 분석 모듈

Purpose:
- 장비 구매/업그레이드 시 데이터 기반 의사결정 지원
- Scanner, Head Type 등 구성 요소별 성능 차이 분석
- 간단하고 명확한 인사이트 제공
"""
import pandas as pd
import numpy as np
import streamlit as st


def analyze_by_configuration(df, config_column, lsl=None, usl=None, target=None):
    """
    구성 요소별 성능 분석
    
    Args:
        df: DataFrame with equipment data
        config_column: Configuration column name (e.g., 'XY Scanner', 'Head Type')
        lsl, usl, target: Spec limits
    
    Returns:
        DataFrame: Configuration statistics with ranking
    """
    if config_column not in df.columns or 'Value' not in df.columns:
        return None
    
    config_stats = []
    
    for config_value, config_df in df.groupby(config_column):
        # NaN이나 빈 값 제외
        if pd.isna(config_value) or (isinstance(config_value, str) and not config_value.strip()):
            continue
        
        measurements = config_df['Value'].dropna()
        
        if len(measurements) == 0:
            continue
        
        mean = measurements.mean()
        std = measurements.std()
        min_val = measurements.min()
        max_val = measurements.max()
        count = len(measurements)
        
        # 장비 수
        n_equipments = config_df['장비명'].nunique() if '장비명' in config_df.columns else 0
        
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
        
        # 신뢰도 판단
        if count >= 30 and n_equipments >= 5:
            confidence = "높음"
        elif count >= 10 and n_equipments >= 2:
            confidence = "보통"
        else:
            confidence = "낮음"
        
        config_stats.append({
            config_column: str(config_value),
            '평균': mean,
            '표준편차': std,
            'Cpk': cpk,
            '장비 수': n_equipments,
            '데이터 수': count,
            '불량률(%)': defect_rate,
            '신뢰도': confidence,
            'Min': min_val,
            'Max': max_val
        })
    
    if len(config_stats) == 0:
        return None
    
    # DataFrame 생성
    df_stats = pd.DataFrame(config_stats)
    
    # Cpk 기준으로 정렬
    if 'Cpk' in df_stats.columns and df_stats['Cpk'].notna().any():
        df_stats = df_stats.sort_values('Cpk', ascending=False, na_position='last')
        df_stats['순위'] = range(1, len(df_stats) + 1)
        
        # 순위 아이콘
        def get_rank_icon(rank, total):
            if rank == 1:
                return "🥇"
            elif rank == 2 and total >= 2:
                return "🥈"
            elif rank == 3 and total >= 3:
                return "🥉"
            elif rank >= total - 1 and total > 3:
                return "⚠️"
            else:
                return ""
        
        df_stats[''] = df_stats['순위'].apply(
            lambda r: get_rank_icon(r, len(df_stats))
        )
        
        # 컬럼 순서
        cols = ['', '순위', config_column, '평균', '표준편차', 'Cpk', 
                '장비 수', '데이터 수', '불량률(%)', '신뢰도', 'Min', 'Max']
        df_stats = df_stats[[c for c in cols if c in df_stats.columns]]
    
    return df_stats


def generate_configuration_insights(df_stats, config_column, lsl=None, usl=None, target=None, unit=''):
    """
    구성별 분석 결과에서 인사이트 생성
    
    Args:
        df_stats: Configuration statistics DataFrame
        config_column: Configuration column name
        lsl, usl, target: Spec limits
        unit: Measurement unit
    
    Returns:
        list: Insight strings
    """
    if df_stats is None or df_stats.empty:
        return []
    
    insights = []
    
    # 1. 최고 성능 구성
    if '순위' in df_stats.columns and len(df_stats) > 0:
        best = df_stats.iloc[0]
        best_config = best[config_column]
        best_cpk = best['Cpk']
        best_equipments = best['장비 수']
        best_confidence = best['신뢰도']
        
        if pd.notna(best_cpk):
            emoji = "🥇" if best_cpk >= 1.67 else "✅" if best_cpk >= 1.33 else "⚠️"
            insights.append(
                f"{emoji} **최고 성능**: {best_config} (Cpk: {best_cpk:.2f}, {best_equipments}대 검증, 신뢰도: {best_confidence})"
            )
    
    # 2. 성능 차이
    if len(df_stats) >= 2 and '평균' in df_stats.columns:
        best = df_stats.iloc[0]
        worst = df_stats.iloc[-1]
        
        if pd.notna(best['평균']) and pd.notna(worst['평균']):
            diff = best['평균'] - worst['평균']
            diff_pct = (abs(diff) / best['평균']) * 100 if best['평균'] != 0 else 0
            
            if diff_pct > 5:
                direction = "우수" if diff < 0 else "높음"
                insights.append(
                    f"📊 **성능 차이**: {best[config_column]}이(가) {worst[config_column]}보다 "
                    f"평균 **{abs(diff):.2f}{unit}** {direction} ({diff_pct:.1f}% 차이)"
                )
    
    # 3. 신뢰도 경고
    low_confidence = df_stats[df_stats['신뢰도'] == '낮음']
    if not low_confidence.empty:
        low_configs = low_confidence[config_column].tolist()
        if len(low_configs) <= 2:
            insights.append(
                f"ℹ️ **데이터 부족**: {', '.join(low_configs)} - 더 많은 데이터로 재분석 권장"
            )
    
    # 4. 신규 구매 추천
    if '순위' in df_stats.columns and len(df_stats) > 0:
        best = df_stats.iloc[0]
        if best['신뢰도'] in ['높음', '보통'] and pd.notna(best['Cpk']):
            if best['Cpk'] >= 1.33:
                insights.append(
                    f"💡 **신규 구매 시 권장**: {best[config_column]} (검증된 데이터 기반)"
                )
    
    # 5. 피해야 할 구성
    if len(df_stats) > 1 and 'Cpk' in df_stats.columns:
        poor_performance = df_stats[df_stats['Cpk'] < 1.0]
        if not poor_performance.empty:
            poor_configs = poor_performance[config_column].tolist()
            if len(poor_configs) <= 2:
                insights.append(
                    f"⚠️ **성능 미달**: {', '.join(poor_configs)} (Cpk < 1.0) - 개선 또는 교체 필요"
                )
    
    return insights


def get_configuration_summary(df_stats, config_column):
    """
    구성별 분석 요약 문장 생성
    
    Args:
        df_stats: Configuration statistics DataFrame
        config_column: Configuration column name
    
    Returns:
        str: Summary sentence
    """
    if df_stats is None or df_stats.empty:
        return f"{config_column}별 데이터가 없습니다."
    
    n_configs = len(df_stats)
    best = df_stats.iloc[0]
    best_config = best[config_column]
    
    if 'Cpk' in df_stats.columns and pd.notna(best['Cpk']):
        return (f"{n_configs}개 {config_column} 비교 결과, "
                f"**{best_config}**이(가) Cpk {best['Cpk']:.2f}로 최고 성능입니다.")
    else:
        return f"{n_configs}개 {config_column}을(를) 비교했습니다."
