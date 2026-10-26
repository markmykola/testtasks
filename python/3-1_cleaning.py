import pandas as pd
import numpy as np

def clean_revenue(val):
    if pd.isna(val) or val == '' or 'NULL':
        return 0.0
    if isinstance(val, str):
        val = val.replace(',', '.')
    try:
        return float(val)
    except ValueError:
        return 0.0

def clean_country(val):
    if pd.isna(val):
        return 'XX'
    val = str(val).strip().upper()
    if len(val) == 2 and val.isalpha():
        return val
    return 'XX'

def clean_events(df):
    bad_mask = df['event_id'].isna() | (df['event_id'] == '')
    quarantine_df = df[bad_mask].copy()
    valid_df = df[~bad_mask].copy()

    if valid_df.empty:
        return valid_df, quarantine_df, 0

    valid_df = valid_df[valid_df['is_test'].astype(str).str.lower() != 'true'].copy()
    
    invalid_revenue_count = valid_df['revenue_usd'].isin(['', 'NULL', None]).sum()
    valid_df['revenue_usd'] = valid_df['revenue_usd'].apply(clean_revenue)
    valid_df['country'] = valid_df['country'].apply(clean_country)
    valid_df['event_time'] = pd.to_datetime(valid_df['event_time'], utc=True, errors='coerce')
    valid_df['ingested_at'] = pd.to_datetime(valid_df['ingested_at'], utc=True, errors='coerce')
    
    valid_df = valid_df.sort_values(by=['ingested_at', 'event_time'], ascending=[True, True])
    valid_df = valid_df.drop_duplicates(subset=['event_id'], keep='last')

    return valid_df, quarantine_df, invalid_revenue_count

# ======= TEST RUN BLOCK =======
if __name__ == '__main__':
    
    raw_df = pd.read_csv('../data/events_raw.csv', dtype=str)
    
    # call the function
    clean_df, quarantine_df, fixed_rev = clean_events(raw_df)
    
    # Output the results to the console to check if everything is working
    print(f"Number of corrected values revenue: {fixed_rev}\n")
    print("=== Cleaned data (first 5 rows) ===")
    print(clean_df[['event_id', 'revenue_usd', 'country', 'event_time']])