"""A stand-in SC25 WebSocket server that mimics the observed device behaviour.

Initial state is what a real SC25 (firmware 10102) sent on 2026-10-16.
Behaviour reproduced on purpose:
* full state burst on connect, as two arrays
* every reply is broadcast to all clients; commands are echoed with from=USER
* writes are not acknowledged
* a mode change pushes CCV again shortly after (the "stale CCV" quirk)
"""

from __future__ import annotations

import asyncio
import copy
import json
from typing import Any

from aiohttp import WSMsgType, web

MAC = "AA:BB:CC:DD:EE:01"

INITIAL: dict[str, dict[str, Any]] = {
    "USRDTA": {
        "name": "SC25_12345678",
        "aqName": "",
        "mode": "DAYCL_MODE",
        "version": 4,
        "language": "DE",
        "timezone": 60,
        "tID": 30,
        "dst": 1,
        "lights": '[{"id":0,"type":"unix"}]',
        "channelCount": 4,
        "netmode": "ST",
        "host": "sc25",
        "groupID": 1,
        "meshing": 1,
        "firstStart": 0,
        "revision": [10102, 10102],
        "latestAvailableRevision": [10102, 10102, 23, 15],
        "firmwareAvailable": 0,
        "usrName": "",
        "unit": 0,
        "demoUse": 0,
        "sysLED": 100,
        "moduleTemp": 37.9,
    },
    "MAX_CHANNEL_VALUES": {"maxPercValue": [0, 0, 0, 0], "wattageAt100": [0, 0, 0, 0]},
    "CLOCK": {
        "year": 2026,
        "month": 10,
        "day": 16,
        "hour": 0,
        "min": 15,
        "sec": 48,
        "mode": "DAYCL_MODE",
        "valid": 1,
    },
    "CCV": {"currentValues": [0, 0, 0, 0]},
    "MOON": {
        "maxmoonlight": 30,
        "minmoonlight": 5,
        "moonStart": 0,
        "moonEnd": 1439,
        "color": "[]",
        "moonlightActive": 0,
        "moonlightCycle": 1,
        "individualTimes": 0,
        "currentCycleDay": 19.7,
        "currentIntensity": 1,
    },
    "CLOUD": {
        "probability": 50,
        "maxAmount": 100,
        "minIntensity": 60,
        "maxIntensity": 100,
        "minDuration": 600,
        "maxDuration": 1500,
        "cloudActive": 0,
        "mode": 0,
        "isCloudActive": 0,
        "cloudRemaining": 0,
        "cloudCurrentIntensity": 100,
        "nextCloudStart": 0,
        "nextCloudDuration": 0,
    },
    "ACCLIMATE": {
        "duration": 30,
        "intensityReduction": 50,
        "currentAcclDay": 1,
        "acclActive": 0,
        "pause": 0,
        "currentAccReduction": 100,
    },
    "DSCRPTN": {
        "description": (
            "confId:10;expMode:false;start:480;end:1260;sunrise:60;sunset:60;intensity:100;"
            "individual:false;sunGlowEnabled:false;sunriseGlowDuration:30;sunriseGlowIntensity:1;"
            "sunsetGlowDuration:30;sunsetGlowIntensity:1;middayDimmingEnabled:false;"
            "middayDimmingStart:660;middayDimmingEnd:840;middayDimmingIntensity:60;"
            "intensities:100,0,0,0"
        )
    },
    "DYCL": {
        "configuration": [
            [0, 0, 0, 0, 0],
            [480, 0, 0, 0, 0],
            [540, 100, 100, 100, 100],
            [1200, 100, 100, 100, 100],
            [1260, 0, 0, 0, 0],
            [1440, 0, 0, 0, 0],
        ]
    },
    "SCNR": {"scenarios": [{"name": "", "icon": "", "channels": [0, 0, 0, 0]} for _ in range(10)]},
    "NET_ST": {
        "dhcp": 1,
        "ip": [192, 168, 1, 50],
        "gateway": [192, 168, 1, 1],
        "subaddress": [255, 255, 255, 0],
        "stSSID": "Aquarium-WLAN",
        "stPW": "Yes",
        "bssidST": "",
    },
    "NET_AP": {"apSSID": "SC25-12345678"},
    "MESH_NETWORK": {"clientList": [MAC]},
}

GET = {
    "GET_USRDTA": "USRDTA",
    "GET_CLOCK": "CLOCK",
    "REQ_CCV": "CCV",
    "GET_MOON": "MOON",
    "GET_CLOUD": "CLOUD",
    "GET_ACCL": "ACCLIMATE",
    "GET_DSCRPTN": "DSCRPTN",
    "GET_DYCL": "DYCL",
    "GET_SCNR": "SCNR",
    "GET_NET_ST": "NET_ST",
    "GET_NET_AP": "NET_AP",
    "GET_MESH_NETWORK": "MESH_NETWORK",
}
SETTINGS = {"MOON", "CLOUD", "ACCLIMATE", "DSCRPTN", "DYCL", "SCNR"}


class FakeSC25:
    def __init__(self) -> None:
        self.state = copy.deepcopy(INITIAL)
        self.clients: set[web.WebSocketResponse] = set()
        self.received: list[dict[str, Any]] = []
        self._runner: web.AppRunner | None = None
        self.port = 0
        self.stale_ccv_delay = 0.15

    @property
    def host(self) -> str:
        return f"127.0.0.1:{self.port}"

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/ws", self._ws)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        for ws in list(self.clients):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()

    def frame(self, title: str) -> dict[str, Any]:
        return {"title": title, "from": MAC, **copy.deepcopy(self.state[title]), "to": "USER"}

    async def _broadcast(self, payload: Any) -> None:
        data = json.dumps(payload)
        for ws in list(self.clients):
            if not ws.closed:
                await ws.send_str(data)

    async def _ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=("arduino",))
        await ws.prepare(request)
        self.clients.add(ws)
        await ws.send_str(
            json.dumps(
                [
                    self.frame(t)
                    for t in (
                        "USRDTA",
                        "MAX_CHANNEL_VALUES",
                        "CLOCK",
                        "NET_ST",
                        "NET_AP",
                        "MESH_NETWORK",
                    )
                ]
            )
        )
        await ws.send_str(
            json.dumps(
                [
                    self.frame(t)
                    for t in ("CCV", "MOON", "CLOUD", "ACCLIMATE", "DSCRPTN", "DYCL", "SCNR")
                ]
            )
        )
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle(json.loads(msg.data))
        finally:
            self.clients.discard(ws)
        return ws

    def _mode_frame(self) -> dict[str, Any]:
        clock = self.state["CLOCK"]
        frame = {"title": "CCMODE", "from": MAC, "mode": clock["mode"], "to": "USER"}
        if clock["mode"] == "MAN_MODE":
            frame.update({k: clock[k] for k in ("duration", "fallbackActive", "remaining")})
        return frame

    async def _handle(self, packet: dict[str, Any]) -> None:
        self.received.append(packet)
        await self._broadcast(packet)  # echo (from=USER) like the real device
        title = packet.get("title")
        body = {k: v for k, v in packet.items() if k not in ("title", "from", "to")}
        if title in GET:
            await self._broadcast(self.frame(GET[title]))
        elif title == "GET_CCMODE":
            await self._broadcast(self._mode_frame())
        elif title in ("MAN_MODE", "DAYCL_MODE"):
            clock = self.state["CLOCK"]
            clock["mode"] = title
            self.state["USRDTA"]["mode"] = title
            for key in ("duration", "fallbackActive", "remaining"):
                clock.pop(key, None)
            if title == "MAN_MODE":
                clock["duration"] = body.get("duration", 300)
                clock["fallbackActive"] = bool(body.get("fallbackActive"))
                clock["remaining"] = clock["duration"] - 2 if clock["fallbackActive"] else -1
            else:
                self.state["CCV"]["currentValues"] = [0, 0, 0, 0]
            stale = self.frame("CCV")

            async def push_stale() -> None:
                await asyncio.sleep(self.stale_ccv_delay)
                await self._broadcast(stale)

            asyncio.get_running_loop().create_task(push_stale())
        elif title in ("CCV-SL", "CCV-SW"):
            if self.state["CLOCK"]["mode"] == "MAN_MODE":
                self.state["CCV"]["currentValues"] = list(body["currentValues"])
        elif title == "PAUSE_ACCLIMATION":
            self.state["ACCLIMATE"]["pause"] = body.get("pause", 0)
        elif title in SETTINGS:
            self.state[title].update(body)
        elif title == "USRDTA":
            self.state["USRDTA"].update(body)
        elif title == "CLOCK":
            self.state["CLOCK"].update(body)
        # PREV-CRV and unknown titles: accepted silently.

    def sent(self, title: str) -> list[dict[str, Any]]:
        return [p for p in self.received if p.get("title") == title]
