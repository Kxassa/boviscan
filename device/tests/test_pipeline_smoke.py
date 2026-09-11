from unittest.mock import MagicMock, patch

from livestock_weight_device.calibration.cattle_proxy import (
    PROXY_METHOD,
    estimate_cattle_weight_kg,
)
from livestock_weight_device.calibration.geometry import default_calibration
from livestock_weight_device.camera.mock import MockCamera
from livestock_weight_device.inference.mock import CPUMockBackend, MockBackend
from livestock_weight_device.pipeline.runner import Pipeline
from livestock_weight_device.pipeline.tracker import SimpleTracker
from livestock_weight_device.inference.base import Detection


def test_mock_pipeline_emits_event():
    cam = MockCamera(width=640, height=480)
    backend = MockBackend()
    cal = default_calibration(height_m=3.0, width=640, height=480, species="cattle")
    pipe = Pipeline(cam, backend, cal, device_id="test-device", species="cattle")
    events = pipe.run(steps=10)
    assert len(events) >= 1
    assert events[0].estimated_weight_kg is not None
    assert events[0].proxy_metrics["area_m2"] > 0
    assert events[0].proxy_metrics.get("research_proxy") is True
    assert events[0].proxy_metrics["weight_proxy"]["method"] == PROXY_METHOD


def test_cpu_mock_on_blob():
    cam = MockCamera(width=640, height=480, seed=1)
    backend = CPUMockBackend(threshold=100, min_area=1000)
    cal = default_calibration(height_m=3.0, width=640, height=480)
    pipe = Pipeline(cam, backend, cal, device_id="test-device")
    events = pipe.run(steps=20)
    assert isinstance(events, list)


def test_calibration_default_height():
    cal = default_calibration()
    assert cal.camera_height_m == 3.0
    mpp = cal.meters_per_pixel_at_ground()
    assert mpp > 0


def test_cattle_proxy_table_interpolation():
    r = estimate_cattle_weight_kg(1.0)
    assert r["research_proxy"] is True
    assert r["weight_kg"] == 420.0
    mid = estimate_cattle_weight_kg(1.1)
    assert mid["weight_kg"] is not None
    assert 420.0 < mid["weight_kg"] < 500.0


def test_tracker_stable_id_across_frames():
    tracker = SimpleTracker(iou_threshold=0.3)
    d1 = Detection(label="livestock", confidence=0.9, x1=100, y1=100, x2=200, y2=200)
    t1 = tracker.update([d1])
    assert len(t1) == 1
    tid = t1[0].track_id
    d2 = Detection(label="livestock", confidence=0.9, x1=105, y1=102, x2=205, y2=202)
    t2 = tracker.update([d2])
    assert len(t2) == 1
    assert t2[0].track_id == tid
    assert t2[0].hits == 2


def test_pipeline_posts_to_api():
    cam = MockCamera(width=640, height=480)
    backend = MockBackend()
    cal = default_calibration(height_m=3.0, width=640, height=480)
    pipe = Pipeline(
        cam,
        backend,
        cal,
        device_id="test-device",
        species="cattle",
        api_base_url="http://127.0.0.1:9",  # nothing listening
        session_id="sess-test",
    )
    # Should not raise even when API is down (offline-first)
    events = pipe.run(steps=10)
    assert len(events) >= 1
    assert events[0].session_id == "sess-test"


def test_pipeline_posts_success_mocked():
    cam = MockCamera(width=640, height=480)
    backend = MockBackend()
    cal = default_calibration(height_m=3.0, width=640, height=480)
    pipe = Pipeline(
        cam,
        backend,
        cal,
        device_id="test-device",
        api_base_url="http://example.test",
        session_id="sess-ok",
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch("livestock_weight_device.pipeline.runner.httpx.post", return_value=mock_resp) as post:
        events = pipe.run(steps=10)
        assert len(events) >= 1
        assert post.called
        args, kwargs = post.call_args
        assert args[0].endswith("/events")
        body = kwargs["json"]
        assert body["session_id"] == "sess-ok"
        assert body["estimated_weight_kg"] is not None
        assert "proxy_metrics" in body
