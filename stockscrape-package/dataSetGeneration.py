import pandas as pd
from sqlalchemy import create_engine
from stockscrape.config import DATABASE_URL

def upload_dataframe(df, table_name):
    """
    Uploads a pandas DataFrame to a PostgreSQL table.
    """
    try:
        # 1. Create the engine
        # Note: DATABASE_URL must start with 'postgresql://' or 'postgresql+psycopg2://'
        engine = create_engine('postgresql://skippy:akhil2003@localhost:5432/stockscrape')

        # 2. Upload the data
        # if_exists options: 'fail', 'replace', or 'append'
        df.to_sql(
            name=table_name, 
            con=engine, 
            if_exists='replace', 
            index=False,
            method='multi',  # This speeds up the upload by batching rows
            chunksize=10000
        )
        
        print(f"Successfully uploaded data to table: {table_name}")

    except Exception as e:
        print(f"An error occurred: {e}")


#df = pd.read_csv('data/earnings_dataset.csv')

#dfTest = df['ticker']

#print(df)

#upload_dataframe(df, 'earnings_call')


import pandas as pd

def process_statement_data(file_path):
    # Load the CSV file
    df = pd.read_csv(file_path)
    
    # Create separate DataFrames based on the statement_type column
    df_income = df[df['statement_type'] == 'income'].copy().reset_index(drop=True)
    df_balance = df[df['statement_type'] == 'balance'].copy().reset_index(drop=True)
    
    # Define a function to drop columns with more than 50% null values
    def drop_null_cols(df_subset):
        # threshold is the minimum number of NON-NULL values to keep the column
        # If over 50% are null, we need at least 50% non-null to keep it
        threshold = len(df_subset) * 0.5
        return df_subset.dropna(axis=1, thresh=threshold)
    
    # Apply the dropping logic to each DataFrame
    df_income = drop_null_cols(df_income)
    df_balance = drop_null_cols(df_balance)
    
    
    return df_income, df_balance

def calculate_group_pct_change(df, group_col, value_col):
    df_copy = df.copy().reset_index(drop=True)

    for _ in range(len(value_col)):
        print(value_col[_])

        value_name = value_col[_]

        new_col_name = f"{value_name}_pct_change"
        df_copy[new_col_name] = df_copy.groupby(group_col)[value_name].pct_change()*100

    return df_copy

import pandas as pd

def compute_leverage_ratios(df):
    """
    Computes Debt-to-Equity and Debt-to-Asset ratios.
    Formula:
    Debt to Equity = total_liabilities / total_equity
    Debt to Assets = total_liabilities / total_assets
    """
    # Create a copy to avoid SettingWithCopy warnings
    df_ratios = df.copy().reset_index(drop=True)
    
    # Calculate Debt to Equity
    # Note: If total_equity is 0, this will result in 'inf' (infinity)
    df_ratios['debt_to_equity'] = df_ratios['total_liabilities'] / df_ratios['total_equity']
    
    # Calculate Debt to Assets
    df_ratios['debt_to_assets'] = df_ratios['total_liabilities'] / df_ratios['total_assets']
    
    return df_ratios


def filter_by_fiscal_year(df, year_threshold):
    """
    Returns a new DataFrame containing only rows where 
    'fiscal_year' is strictly greater than year_threshold.
    """
    # Ensure the column exists to avoid another KeyError
    if 'fiscal_year' not in df.columns:
        print(f"Warning: 'fiscal_year' column not found in DataFrame.")
        return df
    
    # Filter for years above the threshold
    # .copy() ensures we don't modify the original slice
    filtered_df = df[df['fiscal_year'] >= year_threshold].copy()
    
    # Reset the index so the new DF starts at 0
    return filtered_df.reset_index(drop=True)

# Example Usage:
# df_recent_income = filter_by_fiscal_year(df_income, 2020)


# Reading in daily prices
df_prc = pd.read_csv('data/daily_prices.csv')

df_prices = df_prc.rename(columns={'date': 'period_date'})

print(df_prices)


# Example usage:
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', lambda x: '%.3f' % x)
df_inc, df_bal  = process_statement_data('data/fundamentals.csv')

df_income = filter_by_fiscal_year(df_inc, 2015)
df_balance = filter_by_fiscal_year(df_bal, 2015)

df_income = df_income.drop(columns=['statement_type', 'fiscal_year', 'period'])
df_balance = df_balance.drop(columns=['statement_type', 'fiscal_year', 'period'])

# print(df_income.head())
# This is good leave this alone
df_income_with_pct_change = calculate_group_pct_change(df_income, 'ticker', ['gross_profit', 'operating_income', 'net_income', 'revenue'])
print(df_income_with_pct_change)
print("-----------------")
df_balance_with_ratios = compute_leverage_ratios(df_balance)
df_balance_with_ratios_pct_change = calculate_group_pct_change(df_balance_with_ratios, 'ticker', ['total_assets', 'total_liabilities', 'total_equity', 'cash_and_equivalents', 'debt_to_equity', 'debt_to_assets'])
print(df_balance_with_ratios_pct_change)

# combining the two dataframes into one
import pandas as pd

def merge_financials(df_income, df_balance):
    """
    Combines Income and Balance DataFrames based on ticker and fiscal_year.
    """
    # Define the common keys to join on
    # Using both ticker and year ensures 'AAPL 2023' matches 'AAPL 2023'
    join_keys = ['ticker', 'period_date']
    
    # Check if keys exist in both DataFrames
    for df, name in [(df_income, "Income"), (df_balance, "Balance")]:
        missing = [k for k in join_keys if k not in df.columns]
        if missing:
            print(f"Error: {name} DataFrame is missing keys: {missing}")
            return df_income

    # Perform the merge
    # 'how=left' preserves all rows in the first dataframe
    combined_df = pd.merge(
        df_income, 
        df_balance, 
        on=join_keys, 
        how='left',
        suffixes=('', '_bal') # Adds suffix if column names overlap (except keys)
    )
    
    # Clean up the index as requested previously
    return combined_df.reset_index(drop=True)

# Example Usage:
# df_combined = merge_financials(df_income, df_balance)
concatenated_df = merge_financials(df_income_with_pct_change, df_balance_with_ratios_pct_change)
print(concatenated_df)

# Computing price change over a certain number of days
import pandas as pd

def add_price_performance(df_daily_prices):
    """
    Calculates 1, 2, and 3-day price changes from daily data and
    merges them into the combined financials dataframe.
    """
    # 1. Name the columns for the daily price data
    # price_cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
    # df_daily_prices.columns = price_cols
    
    # 2. Convert date and sort to ensure pct_change looks at the correct previous day
    #df_daily_prices['date'] = pd.to_datetime(df_daily_prices['date'])
    #df_daily_prices = df_daily_prices.sort_values(['ticker', 'date']).reset_index(drop=True)

    # 3. Calculate 1, 2, and 3 day percentage changes
    # pct_change(1) is today vs yesterday, pct_change(2) is today vs 2 days ago, etc.
    grouped = df_daily_prices.groupby('ticker')

    
    # 1-day: (Close - Open) / Open
    df_daily_prices['1d_price_chg'] = (
        (df_daily_prices['close'] - df_daily_prices['open']) / df_daily_prices['open']
    ) * 100
    
    # 2-day: (Close today - Open yesterday) / Open yesterday
    # We shift the 'open' column by 1 within each ticker group
    open_yesterday = df_daily_prices.groupby('ticker')['open'].shift(1)
    df_daily_prices['2d_price_chg'] = (
        (df_daily_prices['close'] - open_yesterday) / open_yesterday
    ) * 100
    
    # 3-day: (Close today - Open 2 days ago) / Open 2 days ago
    open_2_days_ago = df_daily_prices.groupby('ticker')['open'].shift(2)
    df_daily_prices['3d_price_chg'] = (
        (df_daily_prices['close'] - open_2_days_ago) / open_2_days_ago
    ) * 100
    
    '''
    grouped = df_daily_prices.groupby('ticker')['close']
    df_daily_prices['1d_price_chg'] = grouped.pct_change(periods=1)
    df_daily_prices['2d_price_chg'] = grouped.pct_change(periods=2)
    df_daily_prices['3d_price_chg'] = grouped.pct_change(periods=3)
    '''


    # print(df_daily_prices)


    num_rows_with_nan = df_daily_prices.isna().any(axis=1).sum()

    print("#################################################")
    print(num_rows_with_nan)


    return df_daily_prices

    # 4. Extract the year to match the 'fiscal_year' in your financials
    # df_daily_prices['period_date'] = df_daily_prices['date'].dt.year

    #df = df_daily_prices[(df_daily_prices['ticker'] == 'A') & (df_daily_prices['date'] == '2015-01-31')]
    #print ("printing dataframe")
    #print(df)

    # 5. Get the LAST trading day of each year for each ticker 
    # (This aligns the annual financial report with the end-of-year price performance)
    # df_yearly_price = df_daily_prices.sort_values('date').groupby(['ticker', 'fiscal_year']).last().reset_index()

    # 6. Merge with the combined financials dataframe
    # We only bring over the new change columns

    '''
    df_prices_renamed = df_daily_prices.rename(columns={'date' : 'period_date'})

    cols_to_merge = ['ticker', 'fiscal_year', '1d_price_chg', '2d_price_chg', '3d_price_chg']
    final_df = pd.merge(
        df_combined, 
        df_prices_renamed, 
        on=['ticker', 'period_date'], 
        how='left'
    )

    return final_df.reset_index(drop=True)
    '''



final_df = add_price_performance (df_prices)

print("--------------------------------------")

print(final_df)


somethingDf = final_df[(final_df['period_date'] == '2016-01-31') & (final_df['ticker'] == 'A')]

print(somethingDf)


def lookup_and_retrieve_rows(df_main, df_reference, column_name='period_date'):
    """
    For every value in df_main[column_name], finds the matching 
    row in df_reference and returns a combined DataFrame.
    """
    # 1. Ensure the column exists in both
    if column_name not in df_main.columns or column_name not in df_reference.columns:
        print(f"Error: {column_name} not found in one of the dataframes.")
        return df_main

    df_main['period_date'] = pd.to_datetime(df_main['period_date'])
    df_reference['period_date'] = pd.to_datetime(df_reference['period_date'])

    # 2. Use merge to "find and get" the rows. 
    # 'left' keeps all rows from df_main and attaches data from df_reference where it matches.
    result_df = pd.merge(
        df_main, 
        df_reference, 
        on=['ticker', 'period_date'], 
        how='left'
    )

    # print(result_df)
    
    return result_df.reset_index(drop=True)


from pandas.tseries.offsets import DateOffset

def round_to_nearest_weekday(df, date_col):
    """
    Adjusts dates in the specified column to the nearest weekday.
    Saturday -> Friday (-1 day)
    Sunday -> Monday (+1 day)
    """
    # 1. Ensure the column is in datetime format
    df[date_col] = pd.to_datetime(df[date_col])
    
    # 2. Get the day of the week (0=Monday, 5=Saturday, 6=Sunday)
    weekday = df[date_col].dt.weekday
    
    # 3. Apply the shifts
    # Shift Saturdays (5) back by 1 day
    df.loc[weekday == 5, date_col] = df.loc[weekday == 5, date_col] - pd.Timedelta(days=1)
    
    # Shift Sundays (6) forward by 1 day
    df.loc[weekday == 6, date_col] = df.loc[weekday == 6, date_col] + pd.Timedelta(days=1)
    
    return df

# Example Usage:
df = round_to_nearest_weekday(concatenated_df, 'period_date')

print("**************************************************************")

print(df)


df_finals = lookup_and_retrieve_rows(concatenated_df, final_df, 'period_date')

print(df_finals)

df_finals.to_csv('training_data.csv', index=False)


cols_to_check = ['1d_price_chg', '2d_price_chg', '3d_price_chg']

num_rows_with_nan = df_finals[cols_to_check].isna().any(axis=1).sum()

print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
print(num_rows_with_nan)
print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")


rows_with_any_nan = df_finals[df_finals.isna().any(axis=1)]
print(rows_with_any_nan)




