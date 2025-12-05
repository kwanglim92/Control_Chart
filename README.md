# Control Chart 분석 시스템 (Streamlit)

장비별 Performance 데이터를 관리도(Control Chart)로 비교 분석하는 웹 애플리케이션입니다.

## 주요 기능

- 📊 **Excel 데이터 업로드**: Performance 데이터가 포함된 Excel 파일 업로드
- 🔍 **다중 필터링**: R/I, Model, Check Items 등 다양한 기준으로 데이터 필터링
- 📈 **관리도 시각화**: 
  - Combined Chart: 여러 그룹을 한 화면에 비교
  - Individual Charts: 그룹별 개별 차트
  - 이중 Y축 지원 (Check Items 2개 선택 시)
- 🚨 **이상 탐지**:
  - Rule of Seven: 평균선 기준 같은 쪽에 7개 이상 연속
  - Trend Violations: 증가/감소 추세가 7개 이상 연속
- 📋 **통계 정보**: 그룹별 평균, 표준편차, UCL, LCL 계산
- 💾 **데이터 다운로드**: 필터링된 데이터 및 통계를 CSV로 저장

## 설치 방법

### 1. 필수 라이브러리 설치

```bash
cd streamlit_app
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 애플리케이션을 사용할 수 있습니다.

## 사용 방법

### 1. 데이터 업로드
- 왼쪽 사이드바에서 Excel 파일(.xlsx, .xls)을 업로드합니다.
- 파일에는 최소한 다음 컬럼이 포함되어야 합니다:
  - `Value`: 측정값
  - `종료일`: 측정 날짜
  - `Check Items`: 측정 항목
  - 기타 필터용 컬럼 (R/I, Model, XY Scanner 등)

### 2. 필터 설정
- 사이드바에서 원하는 필터 조건을 선택합니다.
- **Check Items**는 최대 2개까지 선택 가능합니다 (이중 축 표시용).
- 날짜 범위 필터를 사용하여 특정 기간의 데이터만 볼 수 있습니다.
- "필터 적용" 버튼을 클릭하여 필터를 적용합니다.

### 3. 관리도 보기

#### Combined Chart 탭
- 그룹화 기준을 선택합니다 (예: Check Items, Model, 연도 등).
- "Rule of Seven / Trend 표시" 체크박스로 이상치 하이라이트를 켜거나 끌 수 있습니다.
- Check Items가 2개 선택된 경우, "이중 Y축 사용"을 활성화할 수 있습니다.

#### Individual Charts 탭
- 각 그룹별로 개별 관리도를 확인할 수 있습니다.

#### 통계 탭
- 그룹별 통계 정보(Count, AVG, STD, UCL, LCL 등)를 테이블로 확인합니다.
- 통계 데이터를 CSV로 다운로드할 수 있습니다.

#### 데이터 탭
- 필터링된 원본 데이터를 확인합니다.
- 데이터를 CSV로 다운로드할 수 있습니다.

## 파일 구조

```
streamlit_app/
├── app.py              # 메인 애플리케이션
├── utils.py            # 데이터 처리 유틸리티
├── charts.py           # Plotly 차트 생성 함수
├── requirements.txt    # Python 패키지 의존성
└── README.md          # 이 파일
```

## 기술 스택

- **Streamlit**: 웹 UI 프레임워크
- **Pandas**: 데이터 처리
- **Plotly**: 인터랙티브 차트
- **NumPy**: 통계 계산

## 주요 기능 설명

### Rule of Seven
평균선을 기준으로 같은 쪽(위 또는 아래)에 7개 이상의 데이터 포인트가 연속으로 나타나는 경우를 탐지합니다. 이는 공정이 평균에서 벗어나고 있음을 의미할 수 있습니다.

### Trend Violations
7개 이상의 데이터 포인트가 연속으로 증가하거나 감소하는 추세를 보이는 경우를 탐지합니다. 이는 공정에 체계적인 변화가 발생하고 있음을 나타냅니다.

### 관리한계선 (UCL / LCL)
- **UCL (Upper Control Limit)**: 평균 + 3 × 표준편차
- **LCL (Lower Control Limit)**: 평균 - 3 × 표준편차

## 문제 해결

### 모듈을 찾을 수 없음 (ModuleNotFoundError)
```bash
pip install -r requirements.txt
```

### 포트가 이미 사용 중
```bash
streamlit run app.py --server.port 8502
```

### 차트가 표시되지 않음
- 데이터에 `Value`와 `종료일` 컬럼이 있는지 확인하세요.
- 필터 조건을 확인하여 데이터가 필터링되지 않았는지 확인하세요.

## 라이선스

이 프로젝트는 기존 C# Windows Forms 애플리케이션을 Python Streamlit으로 포팅한 것입니다.
