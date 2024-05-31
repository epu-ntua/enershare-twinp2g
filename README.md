# TwinP2G

This is the repository for the TwinP2G energy optimization tool. TwinP2G provides optimization services for user customized energy networks with energy sector coupling, for example electricity, green hydrogen, natural gas, and synthetic methane.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 

### Installation

To install the TwinP2G tool, clone the main branch of this repository: 

```git clone https://github.com/epu-ntua/enershare-twinp2g```

### Conda Environment

A conda environment must be created and activated for the project:

```conda create --name twinp2g-env```

```conda activate twinp2g-env```

### Install Dependencies

To run properly, the requirements listed in the file ```requirements.txt``` of the repository must be installed:

```pip install -r requirements.txt```

## Running the TwinP2G tool

To use the TwinP2G tool, run the following command in your terminal:

```streamlit run inputs.py```

This command will launch the application, allowing you to interact with the TwinP2G tool via your web browser.
