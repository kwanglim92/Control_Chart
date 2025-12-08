"""
SQLite Database Management for Control Chart App
Normalized Schema: Equipments (Master) + Measurements (Transaction)
"""
import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "control_chart.db"

def init_db():
    """Initialize the database with normalized tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Equipments Table (Master Data)
    # 장비의 고유 스펙을 관리합니다.
    # SID Number를 Primary Key(또는 Unique Key)로 사용합니다.
    c.execute('''
        CREATE TABLE IF NOT EXISTS equipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid TEXT UNIQUE,             -- SID Number (고유 식별자)
            equipment_name TEXT,         -- 장비명 (고객사명 등)
            date TEXT,                   -- 종료일 (생산 완료일)
            ri TEXT,                     -- R/I 구분
            model TEXT,                  -- Model
            xy_scanner TEXT,             -- XY Scanner
            head_type TEXT,              -- Head Type
            mod_vit TEXT,                -- MOD/VIT
            sliding_stage TEXT,          -- Sliding Stage
            sample_chuck TEXT,           -- Sample Chuck
            ae TEXT,                     -- AE
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Measurements Table (Transaction Data)
    # 실제 측정값을 관리하며, equipments 테이블을 참조합니다.
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER,        -- FK to equipments.id
            check_item TEXT,             -- 측정 항목
            value REAL,                  -- 측정 값
            FOREIGN KEY (equipment_id) REFERENCES equipments (id)
        )
    ''')

    # 3. Specs Table (Standards)
    # 모델별/항목별 관리 기준 (LSL, USL, Target)
    c.execute('''
        CREATE TABLE IF NOT EXISTS specs (
            model TEXT,
            check_item TEXT,
            lsl REAL,
            usl REAL,
            target REAL,
            PRIMARY KEY (model, check_item)
        )
    ''')
    
    conn.commit()
    conn.close()

def recreate_tables():
    """Drop and recreate tables (Force schema update)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS measurements")
    c.execute("DROP TABLE IF EXISTS equipments")
    c.execute("DROP TABLE IF EXISTS specs")
    conn.commit()
    conn.close()
    init_db()

def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_FILE)

def sync_specs_from_dataframe(df: pd.DataFrame):
    """
    Sync specs from DataFrame to SQLite.
    Expected columns: Model, Check Item, LSL, USL, Target
    """
    if df.empty:
        return
        
    conn = get_connection()
    c = conn.cursor()
    
    # Clear existing specs (Full Replace strategy for specs too)
    c.execute("DELETE FROM specs")
    
    # Column mapping
    col_map = {
        'Model': 'model',
        'Check Item': 'check_item',
        'LSL': 'lsl',
        'USL': 'usl',
        'Target': 'target'
    }
    
    df_db = df.rename(columns=col_map)
    
    for _, row in df_db.iterrows():
        if pd.isna(row.get('model')) or pd.isna(row.get('check_item')):
            continue
            
        c.execute('''
            INSERT OR REPLACE INTO specs (model, check_item, lsl, usl, target)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            row.get('model'), 
            row.get('check_item'), 
            row.get('lsl') if pd.notna(row.get('lsl')) else None,
            row.get('usl') if pd.notna(row.get('usl')) else None,
            row.get('target') if pd.notna(row.get('target')) else None
        ))
        
    conn.commit()
    conn.close()

def get_spec_for_item(model: str, check_item: str) -> Dict[str, Optional[float]]:
    """Get spec limits for a specific model and check item."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT lsl, usl, target FROM specs WHERE model = ? AND check_item = ?", (model, check_item))
    res = c.fetchone()
    conn.close()
    
    if res:
        return {'lsl': res[0], 'usl': res[1], 'target': res[2]}
    return {'lsl': None, 'usl': None, 'target': None}


def sync_relational_data(df_equip: pd.DataFrame, df_meas: pd.DataFrame, df_specs: pd.DataFrame = None) -> Dict[str, int]:
    """
    Sync data from 3 relational sheets (Equipments, Measurements, Specs).
    """
    recreate_tables()
    conn = get_connection()
    c = conn.cursor()
    
    added_equipments = 0
    added_measurements = 0
    
    # 1. Sync Specs
    if df_specs is not None and not df_specs.empty:
        # Inline Specs Sync
        col_map_specs = {'Model': 'model', 'Check Item': 'check_item', 'LSL': 'lsl', 'USL': 'usl', 'Target': 'target'}
        df_s = df_specs.rename(columns=col_map_specs)
        for _, row in df_s.iterrows():
            if pd.isna(row.get('model')) or pd.isna(row.get('check_item')): continue
            c.execute('''
                INSERT OR REPLACE INTO specs (model, check_item, lsl, usl, target)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                row.get('model'), row.get('check_item'), 
                row.get('lsl') if pd.notna(row.get('lsl')) else None,
                row.get('usl') if pd.notna(row.get('usl')) else None,
                row.get('target') if pd.notna(row.get('target')) else None
            ))

    # 2. Sync Equipments
    # Expected columns: SID, 장비명, 종료일, R/I, Model, ...
    col_map_equip = {
        'SID': 'sid', '장비명': 'equipment_name', '종료일': 'date', 'R/I': 'ri', 'Model': 'model',
        'XY Scanner': 'xy_scanner', 'Head Type': 'head_type', 'MOD/VIT': 'mod_vit',
        'Sliding Stage': 'sliding_stage', 'Sample Chuck': 'sample_chuck', 'AE': 'ae'
    }
    df_e = df_equip.rename(columns=col_map_equip)
    
    # Ensure date is string
    if 'date' in df_e.columns:
        df_e['date'] = df_e['date'].astype(str)
        
    # Map SID -> ID for measurements linking
    sid_to_id = {}
    
    for _, row in df_e.iterrows():
        # If SID is missing, use Equipment Name as fallback? Or skip?
        sid = row.get('sid')
        if pd.isna(sid) or str(sid).strip() == '':
            # Fallback: Use equipment_name if available
            if pd.notna(row.get('equipment_name')):
                sid = row.get('equipment_name')
            else:
                continue # Skip if no identifier
        
        # Insert Equipment
        cols = ['sid', 'equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
        vals = [row.get(col) for col in cols]
        
        placeholders = ', '.join(['?'] * len(cols))
        cols_str = ', '.join(cols)
        
        try:
            c.execute(f"INSERT INTO equipments ({cols_str}) VALUES ({placeholders})", vals)
            equip_id = c.lastrowid
            sid_to_id[str(sid)] = equip_id
            added_equipments += 1
        except sqlite3.IntegrityError:
            # Duplicate SID? Skip or Update?
            print(f"Duplicate SID skipped: {sid}")
            pass

    # 3. Sync Measurements
    # Expected columns: SID, Check Items, Value. (Optional: 장비명 for fallback)
    col_map_meas = {'SID': 'sid', '장비명': 'equipment_name', 'Check Items': 'check_item', 'Value': 'value'}
    df_m = df_meas.rename(columns=col_map_meas)
    
    for _, row in df_m.iterrows():
        sid = row.get('sid')
        
        # Fallback: If SID is empty, try using equipment_name
        if pd.isna(sid) or str(sid).strip() == '':
            if pd.notna(row.get('equipment_name')):
                sid = row.get('equipment_name')
            else:
                continue # Skip if no identifier
        
        equip_id = sid_to_id.get(str(sid))
        
        if equip_id:
            if pd.notna(row.get('check_item')) and pd.notna(row.get('value')):
                c.execute('''
                    INSERT INTO measurements (equipment_id, check_item, value)
                    VALUES (?, ?, ?)
                ''', (equip_id, row['check_item'], row['value']))
                added_measurements += 1
                
    conn.commit()
    conn.close()
    
    return {'equipments': added_equipments, 'measurements': added_measurements}


def import_data_from_df(df: pd.DataFrame, replace: bool = False) -> Dict[str, int]:
    """
    Import data from DataFrame to SQLite with normalized structure.
    Returns count of equipments and measurements added.
    """
    if df.empty:
        return {'equipments': 0, 'measurements': 0}
        
    if replace:
        recreate_tables()
        
    conn = get_connection()
    c = conn.cursor()
    
    # Column mapping
    col_map = {
        '종료일': 'date',
        '장비명': 'equipment_name',
        'R/I': 'ri',
        'Model': 'model',
        'XY Scanner': 'xy_scanner',
        'Head Type': 'head_type',
        'MOD/VIT': 'mod_vit',
        'Sliding Stage': 'sliding_stage',
        'Sample Chuck': 'sample_chuck',
        'AE': 'ae',
        'Check Items': 'check_item',
        'Value': 'value'
    }
    
    df_db = df.rename(columns=col_map)
    
    # Ensure date is string
    if 'date' in df_db.columns:
        df_db['date'] = df_db['date'].astype(str)
        
    added_equipments = 0
    added_measurements = 0
    
    # Process row by row (Not the fastest, but safest for normalization logic)
    # For bulk performance, we could optimize this later using set operations.
    
    # 1. Extract unique equipments
    equip_cols = ['equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                  'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
    
    # 장비명 기준으로 중복 제거 (가장 최근 데이터 기준 or 첫번째 기준)
    # 여기서는 장비명이 같으면 같은 장비로 간주하고 스펙을 업데이트(덮어쓰기) 하거나 무시합니다.
    # INSERT OR IGNORE / INSERT OR REPLACE
    
    for _, row in df_db.iterrows():
        # A. Insert or Get Equipment
        # 장비명이 없으면 건너뜀
        if pd.isna(row.get('equipment_name')):
            continue
            
        equip_data = [row.get(col) for col in equip_cols]
        
        # Check if equipment exists
        c.execute("SELECT id FROM equipments WHERE equipment_name = ?", (row['equipment_name'],))
        res = c.fetchone()
        
        if res:
            equip_id = res[0]
            # Optional: Update specs if changed? For now, keep existing.
        else:
            placeholders = ', '.join(['?'] * len(equip_cols))
            cols_str = ', '.join(equip_cols)
            c.execute(f"INSERT INTO equipments ({cols_str}) VALUES ({placeholders})", equip_data)
            equip_id = c.lastrowid
            added_equipments += 1
            
        # B. Insert Measurement
        if pd.notna(row.get('check_item')) and pd.notna(row.get('value')):
            c.execute('''
                INSERT INTO measurements (equipment_id, check_item, value)
                VALUES (?, ?, ?)
            ''', (equip_id, row['check_item'], row['value']))
            added_measurements += 1
            
    conn.commit()
    conn.close()
    
    return {'equipments': added_equipments, 'measurements': added_measurements}

def sync_from_dataframe(df: pd.DataFrame) -> Dict[str, int]:
    """Wrapper for import_data_from_df to be used by GSheets sync. Defaults to replace=True."""
    return import_data_from_df(df, replace=True)

def insert_single_record(data: Dict[str, Any]):
    """Insert a single record (Equipment + Measurement) from web form."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Handle Equipment
    equip_cols = ['equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                  'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
    
    # Check existence
    c.execute("SELECT id FROM equipments WHERE equipment_name = ?", (data['equipment_name'],))
    res = c.fetchone()
    
    if res:
        equip_id = res[0]
    else:
        # Prepare data for insertion (fill missing with None)
        vals = [data.get(col) for col in equip_cols]
        placeholders = ', '.join(['?'] * len(equip_cols))
        cols_str = ', '.join(equip_cols)
        c.execute(f"INSERT INTO equipments ({cols_str}) VALUES ({placeholders})", vals)
        equip_id = c.lastrowid
        
    # 2. Handle Measurement
    c.execute('''
        INSERT INTO measurements (equipment_id, check_item, value)
        VALUES (?, ?, ?)
    ''', (equip_id, data['check_item'], data['value']))
    
    conn.commit()
    conn.close()

def get_unique_values(column: str) -> List[str]:
    """Get unique values for a column (from equipments or measurements)."""
    conn = get_connection()
    c = conn.cursor()
    
    # Determine which table the column belongs to
    equip_cols = ['equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                  'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae']
    
    table = 'equipments' if column in equip_cols else 'measurements'
    
    try:
        c.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}")
        results = [row[0] for row in c.fetchall()]
    except sqlite3.OperationalError:
        results = []
        
    conn.close()
    return results

def fetch_filtered_data(filters: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Fetch data by JOINing equipments and measurements tables.
    """
    conn = get_connection()
    
    # Base Query: JOIN equipments and measurements
    query = '''
        SELECT 
            e.date, e.equipment_name, e.ri, e.model, e.xy_scanner, 
            e.head_type, e.mod_vit, e.sliding_stage, e.sample_chuck, e.ae,
            m.check_item, m.value
        FROM measurements m
        JOIN equipments e ON m.equipment_id = e.id
        WHERE 1=1
    '''
    params = []
    
    # Map filter keys to DB columns
    # filters keys are like 'model', 'check_item', 'date_range'
    
    for col, values in filters.items():
        if not values:
            continue
            
        if col == 'date_range':
            start, end = values
            query += " AND e.date >= ? AND e.date <= ?"
            params.extend([str(start), str(end)])
        elif col == 'check_item':
            # check_item is in measurements table
            placeholders = ', '.join(['?'] * len(values))
            query += f" AND m.check_item IN ({placeholders})"
            params.extend(values)
        else:
            # All other filters are likely in equipments table
            # e.g. model -> e.model
            placeholders = ', '.join(['?'] * len(values))
            query += f" AND e.{col} IN ({placeholders})"
            params.extend(values)
            
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # Restore original column names for compatibility
    rev_col_map = {
        'date': '종료일',
        'value': 'Value',
        'check_item': 'Check Items',
        'equipment_name': '장비명',
        'ri': 'R/I',
        'model': 'Model',
        'xy_scanner': 'XY Scanner',
        'head_type': 'Head Type',
        'mod_vit': 'MOD/VIT',
        'sliding_stage': 'Sliding Stage',
        'sample_chuck': 'Sample Chuck',
        'ae': 'AE'
    }
    
    df = df.rename(columns=rev_col_map)
    
    # Type conversion
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    if '종료일' in df.columns:
        df['종료일'] = pd.to_datetime(df['종료일'])
        
    return df

def clear_all_data():
    """Clear all data."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM equipments")
    conn.commit()
    conn.close()

def get_equipment_stats() -> Dict[str, Any]:
    """Get equipment statistics for dashboard."""
    conn = get_connection()
    c = conn.cursor()
    
    # Total counts
    c.execute("SELECT COUNT(*) FROM equipments")
    equip_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM measurements")
    meas_count = c.fetchone()[0]
    
    # Breakdown by Model and R/I
    query = '''
        SELECT model, ri, COUNT(*) as count
        FROM equipments
        GROUP BY model, ri
        ORDER BY model, ri
    '''
    df_stats = pd.read_sql_query(query, conn)
    
    conn.close()
    
    return {
        'total_equipments': equip_count,
        'total_measurements': meas_count,
        'breakdown': df_stats
    }

def get_all_equipments() -> pd.DataFrame:
    """Get all equipment details for explorer."""
    conn = get_connection()
    # Fetch all columns from equipments table
    query = "SELECT * FROM equipments"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Date processing
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df['Year'] = df['date'].dt.year
        df['Month'] = df['date'].dt.month
        df['Quarter'] = df['date'].dt.quarter.astype(str) + 'Q'
        df['YearQuarter'] = df['date'].dt.strftime('%Y-') + df['Quarter']
        df['YearMonth'] = df['date'].dt.strftime('%Y-%m')
        
    return df


