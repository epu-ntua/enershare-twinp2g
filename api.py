from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import asyncio
from P2G_case1 import network_execute, upload_results
import uvicorn
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

port=os.environ.get('API_PORT')
app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DataRequest(BaseModel):
    data: str

@app.post("/network_execute/")
def network_execute_endpoint(request: DataRequest):
    try:
        use_case_name, timestamp, output_path, input_path=network_execute(inputs_source='inputs_deeptsf')
        asyncio.run(upload_results(use_case_name, timestamp, output_path, input_path, schema_name='crete_fc_uc'))
        return {'Network simulated and optimized successfully', use_case_name}
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"App execution failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": f"Congratulations! Your API is working as expected. Now head over to /docs"}

if __name__ == "__main__":
    uvicorn.run('api:app', host="0.0.0.0", port=port, reload=True)
