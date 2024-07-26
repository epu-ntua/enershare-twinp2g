import pandas as pd
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, MetaData, text, Table
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.schema import CreateSchema
from sqlalchemy.orm import sessionmaker, Session

from typing import Optional

# Load variables from .env file
load_dotenv()

# Access environmental variables
# TODO: Add commented line below in a .env file to set the DATABASE_URL
database_url = os.environ.get('DATABASE_URL') 

# Create engine with database URL
engine = create_engine(database_url, pool_pre_ping=True)

#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Functions ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a dependency to get the database session
def get_db_session():
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()

# Create a dependency to get the database metadata
def get_metadata(schema='public'):
    metadata = MetaData()
    metadata.reflect(bind=engine, schema=schema)    
    return metadata

# Function to create schema
async def create_schema(schema_name):
    try:
        with engine.connect() as connection:
            if engine.dialect.has_schema(connection, schema_name):
                print(f"Schema \"{schema_name}\" already exists")
            else:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS {schema_name};'))
                # connection.execute(CreateSchema(schema_name, if_not_exists=True))                
                connection.commit()
                print(f"Schema \"{schema_name}\" succesfully created")
    except Exception as e:
        print("An error occurred while creating schema in the database:", e)

async def upload_csv(csv_file, table_name, schema_name):
    try:
        schema_name=schema_name.lower()
        await create_schema(schema_name) # create schema if not exists - wait for schema to be created
        df = pd.read_csv(csv_file)
        with engine.connect() as connection:
            df.to_sql(table_name, connection, schema=schema_name, if_exists='replace', index=False)
            get_metadata()
            return {"message": f"CSV file uploaded and inserted into the '{table_name}' table successfully."}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}
