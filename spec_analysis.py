"""
스펙 분석 및 공정 능력 계산 모듈
품질엔지니어를 위한 Cpk, Cp, 스펙 여유도, 불량률 등 자동 계산 및 시각화
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats as scipy_stats
import streamlit as st


def prepare_spec_data(df):
    """
    Check Item별 스펙 정보 추출 및 일관성 확인
    
    Args:
        df: DataFrame with measurement data (single Check Item assumed)
    
    Returns:
        dict: {
            'item': Check Item name,
            'lsl': Lower Spec Limit,
            'target': Target/Criteria,
            'usl': Upper Spec Limit,
            'measurements': numpy array of measurement values,
            'unit': measurement unit,
            'equipments': list of equipment names,
            'n_equipments': count of unique equipments
        }
    """
    if df.empty:
        return None
    
    item = df['Check Items'].iloc[0] if 'Check Items' in df.columns else 'Unknown'
    
    # Min/Criteria/Max 추출 (measurements 테이블에서는 specs에서 조회해야 함)
    # 여기서는 데이터에 이미 포함되어 있다고 가정
    min_vals = df['Min'].dropna().unique() if 'Min' in df.columns else np.array([])
    crit_vals = df['Criteria'].dropna().unique() if 'Criteria' in df.columns else np.array([])
    max_vals = df['Max'].dropna().unique() if 'Max' in df.columns else np.array([])
    
    # 스펙 일관성 확인
    inconsistent = False
    if len(min_vals) > 1 or len(crit_vals) > 1 or len(max_vals) > 1:
        inconsistent = True
        st.warning(f"⚠️ '{item}' 항목의 스펙이 데이터 간 불일치합니다!")
        
        # 불일치 데이터 표시
        spec_comparison = df[['장비명', 'Min', 'Criteria', 'Max']].drop_duplicates() if '장비명' in df.columns else df[['Min', 'Criteria', 'Max']].drop_duplicates()
        with st.expander("스펙 불일치 상세"):
            st.dataframe(spec_comparison)
    
    # 대표값 사용 (첫 번째 값)
    lsl = min_vals[0] if len(min_vals) > 0 else None
    target = crit_vals[0] if len(crit_vals) > 0 else None
    usl = max_vals[0] if len(max_vals) > 0 else None
    
    # 측정값 추출
    measurements = df['Value'].dropna() if 'Value' in df.columns else df['Measurement'].dropna() if 'Measurement' in df.columns else pd.Series([])
    
    # Unit 추출
    unit = df['Unit'].iloc[0] if 'Unit' in df.columns and not df['Unit'].isna().all() else ''
    
    # 장비 정보
    equipments = df['장비명'].unique().tolist() if '장비명' in df.columns else []
    
    return {
        'item': item,
        'lsl': lsl,
        'target': target,
        'usl': usl,
        'measurements': measurements.values,
        'unit': unit,
        'equipments': equipments,
        'n_equipments': len(equipments),
        'inconsistent': inconsistent
    }


def calculate_process_capability(data, lsl, usl):
    """
    공정 능력 지수 계산 (Cp, Cpk, 스펙 여유도, 불량률)
    
    Args:
        data: dict from prepare_spec_data
        lsl: Lower Spec Limit
        usl: Upper Spec Limit
    
    Returns:
        dict: {
            'mean': 평균,
            'std': 표준편차,
            'cp': 공정 능력 (Cp),
            'cpk': 공정 능력 지수 (Cpk),
            'cpu': Upper Capability Index,
            'cpl': Lower Capability Index,
            'margin': 스펙 여유도 (%),
            'defect_rate': 불량률 (%),
            'n_out_of_spec': 스펙 외부 개수,
            'n': 데이터 개수
        }
    """
    measurements = data['measurements']
    
    if len(measurements) == 0:
        return {
            'mean': None, 'std': None, 'cp': None, 'cpk': None,
            'cpu': None, 'cpl': None, 'margin': None,
            'defect_rate': None, 'n_out_of_spec': 0, 'n': 0
        }
    
    mean = measurements.mean()
    std = measurements.std()
    
    result = {
        'mean': mean,
        'std': std,
        'cp': None,
        'cpk': None,
        'cpu': None,
        'cpl': None,
        'margin': None,
        'defect_rate': None,
        'n_out_of_spec': 0,
        'n': len(measurements)
    }
    
    # Cp 계산 (공정 능력)
    if lsl is not None and usl is not None and std > 0:
        result['cp'] = (usl - lsl) / (6 * std)
    
    # Cpk 계산 (공정 능력 지수)
    if lsl is not None and usl is not None and std > 0:
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        result['cpu'] = cpu
        result['cpl'] = cpl
        result['cpk'] = min(cpu, cpl)
    
    # 불량률 계산
    if lsl is not None and usl is not None:
        out_of_spec = ((measurements < lsl) | (measurements > usl)).sum()
        result['n_out_of_spec'] = int(out_of_spec)
        result['defect_rate'] = (out_of_spec / len(measurements)) * 100
    
    # 스펙 여유도 계산 (%)
    if lsl is not None and usl is not None and std > 0:
        spec_range = usl - lsl
        process_range = 6 * std
        result['margin'] = ((spec_range - process_range) / spec_range) * 100
    
    return result


def create_histogram_with_specs(data, stats):
    """
    히스토그램 + 스펙 라인 + 정규분포 곡선 생성
    
    Args:
        data: dict from prepare_spec_data
        stats: dict from calculate_process_capability
    
    Returns:
        plotly Figure
    """
    measurements = data['measurements']
    lsl = data['lsl']
    target = data['target']
    usl = data['usl']
    unit = data['unit']
    item = data['item']
    
    if len(measurements) == 0:
        # 빈 차트
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 없습니다",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    fig = go.Figure()
    
    # 1. 히스토그램 (실측값 분포)
    fig.add_trace(go.Histogram(
        x=measurements,
        name='측정값 분포',
        nbinsx=min(30, len(measurements) // 2),
        marker_color='lightblue',
        opacity=0.7,
        histnorm='probability density',
        hovertemplate='값: %{x}<br>빈도: %{y}<extra></extra>'
    ))
    
    # 2. 정규분포 곡선 (이론적 분포)
    if stats['mean'] is not None and stats['std'] is not None and stats['std'] > 0:
        x_range = np.linspace(measurements.min(), measurements.max(), 200)
        normal_curve = scipy_stats.norm.pdf(x_range, stats['mean'], stats['std'])
        
        fig.add_trace(go.Scatter(
            x=x_range,
            y=normal_curve,
            mode='lines',
            name='정규분포 (이론)',
            line=dict(color='blue', width=2, dash='dash'),
            hovertemplate='값: %{x:.4f}<br>확률밀도: %{y:.6f}<extra></extra>'
        ))
    
    # 3. 스펙 라인 (LSL, Target, USL)
    max_y = normal_curve.max() * 1.1 if 'normal_curve' in locals() else 1
    
    if lsl is not None:
        fig.add_vline(
            x=lsl,
            line_color='red',
            line_width=3,
            line_dash='solid',
            annotation_text=f'LSL: {lsl}{unit}',
            annotation_position='top',
            annotation=dict(font=dict(color='red', size=12))
        )
    
    if target is not None:
        fig.add_vline(
            x=target,
            line_color='green',
            line_width=3,
            line_dash='dash',
            annotation_text=f'Target: {target}{unit}',
            annotation_position='top',
            annotation=dict(font=dict(color='green', size=12))
        )
    
    if usl is not None:
        fig.add_vline(
            x=usl,
            line_color='red',
            line_width=3,
            line_dash='solid',
            annotation_text=f'USL: {usl}{unit}',
            annotation_position='top',
            annotation=dict(font=dict(color='red', size=12))
        )
    
    # 4. 평균선
    if stats['mean'] is not None:
        fig.add_vline(
            x=stats['mean'],
            line_color='darkblue',
            line_width=2,
            line_dash='dot',
            annotation_text=f"평균: {stats['mean']:.2f}{unit}",
            annotation_position='bottom',
            annotation=dict(font=dict(color='darkblue', size=10))
        )
    
    # 5. ±3σ 영역 (공정 변동 범위)
    if stats['mean'] is not None and stats['std'] is not None:
        lower_3sigma = stats['mean'] - 3 * stats['std']
        upper_3sigma = stats['mean'] + 3 * stats['std']
        
        fig.add_vrect(
            x0=lower_3sigma,
            x1=upper_3sigma,
            fillcolor='yellow',
            opacity=0.1,
            layer='below',
            annotation_text='±3σ (99.7% 범위)',
            annotation_position='top left',
            annotation=dict(font=dict(size=9))
        )
    
    # 레이아웃 설정
    fig.update_layout(
        title=f"스펙 분석: {item}",
        xaxis_title=f"측정값 ({unit})" if unit else "측정값",
        yaxis_title="확률 밀도",
        showlegend=True,
        height=500,
        hovermode='x unified',
        bargap=0.05
    )
    
    return fig


def generate_insights(data, stats):
    """
    데이터 분석 결과 기반 자동 인사이트 생성
    
    Args:
        data: dict from prepare_spec_data
        stats: dict from calculate_process_capability
    
    Returns:
        list of insight strings
    """
    insights = []
    
    # 1. 스펙 준수 여부
    if stats['defect_rate'] is not None:
        if stats['defect_rate'] == 0:
            insights.append("✅ 모든 측정값이 스펙 범위 내에 있습니다!")
        elif stats['defect_rate'] < 0.5:
            insights.append(f"⚠️ {stats['defect_rate']:.2f}% ({stats['n_out_of_spec']}개)가 스펙 외부입니다. 주의 필요.")
        elif stats['defect_rate'] < 3:
            insights.append(f"🔴 {stats['defect_rate']:.1f}% ({stats['n_out_of_spec']}개)가 스펙을 벗어났습니다! 조치 필요!")
        else:
            insights.append(f"🚨 {stats['defect_rate']:.1f}%가 스펙 외부입니다! 즉시 공정 점검 필요!")
    
    # 2. Cpk 평가
    if stats['cpk'] is not None:
        if stats['cpk'] >= 2.0:
            insights.append("✅ Cpk ≥ 2.0: 탁월한 공정 능력! Six Sigma 수준입니다.")
        elif stats['cpk'] >= 1.67:
            insights.append("✅ Cpk ≥ 1.67: 매우 우수한 공정 능력입니다.")
        elif stats['cpk'] >= 1.33:
            insights.append("✅ Cpk ≥ 1.33: 우수한 공정 능력입니다.")
        elif stats['cpk'] >= 1.0:
            insights.append("⚠️ Cpk ≥ 1.0: 공정 능력 양호하나 개선 여지가 있습니다.")
        else:
            insights.append("🔴 Cpk < 1.0: 공정 능력 부족! 공정 개선 필요!")
    
    # 3. 스펙 여유도
    if stats['margin'] is not None:
        if stats['margin'] > 50:
            insights.append(f"💡 스펙 여유도 {stats['margin']:.1f}%: 스펙을 더 타이트하게 설정할 수 있습니다. 고객 요구사항 재검토 권장.")
        elif stats['margin'] > 30:
            insights.append(f"💡 스펙 여유도 {stats['margin']:.1f}%: 스펙을 더 타이트하게 설정 가능합니다.")
        elif stats['margin'] > 10:
            insights.append(f"✅ 스펙 여유도 {stats['margin']:.1f}%: 적정한 스펙 설정입니다.")
        elif stats['margin'] > 0:
            insights.append(f"⚠️ 스펙 여유도 {stats['margin']:.1f}%: 스펙이 다소 타이트합니다. 불량률 증가 위험 있음.")
        else:
            insights.append(f"🔴 스펙 여유도 {stats['margin']:.1f}%: 스펙이 너무 타이트합니다! 공정 변동만으로도 불량 발생 가능!")
    
    # 4. 중심 편향 (평균이 목표값에서 벗어남)
    if data['target'] is not None and stats['mean'] is not None and stats['std'] is not None and stats['std'] > 0:
        bias = stats['mean'] - data['target']
        if abs(bias) > stats['std']:
            direction = "높습니다" if bias > 0 else "낮습니다"
            insights.append(f"⚠️ 평균이 목표값보다 {abs(bias):.2f}{data['unit']} {direction}. 공정 중심 조정 필요.")
        elif abs(bias) > 0.5 * stats['std']:
            direction = "높습니다" if bias > 0 else "낮습니다"
            insights.append(f"ℹ️ 평균이 목표값보다 {abs(bias):.2f}{data['unit']} {direction}. 모니터링 권장.")
    
    # 5. 데이터 개수
    if stats['n'] < 30:
        insights.append(f"ℹ️ 데이터 수({stats['n']}개)가 적습니다. 신뢰성 향상을 위해 더 많은 데이터로 재분석 권장.")
    
    # 6. Cp vs Cpk 비교 (중심 정렬 평가)
    if stats['cp'] is not None and stats['cpk'] is not None:
        ratio = stats['cpk'] / stats['cp']
        if ratio < 0.75:
            insights.append(f"⚠️ Cpk/Cp = {ratio:.2f}: 공정 중심이 목표값에서 크게 벗어났습니다. 중심 정렬 필요!")
        elif ratio < 0.9:
            insights.append(f"ℹ️ Cpk/Cp = {ratio:.2f}: 공정 중심 정렬 개선 여지가 있습니다.")
    
    return insights
