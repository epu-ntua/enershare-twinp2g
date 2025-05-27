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
from database_upload_csv import upload_csv, get_table
from dotenv import load_dotenv
import re

#   
def fillna(file):
    file=file.fillna(method='pad')
    file=file.fillna(method='backfill')
    return file

def dates(file):
    start='2018-07-01 01:00:00'
    end='2018-07-25 23:00:00'
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    start=start.strftime("%Y-%m-%d %H:%M:%S")
    end=end.strftime("%Y-%m-%d %H:%M:%S")
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
    date_format = "%Y-%m-%d %H:%M:%S"
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
    load_dotenv()
    url = os.environ.get('CONNECTOR_URL')
    jwt_token = os.environ.get('JWT_TOKEN')
    forward_id = os.environ.get('FORWARD_ID')
    forward_sender = os.environ.get('FORWARD_SENDER')

    headers = {
        'Authorization': 'Bearer ' + jwt_token,
        'Forward-Id': forward_id,         # reciever connector ID
        'Forward-Sender': forward_sender      # Sender connector ID
    }
    response = requests.get(url+endpoint, headers=headers, params=params)

    # Check if request was successful (status code 200)
    if response.status_code == 200:
        try:
            raw_data = response.text
            cleaned_data = re.sub(r'[\x00-\x1F\x7F]', '', raw_data)
            data = json.loads(cleaned_data)
            
            # data = response.json() 
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            df=df.sort_index() 
            df.index = pd.to_datetime(df.index)
            df.index = df.index.strftime('%Y-%m-%d %H:%M:%S')
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
def network_execute(inputs_source):
    #%matplotlib inline

    logging.basicConfig(level="INFO")
    network = pypsa.Network()
    if inputs_source=='inputs_deeptsf':
        inputs2=get_table('crete_fc_uc.inputs')
    elif inputs_source=='inputs_TwinP2G':
        inputs2=pd.read_csv('data/data_inputs2.csv')
    # inputs2=pd.read_csv('data/data_inputs2.csv')
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
        bus=inputs2['bus']['Bus'].iloc[i]
        longitude=inputs2['longitude']['Bus'].iloc[i]
        latitude=inputs2['latitude']['Bus'].iloc[i]
        network.add("Bus",name=bus, carrier=carrier, x=longitude, y=latitude)
    network.buses
    #
    # ## Lines
    #
    for i in range(lines):
        bus0 = inputs2['from_bus']['Line'].iloc[i]
        bus1 = inputs2['to_bus']['Line'].iloc[i]
        r=inputs2['series_reactance']['Line'].iloc[i]
        x=inputs2['series_resistance']['Line'].iloc[i]
        network.add("Line", f"Line {bus0} - {bus1}", bus0=bus0, bus1=bus1, r=r, x=x, s_nom_extendable=True)
    network.lines
    # 
    # ## Loads
    #
    for i in range(loads):
        bus = inputs2['bus']['Load'].iloc[i]
        carrier=inputs2.loc['Load'].index[i]
        load_data_source_type=inputs2['input_series_source_type']['Load'].iloc[i]
        if load_data_source_type=='csv file':
            load_data_uri=inputs2['input_series_source_uri']['Load'].iloc[i]
            data_load=read_csv(f'data/{load_data_uri}', network)
            network.set_snapshots(data_load.index)
            p_set=np.array(data_load['Value'])
        elif load_data_source_type=='TimescaleDB':
            load_data_uri_data=inputs2['input_series_source_uri']['Load'].iloc[i]
            if carrier=='AC':
                endpoint = 'total_load_actual'
                params={
                    'select': inputs2['input_series_source_uri']['Load'].iloc[i]
                    }  
                #Added to filter the data from the dataspace (DS params not working)
                match = re.search(r'timestamp\.gte\.([0-9\-]+),timestamp\.lte\.([0-9\-]+)', load_data_uri_data)
                if match:
                    start_date = match.group(1)
                    end_date = match.group(2)
                    # print("Start:", start_date)
                    # print("End:", end_date)
                else:
                    print("No dates found")    
                data_load=calls(endpoint,params)
                data_load = data_load[start_date:end_date]                          
                network.set_snapshots(data_load.index)            
                p_set=np.array(data_load['actual_load'])
            elif carrier == 'Natural Gas':
                endpoint= 'desfa_flows_hourly_archive'
                params={
                    'select': inputs2['input_series_source_uri']['Load'].iloc[i]
                    }
                #Added to filter the data from the dataspace (DS params not working)
                match = re.search(r'timestamp\.gte\.([0-9\-]+),timestamp\.lte\.([0-9\-]+),point_id\.eq\.([A-Z0-9_]+)', load_data_uri_data)
                if match:
                    start_date = match.group(1)
                    end_date = match.group(2)
                    exit_point = match.group(3) 
                    # print("Start:", start_date)
                    # print("End:", end_date)
                else:
                    print("No dates found")
                data_load=calls(endpoint,params)
                data_load = data_load[start_date:end_date]
                data_load = data_load[data_load['point_id'] == exit_point]
                network.set_snapshots(data_load.index)
            # if carrier=='AC':
                
            # elif carrier=='Natural Gas':
                p_set=np.array(data_load['value'])
        
        elif load_data_source_type=='deepTSF':
            load_data_uri=inputs2['input_series_source_uri']['Load'].iloc[i]
            data_load=get_table(load_data_uri)
            data_load.set_index(['Datetime'], inplace=True)
            data_load.index = pd.to_datetime(data_load.index)
            data_load.index = data_load.index.strftime('%Y-%m-%d %H:%M:%S')
            data_load = data_load.rename_axis('snapshot')
            network.set_snapshots(data_load.index)
            p_set=np.array(data_load['Value'])

        network.add("Load", f"Load {bus}", bus=bus, carrier=carrier, p_set=p_set)    
    network.loads
    investment_period=investment_period_count(data_load)
    # 
    # ## Generators
    #
    for i in range(generators): 
        bus=inputs2['bus']['Generator'].iloc[i]
        generator_data_source_type=inputs2['input_series_source_type']['Generator'].iloc[i]
        carrier=inputs2.loc['Generator'].index[i]
        if carrier=='Solar':
            # p_min_pu=0    
            if generator_data_source_type =='csv file':
                pv_data=inputs2['input_series_source_uri']['Generator'].iloc[i]
                data_pvprod=read_csv(f'data/{pv_data}', network)
                p_max_pu_value = np.array(data_pvprod['Value'])
            elif generator_data_source_type=='pvlib':
                data_pvprod=pvlib_simulation(data_load)
                p_max_pu_value = np.array(data_pvprod['Value'])
            elif generator_data_source_type=='deepTSF':
                pv_data=inputs2['input_series_source_uri']['Generator'].iloc[i]
                data_pvprod=get_table(pv_data)
                data_pvprod.set_index(['Datetime'], inplace=True)
                p_max_pu_value = np.array(data_pvprod['Value'])
            else: 
                endpoint = 'actual_generation_per_type'  
                params={
                    'select': inputs2['input_series_source_uri']['Generator'].iloc[i]
                    }
                #Added to filter the data from the dataspace (DS params not working)
                pv_data=inputs2['input_series_source_uri']['Generator'].iloc[i]
                match = re.search(r'timestamp\.gte\.([0-9\-]+),timestamp\.lte\.([0-9\-]+)', pv_data)
                if match:
                    start_date = match.group(1)
                    end_date = match.group(2)
                    # print("Start:", start_date)
                    # print("End:", end_date)
                else:
                    print("No dates found")
                data_pvprod=calls(endpoint,params)
                data_pvprod = data_pvprod[start_date:end_date]
                p_max_pu_value=np.array(data_pvprod['solar'])
            p_max_pu_value[p_max_pu_value < 0] = 0

        elif carrier=='Wind':
            # p_min_pu=0
            if generator_data_source_type =='csv file':
                wind_data_source_uri=inputs2['input_series_source_uri']['Generator'].iloc[i]
                data_windprod=read_csv(f'data/{wind_data_source_uri}', network)
                p_max_pu_value = np.array(data_windprod['Value'])
            elif generator_data_source_type=='deepTSF':
                wind_data_source_uri=inputs2['input_series_source_uri']['Generator'].iloc[i]
                data_windprod=get_table(wind_data_source_uri)
                data_windprod.set_index(['Datetime'], inplace=True)
                p_max_pu_value = np.array(data_windprod['Value'])
            else: 
                endpoint = 'actual_generation_per_type'  
                params={
                    'select': inputs2['input_series_source_uri']['Generator'].iloc[i]
                    }
                #Added to filter the data from the dataspace (DS params not working)
                wind_data_source_uri=inputs2['input_series_source_uri']['Generator'].iloc[i]
                match = re.search(r'timestamp\.gte\.([0-9\-]+),timestamp\.lte\.([0-9\-]+)', wind_data_source_uri)
                if match:
                    start_date = match.group(1)
                    end_date = match.group(2)
                    # print("Start:", start_date)
                    # print("End:", end_date)
                else:
                    print("No dates found")
                data_windprod=calls(endpoint,params)
                data_windprod = data_windprod[start_date:end_date]
                p_max_pu_value=np.array(data_windprod['wind_onshore'])
            p_max_pu_value[p_max_pu_value < 0] = 0        
        else:
            # p_min_pu=0.3
            p_max_pu_value = 1  
        network.add("Carrier", name=carrier)
        network.add(
            "Generator",
            f'Generator {bus} {carrier}',
            bus=bus,
            carrier=carrier,  
            p_nom=float(inputs2['p_nom']['Generator'].iloc[i]),  
            # p_min_pu=p_min_pu,
            p_nom_extendable=False,
            p_max_pu=p_max_pu_value,
            capital_cost=float(inputs2['capital_cost']['Generator'].iloc[i]),  
            marginal_cost=float(inputs2['marginal_cost']['Generator'].iloc[i]) 
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
        bus0=inputs2['from_bus']['Link'].iloc[i]
        bus1=inputs2['to_bus']['Link'].iloc[i]
        carrier = inputs2.loc['Link'].index[i]
        efficiency=inputs2['efficiency']['Link'].iloc[i]

        network.add("Carrier", name=carrier)
        network.add(
            "Link",
            name=f'{carrier} {bus0} - {bus1}',
            bus0=bus0,
            bus1=bus1,
            carrier=carrier,
            efficiency=efficiency,
            p_nom=float(inputs2['p_nom']['Link'].iloc[i]),  
            p_nom_extendable=True,
            capital_cost=float(inputs2['capital_cost']['Link'].iloc[i]) // (20 / investment_period), 
            marginal_cost=float(inputs2['marginal_cost']['Link'].iloc[i]),  
        )
    network.links
    #   [markdown]
    # ## Stores
    # 
    for i in range(stores):
        bus=inputs2['bus']['Store'].iloc[i]
        carrier = inputs2.loc['Store'].index[i]
        network.add("Carrier", name=carrier)
        network.add(
            "Store",
            name=f'Store {bus}',
            bus=bus,
            carrier=carrier,
            e_nom=float(inputs2['p_nom']['Store'].iloc[i]),  
            e_cyclic=True,
            e_nom_extendable=True,
            capital_cost=float(inputs2['capital_cost']['Store'].iloc[i]) // (25 / investment_period),  
            marginal_cost=float(inputs2['marginal_cost']['Store'].iloc[i]) 
        )
    network.stores

    #   [markdown]
    # ## Ροη φορτιου και βελτιστοποιηση

    #  
    # network.optimize(network.snapshots, solver_name="glpk", solver_options={})
    try:
        network.optimize(network.snapshots, solver_name="glpk", solver_options={})
    except AttributeError as e:
        print(f"Optimization failed: {e}")
    #   [markdown]
    # ## Results

    #  
    #total system cost for the snapshots optimised
    # network.objective 

    #  
    network.statistics().round(2)

    #  
    statistics=network.statistics().round(2)

    #  
    carrier_colors = {
        'AC': 'red',
        'hydrogen': 'green',
        'DC': 'black',
        'heat': 'yellow',
        'gas': 'blue',
    }

    bus_colors = network.buses.carrier.map(carrier_colors)

    fig = network.iplot(
        bus_sizes=20,
        bus_colors=bus_colors,
        line_widths=2.7,
        link_widths=2,
        iplot=False
    )
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
    use_case_name=inputs2['use_case_name']['Bus'].iloc[0]
    timestamp=inputs2['timestamp']['Bus'].iloc[0]
    output_path = f"./results/{use_case_name}/{timestamp}/outputs"
    input_path = f"./results/{use_case_name}/{timestamp}/inputs"

    os.makedirs(output_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)

    df.to_csv(f"{output_path}/output_series.csv", index=True)
    statistics.to_csv(f"{output_path}/statistics.csv")
    inputs2.to_csv(f"{input_path}/inputs.csv")
    if inputs_source=='inputs_deeptsf':
        return use_case_name, timestamp, output_path, input_path
    elif inputs_source=='inputs_TwinP2G':
        return use_case_name, timestamp, output_path, input_path, fig, network.buses, network.lines, network.links

async def upload_results(use_case_name, timestamp, output_path, input_path, schema_name):
    # schema_name = 'twinp2g_results'

    table_files = {
        'output_series': os.path.join(output_path, "output_series.csv"),
        'statistics': os.path.join(output_path, "statistics.csv"),
        'inputs': os.path.join(input_path, "inputs.csv")
    }
    results = []

    for table_name, csv_file in table_files.items():
        if schema_name=='crete_fc_uc':
            new_table_name = f"{use_case_name}_{table_name}"
        else:
            new_table_name = f"{use_case_name}_{timestamp}_{table_name}"
        result = await upload_csv(csv_file=csv_file, table_name=new_table_name, schema_name=schema_name)
        results.append(result)
    
    for result in results:
        print(result)

#  
if __name__ == "__main__":
    output_path, input_path = network_execute()
    asyncio.run(upload_results(output_path, input_path))