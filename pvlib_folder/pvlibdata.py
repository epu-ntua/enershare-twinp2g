# %%
import pvlib
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.pvsystem import PVSystem
from pvlib.location import Location
from pvlib.modelchain import ModelChain
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS
import time
import math

# %%
def days_between_dates(dt1, dt2):
    date_format = "%Y-%m-%d %H:%M:%S"
    a = time.mktime(time.strptime(dt1, date_format))
    b = time.mktime(time.strptime(dt2, date_format))
    delta = abs(b - a)
    return delta / (60 * 60 * 24)  # Convert seconds to days

# %%
def extend_tmy_data(df, num_years):
    extended_dfs = []
    for year_offset in range(int(num_years)):
        extended_dfs.append(df.copy())
    extended_data = pd.concat(extended_dfs, ignore_index=True)
    return extended_data
# %% 
def pvlib_simulation(data_load):
    latitude=37.983810 
    longitude=23.727539
    surface_tilt=0 
    surface_azimuth=180
    startyear=None
    endyear=None
    freq='h'
    # data_load = pd.read_csv('./load_data1.csv', parse_dates=True)
    # data_load.set_index(['Datetime'], inplace=True)
    start=data_load.index[0]
    end=data_load.index[-1]
    print ('start',start)
    num_days = days_between_dates(start, end)
    num_years = math.ceil(num_days / 365)  


    tmy=pvlib.iotools.get_pvgis_tmy(latitude, 
                                longitude, 
                                outputformat='csv', 
                                usehorizon=True, 
                                userhorizon=None, 
                                startyear=startyear, 
                                endyear=endyear, 
                                map_variables=True, 
                                url='https://re.jrc.ec.europa.eu/api/v5_2/', 
                                timeout=30)[0]


    tmy.columns

    extended_tmy_data = extend_tmy_data(tmy, num_years)
    extended_tmy_data.index=pd.date_range(start=start, periods=len(extended_tmy_data), freq=freq)
    extended_tmy_data_new=extended_tmy_data[start:end]
    extended_tmy_data_new

    # extended_tmy_data_new.to_csv('pvgis_tmy.csv', index=True)

    module_name = 'Canadian_Solar_CS5P_220M___2009_'
    inverter_name = 'ABB__ULTRA_1100_TL_OUTD_2_US_690_x_y_z__690V_' #'Power_Electronics__FS3000CU15__690V_' #'ABB__PVS980_58_2000kVA_K__660V_' #'ABB__ULTRA_1100_TL_OUTD_2_US_690_x_y_z__690V_'
    location=Location(latitude, longitude, tz='Europe/Athens', altitude=100)

    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod') 
    sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
    module = sandia_modules[module_name]
    inverter = sapm_inverters[inverter_name]
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

    system=PVSystem(surface_tilt=surface_tilt, surface_azimuth=surface_azimuth,
                    module_parameters=module, inverter_parameters=inverter,
                    temperature_model_parameters=temperature_model_parameters,
                    modules_per_string=25, strings_per_inverter=215
                    )
    modelchain=ModelChain(system, location)

    data=extended_tmy_data_new
    data.index=pd.to_datetime(data.index)

    modelchain.run_model(data)
    solar_data=modelchain.results.ac
    solar_data=pd.DataFrame(solar_data, columns=(['Value']))

    solar_data.loc[solar_data['Value'] < 0, 'Value'] = 0

    # Convert Watt to MW
    solar_data/=1000000
    solar_data.to_csv('pvlib_folder/solar_data.csv', index_label=['Datetime'])
    solar_data.head(20)
    solar_data.describe()

    solar_data.plot()

    return solar_data

# %%
