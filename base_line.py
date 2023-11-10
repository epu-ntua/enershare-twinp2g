# %%
import numpy as np
import pypsa
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = [15, 5]
from pyomo.environ import Constraint
import logging

# %%
#%matplotlib inline
logging.basicConfig(level="INFO")

# %% [markdown]
# ## Δεδομένα Παραγωγής και Κατανάλωσης

# %%
data=pd.read_csv("time_series_60min_singleindex.csv", parse_dates=True)
data.set_index(['utc_timestamp'], inplace=True)
gr_cols = [col for col in data.columns if col.startswith('GR_')]
data=data[gr_cols]
data=data['2015-01-01':'2020-09-31']
# data=data['2015-01-01':'2020-09-30']
data=data.fillna(method='pad')
data=data.fillna(method='backfill')
data_load=data['GR_load_actual_entsoe_transparency']/2000 #Υποθετω οτι ειναι για 10.000.000/2.000 = 5.000 άτομα
data_pvprod=data['GR_solar_generation_actual']/(2115/5)  
data_pvprod.describe()

# %%
data_load.describe()

# %%
data.head()

# %% [markdown]
# ## Προσομοίωση Δικτύου

# %%
network = pypsa.Network()
network.set_snapshots(data.index)
inputs=pd.read_csv('data_inputs.csv', index_col=['carriers'])
inputs
# %%
inputs['Pnom']['Diesel_Gen']
# %%
#Add buses and carriers to the network
network.add("Bus", "Diesel", carrier='AC')
network.add("Carrier", "diesel")  #diesel=1.27 tonnes/MWh 

network.add("Bus", "Solar", carrier="AC")
network.add("Carrier", "solar")

#Add lines
network.add("Line","Line",bus0="Diesel",bus1="Solar",r=0.01,x=0.1, s_nom_extendable=True)

#Add generators
network.add(
    "Generator",
    "Diesel Gen",
    bus="Diesel",
    carrier="diesel",
    p_nom=inputs['Pnom']['Diesel_Gen'], #MW
    p_nom_extendable=False,
    p_min_pu=0.3,
    control="Slack",
    capital_cost=0, #Capital cost of extending p_nom by 1 MW (€/MW)
    marginal_cost=305, #diesel:0.2€/kWh, CO2 emissions: 80-85€/tCO2*1.27 tonnes/MWh = 105€/MWh (€/MWh)
    )

network.add(
    "Generator",
    "PV Park",
    bus="Solar",
    carrier="solar",
    control="PV", 
    p_nom=inputs['Pnom']['PV_Park'], #MW 
    p_nom_extendable=False,
    p_max_pu=np.array(data_pvprod),
    capital_cost=0, #Capital cost of extending p_nom by 1 MW (€/MW)
    marginal_cost=24 # 20-60€/MWh
    )

#Add loads
network.add("Load", "load 1", bus="Solar", p_set=np.array((data_load))) 

# %% [markdown]
# ## Ροή φορτίου και Βελτιστοποίηση
# Χρησιμοποείται η εντολή network.optimize() για να τρέξει το σύστημα και να βελτιστοποιηθεί το αποτέλεσμα. Ο χρόνος εκτέλεσης ειναι 20sec.

# %%
network.optimize(network.snapshots, solver_name="glpk", solver_options={})

# %% [markdown]
# ## Αποτελέσματα και Σχόλια
# Παρακάτω εμφανίζονται τα δεδομένα της βελτιστοποίησης οπως είναι: το objective function, το μονογραμμικο διάγραμμα απο το network.iplot() της pypsa και γραφικές παραστάσεις στις οποίες απεικονίζονται η παραγωγή και η ζήτηση.

# %%
network.objective

# %%
network.iplot()

# %% [markdown]
# Η πρωτη γραφικη αφορα το σύστημα για ολόκληρο το διάστημα της προσωμόιωσης (5 χρονια, 9 μηνες), ενώ η δεύτερη για το διάστημα **'2020-07-22':'2020-07-25'**.\
# Είναι εμφανές ότι η γεννήτρια λειτουργεί τα βράδια, που δεν υπάρχει ΦΒ παραγωγή, ώστε να καλύψει το φορτίο, ενώ τα μεσημέρια η γεννήτρια λειτουργεί στο 30% ονομαστικής ισχύος για λόγους ευστάθειας και το ΦΒ πάρκο παράγει ενέργεια και η ενέργεια αυτή προτιμάται καθώς το λειτουργικό της κόστος είναι πιο φθηνό.
# 

# %%
df=pd.concat([network.generators_t.p, network.loads_t.p],axis=1)
df.plot(rot=45)

# %%
df.to_csv('results/base_line_results.csv', index=True)

# %%
base_line_statistics=network.statistics()
base_line_statistics.to_csv('results/base_line_statistics.csv')
# %%
df['2020-07-22':'2020-07-25'].plot(rot=45)


