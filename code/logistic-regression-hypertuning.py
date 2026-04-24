import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression  # Changed import
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, precision_score, make_scorer
import matplotlib.pyplot as plt
import seaborn as sns

# Reading in the CSV file
df = pd.read_csv("financial_data_with_categories.csv")

# Dropping any row that has NaN any target variable column
df = df.dropna(subset=["1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df = df.dropna()

# Encoding L to 0 and H to 1
df['1d_price_chg_cat'] = df['1d_price_chg_cat'].map({'L': 0, 'H': 1})
df['2d_price_chg_cat'] = df['2d_price_chg_cat'].map({'L': 0, 'H': 1})
df['3d_price_chg_cat'] = df['3d_price_chg_cat'].map({'L': 0, 'H': 1})

# Creating the data for the different days
df_1day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df_2day_x = df.drop(columns=["ticker", "period_date", "2d_price_chg", "3d_price_chg", "2d_price_chg_cat", "3d_price_chg_cat"])
df_3day_x = df.drop(columns=["ticker", "period_date", "3d_price_chg", "3d_price_chg_cat"])
#df_2day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
#df_3day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])

# Define the hyperparameter grid for Logistic Regression
# C is inverse regularization strength; smaller values = stronger regularization
param_grid = {
    'C': [0.001, 0.01, 0.1, 1, 10, 100],
    'solver': ['liblinear', 'lbfgs', 'newton-cg', 'sag', 'saga'], # liblinear works well for small datasets/L1
    'max_iter': [1000000]
}

# Getting the target variable, splitting it into test and validation set
for x in range(2, 4):
    print("\n" + "="*42)
    print(f"Processing {x}-Day Forecast (Logistic Regression)")
    print("="*42)
    
    target_var_cat = f"{x}d_price_chg_cat"
    df_y = df[target_var_cat]
    
    if target_var_cat == "1d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_1day_x, df_y, test_size=0.2, random_state=35)
    elif target_var_cat == "2d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_2day_x, df_y, test_size=0.2, random_state=35)
    else:
        x_train, x_test, y_train, y_test = train_test_split(df_3day_x, df_y, test_size=0.2, random_state=35)
        
    x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    # Applying feature scaling (CRITICAL for Logistic Regression)
    scaler = StandardScaler()
    x_train_model = scaler.fit_transform(x_train_model)
    x_validation = scaler.transform(x_validation)
    x_test = scaler.transform(x_test)

    y_train_model = y_train_model.astype(int)
    
    # Initialize Logistic Regression
    lr = LogisticRegression(random_state=42)
    
    # Set up the GridSearchCV
    precision_class_1_scorer = make_scorer(precision_score, labels=[1], average='macro', zero_division=0)
    
    grid_search = GridSearchCV(estimator=lr, param_grid=param_grid, cv=3, scoring=precision_class_1_scorer, n_jobs=1)
    
    print("Tuning hyperparameters for maximum precision...")
    grid_search.fit(x_train_model, y_train_model)
    
    # Extract the best model
    best_lr_model = grid_search.best_estimator_
    print(f"Best parameters found: {grid_search.best_params_}")

    # CV results into data frame
    results_df = pd.DataFrame(grid_search.cv_results_)

    # generating heatmap (Note: changed labels to reflect Logistic Regression params)
    pivot_table = results_df.pivot(index='param_C', columns='param_solver', values='mean_test_score')

    sns.heatmap(pivot_table, annot=True, cmap='viridis')
    plt.title(f"Hyperparameter Heatmap (Day {x})")
    plt.show()

    # Metrics display
    print(f"\n{x} Day Prediction metrics")
    validation_predictions = best_lr_model.predict(x_validation)
    print(f"Accuracy on validation set: {accuracy_score(y_validation.astype(int), validation_predictions) * 100:.2f}%")

    test_predictions = best_lr_model.predict(x_test)
    print(f"Accuracy on test set: {accuracy_score(y_test.astype(int), test_predictions) * 100:.2f}%")

    print("\nValidation Classification Report:")
    print(classification_report(y_validation.astype(int), validation_predictions))
