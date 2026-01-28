import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading

class NocoDBViewer:
    """
    NocoDB 데이터를 조회하고 별도의 창에서 표(Table) 형태로 보여주는 재사용 가능한 뷰어 클래스
    """
    def __init__(self, parent, api_token, base_url, table_id):
        """
        :param parent: 부모 Tkinter 창 (tk.Tk 또는 tk.Toplevel)
        :param api_token: NocoDB API 토큰
        :param base_url: NocoDB API 기본 URL (예: http://localhost:8080/api/v2)
        :param table_id: 조회할 테이블 ID
        """
        self.parent = parent
        self.api_token = api_token
        self.base_url = base_url
        self.table_id = table_id
        
        # 표시할 컬럼 설정 (필요에 따라 수정 가능)
        # 딕셔너리 형태: {'필드명': 너비}
        self.columns_config = {
            'Id': 50,
            'Title': 200,      # 예시 필드
            'Status': 100,     # 예시 필드
            'CreatedAt': 150,
            'UpdatedAt': 150
        }

    def open(self):
        """뷰어 창을 엽니다."""
        if not self.api_token:
            messagebox.showerror("오류", "API Token이 설정되지 않았습니다.")
            return

        self._create_window()
        self._fetch_data()

    def _create_window(self):
        """UI 창 생성"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("NocoDB 데이터 뷰어")
        self.window.geometry("1000x600")

        # 상단 컨트롤 프레임
        control_frame = ttk.Frame(self.window, padding="10")
        control_frame.pack(fill=tk.X)

        # 새로고침 버튼
        ttk.Button(control_frame, text="🔄 새로고침", command=self._fetch_data).pack(side=tk.LEFT)
        
        # 상태 메시지 라벨
        self.status_label = ttk.Label(control_frame, text="준비", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # 표(Treeview) 프레임
        tree_frame = ttk.Frame(self.window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 스크롤바
        scrollbar_y = ttk.Scrollbar(tree_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview 생성
        # columns_config의 키(필드명)를 컬럼으로 사용
        columns = list(self.columns_config.keys())
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        # 컬럼 헤더 및 너비 설정
        for col, width in self.columns_config.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='w')

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 스크롤바 연결
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)

    def _fetch_data(self):
        """데이터 가져오기 (스레드 실행)"""
        self.status_label.config(text="데이터 조회 중...", foreground="blue")
        # UI 프리징 방지를 위해 별도 스레드에서 실행
        threading.Thread(target=self._fetch_data_thread, daemon=True).start()

    def _fetch_data_thread(self):
        """실제 API 호출 로직"""
        try:
            headers = {"xc-token": self.api_token}
            url = f"{self.base_url}/tables/{self.table_id}/records"
            
            params = {
                "limit": 1000,
                "sort": "Id"
            }

            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('list', [])
                
                # UI 업데이트는 메인 스레드에서
                self.window.after(0, self._update_tree, records)
            else:
                error_msg = f"조회 실패: {response.status_code}"
                self.window.after(0, lambda: messagebox.showerror("오류", error_msg))
                self.window.after(0, lambda: self.status_label.config(text=error_msg, foreground="red"))

        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            self.window.after(0, lambda: messagebox.showerror("오류", error_msg))
            self.window.after(0, lambda: self.status_label.config(text="오류 발생", foreground="red"))

    def _update_tree(self, records):
        """Treeview 데이터 갱신"""
        # 기존 데이터 삭제
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 새 데이터 추가
        columns = list(self.columns_config.keys())
        
        for record in records:
            values = []
            for col in columns:
                val = record.get(col, '')
                values.append(str(val) if val is not None else '')
            self.tree.insert('', 'end', values=values)

        self.status_label.config(text=f"총 {len(records)}건 조회 완료", foreground="green")

# --- 사용 예시 ---
if __name__ == "__main__":
    # 테스트용 메인 창
    root = tk.Tk()
    root.title("메인 프로그램")
    root.geometry("300x200")

    def open_viewer():
        # 실제 사용 시에는 본인의 설정값으로 변경하세요
        API_TOKEN = "YOUR_NOCODB_API_TOKEN"
        BASE_URL = "http://YOUR_SERVER_IP:8080/api/v2"
        TABLE_ID = "YOUR_TABLE_ID"
        
        viewer = NocoDBViewer(root, API_TOKEN, BASE_URL, TABLE_ID)
        
        # 필요하다면 컬럼 설정을 여기서 동적으로 변경 가능
        viewer.columns_config = {
            'Id': 50,
            'Title': 150,
            'Status': 80
        }
        
        viewer.open()

    ttk.Button(root, text="NocoDB 뷰어 열기", command=open_viewer).pack(expand=True)
    
    root.mainloop()
