from sklearn.model_selection import train_test_split, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
from sklearn import svm
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from sklearn.metrics import precision_score, make_scorer

# Assuming df, df_1day_x, df_2day_x, df_3day_x are already defined in your environment

# Reading in the CSV file
df = pd.read_csv("financial_data_with_categories.csv")

# dropping any row that has NaN any target variable column
df = df.dropna(subset=["1d_price_chg_cat"])
df = df.dropna(subset=["2d_price_chg_cat"])
df = df.dropna(subset=["3d_price_chg_cat"])
df = df.dropna()

# Encoding L to 0 and H to 1
df['1d_price_chg_cat'] = df['1d_price_chg_cat'].map({'L': 0, 'H': 1})
df['2d_price_chg_cat'] = df['2d_price_chg_cat'].map({'L': 0, 'H': 1})
df['3d_price_chg_cat'] = df['3d_price_chg_cat'].map({'L': 0, 'H': 1})


# Creating the data for the different days
df_1day_x = df.drop(columns=["ticker", "period_date", "1d_price_chg", "2d_price_chg", "3d_price_chg", "1d_price_chg_cat", "2d_price_chg_cat", "3d_price_chg_cat"])
df_2day_x = df.drop(columns=["ticker", "period_date", "2d_price_chg", "3d_price_chg", "2d_price_chg_cat", "3d_price_chg_cat"])
df_3day_x = df.drop(columns=["ticker", "period_date", "3d_price_chg", "3d_price_chg_cat"])


for x in range(1, 4): # x will be 1, 2 and 3
    print("------------------------------------------")
    target_var_cat = f"{x}d_price_chg_cat"
    
    # splitting the data into train and test based on target_var_cat doing a 80 / 20 split
    df_y = df[target_var_cat]
    if target_var_cat == "1d_price_chg_cat":
        # Creating testing and training data       
        x_train, x_test, y_train, y_test = train_test_split(df_1day_x, df_y, test_size=0.2, random_state=35)
        print(f"Test Set Length: {len(x_test)}")
        print(f"Test Labels Length: {len(y_test)}")
        # creating the training and validation data from the training data doing an 80 / 20 split again
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)
    elif target_var_cat == "2d_price_chg_cat":
        x_train, x_test, y_train, y_test = train_test_split(df_2day_x, df_y, test_size=0.2, random_state=35)
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)
    else:
        x_train, x_test, y_train, y_test = train_test_split(df_3day_x, df_y, test_size=0.2, random_state=35)
        x_train_model, x_validation, y_train_model, y_validation = train_test_split(x_train, y_train, test_size=0.20, random_state=35)

    # Applying feature scaling
    scaler = StandardScaler()
    scaler.fit(x_train_model)
    x_train_model = scaler.transform(x_train_model)
    x_validation = scaler.transform(x_validation)
    x_test = scaler.transform(x_test)

    y_train_model = y_train_model.astype(int)

    # ---------------------------------------------------------
    # HYPERPARAMETER TUNING SECTION
    # ---------------------------------------------------------
    print(f"Starting Grid Search for {x} Day Prediction...")
    
    # Define the hyperparameters and the values you want to test
    param_grid = {
        'C': [0.1, 1, 10], 
        'gamma': ['scale', 'auto', 0.1, 1],
        'kernel': ['rbf', 'linear']
    }

    precision_class_1_scorer = make_scorer(precision_score, labels=[1], average='macro', zero_division=0)
    
    
    # Initialize the base SVM model
    base_svm = svm.SVC(max_iter=1000000)
    
    # Setup GridSearchCV
    # cv=3 means 3-fold cross-validation. n_jobs=-1 uses all CPU cores.
    grid_search = RandomizedSearchCV(estimator=base_svm, param_distributions=param_grid, cv=3, scoring=precision_class_1_scorer, n_jobs=1, verbose=1)
    
    # Fit the grid search to the data
    grid_search.fit(x_train_model, y_train_model)
    
    # Output the best hyperparameters found
    print(f"Best Parameters for {x} Day: {grid_search.best_params_}")
    
    # Assign the best model found by the grid search to svm_model
    svm_model = grid_search.best_estimator_
    # CV results into data frame
    results_df = pd.DataFrame(grid_search.cv_results_)

    # Filter for the 'linear' kernel
    linear_results = results_df[results_df['param_kernel'] == 'linear']

    # Since gamma didn't affect the linear kernel, we can group by C to get the unique scores
    # (Taking the first value since all gammas for a given C will have the same score)
    c_scores = linear_results.groupby('param_C')['mean_test_score'].first()

    # Plotting the results as a line graph
    plt.figure(figsize=(8, 5))
    c_scores.plot(kind='line', marker='o', color='b', linewidth=2, markersize=8)

    plt.title(f'SVM Grid Search Precision Scores (Linear Kernel) - {x} Day')
    plt.xlabel('Parameter C')
    plt.ylabel('Mean Test Score (Class 1 Precision)')
    plt.grid(True, linestyle='--', alpha=0.7)

    # Make sure the X-axis shows our specific C values cleanly
    plt.xticks(c_scores.index) 
    plt.show()
    # ---------------------------------------------------------

    # Printing accuracy on the validation and test set
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))

    # Plot each series into its assigned axis (axes[0] through axes[3])
    df_y.value_counts().plot.bar(ax=axes[0], title='Full Data (df_y)')
    y_train.value_counts().plot.bar(ax=axes[1], title='Train (y_train)')
    y_test.value_counts().plot.bar(ax=axes[2], title='Test (y_test)')
    y_validation.value_counts().plot.bar(ax=axes[3], title='Validation (y_validation)')

    # Adjust layout to prevent overlapping titles/labels
    plt.tight_layout()
    plt.show()
    
    print(f"{x} Day Prediction metrics")
    
    # Predict using the tuned model
    validation_predictions = svm_model.predict(x_validation)
    print(f"Accuracy on validation set: {accuracy_score(y_validation.astype(int), validation_predictions) * 100:.2f}%")

    test_predictions = svm_model.predict(x_test)
    print(f"Accuracy on test set: {accuracy_score(y_test.astype(int), test_predictions) * 100:.2f}%")

    validation_report = classification_report(y_validation.astype(int), validation_predictions)
    print("Validation Report:")
    print(validation_report)
