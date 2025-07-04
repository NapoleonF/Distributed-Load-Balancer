import asyncio
from typing import Optional
import httpx
import os
import random

from hashing import insert_virtual_server, VIRTUAL_SERVERS_PER_CONTAINER
from utils import random_hostname, hash_string_to_int

DOCKER_IMAGE = "fastapi-server:latest"
DOCKER_NETWORK = "net1"

replicas = {}

def spawn_server(hostname: Optional[str] = None) -> str:
    if not hostname:
        hostname = random_hostname()

    server_id = hash_string_to_int(hostname)
    virtuals = []
    for v_index in range(VIRTUAL_SERVERS_PER_CONTAINER):
        insert_virtual_server(server_id, v_index)
        virtuals.append(v_index)

    cmd = (
        f"docker run -d --name {hostname} --network {DOCKER_NETWORK} "
        f"-e SERVER_ID={hostname} {DOCKER_IMAGE}"
    )
    result = os.popen(cmd).read()
    if not result:
        raise RuntimeError(f"Failed to spawn container {hostname}")

    replicas[hostname] = {
        "server_id": server_id,
        "virtual_indices": virtuals
    }
    return hostname

def remove_server(hostname: str):
    os.system(f"docker stop {hostname} && docker rm {hostname}")
    replicas.pop(hostname, None)

async def heartbeat_checker():
    while True:
        await asyncio.sleep(5)
        for hostname in list(replicas.keys()):
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"http://{hostname}:5000/heartbeat", timeout=2)
                    if res.status_code != 200:
                        raise Exception()
            except:
                print(f"[HEARTBEAT] {hostname} is down. Respawning...")
                remove_server(hostname)
                try:
                    new_host = spawn_server()
                    print(f"[SPAWN] Replaced {hostname} with {new_host}")
                except Exception as e:
                    print(f"[ERROR] Failed to replace server: {e}")

async def shutdown_handler():
    print("Shutting down all servers...")
    for hostname in list(replicas.keys()):
        remove_server(hostname)
    print("All servers shut down successfully.")