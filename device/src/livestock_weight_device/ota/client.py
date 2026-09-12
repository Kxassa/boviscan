"""OTA check/apply interfaces for Pi devices (stubs).

Without LW_OTA_MANIFEST_URL these methods no-op safely and never download
or replace binaries. Real signing flow is documented in docs/OTA.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OtaStatus:
    update_available: bool = False
    current_version: str = "0.1.0"
    candidate_version: str | None = None
    manifest_url: str | None = None
    reason: str = "no_manifest_url"
    verified: bool = False
    applied: bool = False
    rollback_ready: bool = False
    details: dict[str, Any] = field(default_factory=dict)


class OtaClient:
    def __init__(
        self,
        *,
        current_version: str = "0.1.0",
        manifest_url: str | None = None,
        public_key_path: str | None = None,
    ) -> None:
        self.current_version = current_version
        self.manifest_url = manifest_url or os.environ.get("LW_OTA_MANIFEST_URL")
        self.public_key_path = public_key_path or os.environ.get("LW_OTA_PUBLIC_KEY")

    def check_for_update(self) -> OtaStatus:
        if not self.manifest_url:
            return OtaStatus(
                update_available=False,
                current_version=self.current_version,
                manifest_url=None,
                reason="no_manifest_url",
                details={"hint": "Set LW_OTA_MANIFEST_URL to enable OTA checks (see docs/OTA.md)"},
            )
        # Stub: do not fetch or trust remote content without signed verification path
        return OtaStatus(
            update_available=False,
            current_version=self.current_version,
            candidate_version=None,
            manifest_url=self.manifest_url,
            reason="stub_no_fetch",
            verified=False,
            details={
                "note": "Manifest URL configured but fetch/verify not implemented in this stub",
                "public_key_configured": bool(self.public_key_path),
            },
        )

    def apply_update(self, *, force: bool = False) -> OtaStatus:
        status = self.check_for_update()
        if not status.update_available and not force:
            status.reason = status.reason if status.reason != "stub_no_fetch" else "nothing_to_apply"
            status.applied = False
            return status
        # Never apply without verified signed manifest
        return OtaStatus(
            update_available=False,
            current_version=self.current_version,
            manifest_url=self.manifest_url,
            reason="refused_unsigned_or_stub",
            verified=False,
            applied=False,
            rollback_ready=False,
            details={"force": force, "note": "Apply is a safe no-op until signing is wired"},
        )


def check_for_update(current_version: str = "0.1.0") -> OtaStatus:
    return OtaClient(current_version=current_version).check_for_update()


def apply_update(current_version: str = "0.1.0", force: bool = False) -> OtaStatus:
    return OtaClient(current_version=current_version).apply_update(force=force)
