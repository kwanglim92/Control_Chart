"""
SQLite Database Management for Control Chart App
Normalized Schema: Equipments (Master) + Measurements (Transaction)
"""
import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "data/control_chart.db"

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
            end_user TEXT,               -- End User (고객사)
            mfg_engineer TEXT,           -- Manufacturing Engineer
            qc_engineer TEXT,            -- Production QC Engineer
            reference_doc TEXT,          -- Reference Document (체크리스트 버전)
            status TEXT DEFAULT 'pending', -- pending / approved
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Measurements Table (Transaction Data)
    # 실제 측정값을 관리하며, equipments 테이블을 참조합니다.
    c.execute('''
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER,        -- FK to equipments.id
            check_item TEXT,             -- 측정 항목 (legacy)
            check_items TEXT,            -- 측정 항목 (new)
            value REAL,                  -- 측정 값
            sid TEXT,                    -- SID Number (denormalized for query)
            equipment_name TEXT,         -- Equipment Name (denormalized)
            status TEXT DEFAULT 'pending', -- pending / approved
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

    # 4. Approve History Table (Approval/Rejection tracking)
    # 모든 승인/반려 이력을 기록합니다
    c.execute('''
        CREATE TABLE IF NOT EXISTS approval_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid TEXT NOT NULL,                     -- SID Number
            equipment_id INTEGER,                  -- FK to equipments.id (nullable)
            action TEXT NOT NULL,                  -- 'approved', 'rejected', 'resubmitted'
            admin_name TEXT,                       -- 관리자 이름
            reason TEXT,                           -- 반려/승인 사유
            previous_status TEXT,                  -- 이전 상태
            new_status TEXT,                       -- 새 상태
            modification_count INTEGER DEFAULT 0,  -- 수정 항목 개수
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT                          -- JSON: 추가 정보
        )
    ''')

    # 5. Pending Measurements Table (Staging Area)
    # 업로드된 원본 데이터를 검증 전까지 그대로 보관하는 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sid TEXT NOT NULL,
            equipment_name TEXT,
            category TEXT,
            check_items TEXT,
            min_value REAL,
            criteria REAL,
            max_value REAL,
            value REAL,
            unit TEXT,
            pass_fail TEXT,
            trend TEXT,
            remark TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Migration: Add new columns if they don't exist (for backward compatibility)
    
    # Equipments table migrations
    try:
        c.execute("ALTER TABLE equipments ADD COLUMN end_user TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        c.execute("ALTER TABLE equipments ADD COLUMN mfg_engineer TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE equipments ADD COLUMN qc_engineer TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE equipments ADD COLUMN reference_doc TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Measurements table migrations
    try:
        c.execute("ALTER TABLE measurements ADD COLUMN sid TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE measurements ADD COLUMN equipment_name TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE measurements ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE measurements ADD COLUMN check_items TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Data migration: Copy check_item to check_items if needed
    try:
        c.execute("""
            UPDATE measurements 
            SET check_items = check_item 
            WHERE check_items IS NULL AND check_item IS NOT NULL
        """)
    except sqlite3.OperationalError:
        pass
    # pending_measurements table migrations
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN module TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add TEXT columns to preserve original data format (e.g. "0x6e31041e" stays as text)
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN min_text TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN criteria_text TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN max_text TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN value_text TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE pending_measurements ADD COLUMN value_text TEXT")
    except sqlite3.OperationalError:
        pass
        
    # Equipment Table Migrations (Additional Info)
    new_cols = ['end_user', 'mfg_engineer', 'qc_engineer', 'reference_doc']
    for col in new_cols:
        try:
            c.execute(f"ALTER TABLE equipments ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    
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
        'Sliding Stage': 'sliding_stage', 'Sample Chuck': 'sample_chuck', 'AE': 'ae',
        'End User': 'end_user', 'Mfg Engineer': 'mfg_engineer', 'QC Engineer': 'qc_engineer', 'Reference Doc': 'reference_doc'
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
        
        # Insert Equipment (Default status='pending' for new uploads via this function, 
        # but if this function is used for bulk import, maybe we want 'approved'?)
        # Let's assume bulk import via this function is 'approved' for now or 'pending'.
        # For now, let's default to 'approved' if it's a migration, but 'pending' if it's user upload.
        # Actually, this function 'sync_relational_data' seems to be legacy or bulk import.
        # Let's set default to 'approved' for bulk sync to maintain backward compatibility if used.
        
        cols = ['sid', 'equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                'end_user', 'mfg_engineer', 'qc_engineer', 'reference_doc', 'status']
        
        # Prepare values
        vals = [row.get(col) for col in cols[:-1]] # All except status
        vals.append('approved') # Default status for bulk sync
        
        placeholders = ', '.join(['?'] * len(cols))
        cols_str = ', '.join(cols)
        
        try:
            c.execute(f"INSERT INTO equipments ({cols_str}) VALUES ({placeholders})", vals)
            equip_id = c.lastrowid
            sid_to_id[str(sid)] = equip_id
            added_equipments += 1
        except sqlite3.IntegrityError:
            # Duplicate SID? Skip or Update?
            # For now, skip
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


def insert_equipment_from_excel(df_equip: pd.DataFrame, df_meas: pd.DataFrame) -> Dict[str, int]:
    """
    Insert data from uploaded Excel file with status='pending'.
    """
    conn = get_connection()
    c = conn.cursor()
    
    added_equipments = 0
    added_measurements = 0
    
    # Column mapping (Same as sync_relational_data)
    col_map_equip = {
        'SID': 'sid', '장비명': 'equipment_name', '종료일': 'date', 'R/I': 'ri', 'Model': 'model',
        'XY Scanner': 'xy_scanner', 'Head Type': 'head_type', 'MOD/VIT': 'mod_vit',
        'Sliding Stage': 'sliding_stage', 'Sample Chuck': 'sample_chuck', 'AE': 'ae',
        'End User': 'end_user', 'Mfg Engineer': 'mfg_engineer', 'QC Engineer': 'qc_engineer', 'Reference Doc': 'reference_doc'
    }
    df_e = df_equip.rename(columns=col_map_equip)
    if 'date' in df_e.columns:
        df_e['date'] = df_e['date'].astype(str)
        
    sid_to_id = {}
    sid_to_name = {}  # SID → Equipment Name mapping
    
    for _, row in df_e.iterrows():
        sid = row.get('sid')
        if pd.isna(sid) or str(sid).strip() == '':
            if pd.notna(row.get('equipment_name')):
                sid = row.get('equipment_name')
            else:
                continue

        cols = ['sid', 'equipment_name', 'date', 'ri', 'model', 'xy_scanner', 
                'head_type', 'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 
                'end_user', 'mfg_engineer', 'qc_engineer', 'reference_doc', 'status']
        
        vals = [row.get(col) for col in cols[:-1]]
        vals.append('pending') # Set status to pending
        
        placeholders = ', '.join(['?'] * len(cols))
        cols_str = ', '.join(cols)
        
        try:
            c.execute(f"INSERT INTO equipments ({cols_str}) VALUES ({placeholders})", vals)
            equip_id = c.lastrowid
            sid_to_id[str(sid)] = equip_id
            sid_to_name[str(sid)] = row.get('equipment_name', '')  # Store equipment name
            added_equipments += 1
        except sqlite3.IntegrityError:
            # If SID exists, we might want to update or skip. 
            # For upload, maybe reject if exists? Or allow update?
            # Let's skip for now to avoid overwriting approved data easily.
            print(f"Duplicate SID skipped during upload: {sid}")
            pass

    # Measurements
    col_map_meas = {'SID': 'sid', '장비명': 'equipment_name', 'Check Items': 'check_item', 'Value': 'value'}
    df_m = df_meas.rename(columns=col_map_meas)
    
    for _, row in df_m.iterrows():
        sid = row.get('sid')
        if pd.isna(sid) or str(sid).strip() == '':
            if pd.notna(row.get('equipment_name')):
                sid = row.get('equipment_name')
            else:
                continue
        
        equip_id = sid_to_id.get(str(sid))
        if equip_id:
            if pd.notna(row.get('check_item')) and pd.notna(row.get('value')):
                equipment_name = sid_to_name.get(str(sid), '')
                check_item_value = row['check_item']
                
                # Insert with all required columns: sid, equipment_name, check_items, status
                c.execute('''
                    INSERT INTO measurements 
                    (equipment_id, check_item, check_items, value, sid, equipment_name, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (equip_id, check_item_value, check_item_value, row['value'], 
                      str(sid), equipment_name, 'pending'))
                added_measurements += 1
                
    conn.commit()
    conn.close()
    
    # Insert into pending_measurements (Staging)
    # Group by SID to handle multiple equipments in one upload
    for sid, equip_id in sid_to_id.items():
        # Filter measurements for this SID
        # Note: df_meas has 'SID' column
        equip_meas = df_meas[df_meas['SID'].astype(str) == str(sid)]
        if not equip_meas.empty:
            equipment_name = sid_to_name.get(str(sid), '')
            insert_pending_measurements(equip_meas, str(sid), equipment_name)
    
    return {'equipments': added_equipments, 'measurements': added_measurements}


def insert_pending_measurements(df_meas: pd.DataFrame, sid: str, equipment_name: str):
    """
    Insert raw measurement data into pending_measurements table.
    df_meas should contain columns from the upload preview.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Clean up existing pending measurements for this SID to prevent duplicates
    # (e.g. if user re-uploads the same file)
    c.execute("DELETE FROM pending_measurements WHERE sid = ? AND status = 'pending'", (sid,))
    
    for _, row in df_meas.iterrows():
        # Handle NaN values for numeric columns
        val = row.get('Measurement')
        if pd.isna(val): val = None
        
        # Convert to string for TEXT columns (preserves original format like "0x6e31041e")
        def to_text(value):
            if pd.isna(value):
                return ''
            return str(value)
        
        c.execute("""
            INSERT INTO pending_measurements 
            (sid, equipment_name, module, category, check_items, 
             min_value, criteria, max_value, value, 
             min_text, criteria_text, max_text, value_text,
             unit, pass_fail, trend, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, 
            equipment_name,
            row.get('Module'),
            row.get('Category'), 
            row.get('Check Items'), 
            row.get('Min'),         # Numeric (for analysis)
            row.get('Criteria'),
            row.get('Max'), 
            val, 
            to_text(row.get('Min')),      # Text (for display)
            to_text(row.get('Criteria')),
            to_text(row.get('Max')),
            to_text(row.get('Measurement')),
            row.get('Unit'), 
            row.get('PASS/FAIL'),
            row.get('Trend'), 
            row.get('Remark')
        ))
    
    conn.commit()
    conn.close()

def get_pending_measurements(sid: str) -> pd.DataFrame:
    """
    Get measurements for a specific SID with full columns.
    Returns only rows where Trend is present (for Control Chart analysis).
    Includes both pending and approved data.
    """
    conn = get_connection()
    query = """
        SELECT 
            id, sid, equipment_name, category as Category, check_items as "Check Items", 
            min_value as Min, criteria as Criteria, max_value as Max, 
            value as Measurement, unit as Unit, pass_fail as "PASS/FAIL", 
            trend as Trend, remark as Remark, status
        FROM pending_measurements
        WHERE sid = ? AND status IN ('pending', 'approved')
          AND trend IS NOT NULL AND trend != ''
          AND value IS NOT NULL
    """
    df = pd.read_sql_query(query, conn, params=(sid,))
    conn.close()
    return df


def get_full_measurements(sid: str) -> pd.DataFrame:
    """
    Get ALL detailed measurements from pending_measurements table for a SID,
    regardless of status (pending/approved/rejected).
    Used for the Dashboard 'Full Data View'.
    Returns columns in Excel original order (matching upload preview).
    """
    conn = get_connection()
    query = """
        SELECT 
            module as Module,
            check_items as "Check Items", 
            min_text as Min, 
            criteria_text as Criteria, 
            max_text as Max, 
            value_text as Measurement, 
            unit as Unit, 
            pass_fail as "PASS/FAIL",
            category as Category, 
            trend as Trend, 
            remark as Remark
        FROM pending_measurements
        WHERE sid = ?
        ORDER BY id ASC
    """
    df = pd.read_sql_query(query, conn, params=(sid,))
    conn.close()
    
    # Replace None with empty string for better display
    df = df.fillna('')
    
    # Add row number column at the beginning
    df.insert(0, '#', range(1, len(df) + 1))
    
    return df


def get_equipment_status(sid: str) -> str:
    """
    Check the current status of an equipment by SID.
    Returns: 'approved', 'rejected', 'pending', or None (if not exists)
    """
    conn = get_connection()
    c = conn.cursor()
    # SID 중복이 있을 수 있으니 최신 것 하나만 가져옴 (ID 역순)
    c.execute("SELECT status FROM equipments WHERE sid = ? ORDER BY id DESC LIMIT 1", (sid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_all_equipments(filters: dict = None) -> pd.DataFrame:
    """
    Get all equipments with optional filtering.
    filters: {
        'status': ['approved', 'pending', ...],
        'model': ['NX-Wafer', ...],
        'date_range': [start_date, end_date],
        'search': 'keyword'
    }
    """
    conn = get_connection()
    query = "SELECT * FROM equipments WHERE 1=1"
    params = []
    
    if filters:
        if 'status' in filters and filters['status']:
            placeholders = ','.join(['?'] * len(filters['status']))
            query += f" AND status IN ({placeholders})"
            params.extend(filters['status'])
            
        if 'model' in filters and filters['model']:
            placeholders = ','.join(['?'] * len(filters['model']))
            query += f" AND model IN ({placeholders})"
            params.extend(filters['model'])
            
        if 'date_range' in filters and filters['date_range'] and len(filters['date_range']) == 2:
            query += " AND date BETWEEN ? AND ?"
            params.extend(filters['date_range'])
            
        if 'search' in filters and filters['search']:
            keyword = f"%{filters['search']}%"
            query += " AND (sid LIKE ? OR equipment_name LIKE ?)"
            params.extend([keyword, keyword])
            
    query += " ORDER BY id DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    # 날짜 컬럼 변환
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
    return df


def get_pending_equipments() -> pd.DataFrame:
    """Get all equipments with status='pending'."""
    conn = get_connection()
    query = "SELECT * FROM equipments WHERE status = 'pending' ORDER BY uploaded_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def approve_equipment(equip_id: int):
    """
    Approve an equipment by ID.
    Also syncs denormalized columns in measurements table.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Get equipment info for denormalized sync
    c.execute("SELECT sid, equipment_name FROM equipments WHERE id = ?", (equip_id,))
    equip = c.fetchone()
    sid, equip_name = equip if equip else (None, None)
    
    # 2. Update equipment status
    c.execute("UPDATE equipments SET status = 'approved' WHERE id = ?", (equip_id,))
    
    # 3. Sync denormalized columns in measurements table
    c.execute("""
        UPDATE measurements 
        SET status = 'approved',
            sid = ?,
            equipment_name = ?
        WHERE equipment_id = ?
    """, (sid, equip_name, equip_id))
    
    conn.commit()
    conn.close()

def reject_equipment(equip_id: int, reason: str = None, admin_name: str = None):
    """
    Reject an equipment (change status to 'rejected' instead of deleting).
    
    Args:
        equip_id: Equipment ID
        reason: Rejection reason
        admin_name: Admin who rejected
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Get SID first to update pending_measurements
    c.execute("SELECT sid FROM equipments WHERE id = ?", (equip_id,))
    row = c.fetchone()
    if row:
        sid = row[0]
        # Update pending_measurements
        c.execute("UPDATE pending_measurements SET status = 'rejected' WHERE sid = ? AND status = 'pending'", (sid,))
    
    # Change status to rejected instead of deleting
    c.execute("UPDATE equipments SET status = 'rejected' WHERE id = ?", (equip_id,))
    c.execute("UPDATE measurements SET status = 'rejected' WHERE equipment_id = ?", (equip_id,))
    conn.commit()
    conn.close()

def delete_equipment(equip_id: int):
    """Delete an equipment and its measurements by ID (legacy function)."""
    conn = get_connection()
    c = conn.cursor()
    # Delete measurements first (Cascade logic if not set in DB)
    c.execute("DELETE FROM measurements WHERE equipment_id = ?",(equip_id,))
    c.execute("DELETE FROM equipments WHERE id = ?", (equip_id,))
    conn.commit()
    conn.close()

def log_approval_history(sid: str, equipment_id: int = None, action: str = None, 
                         admin_name: str = None, reason: str = None, 
                         previous_status: str = None, new_status: str = None,
                         modification_count: int = 0, metadata: str = None):
    """
    Log approval/rejection history.
    
    Args:
        sid: SID number
        equipment_id: Equipment ID (nullable)
        action: 'approved', 'rejected', 'resubmitted'
        admin_name: Admin name
        reason: Approval/rejection reason
        previous_status: Previous status
        new_status: New status
        modification_count: Number of modifications made
        metadata: JSON string with additional info
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO approval_history 
        (sid, equipment_id, action, admin_name, reason, previous_status, new_status, modification_count, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sid, equipment_id, action, admin_name, reason, previous_status, new_status, modification_count, metadata))
    conn.commit()
    conn.close()

def check_previous_rejections(sid: str) -> pd.DataFrame:
    """
    Check if this SID was rejected before.
    
    Args:
        sid: SID number
    
    Returns:
        DataFrame with previous rejection history
    """
    conn = get_connection()
    query = """
        SELECT 
            action,
            admin_name,
            reason,
            timestamp,
            modification_count
        FROM approval_history
        WHERE sid = ? AND action = 'rejected'
        ORDER BY timestamp DESC
        LIMIT 5
    """
    df = pd.read_sql_query(query, conn, params=(sid,))
    conn.close()
    return df


def is_resubmitted(sid: str) -> bool:
    """Check if the latest action for this SID was 'resubmitted'."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT action FROM approval_history WHERE sid = ? ORDER BY timestamp DESC LIMIT 1", (sid,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 'resubmitted'


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
    # Only fetch approved equipments
    query = '''
        SELECT 
            e.date, e.equipment_name, e.ri, e.model, e.xy_scanner, 
            e.head_type, e.mod_vit, e.sliding_stage, e.sample_chuck, e.ae,
            m.check_item, m.value
        FROM measurements m
        JOIN equipments e ON m.equipment_id = e.id
        WHERE e.status = 'approved'
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

def sync_denormalized_columns():
    """
    Phase 1: Sync denormalized columns in measurements table.
    Updates equipment_name, sid, and status based on equipments table.
    Returns count of updated rows.
    """
    conn = get_connection()
    c = conn.cursor()
    
    updated_counts = {
        'equipment_name': 0,
        'sid': 0,
        'status': 0
    }
    
    # 1. Sync equipment_name
    c.execute("""
        UPDATE measurements 
        SET equipment_name = (
            SELECT e.equipment_name 
            FROM equipments e 
            WHERE e.id = measurements.equipment_id
        )
        WHERE equipment_id IS NOT NULL
          AND (equipment_name IS NULL OR equipment_name = '')
    """)
    updated_counts['equipment_name'] = c.rowcount
    
    # 2. Sync sid
    c.execute("""
        UPDATE measurements 
        SET sid = (
            SELECT e.sid 
            FROM equipments e 
            WHERE e.id = measurements.equipment_id
        )
        WHERE equipment_id IS NOT NULL
          AND (sid IS NULL OR sid = '')
    """)
    updated_counts['sid'] = c.rowcount
    
    # 3. Sync status for approved equipments
    c.execute("""
        UPDATE measurements 
        SET status = 'approved'
        WHERE equipment_id IN (
            SELECT id FROM equipments WHERE status = 'approved'
        )
        AND status != 'approved'
    """)
    updated_counts['status'] = c.rowcount
    
    conn.commit()
    conn.close()
    
    return updated_counts

def get_migration_status():
    """
    Get current data consistency status.
    Returns counts of NULL values in denormalized columns.
    """
    conn = get_connection()
    
    # Count NULL equipment_name
    null_name = pd.read_sql_query("""
        SELECT COUNT(*) as cnt FROM measurements 
        WHERE equipment_name IS NULL AND equipment_id IS NOT NULL
    """, conn)['cnt'].iloc[0]
    
    # Count NULL sid
    null_sid = pd.read_sql_query("""
        SELECT COUNT(*) as cnt FROM measurements 
        WHERE sid IS NULL AND equipment_id IS NOT NULL
    """, conn)['cnt'].iloc[0]
    
    # Count mismatched status
    mismatched_status = pd.read_sql_query("""
        SELECT COUNT(*) as cnt FROM measurements m
        JOIN equipments e ON m.equipment_id = e.id
        WHERE e.status = 'approved' AND m.status != 'approved'
    """, conn)['cnt'].iloc[0]
    
    # Total measurements
    total = pd.read_sql_query("SELECT COUNT(*) as cnt FROM measurements", conn)['cnt'].iloc[0]
    
    conn.close()
    
    return {
        'total_measurements': total,
        'null_equipment_name': null_name,
        'null_sid': null_sid,
        'mismatched_status': mismatched_status
    }


def get_equipment_stats() -> Dict[str, Any]:
    """Get equipment statistics for dashboard."""
    conn = get_connection()
    c = conn.cursor()
    
    # Total counts (Approved only)
    c.execute("SELECT COUNT(*) FROM equipments WHERE status = 'approved'")
    equip_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM measurements")
    meas_count = c.fetchone()[0]
    
    # Breakdown by Model and R/I
    query = '''
        SELECT model, ri, COUNT(*) as count
        FROM equipments
        WHERE status = 'approved'
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




def get_measurements_by_sid(sid: str, status: str = 'approved') -> pd.DataFrame:
    """
    Get measurements by SID and status.
    
    Args:
        sid: SID number
        status: 'approved', 'pending', or 'all'
    
    Returns:
        DataFrame with measurements
    """
    conn = get_connection()
    
    # Use COALESCE to handle both check_item and check_items columns
    if status == 'all':
        query = """
            SELECT 
                id,
                equipment_id,
                COALESCE(check_items, check_item) as check_items,
                value,
                sid,
                equipment_name,
                status
            FROM measurements 
            WHERE sid = ?
        """
        df = pd.read_sql_query(query, conn, params=(sid,))
    else:
        query = """
            SELECT 
                id,
                equipment_id,
                COALESCE(check_items, check_item) as check_items,
                value,
                sid,
                equipment_name,
                status
            FROM measurements 
            WHERE sid = ? AND status = ?
        """
        df = pd.read_sql_query(query, conn, params=(sid, status))
    
    conn.close()
    return df


def get_equipment_count() -> int:
    """Get total number of equipments in the database."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM equipments")
        count = c.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0
    conn.close()
    return count


def update_equipment(equip_id: int, updates: Dict[str, Any]) -> bool:
    """
    Update specific fields of an equipment record.
    
    Args:
        equip_id: Equipment ID
        updates: Dictionary of column_name: new_value
    """
    if not updates:
        return False
        
    conn = get_connection()
    c = conn.cursor()
    
    # Filter out invalid columns to prevent SQL injection or errors
    valid_columns = [
        'sid', 'equipment_name', 'ri', 'model', 'xy_scanner', 'head_type', 
        'mod_vit', 'sliding_stage', 'sample_chuck', 'ae', 'date', 'status',
        'end_user', 'mfg_engineer', 'qc_engineer', 'reference_doc'
    ]
    
    clean_updates = {k: v for k, v in updates.items() if k in valid_columns}
    
    if not clean_updates:
        conn.close()
        return False
        
    set_clause = ", ".join([f"{col} = ?" for col in clean_updates.keys()])
    values = list(clean_updates.values())
    values.append(equip_id)
    
    try:
        c.execute(f"UPDATE equipments SET {set_clause} WHERE id = ?", values)
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error updating equipment: {e}")
        success = False
    finally:
        conn.close()
        
    return success
