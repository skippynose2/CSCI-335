import pandas as pd
import numpy as np
from sklearn.ensemble import AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import precision_score, make_scorer


# Reading in the CSV file
df = pd.read_csv("financial_data_with_categories.csv")

# dropping any row that has NaN any target variable column
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

print(df_1day_x.head())
print("-----------------")
print(df_2day_x.head())
print("------------------")
print(df_3day_x.head())
print("-------------------")

# Define the hyperparameter grid to tune AdaBoost
param_grid = {
    'n_estimators': [50, 100, 200],
    'learning_rate': np.logspace(-2, 0, num=5)
}

# Getting the target variable, splitting it into test and validation set and testing with validation and testing data
for x in range(1, 4): # x will be 1, 2 and 3
    print("\n" + "="*42)
    print(f"Processing {x}-Day Forecast")
    print("="*42)
    
    target_var_cat = f"{x}d_price_chg_cat"
    df_y = df[target_var_cat]
    
    # splitting the data into train and test based on target_var_cat doing a 80 / 20 split
    if target_var_cat == "1d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_1day_x, df_y, test_size=0.2, random_state=35)
    elif target_var_cat == "2d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_2day_x, df_y, test_size=0.2, random_state=35)
    else:
        x_train, x_test, y_train, y_test = train_test_split(df_3day_x, df_y, test_size=0.2, random_state=35)
        
    # creating the training and validation data from the training data doing an 80 / 20 split again
    x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    # Applying feature scaling
    scaler = StandardScaler()
    x_train_model = scaler.fit_transform(x_train_model)
    x_validation = scaler.transform(x_validation)
    x_test = scaler.transform(x_test)

    y_train_model = y_train_model.astype(int)
    
    # Define the base estimator explicitly to allow max_depth tuning
    base_tree = DecisionTreeClassifier(random_state=42)
    
    # Initialize AdaBoost with the custom base estimator
    ada = AdaBoostClassifier(estimator=base_tree, random_state=42)
    
    # Set up the GridSearchCV
    precision_class_1_scorer = make_scorer(precision_score, labels=[1], average='macro', zero_division=0)
    
    grid_search = GridSearchCV(estimator=ada, param_grid=param_grid, cv=3, scoring=precision_class_1_scorer, n_jobs=1)
    
    print("Tuning hyperparameters for maximum precision... This may take a moment.")
    grid_search.fit(x_train_model, y_train_model)
    
    # Extract the best model from the grid search
    best_ada_model = grid_search.best_estimator_
    print(f"Best parameters found: {grid_search.best_params_}")

    # CV results into data frame
    results_df = pd.DataFrame(grid_search.cv_results_)

    # generating heatmap
    pivot_table = results_df.pivot(index='param_n_estimators', columns='param_learning_rate', values='mean_test_score')

    sns.heatmap(pivot_table, annot=True, cmap='viridis')
    plt.show()

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))


    df_y.value_counts().plot.bar(ax=axes[0], title='Full Data (df_y)')
    y_train.value_counts().plot.bar(ax=axes[1], title='Train (y_train)')
    y_test.value_counts().plot.bar(ax=axes[2], title='Test (y_test)')
    y_validation.value_counts().plot.bar(ax=axes[3], title='Validation (y_validation)')


    plt.tight_layout()
    plt.show()

    print(f"\n{x} Day Prediction metrics")
    validation_predictions = best_ada_model.predict(x_validation)
    print(f"Accuracy on validation set: {accuracy_score(y_validation.astype(int), validation_predictions) * 100:.2f}%")

    test_predictions = best_ada_model.predict(x_test)
    print(f"Accuracy on test set: {accuracy_score(y_test.astype(int), test_predictions) * 100:.2f}%")

    print("\nValidation Classification Report:")
    validation_report = classification_report(y_validation.astype(int), validation_predictions)
    print(validation_report)
