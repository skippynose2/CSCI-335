import pandas as pd
import numpy as np

def categorize_change(val):
    # Handle NaN/null values
    if pd.isna(val):
        return np.nan
        
    # Check for negative values 
    # (Prompt did not specify a category for negatives, so we'll label them 'NEG')
    if val < 0:
        return 'L'
    else:
        return 'H'

def main():
    # 1. Load the dataset (replace 'financial_data.csv' with your actual filename)
    df = pd.read_csv('training_data.csv')
    
    # 2. Define the columns we want to categorize
    cols_to_categorize = ['1d_price_chg', '2d_price_chg', '3d_price_chg']
    
    # 3. Iterate through the columns and apply the categorization logic
    for col in cols_to_categorize:
        new_col_name = f"{col}_cat"
        df[new_col_name] = df[col].apply(categorize_change)
        
    # Display the first few rows to verify the logic worked
    print(df[['1d_price_chg', '1d_price_chg_cat', 
              '2d_price_chg', '2d_price_chg_cat', 
              '3d_price_chg', '3d_price_chg_cat']].head())
              
    # 4. Save the updated DataFrame to a new CSV file
    df.to_csv('financial_data_with_categories.csv', index=False)
    print("\nFile saved successfully as 'financial_data_with_categories.csv'")

if __name__ == "__main__":
    main()
