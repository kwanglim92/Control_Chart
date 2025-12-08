# Google Sheets 연동 가이드
(Control Chart Viewer v1.0)

이 문서는 Control Chart Viewer와 Google Sheets를 연동하기 위한 설정 방법을 설명합니다.

## 1. Google Cloud 설정 (최초 1회)

### 1-1. 프로젝트 생성 및 API 활성화
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속합니다.
2. 새 프로젝트를 생성합니다 (예: `control-chart-app`).
3. **API 및 서비스 > 라이브러리** 메뉴로 이동합니다.
4. **"Google Sheets API"**를 검색하고 **[사용(Enable)]** 버튼을 클릭합니다.

### 1-2. 서비스 계정 생성 및 키 다운로드
1. **API 및 서비스 > 사용자 인증 정보(Credentials)** 메뉴로 이동합니다.
2. **[사용자 인증 정보 만들기] > [서비스 계정]**을 선택합니다.
3. 서비스 계정 이름(예: `viewer-bot`)을 입력하고 [만들기]를 누릅니다.
4. 역할(Role)은 선택하지 않아도 됩니다 (건너뛰기).
5. 생성된 서비스 계정을 클릭하고 **[키(Keys)]** 탭으로 이동합니다.
6. **[키 추가] > [새 키 만들기]**를 선택하고 **JSON** 유형을 선택하여 다운로드합니다.
7. 다운로드된 JSON 파일의 내용을 메모장으로 엽니다.

## 2. Streamlit Secrets 설정

프로젝트 폴더 내의 `.streamlit/secrets.toml` 파일을 열고(없으면 생성) 아래 형식으로 내용을 채워넣습니다.
다운로드한 JSON 파일의 내용을 복사해서 붙여넣으세요.

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "..."
client_id = "..."
auth_uri = "..."
token_uri = "..."
auth_provider_x509_cert_url = "..."
client_x509_cert_url = "..."
```

> **주의**: `spreadsheet` 항목에는 실제 연동할 Google Sheet의 전체 URL을 입력해야 합니다.

## 3. Google Sheet 공유 설정 (필수)

1. 연동하려는 Google Sheet를 엽니다.
2. 우측 상단의 **[공유]** 버튼을 클릭합니다.
3. `secrets.toml` 파일의 `client_email` 값(예: `viewer-bot@...iam.gserviceaccount.com`)을 복사하여 공유 대상에 추가합니다.
4. 권한을 **[뷰어]** 또는 **[편집자]**로 설정하고 [전송]을 누릅니다.

## 4. 데이터 구조 (Google Sheets)
효율적인 관리를 위해 **3개의 시트(탭)**로 구성하는 것을 권장합니다.

### 4-1. 시트 구성
하단 탭 이름을 정확히 아래와 같이 설정해야 합니다. (대소문자 구분)

1. **Equipments** (장비 마스터)
2. **Measurements** (측정 데이터)
3. **Specs** (규격 관리)

---

### 4-2. 상세 컬럼 정의

#### 1️⃣ Equipments (장비 마스터)
장비의 고유 정보를 관리합니다. **SID**는 고유해야 합니다.

| 컬럼명 | 설명 | 필수 | 비고 |
|---|---|---|---|
| **SID** | 고유 식별자 (System ID) | ✅ | 공란 시 '장비명'을 사용 |
| **장비명** | 장비 이름 (고객사명) | ✅ | |
| **종료일** | 출고일 (YYYY-MM-DD) | ✅ | |
| **R/I** | Research / Industrial | | |
| **Model** | 장비 모델명 | | |
| **Head Type** | Head Type | | |
| ... | 기타 사양 컬럼 | | |

#### 2️⃣ Measurements (측정 데이터)
실제 측정값을 기록합니다. **SID**를 통해 장비 정보와 연결됩니다.

| 컬럼명 | 설명 | 필수 | 비고 |
|---|---|---|---|
| **SID** | 장비 식별자 | ✅ | 공란 시 '장비명' 컬럼 참조 |
| **장비명** | 장비 이름 | (선택) | SID가 없을 경우 필수 |
| **Check Items** | 측정 항목명 | ✅ | |
| **Value** | 측정값 (숫자) | ✅ | |
| ~~종료일~~ | (삭제 가능) | | 더 이상 필요하지 않음 |

#### 3️⃣ Specs (규격 관리)
모델별/항목별 관리 기준(상한/하한/목표)을 설정합니다.

| 컬럼명 | 설명 | 필수 |
|---|---|---|
| **Model** | 대상 모델명 | ✅ |
| **Check Item** | 대상 항목명 | ✅ |
| **LSL** | 하한값 (Lower Spec Limit) | |
| **USL** | 상한값 (Upper Spec Limit) | |
| **Target** | 목표값 (Target Value) | |

> **Tip**: `Specs` 시트가 없어도 프로그램은 정상 동작하며, 규격선만 표시되지 않습니다.

## 5. 실행 및 동기화

1. 앱을 실행합니다 (`run.bat`).
2. **[데이터 관리]** 탭으로 이동합니다.
3. **[☁️ Google Sheets 동기화 실행]** 버튼을 클릭합니다.
4. 성공 메시지가 뜨면 데이터가 DB에 저장된 것입니다.
