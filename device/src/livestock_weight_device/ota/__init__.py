"""OTA update stubs — safe no-ops without a signed manifest URL. See docs/OTA.md."""

from .client import OtaClient, OtaStatus, check_for_update, apply_update

__all__ = ["OtaClient", "OtaStatus", "check_for_update", "apply_update"]
