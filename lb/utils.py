import random
import string
import hashlib

def random_hostname() -> str:
    return 'S' + ''.join(random.choices(string.ascii_letters + string.digits, k=5))

def hash_string_to_int(s: str, mod: int = 1_000_000) -> int:
    h = hashlib.sha256(s.encode()).hexdigest()
    return int(h, 16) % mod