from collections import abc
from simbricks.schemas import base as schemas

async def send_events(
    write: abc.Callable[[bytes], abc.Awaitable[None]],
    events: schemas.ApiEventBundle,
    event_type: schemas.ApiEventType,
) -> None:
    events_json = events.model_dump_json()
    payload = bytes(f"{event_type.value},{events_json}", encoding="utf-8")
    data = bytes(f"{len(payload):12x}", encoding="utf-8") + payload
    await write(data)

async def _read_all(read: abc.Callable[[int], abc.Awaitable[bytes]], length: int) -> bytes:
    assert length >= 0
    data = bytes()
    while len(data) < length:
        d = await read(length - len(data))
        if (length - len(data)) != 0 and len(d) == 0:
            raise RuntimeError("connection broken")
        data += d
    return data

async def get_events(
        read: abc.Callable[[int], abc.Awaitable[bytes]]
) -> tuple[schemas.ApiEventType, schemas.ApiEventBundle]:
    length_str = (await _read_all(read, 12)).decode("utf-8")
    length = int(length_str, 16)
    payload = (await _read_all(read, length)).decode("utf-8")

    separator = payload.find(",")
    if separator == -1:
        raise RuntimeError("invalid format of event bundle payload")

    event_type = schemas.ApiEventType(payload[:separator])
    events_json = payload[separator+1:]
    events = schemas.ApiEventBundle[event_type.get_type()].model_validate_json(events_json)

    return (event_type, events)