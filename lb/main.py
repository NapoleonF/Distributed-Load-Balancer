# main.py
import os
import random
import asyncio
import httpx
import dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from hashing import map_request_to_server
from servers import spawn_server, remove_server, heartbeat_checker, replicas, shutdown_handler

dotenv.load_dotenv()

INITIAL_SERVERS = int(os.getenv("INITIAL_SERVERS", 3))

@asynccontextmanager
async def lifespan(app: FastAPI):
    for _ in range(INITIAL_SERVERS):
        spawn_server()
    asyncio.create_task(heartbeat_checker())
    yield
    
app = FastAPI(lifespan=lifespan)

@app.on_event("shutdown")
async def shutdown_event():
    print("[SHUTDOWN] Load balancer is shutting down. Cleaning up replicas...")
    await shutdown_handler()


@app.get("/rep")
async def list_replicas():
    return {
        "message": {
            "N": len(replicas),
            "replicas": list(replicas.keys())
        },
        "status": "successful"
    }

@app.post("/add")
async def add_replicas(payload: dict):
    n = payload.get("n")
    hostnames = payload.get("hostnames", [])
    if n is None:
        raise HTTPException(status_code=400, detail="Missing 'n' in payload")
    if len(hostnames) != n:
        return JSONResponse(
            content={
                "message": "<Error> Length of hostname list is not equal to newly added instances",
                "status": "failure"
            },
            status_code=400
        )
    for i in range(n):
        name = hostnames[i] if i < len(hostnames) else None
        try:
            spawn_server(name)
        except Exception as e:
            print(f"Failed to spawn server: {e}")
    return {
        "message": {
            "N": len(replicas),
            "replicas": list(replicas.keys())
        },
        "status": "successful"
    }

@app.delete("/rm")
async def remove_replicas(payload: dict):
    n = payload.get("n")
    hostnames = payload.get("hostnames", [])
    
    if n is None:
        raise HTTPException(status_code=400, detail="Missing 'n' in payload")
    
    all_names = list(replicas.keys())

    # Check that all provided hostnames exist in current replicas
    for name in hostnames:
        if name not in all_names:
            return JSONResponse(
                content={
                    "message": f"<Error> Hostname '{name}' not found among current replicas",
                    "status": "failure"
                },
                status_code=400
            )
    
    # Ensure length of hostnames doesn't exceed n
    if len(hostnames) != n:
        return JSONResponse(
            content={
                "message": "<Error> Hostnames provided not equal to specified 'n'",
                "status": "failure"
            },
            status_code=400
        )

    for name in hostnames:
        remove_server(name)

    return JSONResponse(
        content={
            "message": {
                "N": len(replicas),
                "replicas": list(replicas.keys())
            },
            "status": "successful"
        },
        status_code=200
    )

@app.get("/{path:path}")
async def route_request(path: str, request: Request):
    request_id = random.randint(100000, 999999)
    try:
        server_info = map_request_to_server(request_id)
        if not server_info:
            raise Exception("No server available")
        server_id, virtual_index = server_info
        target_host = [
            name for name, meta in replicas.items()
            if meta.get("server_id") == server_id and virtual_index in meta.get("virtual_indices", [])
        ]
        if not target_host:
            raise Exception("Mapped server not found")
        async with httpx.AsyncClient() as client:
            res = await client.get(f"http://{target_host[0]}:5000/{path}")
            return JSONResponse(content=res.json(), status_code=res.status_code)
    except httpx.RequestError:
        return JSONResponse(content={"message": "Server not reachable", "status": "failure"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"message": f"<Error> {str(e)}", "status": "failure"}, status_code=400)