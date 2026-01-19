"""
Equipment Comparison Tab Renderer
장비 비교 탭 렌더링 함수
"""
import streamlit as st
from .spec_analysis import prepare_spec_data
from .equipment_comparison import (
    create_equipment_comparison_table,
    create_equipment_boxplot,
    detect_outlier_equipments
)


def render_equipment_comparison_content(display_df, selected_equip_item):
    """
    장비 비교 탭의 내용을 렌더링
    
    Args:
        display_df: 전체 필터링된 데이터
        selected_equip_item: 선택된 Check Item
    """
    item_equip_df = display_df[display_df['Check Items'] == selected_equip_item].copy()
    
    if item_equip_df.empty or '장비명' not in item_equip_df.columns:
        st.warning("⚠️ 선택한 항목에 장비 데이터가 없습니다.")
        return
    
    # 스펙 정보 추출
    spec_data = prepare_spec_data(item_equip_df)
    lsl = spec_data['lsl'] if spec_data else None
    usl = spec_data['usl'] if spec_data else None
    target = spec_data['target'] if spec_data else None
    unit = spec_data['unit'] if spec_data else ''
    
    # Task 3.1: 장비별 통계 테이블
    st.markdown("#### 📊 장비별 성능 통계")
    
    df_stats = create_equipment_comparison_table(item_equip_df, lsl, usl, target)
    
    if df_stats is None or df_stats.empty:
        st.warning("⚠️ 장비별 데이터가 없습니다.")
        return
    
    st.dataframe(
        df_stats,
        use_container_width=True,
        hide_index=True,
        column_config={
            '': st.column_config.TextColumn('', width='small'),
            '순위': st.column_config.NumberColumn('순위', width='small'),
            '장비명': st.column_config.TextColumn('장비명', width='medium'),
            '평균': st.column_config.NumberColumn('평균', format=f'%.2f {unit}'),
            '표준편차': st.column_config.NumberColumn('σ', format=f'%.2f {unit}'),
            'Cpk': st.column_config.NumberColumn('Cpk', format='%.2f'),
            '데이터 수': st.column_config.NumberColumn('Count', width='small'),
            '불량 개수': st.column_config.NumberColumn('불량', width='small'),
            '불량률(%)': st.column_config.NumberColumn('불량률', format='%.1f%%', width='small'),
            'Min': st.column_config.NumberColumn('Min', format=f'%.2f'),
            'Max': st.column_config.NumberColumn('Max', format=f'%.2f')
        }
    )
    
    st.caption(f"📊 총 **{len(df_stats)}개** 장비 비교 중")
    st.divider()
    
    # Task 3.2: Box Plot
    st.markdown("#### 📦 장비별 측정값 분포 (Box Plot)")
    
    fig_box = create_equipment_boxplot(item_equip_df, lsl, usl, target, unit)
    if fig_box:
        st.plotly_chart(fig_box, use_container_width=True)
    
    st.divider()
    
    # Task 3.3: 아웃라이어 감지
    st.markdown("#### ⚠️ 이상 장비 감지")
    
    outliers, overall_mean, overall_std, lower_th, upper_th = detect_outlier_equipments(
        item_equip_df, df_stats
    )
    
    if outliers:
        st.warning(f"⚠️ **{len(outliers)}개 장비**가 전체 평균에서 크게 벗어났습니다! (±2σ 기준)")
        
        for outlier in outliers:
            direction = "높습니다" if outlier['차이'] > 0 else "낮습니다"
            emoji = "🔴" if abs(outlier['차이율(%)']) > 10 else "⚠️"
            
            st.markdown(
                f"{emoji} **{outlier['장비명']}**: "
                f"평균이 전체보다 **{outlier['차이']:+.2f}{unit}** {direction} "
                f"({outlier['차이율(%)']:+.1f}%) → 점검 필요"
            )
    else:
        st.success("✅ 모든 장비가 정상 범위 내에 있습니다. (±2σ)")
    
    # 추가 정보
    with st.expander("📋 기준 정보"):
        col_ref1, col_ref2 = st.columns(2)
        with col_ref1:
            st.markdown("**전체 통계**")
            st.metric("전체 평균", f"{overall_mean:.2f} {unit}")
            st.metric("전체 표준편차", f"{overall_std:.2f} {unit}")
        with col_ref2:
            st.markdown("**정상 범위 (±2σ)**")
            st.metric("하한", f"{lower_th:.2f} {unit}")
            st.metric("상한", f"{upper_th:.2f} {unit}")
    
    st.divider()
    
    # Phase 4-Lite: 구성별 분석
    with st.expander("🔬 구성별 성능 비교 (고급 분석)", expanded=False):
        st.caption("💡 Scanner, Head Type 등 구성 요소별 성능 차이를 확인하세요")
        st.caption("⚙️ 장비 구매나 업그레이드 시 데이터 기반 의사결정에 활용할 수 있습니다")
        
        from .configuration_analysis import (
            analyze_by_configuration,
            generate_configuration_insights,
            get_configuration_summary
        )
        
        available_configs = []
        config_display_names = {
            'XY Scanner': '🔬 XY Scanner',
            'Head Type': '🎯 Head Type',
            'MOD/VIT': '⚡ MOD/VIT'
        }
        
        for col in ['XY Scanner', 'Head Type', 'MOD/VIT']:
            if col in item_equip_df.columns:
                unique_vals = item_equip_df[col].dropna().unique()
                unique_vals = [v for v in unique_vals if v and str(v).strip()]
                if len(unique_vals) >= 2:
                    available_configs.append(col)
        
        if not available_configs:
            st.info("ℹ️ 구성별 비교를 위해서는 2개 이상의 서로 다른 구성 데이터가 필요합니다.")
        else:
            display_options = [config_display_names.get(c, c) for c in available_configs]
            selected_display = st.selectbox(
                "비교할 구성 요소 선택",
                display_options,
                key='config_analysis_selector'
            )
            
            selected_config = available_configs[display_options.index(selected_display)]
            
            df_config_stats = analyze_by_configuration(
                item_equip_df, selected_config, lsl, usl, target
            )
            
            if df_config_stats is not None and not df_config_stats.empty:
                summary = get_configuration_summary(df_config_stats, selected_config)
                st.info(f"📋 {summary}")
                
                st.markdown(f"##### {selected_display} 성능 비교")
                st.dataframe(df_config_stats, use_container_width=True, hide_index=True)
                
                insights = generate_configuration_insights(
                    df_config_stats, selected_config, lsl, usl, target, unit
                )
                
                if insights:
                    st.markdown("##### 💡 주요 인사이트")
                    for insight in insights:
                        st.markdown(f"- {insight}")
