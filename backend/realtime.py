import json
import queue
import threading

_SUBSCRIBERS = {}
_LOCK = threading.Lock()


def subscribe(household_id):
    household_id = int(household_id)
    channel = queue.Queue(maxsize=200)
    with _LOCK:
        _SUBSCRIBERS.setdefault(household_id, []).append(channel)
    return channel


def unsubscribe(household_id, channel):
    household_id = int(household_id)
    with _LOCK:
        channels = _SUBSCRIBERS.get(household_id, [])
        if channel in channels:
            channels.remove(channel)
        if not channels:
            _SUBSCRIBERS.pop(household_id, None)


def publish_event(household_id, event):
    household_id = int(household_id)
    with _LOCK:
        channels = list(_SUBSCRIBERS.get(household_id, []))

    for channel in channels:
        try:
            channel.put_nowait(event)
        except queue.Full:
            try:
                channel.get_nowait()
                channel.put_nowait(event)
            except (queue.Empty, queue.Full):
                pass


def sse_stream(household_id, channel):
    try:
        while True:
            try:
                event = channel.get(timeout=25)
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
            except queue.Empty:
                yield ": ping\n\n"
    finally:
        unsubscribe(household_id, channel)
