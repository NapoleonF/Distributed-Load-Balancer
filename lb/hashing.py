import string
from utils import hash_string_to_int

NUM_SLOTS = 512
VIRTUAL_SERVERS_PER_CONTAINER = 9

# Create empty hash ring with 512 slots
hash_ring = [None] * NUM_SLOTS

def virtual_hash(server_id: str, v_index: int) -> int:
    i = server_id
    j = v_index
    return (i**2 + j**2 + 2*j + 25) % NUM_SLOTS

def request_hash(i: string) -> int:
    h = hash_string_to_int(i)
    return (h**2 + 2*h + 17) % NUM_SLOTS

def virtual_hash_updated(server_id: str, v_index: int) -> int:
    key = f"{server_id}-{v_index}"
    return hash_string_to_int(key, mod=NUM_SLOTS)

def request_hash_updated(i: string) -> int:
    return hash_string_to_int(i, mod=NUM_SLOTS)

def insert_virtual_server(server_id: int, virtual_index: int):
    """Insert a virtual server into the hash ring with linear probing."""
    slot = virtual_hash_updated(server_id, virtual_index)

    # Linear probing in case of collision
    original_slot = slot
    while hash_ring[slot] is not None:
        slot = (slot + 1) % NUM_SLOTS
        if slot == original_slot:
            raise RuntimeError("Hash ring full while inserting virtual server")
    hash_ring[slot] = (server_id, virtual_index)

def map_request_to_server(request_id: int):
    """Map a request to the closest virtual server in the hash ring."""
    key = f"request-{request_id}"
    slot = request_hash_updated(key)

    # Search forward for the first non-empty slot
    for i in range(NUM_SLOTS):
        index = (slot + i) % NUM_SLOTS
        if hash_ring[index] is not None:
            return hash_ring[index]  # (server_id, virtual_index)

    return None  # Should never happen if ring is populated
