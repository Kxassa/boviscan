"""LAN discovery: UDP beacon (implemented) and mDNS notes (documented)."""

from .udp_beacon import BeaconPayload, start_udp_beacon, stop_udp_beacon

__all__ = ["BeaconPayload", "start_udp_beacon", "stop_udp_beacon"]
