import streamlit as st
import pandas as pd
import numpy as np
import pypsa
import time
import os
import datetime 
from streamlit import session_state as ss
import plotly.graph_objects as go
from P2G_case1 import network_execute, upload_results, calls
import json
import asyncio

import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
import yaml
from yaml.loader import SafeLoader
from streamlit_keycloak import login
from dataclasses import asdict
from dotenv import load_dotenv
from keycloak import KeycloakOpenID

load_dotenv()
keycloak_url=os.environ.get('KEYCLOAK_URL')
keycloak_realm=os.environ.get('KEYCLOAK_REALM')
keycloak_client_id=os.environ.get('KEYCLOAK_CLIENT_ID')
redirect_uri = os.environ.get('REDIRECT_URI')

visualization_engine_url=os.environ.get('VISUALIZATION_ENGINE_URL')
marketplace_url=os.environ.get('MARKETPLACE_URL')

st.set_page_config(page_title="EnerShare TwinP2G", 
                   page_icon="logo_Enershare_Icon.png",
                   layout='wide', 
                   initial_sidebar_state='expanded', 
                   )
st.title('TwinP2G')

# --- Initialize KeycloakOpenID object ---
keycloak_openid = KeycloakOpenID(
    server_url=keycloak_url,
    realm_name=keycloak_realm,
    client_id=keycloak_client_id,
)

# --- Construct Authentication URL ---
auth_url = keycloak_openid.auth_url(
    redirect_uri=redirect_uri,
    scope="openid email profile"
)

# --- Main Application ---
if "code" in st.experimental_get_query_params() and "access_token" not in st.session_state:
    # Handle the callback
    code = st.experimental_get_query_params()["code"][0]
    try:
        # Exchange the authorization code for tokens
        token = keycloak_openid.token(grant_type="authorization_code", code=code, redirect_uri=redirect_uri)
        st.session_state["access_token"] = token["access_token"]
        st.session_state["refresh_token"] = token["refresh_token"]
        st.session_state["id_token"] = token.get("id_token")
        
        # Clear the query parameters to prevent code reuse
        st.experimental_set_query_params()
        st.success("Successfully logged in!")
        st.rerun()  # Refresh the app to clear the code from the URL
    except Exception as e:
        # Clear the query parameters to avoid reusing the invalid code
        st.experimental_set_query_params()
        if "invalid_grant" in str(e):
            st.error("The authorization code is invalid or has expired. Please try logging in again.")
        else:
            st.error(f"Authentication failed: {e}")
elif "access_token" in st.session_state:

    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        st.success("✅ Logged in")
    with col3:
        if st.button("⎋ Sign out", use_container_width=False):
            st.experimental_set_query_params()
            # Call Keycloak logout endpoint
            try:
                keycloak_openid.logout(refresh_token=st.session_state["refresh_token"])
            except Exception as e:
                st.warning(f"Server-side logout failed: {e}")

            # Clear tokens
            for key in ["access_token", "refresh_token", "id_token"]:
                st.session_state.pop(key, None)

            # Optionally set a logout flag to prevent code reuse on fast rerun
            # st.session_state["logged_out"] = True
            st.rerun()

# keycloak = login(
#     url=keycloak_url,
#     realm=keycloak_realm,
#     client_id=keycloak_client_id,
#     # auto_refresh=True,
#     auto_refresh=False,
#     custom_labels={
#         "labelButton": "Sign in",
#         "labelLogin": "Modelling expert login.",
#         "errorNoPopup": "Unable to open the authentication popup. Allow popups and refresh the page to proceed.",
#         "errorPopupClosed": "Authentication popup was closed manually.",
#         "errorFatal": "Unable to connect to Keycloak using the current configuration."   
#     },
#     init_options={
#         'onLoad': 'login-required',  # Use redirect-based login,
#         'silentCheckSsoFallback': False,  # Fallback to silent check SSO if login-required fails
#         # 'silentCheckSsoRedirectUri': False,
#         'checkLoginIframe': False,
#         'flow': 'standard'

#     }
# )

# if not keycloak.authenticated:
#     # If the user is not authenticated, show the link button
#     st.link_button(label="To visualize the results of TwinP2G simulations please navigate to **Enershare Visualization Engine**", url=visualization_engine_url)

# if keycloak.authenticated:
    network = pypsa.Network()


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
        start=start.strftime('%Y-%m-%d %H:%M:%S')
        end=end.strftime('%Y-%m-%d %H:%M:%S')    
        return(start,end)

    def validate_date_format(date_str):
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValueError('Incorrect date format. Please use YYYY-MM-DD.')

    @st.cache_data
    def plotly_chart_results(df):
        fig = go.Figure()
        for col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col))
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
            st.link_button(label="Navigate to **Enershare Visualization Engine** for further analysis", url=visualization_engine_url)
            for csv_file in csv_files:
                st.write(f'Processing {csv_file}...')
                df=read_output_csv(csv_file)
                if  csv_file.endswith(('statistics.csv' , 'inputs.csv')):
                    st.write(df)
                    st.divider()

                if  csv_file.endswith('output_series.csv'):
                    tab1, tab2=st.tabs(['📈 Chart', '🗃 Data'])
                    tab1.subheader('Components Chart')
                    with tab1:
                        fig = plotly_chart_results(df)
                        st.plotly_chart(fig, use_container_width=True)
                    tab2.subheader('Components Data')
                    tab2.write(df)
                    csv = convert_df(df)
                    # tab2.download_button(label='Download data', data=csv, file_name='df.csv', mime='text/csv')
                    st.divider()                            
            col1, col2 = st.columns(2)
            start = col1.date_input('Start')
            end = col2.date_input('End')
            start,end=selected_dates(start,end)

            st.button('Process Selected Dates', key='b4', on_click=count, args=('b4_count',))        
            button4 = bool(ss.b4_count %2)

            if button4:
                for csv_file in csv_files:
                    dff=read_output_csv(csv_file)
                    filtered_df = dff[(dff.index >= start) & (dff.index <= end)]
                    if  csv_file.endswith('output_series.csv'):
                        tab1, tab2=st.tabs(['📈 Chart', '🗃 Data'])
                        with tab1:
                            fig = plotly_chart_results(filtered_df)
                            st.plotly_chart(fig, use_container_width=True)
                        tab2.write(filtered_df) 
                                
    if use_case=='Your use case':

        st.text_input('Name your use case', key='use_case', placeholder='Name ie use case 1234')
        use_case_name=st.session_state.use_case

        if use_case_name=='':
            st.error('Provide a name!')
    
        with st.container(border=True):
            st.header('Buses')
            buses=st.number_input('Select your electrical network buses', min_value=1)
            bus=[]
            data_bus=[]
            j=0
            l=0
            
            for i in range(buses):
                st.subheader(f'Bus {i}')
                bus.append(f'Bus {i}')
                bus_carrier=st.selectbox(f'Select energy carrier for bus {i}', ('AC','DC','hydrogen','gas','heat'))
                longitude=st.number_input(f'Longitude for bus {i}')
                latitude=st.number_input(f'Latitude for bus {i}')
                bus_data = {
                    'Component':'Bus',
                    'carrier': bus_carrier,
                    'bus': bus[i],
                    'from_bus':None,
                    'to_bus':None,
                    'longitude':longitude,
                    'latitude':latitude,
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
            data_generator=[]

            for i in range(generators):
                st.subheader(f'Generator {i}')
                generator_bus=st.selectbox(f'Select bus for generator {i}', options=bus, key=f'generator_bus{i}')
                generator_carrier=st.selectbox(f'Select generator type {i}', ('Diesel','Coal','Natural Gas', 'Hydro','Solar','Wind'))
                generator_p_nom=st.number_input(f'Generator {i} nominal power (MW)', min_value=0.0, help='')
                generator_capital_cost=st.number_input(f'Generator {i} capital cost (€/MW)', min_value=0.0)
                generator_marginal_cost=st.number_input(f'Generator {i} marginal cost (€/MWh)', min_value=0.0)

                if generator_carrier=='Solar':
                    res_source_type=st.radio('Select your pv production data', ['pvlib','csv file','TimescaleDB'],key=f'pv_data{i}', captions=['*PVLib is a python library that generates pv production data*', '*Upload your pv production data*'])            
                    if res_source_type=='csv file':
                        j+=1
                        st.info("""
                                Upload a file in format: Datetime, Value. \n\r Datetime format: %Y-%m-%d %H:%M:%S (e.g. 2018-01-01 09:00:00)\n\r Value must be in MW. 
                                """, icon="ℹ️")                    
                        st.markdown(
                        """
                        |Datetime |Value |
                        |- | -| 
                        |2018-01-01 10:00:00 | 2.566 |
                        |2018-01-01 11:00:00 | 3.8 |
                        |2018-01-01 12:00:00 | 6.842 |
                        |... |... |
                        """
                        )
                        uploaded = st.file_uploader('Choose a file for pv production', type='csv', key=f'res_source_type{i}')
                        if uploaded is not None:
                            df=read_uploaded_csv(uploaded)
                            # df = pd.read_csv(uploaded, delimiter=',', parse_dates=True)
                            expected_columns = ['Datetime', 'Value']
                            if not set(expected_columns).issubset(df.columns):
                                st.error('Upload a file in format: Datetime, Value')
                            else:
                                df.set_index(['Datetime'], inplace=True)
                                for date in df.index:
                                    validate_date_format(date)
                                st.dataframe(df)
                                df.to_csv(f'./data/pv_data{j}.csv', index=True, header=True)
                                res_source_uri=f'pv_data{j}.csv'
                        else:
                            res_source_uri=None
                    elif res_source_type=='pvlib':
                        res_source_uri=None
                    elif res_source_type=='TimescaleDB':
                        col1,col2=st.columns(2)
                        start_date=col1.date_input('Select start date')
                        end_date=col2.date_input('Select end date')
                        if st.button('Show Data Space dataset', key='solar'):
                            endpoint= 'actual_generation_per_type'
                            params={
                                'select' :f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})" 
                            }
                            dataspace_dataset = calls(endpoint,params)
                            st.dataframe(dataspace_dataset['solar'])
                        res_source_uri=f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})"

                if generator_carrier=='Wind':
                    res_source_type=st.radio('Select your wind production data', ['csv file','TimescaleDB'],key=f'wind_data{i}', captions=['*Upload your wind production data*'])            
                    if res_source_type=='csv file':
                        l+=1
                        st.info("""
                                Upload a file in format: Datetime, Value. \n\r Datetime format: %Y-%m-%d %H:%M:%S (e.g. 2018-01-01 09:00:00)\n\r Value must be in MW. 
                                """, icon="ℹ️")
                        st.markdown(
                        """
                        |Datetime |Value |
                        |- | -| 
                        |2018-01-01 10:00:00 | 2.566 |
                        |2018-01-01 11:00:00 | 3.8 |
                        |2018-01-01 12:00:00 | 6.842 |
                        |... |... |
                        """
                        )
                        uploaded = st.file_uploader('Choose a file for wind production', type='csv', key=f'res_wind_data{i}')
                        if uploaded is not None:
                            df=read_uploaded_csv(uploaded)
                            expected_columns = ['Datetime', 'Value']
                            if not set(expected_columns).issubset(df.columns):
                                st.error('Upload a file in format: Datetime, Value')
                            else:
                                df.set_index(['Datetime'], inplace=True)
                                for date in df.index:
                                    validate_date_format(date)
                                st.dataframe(df)
                                df.to_csv(f'./data/wind_data{l}.csv', index=True, header=True)
                                res_source_uri = f'wind_data{l}.csv'
                        else:
                            res_source_uri=None
                    elif res_source_type == 'TimescaleDB':
                        col1,col2=st.columns(2)
                        start_date=col1.date_input('Select start date')
                        end_date=col2.date_input('Select end date')
                        if st.button('Show Data Space dataset', key='wind'):
                            endpoint= 'actual_generation_per_type'
                            params={
                                'select' :f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})" 
                            }
                            dataspace_dataset = calls(endpoint,params)
                            st.dataframe(dataspace_dataset['wind_onshore'])
                        res_source_uri=f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})"

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
            lines=st.number_input('Select your lines', min_value=0)
            line=[]
            data_line=[]

            for i in range(lines):
                st.subheader(f'Line {i}')
                line.append(f'Line {i}')
                line_bus0=st.selectbox('From bus:', bus, key=f'line_bus0{i}')  
                line_bus1=st.selectbox('To bus:', bus, key=f'line_bus1{i}')
                line_reactance=st.number_input(f'Line {i} series reactance (Ohm)', min_value=0.0, help='')
                line_resistance=st.number_input(f'Line {i} series resistance (Ohm)', min_value=0.0, help='')
                line_data = {
                'Component':'Line',
                'carrier': 'AC',        
                'from_bus': line_bus0,
                'to_bus': line_bus1,
                'series_reactance':line_reactance,
                'series_resistance': line_resistance
                }
                data_line.append(line_data)
                st.divider()

        with st.container(border=True):
            st.header('Loads')
            loads=st.number_input('Select your load buses', min_value=1)
            data_load=[]
            k=0
            # investment_period=st.number_input('Investment period', 0,25,5)
            
            for i in range(loads):
                k+=1
                st.subheader(f'Load {i}')
                load_buses=st.selectbox('Load in bus:', bus, key=f'load_bus{i}')   
                load_carriers=st.selectbox(f'Select load type {i}', ('AC','Natural Gas', 'hydrogen'))

                load_source_type=st.radio('Select your load data', ['csv file','TimescaleDB'],key=f'load_source_type_data{i}', captions=['*Upload your load data*'])            
                if load_source_type=='csv file':
                    st.info("""
                            Upload a file in format: Datetime, Value. \n\r Datetime format: %Y-%m-%d %H:%M:%S (e.g. 2018-01-01 09:00:00)\n\r Value must be in MW. 
                            """, icon="ℹ️")
                    st.markdown(
                        """
                        | Datetime            | Value |
                        |---------------------|---------------------|
                        | 2018-01-01 10:00:00 | 0                   |
                        | 2018-01-01 11:00:00 | 1.175               |
                        | 2018-01-01 12:00:00 | 2.55                |
                        | ...                 | ...                 |
                        """
                    )
                    uploaded = st.file_uploader('Choose a file for load', type='csv', key=f'load_data{i}')
                    if uploaded is not None:
                        df=read_uploaded_csv(uploaded)
                        expected_columns = ['Datetime', 'Value']
                        if not set(expected_columns).issubset(df.columns):
                            st.error('Upload a file in format: Datetime, Value')
                        else:
                            df.set_index(['Datetime'], inplace=True)
                            for date in df.index:
                                validate_date_format(date)
                            st.dataframe(df)
                            df.to_csv(f'./data/load_data{k}.csv', index=True, header=True) 
                            load_source_type='csv file'
                            load_source_uri=f'load_data{k}.csv' 
                    else:                
                        load_source_uri=None
                elif load_source_type=='TimescaleDB':
                    col1,col2=st.columns(2)
                    start_date=col1.date_input('Select load data start date')
                    end_date=col2.date_input('Select load data end date')
                    if load_carriers=='Natural Gas':
                        with open('data/desfa_flows_hourly_archive.json', 'r') as file:
                            data = json.load(file)
                        allowed_values=data['properties']['point_id']['allowed_values']
                        exit_point=st.selectbox('Exit Point', allowed_values)
                        st.write(f'Exit point: {exit_point}')
                        if st.button('Show Data Space dataset', key = 'desfa_flows'):
                            endpoint= 'desfa_flows_hourly_archive'
                            params={
                                'select' :f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date},point_id.eq.{exit_point})" 
                            }
                            dataspace_dataset = calls(endpoint,params)
                            st.dataframe(dataspace_dataset)
                        load_source_uri=f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date},point_id.eq.{exit_point})"
                    elif load_carriers=='AC':
                        if st.button('Show Data Space dataset', key='ipto_total_load'):
                            endpoint= 'total_load_actual'
                            params={
                                'select' :f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})" 
                            }
                            dataspace_dataset = calls(endpoint,params)
                            st.dataframe(dataspace_dataset)
                        load_source_uri=f"*&and=(timestamp.gte.{start_date},timestamp.lte.{end_date})"
                    else:
                        load_source_uri=None


                load_data={
                'Component':'Load',
                'carrier': load_carriers,
                'bus': load_buses, 
                'investment_period':None,#investment_period,
                'input_series_source_type':load_source_type,
                'input_series_source_uri':load_source_uri,
                }
                data_load.append(load_data)  
                st.divider()

        with st.container(border=True):
            st.header('Links')
            st.info("""
                    The link is a component for controllable directed flows between two buses, bus0 and bus1 with arbitrary energy carriers.\n
                    The Link component can be used for any element with a controllable power flow: Energy conversion from AC to hydrogen network via **Electrolysis** and vice versa via **Fuel Cell** and energy conversion from hydrogen to synthetic natural gas via **Methanation**.
                    """,icon="ℹ️")
            links=st.number_input('Select your links', min_value=0)
            data_link=[]

            for i in range(links):
                link_carriers=st.radio(f'Select link {i} type', options=['Electrolysis','Fuel Cell', 'Methanation'], key=f'link_carrier{i}')
                st.subheader(link_carriers)
                link_bus0=st.selectbox(f'{link_carriers} link from bus:', bus, key=f'link_bus0{i}')
                link_bus1=st.selectbox(f'{link_carriers} link to bus:', bus, key=f'link_bus1{i}')
                link_p_nom=st.number_input(f'{link_carriers} nominal power (MW)',min_value=0.0, key=f'link_p_nom{i}', help='Limit of active power which can pass through link')
                link_capital_cost=st.number_input(f'{link_carriers}  capital cost (€/MW)',min_value=0.0, step=100.0, key=f'link_capex{i}', help='Capital cost of extending nominal power by 1 MW')
                link_marginal_cost=st.number_input(f'{link_carriers} marginal cost (€/MWh)',min_value=0.0, key=f'link_opex{i}', help='Marginal cost of transfering 1 MWh (before efficiency losses) from bus0 to bus1')
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
            stores=st.number_input('Select your stores', min_value=0)
            data_store=[]

            for i in range(stores):
                store_carrier=st.radio(f'Select store {i} type', options=['Hydrogen Store'], key=(f'store_carrier {i}'))
                store_buses=st.selectbox(f'{store_carrier} {i} bus:', options=bus, key=(f'store_bus {i}'))
                store_p_nom=st.number_input(f'{store_carrier} {i} nominal energy capacity (MWh)',min_value=0.0, key=(f'store_p_nom {i}'))
                store_capital_cost=st.number_input(f'{store_carrier} {i} capital cost (€/MWh)', min_value=0.0, step=100.0, key=(f'store_capex {i}'), help='Capital cost of extending nominal energy capacity by 1 MWh')
                store_marginal_cost=st.number_input(f'{store_carrier} {i} marginal cost (€/MWh)',min_value=0.0, key=(f'store_opex {i}'), help='Marginal cost of production of 1 MWh')

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
        
        col = st.columns(10)
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
                    
                    inputs.to_csv('data/data_inputs2.csv', index=False)

                    # network_execute()
                    use_case_name, timestamp, output_path, input_path, fig, network.buses, network.lines, network.links = network_execute()
                    asyncio.run(upload_results(use_case_name, timestamp, output_path, input_path, schema_name='twinp2g_results'))
                    
                    st.link_button("Your results are ready, navigate to the **EnerShare Visualization Engine** to analyze them", visualization_engine_url)
                    st.plotly_chart(fig)

                    st.dataframe(network.buses, use_container_width=True)
                    st.markdown(
                                """
                                <style>
                                [data-testid="stElementToolbar"] {
                                    display: none;
                                }
                                </style>
                                """,
                                unsafe_allow_html=True
                            )
                    st.dataframe(network.lines)
                    st.dataframe(network.links)

                    # st.write(inputs) 
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
                    tab2.subheader('Components Data')
                    tab2.write(df)
                    csv = convert_df(df)
                    # tab2.download_button(label='Download data as CSV', data=csv, file_name='df.csv', mime='text/csv')
                                                    
                    st.write(time.strftime('%d/%m/%Y, %H:%M:%S', time.localtime()))
                    end=time.time()
                    time_lapsed = end - start
                    time_convert(time_lapsed)
                
                col1, col2 = st.columns(2)
                start = col1.date_input('Start')
                end = col2.date_input('End')
                
                start,end=selected_dates(start,end)

                st.button('Process Selected Dates', key='b2', on_click=count, args=('b2_count',))
                button2 = bool(ss.b2_count %2)

                if button2:
                    filtered_df = df[(df.index >= start) & (df.index <= end)]
                    tab5, tab6=st.tabs(['📈 Chart', '🗃 Data'])
                    with tab5:
                        fig = plotly_chart_results(filtered_df)
                        st.plotly_chart(fig, use_container_width=True)        
                    tab6.write(filtered_df) 
else:
    # Custom-styled login button
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 20px; background-color: #FFF8DC; padding: 20px; border-radius: 10px;  display: flex; align-items: center;">
            <a href="{auth_url}" style="
                display: inline-block;
                padding: 10px 20px;
                font-size: 16px;
                font-family: sans-serif;
                color: white;
                background-color: #007BFF;
                text-decoration: none;
                border-radius: 5px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-right: 10px;
            ">
                Sign in
            </a>
            <span style="font-size: 16px; color: #8B8000; text-align: left;">Modelling expert login.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
# Link to the visualization engine
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 10px; display: flex; align-items: center;">
            <a href="{visualization_engine_url}" style="
                font-size: 14px;
                font-family: sans-serif;
                color: black;
                text-decoration: none;
                border: 1px solid grey;
                padding: 5px 10px;
                border-radius: 5px;
                display: inline-block;
            ">
                To visualize the results of TwinP2G simulations please navigate to <b>Enershare Visualization Engine<b>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div style="text-align: center; margin-top: 10px; display: flex; align-items: center;">
            <a href="{marketplace_url}" style="
                font-size: 14px;
                font-family: sans-serif;
                color: black;
                text-decoration: none;
                border: 1px solid grey;
                padding: 5px 10px;
                border-radius: 5px;
                display: inline-block;
            ">
                To access data from Data Space please navigate to <b>Enershare Marketplace<b>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )
footer = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: white;
    color: black;
    padding: 10px;
    box-shadow: 0px -2px 5px rgba(9, 228, 122, 0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
}

.footer img {
    height: 45px;  /* Adjust size as needed */
}
</style>

<div class="footer">
    <p>Copyright EnerShare Consortium &copy;2025. All rights reserved.</p>
    <img src="https://upload.wikimedia.org/wikipedia/commons/b/b7/Flag_of_Europe.svg" alt="EU Flag">
    <p>Co-funded by the Horizon 2020 Framework Programme of the European Union under Grant Agreement No 101069831</p>
</div>
"""
st.markdown(footer,unsafe_allow_html=True)
# elif authentication_status == False:
#     st.error('Username/password is incorrect')
# elif authentication_status == None:
#     st.warning('Please enter your username and password')