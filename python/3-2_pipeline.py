import pandas as pd
import numpy as np
import os
import argparse

# This block is responsible for cleaning monetary values
def clean_revenue(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace('"', '').replace("'", "")
    if val_str.upper() == 'NULL' or val_str == '':
        return 0.0
    val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

# Normalizes country codes
def clean_country(val):
    if pd.isna(val):
        return 'XX'
    val = str(val).strip().upper()
    if len(val) == 2 and val.isalpha():
        return val
    return 'XX'

# Core logic of cleaning
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

def run_pipeline(input_dir, output_dir, since_date):
    """
    Orchestrates the ETL process: 
    Reads raw CSV, applies cleaning transformations, filters data incrementally 
    based on the 'since_date' (catching late arrivals via ingested_at), 
    and writes partitioned Parquet files for downstream analytics.
    """
    input_path = os.path.join(input_dir, 'events_raw.csv')
    df = pd.read_csv(input_path, dtype=str)
    
    rows_in = len(df)
    clean_df, quarantine_df, invalid_rev_count = clean_events(df)
    
    since_ts = pd.to_datetime(since_date, utc=True)
    clean_df = clean_df[clean_df['ingested_at'] >= since_ts].copy()

    rows_out = len(clean_df)
    rows_quarantined = len(quarantine_df)
    duplicates_removed = rows_in - rows_out - rows_quarantined - len(df[df['is_test'].astype(str).str.lower() == 'true'])

    clean_df['event_date'] = clean_df['event_time'].dt.strftime('%Y-%m-%d')
    
    os.makedirs(output_dir, exist_ok=True)
    clean_df.to_parquet(
        os.path.join(output_dir, 'clean_events'), 
        partition_cols=['event_date'], 
        engine='pyarrow',
        index=False
    )
    
    if not quarantine_df.empty:
        quarantine_df.to_parquet(os.path.join(output_dir, 'quarantined_events.parquet'), index=False)

    print(f"Summary -> Rows in: {rows_in} | Rows out: {rows_out} | Duplicates removed: {duplicates_removed} | Rows quarantined: {rows_quarantined} | Unparseable revenues fixed: {invalid_rev_count}\n")

# Needed to run file from console/terminal
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--since', required=True)
    args = parser.parse_args()
    
    # 1. Launching the main pipeline
    run_pipeline(args.input, args.output, args.since)

    # 2. Immediately after this, we verify the result using the provided output path
    clean_path = os.path.join(args.output, 'clean_events')
    if os.path.exists(clean_path):
        clean_df = pd.read_parquet(clean_path)
        print("=== Очищені дані (перші 5 рядків) ===")
        print(clean_df[['event_id', 'revenue_usd', 'country', 'event_time']].head())

    quarantine_path = os.path.join(args.output, 'quarantined_events.parquet')
    if os.path.exists(quarantine_path):
        quarantine_df = pd.read_parquet(quarantine_path)
        print("\n=== Карантинні дані ===")
        print(quarantine_df)
    else:
        print("\n=== Карантинні дані ===")
        print("Карантин порожній (немає поганих рядків), файл не створювався.")
