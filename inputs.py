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
st.set_page_config(layout="wide", initial_sidebar_state='expanded')

st.title('Twin P2G')
if 'b1_count' not in ss:
    ss.b1_count = 0
if 'b2_count' not in ss:
    ss.b2_count = 0
if 'b3_count' not in ss:
    ss.b3_count = 0
if 'b4_count' not in ss:
    ss.b4_count = 0

def count(key):
    ss[key] += 1

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')

def time_convert(sec):
    mins = sec // 60
    sec = sec % 60
    hours = mins // 60
    mins = mins % 60
    st.write("Time Lapsed = {0}:{1}:{2}".format(int(hours),int(mins),sec))

def list_csv_files(folder_path):
    csv_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".csv"):
                csv_files.append(os.path.join(root, file))
    return csv_files

def selected_dates(start,end):
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    start=start.strftime("%Y-%m-%d %H:%M:%S+00:00")
    end=end.strftime("%Y-%m-%d %H:%M:%S+00:00")
        
    return(start,end)

def validate_date_format(date_str):
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S+00:00")
    except ValueError:
        raise ValueError("Incorrect date format. Please use YYYY-MM-DD.")

def plotly_chart_results(df):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode='lines', name=col))
    plot=st.plotly_chart(fig, use_container_width=True)
    
    return plot


use_case=st.selectbox('Select your use case', options=('Your use case', 'See use cases'))

if use_case=='See use cases':
    # Set the default folder to "results"
    default_folder = "results"

    # Select a folder within "results"
    selected_subfolder = st.sidebar.radio("Select a subfolder", os.listdir(default_folder))
    preferred_csv_file = "inputs.csv"  

    st.write(f"Selected Subfolder: {selected_subfolder}")

    selected_subfolder_path = os.path.join(default_folder, selected_subfolder)

    csv_files = list_csv_files(selected_subfolder_path)

    if csv_files:
        csv_files.sort(key=lambda x: x == os.path.join(selected_subfolder_path, preferred_csv_file), reverse=True)

        st.write("CSV Files in Selected Subfolder:")
        for csv_file in csv_files:
            st.write(f"📄{csv_file}")
    else:
        st.warning("No CSV files found in the selected subfolder.")
    
    st.button("Process Selected CSV Files", key='b3', on_click=count, args=('b3_count',))
    button1 = bool(ss.b3_count %2)
    if button1:
        for csv_file in csv_files:
            st.write(f"Processing {csv_file}...")
            df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
            if  csv_file.endswith(("statistics.csv" , "inputs.csv",'data.csv')):
                st.write(df)

            if  csv_file.endswith("results.csv" ):
                tab1, tab2=st.tabs(["📈 Chart", "🗃 Data"])
                with tab1:
                    plotly_chart_results(df)    
                tab2.write(df) 
                            
            if csv_file.endswith('stores.csv'):
                tab1, tab2=st.tabs(["📈 Chart", "🗃 Data"])
                with tab1:
                    st.line_chart(df)    
                tab2.write(df) 
                csv = convert_df(df)
                tab2.download_button(label="Download data as CSV", data=csv, file_name='df.csv', mime='text/csv')

        col1, col2 = st.columns(2)
        start = col1.date_input("Start", datetime.date(2020, 7, 22))
        end = col2.date_input("End", datetime.date(2020, 7, 25))
        start,end=selected_dates(start,end)

        st.button("Process Selected Dates", key='b4', on_click=count, args=('b4_count',))
        
        button2 = bool(ss.b4_count %2)
        if button2:
            for csv_file in csv_files:
                dff = pd.read_csv(csv_file,index_col=0, parse_dates=True)
                filtered_df = dff[(dff.index >= start) & (dff.index <= end)]

                if  csv_file.endswith("results.csv" ):
                    tab1, tab2=st.tabs(["📈 Chart", "🗃 Data"])
                    with tab1:
                        plotly_chart_results(filtered_df)    
                    tab2.write(filtered_df) 
                                
                if csv_file.endswith('stores.csv'):
                    tab1, tab2=st.tabs(["📈 Chart", "🗃 Data"])
                    with tab1:
                        st.line_chart(filtered_df)    
                    tab2.write(filtered_df) 
    
if use_case=='Your use case':
    cont=st.container()
    st.text_input("Name your use case", key="use_case",placeholder='Name ie use case 1234')
    use_case_name=st.session_state.use_case
    if use_case_name=='':
        st.error('Provide a name!')

    if use_case_name in os.listdir('results'):
        st.error('This name is already existing.')
    
    st.subheader('Network')
    buses=st.number_input('Select your electrical network buses', min_value=1)
    col = st.columns(buses)
    
    bus=[]
    data_bus=[]
    carriers=[]
    P_nom=[]
    marginal_cost_list = []
    capital_cost_list=[]
    line_bus0=[]
    line_bus1=[]

    j=0
    l=0
    pv_data_list=[]
    csv_upload=[]
    
    for i in range(buses):
        with col[i]:
            st.subheader(f'Bus {i}')
            bus.append(f'Bus {i}')
            generator=st.radio(f'Select generator for bus {i}', ('Diesel','Coal','Natural Gas', 'Hydro','Solar','Wind'))
            carriers.append(generator)
            gen=st.number_input(f'Pnom generator {i}', value=5.0, min_value=0.0, help='')
            P_nom.append(gen)
            marginal_gen=st.number_input(f'marginal cost generator {i}', value=50, min_value=0)
            marginal_cost_list.append(marginal_gen)
            capital_cost_list.append(0)
            line_bus0.append(None)
            line_bus1.append(None)

            if generator=='Solar':
                pv_data=st.radio('Select your pv production data', ['pvlib','csv file','TimescaleDB'],key=f'pv_data{i}', captions=['*PVLib is a python library that generates pv production data*', '*Path to your pv production data*'])            
                pv_data_list.append(pv_data)
                if pv_data=='csv file':
                    j+=1
                    uploaded = st.file_uploader("Choose a file for pv production", type='csv', key=f'res_data{i}')
                    if uploaded is not None:
                        df = pd.read_csv(uploaded, delimiter=",", parse_dates=True)
                        expected_columns = ['Datetime', 'GR_solar_generation']
                        if not set(expected_columns).issubset(df.columns):
                            st.error('Upload a file in format: Datetime, GR_solar_generation')
                        else:
                            df.set_index(['Datetime'], inplace=True)
                            for date in df.index:
                               validate_date_format(date)
                            st.dataframe(df)
                            df.to_csv(f'pv_data{j}.csv', index=True, header=True)
                            csv_upload.append(f'pv_data{j}.csv')
                    else:
                        csv_upload.append(None) 
                if pv_data=='pvlib':
                    csv_upload.append(None)

            if generator=='Wind':
                wind_data=st.radio('Select your wind production data', ['csv file','TimescaleDB'],key=f'wind_data{i}', captions=['*Path to your pv production data*'])            
                pv_data_list.append(wind_data)
                if wind_data=='csv file':
                    l+=1
                    uploaded = st.file_uploader("Choose a file for wind production", type='csv', key=f'res_wind_data{i}')
                    if uploaded is not None:
                        df = pd.read_csv(uploaded, delimiter=",", parse_dates=True)
                        expected_columns = ['Datetime', 'GR_wind_onshore_generation_actual']
                        if not set(expected_columns).issubset(df.columns):
                            st.error('Upload a file in format: Datetime, GR_wind_onshore_generation_actual')
                        else:
                            df.set_index(['Datetime'], inplace=True)
                            for date in df.index:
                               validate_date_format(date)
                            st.dataframe(df)
                            df.to_csv(f'wind_data{l}.csv', index=True, header=True)
                            csv_upload.append(f'wind_data{l}.csv')
                else:
                    csv_upload.append(None) 

            if generator not in (('Solar','Wind')):
                pv_data_list.append(None)
                csv_upload.append(None)

            generator_data = {
                'Component':'Generator',
                "Carrier": carriers[i],
                "Bus": bus[i],
                'From Bus':line_bus0[i],
                'To Bus':line_bus1[i],
                "Pnom": P_nom[i],
                'Capital Cost': capital_cost_list[i],
                "Marginal Cost": marginal_cost_list[i],
                'input_series_source_type':pv_data_list[i] ,
                'input_series_source_uri': csv_upload[i],
                'use_case_name':use_case_name
            }
            data_bus.append(generator_data) 
    st.divider()

    lines=st.number_input('Select your lines', 1, 10)
    cols = st.columns(lines)

    line=[]
    data_line=[]

    for i in range(lines):
        with cols[i]:
            st.subheader(f'Line {i}')
            line.append(f'Line {i}')
            pv_data_list.append(None)

            bus0=st.radio('From bus:', bus, key=f'line_bus0{i}')  
            line_bus0.append(bus0)
            bus1=st.radio('To bus:', bus, key=f'line_bus1{i}')
            line_bus1.append(bus1)
            carriers.append('AC')

            line_data = {
            'Component':'Line',
            "Carrier": carriers[i+buses],          
            "From Bus": line_bus0[i+buses],
            "To Bus": line_bus1[i+buses],
            }
            data_line.append(line_data)

    st.divider()

    loads=st.number_input('Select your load buses', min_value=1)
    cols = st.columns(loads)

    load=[]
    load_buses=[]
    data_load=[]
    k=0
    investment_period=st.number_input('Investment period', 0,25,5)
    for i in range(loads):
        k+=1
        with cols[i]:
            st.subheader(f'Load {i}')
            load.append(f'Load {i}')
            load_bus=st.radio('Load in bus:', bus, key=f'load_bus{i}')   
            load_buses.append(load_bus) 
            uploaded = st.file_uploader("Choose a file for load", type='csv', key=f'load_data{i}')
            if uploaded is not None:
                df = pd.read_csv(uploaded, delimiter=",", parse_dates=True)
                expected_columns = ['Datetime', 'GR_load']
                if not set(expected_columns).issubset(df.columns):
                    st.error('Upload a file in format: Datetime, GR_load')
                else:
                    df.set_index(['Datetime'], inplace=True)
                    for date in df.index:
                        validate_date_format(date)
                    st.dataframe(df)
                    df.to_csv(f'load_data{k}.csv', index=True, header=True) 
                    pv_data_list.append('csv file')
                    csv_upload.append(f'load_data{k}.csv') 
            else:
                pv_data_list.append(None) 
                csv_upload.append(None) 
            carriers.append('AC')
            load_data={
            'Component':'Load',
            "Carrier": carriers[i+buses],
            "Bus": load_buses[i], 
            'Investment Period':investment_period,
            'input_series_source_type':pv_data_list[i+buses+lines],
            'input_series_source_uri':csv_upload[i+buses]
            }
            data_load.append(load_data)  

    st.divider()

    with st.container():
        electrolyzer=[]
        fuel_cell=[]
        H2_store=[]
        H2_bus=['Hydrogen Bus']
        col1, col2, col3=st.columns(3)
        with col1:
            st.subheader('Electrolyzer')
            bus0_el=st.radio('Electrolyzer link from bus:',bus)
            bus1_el=st.radio('Electrolyzer link to bus:',H2_bus)
            P_el=st.number_input('Pnominal electrolyser',min_value=0.0, value=2.5)
            cost_el=st.number_input('electrolyser cost per MW',min_value=0, value=1000000, step=100)
            marginal_el=st.number_input('marginal cost el',min_value=0, value=110)

            electrolyzer={
                'Component':'Link',
                'Carrier':'Electrolysis',
                "From Bus": [bus0_el],
                "To Bus": [bus1_el],
                'Pnom': [P_el],
                'Capital Cost': [cost_el],
                'Marginal Cost': [marginal_el]
            }

        with col2:
            st.subheader('Fuel Cell')
            bus0_fc=st.radio('Fuel Cell link from bus:',H2_bus)
            bus1_fc=st.radio('Fuel Cell link to bus:',bus)
            P_fc=st.number_input('Pnominal fuel cell',min_value=0.0, value=1.2)
            cost_fc=st.number_input('fuel cell cost', min_value=0, value=1000000, step=100)
            marginal_fc=st.number_input('marginal cost fc', min_value=0, value=110)
            fuel_cell={
                'Component':'Link',
                'Carrier':'Fuel Cell',
                "From Bus": [bus0_fc],
                "To Bus": [bus1_fc],
                'Pnom': [P_fc],
                'Capital Cost': [cost_fc],
                'Marginal Cost': [marginal_fc]
            }

        with col3:
            st.subheader('Hydrogen Storage')
            bus_H2=st.radio('Hydrogen Storage bus:', H2_bus)
            P_H2=st.number_input('Pnominal H2 buffer',min_value=0.0, value=15.0)
            cost_H2=st.number_input('H2 buffer cost', min_value=0, value=40000, step=100)
            marginal_H2=st.number_input('marginal cost H2',min_value=0, value=10)
            H2_store={
                'Component':'Store',
                'Carrier':'Hydrogen Store',
                "Bus": [bus_H2],
                'Pnom': [P_H2],
                'Capital Cost': [cost_H2],
                'Marginal Cost': [marginal_H2] 
            }

        df_bus = pd.DataFrame(data_bus)
        df_line = pd.DataFrame(data_line)
        df_load = pd.DataFrame(data_load)
        df_el = pd.DataFrame(electrolyzer)
        df_fc = pd.DataFrame(fuel_cell)
        df_H2 = pd.DataFrame(H2_store)

        inputs = pd.concat([df_bus, df_line, df_load, df_el, df_fc, df_H2], ignore_index=True)
        
        inputs.to_csv('data_inputs2.csv', index=False)
        st.write(inputs)
                
        st.button("Submit", key='b1', on_click=count, args=('b1_count',))
        results = bool(ss.b1_count %2)
      
    if results:
            with st.container():
                with st.spinner():
                    start= time.time()
                    timer=time.strftime("%d/%m/%Y, %H:%M:%S", time.localtime())
                    st.write(timer)

                    from P2G_case1 import network

                    st.write(inputs) 
                    statistics=pd.read_csv(f"./results/{use_case_name}/statistics.csv",index_col=0)
                    st.write(statistics)
                    df=pd.read_csv(f"./results/{use_case_name}/results.csv", index_col=0, parse_dates=True)
                    stores=pd.read_csv(f"./results/{use_case_name}/stores.csv", index_col=0, parse_dates=True)

                    tab1, tab2 = st.tabs(["📈 Chart", "🗃 Data"])
                    tab1.subheader('Components Chart')
                    with tab1:
                        plotly_chart_results(df)
                    tab2.subheader('Components Chart')
                    tab2.write(df)
                    csv = convert_df(df)
                    tab2.download_button(label="Download data as CSV", data=csv, file_name='df.csv', mime='text/csv')

                    tab3, tab4 = st.tabs(["📈 Chart", "🗃 Data"])
                    tab3.subheader('H2 store')
                    tab3.line_chart(stores)
                    tab4.subheader('H2 store')
                    tab4.write(stores)
                                                     
                    st.write('Done!')
                    st.write(time.strftime("%d/%m/%Y, %H:%M:%S", time.localtime()))
                    end=time.time()
                    time_lapsed = end - start
                    time_convert(time_lapsed)
                
                col1, col2 = st.columns(2)
                start = col1.date_input("Start", datetime.date(2020, 7, 22))
                end = col2.date_input("End", datetime.date(2020, 7, 25))
                
                start,end=selected_dates(start,end)

                st.button("Process Selected Dates", key='b2', on_click=count, args=('b2_count',))
                button = bool(ss.b2_count %2)

                if button:
                    filtered_df = df[(df.index >= start) & (df.index <= end)]
                    filtered_stores=stores[(stores.index >= start) & (stores.index <= end)]
                    tab5, tab6=st.tabs(["📈 Chart", "🗃 Data"])
                    with tab5:
                        plotly_chart_results(filtered_df)
                    tab6.write(filtered_df) 
                    tab7, tab8=st.tabs(["📈 Chart", "🗃 Data"])
                    tab7.line_chart(filtered_stores)
                    tab8.write(filtered_stores) 