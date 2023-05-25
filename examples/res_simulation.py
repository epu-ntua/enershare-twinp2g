import pvlib
import pandas as pd
import matplotlib.pyplot as plt

times = pd.date_range(start='2016-07-01', end='2016-07-04', freq='1H')

coordinates = [
    (37.98, 23.73, 'Thens', 300, 'Etc/GMT-2')
]

sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
sapm_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
module = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
inverter = sapm_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

energies = pd.DataFrame(index=times, columns=coordinates)

for location in coordinates:
    latitude, longitude, name, altitude, timezone = location
    weather = pvlib.iotools.get_pvgis_tmy(latitude, longitude, map_variables=True)[0]
    weather = weather.reindex(times)  # Reindex weather data to match desired times
    solpos = pvlib.solarposition.get_solarposition(times, latitude, longitude)
    dni_extra = pvlib.irradiance.get_extra_radiation(times)
    airmass = pvlib.atmosphere.get_relative_airmass(solpos['apparent_zenith'])
    pressure = pvlib.atmosphere.alt2pres(altitude)
    am_abs = pvlib.atmosphere.get_absolute_airmass(airmass, pressure)
    aoi = pvlib.irradiance.aoi(latitude, 180, solpos['apparent_zenith'], solpos['azimuth'])
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=latitude,
        surface_azimuth=180,
        solar_zenith=solpos['apparent_zenith'],
        solar_azimuth=solpos['azimuth'],
        dni=weather['dni'],
        ghi=weather['ghi'],
        dhi=weather['dhi'],
        dni_extra=dni_extra,
        model='haydavies',
    )
    cell_temperature = pvlib.temperature.sapm_cell(
        poa_global=total_irradiance['poa_global'],
        temp_air=weather["temp_air"],
        wind_speed=weather["wind_speed"],
        **temperature_model_parameters,
    )
    effective_irradiance = pvlib.pvsystem.sapm_effective_irradiance(
        poa_direct=total_irradiance['poa_direct'],
        poa_diffuse=total_irradiance['poa_diffuse'],
        airmass_absolute=am_abs,
        aoi=aoi,
        module=module,
    )
    dc = pvlib.pvsystem.sapm(effective_irradiance, cell_temperature, module)
    ac = pvlib.inverter.sandia(dc['v_mp'], dc['p_mp'], inverter)
    energies[location] = ac

energies.plot()
plt.ylabel('Hourly energy yield (W hr)')
plt.show()
