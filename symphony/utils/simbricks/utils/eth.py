import random


def rand_mac() -> list[int]:
    mac_b = [
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
    ]
    return mac_b


def rand_mac_s() -> str:
    mac_bytes = rand_mac()
    mac = ":".join(f"{byte:02x}" for byte in mac_bytes)
    return mac
