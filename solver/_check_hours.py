import pandas as pd
import os

cache_base = os.path.expanduser("~/.cache/kagglehub/datasets/evgenyarbatov/ho-chi-minh-city-road-traffic/versions")
parquet_path = None
if os.path.exists(cache_base):
    for ver_dir in sorted(os.listdir(cache_base), reverse=True):
        candidate = os.path.join(cache_base, ver_dir, "vietnam-road-traffic-observations.parquet")
        if os.path.exists(candidate):
            parquet_path = candidate
            break

if parquet_path:
    df = pd.read_parquet(parquet_path)
    # Convert string to datetime, then to UTC+7
    df['dt'] = pd.to_datetime(df['timestamp']).dt.tz_convert('Asia/Ho_Chi_Minh')
    df['hour'] = df['dt'].dt.hour
    
    print("Data points per hour:")
    print(df['hour'].value_counts().sort_index())
    
    # Calculate average congestion per hour
    df['congestion_ratio'] = df['currentSpeed'] / df['freeFlowSpeed']
    hourly_congestion = df.groupby('hour')['congestion_ratio'].mean()
    print("\nAverage congestion ratio per hour:")
    print(hourly_congestion)
else:
    print("Parquet file not found")
