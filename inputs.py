import streamlit as st
import pandas as pd
import numpy as np
import pypsa
import time
import os
import datetime 
from streamlit import session_state as ss
import plotly.graph_objects as go

network = pypsa.Network()
st.set_page_config(layout='wide', initial_sidebar_state='expanded')

st.title('Twin P2G')

# Set session_state keys = 0
count_vars = ['b1_count', 'b2_count', 'b3_count', 'b4_count', 'b5_count', 'b6_count']
for var in count_vars:
    if var not in ss:
        ss[var] = 0

def count(key):
    ss[key] += 1
    ss[key] %= 2

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')

def time_convert(sec):
    mins = sec // 60
    sec = sec % 60
    hours = mins // 60
    mins = mins % 60
    st.write('Time Lapsed = {0}:{1}:{2}'.format(int(hours),int(mins),sec))


def list_csv_files(folder_path):
    csv_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    return csv_files

def selected_dates(start,end):
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    start=start.strftime('%Y-%m-%d %H:%M:%S+00:00')
    end=end.strftime('%Y-%m-%d %H:%M:%S+00:00')    
    return(start,end)

def validate_date_format(date_str):
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S+00:00')
    except ValueError:
        raise ValueError('Incorrect date format. Please use YYYY-MM-DD.')

@st.cache_data
def plotly_chart_results(df):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col))
    # plot=st.plotly_chart(fig, use_container_width=True)
    return fig

@st.cache_data
def read_uploaded_csv(uploaded):
    df = pd.read_csv(uploaded, delimiter=',', parse_dates=True)
    return df

@st.cache_data
def read_output_csv(csv_file):
    df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
    return df


use_case=st.selectbox('Select your use case', options=('Your use case', 'See use cases'))

if use_case=='See use cases':
    # Set the default folder to 'results'
    default_folder = 'results'

    # Select a folder within 'results'
    selected_subfolder = st.sidebar.radio('Select a subfolder', os.listdir(default_folder))
    preferred_csv_file = 'inputs.csv'  

    st.write(f'Selected Subfolder: {selected_subfolder}')

    selected_subfolder_path = os.path.join(default_folder, selected_subfolder)

    csv_files = list_csv_files(selected_subfolder_path)

    if csv_files:
        csv_files.sort(key=lambda x: x == os.path.join(selected_subfolder_path, preferred_csv_file), reverse=True)

        st.write('CSV Files in Selected Subfolder:')
        for csv_file in csv_files:
            st.write(f'📄{csv_file}')
    else:
        st.warning('No CSV files found in the selected subfolder.')
    
    button3 = bool(ss.b3_count %2)
    button5 = bool(ss.b5_count %2)

    def submit_disabled():
        if button5:
            ss.b5_count=0
            ss.b3_count=0
            ss.b4_count=0
        return bool(ss.b3_count % 2)
    
    col = st.columns(6)
    col[0].button('Process Selected CSV Files', key='b3', on_click=count, args=('b3_count',), type='primary', disabled=submit_disabled())
    col[1].button('Stop', key='b5', on_click=count, args=('b5_count',))
    ss.b1_count = 0
    ss.b2_count = 0

    if button5:
        st.stop()

    if button3==False:
        ss.b4_count =0
    else:
        for csv_file in csv_files:
            st.write(f'Processing {csv_file}...')
            df=read_output_csv(csv_file)
            # df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
            if  csv_file.endswith(('statistics.csv' , 'inputs.csv')):
                st.write(df)
                st.divider()

            if  csv_file.endswith('output_series.csv'):
                tab1, tab2=st.tabs(['📈 Chart', '🗃 Data'])
                tab1.subheader('Components Chart')
                with tab1:
                    fig = plotly_chart_results(df)
                    st.plotly_chart(fig, use_container_width=True)
                    # plotly_chart_results(df)    
                tab2.subheader('Components Data')
                tab2.write(df)
                csv = convert_df(df)
                tab2.download_button(label='Download data', data=csv, file_name='df.csv', mime='text/csv')
                st.divider()                            
        col1, col2 = st.columns(2)
        start = col1.date_input('Start', datetime.date(2020, 7, 22))
        end = col2.date_input('End', datetime.date(2020, 7, 25))
        start,end=selected_dates(start,end)

        st.button('Process Selected Dates', key='b4', on_click=count, args=('b4_count',))        
        button4 = bool(ss.b4_count %2)

        if button4:
            for csv_file in csv_files:
                dff=read_output_csv(csv_file)
                # dff = pd.read_csv(csv_file,index_col=0, parse_dates=True)
                filtered_df = dff[(dff.index >= start) & (dff.index <= end)]
                if  csv_file.endswith('output_series.csv'):
                    tab1, tab2=st.tabs(['📈 Chart', '🗃 Data'])
                    with tab1:
                        fig = plotly_chart_results(filtered_df)
                        st.plotly_chart(fig, use_container_width=True)
                        # plotly_chart_results(filtered_df)    
                    tab2.write(filtered_df) 
                               
if use_case=='Your use case':

    st.text_input('Name your use case', key='use_case', placeholder='Name ie use case 1234')
    use_case_name=st.session_state.use_case

    if use_case_name=='':
        st.error('Provide a name!')
  
    with st.container(border=True):
        st.header('Buses')
        buses=st.number_input('Select your electrical network buses', min_value=1)
        col = st.columns(buses)
        bus=[]
        data_bus=[]
        j=0
        l=0
        
        for i in range(buses):
            st.subheader(f'Bus {i}')
            bus.append(f'Bus {i}')
            bus_carrier=st.selectbox(f'Select energy carrier for bus {i}', ('AC','DC','hydrogen','gas','heat'))

            bus_data = {
                'Component':'Bus',
                'carrier': bus_carrier,
                'bus': bus[i],
                'from_bus':None,
                'to_bus':None,
                'p_nom':None,
                'capital_cost':None,
                'marginal_cost':None,
                'input_series_source_type':None,
                'input_series_source_uri':None,
                'use_case_name':use_case_name,
                'investment_period':None,
                'efficiency':None,
                'timestamp':None
            }
            data_bus.append(bus_data) 
            st.divider()
    
    with st.container(border=True):
        st.header('Generators')
        generators=st.number_input('Select your generators', min_value=1)
        col = st.columns(generators)
        data_generator=[]

        for i in range(generators):
            st.subheader(f'Generator {i}')
            generator_bus=st.selectbox(f'Select bus for generator {i}', options=bus, key=f'generator_bus{i}')
            generator_carrier=st.selectbox(f'Select generator type {i}', ('Diesel','Coal','Natural Gas', 'Hydro','Solar','Wind'))
            generator_p_nom=st.number_input(f'Generator {i} nominal power (MW)', value=5.0, min_value=0.0, help='')
            generator_capital_cost=st.number_input(f'Generator {i} capital cost (€/MW)', value=0, min_value=0)
            generator_marginal_cost=st.number_input(f'Generator {i} marginal cost (€/MWh)', value=50, min_value=0)

            if generator_carrier=='Solar':
                res_source_type=st.radio('Select your pv production data', ['pvlib','csv file','TimescaleDB'],key=f'pv_data{i}', captions=['*PVLib is a python library that generates pv production data*', '*Path to your pv production data*'])            
                if res_source_type=='csv file':
                    j+=1
                    st.info("""
                            Upload a file in format: Datetime, GR_solar_generation. \n\r Datetime format: %Y-%m-%d %H:%M:%S+00:00 (e.g. 2018-01-01 09:00:00+00:00)\n\r GR_solar_generation must be in MW. 
                            """, icon="ℹ️")
                    csv_upload_format=pd.read_csv('pv_data.csv', delimiter=',',index_col=0, parse_dates=True)
                    st.dataframe(csv_upload_format['GR_solar_generation']['2018-01-01 09:00:00+00:00':'2018-01-01 13:00:00+00:00'])
                    uploaded = st.file_uploader('Choose a file for pv production', type='csv', key=f'res_source_type{i}')
                    if uploaded is not None:
                        df=read_uploaded_csv(uploaded)
                        # df = pd.read_csv(uploaded, delimiter=',', parse_dates=True)
                        expected_columns = ['Datetime', 'GR_solar_generation']
                        if not set(expected_columns).issubset(df.columns):
                            st.error('Upload a file in format: Datetime, GR_solar_generation')
                        else:
                            df.set_index(['Datetime'], inplace=True)
                            for date in df.index:
                               validate_date_format(date)
                            st.dataframe(df)
                            df.to_csv(f'pv_data{j}.csv', index=True, header=True)
                            res_source_uri=f'pv_data{j}.csv'
                    else:
                        res_source_uri=None
                if res_source_type=='pvlib':
                    res_source_uri=None

            if generator_carrier=='Wind':
                res_source_type=st.radio('Select your wind production data', ['csv file','TimescaleDB'],key=f'wind_data{i}', captions=['*Path to your pv production data*'])            
                if res_source_type=='csv file':
                    l+=1
                    st.info("""
                            Upload a file in format: Datetime, GR_wind_onshore_generation_actual. \n\r Datetime format: %Y-%m-%d %H:%M:%S+00:00 (e.g. 2018-01-01 09:00:00+00:00)\n\r GR_wind_onshore_generation_actual must be in MW. 
                            """, icon="ℹ️")
                    csv_upload_format=pd.read_csv('wind_data.csv', delimiter=',',index_col=0, parse_dates=True)
                    st.dataframe(csv_upload_format['2018-01-01 09:00:00+00:00':'2018-01-01 13:00:00+00:00'])
                    uploaded = st.file_uploader('Choose a file for wind production', type='csv', key=f'res_wind_data{i}')
                    if uploaded is not None:
                        df=read_uploaded_csv(uploaded)
                        # df = pd.read_csv(uploaded, delimiter=',', parse_dates=True)
                        expected_columns = ['Datetime', 'GR_wind_onshore_generation_actual']
                        if not set(expected_columns).issubset(df.columns):
                            st.error('Upload a file in format: Datetime, GR_wind_onshore_generation_actual')
                        else:
                            df.set_index(['Datetime'], inplace=True)
                            for date in df.index:
                               validate_date_format(date)
                            st.dataframe(df)
                            df.to_csv(f'wind_data{l}.csv', index=True, header=True)
                            res_source_uri = f'wind_data{l}.csv'
                    else:
                        res_source_uri=None
                else:
                    res_source_type = None
                    res_source_uri=None

            if generator_carrier not in (('Solar','Wind')):
                res_source_type = None
                res_source_uri=None

            generator_data = {
                'Component':'Generator',
                'carrier': generator_carrier,
                'bus':generator_bus,
                'p_nom': generator_p_nom,
                'capital_cost': generator_capital_cost,
                'marginal_cost': generator_marginal_cost,
                'input_series_source_type':res_source_type ,
                'input_series_source_uri': res_source_uri,
            }
            data_generator.append(generator_data) 
            st.divider()

    with st.container(border=True):
        st.header('Lines')
        lines=st.number_input('Select your lines', 1, 10)
        col = st.columns(lines)
        line=[]
        data_line=[]

        for i in range(lines):
            st.subheader(f'Line {i}')
            line.append(f'Line {i}')
            line_bus0=st.selectbox('From bus:', bus, key=f'line_bus0{i}')  
            line_bus1=st.selectbox('To bus:', bus, key=f'line_bus1{i}')

            line_data = {
            'Component':'Line',
            'carrier': 'AC',        
            'from_bus': line_bus0,
            'to_bus': line_bus1,
            }
            data_line.append(line_data)
            st.divider()

    with st.container(border=True):
        st.header('Loads')
        loads=st.number_input('Select your load buses', min_value=1)
        col = st.columns(loads)
        data_load=[]
        k=0
        investment_period=st.number_input('Investment period', 0,25,5)
        
        for i in range(loads):
            k+=1
            st.subheader(f'Load {i}')
            load_buses=st.selectbox('Load in bus:', bus, key=f'load_bus{i}')   
            load_carriers='AC'
            st.info("""
                    Upload a file in format: Datetime, GR_load. \n\r Datetime format: %Y-%m-%d %H:%M:%S+00:00 (e.g. 2018-01-01 09:00:00+00:00)\n\r GR_load must be in MW. 
                    """, icon="ℹ️")
            csv_upload_format=pd.read_csv('load_data.csv', delimiter=',',index_col=0, parse_dates=True)
            st.dataframe(csv_upload_format['2018-01-01 09:00:00+00:00':'2018-01-01 13:00:00+00:00'])
            uploaded = st.file_uploader('Choose a file for load', type='csv', key=f'load_data{i}')
            if uploaded is not None:
                df=read_uploaded_csv(uploaded)
                # df = pd.read_csv(uploaded, delimiter=',', parse_dates=True)
                expected_columns = ['Datetime', 'GR_load']
                if not set(expected_columns).issubset(df.columns):
                    st.error('Upload a file in format: Datetime, GR_load')
                else:
                    df.set_index(['Datetime'], inplace=True)
                    for date in df.index:
                        validate_date_format(date)
                    st.dataframe(df)
                    df.to_csv(f'load_data{k}.csv', index=True, header=True) 
                    load_source_type='csv file'
                    load_source_uri=f'load_data{k}.csv' 
            else:
                load_source_type=None 
                load_source_uri=None

            load_data={
            'Component':'Load',
            'carrier': load_carriers,
            'bus': load_buses, 
            'investment_period':investment_period,
            'input_series_source_type':load_source_type,
            'input_series_source_uri':load_source_uri,
            }
            data_load.append(load_data)  
            st.divider()

    with st.container(border=True):
        st.header('Links')
        st.info("""
                The link is a component for controllable directed flows between two buses, bus0 and bus1 with arbitrary energy carriers.\n
                The Link component can be used for any element with a controllable power flow: Energy conversion from AC to hydrogen network via **Electrolysis** and vice versa via **Fuel Cell**
                """,icon="ℹ️")
        links=st.number_input('Select your links', min_value=2)
        col = st.columns(links)
        data_link=[]

        for i in range(links):
            link_carriers=st.radio(f'Select link {i} type', options=['Electrolysis','Fuel Cell'], key=f'link_carrier{i}')
            st.subheader(link_carriers)
            link_bus0=st.selectbox(f'{link_carriers} link from bus:', bus, key=f'link_bus0{i}')
            link_bus1=st.selectbox(f'{link_carriers} link to bus:', bus, key=f'link_bus1{i}')
            link_p_nom=st.number_input(f'{link_carriers} nominal power (MW)',min_value=0.0, value=2.5, key=f'link_p_nom{i}', help='Limit of active power which can pass through link')
            link_capital_cost=st.number_input(f'{link_carriers}  capital cost (€/MW)',min_value=0, value=1000000, step=100, key=f'link_capex{i}', help='Capital cost of extending nominal power by 1 MW')
            link_marginal_cost=st.number_input(f'{link_carriers} marginal cost (€/MWh)',min_value=0, value=110, key=f'link_opex{i}', help='Marginal cost of transfering 1 MWh (before efficiency losses) from bus0 to bus1')
            link_efficiency=st.number_input(f'{link_carriers} efficiency',min_value=0.0, value=0.6, key=f'link_efficiency{i}', help='Efficiency of power transfer from bus0 to bus1')

            link_data={
                'Component':'Link',
                'carrier':link_carriers,
                'from_bus': link_bus0,
                'to_bus': link_bus1,
                'p_nom': link_p_nom,
                'capital_cost': link_capital_cost,
                'marginal_cost': link_marginal_cost,
                'efficiency':link_efficiency
            }
            data_link.append(link_data)
            st.divider()

    
    with st.container(border=True):
        st.header('Storage')
        stores=st.number_input('Select your stores', min_value=1)
        col = st.columns(stores)
        data_store=[]

        for i in range(stores):
            store_carrier=st.radio(f'Select store {i} type', options=['Hydrogen Store'], key=(f'store_carrier {i}'))
            store_buses=st.selectbox(f'{store_carrier} {i} bus:', options=bus, key=(f'store_bus {i}'))
            store_p_nom=st.number_input(f'{store_carrier} {i} nominal energy capacity (MWh)',min_value=0.0, value=15.0, key=(f'store_p_nom {i}'))
            store_capital_cost=st.number_input(f'{store_carrier} {i} capital cost (€/MWh)', min_value=0, value=40000, step=100, key=(f'store_capex {i}'), help='Capital cost of extending nominal energy capacity by 1 MWh')
            store_marginal_cost=st.number_input(f'{store_carrier} {i} marginal cost (€/MWh)',min_value=0, value=10, key=(f'store_opex {i}'), help='Marginal cost of production of 1 MWh')

            store_data={
                'Component':'Store',
                'carrier':store_carrier,
                'bus': store_buses,
                'p_nom': store_p_nom,
                'capital_cost': store_capital_cost,
                'marginal_cost': store_marginal_cost 
            }
            data_store.append(store_data)
            st.divider()
    
    results = bool(ss.b1_count %2)
    button_stop = bool(ss.b6_count %2)
    
    def submit_disabled():
        if button_stop:
            ss.b6_count=0
            ss.b1_count=0
            ss.b2_count=0
        return bool(ss.b1_count % 2)
    
    col = st.columns(14)
    col[0].button('Submit', key='b1', on_click=count, args=('b1_count',), type='primary', disabled=submit_disabled())
    col[1].button('Stop', key='b6', on_click=count, args=('b6_count',))
    
    ss.b3_count = 0
    ss.b4_count = 0
    
    if button_stop:
        st.empty()
        st.stop()
   
    if results==False:
        ss.b2_count=0
    else:
        with st.container(border=True):
            with st.spinner():
                start= time.time()
                timestamp=time.strftime('%Y.%m.%d %H.%M.%S', time.localtime())
                st.write(timestamp)
                for i in range(buses):
                    data_bus[i]['timestamp'] = timestamp
                df_bus = pd.DataFrame(data_bus)
                df_generator = pd.DataFrame(data_generator)
                df_line = pd.DataFrame(data_line)
                df_load = pd.DataFrame(data_load)
                df_link = pd.DataFrame(data_link)
                df_H2 = pd.DataFrame(data_store)

                inputs = pd.concat([df_bus, df_generator, df_line, df_load, df_link, df_H2], ignore_index=True)
                
                inputs.to_csv('data_inputs2.csv', index=False)

                from P2G_case1 import network
                
                st.write(inputs) 
                uploaded=f'./results/{use_case_name}/{timestamp}/outputs/statistics.csv'
                statistics=read_uploaded_csv(uploaded)
                st.write(statistics)
                uploaded=f'./results/{use_case_name}/{timestamp}/outputs/output_series.csv'
                df=read_uploaded_csv(uploaded)
                df.set_index(['Datetime'], inplace=True)

                tab1, tab2 = st.tabs(['📈 Chart', '🗃 Data'])
                tab1.subheader('Components Chart')
                with tab1:
                    fig = plotly_chart_results(df)
                    st.plotly_chart(fig, use_container_width=True)    
                    # plotly_chart_results(df)
                tab2.subheader('Components Data')
                tab2.write(df)
                csv = convert_df(df)
                tab2.download_button(label='Download data as CSV', data=csv, file_name='df.csv', mime='text/csv')
                                                 
                st.write(time.strftime('%d/%m/%Y, %H:%M:%S', time.localtime()))
                end=time.time()
                time_lapsed = end - start
                time_convert(time_lapsed)
            
            col1, col2 = st.columns(2)
            start = col1.date_input('Start', datetime.date(2020, 7, 22))
            end = col2.date_input('End', datetime.date(2020, 7, 25))
            
            start,end=selected_dates(start,end)

            st.button('Process Selected Dates', key='b2', on_click=count, args=('b2_count',))
            button2 = bool(ss.b2_count %2)

            if button2:
                filtered_df = df[(df.index >= start) & (df.index <= end)]
                tab5, tab6=st.tabs(['📈 Chart', '🗃 Data'])
                with tab5:
                    fig = plotly_chart_results(filtered_df)
                    st.plotly_chart(fig, use_container_width=True)        
                    # plotly_chart_results(filtered_df)
                tab6.write(filtered_df) 