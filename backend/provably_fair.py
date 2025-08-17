import hmac, hashlib, os, binascii
from math import floor

# Gera seeds e hash para provar justiça (revelar server_seed depois)
def generate_server_seed():
    seed = binascii.hexlify(os.urandom(32)).decode()
    seed_hash = hashlib.sha256(seed.encode()).hexdigest()
    return seed, seed_hash


def derive_float_0_1(server_seed: str, client_seed: str, nonce: int, cursor: int):
    # HMAC(server_seed, f"{client_seed}:{nonce}:{cursor}") -> bytes -> número [0,1)
    msg = f"{client_seed}:{nonce}:{cursor}".encode()
    digest = hmac.new(server_seed.encode(), msg, hashlib.sha256).digest()
    # usa 8 bytes para formar inteiro
    val = int.from_bytes(digest[:8], 'big')
    return (val / (1 << 64))


def pick_index(n: int, **kw):
    r = derive_float_0_1(**kw)
    return floor(r * n)