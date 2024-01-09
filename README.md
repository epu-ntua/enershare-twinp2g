
# TwinP2G
This is the repository for the TwinP2G energy optimization tool. TwinP2G provides optimization services for user customized energy networks with energy sector coupling, for example electricity, green hydrogen, natural gas, and synthetic methane.

## Installation
To install the TwinP2G tool, clone the main branch of this repository: 

```git clone https://github.com/epu-ntua/enershare-twinp2g```

## Requirements
To run properly, the requirements listed in the file ```requirements.txt``` of the repository must be installed.

## Data Uploading
Currently, TwinP2G supports csv files for uploading data such as renewable energy output timeseries, and network loads timeseries. The format of uploaded timeseries files is shown at the corresponding step of the TwinP2G network customization wizard, prompting and guiding the user accordingly. 

### File format
The supported format usually comes in the form of two columns, one with name ``` 'Datetime' ```, and the other with name such as ```'GR_wind_onshore_generation_actual'```, or ```'GR_solar_generation'``` for renewable generation timeseries, or ```'GR_load'``` for loads timeseries.

The time input format of the ``` 'Datetime' ``` column must be in the form of ```YYYY-MM-DD hh:mm:ss+00:00``` (e.g. 2018-01-01 09:00:00+00:00). The other column of the values of the timeseries (energy production timeseries or energy load timeseries) must be in the form of float numbers, and in ```MWh```. For example:
|Datetime |GR_solar_generation |
|- | -| 
|2018-04-09 05:00:00 | 0 |
|2018-04-09 06:00:00 | 1.175 |
|2018-04-09 07:00:00 | 2.55 |
|... |... | 

for renewable generation input, and:
|Datetime |GR_load |
|- | -| 
|2018-04-09 05:00:00 | 2.566 |
|2018-04-09 06:00:00 | 3.8 |
|2018-04-09 07:00:00 | 6.842 |
|... |... |

for load inputs.
The wizard then checks if at least two columns of the csv file uploaded have the names specified above, and if not, it raises a warning, prompting to upload a file with correct columns names.

## Energy carriers
Energy carriers is where energy is stored in nature. The currently supported energy carriers are ```AC, DC, hydrogen, natural gas```. Energy can be transformed at buses with the help of links from one carrier to the other, e.g from electricity to green hydrogen, via an electrolysis component.

## Components that can be used
The following energy network components are supported. For more in depth information, components and their features can be found at PyPSA library documentation  ```https://pypsa.readthedocs.io/en/latest/components.html```.

### Buses
Buses are an energy network's nodes. Energy can come into and out of them. Minimum number of buses must be 1. An energy carrier must be specified for each bus.

### Generators
Generators produce energy. They must be assigned to one of the network's buses, and they must be of one of the supported generator types: ```Diesel, Coal, Natural Gas, Hydro, Solar, Wind```. They must be assigned a nominal power in MW, that is the maximum power they can reach at a single time snapshot. They must also be assigned a capital cost and a marginal production cost, in €/MW and in €/MWh respectively.

If a generator is a renewable energy generator, namely either ```Wind``` or ```Solar``` type, then the user will be prompted to upload an energy generation file with that generator's energy output timeseries.

### Lines
A Line is the component that simply transfers energy from one geographic location to another. It resembles ordinary electricity power lines. The start and end buses of a line must be specified. Energy can flow both ways inside a line.

### Loads
A load represents an energy demand timeseries, for example the electricity demand timeseries of a village, or its natural gas demand, or its hydrogen demand timeseries. Therefore, loads must be assigned to a single bus of the network. Then the wizard prompts the user to upload the load's energy timeseries file.

### Links
Links are mathematical instruments resembling devices that can transform energy from one carrier to the other. Supported links are ```Electrolysis, Fuel Cell and Methanation```. For example a fuel cell can transform hydrogen to electricity. Therefore links, just like lines, must be assigned to a starting and ending buses of the network. However, energy can only flow from the starting to the ending bus.

### Energy storage
Energy storage, or simply stores, is where energy can be stored for future usage. Currently, only ```hydrogen``` storage is supported. Stores must be assigned to a single bus. They must also be provided with a ```nominal energy capacity (MWh)``` a ```capital cost (€/MW)``` and a ```marginal cost (€/MWh)```.

## Optimization
After the network has been configured, the optimal power flow is found for the given timeslots, via the Linopy in-built method of PyPSA library. The optimal power flow is that which minimizes the total monetary costs of power generation, while respecting that the network specifications, such as energy demand satisfaction in each timeslot of the simulation must be met. The monetary costs of the simulation, are defined as the sum of capital and operational costs of all components of the network, for every timeslot.




