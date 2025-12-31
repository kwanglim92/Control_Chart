"""
승인 검증 시스템을 위한 유틸리티 함수들
"""
import pandas as pd
from io import BytesIO
from datetime import datetime
import streamlit as st


def create_original_excel(equipment_dict, measurements_df):
    """
    원본 데이터 엑셀 파일 생성
    
    Args:
        equipment_dict: 장비 정보 딕셔너리
        measurements_df: 측정 데이터 DataFrame
    
    Returns:
        bytes: 엑셀 파일 바이너리 데이터
    """
    buffer = BytesIO()
    
    # Equipment를 DataFrame으로 변환
    df_eq = pd.DataFrame([equipment_dict])
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Equipment 시트
        df_eq.to_excel(writer, sheet_name='Equipment', index=False)
        
        # Measurements 시트
        measurements_df.to_excel(writer, sheet_name='Measurements', index=False)
        
        # Summary 시트
        summary = pd.DataFrame({
            'Item': ['SID', '장비명', 'Model', '측정 데이터 개수', '다운로드 일시', '비고'],
            'Value': [
                equipment_dict.get('sid', ''),
                equipment_dict.get('equipment_name', ''),
                equipment_dict.get('model', ''),
                len(measurements_df),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '승인 전 원본 데이터'
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)
    
    buffer.seek(0)
    return buffer.getvalue()


def create_modified_excel(original_eq_dict, edited_eq_dict, original_meas_df, edited_meas_df):
    """
    수정된 데이터 + 변경 이력 엑셀 파일 생성
    
    Args:
        original_eq_dict: 원본 장비 정보 딕셔너리
        edited_eq_dict: 수정된 장비 정보 딕셔너리
        original_meas_df: 원본 측정 데이터 DataFrame
        edited_meas_df: 수정된 측정 데이터 DataFrame
    
    Returns:
        bytes: 엑셀 파일 바이너리 데이터
    """
    buffer = BytesIO()
    
    # DataFrame 변환
    df_original_eq = pd.DataFrame([original_eq_dict])
    df_edited_eq = pd.DataFrame([edited_eq_dict])
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # 수정된 데이터
        df_edited_eq.to_excel(writer, sheet_name='Equipment (Modified)', index=False)
        edited_meas_df.to_excel(writer, sheet_name='Measurements (Modified)', index=False)
        
        # 원본 데이터 (비교용)
        df_original_eq.to_excel(writer, sheet_name='Equipment (Original)', index=False)
        original_meas_df.to_excel(writer, sheet_name='Measurements (Original)', index=False)
        
        # 변경 이력
        changes_log = []
        
        # Equipment 변경사항
        for col in df_original_eq.columns:
            orig_val = df_original_eq[col].iloc[0]
            edit_val = df_edited_eq[col].iloc[0]
            if orig_val != edit_val:
                changes_log.append({
                    '시트': 'Equipment',
                    '필드': col,
                    '원본': str(orig_val),
                    '수정': str(edit_val),
                    '변경 일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # Measurements 변경사항
        for idx in original_meas_df.index:
            for col in original_meas_df.columns:
                orig_val = original_meas_df.loc[idx, col]
                edit_val = edited_meas_df.loc[idx, col]
                if orig_val != edit_val:
                    changes_log.append({
                        '시트': 'Measurements',
                        '필드': f"Row {idx + 1} - {col}",
                        '원본': str(orig_val),
                        '수정': str(edit_val),
                        '변경 일시': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        if changes_log:
            df_changes = pd.DataFrame(changes_log)
            df_changes.to_excel(writer, sheet_name='변경 이력', index=False)
        
        # 승인 체크리스트
        checklist = pd.DataFrame({
            '검증 항목': [
                '장비 사양 확인',
                '측정값 범위 확인',
                'Trend/Pass 여부 확인',
                '고객사 정보 확인',
                '엔지니어 정보 확인'
            ],
            '확인 (O/X)': ['', '', '', '', ''],
            '담당자': ['', '', '', '', ''],
            '비고': ['', '', '', '', '']
        })
        checklist.to_excel(writer, sheet_name='승인 체크리스트', index=False)
    
    buffer.seek(0)
    return buffer.getvalue()


def compare_dataframes(original_df, edited_df):
    """
    두 DataFrame을 비교하여 변경사항 추출
    
    Args:
        original_df: 원본 DataFrame
        edited_df: 수정된 DataFrame
    
    Returns:
        list: 변경사항 리스트 (딕셔너리 형태)
    """
    changes = []
    
    if original_df.shape != edited_df.shape:
        return changes  # 크기가 다르면 비교 불가
    
    for col in original_df.columns:
        for idx in original_df.index:
            orig_val = original_df.loc[idx, col]
            edit_val = edited_df.loc[idx, col]
            
            # NaN 처리
            if pd.isna(orig_val) and pd.isna(edit_val):
                continue
            
            if orig_val != edit_val:
                changes.append({
                    'Row': idx,
                    'Column': col,
                    'Original': str(orig_val),
                    'Modified': str(edit_val)
                })
    
    return changes


def compare_dicts(original_dict, edited_dict):
    """
    두 딕셔너리를 비교하여 변경사항 추출
    
    Args:
        original_dict: 원본 딕셔너리
        edited_dict: 수정된 딕셔너리
    
    Returns:
        list: 변경사항 리스트 (딕셔너리 형태)
    """
    changes = []
    
    for key in original_dict.keys():
        if key in edited_dict:
            if original_dict[key] != edited_dict[key]:
                changes.append({
                    'Field': key,
                    'Original': str(original_dict[key]),
                    'Modified': str(edited_dict[key])
                })
    
    return changes
