# importing modules and packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn import preprocessing

# importing data- fix once in github
df = pd.read_csv('Real estate.csv')
df.drop('No', inplace=True, axis=1)

print(df.head())

print(df.columns)

# fix till here

# creating feature variables
y1 = df['One day price change']
y2 = df['Two day price change']
y3 = df['Three day price change']
x1 = df.drop(columns = ['One day price change', 'Two day price change', 'Three day price change'], axis = 1)
x2 = df.drop(columns = ['Two day price change', 'Three day price change'], axis = 1)
x3 = df.drop(columns = ['Three day price change'], axis = 1)


# creating train and test sets
x1_train, x1_test, y1_train, y1_test = train_test_split(
    x1, y1, test_size=0.2, random_state=89)
x2_train, x2_test, y2_train, y2_test = train_test_split(
    x2, y2, test_size=0.2, random_state=66)
x3_train, x3_test, y3_train, y3_test = train_test_split(
    x3, y3, test_size=0.2, random_state=110)

# creating a regression model and fitting the model
model1 = LinearRegression()
model1.fit(x1_train, y1_train)
model2 = LinearRegression()
model2.fit(x2_train, y2_train)
model3 = LinearRegression()
model3.fit(x3_train, y3_train)

# making predictions
predictions1 = model1.predict(x1_test)
predictions2 = model2.predict(x2_test)
predictions3 = model3.predict(x3_test)


# model evaluation
print('Model 1 mean_squared_error : ', mean_squared_error(y1_test, predictions1))
print('Model 1 mean_absolute_error : ', mean_absolute_error(y1_test, predictions1))
print('Model 2 mean_squared_error : ', mean_squared_error(y2_test, predictions2))
print('Model 2 mean_absolute_error : ', mean_absolute_error(y2_test, predictions2))
print('Model 3 mean_squared_error : ', mean_squared_error(y3_test, predictions3))
print('Model 3 mean_absolute_error : ', mean_absolute_error(y3_test, predictions3))