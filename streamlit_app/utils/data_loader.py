import pandas as pd

def load_csv(path):
    try:
        df = pd.read_csv(path)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df = df.sort_values('timestamp')
        return df
    except Exception as e:
        return pd.DataFrame()

def calculate_rul(df, event_col='event'):
    rul = []
    event_indices = df.index[df[event_col] == 1].tolist()
    n = len(df)
    for i in range(n):
        future = [idx for idx in event_indices if idx >= i]
        rul.append(future[0] - i if future else n - i - 1)
    return rul
