# Control Chart Viewer v1.0

장비별 Performance 데이터를 관리도(Control Chart)로 비교 분석하는 웹 애플리케이션입니다.
**Google Sheets**와 연동되어 실시간 데이터를 시각화하는 **Viewer** 전용 모드로 동작합니다.

## 🚀 주요 기능 (v1.0)

### 1. 데이터 관리 (Data Management)
- **Google Sheets 연동**: 웹상의 Google Sheet 데이터를 실시간으로 DB에 동기화
- **관계형 데이터 구조 (New)**: `Equipments`(장비), `Measurements`(측정), `Specs`(규격) 3개 시트를 연동하여 체계적인 관리 지원
- **Viewer 모드**: 데이터 수정/삭제 없이 안전하게 조회만 가능 (단방향 동기화)
- **데이터 무결성**: 동기화 시 기존 데이터를 최신 상태로 완전 교체 (중복 방지)

### 2. 장비 현황 (Equipment Explorer)
- **하이브리드 탐색**: 기간 설정 -> Sunburst(계층) -> Split View(연구/산업용) 흐름
- **인터랙티브 차트**: 막대 그래프 클릭 시 하단 리스트 자동 필터링
- **멀티 탭 상세 보기**: 여러 장비 선택 시 브라우저 탭처럼 개별 상세 정보 표시
- **스펙 비교 (Comparison)**: 2개 이상 선택 시 자동으로 비교표 생성

### 3. Control Chart 분석
- **다중 필터링**:
  - **R/I (용도)**: 선택 시 Model 목록 자동 필터링 (Research/Industrial)
  - **Model**: 모델별 필터링
  - **Check Items**: 분석 항목 선택 (최대 2개 권장)
  - **날짜 범위**: 분석 기간 설정 (초기화 버튼 포함)
- **고급 시각화**:
  - **규격선 표시 (New)**: 모델/항목별 USL, LSL, Target 라인 표시
  - **조건부 서식**: 연구용(💎) vs 산업용(●) 모델 마커 구분
  - **스마트 라벨링**: 그룹화 기준 'None' 선택 시 항목명 자동 표시
  - **개선된 툴팁**: 항목명 -> 장비명(모델) -> 날짜 -> 값 순서로 정보 표시
- **이상 탐지 (SPC Rules)**:
  - **Rule of Seven**: 평균선 기준 7점 연속 편향
  - **Trend Violations**: 7점 연속 상승/하락 추세

### 4. 사용자 지원 (Support)
- **사용 가이드 탭**: 프로그램 내에서 상세한 사용법(동기화, 조회, 분석)을 바로 확인 가능
- **개발자 정보**: 사이드바 하단에서 개발자 연락처 및 소속 정보 제공

## 📂 파일 구조

```
streamlit_app/
├── app.py              # 메인 애플리케이션 (UI 및 탭 구성)
├── charts.py           # Plotly 차트 생성 로직
├── database.py         # SQLite DB 연동 및 동기화 로직
├── utils.py            # 데이터 전처리 및 통계 계산
├── requirements.txt    # 의존성 패키지 목록
├── run.bat             # 간편 실행 스크립트
├── README.md           # 프로젝트 설명서
└── AUTO_LOAD_GUIDE.md  # Google Sheets 연동 가이드
```

## 🛠️ 설치 및 실행

### 1. 환경 설정
```bash
cd streamlit_app
pip install -r requirements.txt
```

### 2. 관리자 비밀번호 설정 (환경변수)

#### Windows (PowerShell)
```powershell
# 현재 세션만
$env:ADMIN_PASSWORD="pqc123"

# 영구 설정 (선택사항)
[System.Environment]::SetEnvironmentVariable('ADMIN_PASSWORD', 'pqc123', 'User')
```

#### Linux/Mac
```bash
export ADMIN_PASSWORD="pqc123"
```

### 3. 실행

#### 로컬 실행
터미널에서 아래 명령어를 실행하세요.
```bash
# 환경변수 설정 (Windows)
$env:ADMIN_PASSWORD="pqc123"

# 앱 실행
streamlit run app.py
```

#### Docker 실행 (서버 배포)
```bash
# 1. 관리자 비밀번호 설정 (docker-compose.yml 수정)
# environment:
#   - ADMIN_PASSWORD=your_secure_password_here

# 2. Docker 컨테이너 빌드 및 실행
docker-compose up -d

# 3. 브라우저에서 접속
# http://your-server-ip:80
```

**관리자 비밀번호 설정 방법:**
1. `docker-compose.yml` 파일에서 `ADMIN_PASSWORD` 값 변경
2. 설정하지 않으면 기본값 `admin123` 사용 (개발용)

## 💡 사용 팁
- **데이터 동기화**: `데이터 관리` 탭에서 'Google Sheets 동기화 실행'을 누르면 최신 데이터를 불러옵니다.
- **비교 분석**: 장비 목록에서 체크박스를 여러 개 선택하면 '비교하기' 탭이 자동으로 생깁니다.
- **규격 관리**: Google Sheets의 `Specs` 시트에 관리 기준을 입력하면 차트에 자동으로 반영됩니다.

---
**Last Updated**: 2025-12-08 (Phase 3 Complete - Relational Data & Specs)
