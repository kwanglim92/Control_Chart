import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import threading
import requests
from datetime import datetime
from typing import Dict

class ChecklistUploaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 NocoDB Checklist Uploader v2")
        self.root.geometry("1100x950")
        self.root.resizable(True, True)

        # 설정 (NocoDB API)
        self.BASE_URL = "http://10.4.1.141:8003/api/v2"
        self.API_TOKEN = "fkyIVsRDiwZzOj_vhwg_UFFBEWVNCKcET5pacie0"  # 기본값
        self.BASE_ID = "pdb2qjlkujb4bld"
        
        # Table IDs (최신)
        self.TABLE_IDS = {
            "Engineers": "mu8lyr6gb7ib5vz",
            "Equipments": "m59x2omec97hpjo",
            "ChecklistRawData": "mefhik2pjcx5tve"
        }
        
        # NocoDB 필드 캐시
        self.nocodb_fields = {}
        
        # 데이터 저장
        self.equipment_info = {}
        self.measurement_data = pd.DataFrame()
        self.equipment_config = {}  # 장비 구성 선택값
        self.required_config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']

        self.setup_ui()
        
        # 초기 필드 정보 조회
        self.fetch_nocodb_fields()

    def setup_ui(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 제목
        title_label = ttk.Label(main_frame, text="NocoDB Checklist Uploader v2", 
                                font=('Helvetica', 16, 'bold'))
        title_label.pack(pady=(0, 10))

        # === 1. API Token 섹션 ===
        token_frame = ttk.LabelFrame(main_frame, text="1. NocoDB API Token", padding="10")
        token_frame.pack(fill=tk.X, pady=10)

        token_inner = ttk.Frame(token_frame)
        token_inner.pack(fill=tk.X)

        self.token_var = tk.StringVar(value=self.API_TOKEN)
        self.token_entry = ttk.Entry(token_inner, textvariable=self.token_var, width=60, show="*", state='readonly')
        self.token_entry.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        ttk.Label(token_inner, text="✅ 기본 설정됨", foreground="green").pack(side=tk.LEFT, padx=5)
        ttk.Button(token_inner, text="변경", command=self.change_token).pack(side=tk.RIGHT)

        # === 2. 파일 선택 섹션 ===
        file_frame = ttk.LabelFrame(main_frame, text="2. Excel 파일 선택", padding="10")
        file_frame.pack(fill=tk.X, pady=10)

        self.file_path_var = tk.StringVar(value="Industrial Check List 파일을 선택하세요 (.xlsx)")
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly', width=60)
        file_entry.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)

        self.browse_btn = ttk.Button(file_frame, text="찾아보기", command=self.browse_file)
        self.browse_btn.pack(side=tk.RIGHT)

        # === 3. 탭 프리뷰 섹션 ===
        preview_frame = ttk.LabelFrame(main_frame, text="3. 업로드 데이터 미리보기", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # 탭 생성
        self.tab_control = ttk.Notebook(preview_frame)
        
        # Equipments 탭
        self.equip_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.equip_tab, text="📋 Equipments 테이블")
        
        # === 기본 정보 표시 ===
        info_display_frame = ttk.LabelFrame(self.equip_tab, text="추출된 기본 정보", padding="10")
        info_display_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.basic_info_text = tk.Text(info_display_frame, height=8, state='disabled',
                                       font=('Consolas', 9), wrap=tk.WORD, bg='#f0f0f0')
        self.basic_info_text.pack(fill=tk.X)
        
        # === 장비 구성 선택 프레임 ===
        config_outer_frame = ttk.LabelFrame(self.equip_tab, text="장비 구성 선택 (필수)", padding="10")
        config_outer_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 검증 상태 표시
        validation_frame = ttk.Frame(config_outer_frame)
        validation_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.validation_status_label = ttk.Label(validation_frame, text="", font=('Helvetica', 10, 'bold'))
        self.validation_status_label.pack(side=tk.LEFT)
        
        # 구성 필드들
        config_grid_frame = ttk.Frame(config_outer_frame)
        config_grid_frame.pack(fill=tk.X)
        
        self.config_widgets = {}
        self.config_labels = {}
        config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
        
        for idx, field in enumerate(config_fields):
            row = idx // 2
            col = idx % 2
            
            field_frame = ttk.Frame(config_grid_frame)
            field_frame.grid(row=row, column=col, padx=10, pady=5, sticky='ew')
            
            # 필드 라벨 (필수 표시 포함)
            label_text = f"{field}:"
            label = ttk.Label(field_frame, text=label_text, width=15)
            label.pack(side=tk.LEFT)
            self.config_labels[field] = label
            
            # 콤보박스
            combo = ttk.Combobox(field_frame, state='readonly', width=25)
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            combo.bind('<<ComboboxSelected>>', lambda e, f=field: self.on_config_change(f))
            self.config_widgets[field] = combo
        
        config_grid_frame.columnconfigure(0, weight=1)
        config_grid_frame.columnconfigure(1, weight=1)
        
        # 선택 완료 버튼
        confirm_btn_frame = ttk.Frame(config_outer_frame)
        confirm_btn_frame.pack(fill=tk.X, pady=10)
        
        self.confirm_config_btn = ttk.Button(confirm_btn_frame, text="✅ 선택 완료 (미리보기 업데이트)", 
                                             command=self.confirm_equipment_config, state='disabled')
        self.confirm_config_btn.pack()
        
        # === NocoDB 업로드 미리보기 버튼 (별도 창) ===
        preview_btn_frame = ttk.Frame(self.equip_tab)
        preview_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.preview_upload_btn = ttk.Button(
            preview_btn_frame, 
            text="📋 NocoDB 업로드 형태 미리보기",
            command=self.show_upload_preview,
            state='disabled',
            width=30
        )
        self.preview_upload_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            preview_btn_frame,
            text="※ 선택 완료 후 업로드될 데이터 형태를 별도 창에서 확인할 수 있습니다.",
            foreground="gray",
            font=('Helvetica', 9)
        ).pack(side=tk.LEFT, padx=10)
        
        # ChecklistRawData 탭
        self.data_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.data_tab, text="📊 ChecklistRawData 테이블")
        
        data_scroll_frame = ttk.Frame(self.data_tab)
        data_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        data_scrollbar = ttk.Scrollbar(data_scroll_frame)
        data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.data_text = tk.Text(data_scroll_frame, height=12, state='disabled', 
                                font=('Consolas', 9), yscrollcommand=data_scrollbar.set, wrap=tk.WORD)
        self.data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        data_scrollbar.config(command=self.data_text.yview)
        
        # Raw Data 보기 버튼
        btn_frame = ttk.Frame(self.data_tab)
        btn_frame.pack(fill=tk.X, pady=5)
        self.view_raw_btn = ttk.Button(btn_frame, text="📄 Raw Data 상세보기", 
                                       command=self.show_raw_data, state='disabled')
        self.view_raw_btn.pack(side=tk.LEFT, padx=5)
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)

        # === 4. 진행 상황 ===
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)

        # === 5. 로그 ===
        log_frame = ttk.LabelFrame(main_frame, text="4. 업로드 로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_scroll_frame = ttk.Frame(log_frame)
        log_scroll_frame.pack(fill=tk.BOTH, expand=True)

        log_scrollbar = ttk.Scrollbar(log_scroll_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_scroll_frame, height=6, state='disabled', font=('Consolas', 9),
                                yscrollcommand=log_scrollbar.set, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)

        # === 6. 업로드 및 데이터 조회 버튼 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        self.upload_btn = ttk.Button(button_frame, text="✅ NocoDB에 업로드", 
                                     command=self.start_upload, state='disabled', width=20)
        self.upload_btn.pack(side=tk.LEFT, padx=5)
        
        # [NEW] 데이터 조회 버튼
        self.view_data_btn = ttk.Button(button_frame, text="📊 NocoDB 데이터 조회",
                                        command=self.view_nocodb_data, width=25)
        self.view_data_btn.pack(side=tk.LEFT, padx=5)

    def change_token(self):
        """API Token 변경"""
        dialog = tk.Toplevel(self.root)
        dialog.title("API Token 변경")
        dialog.geometry("500x150")
        dialog.resizable(False, False)
        dialog.grab_set()
        
        ttk.Label(dialog, text="새 API Token을 입력하세요:", font=('Helvetica', 10)).pack(pady=10)
        
        new_token_var = tk.StringVar(value=self.API_TOKEN)
        token_entry = ttk.Entry(dialog, textvariable=new_token_var, width=60)
        token_entry.pack(pady=10, padx=20)
        
        def save_token():
            new_token = new_token_var.get().strip()
            if not new_token:
                messagebox.showerror("오류", "Token을 입력하세요.")
                return
            self.API_TOKEN = new_token
            self.token_var.set(new_token)
            self.fetch_nocodb_fields()
            messagebox.showinfo("완료", "API Token이 변경되었습니다!")
            self.log("✅ API Token이 변경되었습니다.")
            dialog.destroy()
        
        ttk.Button(dialog, text="저장", command=save_token).pack(pady=10)

    def fetch_nocodb_fields(self):
        """NocoDB 테이블 필드 정보 조회"""
        try:
            headers = {"xc-token": self.API_TOKEN}
            
            # Equipments 테이블
            equip_url = f"{self.BASE_URL}/meta/tables/{self.TABLE_IDS['Equipments']}"
            response = requests.get(equip_url, headers=headers)
            
            if response.status_code == 200:
                columns = response.json().get('columns', [])
                equip_fields = {}
                for col in columns:
                    col_title = col.get('title')
                    col_type = col.get('uidt')
                    col_options = col.get('colOptions', {})
                    if col_title and col_title not in ['Id', 'CreatedAt', 'UpdatedAt']:
                        equip_fields[col_title] = {
                            'type': col_type,
                            'options': [opt.get('title') for opt in col_options.get('options', [])] if col_type == 'SingleSelect' else []
                        }
                self.nocodb_fields['Equipments'] = equip_fields
                self.log(f"✅ Equipments 필드 {len(equip_fields)}개 조회됨")
                
                # 장비 구성 필드의 옵션 업데이트
                self.update_config_options()
            
            # ChecklistRawData 테이블
            data_url = f"{self.BASE_URL}/meta/tables/{self.TABLE_IDS['ChecklistRawData']}"
            response = requests.get(data_url, headers=headers)
            
            if response.status_code == 200:
                columns = response.json().get('columns', [])
                data_fields = {}
                for col in columns:
                    col_title = col.get('title')
                    col_type = col.get('uidt')
                    if col_title and col_title not in ['Id', 'CreatedAt', 'UpdatedAt']:
                        data_fields[col_title] = col_type
                self.nocodb_fields['ChecklistRawData'] = data_fields
                self.log(f"✅ ChecklistRawData 필드 {len(data_fields)}개 조회됨")
                
        except Exception as e:
            self.log(f"⚠️ 필드 조회 오류: {str(e)}")

    def update_config_options(self):
        """장비 구성 필드 옵션 업데이트 (NocoDB에서 직접)"""
        equip_fields = self.nocodb_fields.get('Equipments', {})
        
        for field_name, combo_widget in self.config_widgets.items():
            if field_name in equip_fields:
                options = equip_fields[field_name].get('options', [])
                combo_widget['values'] = options
                if options:
                    combo_widget.set('')  # 초기화
            
            # 필수 필드 표시
            if field_name in self.required_config_fields:
                label = self.config_labels[field_name]
                label.config(text=f"{field_name}:  *", foreground='red')
            else:
                label = self.config_labels[field_name]
                label.config(text=f"{field_name}:", foreground='black')
    
    def update_config_for_model(self, model: str):
        """모델 로드 후 초기화 (조건부 규칙 없이 단순 리셋)"""
        # 현재 구성 초기화
        self.equipment_config = {}
        
        # 모든 콤보박스 초기화
        for field_name, combo_widget in self.config_widgets.items():
            combo_widget.set('')  # 초기화
        
        # 검증 상태 업데이트
        self.update_validation_status()
    
    def on_config_change(self, changed_field: str):
        """장비 구성 선택 변경 시 (조건부 규칙 없음)"""
        # 현재 구성 가져오기
        current_config = self.get_current_config()
        
        # 변경된 필드값 저장
        self.equipment_config[changed_field] = current_config.get(changed_field, '')
        
        # 검증 상태 업데이트
        self.update_validation_status()
    
    def get_current_config(self) -> Dict[str, str]:
        """현재 선택된 구성 반환"""
        config = {}
        for field_name, combo in self.config_widgets.items():
            value = combo.get()
            if value:
                config[field_name] = value
        return config
    
    def update_validation_status(self):
        """검증 상태 업데이트 (필수 필드 확인만)"""
        model = self.equipment_info.get('model')
        if not model:
            self.validation_status_label.config(text="", foreground="black")
            return
        
        config = self.get_current_config()
        
        # 필수 필드 확인
        missing_fields = []
        for field in self.required_config_fields:
            if field not in config or not config[field]:
                missing_fields.append(field)
        
        if not missing_fields:
            self.validation_status_label.config(
                text="✅ 모든 필수 항목 선택됨 - 업로드 가능",
                foreground="green"
            )
        else:
            self.validation_status_label.config(
                text=f"❌ {len(missing_fields)}개 필수 항목 미선택",
                foreground="red"
            )
        
        # "선택 완료" 버튼 활성화 여부
        if not missing_fields and self.equipment_info.get('model'):
            self.confirm_config_btn.config(state='normal')
        else:
            self.confirm_config_btn.config(state='disabled')
    
    def confirm_equipment_config(self):
        """장비 구성 선택 완료 - NocoDB 업로드 형태 미리보기 업데이트"""
        config = self.get_current_config()
        
        if len(config) != len(self.required_config_fields):
            messagebox.showwarning("경고", "모든 필수 항목을 선택해주세요.")
            return
        
        # 장비 구성 저장
        self.equipment_config = config
        
        # Equipments 테이블 미리보기 업데이트
        info = self.equipment_info
        equip_preview = "📋 Equipments 테이블 업로드 형태:\n\n"
        equip_preview += "=" * 60 + "\n"
        equip_preview += "[기본 정보]\n"
        equip_preview += f"  Sid: {info.get('sid', 'N/A')}\n"
        equip_preview += f"  model: {info.get('model', 'N/A')}\n"
        equip_preview += f"  end_user: {info.get('end_user', 'N/A')}\n"
        equip_preview += f"  end_date: {info.get('end_date', 'N/A')}\n"
        equip_preview += f"  production_engineer: {info.get('production_engineer', 'N/A')}\n"
        equip_preview += f"  qc_engineer: {info.get('qc_engineer', 'N/A')}\n"
        equip_preview += f"  checklist_version: {info.get('checklist_version', 'N/A')}\n"
        equip_preview += f"  approval_status: 대기\n"
        equip_preview += "\n[장비 구성]\n"
        
        for field_name, value in config.items():
            equip_preview += f"  {field_name}: {value}\n"
        
        equip_preview += "\n" + "=" * 60 + "\n"
        equip_preview += "✅ 업로드 준비 완료!\n"
        
        self.update_preview(self.equip_text, equip_preview)
        
        self.log(f"✅ 장비 구성 선택 완료: {', '.join([f'{k}={v}' for k, v in config.items()])}")
        messagebox.showinfo("완료", "장비 구성이 확정되었습니다!\n\n이제 'NocoDB에 업로드' 버튼으로 업로드할 수 있습니다.")
    
    def update_basic_info_display(self):
        """기본 정보 표시 업데이트"""
        self.basic_info_text.config(state='normal')
        self.basic_info_text.delete(1.0, tk.END)
        
        info = self.equipment_info
        model = info.get('model', 'N/A')
        display_name = model
        
        basic_info = f"""┌─ 추출된 장비 정보 ─────────────────────────────┐

  • SID                : {info.get('sid', 'N/A')}
  • Model              : {display_name}
  • End User           : {info.get('end_user', 'N/A')}
  • End Date           : {info.get('end_date', 'N/A')}
  • Production Engineer: {info.get('production_engineer', 'N/A')}
  • QC Engineer        : {info.get('qc_engineer', 'N/A')}
  • Checklist Version  : {info.get('checklist_version', 'N/A')}

└───────────────────────────────────────────────────┘
"""
        
        self.basic_info_text.insert(tk.END, basic_info)
        self.basic_info_text.config(state='disabled')

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"> {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def update_preview(self, widget, text):
        """탭 미리보기 업데이트"""
        widget.config(state='normal')
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, text)
        widget.config(state='disabled')

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")])
        if file_path:
            self.file_path_var.set(file_path)
            self.extract_and_preview(file_path)

    def extract_and_preview(self, filepath):
        """Excel 파일에서 정보 추출 및 미리보기"""
        try:
            # Last 시트에서 장비 정보 추출
            df_last = pd.read_excel(filepath, sheet_name='Last', header=None)
            
            equip_info = {}
            
            # checklist_version 추출 (첫 행에서 "Industrial Check List v3.21.1" 같은 패턴)
            for row_idx in range(min(5, len(df_last))):
                for col_idx in range(min(15, len(df_last.columns))):
                    cell_value = df_last.iloc[row_idx, col_idx]
                    if pd.notna(cell_value) and 'Industrial Check List' in str(cell_value):
                        # "Industrial Check List v3.21.1" -> "v3.21.1"
                        version_str = str(cell_value).strip()
                        if 'v' in version_str:
                            equip_info['checklist_version'] = version_str.split('v')[-1].strip()
                        break
                if 'checklist_version' in equip_info:
                    break
            
            if len(df_last) > 21 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[21, 11]):
                equip_info['model'] = str(df_last.iloc[21, 11]).strip()
            if len(df_last) > 24 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[24, 11]):
                equip_info['sid'] = str(df_last.iloc[24, 11]).strip()
            if len(df_last) > 30 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[30, 11]):
                date_val = df_last.iloc[30, 11]
                if isinstance(date_val, (datetime, pd.Timestamp)):
                    equip_info['end_date'] = date_val.strftime('%Y-%m-%d')
                else:
                    equip_info['end_date'] = str(date_val)
            if len(df_last) > 33 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[33, 11]):
                equip_info['end_user'] = str(df_last.iloc[33, 11]).strip()
            if len(df_last) > 36 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[36, 11]):
                equip_info['production_engineer'] = str(df_last.iloc[36, 11]).strip()
            if len(df_last) > 39 and len(df_last.columns) > 11 and pd.notna(df_last.iloc[39, 11]):
                equip_info['qc_engineer'] = str(df_last.iloc[39, 11]).strip()

            self.equipment_info = equip_info

            # 기본 정보 표시 업데이트
            self.update_basic_info_display()
            
            # 모델에 따른 장비 구성 옵션 설정
            if equip_info.get('model'):
                self.update_config_for_model(equip_info['model'])

            # 모델 시트에서 측정 데이터 추출 (전체 데이터, Trend 필터 제거)
            excel_file = pd.ExcelFile(filepath)
            model_sheet = equip_info.get('model', '')
            
            if model_sheet and model_sheet in excel_file.sheet_names:
                df_data = pd.read_excel(filepath, sheet_name=model_sheet)
                # Measurement가 있는 행만 추출 (Trend 필터 제거 - 전체 데이터)
                df_filtered = df_data[df_data.get('Measurement', pd.Series()).notna()]
                self.measurement_data = df_filtered
                data_count = len(df_filtered)
                trend_count = len(df_filtered[df_filtered.get('Trend', pd.Series()).notna()])
            else:
                self.measurement_data = pd.DataFrame()
                data_count = 0
                trend_count = 0

            # Equipments 탭 미리보기
            equip_preview = "📋 Equipments 테이블 업로드 형태:\n\n"
            equip_preview += "=" * 60 + "\n"
            equip_preview += "[기본 정보]\n"
            equip_preview += f"  Sid: {equip_info.get('sid', 'N/A')}\n"
            equip_preview += f"  model: {equip_info.get('model', 'N/A')}\n"
            equip_preview += f"  end_user: {equip_info.get('end_user', 'N/A')}\n"
            equip_preview += f"  end_date: {equip_info.get('end_date', 'N/A')}\n"
            equip_preview += f"  production_engineer: {equip_info.get('production_engineer', 'N/A')}\n"
            equip_preview += f"  qc_engineer: {equip_info.get('qc_engineer', 'N/A')}\n"
            equip_preview += f"  checklist_version: {equip_info.get('checklist_version', 'N/A')}\n"
            equip_preview += f"  approval_status: 대기\n"
            equip_preview += "\n[장비 구성] - 위 콤보박스에서 선택 필요\n"
            
            config_fields = ['ri', 'xy_scanner', 'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
            for field in config_fields:
                equip_preview += f"  {field}: (선택 필요)\n"
            
            equip_preview += "\n" + "=" * 60 + "\n"
            equip_preview += "⚠️ 장비 구성을 모두 선택해야 업로드할 수 있습니다.\n"

            # ChecklistRawData 탭 미리보기
            data_preview = "📊 ChecklistRawData 테이블 업로드 형태:\n\n"
            data_preview += f"총 {data_count}건의 측정 데이터 (Trend 항목: {trend_count}건)\n"
            data_preview += "=" * 60 + "\n\n"
            
            if data_count > 0:
                data_preview += f"Equipment SID: {equip_info.get('sid', 'N/A')}\n\n"
                data_preview += "첫 3개 레코드 미리보기:\n"
                data_preview += "-" * 60 + "\n"
                
                for idx, row in self.measurement_data.head(3).iterrows():
                    is_trend = pd.notna(row.get('Trend'))
                    trend_mark = "✓ Trend" if is_trend else ""
                    data_preview += f"\n[레코드 {idx + 1}] {trend_mark}\n"
                    data_preview += f"  Module: {row.get('Module', 'N/A')}\n"
                    data_preview += f"  Check Items: {row.get('Check Items', 'N/A')}\n"
                    data_preview += f"  Measurement: {row.get('Measurement', 'N/A')}\n"
                    data_preview += f"  Criteria: {row.get('Criteria', 'N/A')}\n"
                    data_preview += f"  PASS/FAIL: {row.get('PASS/FAIL', 'N/A')}\n"
                
                data_preview += "\n" + "-" * 60 + "\n"
                data_preview += f"... 외 {data_count - 3}건\n"
                data_preview += f"\n✅ 전체 데이터가 업로드됩니다 (Trend 항목 포함)\n"
                
                self.view_raw_btn.config(state='normal')
            else:
                data_preview += "(측정 데이터 없음)\n"
            
            self.update_preview(self.data_text, data_preview)
            
            self.log(f"✅ 정보 추출 완료: SID {equip_info.get('sid', 'N/A')}, 전체 {data_count}건 (Trend {trend_count}건)")
            
            # 미리보기 버튼 활성화
            self.preview_upload_btn.config(state='normal')

        except Exception as e:
            messagebox.showerror("오류", f"파일 읽기 실패:\n{str(e)}")
            self.log(f"❌ 오류: {str(e)}")

    def show_raw_data(self):
        """Raw Data 팝업 창 with Trend 필터"""
        if self.measurement_data.empty:
            messagebox.showinfo("정보", "측정 데이터가 없습니다.")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title(f"📄 Raw Data - SID: {self.equipment_info.get('sid', 'N/A')}")
        popup.geometry("1200x700")
        
        # 프레임
        frame = ttk.Frame(popup, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단: 타이틀 + Trend 필터
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=5)
        
        total_count = len(self.measurement_data)
        trend_count = len(self.measurement_data[self.measurement_data.get('Trend', pd.Series()).notna()])
        
        title_label = ttk.Label(header_frame, text=f"총 {total_count}건의 측정 데이터 (Trend: {trend_count}건)", 
                               font=('Helvetica', 12, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        # Trend 필터 체크박스
        trend_filter_var = tk.BooleanVar(value=False)
        
        def update_table(show_trend_only):
            # Treeview 초기화
            for item in tree.get_children():
                tree.delete(item)
            
            # 필터링
            if show_trend_only:
                filtered_df = self.measurement_data[self.measurement_data.get('Trend', pd.Series()).notna()]
            else:
                filtered_df = self.measurement_data
            
            # 데이터 삽입
            for idx, row in filtered_df.iterrows():
                values = [row.get(col, '') for col in columns]
                tree.insert("", "end", values=values)
            
            # 카운트 업데이트
            count_text = f"표시: {len(filtered_df)}건"
            if show_trend_only:
                count_text += " (Trend 항목만)"
            count_label.config(text=count_text)
        
        trend_check = ttk.Checkbutton(header_frame, text="Trend 항목만 보기", 
                                      variable=trend_filter_var,
                                      command=lambda: update_table(trend_filter_var.get()))
        trend_check.pack(side=tk.RIGHT, padx=10)
        
        count_label = ttk.Label(header_frame, text=f"표시: {total_count}건", foreground="blue")
        count_label.pack(side=tk.RIGHT, padx=10)
        
        # Treeview로 테이블 표시
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤바
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        columns = list(self.measurement_data.columns)
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 헤더 설정
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # 초기 데이터 로드
        update_table(False)
        
        # 닫기 버튼
        ttk.Button(frame, text="닫기", command=popup.destroy).pack(pady=10)
    
    def show_upload_preview(self):
        """NocoDB 업로드 형태 미리보기 (별도 창)"""
        if not self.equipment_info.get('sid'):
            messagebox.showwarning("경고", "먼저 Excel 파일을 선택하고 장비 구성을 완료하세요.")
            return
        
        # 업로드 데이터 생성
        upload_data = {
            'sid': self.equipment_info.get('sid', ''),
            'model': self.equipment_info.get('model', ''),
            'end_user': self.equipment_info.get('end_user', ''),
            'end_date': self.equipment_info.get('end_date', ''),
            'production_engineer': self.equipment_info.get('production_engineer', ''),
            'checklist_version': self.equipment_info.get('checklist_version', ''),
            'approval_status': 'pending',
            **self.equipment_config  # 장비 구성 추가
        }
        
        # 팝업 창 생성
        preview_window = tk.Toplevel(self.root)
        preview_window.title("NocoDB Equipments 업로드 형태 미리보기")
        preview_window.geometry("700x600")
        
        # 상단 정보
        info_frame = ttk.Frame(preview_window, padding="10")
        info_frame.pack(fill=tk.X)
        
        ttk.Label(
            info_frame,
            text="📋 Equipments 테이블 업로드 데이터",
            font=('Helvetica', 14, 'bold')
        ).pack(anchor=tk.W)
        
        ttk.Label(
            info_frame,
            text="※ 아래 형태로 NocoDB에 업로드됩니다.",
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # 데이터 표시 프레임
        data_frame = ttk.Frame(preview_window, padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(data_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 텍스트 위젯
        text_widget = tk.Text(
            data_frame,
            font=('Consolas', 10),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            bg='#f5f5f5'
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # 데이터 포맷팅
        preview_text = "=" * 60 + "\n"
        preview_text += "[Equipments 테이블 업로드 데이터]\n"
        preview_text += "=" * 60 + "\n\n"
        
        # 필드별 표시
        field_labels = {
            'sid': 'SID',
            'model': 'Model',
            'end_user': 'End User',
            'end_date': 'End Date',
            'production_engineer': 'Production Engineer',
            'ri': 'RI',
            'xy_scanner': 'XY Scanner',
            'head_type': 'Head Type',
            'mod_vit': 'MOD VIT',
            'sliding_stage': 'Sliding Stage',
            'sample_chuck': 'Sample Chuck',
            'ae': 'AE',
            'checklist_version': 'Checklist Version',
            'approval_status': 'Approval Status'
        }
        
        for field, label in field_labels.items():
            value = upload_data.get(field, '(NULL)')
            preview_text += f"  • {label:25s}: {value}\n"
        
        preview_text += "\n" + "=" * 60 + "\n"
        
        # 텍스트 삽입
        text_widget.insert('1.0', preview_text)
        text_widget.config(state='disabled')
        
        # 하단 버튼
        button_frame = ttk.Frame(preview_window, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="닫기",
            command=preview_window.destroy,
            width=15
        ).pack(side=tk.RIGHT, padx=5)

    def start_upload(self):
        if not self.API_TOKEN:
            messagebox.showerror("오류", "API Token을 먼저 설정하세요.")
            return
        
        if not self.equipment_info.get('sid'):
            messagebox.showerror("오류", "먼저 Excel 파일을 선택하세요.")
            return
        
        # 필수 필드 검증
        config = self.get_current_config()
        missing_configs = []
        for field in self.required_config_fields:
            if field not in config or not config[field]:
                missing_configs.append(field)
        
        if missing_configs:
            messagebox.showerror("오류", f"다음 필수 장비 구성을 선택하세요:\n\n" + "\n".join(f"• {f}" for f in missing_configs))
            return
        
        # 검증 통과 - 구성 저장
        self.equipment_config = config
        
        # [NEW] SID 중복 검사
        if not self.check_sid_duplicate():
            return  # 사용자가 취소한 경우
        
        self.upload_btn.config(state='disabled')
        self.browse_btn.config(state='disabled')
        self.progress_var.set(0)
        
        threading.Thread(target=self.run_upload, daemon=True).start()

    def run_upload(self):
        """NocoDB에 데이터 업로드"""
        try:
            headers = {"xc-token": self.API_TOKEN}

            # 1단계: Equipments 테이블에 삽입
            self.log("1/2: 장비 정보 업로드 중...")
            
            equip_payload = {}
            
            # 기본 정보
            basic_mapping = {
                'sid': 'Sid',
                'model': 'model',
                'end_user': 'end_user',
                'end_date': 'end_date',
                'production_engineer': 'production_engineer',
                'qc_engineer': 'qc_engineer',
                'checklist_version': 'checklist_version'
            }
            
            for excel_field, nocodb_field in basic_mapping.items():
                value = self.equipment_info.get(excel_field)
                if value and nocodb_field in self.nocodb_fields.get('Equipments', {}):
                    equip_payload[nocodb_field] = value
            
            # 장비 구성 추가
            for field_name, value in self.equipment_config.items():
                if field_name in self.nocodb_fields.get('Equipments', {}):
                    equip_payload[field_name] = value
            
            # approval_status
            if 'approval_status' in self.nocodb_fields.get('Equipments', {}):
                equip_payload['approval_status'] = "대기"
            
            self.log(f"→ 업로드 필드: {list(equip_payload.keys())}")
            
            url_equip = f"{self.BASE_URL}/tables/{self.TABLE_IDS['Equipments']}/records"
            response = requests.post(url_equip, headers=headers, json=equip_payload)
            
            if response.status_code in [200, 201]:
                self.log(f"✅ 장비 정보 업로드 완료: {self.equipment_info.get('sid')}")
                self.progress_var.set(50)
            else:
                self.log(f"❌ 장비 업로드 실패: {response.status_code} - {response.text}")
                messagebox.showerror("오류", f"장비 업로드 실패:\n{response.text}")
                return

            # 2단계: ChecklistRawData 테이블에 측정 데이터 삽입 (전체 데이터)
            total_records = len(self.measurement_data)
            self.log(f"2/2: 측정 데이터 업로드 중 (전체 {total_records}건)...")
            url_data = f"{self.BASE_URL}/tables/{self.TABLE_IDS['ChecklistRawData']}/records"
            
            success_count = 0
            fail_count = 0
            
            for idx, row in self.measurement_data.iterrows():
                data_payload = {}
                
                checklist_fields = self.nocodb_fields.get('ChecklistRawData', {})
                
                if 'equipment' in checklist_fields:
                    data_payload['equipment'] = self.equipment_info.get('sid')
                
                data_mapping = {
                    'Module': 'module',
                    'Check Items': 'check_items',
                    'Min': 'min',
                    'Criteria': 'criteria',
                    'Max': 'max',
                    'Measurement': 'measurement',
                    'Unit': 'unit',
                    'PASS/FAIL': 'pass_fail',
                    'Trend': 'trend'
                }
                
                for excel_col, nocodb_field in data_mapping.items():
                    if excel_col in row.index:
                        value = row.get(excel_col)
                        
                        if nocodb_field in checklist_fields or not checklist_fields:
                            if nocodb_field == 'trend':
                                data_payload[nocodb_field] = bool(value) if pd.notna(value) else False
                            elif pd.notna(value):
                                data_payload[nocodb_field] = value
                
                response = requests.post(url_data, headers=headers, json=data_payload)
                
                if response.status_code in [200, 201]:
                    success_count += 1
                else:
                    fail_count += 1
                    if fail_count <= 5:  # 처음 5개 오류만 로깅
                        self.log(f"⚠️ Row {idx} 업로드 실패: {response.text[:100]}")
                
                # 진행률 업데이트
                progress = 50 + int((idx + 1) / total_records * 50)
                self.progress_var.set(progress)
            
            self.progress_var.set(100)
            self.log(f"✅ 측정 데이터 업로드 완료: 성공 {success_count}건, 실패 {fail_count}건")
            self.log("✅ 모든 데이터 업로드 완료!")
            messagebox.showinfo("성공", f"NocoDB 업로드가 완료되었습니다!\n\n장비 정보: 1건\n측정 데이터: {success_count}/{total_records}건")

        except Exception as e:
            self.log(f"❌ 오류 발생: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            messagebox.showerror("오류", f"업로드 중 오류:\n{str(e)}")
        
        finally:
            self.upload_btn.config(state='normal')
            self.browse_btn.config(state='normal')
            
            # [NEW] 업로드 완료 후 데이터 확인 옵션
            if 'success_count' in locals() and success_count > 0:
                result = messagebox.askyesno("데이터 확인", 
                                            "업로드된 데이터를 확인하시겠습니까?")
                if result:
                    self.view_nocodb_data()
    
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
    
    def check_sid_duplicate(self):
        """업로드 전 SID 중복 검사"""
        sid = self.equipment_info.get('sid', '')
        if not sid:
            return True  # SID가 없으면 검사 스킵
        
        existing_sids = self.fetch_existing_sids()
        
        if str(sid) in existing_sids:
            result = messagebox.askyesno(
                "⚠️ 중복 경고",
                f"SID '{sid}'가 이미 NocoDB에 존재합니다.\n\n"
                f"계속 진행하면 중복 데이터가 생성됩니다.\n\n"
                f"계속 진행하시겠습니까?"
            )
            return result
        
        return True
    
    def view_nocodb_data(self):
        """NocoDB 데이터 조회"""
        # 테이블 선택 다이얼로그
        choice_window = tk.Toplevel(self.root)
        choice_window.title("테이블 선택")
        choice_window.geometry("400x200")
        choice_window.transient(self.root)
        choice_window.grab_set()
        
        ttk.Label(choice_window, text="조회할 테이블을 선택하세요:", 
                 font=('Helvetica', 12, 'bold')).pack(pady=20)
        
        button_frame = ttk.Frame(choice_window)
        button_frame.pack(pady=10)
        
        def view_equipments():
            choice_window.destroy()
            self._fetch_and_display_data('Equipments')
        
        def view_checklist():
            choice_window.destroy()
            self._fetch_and_display_data('ChecklistRawData')
        
        ttk.Button(button_frame, text="📋 Equipments", 
                  command=view_equipments, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="📊 ChecklistRawData", 
                  command=view_checklist, width=20).pack(side=tk.LEFT, padx=10)
        ttk.Button(choice_window, text="취소", 
                  command=choice_window.destroy, width=15).pack(pady=10)
    
    def _fetch_and_display_data(self, table_name):
        """NocoDB에서 데이터 조회 및 표시"""
        try:
            self.log(f"\n📊 {table_name} 데이터 조회 중...")
            
            headers = {"xc-token": self.API_TOKEN}
            url = f"{self.BASE_URL}/tables/{self.TABLE_IDS[table_name]}/records"
            
            params = {
                "limit": 1000,
                "sort": "Id"
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                self.log(f"❌ API 오류: {response.status_code}")
                messagebox.showerror("오류", f"데이터 조회 실패: {response.status_code}")
                return
            
            data = response.json()
            records = data.get('list', [])
            
            if not records:
                self.log(f"ℹ️ {table_name}에 데이터가 없습니다.")
                messagebox.showinfo("조회 결과", f"{table_name} 테이블에 데이터가 없습니다.")
                return
            
            self.log(f"✅ {len(records)}건의 데이터 조회 성공")
            self.open_data_viewer(records, table_name)
            
        except Exception as e:
            self.log(f"❌ 데이터 조회 오류: {str(e)}")
            messagebox.showerror("오류", f"데이터 조회 중 오류:\n{str(e)}")
    
    def open_data_viewer(self, records, table_name):
        """데이터 뷰어 창 열기"""
        viewer = tk.Toplevel(self.root)
        viewer.title(f"NocoDB {table_name} 데이터 조회")
        viewer.geometry("1400x700")
        
        # 상단 정보
        info_frame = ttk.Frame(viewer, padding="10")
        info_frame.pack(fill=tk.X)
        
        # 레코드 개수 라벨
        count_label = ttk.Label(
            info_frame,
            text=f"총 {len(records)}건의 레코드",
            font=('Helvetica', 12, 'bold')
        )
        count_label.pack(side=tk.LEFT, padx=10)
        
        # 새로고침 버튼
        def refresh_data():
            try:
                self.log(f"\n🔄 {table_name} 데이터 새로고침 중...")
                
                headers = {"xc-token": self.API_TOKEN}
                url = f"{self.BASE_URL}/tables/{self.TABLE_IDS[table_name]}/records"
                
                params = {"limit": 1000, "sort": "Id"}
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    new_records = data.get('list', [])
                    
                    # Treeview 초기화
                    for item in tree.get_children():
                        tree.delete(item)
                    
                    # 새 데이터 삽입
                    for record in new_records:
                        values = [str(record.get(col, '')) for col in columns]
                        tree.insert('', 'end', values=values)
                    
                    count_label.config(text=f"총 {len(new_records)}건의 레코드")
                    self.log(f"✅ 새로고침 완료: {len(new_records)}건")
                else:
                    self.log(f"❌ 새로고침 실패: {response.status_code}")
                    
            except Exception as e:
                self.log(f"❌ 새로고침 오류: {str(e)}")
        
        ttk.Button(info_frame, text="🔄 새로고침", 
                  command=refresh_data, width=15).pack(side=tk.LEFT, padx=10)
        
        ttk.Label(info_frame, text="※ 데이터는 Id 순서대로 표시됩니다.", 
                 foreground="gray").pack(side=tk.LEFT, padx=10)
        
        # Treeview 프레임
        tree_frame = ttk.Frame(viewer)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 스크롤바
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 컬럼 정의 (테이블별)
        if table_name == 'Equipments':
            columns = ['Id', 'sid', 'model', 'end_user', 'end_date', 'ri', 'xy_scanner', 
                      'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 'approval_status']
        else:  # ChecklistRawData
            columns = ['Id', 'sid', 'item_name', 'spec', 'measured_value', 'unit', 'result']
        
        # Treeview 생성
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 컬럼 헤더 설정
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120 if col != 'Id' else 50, anchor='w')
        
        # 데이터 삽입
        for record in records:
            values = [str(record.get(col, '')) for col in columns]
            tree.insert('', 'end', values=values)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=tree.yview)
        scrollbar_x.config(command=tree.xview)
        
        # 하단 닫기 버튼
        button_frame = ttk.Frame(viewer, padding="10")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="닫기", 
                  command=viewer.destroy, width=15).pack(side=tk.RIGHT, padx=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChecklistUploaderGUI(root)
    root.mainloop()

