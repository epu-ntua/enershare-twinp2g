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

# %%
#%matplotlib inline
logging.basicConfig(level="INFO")

# %% [markdown]
# ## Δεδομένα Παραγωγής και Κατανάλωσης

# %% 
def fillna(file):
    file=file.fillna(method='pad')
    file=file.fillna(method='backfill')
    return file

def dates(file):
    start='2019-01-01'
    end='2020-09-30'
    file=file[start:end]
    return file

#%% Read CSV from 'input_series_source_uri'
def read_csv(data):
    data_csv = pd.read_csv(data, parse_dates=True)
    data_csv.set_index(['Datetime'], inplace=True)
    data_csv=fillna(data_csv)
    data_csv=dates(data_csv) 
    network.set_snapshots(data_csv.index)
    print(data_csv)
    return data_csv 

# %% [markdown]
# ## Προσομοίωση Δικτύου
# %%
inputs2=pd.read_csv('data_inputs2.csv')
inputs2.set_index(['Component','Carrier'],inplace=True)
inputs2
# %%
network = pypsa.Network()

# %%
buses=inputs2.index.get_level_values('Component').value_counts()['Generator']
lines=inputs2.index.get_level_values('Component').value_counts()['Line']
loads=inputs2.index.get_level_values('Component').value_counts()['Load']

#%%
for i in range(buses):
    network.add("Bus",f"Bus {i}")
network.buses

#%%
for i in range(lines):
    bus0 = inputs2['From Bus']['Line'][i]
    bus1 = inputs2['To Bus']['Line'][i]
    network.add("Line", f"Line {i}", bus0=bus0, bus1=bus1, r=0.01, x=0.1, s_nom_extendable=True)
network.lines

#%%
for i in range(loads):
    bus = inputs2['Bus']['Load'][i]
    load_data_source_type=inputs2['input_series_source_type']['Load'][i]
    if load_data_source_type=='csv file':
        load_data_uri=inputs2['input_series_source_uri']['Load'][i]
        data_load=read_csv(load_data_uri)
        p_set=np.array(data_load['GR_load'])
    network.add("Load", f"Load {i}", bus=bus, p_set=p_set)    
network.loads

#%%
for i in range(buses): 
    generator_data_source_type=inputs2['input_series_source_type']['Generator'][i]
    carrier=inputs2.loc['Generator'].index[i]

    if carrier=='Solar':  
        if generator_data_source_type =='csv file':
            pv_data=inputs2['input_series_source_uri']['Generator'][i]
            data_pvprod=read_csv(pv_data)
            p_max_pu_value = np.array(data_pvprod['GR_solar_generation'])
        else: #if generator_data_source_type=='pvlib' or generator_data_source_type=='TimescaleDB'
            p_max_pu_value=1  

    if carrier=='Wind':
        if generator_data_source_type =='csv file':
            wind_data_source_uri=inputs2['input_series_source_uri']['Generator'][i]
            data_windprod=read_csv(wind_data_source_uri)
            p_max_pu_value = np.array(data_windprod['GR_wind_onshore_generation_actual'])
        else: #if generator_data_source_type=='TimescaleDB'
            p_max_pu_value=1  
    
    else:
        p_max_pu_value = 1  
    
    network.add(
        "Generator",
        f'Generator {i}',
        bus=inputs2['Bus']['Generator'][i],
        carrier=carrier,  
        p_nom=float(inputs2['Pnom']['Generator'][i]),  
        p_nom_extendable=False,
        p_max_pu=p_max_pu_value,
        capital_cost=float(inputs2['Capital Cost']['Generator'][i]),  
        marginal_cost=float(inputs2['Marginal Cost']['Generator'][i]) 
    )
network.generators

# %% [markdown]
# ## Προσωμοίωση Power to Gas  

# %%
network.add("Bus", "Hydrogen Bus", carrier="hydrogen")

#%%
links=inputs2.index.get_level_values('Component').value_counts()['Link']
stores = inputs2.index.get_level_values('Component').value_counts()['Store']

#%%
for i in range(links):
    carrier = inputs2.loc['Link'].index[i]
    if carrier == 'Electrolysis':
        efficiency = 0.7
    elif carrier == 'Fuel Cell':
        efficiency = 0.6
    
    network.add(
        "Link",
        name=carrier,
        bus0=inputs2['From Bus']['Link'][i],
        bus1=inputs2['To Bus']['Link'][i],
        carrier=carrier,
        efficiency=efficiency,
        p_nom=float(inputs2['Pnom']['Link'][i]),  
        p_nom_extendable=True,
        capital_cost=float(inputs2['Capital Cost']['Link'][i]) // (25 / float(inputs2['Investment Period']['Load'][0])), 
        marginal_cost=float(inputs2['Marginal Cost']['Link'][i]),  
    )
network.links

#%%
# Add H2 store
for i in range(stores):
    carrier = inputs2.loc['Store'].index[i]
    
    network.add(
        "Store",
        name=carrier,
        bus=inputs2['Bus']['Store'][i],
        carrier=carrier,
        e_nom=float(inputs2['Pnom']['Store'][i]),  
        e_cyclic=True,
        e_nom_extendable=True,
        capital_cost=float(inputs2['Capital Cost']['Store'][i]) // (25 / float(inputs2['Investment Period']['Load'][0])),  
        marginal_cost=float(inputs2['Marginal Cost']['Store'][i]) 
    )
network.stores

# %% [markdown]
# ## Ροη φορτιου και βελτιστοποιηση
# Χρησιμοποείται η εντολή network.optimize() για να τρέξει το σύστημα και να βελτιστοποιηθεί το αποτέλεσμα. Ο χρόνος εκτέλεσης ειναι 21min 7sec.

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
# network.export_to_csv_folder('network_components1')

# %%
network.iplot()

# %% [markdown]
# Οι δύο πρωτες γραφικές αφορούν το σύστημα για ολόκληρο το διάστημα της προσωμόιωσης (5 χρονια, 9 μηνες) και παρατηρούμε ότι το Power to Gas σύστημα δεν λειτουργει.\
# Αυτο συμβαίνει διότι με τις σημερινές τιμές των στοιχείων το σύστημα χρησιμοποιεί την ενέργεια απο την γεννητρια diesel ακομα και αν το λειτουργικο της κοστος της ειναι πιο ακριβό, αφού το κόστος κεφαλαίου του ηλεκτρολύτη και του fuel cell ειναι πολυ ακριβά.

# %%
df=pd.concat([network.generators_t.p, network.links_t.p0, network.loads_t.p],axis=1)
df.plot(rot=45)
network.stores_t.e.plot(rot=45)

# %% [markdown]
# Στις παρακάτω γραφικές μπορούμε να δούμε την απόκριση του συστηματος για το διάστημα **'2020-07-22':'2020-07-25'** όπου και είναι εμφανές ότι η γεννήτρια λειτουργεί τα βράδια, που δεν υπάρχει ΦΒ παραγωγή, ώστε να καλύψει το φορτίο, ενώ τα μεσημέρια η γεννήτρια λειτουργεί στο 30% ονομαστικής ισχύος για λόγους ευστάθειας και το ΦΒ πάρκο παράγει ενέργεια και η ενέργεια αυτή προτιμάται καθώς το λειτουργικό της κόστος είναι πιο φθηνό.

# %%
df['2020-07-22':'2020-07-25'].plot(rot=45)
network.stores_t.e['2020-07-22':'2020-07-25'].plot(rot=45)


# %% creates a folder to save the files
use_case_name=inputs2['use_case_name']['Generator'][0]
os.makedirs(f"./results/{use_case_name}")
# Results for generators, links, loads
df.to_csv(f"./results/{use_case_name}/results.csv",index=True)  
statistics.to_csv(f"./results/{use_case_name}/statistics.csv") 
stores=network.stores_t.e
stores.to_csv(f"./results/{use_case_name}/stores.csv")
inputs2.to_csv(f"./results/{use_case_name}/inputs.csv")
