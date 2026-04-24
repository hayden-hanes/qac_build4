import argparse
import pandas as pd
import os
import sys

def calculate_beneish_mscore(df):
    # Calculate the Beneish M-Score using the specified Compustat variable mappings
    # M-Score formula components
    # Assuming the following mappings based on typical Beneish M-Score calculations:
    # 1. DSRI = (Receivables / Sales)
    # 2. GMI = (Gross Profit / Sales)
    # 3. AQI = (Current Assets / Total Assets)
    # 4. SGI = (Sales Growth Index)
    # 5. DEPI = (Depreciation / (Depreciation + Capital Expenditures))
    # 6. SGAI = (Selling, General and Administrative Expenses / Sales)
    # 7. LVGI = (Total Liabilities / Total Assets)
    
    # Calculate each component
    df['DSRI'] = df['rect'] / df['sale']
    df['GMI'] = df['gp'] / df['sale']
    df['AQI'] = df['act'] / df['at']
    df['SGI'] = df['sale'].pct_change().fillna(0) + 1  # Sales growth index
    df['DEPI'] = df['dp'] / (df['dp'] + df['capx'])
    df['SGAI'] = df['xsga'] / df['sale']
    df['LVGI'] = df['lt'] / df['at']

    # Calculate M-Score
    df['M_Score'] = (-4.840 + (0.920 * df['DSRI']) + (0.528 * df['GMI']) +
                     (0.404 * df['AQI']) + (0.892 * df['SGI']) +
                     (0.115 * df['DEPI']) - (0.172 * df['SGAI']) +
                     (0.327 * df['LVGI']))

    return df[['gvkey', 'datadate', 'M_Score']]

def main():
    parser = argparse.ArgumentParser(description='Calculate Beneish M-Score from Compustat data.')
    parser.add_argument('--data', required=True, help='Path to the input CSV data file.')
    parser.add_argument('--report_dir', required=True, help='Directory to save the report.')

    args = parser.parse_args()

    # Read the CSV file
    df = pd.read_csv(args.data)

    # Validate required columns
    required_columns = ['rect', 'sale', 'gp', 'act', 'at', 'dp', 'capx', 'xsga', 'lt']
    for col in required_columns:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}' in the dataset.")
            sys.exit(1)

    # Handle missing values with listwise deletion
    df = df.dropna(subset=required_columns)

    # Calculate the Beneish M-Score
    mscore_df = calculate_beneish_mscore(df)

    # Save the results to the report directory
    output_file = os.path.join(args.report_dir, 'beneish_m_score.csv')
    mscore_df.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()