"""
Control Chart 데이터 처리 및 통계 유틸리티 함수
"""
import re
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from unicodedata import normalize as unicode_normalize


def normalize_key(text: str) -> str:
    """
    C# NormalizeKey 함수 포팅
    문자열을 정규화하여 일관된 비교를 위한 키 생성
    """
    if not text or not isinstance(text, str):
        return ""
    
    s = text.strip()
    # 전각/호환문자 통일 (NFKC 정규화)
    s = unicode_normalize('NFKC', s)
    # 모든 공백을 하나로
    s = re.sub(r'\s+', ' ', s)
    # 대소문자 무시
    s = s.upper()
    
    return s


def clean_numeric_string(s: str) -> str:
    """
    C# CleanNumericString 함수 포팅
    숫자, 소수점, 부호만 남기고 제거
    """
    if not s or not isinstance(s, str):
        return ""
    
    # 숫자, '.', '-' 만 남김
    return re.sub(r'[^\d\.\-]', '', s)


def load_data(file) -> pd.DataFrame:
    """
    Excel 파일을 로드하고 기본 전처리 수행
    """
    try:
        df = pd.read_excel(file)
        return df
    except Exception as e:
        raise ValueError(f"Excel 파일 로딩 실패: {str(e)}")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    C# FilterUploadedData 함수 포팅
    Value 컬럼의 유효한 숫자 데이터만 필터링
    """
    if 'Value' not in df.columns:
        raise ValueError("'Value' 컬럼이 없습니다.")
    
    def is_valid_numeric(val):
        if pd.isna(val) or val == '':
            return False
        clean = clean_numeric_string(str(val))
        try:
            float(clean)
            return True
        except:
            return False
    
    # 유효한 숫자 행만 필터링
    mask = df['Value'].apply(is_valid_numeric)
    cleaned_df = df[mask].copy()
    
    # Value를 float로 변환
    cleaned_df['Value'] = cleaned_df['Value'].apply(
        lambda x: float(clean_numeric_string(str(x)))
    )
    
    return cleaned_df


def normalize_check_items_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    C# NormalizeCheckItemsColumn 함수 포팅
    Check Items 컬럼의 공백 정규화
    """
    if 'Check Items' not in df.columns:
        return df
    
    def normalize_text(text):
        if not isinstance(text, str) or not text:
            return text
        # 앞뒤 공백 제거
        s = text.strip()
        # 연속된 공백을 하나로
        s = re.sub(r'\s+', ' ', s)
        return s
    
    df['Check Items'] = df['Check Items'].apply(normalize_text)
    return df


def calculate_stats(values: np.ndarray) -> Dict[str, float]:
    """
    통계값 계산: 평균, 표준편차, UCL, LCL
    """
    if len(values) == 0:
        return {
            'count': 0,
            'avg': 0.0,
            'std': 0.0,
            'ucl': 0.0,
            'lcl': 0.0,
            'max': 0.0,
            'min': 0.0
        }
    
    avg = np.mean(values)
    std = np.std(values, ddof=0)  # 모표준편차 (C# 코드와 동일)
    ucl = avg + 3 * std
    lcl = avg - 3 * std
    
    return {
        'count': len(values),
        'avg': avg,
        'std': std,
        'ucl': ucl,
        'lcl': lcl,
        'max': np.max(values),
        'min': np.min(values)
    }


def detect_rule_of_seven(values: np.ndarray, mean: float) -> List[int]:
    """
    C# DetectRuleOfSeven 함수 포팅
    평균선을 기준으로 같은 쪽에 7개 이상 연속된 인덱스 반환
    """
    hits = set()
    run_len = 0
    last_sign = 0
    
    for i in range(len(values)):
        if values[i] > mean:
            sign = 1
        elif values[i] < mean:
            sign = -1
        else:
            sign = 0
        
        if sign == 0:
            run_len = 0
            last_sign = 0
            continue
        
        if sign == last_sign:
            run_len += 1
        else:
            run_len = 1
            last_sign = sign
        
        if run_len >= 7:
            # i-6 ... i 까지 7개
            for j in range(i - 6, i + 1):
                hits.add(j)
    
    return sorted(list(hits))


def detect_trend_violations(values: np.ndarray) -> List[int]:
    """
    C# DetectTrendViolations 함수 포팅
    7개 점이 증가(혹은 감소) 방향으로 연속될 때의 인덱스 반환
    """
    hits = set()
    n = len(values)
    run_len = 0
    last_sign = 0
    
    for i in range(1, n):
        if values[i] > values[i - 1]:
            sign = 1
        elif values[i] < values[i - 1]:
            sign = -1
        else:
            sign = 0
        
        if sign == 0:
            run_len = 0
            last_sign = 0
            continue
        
        if sign == last_sign:
            run_len += 1
        else:
            run_len = 1
            last_sign = sign
        
        if run_len >= 6:  # 7개 점 추세 → diff가 6번 연속
            start = i - 6
            for j in range(start, i + 1):
                hits.add(j)
    
    return sorted(list(hits))


def add_date_columns(df: pd.DataFrame, date_col: str = '종료일') -> pd.DataFrame:
    """
    날짜 컬럼에서 연도, 분기, 월 추출
    """
    if date_col not in df.columns:
        return df
    
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    df['연도'] = df[date_col].dt.year.astype(str)
    df['분기'] = ((df[date_col].dt.month - 1) // 3 + 1).astype(str)
    df['월'] = df[date_col].dt.month.apply(lambda x: f"{x:02d}" if pd.notna(x) else None)
    
    return df


def build_display_map(df: pd.DataFrame, column: str) -> Tuple[List[str], Dict[str, str]]:
    """
    컬럼의 값들을 정규화 키로 중복 제거하고 표시용 라벨 매핑 생성
    Returns: (정렬된 표시 라벨 리스트, {정규화키: 표시라벨} 딕셔너리)
    """
    if column not in df.columns:
        return [], {}
    
    key_to_display = {}
    
    for val in df[column].dropna():
        raw = str(val)
        if not raw.strip():
            continue
        
        key = normalize_key(raw)
        if key not in key_to_display:
            key_to_display[key] = raw  # 최초 등장 원본을 표시 라벨로 고정
    
    # 표시 라벨을 정렬
    display_labels = sorted(key_to_display.values())
    
    return display_labels, key_to_display
