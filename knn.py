import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt

df = pd.read_csv("financial_data_with_categories.csv")

# Drop any row that has NaN any target variable column
df = df.dropna(subset=["1d_price_chg_cat"])
df = df.dropna(subset=["2d_price_chg_cat"])
df = df.dropna(subset=["3d_price_chg_cat"])
df = df.dropna()

# Encoding L to 0 and H to 1
df['1d_price_chg_cat'] = df['1d_price_chg_cat'].map({'L': 0, 'H': 1})
df['2d_price_chg_cat'] = df['2d_price_chg_cat'].map({'L': 0, 'H': 1})
df['3d_price_chg_cat'] = df['3d_price_chg_cat'].map({'L': 0, 'H': 1})

# Create data for different days 
df_1day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df_2day_x = df.drop(columns=["ticker", "period_date", "2d_price_chg", "3d_price_chg", "2d_price_chg_cat", "3d_price_chg_cat"])
df_3day_x = df.drop(columns=["ticker", "period_date", "3d_price_chg", "3d_price_chg_cat"])

print(df_1day_x.head())
print("-----------------")
print(df_2day_x.head())
print("------------------")
print(df_3day_x.head())
print("-------------------")

# Loop through 1-day, 2-day, 3-day predictions
for x in range(1, 4):
    print("------------------------------------------")
    target_var_cat = f"{x}d_price_chg_cat"
    df_y = df[target_var_cat]

    if target_var_cat == "1d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_1day_x, df_y, test_size=0.2, random_state=35)
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    elif target_var_cat == "2d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_2day_x, df_y, test_size=0.2, random_state=35)
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    else:
        x_train, x_test, y_train, y_test = train_test_split(df_3day_x, df_y, test_size=0.2, random_state=35)
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    # Feature scaling 
    scaler = StandardScaler()
    scaler.fit(x_train_model)
    x_train_model = scaler.transform(x_train_model)
    x_validation = scaler.transform(x_validation)
    x_test = scaler.transform(x_test)

    y_train_model = y_train_model.astype(int)

    # Try multiple K values (hyperparameter tuning)
    for k in [3, 5, 7, 9]:
        print(f"\n=== {x}-Day Prediction with K={k} ===")

        knn_model = KNeighborsClassifier(n_neighbors=k)
        knn_model.fit(x_train_model, y_train_model)

        # Plot class distributions
        fig, axes = plt.subplots(1, 4, figsize=(16, 4))
        df_y.value_counts().plot.bar(ax=axes[0], title='Full Data (df_y)')
        y_train.value_counts().plot.bar(ax=axes[1], title='Train (y_train)')
        y_test.value_counts().plot.bar(ax=axes[2], title='Test (y_test)')
        y_validation.value_counts().plot.bar(ax=axes[3], title='Validation (y_validation)')
        plt.tight_layout()
        plt.show()

        # Print validation performance
        val_preds = knn_model.predict(x_validation)
        print(f"Validation Accuracy: {accuracy_score(y_validation.astype(int), val_preds) * 100}")

        # Print test performance
        test_preds = knn_model.predict(x_test)
        print(f"Test Accuracy: {accuracy_score(y_test.astype(int), test_preds) * 100}")

        # Print report 
        print("Classification Report (Validation):")
        print(classification_report(y_validation.astype(int), val_preds))
