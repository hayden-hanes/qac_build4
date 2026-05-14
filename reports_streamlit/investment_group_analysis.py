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
    # Read data
    df = pd.read_csv(data_path)

    # Resolve ALL columns (no hardcoding anywhere)
    gvkey_col = resolve_col(df, "gvkey")
    capx_col = resolve_col(df, "capx")
    ebit_col = resolve_col(df, "ebit")
    ni_col = resolve_col(df, "ni")
    sale_col = resolve_col(df, "sale")

    # Drop missing values (listwise deletion)
    df = df[[gvkey_col, capx_col, ebit_col, ni_col, sale_col]].dropna()

    # Compute average CAPX per firm
    avg_capx = df.groupby(gvkey_col)[capx_col].mean().reset_index()
    avg_capx = avg_capx.rename(columns={capx_col: "avg_capx"})

    # Split firms into High vs Low investment groups
    threshold = avg_capx["avg_capx"].median()
    avg_capx["investment_group"] = avg_capx["avg_capx"].apply(
        lambda x: "High" if x > threshold else "Low"
    )

    # Merge group labels back to main data
    df = df.merge(avg_capx[[gvkey_col, "investment_group"]], on=gvkey_col)

    # Compute group-level averages
    comparison = df.groupby("investment_group").agg(
        avg_ebit=(ebit_col, "mean"),
        avg_ni=(ni_col, "mean"),
        avg_sale=(sale_col, "mean")
    ).reset_index()

    # Save output
    os.makedirs(report_dir, exist_ok=True)
    output_path = os.path.join(report_dir, "investment_group_comparison.csv")
    comparison.to_csv(output_path, index=False)

    # Print output for Streamlit
    print("\n=== Investment Group Comparison ===\n")
    print(comparison.to_string(index=False))
    print(f"\nSaved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare financial metrics for high vs low investment firms.")
    parser.add_argument("--data", required=True, help="Path to CSV data file")
    parser.add_argument("--report_dir", required=True, help="Directory to save output")

    args = parser.parse_args()
    main(args.data, args.report_dir)