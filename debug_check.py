import sqlite3
import pandas as pd

conn = sqlite3.connect('data/control_chart.db')

print('=== Check Riken data ===')
df = pd.read_sql_query("SELECT COUNT(*) as cnt FROM measurements WHERE equipment_name = 'Riken'", conn)
print('Riken in measurements:', df['cnt'].iloc[0])

df2 = pd.read_sql_query("SELECT COUNT(*) as cnt FROM pending_measurements WHERE equipment_name = 'Riken'", conn)
print('Riken in pending_measurements:', df2['cnt'].iloc[0])

print()
print('=== All unique equipment_names in measurements ===')
df3 = pd.read_sql_query('SELECT DISTINCT equipment_name FROM measurements LIMIT 20', conn)
print(df3)

print()
print('=== Check by equipment_id ===')
equip = pd.read_sql_query("SELECT id, equipment_name, sid FROM equipments WHERE equipment_name = 'Riken'", conn)
print('Riken equipment info:')
print(equip)

if not equip.empty:
    equip_id = equip['id'].iloc[0]
    meas = pd.read_sql_query(f"SELECT COUNT(*) as cnt FROM measurements WHERE equipment_id = {equip_id}", conn)
    print(f'Measurements for equipment_id {equip_id}:', meas['cnt'].iloc[0])

conn.close()
