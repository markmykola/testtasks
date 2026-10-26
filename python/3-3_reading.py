import pandas as pd

def load_daily_refactored(path, day):
    df = pd.read_csv(path)
    
    # Filter by exact date safely
    df['event_time'] = pd.to_datetime(df['event_time'], utc=True, errors='coerce')
    df = df[df['event_time'].dt.strftime('%Y-%m-%d') == day].copy()
    
    # Clean revenue (handle commas and empty strings safely)
    if df['revenue_usd'].dtype == object:
        df['revenue_usd'] = df['revenue_usd'].str.replace(',', '.', regex=False)
    df['revenue_usd'] = pd.to_numeric(df['revenue_usd'], errors='coerce').fillna(0.0)
    
    # Vectorized grouping (much faster than iterrows)
    df['key'] = df['app_id'].astype(str) + "-" + df['media_source'].astype(str)
    result = df.groupby('key', as_index=False)['revenue_usd'].sum()
    
    return result.rename(columns={'revenue_usd': 'revenue'}).sort_values('revenue', ascending=False)

# ======= Launch block =======
if __name__ == '__main__':
    # We specify the path to our test data and the specific day for verification.
    test_file_path = '../data/events_raw.csv'
    test_day = '2026-01-01'
    
    print(f"Running the refactored function for a date: {test_day}...")
    
    try:
        result_df = load_daily_refactored(test_file_path, test_day)
        print("\n=== Consolidated revenue result ===")
        print(result_df)
    except FileNotFoundError:
        print(f"\nError: File {test_file_path} not found.")
        print("Make sure you run the file from the `python` folder, and that the data is located in `data`./")