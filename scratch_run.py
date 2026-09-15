import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append('solver')
from pipeline import run_full_pipeline

try:
    res = run_full_pipeline(planning_days=5, order_limit=100)
    print('Total orders from KPI:', res['kpis']['total_orders'])
    print('Unassigned count (if any):', len(res.get('unassigned', [])))
except Exception as e:
    import traceback
    traceback.print_exc()
