import sys
sys.path.append('solver')
from pipeline import get_orders
from dinic_flow import split_orders, build_vehicle_infos_from_db, OrderInfo

orders_raw = get_orders()[:100]
orders_info = []
for o in orders_raw:
    qty = o.get('total_quantity', 0)
    w_min = max(1, int(qty * 0.15))
    orders_info.append(OrderInfo(
        order_id=o['id'], order_code=o['order_code'], customer_id=o.get('customer_id', 0),
        total_quantity=qty, total_weight_kg=o.get('total_weight_kg', 0),
        customer_lat=o.get('customer_lat', 10.78), customer_lon=o.get('customer_lon', 106.70),
        customer_name=o.get('customer_name', 'Unknown'),
        time_window_start=o.get('time_window_start', '08:00'),
        time_window_end=o.get('time_window_end', '17:00'),
        w_min=w_min, w_max=qty
    ))

vehicles_info = build_vehicle_infos_from_db()
assignments = split_orders(orders_info, vehicles_info, num_days=5, delivery_dates=['d1', 'd2', 'd3', 'd4', 'd5'])
print('Total orders:', len(orders_info))
print('Total assignments:', len(assignments))

zero_flow = 0
for a in assignments:
    if a.assigned_quantity <= 0:
        zero_flow += 1

print('Zero flow assignments:', zero_flow)
orders_with_flow = set([a.order_code for a in assignments if a.assigned_quantity > 0])
print('Orders with flow:', len(orders_with_flow))
