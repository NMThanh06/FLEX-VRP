import sys
sys.path.append('solver')
from db import get_orders, delete_order

orders = get_orders()
deleted_count = 0
for o in orders:
    qty = o.get('total_quantity', 0)
    lat = o.get('customer_lat')
    lon = o.get('customer_lon')
    if qty <= 0 or not lat or not lon:
        try:
            delete_order(o['id'])
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting {o['id']}: {e}")

print(f"Successfully deleted {deleted_count} invalid orders.")
