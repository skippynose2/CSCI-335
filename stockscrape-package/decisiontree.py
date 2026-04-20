import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import matplotlib.pyplot as plt


# Load data
df = pd.read_csv("financial_data_with_categories.csv")

# Drop NaNs
df = df.dropna(subset=["1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df = df.dropna()

# Encode labels
df['1d_price_chg_cat'] = df['1d_price_chg_cat'].map({'L': 0, 'H': 1})
df['2d_price_chg_cat'] = df['2d_price_chg_cat'].map({'L': 0, 'H': 1})
df['3d_price_chg_cat'] = df['3d_price_chg_cat'].map({'L': 0, 'H': 1})

# Feature sets
df_1day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df_2day_x = df.drop(columns=["ticker", "period_date", "2d_price_chg", "3d_price_chg", "2d_price_chg_cat", "3d_price_chg_cat"])
df_3day_x = df.drop(columns=["ticker", "period_date", "3d_price_chg", "3d_price_chg_cat"])

# Loop
for x in range(1, 4):
    print("\n====================================")
    print(f"{x}-Day Prediction")
    print("====================================")

    target_var = f"{x}d_price_chg_cat"
    df_y = df[target_var]

    if x == 1:
        X = df_1day_x
    elif x == 2:
        X = df_2day_x
    else:
        X = df_3day_x

    # Split
    x_train, x_test, y_train, y_test = train_test_split(X, df_y, test_size=0.2, random_state=35)
    x_train_model, x_val, y_train_model, y_val = train_test_split(x_train, y_train, test_size=0.2, random_state=35)

    y_train_model = y_train_model.astype(int)

    # Plot class distributions once per day
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))

    df_y.value_counts().plot.bar(ax=axes[0], title='Full Data')
    y_train.value_counts().plot.bar(ax=axes[1], title='Train')
    y_test.value_counts().plot.bar(ax=axes[2], title='Test')
    y_val.value_counts().plot.bar(ax=axes[3], title='Validation')

    plt.tight_layout()
    plt.show()

    # Try depths
    for depth in [3, 5, 10, None]:
        print(f"\n--- max_depth={depth} ---")

        model = DecisionTreeClassifier(max_depth=depth, random_state=35)
        model.fit(x_train_model, y_train_model)

        val_preds = model.predict(x_val)
        test_preds = model.predict(x_test)

        print("Validation Accuracy:", accuracy_score(y_val, val_preds))
        print("Test Accuracy:", accuracy_score(y_test, test_preds))

        print("Classification Report (Validation):")
        print(classification_report(y_val, val_preds))
