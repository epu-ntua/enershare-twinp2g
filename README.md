# TwinP2G

This is the repository for the TwinP2G energy optimization tool. TwinP2G provides optimization services for user customized energy networks with energy sector coupling, for example electricity, green hydrogen, natural gas, and synthetic methane.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 

## Installation

To install the TwinP2G tool, clone the main branch of this repository: 

`git clone https://github.com/epu-ntua/enershare-twinp2g`

### Set Up Environment Variables
Ensure that the necessary environment variables are configured. These variables should be saved in a `.env` file, which contains key configuration details for the app to function properly.
-  You can find an example of the required credentials in the 
[.env.example](https://github.com/epu-ntua/enershare-twinp2g/blob/dev/.env.example).
- Download the `.env.example` file, rename it to `.env`, and update the values with your specific settings.

Here are the key variables you need to configure in the `.env` file:

- **Visualization Engine**: \
`VISUALIZATION_ENGINE_URL=<insert visualization_engine_url>`\
URL to visualize the simulation results.
- **Keycloak**:
TwinP2G uses Keycloak for identity and access management.
    - `KEYCLOAK_URL=<insert keycloak_url>`\
    Keycloak server URL for authentication.
    - `KEYCLOAK_REALM=<insert keycloak_realm>`\
    The realm in Keycloak for authentication and authorization.
    - `KEYCLOAK_CLIENT_ID=<insert keycloak_client_id>`\
    The client ID registered in Keycloak for your application.
- **DataSpace Connector**: 
    - `CONNECTOR_URL=<insert connector_url>`\
    The URL of the connector service you are interfacing with.
    - `JWT_TOKEN=<insert jwt_token>`\
    JWT token for authentication.
    - `FORWARD_ID=<insert forward_id>`\
    Identifier for routing messages or requests.
    - `FORWARD_SENDER=<insert forward_sender>`\
    Sender information for the forwarding process.

- **Database**: \
`DATABASE_URL=<insert database_url>`\
The connection string for your database, where the simulation results will be stored.

### Launch the Application
Once the `.env` file is set up, launch the app using the following Docker command:

`docker-compose up --build`

After running the command, you can access the TwinP2G interface through your browser at: http://localhost:8501/