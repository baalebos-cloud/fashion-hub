"""
Minimal in-process event publisher. Kept intentionally simple (no external
message broker) for the modular-monolith phase -- Celery already provides
durable async dispatch for anything that needs to survive a process
restart (see app/workers/). This publisher exists so services can emit a
named event without hard-coding which notification/audit/webhook side
effects should run, making it easy to add new subscribers later without
touching the emitting service.
"""
from collections import defaultdict
from typing import Callable

_SUBSCRIBERS: dict[str, list[Callable]] = defaultdict(list)


def publish(event_name: str, **payload) -> None:
    for handler in _SUBSCRIBERS.get(event_name, []):
        handler(**payload)


def subscribe(event_name: str, handler: Callable) -> None:
    _SUBSCRIBERS[event_name].append(handler)
