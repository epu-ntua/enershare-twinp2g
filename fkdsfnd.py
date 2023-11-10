#%%   
import pandas as pd
import json 
import streamlit as st
# Opening JSON file 
# f = open('data_inputs2.json',) 
# with open('json_schema2.json') as f:
#%%
def fillna(file):
    file=file.fillna(method='pad')
    file=file.fillna(method='backfill')
    return file

def dates(file):
    start='2019-01-01'
    end='2020-09-30'
    file=file[start:end]
    return file

data=pd.read_csv('wind_data.csv', parse_dates=True)
data.set_index(['Datetime'], inplace=True)
data=fillna(data)
# data=dates(data)
data/=(1000)
# data.head(15)
data.describe()
#%%
data.to_csv('wind_data.csv',index=True)

#%%
with open('inputs.json') as f:
  data = json.load(f)
#   data=json.dumps(data, indent = 4)

# print(data)   
# print(json.dumps(data, indent=4))
#%%
# print(json.dumps(data['properties']['Component']['properties'], indent=4))
data['properties']['Bus']['properties']
# %%
# carriers=json.dumps(data['properties']['Carrier']['properties']['Generator']['allowed_values'], indent=4)
carriers=data['properties']['Carrier']['properties']['Generator']['allowed_values']
bus=data['properties']['input_series_source_type']['properties']["Generator"]['Solar']['allowed_values']
# st.write(carriers)
st.radio("skdjk",options=carriers)
choose=st.radio("jgjhg",options=bus)

if choose== 'csv file':
  st.file_uploader('JHJJ')

# %%
# print(json.dumps(data['properties']['input_series_source_type']['properties']['Generator'], indent=4))

# %%
