"""WebSocket client for the daytime Smart Control SC25.

Protocol (reverse engineered from the device web app, firmware 10102):

* ``ws://<host>/ws`` with sub-protocol ``arduino``, one JSON object or a JSON
  array of objects per frame, no authentication.
* On connect the device pushes its full state unprompted.
* Every frame is broadcast to all connected clients, including commands sent
  by other clients. Those carry ``"from": "USER"`` and are dropped.
* Writes are never acknowledged; state is confirmed by re-reading.
* Channel arrays always have four entries in the order White, Blue, Red,
  Green, integer percent 0-100.
"""

from __future__ import annotations

import asyncio
import collections
from collections.abc import Callable
import contextlib
from datetime import datetime
import json
import logging
import time
from typing import Any

import aiohttp

from .daycycle import DaycycleSettings, build_curve

_LOGGER = logging.getLogger(__name__)

CHANNELS = ("white", "blue", "red", "green")

MODE_DAYCYCLE = "DAYCL_MODE"
MODE_MANUAL = "MAN_MODE"

TO_MASTER = "MASTER"
TO_ALL_LIGHTS = "ALL-LIGHTS"
FROM_USER = "USER"

# Titles requested after (re)connecting if the connect burst does not arrive.
INITIAL_REQUESTS = (
    "GET_USRDTA",
    "GET_CLOCK",
    "REQ_CCV",
    "GET_DSCRPTN",
    "GET_DYCL",
    "GET_MOON",
    "GET_CLOUD",
    "GET_ACCL",
    "GET_SCNR",
    "GET_NET_ST",
)

FAVORITE_SLOTS = 10
SETTINGS_SETTLE = 0.7  # the vendor app waits this long before reading back

# Frames that make up a usable state; all arrive in the connect burst.
REQUIRED_TITLES = frozenset({"USRDTA", "CCV", "CLOCK"})

BURST_TIMEOUT = 3
KEEPALIVE_INTERVAL = 10
SLOW_POLL_EVERY = 6  # keepalive ticks between settings refreshes
MODE_SETTLE = 0.5
# After a CCMODE confirmation, CLOCK frames with another mode are stale replies
# that were already on their way; the device announces real changes via CCMODE.
MODE_GUARD = 3.0
RECONNECT_MIN = 2
RECONNECT_MAX = 60
CONNECT_TIMEOUT = 5  # per handshake attempt
START_TIMEOUT = 15  # first state, including one reconnect


class SC25Error(Exception):
    """Base error."""


class SC25ConnectionError(SC25Error):
    """The controller could not be reached."""


def iter_frames(payload: Any) -> list[dict[str, Any]]:
    """Normalise a decoded WebSocket payload into a list of frames."""
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [frame for frame in payload if isinstance(frame, dict)]
    return []


def clamp_percent(value: Any) -> int:
    """Clamp a value to an integer percentage."""
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return 0


class SC25State:
    """Last known state of the controller, keyed by frame title."""

    def __init__(self) -> None:
        self.frames: dict[str, dict[str, Any]] = {}
        self._mode_confirmed_at = -MODE_GUARD

    def update(self, frame: dict[str, Any]) -> None:
        title = frame.get("title")
        if title == "CLOCK":
            known = self.frames.get("CLOCK", {})
            if (
                time.monotonic() - self._mode_confirmed_at < MODE_GUARD
                and known.get("mode")
                and frame.get("mode") != known.get("mode")
            ):
                frame = {
                    **frame,
                    **{
                        k: known[k]
                        for k in ("mode", "duration", "fallbackActive", "remaining")
                        if k in known
                    },
                }
            self.frames["CLOCK"] = frame
            return
        if title == "CCMODE":
            self._mode_confirmed_at = time.monotonic()
            # Mode replies update the mode carried by CLOCK.
            clock = dict(self.frames.get("CLOCK", {}))
            clock.update({k: v for k, v in frame.items() if k not in ("title", "from", "to")})
            if frame.get("mode") == MODE_DAYCYCLE:
                for key in ("duration", "fallbackActive", "remaining"):
                    clock.pop(key, None)
            self.frames["CLOCK"] = clock
            return
        if title:
            self.frames[title] = frame

    def get(self, title: str) -> dict[str, Any]:
        return self.frames.get(title, {})

    @property
    def mac(self) -> str | None:
        return self.get("USRDTA").get("from")

    @property
    def name(self) -> str:
        usrdta = self.get("USRDTA")
        for key in ("aqName", "usrName", "name"):
            value = usrdta.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "SC25"

    @property
    def channel_count(self) -> int:
        try:
            count = int(self.get("USRDTA").get("channelCount", 4))
        except (TypeError, ValueError):
            count = 4
        return max(1, min(4, count))

    @property
    def revision(self) -> str | None:
        rev = self.get("USRDTA").get("revision")
        if isinstance(rev, list) and rev:
            return ".".join(str(part) for part in rev[:1])
        return None

    @property
    def mode(self) -> str | None:
        return self.get("CLOCK").get("mode") or self.get("USRDTA").get("mode")

    @property
    def manual_remaining(self) -> int | None:
        """Seconds until the manual mode falls back, None if not running."""
        clock = self.get("CLOCK")
        if clock.get("mode") != MODE_MANUAL or not clock.get("fallbackActive"):
            return None
        try:
            remaining = int(clock.get("remaining", -1))
        except (TypeError, ValueError):
            return None
        return remaining if remaining >= 0 else None

    @property
    def current_values(self) -> list[int]:
        values = self.get("CCV").get("currentValues") or []
        values = [clamp_percent(v) for v in values[:4]]
        return values + [0] * (4 - len(values))

    @property
    def daycycle(self) -> list[list[int]]:
        """Setpoints as [minute, white, blue, red, green]."""
        rows = self.get("DYCL").get("configuration") or []
        return [
            [int(row[0]), *(clamp_percent(v) for v in row[1:5])]
            for row in rows
            if isinstance(row, list) and len(row) >= 2
        ]

    @property
    def daycycle_settings(self) -> DaycycleSettings:
        return DaycycleSettings.parse(self.get("DSCRPTN").get("description"))

    @property
    def favorites(self) -> list[dict[str, Any]]:
        """The 10 favourite slots as {name, icon, channels}."""
        slots = self.get("SCNR").get("scenarios")
        slots = slots if isinstance(slots, list) else []
        result = []
        for i in range(FAVORITE_SLOTS):
            slot = slots[i] if i < len(slots) and isinstance(slots[i], dict) else {}
            channels = [clamp_percent(v) for v in (slot.get("channels") or [])[:4]]
            result.append(
                {
                    "name": str(slot.get("name") or ""),
                    "icon": str(slot.get("icon") or ""),
                    "channels": channels + [0] * (4 - len(channels)),
                }
            )
        return result

    @property
    def moon_channels(self) -> set[str]:
        """Channels used for moonlight, from the ``color`` code string."""
        color = self.get("MOON").get("color")
        codes = color if isinstance(color, str) else ""
        return {ch for ch in CHANNELS if ch[0] in codes}

    @property
    def module_temperature(self) -> float | None:
        value = self.get("USRDTA").get("moduleTemp")
        return float(value) if isinstance(value, (int, float)) else None


class SC25Client:
    """Persistent connection to one SC25 controller."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self.host = host
        self.state = SC25State()
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._runner: asyncio.Task | None = None
        self._listeners: list[Callable[[], None]] = []
        self._initial_state = asyncio.Event()
        self._waiters: dict[str, list[asyncio.Future]] = {}
        self._closing = False
        self._seen: set[str] = set()
        self._send_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        # Recent traffic for diagnostics: (monotonic time, direction, frame).
        self.trace: collections.deque[tuple[float, str, str]] = collections.deque(maxlen=200)
        self.last_command_at = 0.0  # monotonic time of the last light/mode command
        self.available = False

    @property
    def url(self) -> str:
        return f"ws://{self.host}/ws"

    # -- lifecycle -----------------------------------------------------

    async def start(self) -> None:
        """Connect and keep the connection alive in the background."""
        self._closing = False
        self._runner = asyncio.create_task(self._run(), name=f"sc25-{self.host}")
        try:
            await asyncio.wait_for(self._initial_state.wait(), START_TIMEOUT)
        except TimeoutError as err:
            await self.stop()
            raise SC25ConnectionError(f"No state received from {self.host}") from err

    async def stop(self) -> None:
        self._closing = True
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        if self._runner is not None:
            self._runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._runner
            self._runner = None

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return remove

    def _notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                _LOGGER.exception("Error in SC25 listener")

    async def _run(self) -> None:
        delay = RECONNECT_MIN
        while not self._closing:
            try:
                await self._connect_once()
                delay = RECONNECT_MIN
            except (aiohttp.ClientError, OSError, TimeoutError) as err:
                _LOGGER.debug("SC25 %s connection error: %s", self.host, err)
            if self._closing:
                break
            if self.available:
                _LOGGER.warning("Lost connection to SC25 at %s", self.host)
            self.available = False
            self._notify()
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)

    async def _connect_once(self) -> None:
        async with asyncio.timeout(CONNECT_TIMEOUT):
            ws = await self._session.ws_connect(
                self.url,
                protocols=("arduino",),
                timeout=aiohttp.ClientWSTimeout(ws_close=CONNECT_TIMEOUT),
                heartbeat=None,
                autoping=True,
            )
        self._ws = ws
        self._seen = set()
        tasks = [
            asyncio.create_task(self._bootstrap()),
            asyncio.create_task(self._keepalive()),
        ]
        try:
            while True:
                msg = await ws.receive(timeout=KEEPALIVE_INTERVAL * 3)
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._handle_text(msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break
        finally:
            for task in tasks:
                task.cancel()
            self._ws = None
            await ws.close()

    async def _bootstrap(self) -> None:
        # The device pushes its whole state on connect. Requesting it as well
        # is only a fallback: replies can overtake the burst, and the burst's
        # older CLOCK would then undo a mode change made in the meantime.
        await asyncio.sleep(BURST_TIMEOUT)
        if not self._seen >= REQUIRED_TITLES:
            _LOGGER.debug("SC25 %s sent no state burst, requesting it", self.host)
            for title in INITIAL_REQUESTS:
                await self.request(title)

    async def _keepalive(self) -> None:
        # The device only pushes on mode changes, so live output (which moves
        # during daycycle ramps) and the slower settings are polled. This also
        # detects dead sockets.
        tick = 0
        while True:
            await asyncio.sleep(KEEPALIVE_INTERVAL)
            await self.request("REQ_CCV")
            await self.request("GET_CLOCK")
            if tick % SLOW_POLL_EVERY == 0:
                for title in ("GET_USRDTA", "GET_MOON", "GET_CLOUD", "GET_ACCL", "GET_NET_ST"):
                    await self.request(title)
            tick += 1

    def _handle_text(self, data: str) -> None:
        self.trace.append((time.monotonic(), "<<", data[:300]))
        _LOGGER.debug("SC25 %s << %s", self.host, data[:300])
        try:
            payload = json.loads(data)
        except ValueError:
            _LOGGER.debug("Ignoring non-JSON frame: %s", data[:200])
            return
        changed = False
        for frame in iter_frames(payload):
            if frame.get("from") == FROM_USER:
                continue  # another client's command echoed back
            title = frame.get("title")
            if title in (None, "REQ_KEEP_ALIVE"):
                continue
            self._seen.add(title)
            self.state.update(frame)
            changed = True
            for future in self._waiters.pop(title, []):
                if not future.done():
                    future.set_result(frame)
        if changed:
            if not self.available and self._seen >= REQUIRED_TITLES:
                self.available = True
                self._initial_state.set()
            self._notify()

    # -- sending -------------------------------------------------------

    async def send(self, packet: dict[str, Any]) -> None:
        ws = self._ws
        if ws is None or ws.closed:
            raise SC25ConnectionError(f"Not connected to {self.host}")
        data = json.dumps(packet, separators=(",", ":"))
        self.trace.append((time.monotonic(), ">>", data[:300]))
        _LOGGER.debug("SC25 %s >> %s", self.host, data)
        async with self._send_lock:
            await ws.send_str(data)

    async def request(self, title: str, *, to: str = TO_MASTER) -> None:
        await self.send({"title": title, "to": to, "from": FROM_USER})

    async def request_and_wait(
        self, title: str, reply: str, *, to: str = TO_MASTER, timeout: float = 3
    ) -> dict[str, Any] | None:
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._waiters.setdefault(reply, []).append(future)
        await self.request(title, to=to)
        try:
            return await asyncio.wait_for(future, timeout)
        except TimeoutError:
            return None

    # -- commands ------------------------------------------------------

    async def set_mode(
        self,
        manual: bool,
        *,
        fallback_seconds: int | None = None,
    ) -> None:
        """Switch between manual and daycycle mode.

        With ``fallback_seconds`` (60-86400) the controller returns to the
        daycycle on its own after that time; ``None`` keeps manual mode.
        """
        if manual:
            packet: dict[str, Any] = {
                "title": MODE_MANUAL,
                "to": TO_ALL_LIGHTS,
                "from": FROM_USER,
                "duration": max(60, min(86400, fallback_seconds or 300)),
                "fallbackActive": fallback_seconds is not None,
            }
        else:
            packet = {"title": MODE_DAYCYCLE, "to": TO_ALL_LIGHTS, "from": FROM_USER}
        wanted = packet["title"]
        self.last_command_at = time.monotonic()
        for _ in range(3):
            await self.send(packet)
            # The reply can still carry the old mode if it overtakes the switch.
            for _ in range(3):
                await self.request_and_wait("GET_CCMODE", "CCMODE", to=TO_ALL_LIGHTS)
                if self.state.mode == wanted:
                    return
                await asyncio.sleep(0.3)
        _LOGGER.warning("SC25 %s did not confirm mode %s", self.host, wanted)

    async def set_channels(self, values: list[int], *, fallback_seconds: int | None = None) -> None:
        """Set all four channels (switches to manual mode if needed)."""
        values = [clamp_percent(v) for v in values[:4]]
        values += [0] * (4 - len(values))
        if self.state.mode != MODE_MANUAL:
            await self.set_mode(True, fallback_seconds=fallback_seconds)
            # The mode change makes the device push its old CCV a little later;
            # let that arrive before writing, or it overwrites the readback.
            await asyncio.sleep(MODE_SETTLE)
        self.last_command_at = time.monotonic()
        for _ in range(3):
            await self.send(
                {
                    "title": "CCV-SL",
                    "to": TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "currentValues": values,
                }
            )
            reply = await self.request_and_wait("REQ_CCV", "CCV")
            if reply and self.state.current_values == values:
                return
            if self.state.mode != MODE_MANUAL:
                # Values are ignored outside manual mode, e.g. after a fallback.
                await self.set_mode(True, fallback_seconds=fallback_seconds)
            await asyncio.sleep(MODE_SETTLE)
        _LOGGER.warning("SC25 %s did not confirm values %s", self.host, values)

    async def _write_settings(self, title: str, request: str, changes: dict[str, Any]) -> None:
        """Send a settings frame built from the last known one plus changes."""
        async with self._write_lock:
            current = self.state.get(title)
            if not current:
                current = await self.request_and_wait(request, title) or {}
            if not current:
                raise SC25Error(f"{title} state unknown, refusing to write")
            packet = {
                k: v
                for k, v in current.items()
                if k not in ("title", "from", "to") and not _is_status_field(title, k)
            }
            packet.update(changes)
            packet.update({"title": title, "to": TO_ALL_LIGHTS, "from": FROM_USER})
            await self.send(packet)
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait(request, title)

    async def set_moon(self, **changes: Any) -> None:
        """Change MOON fields (wire names: moonlightActive, maxmoonlight, ...)."""
        await self._write_settings("MOON", "GET_MOON", changes)

    async def set_moon_channel(self, channel: str, enabled: bool) -> None:
        active = set(self.state.moon_channels)
        active.add(channel) if enabled else active.discard(channel)
        # Keep the vendor app's order (w, b, r, g).
        await self.set_moon(color="".join(ch[0] for ch in CHANNELS if ch in active))

    async def set_cloud(self, **changes: Any) -> None:
        """Change CLOUD fields in wire units (seconds, remaining-light %)."""
        await self._write_settings("CLOUD", "GET_CLOUD", changes)

    async def set_acclimation(self, **changes: Any) -> None:
        await self._write_settings("ACCLIMATE", "GET_ACCL", changes)

    async def set_moonlight(self, active: bool) -> None:
        await self.set_moon(moonlightActive=1 if active else 0)

    async def set_clouds(self, active: bool) -> None:
        await self.set_cloud(cloudActive=1 if active else 0)

    async def set_acclimation_active(self, active: bool) -> None:
        await self.set_acclimation(acclActive=1 if active else 0)

    async def set_acclimation_paused(self, paused: bool) -> None:
        async with self._write_lock:
            await self.send(
                {
                    "title": "PAUSE_ACCLIMATION",
                    "to": TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "pause": 1 if paused else 0,
                }
            )
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait("GET_ACCL", "ACCLIMATE")

    async def set_daycycle_settings(self, **changes: Any) -> None:
        """Change easy-mode settings and write the matching curve.

        Leaves expert mode: the curve is rebuilt from the settings.
        """
        settings = self.state.daycycle_settings.with_changes(expert_mode=False, **changes)
        curve = build_curve(settings, self.state.channel_count)  # validates
        await self._write_daycycle(settings, curve)

    async def set_daycycle_curve(self, curve: list[list[int]]) -> None:
        """Write a free-form curve (expert mode)."""
        rows = sorted(
            [int(r[0]), *(clamp_percent(v) for v in (list(r[1:5]) + [0] * 4)[:4])] for r in curve
        )
        if len(rows) < 2 or rows[0][0] != 0 or rows[-1][0] != 1440:
            raise ValueError("Die Kurve muss bei Minute 0 beginnen und bei 1440 enden.")
        if len({r[0] for r in rows}) != len(rows):
            raise ValueError("Jede Minute darf nur einmal vorkommen.")
        settings = self.state.daycycle_settings.with_changes(expert_mode=True)
        await self._write_daycycle(settings, rows)

    async def _write_daycycle(self, settings: DaycycleSettings, curve: list[list[int]]) -> None:
        async with self._write_lock:
            await self.send(
                {
                    "title": "DSCRPTN",
                    "to": TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "description": settings.encode(),
                }
            )
            await self.send(
                {
                    "title": "DYCL",
                    "to": TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "configuration": curve,
                }
            )
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait("GET_DSCRPTN", "DSCRPTN")
            await self.request_and_wait("GET_DYCL", "DYCL")

    async def save_favorite(self, slot: int, name: str, channels: list[int] | None = None) -> None:
        """Store ``channels`` (default: current output) in slot 1-10."""
        if not 1 <= slot <= FAVORITE_SLOTS:
            raise ValueError("Favoriten-Platz muss zwischen 1 und 10 liegen.")
        values = channels if channels is not None else self.state.current_values
        values = [clamp_percent(v) for v in values[:4]] + [0] * (4 - len(values[:4]))
        favorites = self.state.favorites
        favorites[slot - 1] = {
            "name": name.strip()[:32],
            "icon": favorites[slot - 1]["icon"],
            "channels": values,
        }
        await self._write_favorites(favorites)

    async def delete_favorite(self, slot: int) -> None:
        if not 1 <= slot <= FAVORITE_SLOTS:
            raise ValueError("Favoriten-Platz muss zwischen 1 und 10 liegen.")
        favorites = self.state.favorites
        favorites[slot - 1] = {"name": "", "icon": "", "channels": [0, 0, 0, 0]}
        await self._write_favorites(favorites)

    async def _write_favorites(self, favorites: list[dict[str, Any]]) -> None:
        async with self._write_lock:
            await self.send(
                {"title": "SCNR", "to": "ALL", "from": FROM_USER, "scenarios": favorites}
            )
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait("GET_SCNR", "SCNR")

    async def set_name(self, name: str) -> None:
        async with self._write_lock:
            await self.send(
                {
                    "title": "USRDTA",
                    "to": self.state.mac or TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "name": name.strip()[:32],
                }
            )
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait("GET_USRDTA", "USRDTA")

    async def sync_clock(self, now: datetime) -> None:
        """Set the controller clock to local wall time ``now``."""
        async with self._write_lock:
            await self.send(
                {
                    "title": "CLOCK",
                    "to": TO_ALL_LIGHTS,
                    "from": FROM_USER,
                    "year": now.year,
                    "month": now.month,  # 1-based on the wire, like Python
                    "day": now.day,
                    "hour": now.hour,
                    "min": now.minute,
                    "sec": now.second,
                }
            )
            await asyncio.sleep(SETTINGS_SETTLE)
            await self.request_and_wait("GET_CLOCK", "CLOCK")

    async def preview_daycycle(self, *, seconds: int = 80, start: int = 0, end: int = 1439) -> None:
        """Play the daycycle in fast motion; the device returns on its own."""
        await self.send(
            {
                "title": "PREV-CRV",
                "to": "ALL",
                "from": FROM_USER,
                "previewTime": max(10, min(600, int(seconds))),
                "startTime": max(0, min(1438, int(start))),
                "endTime": max(1, min(1439, int(end))),
            }
        )


# Read-only runtime fields the device adds to settings frames.
_STATUS_FIELDS = {
    "MOON": {"currentCycleDay", "currentIntensity"},
    "CLOUD": {
        "isCloudActive",
        "cloudRemaining",
        "cloudCurrentIntensity",
        "nextCloudStart",
        "nextCloudDuration",
    },
    "ACCLIMATE": {"currentAccReduction"},
}


def _is_status_field(title: str, key: str) -> bool:
    return key in _STATUS_FIELDS.get(title, set())
