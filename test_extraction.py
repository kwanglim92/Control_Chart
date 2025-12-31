import pandas as pd
from datetime import datetime

def extract_equipment_info_from_last_sheet(excel_file):
    """Last 시트에서 장비 기본 정보 자동 추출"""
    try:
        df = pd.read_excel(excel_file, sheet_name='Last', header=None)
        
        info = {}
        
        # Product Model (Row 21, Column 1)
        if len(df) > 21 and pd.notna(df.iloc[21, 1]):
            info['model'] = str(df.iloc[21, 1]).strip()
        
        # SID Number (Row 24, Column 1)
        if len(df) > 24 and pd.notna(df.iloc[24, 1]):
            info['sid'] = str(df.iloc[24, 1]).strip()
        
        # Reference Document (Row 27, Column 1)
        if len(df) > 27 and pd.notna(df.iloc[27, 1]):
            info['reference_doc'] = str(df.iloc[27, 1]).strip()
        
        # Date of Final Test (Row 30, Column 1)
        if len(df) > 30 and pd.notna(df.iloc[30, 1]):
            date_val = df.iloc[30, 1]
            if isinstance(date_val, datetime):
                info['date'] = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, pd.Timestamp):
                info['date'] = date_val.strftime('%Y-%m-%d')
            else:
                info['date'] = str(date_val)
        
        # End User (Row 33, Column 1)
        if len(df) > 33 and pd.notna(df.iloc[33, 1]):
            info['end_user'] = str(df.iloc[33, 1]).strip()
        
        # Manufacturing Engineer (Row 36, Column 1)
        if len(df) > 36 and pd.notna(df.iloc[36, 1]):
            info['mfg_engineer'] = str(df.iloc[36, 1]).strip()
        
        # Production QC Engineer (Row 39, Column 1)
        if len(df) > 39 and pd.notna(df.iloc[39, 1]):
            info['qc_engineer'] = str(df.iloc[39, 1]).strip()
        
        return info
        
    except Exception as e:
        print(f"오류: {str(e)}")
        return {}

# 테스트
result = extract_equipment_info_from_last_sheet('Industrial Check List v3.21.1.xlsx')
print("추출된 정보:")
for key, value in result.items():
    print(f"  {key}: {value}")
