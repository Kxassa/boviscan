from livestock_weight_device.discovery.udp_beacon import BeaconPayload, start_udp_beacon, stop_udp_beacon
from livestock_weight_device.ota.client import OtaClient, apply_update, check_for_update


def test_beacon_payload_json():
    p = BeaconPayload(device_id="device-local-01", health={"camera_ok": True})
    raw = p.to_json()
    assert b"device-local-01" in raw
    assert b"camera_ok" in raw


def test_beacon_start_stop():
    start_udp_beacon("device-test-beacon", interval_s=60.0, api_base=None)
    stop_udp_beacon()


def test_ota_noop_without_manifest():
    st = check_for_update()
    assert st.update_available is False
    assert st.reason == "no_manifest_url"
    applied = apply_update()
    assert applied.applied is False


def test_ota_stub_with_url_env(monkeypatch):
    monkeypatch.setenv("LW_OTA_MANIFEST_URL", "https://example.invalid/manifest.json")
    client = OtaClient(current_version="0.1.0")
    st = client.check_for_update()
    assert st.update_available is False
    assert st.reason == "stub_no_fetch"
    assert st.verified is False
    ap = client.apply_update(force=True)
    assert ap.applied is False
    assert ap.reason == "refused_unsigned_or_stub"
