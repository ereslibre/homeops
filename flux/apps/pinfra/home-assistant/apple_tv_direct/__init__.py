"""Connect the Apple TV integration to devices it cannot discover.

The built-in apple_tv integration only connects to a device it has just found
over mDNS. The Apple TV ignores unicast mDNS queries coming from another
subnet, and multicast never reaches the pod network, so from the Home
Assistant pod the device is never found although its address (a static DHCP
mapping) is perfectly reachable. This wraps the integration's scan so that,
when it comes back empty, a Companion config is built from the address and
credentials stored in the config entry. The Companion port changes on reboot,
so it is found by trying to authenticate against the candidate ports.

AirPlay (which tunnels the MRP protocol that reports what is playing) can be
added per address with credentials paired outside Home Assistant, since the
integration's own pairing flow also depends on discovery:

    apple_tv_direct:
      10.0.1.35:
        airplay_credentials: !env_var APPLE_TV_AIRPLAY_CREDENTIALS
        airplay_properties:  # the device's _airplay._tcp TXT record
          features: "0x4A7FDFD5,0x3C177FDE"
"""

import asyncio
import logging

import voluptuous as vol

from pyatv import connect
from pyatv.conf import AppleTV, ManualService
from pyatv.const import Protocol

from homeassistant.components.apple_tv import AppleTVManager
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "apple_tv_direct"
CONF_AIRPLAY_CREDENTIALS = "airplay_credentials"
CONF_AIRPLAY_PROPERTIES = "airplay_properties"
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Any(
            None,
            {
                cv.string: {
                    vol.Required(CONF_AIRPLAY_CREDENTIALS): cv.string,
                    vol.Optional(CONF_AIRPLAY_PROPERTIES, default={}): {
                        cv.string: cv.string
                    },
                }
            },
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Companion is served from the dynamic port range; seen on 49152-49156.
COMPANION_PORTS = range(49152, 49171)
AIRPLAY_PORT = 7000
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


async def _find(
    hass: HomeAssistant, entry: ConfigEntry, devices: dict[str, dict]
) -> AppleTV | None:
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
            # The integration sets the Companion credentials itself before
            # connecting.
            return _config(entry, port)

    _LOGGER.debug("%s: no Companion port answered on %s (open: %s)", entry.title, address, open_ports)
    return None


def _add_airplay(conf: AppleTV, entry: ConfigEntry, devices: dict[str, dict]) -> None:
    """Add AirPlay to the config, with the credentials paired outside HA.

    AirPlay is not in the entry, so the integration only scans for Companion
    and never sets AirPlay credentials; without this, a device found by the
    integration's own scan (e.g. over the mDNS reflector) is connected over
    Companion only, which reports power but never what is playing.
    """
    if not (airplay := devices.get(entry.data[CONF_ADDRESS])):
        return
    if service := conf.get_service(Protocol.AirPlay):
        service.credentials = airplay[CONF_AIRPLAY_CREDENTIALS]
        return
    conf.add_service(
        ManualService(
            entry.unique_id,
            Protocol.AirPlay,
            AIRPLAY_PORT,
            airplay[CONF_AIRPLAY_PROPERTIES],
            credentials=airplay[CONF_AIRPLAY_CREDENTIALS],
        )
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Make the apple_tv integration fall back to a direct connection."""
    devices = config.get(DOMAIN) or {}
    scan = AppleTVManager._scan
    if getattr(scan, "_apple_tv_direct", False):
        return True

    async def _scan(self: AppleTVManager) -> AppleTV | None:
        conf = await scan(self) or await _find(self.hass, self.config_entry, devices)
        if conf:
            _add_airplay(conf, self.config_entry, devices)
        return conf

    _scan._apple_tv_direct = True
    AppleTVManager._scan = _scan

    # apple_tv is a dependency, so its entries were set up (and may already
    # be connected through the unpatched scan, without AirPlay) before this
    # ran; reconnect them through the patched one.
    for entry in hass.config_entries.async_entries("apple_tv"):
        if entry.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS):
            hass.config_entries.async_schedule_reload(entry.entry_id)
    return True
