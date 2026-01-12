import json
from typing import get_args
from collections import abc

from simbricks.client.namespace import EventFromRunner_U, EventToRunner_U


def __event_to_dict(event: EventToRunner_U | EventToRunner_U) -> dict:
    assert hasattr(event, "to_dict")
    return {"type": event.__class__.__name__, "data": event.to_dict()}


def __event_from_dict(event_dict: dict) -> EventToRunner_U | EventFromRunner_U:
    assert "type" in event_dict
    assert "data" in event_dict

    ty = event_dict["type"]
    data = event_dict["data"]

    types_to_check = get_args(EventFromRunner_U)
    types_to_check += get_args(EventToRunner_U)
    for model_type in types_to_check:
        if model_type.__name__ == ty:
            assert hasattr(model_type, "from_dict")
            event = model_type.from_dict(data)
            return event

    raise Exception(f"Cannot resolve event dict: {event_dict}")


async def send_events(
    write: abc.Callable[[bytes], abc.Awaitable[None]],
    events: list[EventToRunner_U] | list[EventFromRunner_U],
) -> None:
    events = [__event_to_dict(event) for event in events]
    events_json = json.dumps(events)
    data = bytes(f"{len(events_json):12x},{events_json}", encoding="utf-8")
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
    read: abc.Callable[[int], abc.Awaitable[bytes]],
) -> list[EventFromRunner_U] | list[EventToRunner_U]:

    length_str = (await _read_all(read, 12)).decode("utf-8")
    length = int(length_str, 16)
    payload = (await _read_all(read, length)).decode("utf-8")

    separator = payload.find(",")
    if separator == -1:
        raise RuntimeError("invalid format of event bundle payload")

    events_json = json.loads(payload[separator + 1 :])
    events = [__event_from_dict(event) for event in events_json]

    return events
