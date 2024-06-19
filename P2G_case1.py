#  
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
import time
import math
from pvlib_folder.pvlibdata import pvlib_simulation
import requests
import json
import asyncio
from database_upload_csv import upload_csv
#   
def fillna(file):
    file=file.fillna(method='pad')
    file=file.fillna(method='backfill')
    return file

def dates(file):
    start='2018-07-01 01:00:00+00:00'
    end='2018-07-25 23:00:00+00:00'
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    start=start.strftime("%Y-%m-%d %H:%M:%S+00:00")
    end=end.strftime("%Y-%m-%d %H:%M:%S+00:00")
    file=file[start:end]
    return file

#  Read CSV from 'input_series_source_uri'
def read_csv(data, network):
    data_csv = pd.read_csv(data, parse_dates=True)
    data_csv.set_index(['Datetime'], inplace=True)
    data_csv=fillna(data_csv)
    # data_csv=dates(data_csv) 
    return data_csv 
# 
def components_count(carrier, inputs2):
    try:
        component=inputs2.index.get_level_values('Component').value_counts()[carrier]
    except KeyError:
        component=0
    return component

# 
def days_between_dates(dt1, dt2):
    date_format = "%Y-%m-%d %H:%M:%S+00:00"
    a = time.mktime(time.strptime(dt1, date_format))
    b = time.mktime(time.strptime(dt2, date_format))
    delta = abs(b - a)
    return delta / (60 * 60 * 24)  # Convert seconds to days

#  Calculates the investment period from load_data.csv
def investment_period_count(data_load):
    start=data_load.index[0]
    end=data_load.index[-1]
    num_days = days_between_dates(start, end) 
    investment_period = (num_days / 365)  
    return investment_period

def calls(endpoint,params):
    df=None
    url = 'https://enershare.epu.ntua.gr/consumer-data-app/openapi/12.0.2/'    # https://<baseurl>/<data-app-path>/openapi/<beckend-service-version>/
    jwt_token = 'APIKEY-sgqgCPJWgQjmMWrKLAmkETDE' 

    headers = {
        'Authorization': 'Bearer' + jwt_token,
        'Forward-Id': 'urn:ids:enershare:connectors:NTUA:Provider:Pilot4',         # reciever connector ID
        'Forward-Sender': 'urn:ids:enershare:connectors:NTUA:Consumer:ConsumerAgent'      # Sender connector ID
    }
    response = requests.get(url+endpoint, headers=headers, params=params)

    # Check if request was successful (status code 200)
    if response.status_code == 200:
        try:
            data = response.json() 
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df=df.sort_index() 
            df.index = pd.to_datetime(df.index)
            df.index = df.index.strftime('%Y-%m-%d %H:%M:%S+00:00')
            df = df.rename_axis('snapshot')
        except ValueError:  
            print("Response content is not valid JSON")
            print(response.text)
    else:
        print(f"Request failed with status code: {response.status_code}")
        print("Response text:", response.text)
    return df
#   [markdown]
# ## Network Simulation
#  
def network_execute():
    #%matplotlib inline

    logging.basicConfig(level="INFO")
    network = pypsa.Network()
    inputs2=pd.read_csv('data/data_inputs2.csv')
    inputs2.set_index(['Component','carrier'],inplace=True)
    inputs2

    # Number of Components
    buses=components_count('Bus', inputs2)
    generators=components_count('Generator', inputs2)
    lines=components_count('Line', inputs2)
    loads=components_count('Load', inputs2)

    # ## Buses
    network.add("Carrier", 'AC')
    # 
    for i in range(buses):
        carrier=inputs2.loc['Bus'].index[i]
        bus=inputs2['bus']['Bus'][i]
        network.add("Bus",name=bus, carrier=carrier)
    network.buses
    #
    # ## Lines
    #
    for i in range(lines):
        bus0 = inputs2['from_bus']['Line'][i]
        bus1 = inputs2['to_bus']['Line'][i]
        r=inputs2['series_reactance']['Line'][i]
        x=inputs2['series_resistance']['Line'][i]
        network.add("Line", f"Line {bus0} - {bus1}", bus0=bus0, bus1=bus1, r=r, x=x, s_nom_extendable=True)
    network.lines
    # 
    # ## Loads
    #
    for i in range(loads):
        bus = inputs2['bus']['Load'][i]
        carrier=inputs2.loc['Load'].index[i]
        load_data_source_type=inputs2['input_series_source_type']['Load'][i]
        if load_data_source_type=='csv file':
            load_data_uri=inputs2['input_series_source_uri']['Load'][i]
            data_load=read_csv(f'data/{load_data_uri}', network)
            network.set_snapshots(data_load.index)
            p_set=np.array(data_load['GR_load'])
        else:
            if carrier=='AC':
                endpoint = 'total_load_actual'
            elif carrier == 'Natural Gas':
                endpoint= 'desfa_flows_hourly_archive'
            params={
                'select': inputs2['input_series_source_uri']['Load'][i]
                }
            data_load=calls(endpoint,params)
            network.set_snapshots(data_load.index)
            p_set=np.array(data_load['actual_load'])

        network.add("Load", f"Load {bus}", bus=bus, carrier=carrier, p_set=p_set)    
    network.loads
    investment_period=investment_period_count(data_load)
    # 
    # ## Generators
    #
    for i in range(generators): 
        bus=inputs2['bus']['Generator'][i]
        generator_data_source_type=inputs2['input_series_source_type']['Generator'][i]
        carrier=inputs2.loc['Generator'].index[i]
        if carrier=='Solar':
            # p_min_pu=0    
            if generator_data_source_type =='csv file':
                pv_data=inputs2['input_series_source_uri']['Generator'][i]
                data_pvprod=read_csv(f'data/{pv_data}', network)
                p_max_pu_value = np.array(data_pvprod['GR_solar_generation'])
            elif generator_data_source_type=='pvlib':
                data_pvprod=pvlib_simulation(data_load)
                p_max_pu_value = np.array(data_pvprod['GR_solar_generation'])
            else: 
                endpoint = 'actual_generation_per_type'  
                params={
                    'select': inputs2['input_series_source_uri']['Generator'][i]
                    }
                data_pvprod=calls(endpoint,params)
                p_max_pu_value=np.array(data_pvprod['solar'])

        elif carrier=='Wind':
            # p_min_pu=0
            if generator_data_source_type =='csv file':
                wind_data_source_uri=inputs2['input_series_source_uri']['Generator'][i]
                data_windprod=read_csv(f'data/{wind_data_source_uri}', network)
                p_max_pu_value = np.array(data_windprod['GR_wind_onshore_generation_actual'])
            else: 
                endpoint = 'actual_generation_per_type'  
                params={
                    'select': inputs2['input_series_source_uri']['Generator'][i]
                    }
                data_windprod=calls(endpoint,params)
                p_max_pu_value=np.array(data_windprod['wind_onshore'])
        
        else:
            # p_min_pu=0.3
            p_max_pu_value = 1  
        network.add("Carrier", name=carrier)
        network.add(
            "Generator",
            f'Generator {bus}',
            bus=bus,
            carrier=carrier,  
            p_nom=float(inputs2['p_nom']['Generator'][i]),  
            # p_min_pu=p_min_pu,
            p_nom_extendable=False,
            p_max_pu=p_max_pu_value,
            capital_cost=float(inputs2['capital_cost']['Generator'][i]),  
            marginal_cost=float(inputs2['marginal_cost']['Generator'][i]) 
        )
    network.generators

    #   [markdown]
    # ##  Power to Gas  

    #  Number of Links and Stores
    links=components_count('Link', inputs2)
    stores=components_count('Store', inputs2)
    #   [markdown]
    # ## Links
    # 
    for i in range(links):
        bus0=inputs2['from_bus']['Link'][i]
        bus1=inputs2['to_bus']['Link'][i]
        carrier = inputs2.loc['Link'].index[i]
        efficiency=inputs2['efficiency']['Link'][i]

        network.add("Carrier", name=carrier)
        network.add(
            "Link",
            name=f'{carrier} {bus0} - {bus1}',
            bus0=bus0,
            bus1=bus1,
            carrier=carrier,
            efficiency=efficiency,
            p_nom=float(inputs2['p_nom']['Link'][i]),  
            p_nom_extendable=True,
            capital_cost=float(inputs2['capital_cost']['Link'][i]) // (20 / investment_period), 
            marginal_cost=float(inputs2['marginal_cost']['Link'][i]),  
        )
    network.links
    #   [markdown]
    # ## Stores
    # 
    for i in range(stores):
        bus=inputs2['bus']['Store'][i]
        carrier = inputs2.loc['Store'].index[i]
        network.add("Carrier", name=carrier)
        network.add(
            "Store",
            name=f'Store {bus}',
            bus=bus,
            carrier=carrier,
            e_nom=float(inputs2['p_nom']['Store'][i]),  
            e_cyclic=True,
            e_nom_extendable=True,
            capital_cost=float(inputs2['capital_cost']['Store'][i]) // (25 / investment_period),  
            marginal_cost=float(inputs2['marginal_cost']['Store'][i]) 
        )
    network.stores

    #   [markdown]
    # ## Ροη φορτιου και βελτιστοποιηση

    #  
    network.optimize(network.snapshots, solver_name="glpk", solver_options={})

    #   [markdown]
    # ## Results

    #  
    #total system cost for the snapshots optimised
    network.objective 

    #  
    network.statistics().round(2)

    #  
    statistics=network.statistics().round(2)

    #  
    # network.iplot()

    #  
    if links==0 and stores==0:
        df=pd.concat([network.generators_t.p, network.loads_t.p],axis=1)
    else:    
        df=pd.concat([network.generators_t.p, network.links_t.p0, network.stores_t.e, network.loads_t.p],axis=1)
        network.stores_t.e.plot(rot=45)
    df.plot(rot=45)
    # 
    df.index.names = ['Datetime']
    df

    #   creates a folder to save the files
    use_case_name=inputs2['use_case_name']['Bus'][0]
    timestamp=inputs2['timestamp']['Bus'][0]
    output_path = f"./results/{use_case_name}/{timestamp}/outputs"
    input_path = f"./results/{use_case_name}/{timestamp}/inputs"

    os.makedirs(output_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)

    df.to_csv(f"{output_path}/output_series.csv", index=True)
    statistics.to_csv(f"{output_path}/statistics.csv")
    inputs2.to_csv(f"{input_path}/inputs.csv")

    return output_path, input_path

async def upload_results(output_path, input_path):
    schema_name = 'twinp2g_results'

    table_files = {
        'output_series': os.path.join(output_path, "output_series.csv"),
        'statistics': os.path.join(output_path, "statistics.csv"),
        'inputs': os.path.join(input_path, "inputs.csv")
    }
    results = []

    for table_name, csv_file in table_files.items():
        result = await upload_csv(csv_file=csv_file, table_name=table_name, schema_name=schema_name)
        results.append(result)
    
    for result in results:
        print(result)

#  
if __name__ == "__main__":
    output_path, input_path = network_execute()
    asyncio.run(upload_results(output_path, input_path))