import numpy as np
import pandas as pd
pd.set_option('display.max_columns',None)
file=pd.read_csv(r'C:\Users\manager\Desktop\dataset\neflix\netflix_titles.csv')
file_df=pd.DataFrame(file)
print(file_df.head())
print(file_df.info())
# print(file_df['Target'].unique())

