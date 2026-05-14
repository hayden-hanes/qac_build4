import pandas as pd
import matplotlib.pyplot as plt
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
    # Read the dataset
    df = pd.read_csv(data_path)

    # Resolve necessary columns
    ticker_col = resolve_col(df, "ticker symbol")
    net_income_col = resolve_col(df, "net income (loss)")
    fiscal_year_col = resolve_col(df, "fiscal year-end month")

    # Filter for Apple and Nvidia
    filtered_df = df[df[ticker_col].isin(['AAPL', 'NVDA'])]

    # Handle missing values by using listwise deletion
    filtered_df = filtered_df.dropna(subset=[net_income_col, fiscal_year_col])

    # Extract the last 10 years of data
    filtered_df['fiscal_year'] = pd.to_datetime(filtered_df[fiscal_year_col]).dt.year
    last_10_years = filtered_df['fiscal_year'].max() - 10
    filtered_df = filtered_df[filtered_df['fiscal_year'] > last_10_years]

    # Create the line chart
    plt.figure(figsize=(10, 6))
    for ticker in ['AAPL', 'NVDA']:
        ticker_data = filtered_df[filtered_df[ticker_col] == ticker]
        plt.plot(ticker_data['fiscal_year'], ticker_data[net_income_col], marker='o', label=ticker)

    plt.title('Net Income of Apple and Nvidia Over the Last 10 Years')
    plt.xlabel('Fiscal Year')
    plt.ylabel('Net Income')
    plt.legend()
    plt.grid()
    
    # Save the plot
    report_path = os.path.join(report_dir, 'net_income_chart.png')
    plt.savefig(report_path)
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze financial data for Apple and Nvidia.')
    parser.add_argument('--data', required=True, help='Path to the input CSV data file.')
    parser.add_argument('--report_dir', required=True, help='Directory to save the report artifacts.')
    args = parser.parse_args()

    main(args.data, args.report_dir)