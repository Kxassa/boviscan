#!/usr/bin/env python3
"""Firestore soak helper for boviscan-c2430.

Default: dry-run probe (credentials / emulator / library presence).
Optional: --write one test doc to device_health when credentials allow.

Never prints secret material. No credentials committed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DEFAULT = "boviscan-c2430"
COL_HEALTH = "device_health"
COL_SESSIONS = "weighing_sessions"
TEST_DEVICE = "soak-device-check"


def _env_report() -> dict:
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    creds_path = Path(creds) if creds else None
    return {
        "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("FIREBASE_PROJECT_ID")
        or PROJECT_DEFAULT,
        "FIRESTORE_EMULATOR_HOST": os.environ.get("FIRESTORE_EMULATOR_HOST"),
        "GOOGLE_APPLICATION_CREDENTIALS_set": bool(creds),
        "credentials_file_exists": bool(creds_path and creds_path.is_file()),
        # Intentionally do not echo the path contents or full path in CI logs if unset
        "credentials_path_configured": bool(creds),
    }


def _try_import_firestore():
    try:
        from google.cloud import firestore  # type: ignore

        return firestore, None
    except ImportError as e:
        return None, str(e)


def dry_run() -> dict:
    env = _env_report()
    firestore, err = _try_import_firestore()
    mode = "disabled"
    if env["FIRESTORE_EMULATOR_HOST"] or (
        env["GOOGLE_APPLICATION_CREDENTIALS_set"] and env["credentials_file_exists"]
    ):
        mode = "firestore" if firestore else "stub"
    elif env["GOOGLE_APPLICATION_CREDENTIALS_set"] and not env["credentials_file_exists"]:
        mode = "stub_missing_file"
    report = {
        "ok": True,
        "dry_run": True,
        "mode_estimate": mode,
        "collections": {
            "weighing_sessions": COL_SESSIONS,
            "device_health": COL_HEALTH,
        },
        "env": env,
        "firestore_library": firestore is not None,
        "firestore_import_error": err,
        "message": (
            "Dry-run only. Pass --write to insert one test device_health doc "
            "when credentials/emulator + library are available."
        ),
    }
    return report


def write_test_doc() -> dict:
    base = dry_run()
    firestore, err = _try_import_firestore()
    if firestore is None:
        base["ok"] = False
        base["dry_run"] = False
        base["message"] = f"Cannot write: firestore library missing ({err}). pip install -e '.[firestore]' in api/"
        return base
    if not (
        base["env"]["FIRESTORE_EMULATOR_HOST"]
        or (base["env"]["GOOGLE_APPLICATION_CREDENTIALS_set"] and base["env"]["credentials_file_exists"])
    ):
        base["ok"] = False
        base["dry_run"] = False
        base["message"] = (
            "Cannot write: set GOOGLE_APPLICATION_CREDENTIALS to an existing SA JSON "
            "or FIRESTORE_EMULATOR_HOST. See docs/FIRESTORE_SOAK.md."
        )
        return base

    project = base["env"]["GOOGLE_CLOUD_PROJECT"]
    client = firestore.Client(project=project)
    doc_id = TEST_DEVICE
    payload = {
        "device_id": doc_id,
        "online": True,
        "pipeline_state": "soak_check",
        "source": "ops/scripts/firestore_soak_check.py",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "note": "temporary soak probe — safe to delete",
    }
    client.collection(COL_HEALTH).document(doc_id).set(payload, merge=True)
    base["ok"] = True
    base["dry_run"] = False
    base["wrote"] = {"collection": COL_HEALTH, "id": doc_id, "fields": sorted(payload.keys())}
    base["message"] = f"Wrote test doc {COL_HEALTH}/{doc_id} in project {project}"
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BoviScan Firestore soak check")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write one device_health test doc when credentials/emulator present",
    )
    args = parser.parse_args(argv)
    report = write_test_doc() if args.write else dry_run()
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
