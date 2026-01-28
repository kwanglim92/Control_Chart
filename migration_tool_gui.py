import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import sqlite3
import pandas as pd
import os
import threading
import requests
from datetime import datetime

class MigrationToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 NocoDB Migration Tool (GUI)")
        self.root.geometry("900x900")  # 초기 크기 증가
        self.root.resizable(True, True)  # 마우스로 크기 조절 가능

        # NocoDB API 설정
        self.BASE_URL = "http://10.4.1.141:8003/api/v2"
        self.API_TOKEN = "fkyIVsRDiwZzOj_vhwg_UFFBEWVNCKcET5pacie0"  # 기본 토큰
        self.BASE_ID = "pdb2qjlkujb4bld"
        self.TABLE_IDS = {
            "Engineers": "mu8lyr6gb7ib5vz",
            "Equipments": "m59x2omec97hpjo",  # 업데이트됨
            "ChecklistRawData": "mefhik2pjcx5tve"  # 업데이트됨
        }

        # 스타일 설정
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("TLabel", font=('Helvetica', 10))

        # 메인 프레임
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_label = ttk.Label(main_frame, text="NocoDB 데이터 마이그레이션 도구 (API Direct)", font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # === 1. 파일 선택 섹션 (먼저) ===
        file_frame = ttk.LabelFrame(main_frame, text="Step 1. SQLite 파일 선택", padding="10")
        file_frame.pack(fill=tk.X, pady=10)

        self.file_path_var = tk.StringVar(value="SQLite 파일을 선택하세요 (.db)")
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly', width=60)
        self.file_entry.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)

        self.browse_btn = ttk.Button(file_frame, text="찾아보기", command=self.browse_file)
        self.browse_btn.pack(side=tk.RIGHT)
        
        # === 2. API Token 표시 섹션 ===
        token_frame = ttk.LabelFrame(main_frame, text="Step 2. NocoDB API Token", padding="10")
        token_frame.pack(fill=tk.X, pady=10)
        
        token_display_frame = ttk.Frame(token_frame)
        token_display_frame.pack(fill=tk.X)
        
        # 토큰 상태 표시
        self.token_status_label = ttk.Label(
            token_display_frame,
            text=f"✅ API Token 설정됨: {self.API_TOKEN[:10]}...{self.API_TOKEN[-10:]}",
            foreground="green",
            font=('Helvetica', 10)
        )
        self.token_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(token_display_frame, text="🔑 변경", command=self.change_token, width=10).pack(side=tk.LEFT)
        
        # === 3. DB 분석 버튼 ===
        analyze_frame = ttk.LabelFrame(main_frame, text="Step 3. DB 구조 분석", padding="10")
        analyze_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(analyze_frame, text="※ 파일 선택 후 바로 실행 가능합니다!", 
                 foreground="blue", font=('Helvetica', 9, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.analyze_btn = ttk.Button(analyze_frame, text="DB 구조 분석 시작", 
                                      command=self.analyze_db, state='disabled', width=20)
        self.analyze_btn.pack(anchor=tk.W)

        # 진행 상황 섹션
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=20)

        # === 4. 마이그레이션 버튼 (하단 고정) ===
        migration_frame = ttk.LabelFrame(main_frame, text="Step 4. Equipments 마이그레이션", padding="10")
        migration_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        ttk.Label(migration_frame, text="※ API Token 설정 완료 후 실행하세요!", 
                 foreground="blue", font=('Helvetica', 9, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        # 마이그레이션 상태 정보
        self.migration_state = {
            'total_count': 0,
            'current_index': 0,
            'uploaded_count': 0,
            'failed_count': 0,
            'data': None
        }
        
        # 진행 상황 표시
        status_frame = ttk.Frame(migration_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.migration_status_label = ttk.Label(status_frame, text="진행 상황: 0 / 0 (0%)", 
                                                font=('Helvetica', 10, 'bold'))
        self.migration_status_label.pack(side=tk.LEFT)
        
        
        # NocoDB 현재 데이터 조회 버튼
        view_frame = ttk.Frame(migration_frame)
        view_frame.pack(fill=tk.X, pady=5)
        
        self.view_nocodb_btn = ttk.Button(
            view_frame, 
            text="📊 NocoDB 현재 데이터 조회", 
            command=self.view_nocodb_data,
            width=25
        )
        self.view_nocodb_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            view_frame, 
            text="※ 마이그레이션 전/후 NocoDB 상태를 확인할 수 있습니다.",
            foreground="gray",
            font=('Helvetica', 9)
        ).pack(side=tk.LEFT, padx=10)
        
        # 버튼 프레임
        button_frame = ttk.Frame(migration_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.upload_preview_btn = ttk.Button(
            button_frame, 
            text="📋 업로드 미리보기 (체크박스 선택)", 
            command=self.open_upload_preview,
            state='disabled', 
            width=30
        )
        self.upload_preview_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            button_frame,
            text="※ 업로드할 데이터를 선택하고 중복을 확인할 수 있습니다.",
            foreground="gray",
            font=('Helvetica', 9)
        ).pack(side=tk.LEFT, padx=10)

        # 로그 섹션 (나머지 공간 채움)
        log_frame = ttk.LabelFrame(main_frame, text="작업 로그", padding="10")
        log_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 스크롤바와 텍스트 위젯을 담을 프레임
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)

        # 수직 스크롤바
        scrollbar = ttk.Scrollbar(log_text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_text_frame, height=25, state='disabled', font=('Consolas', 9), 
                                yscrollcommand=scrollbar.set, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 스크롤바와 텍스트 연결
        scrollbar.config(command=self.log_text.yview)

        # 마우스 휠 스크롤 이벤트 바인딩
        def on_mousewheel(event):
            self.log_text.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.log_text.bind("<MouseWheel>", on_mousewheel)  # Windows/MacOS
        self.log_text.bind("<Button-4>", lambda e: self.log_text.yview_scroll(-1, "units"))  # Linux scroll up
        self.log_text.bind("<Button-5>", lambda e: self.log_text.yview_scroll(1, "units"))   # Linux scroll down


    def change_token(self):
        """API Token 변경"""
        # 다이얼로그로 새 토큰 입력받기
        new_token = tk.simpledialog.askstring(
            "API Token 변경",
            "새로운 API Token을 입력하세요:",
            initialvalue=self.API_TOKEN,
            show='*'
        )
        
        if new_token and new_token.strip():
            self.API_TOKEN = new_token.strip()
            # 상태 레이블 업데이트
            self.token_status_label.config(
                text=f"✅ API Token 설정됨: {self.API_TOKEN[:10]}...{self.API_TOKEN[-10:]}",
                foreground="green"
            )
            messagebox.showinfo("완료", "API Token이 변경되었습니다!")
            self.log("✅ API Token 변경 완료")
            self.log(f"→ 새 토큰: {self.API_TOKEN[:10]}...{self.API_TOKEN[-10:]}")
        elif new_token is not None:  # 빈 문자열인 경우
            messagebox.showwarning("경고", "API Token을 입력하세요.")

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.analyze_btn.config(state='normal')
            self.log(f"✅ 파일 선택됨: {os.path.basename(file_path)}")
            self.log("→ 다음: [DB 구조 분석 시작] 버튼을 클릭하세요.")
            self.log("   (선택) 분석 전 API Token을 미리 설정하면 Select 필드 검증도 가능합니다.")

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"> {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def analyze_db(self):
        """DB 구조 분석 (상세)"""
        db_path = self.file_path_var.get()
        if not os.path.exists(db_path):
            messagebox.showerror("오류", "파일을 찾을 수 없습니다.")
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            self.log("=" * 80)
            self.log("📊 DB 구조 분석 시작 (상세 모드)")
            self.log("=" * 80)
            
            # Equipments 테이블 분석
            cursor.execute("PRAGMA table_info(equipments)")
            equip_columns_info = cursor.fetchall()
            equip_columns = [row[1] for row in equip_columns_info]
            
            # 매핑 규칙
            column_mapping = {
                'equipment_name': 'end_user',
                'mfg_engineer': 'production_engineer',
                'me3_engineer': 'production_engineer',
                'status': 'approval_status',
                'uploaded_at': 'registered_at',
                'date': 'end_date'
            }
            
            # === STEP 1: NocoDB 실제 필드 조회 ===
            nocodb_fields = []
            nocodb_field_types = {}
            
            self.log("\n┌─ STEP 1: NocoDB Equipments 테이블 필드 목록 (실제 조회) ──")
            self.log("│")
            
            if self.API_TOKEN:
                try:
                    headers = {"xc-token": self.API_TOKEN}
                    table_meta_url = f"{self.BASE_URL}/meta/tables/{self.TABLE_IDS['Equipments']}"
                    response = requests.get(table_meta_url, headers=headers)
                    
                    if response.status_code == 200:
                        table_meta = response.json()
                        columns = table_meta.get('columns', [])
                        
                        for col in columns:
                            col_title = col.get('title')
                            col_type = col.get('uidt')
                            if col_title and col_title != 'Id':  # AutoNumber ID 제외
                                nocodb_fields.append(col_title)
                                nocodb_field_types[col_title] = col_type
                        
                        self.log("│ ✅ NocoDB API 조회 성공")
                        self.log("│")
                        for idx, field in enumerate(nocodb_fields, 1):
                            field_type = nocodb_field_types.get(field, 'Unknown')
                            self.log(f"│  {idx:2d}. {field:25s} ({field_type})")
                        self.log(f"│  → 총 {len(nocodb_fields)}개 필드")
                    else:
                        self.log(f"│ ⚠️ NocoDB API 조회 실패 (HTTP {response.status_code})")
                        self.log("│ → 기본 필드 목록 사용")
                        # 폴백: 기본 필드 목록
                        nocodb_fields = [
                            'sid', 'end_user', 'model', 'ri', 'process', 'start_date', 'end_date', 
                            'production_engineer', 'qc_engineer', 'xy_scanner', 'head_type', 
                            'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                            'checklist_version', 'approval_status', 'registered_at'
                        ]
                        for idx, field in enumerate(nocodb_fields, 1):
                            self.log(f"│  {idx:2d}. {field}")
                        self.log(f"│  → 총 {len(nocodb_fields)}개 필드 (기본값)")
                except Exception as e:
                    self.log(f"│ ❌ API 조회 오류: {str(e)}")
                    self.log("│ → 기본 필드 목록 사용")
                    nocodb_fields = [
                        'sid', 'end_user', 'model', 'ri', 'process', 'start_date', 'end_date', 
                        'production_engineer', 'qc_engineer', 'xy_scanner', 'head_type', 
                        'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                        'checklist_version', 'approval_status', 'registered_at'
                    ]
                    for idx, field in enumerate(nocodb_fields, 1):
                        self.log(f"│  {idx:2d}. {field}")
                    self.log(f"│  → 총 {len(nocodb_fields)}개 필드 (기본값)")
            else:
                self.log("│ ℹ️ API Token이 없습니다.")
                self.log("│ → 기본 필드 목록 사용 (실제와 다를 수 있음)")            # NocoDB 필드명 (자동 생성 필드 및 NocoDB에 없는 필드 제외)
                nocodb_fields = [
                    'sid', 'end_user', 'model', 'ri', 'process', 'start_date', 'end_date', 
                    'production_engineer', 'xy_scanner', 'head_type', 
                    'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                    'checklist_version', 'approval_status'
                    # 제외: 'registered_at' (CreatedTime, 자동 생성으로 API에서 설정 불가)
                    # 제외: 'qc_engineer' (NocoDB 스키마에 없음)
                ]
                for idx, field in enumerate(nocodb_fields, 1):
                    self.log(f"│  {idx:2d}. {field}")
                self.log(f"│  → 총 {len(nocodb_fields)}개 필드 (기본값)")
                self.log("│")
                self.log("│ ⚠️ API Token 설정 후 다시 분석하면 실제 필드를 확인할 수 있습니다.")
            
            self.log("└────────────────────────────────────────────────────────────")
            
            self.log("\n┌─ STEP 2: SQLite DB Equipments 테이블 컬럼 목록 ───────────────")
            self.log("│")
            for idx, col in enumerate(equip_columns, 1):
                col_type = equip_columns_info[idx-1][2]  # type
                self.log(f"│  {idx:2d}. {col:25s} ({col_type})")
            self.log(f"│  → 총 {len(equip_columns)}개 컬럼")
            self.log("└────────────────────────────────────────────────────────────")
            
            self.log("\n┌─ STEP 3: 필드 매칭 분석 (NocoDB 기준) ─────────────────────")
            self.log("│")
            
            # NocoDB 시스템 필드 제외 (CreatedAt, UpdatedAt 등)
            system_fields = ['CreatedAt', 'UpdatedAt', 'nc_created_by', 'nc_updated_by', 'nc_order']
            link_fields = []  # LinkToAnotherRecord, ForeignKey 등
            
            matched_direct = []
            matched_mapped = []
            missing_in_db = []
            extra_in_db = []
            
            # 역매핑: SQLite → NocoDB
            reverse_mapping = {v: k for k, v in column_mapping.items()}
            
            # 사용된 SQLite 컬럼 추적
            used_sqlite_cols = set()
            
            self.log("│ NocoDB 필드              → SQLite 컬럼            상태")
            self.log("│ " + "─" * 58)
            
            for nocodb_field in nocodb_fields:
                field_type = nocodb_field_types.get(nocodb_field, '')
                
                # 시스템 필드 스킵
                if nocodb_field in system_fields:
                    continue
                
                # 링크 필드 스킵 (나중에 별도 표시)
                if field_type in ['LinkToAnotherRecord', 'ForeignKey', 'Links']:
                    link_fields.append(nocodb_field)
                    continue
                
                # 대소문자 구분 없이 비교 (NocoDB는 대문자 시작, SQLite는 소문자)
                nocodb_lower = nocodb_field.lower()
                
                # 1. 직접 매칭 (대소문자 무시)
                matched_col = None
                for col in equip_columns:
                    if col.lower() == nocodb_lower:
                        matched_col = col
                        break
                
                if matched_col:
                    self.log(f"│ {nocodb_field:24s} → {matched_col:24s} ✅ 직접 매칭")
                    matched_direct.append(nocodb_field)
                    used_sqlite_cols.add(matched_col)
                # 2. 역매핑으로 찾기 (NocoDB 필드명 → SQLite 원본 컬럼)
                elif nocodb_lower in reverse_mapping:
                    sqlite_col = reverse_mapping[nocodb_lower]
                    if sqlite_col in equip_columns:
                        self.log(f"│ {nocodb_field:24s} ← {sqlite_col:24s} 🔄 매핑")
                        matched_mapped.append((nocodb_field, sqlite_col))
                        used_sqlite_cols.add(sqlite_col)
                    else:
                        self.log(f"│ {nocodb_field:24s}   (없음)                    ❌ DB에 없음")
                        missing_in_db.append(nocodb_field)
                # 3. 매핑 규칙으로 찾기 (SQLite → NocoDB)
                else:
                    found = False
                    for sqlite_col, noco_target in column_mapping.items():
                        if noco_target.lower() == nocodb_lower and sqlite_col in equip_columns:
                            self.log(f"│ {nocodb_field:24s} ← {sqlite_col:24s} 🔄 매핑")
                            matched_mapped.append((nocodb_field, sqlite_col))
                            used_sqlite_cols.add(sqlite_col)
                            found = True
                            break
                    
                    if not found:
                        self.log(f"│ {nocodb_field:24s}   (없음)                    ❌ DB에 없음")
                        missing_in_db.append(nocodb_field)
            
            # 링크 필드 표시
            if link_fields:
                self.log("│")
                self.log("│ [관계 필드 - 스킵됨]")
                for lf in link_fields:
                    self.log(f"│ {lf:24s}   (관계)                    ℹ️ 링크 필드")
            
            # SQLite에만 있는 컬럼
            self.log("│")
            self.log("│ [SQLite DB에만 있는 컬럼]")
            for col in equip_columns:
                if col not in used_sqlite_cols and col not in ['id']:
                    self.log(f"│                          ← {col:24s} ⚠️ NocoDB 없음")
                    extra_in_db.append(col)
            
            self.log("│")
            self.log(f"│ 요약: ✅ 직접 {len(matched_direct)}개 | 🔄 매핑 {len(matched_mapped)}개 | ❌ DB없음 {len(missing_in_db)}개 | ⚠️ NocoDB없음 {len(extra_in_db)}개")
            self.log("└────────────────────────────────────────────────────────────")
            
            # 샘플 데이터 조회 (NocoDB 필드명으로 변환하여 표시)
            self.log("\n┌─ STEP 4: 샘플 데이터 미리보기 - NocoDB 업로드 형태 ───────")
            self.log("│")
            cursor.execute("SELECT * FROM equipments LIMIT 3")
            sample_rows = cursor.fetchall()
            
            if sample_rows:
                for row_idx, row in enumerate(sample_rows, 1):
                    self.log(f"│ === 샘플 {row_idx} (NocoDB 업로드 형태) ===")
                    
                    # SQLite 데이터를 딕셔너리로 변환
                    sqlite_data = {}
                    for col_idx, col_name in enumerate(equip_columns):
                        sqlite_data[col_name] = row[col_idx]
                    
                    # NocoDB 필드 순서대로 매칭된 값 표시
                    for nocodb_field in nocodb_fields:
                        field_type = nocodb_field_types.get(nocodb_field, '')
                        
                        # 시스템 필드 스킵
                        if nocodb_field in ['CreatedAt', 'UpdatedAt', 'nc_created_by', 'nc_updated_by', 'nc_order']:
                            continue
                        
                        # 링크 필드 스킵
                        if field_type in ['LinkToAnotherRecord', 'ForeignKey', 'Links']:
                            continue
                        
                        # 대소문자 무시하고 매칭
                        nocodb_lower = nocodb_field.lower()
                        value = None
                        
                        # 1. 직접 매칭 (대소문자 무시)
                        for sqlite_col, sqlite_val in sqlite_data.items():
                            if sqlite_col.lower() == nocodb_lower:
                                value = sqlite_val
                                break
                        
                        # 2. 매핑 규칙 적용
                        if value is None:
                            for sqlite_col, noco_target in column_mapping.items():
                                if noco_target.lower() == nocodb_lower and sqlite_col in sqlite_data:
                                    value = sqlite_data[sqlite_col]
                                    break
                        
                        # 값 표시
                        if value is not None:
                            # 값이 너무 길면 자르기
                            val_str = str(value)
                            if len(val_str) > 50:
                                val_str = val_str[:47] + "..."
                            self.log(f"│  • {nocodb_field:20s}: {val_str}")
                        else:
                            self.log(f"│  • {nocodb_field:20s}: (NULL)")
                    
                    self.log("│")
            else:
                self.log("│  (데이터 없음)")
            
            self.log("│ ℹ️ 위 형태로 NocoDB에 업로드됩니다.")
            self.log("└────────────────────────────────────────────────────────────")
            
            # 고유값 분석 (Select 필드 옵션 확인용)
            self.log("\n┌─ STEP 4.5: NocoDB Select 필드 옵션 검증 ──────────────────")
            self.log("│")
            
            # API Token 확인
            if self.API_TOKEN:
                self.log("│ [NocoDB 필드 타입 조회 중...]")
                try:
                    # NocoDB 테이블 스키마 조회
                    headers = {"xc-token": self.API_TOKEN}
                    # 2번 방식: /meta/tables/{tableId}
                    table_meta_url = f"{self.BASE_URL}/meta/tables/{self.TABLE_IDS['Equipments']}"
                    response = requests.get(table_meta_url, headers=headers)
                    
                    if response.status_code == 200:
                        table_meta = response.json()
                        columns = table_meta.get('columns', [])
                        
                        # Select 타입 필드 찾기
                        select_fields = {}
                        for col in columns:
                            col_type = col.get('uidt')  # UI Data Type
                            col_title = col.get('title')
                            
                            if col_type in ['SingleSelect', 'MultiSelect']:
                                # Select 필드의 옵션 목록
                                col_meta = col.get('colOptions', {})
                                options = col_meta.get('options', [])
                                option_values = [opt.get('title') for opt in options]
                                select_fields[col_title] = {
                                    'type': col_type,
                                    'options': option_values
                                }
                        
                        if select_fields:
                            self.log(f"│ → {len(select_fields)}개의 Select 필드 발견")
                            self.log("│")
                            
                            # 각 Select 필드에 대해 DB 고유값 비교
                            for field_name, field_info in select_fields.items():
                                # NocoDB 필드명을 DB 컬럼명으로 매핑
                                reverse_mapping = {v: k for k, v in column_mapping.items()}
                                db_col = reverse_mapping.get(field_name, field_name)
                                
                                if db_col in equip_columns:
                                    self.log(f"│ [{field_name}] ({field_info['type']})")
                                    
                                    # DB에서 고유값 조회
                                    query = f"SELECT DISTINCT {db_col} FROM equipments WHERE {db_col} IS NOT NULL AND {db_col} != '' ORDER BY {db_col}"
                                    cursor.execute(query)
                                    db_values = [row[0] for row in cursor.fetchall()]
                                    
                                    # 장비 구성 필드는 "선택하세요" → "N/A" 변환 적용
                                    config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
                                    if field_name in config_fields:
                                        db_values = ["N/A" if str(v).strip() == "선택하세요" else v for v in db_values]
                                    
                                    # NocoDB 옵션과 비교
                                    nocodb_options = set(field_info['options'])
                                    db_values_set = set(db_values)
                                    
                                    matched = nocodb_options & db_values_set
                                    missing_in_nocodb = db_values_set - nocodb_options
                                    extra_in_nocodb = nocodb_options - db_values_set
                                    
                                    self.log(f"│   NocoDB 옵션 ({len(nocodb_options)}개):")
                                    for opt in sorted(nocodb_options):
                                        self.log(f"│     • {opt}")
                                    
                                    self.log(f"│   DB 실제 값 ({len(db_values)}개):")
                                    for val in db_values:  # 모두 표시
                                        status = "✅" if val in nocodb_options else "❌"
                                        self.log(f"│     {status} {val}")
                                    
                                    if missing_in_nocodb:
                                        self.log(f"│   ⚠️ 경고: DB에는 있지만 NocoDB 옵션에 없음 ({len(missing_in_nocodb)}개):")
                                        for val in sorted(missing_in_nocodb):
                                            self.log(f"│     ❌ {val}")
                                        self.log(f"│   → 이 값들은 업로드 실패합니다!")
                                    else:
                                        self.log(f"│   ✅ 모든 DB 값이 NocoDB 옵션에 존재합니다.")
                                    
                                    self.log("│")
                        else:
                            self.log("│ → Select 타입 필드가 없습니다. (모두 Text 타입)")
                            self.log("│ → 고유값 검증 불필요 (자유로운 업로드 가능)")
                    else:
                        self.log(f"│ ⚠️ NocoDB API 조회 실패 (HTTP {response.status_code})")
                        self.log("│ → API Token을 확인하거나 수동으로 옵션을 확인하세요.")
                        
                except Exception as e:
                    self.log(f"│ ⚠️ API 조회 오류: {str(e)}")
                    self.log("│ → API Token을 먼저 설정하거나, 나중에 다시 분석하세요.")
            else:
                self.log("│ ℹ️ API Token이 설정되지 않았습니다.")
                self.log("│ → Select 필드 검증을 건너뜁니다.")
                self.log("│ → API Token 설정 후 다시 분석을 실행하세요.")
            
            self.log("└────────────────────────────────────────────────────────────")
            
            # 데이터 통계
            cursor.execute("SELECT COUNT(*) FROM equipments")
            equip_count = cursor.fetchone()[0]
            
            self.log("\n┌─ STEP 5: 데이터 통계 ──────────────────────────────────────")
            self.log(f"│  총 레코드 수: {equip_count}건")
            
            # 날짜 범위
            date_cols = [col for col in ['date', 'end_date', 'Date'] if col in equip_columns]
            if date_cols:
                date_col = date_cols[0]
                cursor.execute(f"SELECT MIN({date_col}), MAX({date_col}) FROM equipments WHERE {date_col} IS NOT NULL")
                min_date, max_date = cursor.fetchone()
                if min_date and max_date:
                    self.log(f"│  날짜 범위: {min_date} ~ {max_date}")
            
            # 모델 종류
            if 'model' in equip_columns:
                cursor.execute("SELECT DISTINCT model FROM equipments WHERE model IS NOT NULL")
                models = [row[0] for row in cursor.fetchall()]
                self.log(f"│  모델 종류: {', '.join(models) if models else '(없음)'}")
            
            self.log("└────────────────────────────────────────────────────────────")
            
            # 권고사항
            self.log("\n┌─ STEP 6: 권고 사항 ────────────────────────────────────────")
            self.log("│")
            
            has_warnings = False
            has_select_errors = False
            
            if missing_in_db:
                self.log("│  ⚠️ 경고: NocoDB에만 있는 필드가 있습니다.")
                self.log("│     → 이 필드들은 NULL 값으로 업로드됩니다.")
                self.log("│")
                has_warnings = True
            if extra_in_db:
                self.log("│  ℹ️ 정보: DB에만 있는 컬럼이 있습니다.")
                self.log("│     → 이 데이터는 NocoDB에 업로드되지 않습니다.")
                self.log("│     → 필요하면 NocoDB에 컬럼을 추가하세요.")
                self.log("│")
            
            # Select 필드 검증 결과 확인
            select_has_issues = False
            if self.API_TOKEN and 'select_fields' in locals():
                for field_name, field_info in select_fields.items():
                    reverse_mapping = {v: k for k, v in column_mapping.items()}
                    db_col = reverse_mapping.get(field_name, field_name)
                    if db_col in equip_columns:
                        query = f"SELECT DISTINCT {db_col} FROM equipments WHERE {db_col} IS NOT NULL AND {db_col} != ''"
                        cursor.execute(query)
                        db_values = [row[0] for row in cursor.fetchall()]
                        nocodb_options = set(field_info['options'])
                        db_values_set = set(db_values)
                        missing_in_nocodb = db_values_set - nocodb_options
                        if missing_in_nocodb:
                            select_has_issues = True
                            break
            
            if select_has_issues:
                self.log("│  ❌ 치명적: Select 필드에 NocoDB 옵션에 없는 값이 있습니다!")
                self.log("│     → 마이그레이션하면 해당 행들이 업로드 실패합니다.")
                self.log("│     → NocoDB에 누락된 옵션을 추가한 후 다시 분석하세요.")
                self.log("│")
                has_select_errors = True
            elif matched_direct and matched_mapped:
                self.log("│  ✅ 권장: 매칭 상태가 양호합니다.")
                if not has_warnings:
                    self.log("│     → 마이그레이션을 진행할 수 있습니다.")
                else:
                    self.log("│     → 경고 사항을 확인한 후 마이그레이션을 진행하세요.")
            
            self.log("└────────────────────────────────────────────────────────────")
            
            self.log("\n" + "=" * 80)
            self.log("✅ DB 구조 분석 완료")
            self.log("=" * 80)
            
            # 마이그레이션 버튼 활성화 조건
            if has_select_errors:
                # 사용자의 요청으로 오류가 있어도 마이그레이션 허용
                self.log("\n⚠️ 경고: Select 필드에 NocoDB 옵션에 없는 값이 있습니다.")
                self.log("→ 해당 데이터는 업로드 시 오류가 발생하거나 NULL로 처리될 수 있습니다.")
                self.log("→ 하지만 마이그레이션은 진행할 수 있도록 버튼을 활성화합니다.")
            
            if self.API_TOKEN:
                # 마이그레이션 데이터 준비 (DB 연결이 닫히기 전에 실행해야 함)
                self.prepare_migration_data(conn)
                
                self.upload_preview_btn.config(state='normal')
                self.log("\n✅ 마이그레이션 버튼 활성화됨")
                self.log("→ Step 4에서 [📋 업로드 미리보기] 버튼을 클릭하여 업로드할 데이터를 선택하세요.")
            else:
                self.log("\n→ 다음: Step 2에서 API Token을 입력하세요.")
            
            # DB 연결 종료 (모든 쿼리 작업 완료 후)
            conn.close()
            
            # 요약 메시지
            summary_parts = [f"DB 분석 완료!\n\n총 {equip_count}건의 장비 데이터"]
            summary_parts.append(f"\n매칭 결과:")
            summary_parts.append(f"✅ 직접 매칭: {len(matched_direct)}개")
            summary_parts.append(f"🔄 매핑 필요: {len(matched_mapped)}개")
            summary_parts.append(f"❌ DB에 없음: {len(missing_in_db)}개")
            summary_parts.append(f"⚠️ NocoDB에 없음: {len(extra_in_db)}개")
            
            if has_select_errors:
                summary_parts.append(f"\n⛔ Select 필드 오류 있음!")
                summary_parts.append(f"NocoDB 옵션 추가 필요")
            elif self.API_TOKEN:
                summary_parts.append(f"\n✅ 마이그레이션 가능!")
                summary_parts.append(f"다음: 마이그레이션 시작")
            else:
                summary_parts.append(f"\n다음: API Token 입력")
            
            summary = "\n".join(summary_parts)
            messagebox.showinfo("분석 완료", summary)
            
        except Exception as e:
            self.log(f"❌ 분석 중 오류: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("오류", f"DB 분석 중 오류가 발생했습니다:\n{str(e)}")


    def prepare_migration_data(self, conn):
        """마이그레이션 데이터 준비"""
        try:
            # 동적 컬럼 감지 (여기서는 사용하지 않지만, 필요시 추가)
            # cursor.execute("PRAGMA table_info(equipments)")
            # equip_columns = [row[1] for row in cursor.fetchall()]
            # self.log(f"equipments 테이블 컬럼: {', '.join(equip_columns)}")

            # cursor.execute("PRAGMA table_info(measurements)")
            # meas_columns = [row[1] for row in cursor.fetchall()]
            # self.log(f"measurements 테이블 컬럼: {', '.join(meas_columns)}")

            # 데이터 준비 시작
            equip_full_df = pd.read_sql_query('SELECT * FROM equipments', conn)
            
            self.log(f"ℹ️ 원본 컬럼: {list(equip_full_df.columns)}")
            
            # 컬럼 매핑 (SQLite → NocoDB)
            column_mapping = {}
            
            # equipment_name이 있으면 end_user로 매핑 (기존 end_user는 삭제)
            if 'equipment_name' in equip_full_df.columns:
                if 'end_user' in equip_full_df.columns:
                    # 기존 end_user 컬럼 삭제 (equipment_name을 사용)
                    equip_full_df = equip_full_df.drop(columns=['end_user'])
                    self.log(f"ℹ️ 기존 end_user 컬럼 삭제 (equipment_name 사용)")
                column_mapping['equipment_name'] = 'end_user'
            
            # date → end_date 매핑
            if 'date' in equip_full_df.columns:
                if 'end_date' in equip_full_df.columns:
                    # 기존 end_date 컬럼 삭제 (date를 사용)
                    equip_full_df = equip_full_df.drop(columns=['end_date'])
                    self.log(f"ℹ️ 기존 end_date 컬럼 삭제 (date 사용)")
                column_mapping['date'] = 'end_date'
            
            # 기타 매핑
            if 'me3_engineer' in equip_full_df.columns:
                column_mapping['me3_engineer'] = 'production_engineer'
            if 'status' in equip_full_df.columns:
                column_mapping['status'] = 'approval_status'
            if 'uploaded_at' in equip_full_df.columns:
                column_mapping['uploaded_at'] = 'registered_at'
            
            # 매핑 적용
            if column_mapping:
                equip_full_df = equip_full_df.rename(columns=column_mapping)
                self.log(f"ℹ️ 컬럼 매핑 적용: {column_mapping}")
            
            self.log(f"ℹ️ 매핑 후 컬럼: {list(equip_full_df.columns)}")
            
            # 날짜 기준 정렬 (오래된 순 → end_date 빠른 것부터)
            if 'end_date' in equip_full_df.columns:
                equip_full_df['end_date'] = pd.to_datetime(equip_full_df['end_date'], errors='coerce')
                equip_full_df = equip_full_df.sort_values('end_date', ascending=True, na_position='last')
                equip_full_df = equip_full_df.reset_index(drop=True)
                self.log(f"ℹ️ end_date 기준 오름차순 정렬 완료")
            
            # 마이그레이션 상태 업데이트
            self.migration_state['data'] = equip_full_df
            self.migration_state['total_count'] = len(equip_full_df)
            self.migration_state['current_index'] = 0
            self.migration_state['uploaded_count'] = 0
            self.migration_state['failed_count'] = 0
            
            self.update_migration_status()
            self.log(f"✅ 마이그레이션 데이터 준비 완료: 총 {len(equip_full_df)}건")
            
        except Exception as e:
            self.log(f"❌ 데이터 준비 오류: {str(e)}")
    
    def update_migration_status(self):
        """마이그레이션 진행 상황 업데이트"""
        total = self.migration_state['total_count']
        current = self.migration_state['current_index']
        uploaded = self.migration_state['uploaded_count']
        failed = self.migration_state['failed_count']
        
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_var.set(percentage)
            status_text = f"진행 상황: {current} / {total} ({percentage}%) | ✅ {uploaded}건 | ❌ {failed}건"
            self.migration_status_label.config(text=status_text)
        else:
            self.migration_status_label.config(text="진행 상황: 0 / 0 (0%)")
    
    def upload_batch(self, batch_size):
        """배치 단위 업로드"""
        if not self.API_TOKEN:
            messagebox.showerror("오류", "API Token을 먼저 설정하세요.")
            return
        
        if self.migration_state['data'] is None:
            messagebox.showerror("오류", "마이그레이션 데이터가 준비되지 않았습니다.")
            return
        
        threading.Thread(target=self._upload_batch_thread, args=(batch_size,), daemon=True).start()
    
    def _upload_batch_thread(self, batch_size):
        """배치 업로드 스레드"""
        try:
            df = self.migration_state['data']
            start_idx = self.migration_state['current_index']
            total = self.migration_state['total_count']
            
            if start_idx >= total:
                self.log("✅ 모든 데이터 업로드 완료!")
                messagebox.showinfo("완료", "모든 데이터가 업로드되었습니다!")
                return
            
            end_idx = min(start_idx + batch_size, total)
            batch_df = df.iloc[start_idx:end_idx]
            
            self.log(f"\n{'='*60}")
            self.log(f"📤 {start_idx+1}~{end_idx}번 업로드 중... ({len(batch_df)}건)")
            self.log(f"{'='*60}")
            
            headers = {"xc-token": self.API_TOKEN, "Content-Type": "application/json"}
            url_equip = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
            
            # NocoDB 필드명 (자동 생성 필드 및 NocoDB에 없는 필드 제외)
            nocodb_fields = [
                'sid', 'end_user', 'model', 'ri', 'process', 'start_date', 'end_date', 
                'production_engineer', 'xy_scanner', 'head_type', 
                'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                'checklist_version', 'approval_status'
                # 제외: 'registered_at' (CreatedTime, 자동 생성)
                # 제외: 'qc_engineer' (NocoDB 스키마에 없음)
            ]
            
            # 장비 구성 필드 (N/A 매핑 필요)
            config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
            
            for idx, row in batch_df.iterrows():
                payload = {}
                for col in nocodb_fields:
                    if col in df.columns:
                        val = row[col]
                        if not isinstance(val, pd.Series) and pd.notna(val):
                            if isinstance(val, (pd.Timestamp, datetime)):
                                payload[col] = val.strftime('%Y-%m-%d')
                            else:
                                # "선택하세요" → "N/A" 변환
                                if col in config_fields and str(val).strip() == "선택하세요":
                                    payload[col] = "N/A"
                                else:
                                    payload[col] = val
                
                response = requests.post(url_equip, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    self.migration_state['uploaded_count'] += 1
                    sid = payload.get('sid', f'Row {idx+1}')
                    self.log(f"  ✅ {self.migration_state['current_index']+1}번: {sid}")
                else:
                    self.migration_state['failed_count'] += 1
                    self.log(f"  ❌ {self.migration_state['current_index']+1}번 실패: {response.status_code} - {response.text[:100]}")
                
                self.migration_state['current_index'] += 1
                self.update_migration_status()
            
            self.log(f"{'='*60}")
            self.log(f"✅ 배치 업로드 완료: {start_idx+1}~{end_idx}번")
            self.log(f"{'='*60}\n")
            
            if self.migration_state['current_index'] >= total:
                self.log("🎉 전체 마이그레이션 완료!")
                messagebox.showinfo("완료", f"전체 마이그레이션이 완료되었습니다!\n\n✅ 성공: {self.migration_state['uploaded_count']}건\n❌ 실패: {self.migration_state['failed_count']}건")
            
        except Exception as e:
            self.log(f"❌ 배치 업로드 오류: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
    
    def upload_all_remaining(self):
        """남은 전체 데이터 업로드"""
        remaining = self.migration_state['total_count'] - self.migration_state['current_index']
        
        if remaining <= 0:
            messagebox.showinfo("알림", "이미 모든 데이터가 업로드되었습니다!")
            return
        
        result = messagebox.askyesno("확인", 
                                     f"남은 {remaining}건의 데이터를 모두 업로드하시겠습니까?\n\n"
                                     f"현재 진행: {self.migration_state['current_index']} / {self.migration_state['total_count']}")
        
        if result:
            self.upload_batch(remaining)
    
    def upload_selected_items(self, selected_indices):
        """선택된 항목만 업로드"""
        if not self.API_TOKEN:
            messagebox.showerror("오류", "API Token을 먼저 설정하세요.")
            return
        
        threading.Thread(target=self._upload_selected_thread, args=(selected_indices,), daemon=True).start()
    
    def _upload_selected_thread(self, selected_indices):
        """선택된 항목 업로드 스레드"""
        try:
            df = self.migration_state['data']
            total = len(selected_indices)
            
            self.log(f"\n{'='*60}")
            self.log(f"📤 선택된 {total}건 업로드 시작...")
            self.log(f"{'='*60}")
            
            headers = {"xc-token": self.API_TOKEN, "Content-Type": "application/json"}
            url_equip = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
            
            # NocoDB 필드명 (자동 생성 필드 제외)
            nocodb_fields = [
                'sid', 'end_user', 'model', 'ri', 'process', 'start_date', 'end_date', 
                'production_engineer', 'xy_scanner', 'head_type', 
                'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                'checklist_version', 'approval_status'
            ]
            
            # 장비 구성 필드 (N/A 매핑 필요)
            config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
            
            uploaded_count = 0
            failed_count = 0
            
            for count, idx in enumerate(selected_indices, 1):
                row = df.iloc[idx]
                payload = {}
                
                for col in nocodb_fields:
                    if col in df.columns:
                        val = row[col]
                        if not isinstance(val, pd.Series) and pd.notna(val):
                            if isinstance(val, (pd.Timestamp, datetime)):
                                payload[col] = val.strftime('%Y-%m-%d')
                            else:
                                # "선택하세요" → "N/A" 변환
                                if col in config_fields and str(val).strip() == "선택하세요":
                                    payload[col] = "N/A"
                                else:
                                    payload[col] = val
                
                response = requests.post(url_equip, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    uploaded_count += 1
                    sid = payload.get('sid', f'Row {idx+1}')
                    self.log(f"  ✅ {count}/{total}: {sid}")
                else:
                    failed_count += 1
                    self.log(f"  ❌ {count}/{total} 실패: {response.status_code} - {response.text[:100]}")
                
                # 진행률 업데이트
                progress = int((count / total) * 100)
                self.progress_var.set(progress)
            
            self.log(f"{'='*60}")
            self.log(f"✅ 선택 항목 업로드 완료")
            self.log(f"{'='*60}\n")
            self.log(f"📊 결과: ✅ 성공 {uploaded_count}건 | ❌ 실패 {failed_count}건")
            
            messagebox.showinfo("완료", 
                              f"선택 항목 업로드가 완료되었습니다!\n\n"
                              f"✅ 성공: {uploaded_count}건\n"
                              f"❌ 실패: {failed_count}건")
            
        except Exception as e:
            self.log(f"❌ 선택 항목 업로드 오류: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
    
    def reset_migration(self):
        """마이그레이션 리셋"""
        result = messagebox.askyesno("확인", 
                                     "마이그레이션을 처음부터 다시 시작하시겠습니까?\n\n"
                                     "※ NocoDB에 이미 업로드된 데이터는 삭제되지 않습니다.")
        
        if result:
            self.migration_state['current_index'] = 0
            self.migration_state['uploaded_count'] = 0
            self.migration_state['failed_count'] = 0
            self.update_migration_status()
            self.progress_var.set(0)
            self.log("🔄 마이그레이션 진행 상황이 리셋되었습니다.")
    
    def view_nocodb_data(self):
        """NocoDB Equipments 테이블 현재 데이터 조회"""
        if not self.API_TOKEN:
            messagebox.showerror("오류", "API Token을 먼저 설정하세요.")
            return
        
        try:
            self.log("\n📊 NocoDB 데이터 조회 중...")
            
            # NocoDB API로 데이터 조회
            headers = {"xc-token": self.API_TOKEN}
            url = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
            
            # 전체 데이터 조회 (정렬: Id 오름차순)
            params = {
                "limit": 1000,  # 최대 1000건
                "sort": "Id"
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                self.log(f"❌ NocoDB API 오류: {response.status_code}")
                messagebox.showerror("오류", f"데이터 조회 실패: {response.status_code}\n{response.text[:200]}")
                return
            
            data = response.json()
            records = data.get('list', [])
            
            if not records:
                self.log("ℹ️ NocoDB에 데이터가 없습니다.")
                messagebox.showinfo("조회 결과", "NocoDB Equipments 테이블에 데이터가 없습니다.")
                return
            
            self.log(f"✅ {len(records)}건의 데이터 조회 성공")
            
            # 데이터 뷰어 창 열기
            self.open_data_viewer(records)
            
        except Exception as e:
            self.log(f"❌ 데이터 조회 오류: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("오류", f"데이터 조회 중 오류가 발생했습니다:\n{str(e)}")
    
    def fetch_existing_sids(self):
        """NocoDB에서 기존 SID 목록 조회 (중복 검사용)"""
        try:
            headers = {"xc-token": self.API_TOKEN}
            url = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
            
            # SID 필드만 조회
            params = {
                "fields": "sid",
                "limit": 10000
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('list', [])
                # SID 집합 반환
                return {r.get('sid') for r in records if r.get('sid')}
            else:
                self.log(f"⚠️ SID 조회 실패: {response.status_code}")
                return set()
                
        except Exception as e:
            self.log(f"⚠️ SID 조회 오류: {str(e)}")
            return set()
    
    def open_upload_preview(self):
        """SQLite 업로드 미리보기 창 (체크박스 방식)"""
        if not self.API_TOKEN:
            messagebox.showerror("오류", "API Token을 먼저 설정하세요.")
            return
        
        if self.migration_state['data'] is None:
            messagebox.showerror("오류", "마이그레이션 데이터가 준비되지 않았습니다.\nDB 구조 분석을 먼저 실행하세요.")
            return
        
        try:
            self.log("\n📋 업로드 미리보기 창 열기...")
            
            # 기존 SID 조회
            existing_sids = self.fetch_existing_sids()
            self.log(f"ℹ️ NocoDB 기존 SID: {len(existing_sids)}개")
            
            # 미리보기 창 생성
            preview_window = tk.Toplevel(self.root)
            preview_window.title("SQLite → NocoDB 업로드 미리보기")
            preview_window.geometry("1600x800")
            
            # 상단 정보
            info_frame = ttk.Frame(preview_window, padding="10")
            info_frame.pack(fill=tk.X)
            
            ttk.Label(
                info_frame,
                text=f"총 {self.migration_state['total_count']}건의 레코드",
                font=('Helvetica', 12, 'bold')
            ).pack(side=tk.LEFT, padx=10)
            
            # 선택 개수 표시
            selection_label = ttk.Label(
                info_frame,
                text="선택: 0건",
                font=('Helvetica', 11),
                foreground="blue"
            )
            selection_label.pack(side=tk.LEFT, padx=20)
            
            # 전체 선택/해제 버튼
            def select_all():
                for item_id in tree.get_children():
                    values = tree.item(item_id)['values']
                    status = values[-1]  # 마지막 컬럼이 상태
                    if status == "✅ 신규":  # 신규만 선택
                        tree.item(item_id, tags=('checked',))
                update_selection_count()
            
            def deselect_all():
                for item_id in tree.get_children():
                    tree.item(item_id, tags=('unchecked',))
                update_selection_count()
            
            ttk.Button(info_frame, text="전체 선택", command=select_all, width=12).pack(side=tk.LEFT, padx=5)
            ttk.Button(info_frame, text="전체 해제", command=deselect_all, width=12).pack(side=tk.LEFT, padx=5)
            
            # Treeview 프레임
            tree_frame = ttk.Frame(preview_window)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 스크롤바
            scrollbar_y = ttk.Scrollbar(tree_frame)
            scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
            
            scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
            scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
            
            # 표시할 컬럼
            columns = ['☑', '#', 'sid', 'model', 'end_user', 'end_date', 'ri', 'xy_scanner', 
                      'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 'approval_status', '상태']
            
            # Treeview 생성
            tree = ttk.Treeview(
                tree_frame,
                columns=columns,
                show='headings',
                yscrollcommand=scrollbar_y.set,
                xscrollcommand=scrollbar_x.set,
                selectmode='none'
            )
            
            # 컬럼 헤더 설정
            column_widths = {
                '☑': 30,
                '#': 40,
                'sid': 150,
                'model': 120,
                'end_user': 180,
                'end_date': 100,
                'ri': 90,
                'xy_scanner': 120,
                'head_type': 120,
                'mod_vit': 150,
                'sliding_stage': 100,
                'sample_chuck': 140,
                'ae': 110,
                'approval_status': 110,
                '상태': 80
            }
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=column_widths.get(col, 100), anchor='w' if col != '☑' else 'center')
            
            # 데이터 삽입
            df = self.migration_state['data']
            config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
            
            # 디버그: 컬럼 확인
            self.log(f"ℹ️ DataFrame 컬럼: {list(df.columns)}")
            if len(df) > 0:
                first_row = df.iloc[0]
                self.log(f"ℹ️ 첫 번째 행 샘플:")
                self.log(f"   - sid: {first_row.get('sid', 'N/A')}")
                self.log(f"   - end_user: {first_row.get('end_user', 'N/A')}")
                self.log(f"   - end_date: {first_row.get('end_date', 'N/A')}")
            
            for idx, row in df.iterrows():
                # 안전한 값 추출 함수 (개선)
                def safe_get(row, col):
                    try:
                        if col not in row.index:
                            return ''
                        val = row[col]
                        if pd.isna(val):
                            return ''
                        # Timestamp 처리
                        if isinstance(val, pd.Timestamp):
                            return val.strftime('%Y-%m-%d')
                        # 일반 값
                        return str(val).strip()
                    except Exception as e:
                        self.log(f"⚠️ safe_get 오류 ({col}): {e}")
                        return ''
                
                sid = safe_get(row, 'sid')
                is_duplicate = str(sid) in existing_sids if sid else False
                status = "⚠️ 중복" if is_duplicate else "✅ 신규"
                
                values = [
                    '☐',  # 체크박스 (텍스트로 표현)
                    idx + 1,
                    safe_get(row, 'sid'),
                    safe_get(row, 'model'),
                    safe_get(row, 'end_user'),
                    safe_get(row, 'end_date'),
                    safe_get(row, 'ri'),
                    safe_get(row, 'xy_scanner'),
                    safe_get(row, 'head_type'),
                    safe_get(row, 'mod_vit'),
                    safe_get(row, 'sliding_stage'),
                    safe_get(row, 'sample_chuck'),
                    safe_get(row, 'ae'),
                    safe_get(row, 'approval_status'),
                    status
                ]
                
                item_id = tree.insert('', 'end', values=values, tags=('unchecked' if not is_duplicate else 'duplicate',))
            
            # 태그 스타일
            tree.tag_configure('checked', background='#e3f2fd')
            tree.tag_configure('unchecked', background='white')
            tree.tag_configure('duplicate', background='#ffebee', foreground='gray')
            
            # 클릭 이벤트 (체크박스 토글)
            def on_click(event):
                region = tree.identify_region(event.x, event.y)
                if region == "cell":
                    item_id = tree.identify_row(event.y)
                    if item_id:
                        tags = tree.item(item_id, 'tags')
                        if 'duplicate' in tags:
                            return  # 중복은 선택 불가
                        
                        # 체크 상태 토글
                        if 'checked' in tags:
                            tree.item(item_id, tags=('unchecked',))
                            values = list(tree.item(item_id, 'values'))
                            values[0] = '☐'
                            tree.item(item_id, values=values)
                        else:
                            tree.item(item_id, tags=('checked',))
                            values = list(tree.item(item_id, 'values'))
                            values[0] = '☑'
                            tree.item(item_id, values=values)
                        
                        update_selection_count()
            
            tree.bind('<Button-1>', on_click)
            
            def update_selection_count():
                count = sum(1 for item_id in tree.get_children() if 'checked' in tree.item(item_id, 'tags'))
                selection_label.config(text=f"선택: {count}건")
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar_y.config(command=tree.yview)
            scrollbar_x.config(command=tree.xview)
            
            # 하단 버튼
            button_frame = ttk.Frame(preview_window, padding="10")
            button_frame.pack(fill=tk.X)
            
            def upload_selected():
                # 선택된 항목 업로드
                selected_indices = []
                for item_id in tree.get_children():
                    if 'checked' in tree.item(item_id, 'tags'):
                        values = tree.item(item_id, 'values')
                        idx = int(values[1]) - 1  # # 컬럼에서 인덱스 가져오기
                        selected_indices.append(idx)
                
                if not selected_indices:
                    messagebox.showwarning("경고", "업로드할 항목을 선택하세요.")
                    return
                
                result = messagebox.askyesno("확인", 
                                            f"{len(selected_indices)}건의 데이터를 업로드하시겠습니까?")
                if result:
                    preview_window.destroy()
                    self.upload_selected_items(selected_indices)
            
            ttk.Button(
                button_frame,
                text="✅ 선택 항목 업로드",
                command=upload_selected,
                width=20
            ).pack(side=tk.RIGHT, padx=5)
            
            ttk.Button(
                button_frame,
                text="닫기",
                command=preview_window.destroy,
                width=15
            ).pack(side=tk.RIGHT, padx=5)
            
            self.log("✅ 업로드 미리보기 창 열림")
            
        except Exception as e:
            self.log(f"❌ 미리보기 창 오류: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("오류", f"미리보기 창을 여는 중 오류가 발생했습니다:\n{str(e)}")
    
    def open_data_viewer(self, records=None):
        """데이터 뷰어 창 열기"""
        viewer = tk.Toplevel(self.root)
        viewer.title("NocoDB Equipments 데이터 조회")
        viewer.geometry("1400x700")
        
        # 상단 정보
        info_frame = ttk.Frame(viewer, padding="10")
        info_frame.pack(fill=tk.X)
        
        # 레코드 개수 라벨 (동적 업데이트용)
        count_label = ttk.Label(
            info_frame,
            text=f"총 {len(records) if records else 0}건의 레코드",
            font=('Helvetica', 12, 'bold')
        )
        count_label.pack(side=tk.LEFT, padx=10)
        
        # 새로고침 버튼 (tree는 아래에서 정의되므로 함수로 감싸기)
        def create_refresh_button():
            def refresh_data():
                try:
                    self.log("\n🔄 NocoDB 데이터 새로고침 중...")
                    
                    headers = {"xc-token": self.API_TOKEN}
                    url = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
                    
                    params = {
                        "limit": 1000,
                        "sort": "Id"
                    }
                    
                    response = requests.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        new_records = data.get('list', [])
                        
                        # Treeview 초기화
                        for item in tree.get_children():
                            tree.delete(item)
                        
                        # 새 데이터 삽입
                        for record in new_records:
                            values = []
                            for col in columns:
                                val = record.get(col, '')
                                values.append(str(val) if val is not None else '')
                            tree.insert('', 'end', values=values)
                        
                        # 개수 업데이트
                        count_label.config(text=f"총 {len(new_records)}건의 레코드")
                        self.log(f"✅ 새로고침 완료: {len(new_records)}건")
                        
                    else:
                        self.log(f"❌ 새로고침 실패: {response.status_code}")
                        messagebox.showerror("오류", f"새로고침 실패: {response.status_code}")
                        
                except Exception as e:
                    self.log(f"❌ 새로고침 오류: {str(e)}")
                    messagebox.showerror("오류", f"새로고침 중 오류가 발생했습니다:\n{str(e)}")
            
            return refresh_data
        
        refresh_btn = ttk.Button(
            info_frame,
            text="🔄 새로고침",
            command=create_refresh_button(),
            width=15
        )
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(
            info_frame,
            text="※ 데이터는 Id 순서대로 표시됩니다.",
            foreground="gray"
        ).pack(side=tk.LEFT, padx=10)
        
        # Treeview 프레임
        tree_frame = ttk.Frame(viewer)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 스크롤바
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 표시할 컬럼 정의
        columns = ['Id', 'sid', 'model', 'end_user', 'end_date', 'ri', 'xy_scanner', 
                   'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 'approval_status']
        
        # Treeview 생성
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 컬럼 헤더 설정
        column_widths = {
            'Id': 50,
            'sid': 150,
            'model': 120,
            'end_user': 200,
            'end_date': 100,
            'ri': 100,
            'xy_scanner': 130,
            'head_type': 130,
            'mod_vit': 160,
            'sliding_stage': 100,
            'sample_chuck': 150,
            'ae': 120,
            'approval_status': 100
        }
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=column_widths.get(col, 100), anchor='w')
        
        # 데이터 삽입
        for record in records:
            values = []
            for col in columns:
                val = record.get(col, '')
                # None을 빈 문자열로 변환
                values.append(str(val) if val is not None else '')
            tree.insert('', 'end', values=values)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        # 하단 닫기 버튼
        button_frame = ttk.Frame(viewer, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="닫기",
            command=viewer.destroy,
            width=15
        ).pack(side=tk.RIGHT, padx=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = MigrationToolGUI(root)
    root.mainloop()

