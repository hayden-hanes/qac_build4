import pandas as pd
import argparse
import os

def resolve_col(df, key):
    key = key.lower().strip()
    matches = []
    for col in df.columns:
        col_l = col.lower().strip()
        if col_l == key:
            return col
        if col_l.startswith(f"({key})"):
            return col
        if key in col_l:
            matches.append(col)
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        raise ValueError(f"Ambiguous column match for '{key}': {matches}")
    raise ValueError(f"Could not resolve column: {key}")

def main(data_path, report_dir):
    # Read the data
    df = pd.read_csv(data_path)

    # Handle missing values with listwise deletion
    df.dropna(subset=[resolve_col(df, "capx"), resolve_col(df, "ebit"), resolve_col(df, "ni"), resolve_col(df, "sale")], inplace=True)

    # Calculate average Capital Expenditures for each firm
    capx_col = resolve_col(df, "capx")
    ebit_col = resolve_col(df, "ebit")
    ni_col = resolve_col(df, "ni")
    sale_col = resolve_col(df, "sale")
    
    gvkey_col = resolve_col(df, "gvkey")

    avg_capx = df.groupby(gvkey_col)[capx_col].mean().reset_index()
    avg_capx = avg_capx.rename(columns={capx_col: "avg_capx"})

    threshold = avg_capx["avg_capx"].median()
    avg_capx["investment_group"] = avg_capx["avg_capx"].apply(
    lambda x: "High" if x > threshold else "Low"
)

    df = df.merge(avg_capx[[gvkey_col, "investment_group"]], on=gvkey_col)

    # Calculate average financial metrics for each investment group
    comparison = df.groupby('investment_group').agg(
        avg_ebit=(ebit_col, 'mean'),
        avg_ni=(ni_col, 'mean'),
        avg_sale=(sale_col, 'mean')
    ).reset_index()

    # Save the results to a file
    report_file = os.path.join(report_dir, 'investment_group_comparison.csv')
    comparison.to_csv(report_file, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze firm investment spending and financial metrics.')
    parser.add_argument('--data', required=True, help='Path to the input CSV data file.')
    parser.add_argument('--report_dir', required=True, help='Directory to save the report.')
    args = parser.parse_args()
    
    main(args.data, args.report_dir)