# %%
import numpy as np
import pypsa
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = [10, 5]
from pyomo.environ import Constraint
import logging
import datetime
import os
import subprocess


# %%
#%matplotlib inline
logging.basicConfig(level="INFO")
# %%
network = pypsa.Network()

# %% 
def fillna(file):
    file=file.fillna(method='pad')
    file=file.fillna(method='backfill')
    return file

def dates(file):
    start='2018-01-01 01:00:00+00:00'
    end='2019-10-31 23:00:00+00:00'
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    start=start.strftime("%Y-%m-%d %H:%M:%S+00:00")
    end=end.strftime("%Y-%m-%d %H:%M:%S+00:00")
    file=file[start:end]
    return file

#%% Read CSV from 'input_series_source_uri'
def read_csv(data):
    data_csv = pd.read_csv(data, parse_dates=True)
    data_csv.set_index(['Datetime'], inplace=True)
    data_csv=fillna(data_csv)
    data_csv=dates(data_csv) 
    network.set_snapshots(data_csv.index)
    return data_csv 
#%% Call pvlibdata.py
def pvlib():
    subprocess.call(['python','./pvlib_folder/pvlibdata.py'])
    pv_data='pvlib_folder/solar_data.csv'
    data_pvprod=read_csv(pv_data)
    return data_pvprod

# %% [markdown]
# ## Προσομοίωση Δικτύου
# %%
inputs2=pd.read_csv('data_inputs2.csv')
inputs2.set_index(['Component','carrier'],inplace=True)
inputs2

# %% Number of Components
buses=inputs2.index.get_level_values('Component').value_counts()['Bus']
generators=inputs2.index.get_level_values('Component').value_counts()['Generator']
lines=inputs2.index.get_level_values('Component').value_counts()['Line']
loads=inputs2.index.get_level_values('Component').value_counts()['Load']
# %% [markdown]
# ## Buses
#%%
for i in range(buses):
    carrier=inputs2.loc['Bus'].index[i]
    bus=inputs2['bus']['Bus'][i]
    network.add("Bus",name=bus, carrier=carrier)
network.buses
# %% [markdown]
# ## Lines
#%%
for i in range(lines):
    bus0 = inputs2['from_bus']['Line'][i]
    bus1 = inputs2['to_bus']['Line'][i]
    network.add("Line", f"Line {bus0} - {bus1}", bus0=bus0, bus1=bus1, r=0.01, x=0.1, s_nom_extendable=True)
network.lines
# %% [markdown]
# ## Loads
#%%
for i in range(loads):
    bus = inputs2['bus']['Load'][i]
    load_data_source_type=inputs2['input_series_source_type']['Load'][i]
    if load_data_source_type=='csv file':
        load_data_uri=inputs2['input_series_source_uri']['Load'][i]
        data_load=read_csv(load_data_uri)
        print(data_load)
        p_set=np.array(data_load['GR_load'])
    network.add("Load", f"Load {bus}", bus=bus, p_set=p_set)    
network.loads
# %% [markdown]
# ## Generators
#%%
for i in range(generators): 
    bus=inputs2['bus']['Generator'][i]
    generator_data_source_type=inputs2['input_series_source_type']['Generator'][i]
    carrier=inputs2.loc['Generator'].index[i]
    if carrier=='Solar':  
        if generator_data_source_type =='csv file':
            pv_data=inputs2['input_series_source_uri']['Generator'][i]
            data_pvprod=read_csv(pv_data)
            p_max_pu_value = np.array(data_pvprod['GR_solar_generation'])
        elif generator_data_source_type=='pvlib':
            data_pvprod=pvlib()
            p_max_pu_value = np.array(data_pvprod['GR_solar_generation'])
        else: 
            p_max_pu_value=1  

    elif carrier=='Wind':
        if generator_data_source_type =='csv file':
            wind_data_source_uri=inputs2['input_series_source_uri']['Generator'][i]
            data_windprod=read_csv(wind_data_source_uri)
            p_max_pu_value = np.array(data_windprod['GR_wind_onshore_generation_actual'])
        else: 
            p_max_pu_value=1  
    
    else:
        p_max_pu_value = 1  
    
    network.add(
        "Generator",
        f'Generator {bus}',
        bus=bus,
        carrier=carrier,  
        p_nom=float(inputs2['p_nom']['Generator'][i]),  
        p_nom_extendable=False,
        p_max_pu=p_max_pu_value,
        capital_cost=float(inputs2['capital_cost']['Generator'][i]),  
        marginal_cost=float(inputs2['marginal_cost']['Generator'][i]) 
    )
network.generators

# %% [markdown]
# ## Προσωμοίωση Power to Gas  


#%% Number of Links and Stores
links=inputs2.index.get_level_values('Component').value_counts()['Link']
stores = inputs2.index.get_level_values('Component').value_counts()['Store']
# %% [markdown]
# ## Links
#%%
for i in range(links):
    bus0=inputs2['from_bus']['Link'][i]
    bus1=inputs2['to_bus']['Link'][i]
    carrier = inputs2.loc['Link'].index[i]
    efficiency=inputs2['efficiency']['Link'][i]

    network.add(
        "Link",
        name=f'{carrier} {bus0} - {bus1}',
        bus0=bus0,
        bus1=bus1,
        carrier=carrier,
        efficiency=efficiency,
        p_nom=float(inputs2['p_nom']['Link'][i]),  
        p_nom_extendable=True,
        capital_cost=float(inputs2['capital_cost']['Link'][i]) // (25 / float(inputs2['investment_period']['Load'][0])), 
        marginal_cost=float(inputs2['marginal_cost']['Link'][i]),  
    )
network.links
# %% [markdown]
# ## Stores
#%%
for i in range(stores):
    bus=inputs2['bus']['Store'][i]
    carrier = inputs2.loc['Store'].index[i]
    network.add(
        "Store",
        name=f'Store {bus}',
        bus=bus,
        carrier=carrier,
        e_nom=float(inputs2['p_nom']['Store'][i]),  
        e_cyclic=True,
        e_nom_extendable=True,
        capital_cost=float(inputs2['capital_cost']['Store'][i]) // (25 / float(inputs2['investment_period']['Load'][0])),  
        marginal_cost=float(inputs2['marginal_cost']['Store'][i]) 
    )
network.stores

# %% [markdown]
# ## Ροη φορτιου και βελτιστοποιηση

# %%
network.optimize(network.snapshots, solver_name="glpk", solver_options={})

# %% [markdown]
# ## Αποτελέσματα και Σχόλια
# Παρακάτω εμφανίζονται τα δεδομένα της βελτιστοποίησης οπως είναι: το objective function, το μονογραμμικο διάγραμμα απο το network.iplot() της pypsa και γραφικές παραστάσεις στις οποίες απεικονίζονται η παραγωγή, η ζήτηση, ο ηλεκτρολυτης και το fuel cell και τέλος το store υδρογονου.

# %%
#total system cost for the snapshots optimised
network.objective 

# %%
network.statistics().round(2)

# %%
statistics=network.statistics()

# %%
network.iplot()

# %%
df=pd.concat([network.generators_t.p, network.links_t.p0, network.stores_t.e, network.loads_t.p],axis=1)
df.plot(rot=45)
network.stores_t.e.plot(rot=45)
#%%
df.index.names = ['Datetime']
df

# %% creates a folder to save the files
use_case_name=inputs2['use_case_name']['Bus'][0]
timestamp=inputs2['timestamp']['Bus'][0]
os.makedirs(f"./results/{use_case_name}/{timestamp}")
os.makedirs(f"./results/{use_case_name}/{timestamp}/inputs")
os.makedirs(f"./results/{use_case_name}/{timestamp}/outputs")
#%%
df.to_csv(f"./results/{use_case_name}/{timestamp}/outputs/output_series.csv",index=True)  
statistics.to_csv(f"./results/{use_case_name}/{timestamp}/outputs/statistics.csv") 
inputs2.to_csv(f"./results/{use_case_name}/{timestamp}/inputs/inputs.csv")
