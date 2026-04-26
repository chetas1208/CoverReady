from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from coverready_api.config.settings import Settings


logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15
RECENT_EVENT_LIMIT = 25


@dataclass(frozen=True)
class WorkspaceEvent:
    event_type: str
    workspace_id: str
    payload: dict[str, Any]
    created_at: float

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": self.event_type,
                "workspace_id": self.workspace_id,
                "payload": self.payload,
                "created_at": self.created_at,
            },
            sort_keys=True,
            default=str,
        )


_SUBSCRIBERS: dict[str, set[asyncio.Queue[WorkspaceEvent]]] = defaultdict(set)
_RECENT_EVENTS: dict[str, deque[WorkspaceEvent]] = defaultdict(lambda: deque(maxlen=RECENT_EVENT_LIMIT))


def _channel(workspace_id: str) -> str:
    return f"coverready.workspace.{workspace_id}.events"


def publish_workspace_event(
    settings: Settings,
    workspace_id: str | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not workspace_id:
        return
    event = WorkspaceEvent(
        event_type=event_type,
        workspace_id=workspace_id,
        payload=payload or {},
        created_at=time.time(),
    )
    _RECENT_EVENTS[workspace_id].append(event)

    for queue in list(_SUBSCRIBERS.get(workspace_id, set())):
        with suppress(asyncio.QueueFull):
            queue.put_nowait(event)

    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.publish(_channel(workspace_id), event.to_json())
        client.close()
    except Exception as exc:
        logger.debug("Skipping Redis event publish.", extra={"workspace_id": workspace_id, "event_type": event_type, "error": str(exc)})


def format_sse(event: WorkspaceEvent) -> str:
    return f"event: {event.event_type}\ndata: {event.to_json()}\n\n"


async def workspace_event_stream(settings: Settings, workspace_id: str, *, replay_only: bool = False) -> AsyncIterator[str]:
    queue: asyncio.Queue[WorkspaceEvent] = asyncio.Queue(maxsize=100)
    _SUBSCRIBERS[workspace_id].add(queue)

    redis_pubsub = None
    try:
        redis_pubsub = await _open_redis_pubsub(settings, workspace_id)
        for event in list(_RECENT_EVENTS.get(workspace_id, [])):
            yield format_sse(event)
        if replay_only:
            return

        while True:
            redis_task = None
            queue_task = asyncio.create_task(queue.get())
            if redis_pubsub is not None:
                redis_task = asyncio.create_task(redis_pubsub.get_message(ignore_subscribe_messages=True, timeout=HEARTBEAT_SECONDS))
            tasks = [queue_task, *([redis_task] if redis_task else [])]
            done, pending = await asyncio.wait(tasks, timeout=HEARTBEAT_SECONDS, return_when=asyncio.FIRST_COMPLETED)

            for task in pending:
                task.cancel()

            if not done:
                yield ": ping\n\n"
                continue

            emitted = False
            for task in done:
                result = task.result()
                if isinstance(result, WorkspaceEvent):
                    yield format_sse(result)
                    emitted = True
                elif isinstance(result, dict) and result.get("data"):
                    event = _event_from_redis_message(result)
                    if event and event.workspace_id == workspace_id:
                        yield format_sse(event)
                        emitted = True
            if not emitted:
                yield ": ping\n\n"
    finally:
        _SUBSCRIBERS[workspace_id].discard(queue)
        if redis_pubsub is not None:
            with suppress(Exception):
                await redis_pubsub.unsubscribe(_channel(workspace_id))
                await redis_pubsub.close()


async def _open_redis_pubsub(settings: Settings, workspace_id: str):
    try:
        import redis.asyncio as aioredis

        client = aioredis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        pubsub = client.pubsub()
        await pubsub.subscribe(_channel(workspace_id))
        return pubsub
    except Exception as exc:
        logger.debug("Redis SSE subscription unavailable; using local stream only.", extra={"workspace_id": workspace_id, "error": str(exc)})
        return None


def _event_from_redis_message(message: dict[str, Any]) -> WorkspaceEvent | None:
    raw = message.get("data")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    if not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
        return WorkspaceEvent(
            event_type=payload["type"],
            workspace_id=payload["workspace_id"],
            payload=payload.get("payload") or {},
            created_at=float(payload.get("created_at") or time.time()),
        )
    except Exception:
        return None
