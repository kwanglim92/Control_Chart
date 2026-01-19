"""
품질 분석 탭
Quality Analysis Tab

Features:
- 데이터 컨텍스트 카드
- 상세 필터 시스템 (6개 필터)
- 6개 분석 탭:
  - Cpk/Spec 분석
  - 장비 비교
  - 설정 조합 분석
  - 개별 관리도
  - 통계 요약
  - 원본 데이터
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

# Internal modules
# Internal modules
from modules import database as db
from modules.utils import calculate_stats
from modules.charts import create_control_chart


def render_quality_analysis_tab():
    """Tab 2: Quality Analysis"""
    st.header("📈 Control Chart 분석")
    
    if not st.session_state.analysis_triggered:
        st.info("👈 왼쪽 사이드바에서 필터를 선택하고 **'분석 시작'** 버튼을 눌러주세요.")
        return

    display_df = st.session_state.filtered_data
    
    if display_df is None or display_df.empty:
        st.warning("조건에 맞는 데이터가 없습니다.")
        return
        
    # Import render_data_context_card from app module
    # We need to handle this carefully to avoid circular imports
    # For now, let's inline it or consider moving it to a separate utils module
    # Let's inline the function here temporarily
    from app import render_data_context_card
    
    # --- Local Date Range Filter ---
    st.markdown("##### 📅 분석 기간 설정")
    
    min_date = display_df['종료일'].min().date()
    max_date = display_df['종료일'].max().date()
    
    # Ensure min <= max
    if min_date > max_date:
        min_date, max_date = max_date, min_date
        
    c_filter1, c_filter2 = st.columns([1, 3])
    with c_filter1:
        date_range = st.date_input(
            "기간 선택",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key='analysis_date_range'
        )
        
    # Apply Filter
    if len(date_range) == 2:
        start_d, end_d = date_range
        mask = (display_df['종료일'].dt.date >= start_d) & (display_df['종료일'].dt.date <= end_d)
        display_df = display_df.loc[mask]
        
    if display_df.empty:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return
        
    st.caption(f"선택 기간: {date_range[0]} ~ {date_range[1] if len(date_range)>1 else date_range[0]} | 데이터 수: {len(display_df)}건")
    st.divider()
    # -------------------------------
    
    # ========== 데이터 컨텍스트 카드 (Phase 0) ==========
    render_data_context_card(display_df)
    st.divider()
    # ==================================================
    
    # ========== 상세 필터 (Phase 1) ==========
    st.markdown("### 🔍 상세 필터")
    st.caption("💡 아래 필터를 사용하여 데이터를 세밀하게 탐색할 수 있습니다. 차트만 업데이트됩니다.")
    
    with st.container(border=True):
        # 2행 3열 레이아웃
        filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)
        filter_row2_col1, filter_row2_col2, filter_row2_col3 = st.columns(3)
        
        # Row 1
        with filter_row1_col1:
            st.markdown("**📋 Check Items**")
            available_items = sorted(display_df['Check Items'].unique().tolist()) if 'Check Items' in display_df.columns else []
            selected_items = st.multiselect(
                "항목 선택",
                options=available_items,
                default=available_items,
                key='filter_check_items',
                label_visibility='collapsed',
                help="분석할 Check Items를 선택하세요"
            )
        
        with filter_row1_col2:
            st.markdown("**🔎 장비명 검색**")
            equipment_search = st.text_input(
                "장비명 입력",
                placeholder="Samsung, LG, WD...",
                key='filter_equipment_search',
                label_visibility='collapsed',
                help="장비명의 일부를 입력하여 필터링"
            )
        
        with filter_row1_col3:
            st.markdown("**📦 Model**")
            available_models = sorted(display_df['Model'].unique().tolist()) if 'Model' in display_df.columns else []
            selected_models = st.multiselect(
                "모델 선택",
                options=available_models,
                default=available_models,
                key='filter_models',
                label_visibility='collapsed',
                help="분석할 모델을 선택하세요"
            )
        
        # Row 2
        with filter_row2_col1:
            st.markdown("**🔬 XY Scanner**")
            available_scanners = sorted(display_df['XY Scanner'].dropna().unique().tolist()) if 'XY Scanner' in display_df.columns else []
            # 빈 문자열 제거
            available_scanners = [s for s in available_scanners if s and str(s).strip()]
            selected_scanners = st.multiselect(
                "Scanner 선택",
                options=available_scanners,
                default=available_scanners,
                key='filter_scanners',
                label_visibility='collapsed',
                help="Scanner 타입별 필터링"
            )
        
        with filter_row2_col2:
            st.markdown("**🎯 Head Type**")
            available_heads = sorted(display_df['Head Type'].dropna().unique().tolist()) if 'Head Type' in display_df.columns else []
            # 빈 문자열 제거
            available_heads = [h for h in available_heads if h and str(h).strip()]
            selected_heads = st.multiselect(
                "Head 선택",
                options=available_heads,
                default=available_heads,
                key='filter_heads',
                label_visibility='collapsed',
                help="Head 타입별 필터링"
            )
        
        with filter_row2_col3:
            # 필터 제어
            st.markdown("**⚙️ 필터 제어**")
            col_reset, col_info = st.columns([1, 1])
            with col_reset:
                if st.button("🔄 초기화", use_container_width=True, help="모든 필터를 기본값으로 복원"):
                    # Session state 초기화
                    for key in ['filter_check_items', 'filter_equipment_search', 
                               'filter_models', 'filter_scanners', 'filter_heads']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            with col_info:
                # 필터 상태 표시
                active_filters = 0
                if selected_items and len(selected_items) < len(available_items):
                    active_filters += 1
                if equipment_search and equipment_search.strip():
                    active_filters += 1
                if selected_models and len(selected_models) < len(available_models):
                    active_filters += 1
                if selected_scanners and len(selected_scanners) < len(available_scanners):
                    active_filters += 1
                if selected_heads and len(selected_heads) < len(available_heads):
                    active_filters += 1
                
                if active_filters > 0:
                    st.metric("활성 필터", f"{active_filters}개", delta="필터링 중", delta_color="off")
                else:
                    st.info("전체\\n데이터")
    
    st.divider()
    # =========================================
    
    # ========== 필터 적용 로직 (Task 1.2) ==========
    filtered_df = display_df.copy()
    
    # 1. Check Items 필터
    if selected_items:
        filtered_df = filtered_df[filtered_df['Check Items'].isin(selected_items)]
    
    # 2. 장비명 검색 필터 (대소문자 무시, 부분 일치)
    if equipment_search and equipment_search.strip():
        filtered_df = filtered_df[
            filtered_df['장비명'].str.contains(equipment_search, case=False, na=False, regex=False)
        ]
    
    # 3. Model 필터
    if selected_models:
        filtered_df = filtered_df[filtered_df['Model'].isin(selected_models)]
    
    # 4. Scanner 필터
    if selected_scanners:
        filtered_df = filtered_df[filtered_df['XY Scanner'].isin(selected_scanners)]
    
    # 5. Head 필터
    if selected_heads:
        filtered_df = filtered_df[filtered_df['Head Type'].isin(selected_heads)]
    
    # 필터 결과 표시
    if filtered_df.empty:
        st.warning("⚠️ 선택한 조건에 맞는 데이터가 없습니다. 필터를 조정해주세요.")
        # 필터 초기화 제안
        if st.button("🔄 필터 초기화하기"):
            for key in ['filter_check_items', 'filter_equipment_search', 
                       'filter_models', 'filter_scanners', 'filter_heads']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        return
    
    # 데이터 변경 안내 (필터 적용됨)
    if len(filtered_df) < len(display_df):
        col_filter_info1, col_filter_info2 = st.columns([3, 1])
        with col_filter_info1:
            st.success(
                f"📋 필터 적용 완료: **{len(filtered_df):,}개** 데이터 "
                f"({len(filtered_df['장비명'].unique())}개 장비)"
            )
        with col_filter_info2:
            reduction = (1 - len(filtered_df) / len(display_df)) * 100
            st.metric("필터율", f"{reduction:.1f}%", delta=f"-{len(display_df) - len(filtered_df)}개")
    
    # 필터링된 데이터를 display_df로 교체
    display_df = filtered_df
    # ===============================================
    
    # ========== 현재 필터 조건 표시 (Task 1.3) ==========
    with st.expander("📋 현재 필터 조건", expanded=False):
        filter_summary = []
        
        # 기본 미터릭
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            st.metric("적용 필터", f"{active_filters}개")
        with col_metric2:
            st.metric("최종 데이터", f"{len(display_df)}개")
        with col_metric3:
            st.metric("장비 수", f"{display_df['장비명'].nunique()}대")
        
        st.divider()
        
        # 상세 조건
        if selected_items and len(selected_items) < len(available_items):
            selected_str = ", ".join(selected_items[:5])
            if len(selected_items) > 5:
                selected_str += f" 외 {len(selected_items) - 5}개"
            filter_summary.append(f"**Check Items**: {selected_str}")
        
        if equipment_search and equipment_search.strip():
            filter_summary.append(f"**장비명 검색**: '{equipment_search}'")
        
        if selected_models and len(selected_models) < len(available_models):
            models_str = ", ".join(selected_models)
            filter_summary.append(f"**Model**: {models_str}")
        
        if selected_scanners and len(selected_scanners) < len(available_scanners):
            scanner_str = ", ".join(selected_scanners[:3])
            if len(selected_scanners) > 3:
                scanner_str += f" 외 {len(selected_scanners) - 3}개"
            filter_summary.append(f"**XY Scanner**: {scanner_str}")
        
        if selected_heads and len(selected_heads) < len(available_heads):
            heads_str = ", ".join(selected_heads[:3])
            if len(selected_heads) > 3:
                heads_str += f" 외 {len(selected_heads) - 3}개"
            filter_summary.append(f"**Head Type**: {heads_str}")
        
        if filter_summary:
            st.markdown("적용 중인 필터:")
            for item in filter_summary:
                st.markdown(f"- {item}")
        else:
            st.info("모든 필터가 기본 상태입니다. (전체 데이터 표시)")
    # ===============================================
        
    # Tabs for Analysis Sub-views
    tab1, tab_spec, tab_equip, tab3, tab4 = st.tabs([
        "📈 Trend 분석", 
        "📊 SPEC 분석", 
        "🏭 장비 비교", 
        "📉 통계 요약", 
        "💾 데이터"
    ])
    
    # Simplified Grouping Options (Time-based only)
    group_options = ['None', '연도', '분기', '월']
    
    with tab1:
        st.subheader("📈 Trend 분석 (시계열 Control Chart)")
        
        c1, c2 = st.columns([1, 3])
        with c1:
            group_by_selection = st.selectbox("그룹화 기준 (시간)", group_options, index=0, key='combined_group')
            show_violations = st.checkbox("Rule of Seven / Trend 표시", value=True, key='combined_viol')
            
        # Logic to determine actual group column
        if group_by_selection == 'None':
            if display_df['Check Items'].nunique() > 1:
                group_col = 'Check Items'
                st.caption("ℹ️ 'None' 선택 시, 항목(Check Items)별로 구분됩니다.")
            else:
                item_name = display_df['Check Items'].iloc[0]
                display_df[item_name] = item_name
                group_col = item_name
        elif group_by_selection == '연도':
            group_col = '연도'
        elif group_by_selection == '분기':
            if '분기' not in display_df.columns:
                 display_df['분기'] = display_df['종료일'].dt.to_period('Q').astype(str)
            display_df['YearQuarter'] = display_df['연도'] + '-' + display_df['분기'] + 'Q'
            group_col = 'YearQuarter'
        elif group_by_selection == '월':
            display_df['YearMonth'] = display_df['연도'] + '-' + display_df['월']
            group_col = 'YearMonth'
            
        # 이중 축 로직
        use_dual_axis = False
        if group_col == 'Check Items' and display_df['Check Items'].nunique() == 2:
            use_dual_axis = st.checkbox("이중 Y축 사용", value=True, key='combined_dual')
            
        # Spec Fetching Logic
        specs = None
        unique_models = display_df['Model'].unique()
        unique_items = display_df['Check Items'].unique()
        
        if len(unique_models) == 1 and len(unique_items) == 1:
            specs = db.get_spec_for_item(unique_models[0], unique_items[0])
            if specs and all(v is None for v in specs.values()):
                specs = None
            
        try:
            fig_combined = create_control_chart(
                display_df, 
                group_col=group_col,
                equipment_col='장비명',
                show_violations=show_violations,
                use_dual_axis=use_dual_axis,
                specs=specs
            )
            st.plotly_chart(fig_combined, use_container_width=True)
        except Exception as e:
            st.error(f"차트 생성 오류: {e}")
    
    # ========== 스펙 분석 탭 (Phase 2 - NEW) ==========
    with tab_spec:
        st.subheader("📊 스펙 분석 (Spec Analysis with Cpk)")
        st.caption("💡 공정 능력 지수(Cpk)를 자동 계산하고, 스펙 적정성을 평가합니다.")
        
        from modules.spec_analysis import (
            prepare_spec_data,
            calculate_process_capability,
            create_histogram_with_specs,
            generate_insights
        )
        
        # Check Item 선택
        unique_items = display_df['Check Items'].unique().tolist() if 'Check Items' in display_df.columns else []
        
        if len(unique_items) == 0:
            st.warning("⚠️ Check Item이 없습니다.")
        elif len(unique_items) == 1:
            selected_spec_item = unique_items[0]
            st.info(f"분석 항목: **{selected_spec_item}**")
        else:
            selected_spec_item = st.selectbox(
                "분석 항목 선택",
                unique_items,
                key='spec_analysis_item',
                help="Cpk를 계산할 Check Item을 선택하세요"
            )
        
        if len(unique_items) > 0:
            item_df = display_df[display_df['Check Items'] == selected_spec_item]
            
            # 1. 데이터 준비
            data = prepare_spec_data(item_df)
            
            if data is None or len(data['measurements']) == 0:
                st.warning("⚠️ 선택한 항목에 측정 데이터가 없습니다.")
            else:
                # 2. 통계 계산
                stats = calculate_process_capability(data, data['lsl'], data['usl'])
                
                # 3. 핵심 지표 표시
                st.markdown("#### 📈 핵심 공정 지표")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if stats['cpk'] is not None:
                        cpk_val = stats['cpk']
                        if cpk_val >= 1.67:
                            delta_text = "✅ 매우우수"
                            delta_color = "normal"
                        elif cpk_val >= 1.33:
                            delta_text = "✅ 우수"
                            delta_color = "normal"
                        elif cpk_val >= 1.0:
                            delta_text = "🟡 양호"
                            delta_color = "off"
                        else:
                            delta_text = "🔴 부적합"
                            delta_color = "inverse"
                        
                        st.metric(
                            "Cpk (공정능력)",
                            f"{cpk_val:.2f}",
                            delta=delta_text,
                            delta_color=delta_color,
                            help="Cpk >= 1.33: 우수, >= 1.0: 양호, < 1.0: 부적합"
                        )
                    else:
                        st.metric("Cpk", "N/A", help="스펙 정보 없음")
                
                with col2:
                    if stats['mean'] is not None:
                        st.metric(
                            "평균",
                            f"{stats['mean']:.2f} {data['unit']}",
                            help=f"측정값 평균 ({stats['n']}개 데이터)"
                        )
                    else:
                        st.metric("평균", "N/A")
                
                with col3:
                    if stats['std'] is not None:
                        st.metric(
                            "표준편차 (σ)",
                            f"{stats['std']:.2f} {data['unit']}",
                            help="공정 변동성 지표"
                        )
                    else:
                        st.metric("표준편차", "N/A")
                
                with col4:
                    if stats['margin'] is not None:
                        margin = stats['margin']
                        if margin > 40:
                            delta_text = "🔵 여유 많음"
                            delta_color = "normal"
                        elif margin > 20:
                            delta_text = "✅ 적정"
                            delta_color = "normal"
                        elif margin > 10:
                            delta_text = "⚠️ 주의"
                            delta_color = "off"
                        else:
                            delta_text = "🔴 부족"
                            delta_color = "inverse"
                        
                        st.metric(
                            "스펙 여유도",
                            f"{margin:.1f}%",
                            delta=delta_text,
                            delta_color=delta_color,
                            help="스펙 대비 공정 변동 여유 공간"
                        )
                    else:
                        st.metric("스펙 여유도", "N/A")
                
                st.divider()
                
                # 4. 히스토그램 + 스펙 라인
                st.markdown("#### 📊 측정값 분포")
                
                fig = create_histogram_with_specs(data, stats)
                st.plotly_chart(fig, use_container_width=True)
                
                # 5. 인사이트
                st.markdown("#### 💡 분석 결과 및 권장사항")
                
                insights = generate_insights(data, stats)
                for insight in insights:
                    st.markdown(f"- {insight}")
                
                # 6. 상세 통계 (Expander)
                with st.expander("📋 상세 통계", expanded=False):
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        st.markdown("**스펙 정보**")
                        st.json({
                            'Check Item': data['item'],
                            'LSL (Min)': data['lsl'],
                            'Target (Criteria)': data['target'],
                            'USL (Max)': data['usl'],
                            'Unit': data['unit']
                        })
                    
                    with col_detail2:
                        st.markdown("**공정 통계**")
                        st.json({
                            '평균': round(stats['mean'], 4) if stats['mean'] else None,
                            '표준편차': round(stats['std'], 4) if stats['std'] else None,
                            'Cp': round(stats['cp'], 3) if stats['cp'] else None,
                            'Cpk': round(stats['cpk'], 3) if stats['cpk'] else None,
                            'CPU': round(stats['cpu'], 3) if stats['cpu'] else None,
                            'CPL': round(stats['cpl'], 3) if stats['cpl'] else None,
                            '스펙 여유도 (%)': round(stats['margin'], 2) if stats['margin'] else None,
                            '불량률 (%)': round(stats['defect_rate'], 2) if stats['defect_rate'] else None,
                            '스펙 외부 개수': stats['n_out_of_spec'],
                            '데이터 수': stats['n'],
                            '장비 수': data['n_equipments']
                        })
    # =================================================
        
    with tab_equip:
        st.subheader("🏭 장비 비교 (Equipment Comparison)")
        st.caption("💡 장비 간 성능 차이를 분석하고, 문제 장비를 자동으로 식별합니다.")
        
        # Check Item 선택
        unique_items_equip = display_df['Check Items'].unique().tolist() if 'Check Items' in display_df.columns else []
        with c1:
            group_by_stat_sel = st.selectbox("그룹화 기준 (통계)", group_options, index=0, key='stat_group')
            
        if group_by_stat_sel == 'None':
            if display_df['Check Items'].nunique() > 1:
                group_col_stat = 'Check Items'
            else:
                item_name = display_df['Check Items'].iloc[0]
                display_df[item_name] = item_name 
                group_col_stat = item_name
        elif group_by_stat_sel == '연도':
            group_col_stat = '연도'
        elif group_by_stat_sel == '분기':
            display_df['YearQuarter'] = display_df['연도'] + '-' + display_df['분기'] + 'Q'
            group_col_stat = 'YearQuarter'
        elif group_by_stat_sel == '월':
            display_df['YearMonth'] = display_df['연도'] + '-' + display_df['월']
            group_col_stat = 'YearMonth'
            
        stats_list = []
        for name, group in display_df.groupby(group_col_stat):
            s = calculate_stats(group['Value'].values)
            stats_list.append({
                '그룹': name,
                'Count': s['count'],
                'AVG': round(s['avg'], 3),
                'STD': round(s['std'], 3),
                'UCL': round(s['ucl'], 3),
                'LCL': round(s['lcl'], 3),
                'Min': round(s['min'], 3),
                'Max': round(s['max'], 3)
            })
            
        if stats_list:
            st.dataframe(pd.DataFrame(stats_list), use_container_width=True)
        else:
            st.info("통계 데이터가 없습니다.")
        
    with tab4:
        st.subheader("💾 필터링된 원본 데이터")
        st.dataframe(display_df, use_container_width=True)
