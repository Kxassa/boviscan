from livestock_weight_device.calibration.geometry import default_calibration
from livestock_weight_device.camera.mock import MockCamera
from livestock_weight_device.inference.mock import MockBackend, CPUMockBackend
from livestock_weight_device.pipeline.runner import Pipeline


def test_mock_pipeline_emits_event():
    cam = MockCamera(width=640, height=480)
    backend = MockBackend()
    cal = default_calibration(height_m=3.0, width=640, height=480)
    pipe = Pipeline(cam, backend, cal, device_id="test-device", species="cattle")
    events = pipe.run(steps=10)
    assert len(events) >= 1
    assert events[0].estimated_weight_kg is not None
    assert events[0].proxy_metrics["area_m2"] > 0


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
