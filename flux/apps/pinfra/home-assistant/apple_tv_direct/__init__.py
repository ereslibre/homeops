"""Connect the Apple TV integration to devices it cannot discover.

The built-in apple_tv integration only connects to a device it has just found
over mDNS. The Apple TV ignores unicast mDNS queries coming from another
subnet, and multicast never reaches the pod network, so from the Home
Assistant pod the device is never found although its address (a static DHCP
mapping) is perfectly reachable. This wraps the integration's scan so that,
when it comes back empty, a Companion config is built from the address and
credentials stored in the config entry. The Companion port changes on reboot,
so it is found by trying to authenticate against the candidate ports.
"""

import asyncio
import logging

from pyatv import connect
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol

from homeassistant.components.apple_tv import AppleTVManager
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "apple_tv_direct"
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

# Companion is served from the dynamic port range; seen on 49152-49156.
COMPANION_PORTS = range(49152, 49171)
PROBE_TIMEOUT = 1
VERIFY_TIMEOUT = 10

_LOGGER = logging.getLogger(__name__)

# Last port that worked, per config entry, tried first next time.
_ports: dict[str, int] = {}


def _config(entry: ConfigEntry, port: int, credentials: str | None = None) -> AppleTV:
    conf = AppleTV(entry.data[CONF_ADDRESS], entry.data[CONF_NAME])
    conf.add_service(
        ManualService(entry.unique_id, Protocol.Companion, port, {}, credentials=credentials)
    )
    return conf


async def _is_open(address: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port), PROBE_TIMEOUT
        )
    except (OSError, TimeoutError):
        return False
    writer.close()
    return True


async def _verify(hass: HomeAssistant, entry: ConfigEntry, port: int, credentials: str) -> bool:
    """Whether the Companion credentials authenticate on this port."""
    try:
        atv = await asyncio.wait_for(
            connect(_config(entry, port, credentials), hass.loop), VERIFY_TIMEOUT
        )
    except Exception:  # noqa: BLE001 - any failure just means "not this port"
        return False
    atv.close()
    return True


async def _find(hass: HomeAssistant, entry: ConfigEntry) -> AppleTV | None:
    stored = entry.data.get("credentials", {})
    credentials = stored.get(str(Protocol.Companion.value)) or stored.get(
        Protocol.Companion.value
    )
    if not credentials:
        return None

    address = entry.data[CONF_ADDRESS]
    open_ports = [
        port
        for port, is_open in zip(
            COMPANION_PORTS,
            await asyncio.gather(*(_is_open(address, p) for p in COMPANION_PORTS)),
        )
        if is_open
    ]
    if (last := _ports.get(entry.entry_id)) in open_ports:
        open_ports.remove(last)
        open_ports.insert(0, last)

    for port in open_ports:
        if await _verify(hass, entry, port, credentials):
            _ports[entry.entry_id] = port
            _LOGGER.debug("%s: Companion found on %s:%d", entry.title, address, port)
            # The integration sets the credentials itself before connecting.
            return _config(entry, port)

    _LOGGER.debug("%s: no Companion port answered on %s (open: %s)", entry.title, address, open_ports)
    return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Make the apple_tv integration fall back to a direct connection."""
    scan = AppleTVManager._scan
    if getattr(scan, "_apple_tv_direct", False):
        return True

    async def _scan(self: AppleTVManager) -> AppleTV | None:
        if conf := await scan(self):
            return conf
        return await _find(self.hass, self.config_entry)

    _scan._apple_tv_direct = True
    AppleTVManager._scan = _scan
    return True
