import sys
sys.path.insert(0, './solver')
from db import _get_mysql_conn

conn = _get_mysql_conn()
try:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO vehicles (user_id, license_plate, name, max_weight_kg, max_length_cm, max_width_cm, max_height_cm, status, created_at, updated_at)
            VALUES 
            (1, '29C-12345', 'Xe tải 1 Tấn', 1000, 300, 160, 160, 'available', NOW(), NOW()),
            (1, '29C-54321', 'Xe tải 2.5 Tấn', 2500, 430, 190, 185, 'available', NOW(), NOW()),
            (1, '29C-99999', 'Xe tải 5 Tấn', 5000, 600, 220, 210, 'available', NOW(), NOW())
        """)
    conn.commit()
    print('Seeded 3 vehicles')
finally:
    conn.close()
