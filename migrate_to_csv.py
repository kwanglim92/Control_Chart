import sqlite3
import pandas as pd
import os

def migrate():
    db_path = 'data/control_chart.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} 파일을 찾을 수 없습니다.")
        return

    conn = sqlite3.connect(db_path)
    print(f"Connected to {db_path}")

    # 1. 엔지니어 목록 추출 (Engineers.csv)
    print("Extracting engineers...")
    equip_df = pd.read_sql_query('SELECT me3_engineer, qc_engineer FROM equipments', conn)
    all_engineers = pd.concat([equip_df['me3_engineer'], equip_df['qc_engineer']]).unique()
    
    eng_df = pd.DataFrame({
        'name': [e for e in all_engineers if e and str(e).strip()],
        'department': 'Unknown',
        'role': 'Engineer',
        'active': True
    })
    eng_df.to_csv('engineers.csv', index=False, encoding='utf-8-sig')
    print(f"Saved engineers.csv ({len(eng_df)} records)")

    # 2. 장비 데이터 추출 (Equipments.csv)
    print("Extracting equipments...")
    equip_full_df = pd.read_sql_query('SELECT * FROM equipments', conn)
    # NocoDB 필드명에 맞게 매핑
    equip_full_df = equip_full_df.rename(columns={
        'me3_engineer': 'production_engineer',
        'status': 'approval_status'
    })
    # registered_at 필드용 created_at (있다면)
    if 'uploaded_at' in equip_full_df.columns:
        equip_full_df = equip_full_df.rename(columns={'uploaded_at': 'registered_at'})
    
    equip_full_df.to_csv('equipments.csv', index=False, encoding='utf-8-sig')
    print(f"Saved equipments.csv ({len(equip_full_df)} records)")

    # 3. 측정 데이터 추출 (ChecklistRawData.csv)
    print("Extracting measurements...")
    meas_df = pd.read_sql_query('SELECT * FROM measurements', conn)
    # equipment 링크를 위해 sid를 equipment 필드로 매핑
    meas_df = meas_df.rename(columns={'sid': 'equipment'})
    
    # 기본 trend 값 설정 (SQLite에 없으므로 일단 False)
    meas_df['trend'] = False
    
    meas_df.to_csv('checklist_raw_data.csv', index=False, encoding='utf-8-sig')
    print(f"Saved checklist_raw_data.csv ({len(meas_df)} records)")

    conn.close()
    print("\nMigration preparation complete! Please import these CSV files into NocoDB.")

if __name__ == "__main__":
    migrate()
