from fastapi import FastAPI
import os
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

server_id = os.getenv("SERVER_ID", "default_server")

@app.get("/home")
async def root():
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Hello from Server: {server_id}",
            "status": "successful"
        }
    )
    
@app.get("/heartbeat")
async def heartbeat():
    return JSONResponse(
        status_code=200,
        content={}
    )