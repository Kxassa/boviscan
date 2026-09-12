"""Hailo backend: graceful fallback without SDK / HEF (CI-safe)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from livestock_weight_device.config import InferenceConfig, load_config
from livestock_weight_device.inference.factory import create_inference_backend
from livestock_weight_device.inference.hailo import (
    HailoBackend,
    POSTPROCESS_HOOKS,
    probe_hailo_sdk,
)
from livestock_weight_device.inference.base import Detection


def test_probe_sdk_without_hailo():
    info = probe_hailo_sdk()
    assert "sdk_importable" in info
    # On CI / laptop we expect no Hailo SDK
    if not info["sdk_importable"]:
        assert info.get("error")


def test_hailo_fallback_missing_hef():
    backend = HailoBackend(hef_path="/tmp/does-not-exist-boviscan.hef", fallback_to_cpu=True)
    backend.load()
    assert backend.hailo_ready is False
    assert backend.fallback_active is True
    assert any("not found" in e.lower() or "HEF" in e for e in backend.load_errors)
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[80:160, 100:220] = 200
    # cpu_mock needs a prior frame for motion; still must not raise
    dets = backend.predict(frame)
    assert isinstance(dets, list)
    st = backend.status()
    assert st["fallback_active"] is True
    assert st["hailo_ready"] is False
    backend.close()


def test_hailo_fallback_missing_path_entirely():
    backend = HailoBackend(fallback_to_cpu=True)
    backend.load()
    assert backend.fallback_active is True
    assert any("not configured" in e.lower() for e in backend.load_errors)


def test_hailo_no_fallback_raises():
    backend = HailoBackend(hef_path=None, fallback_to_cpu=False)
    with pytest.raises(RuntimeError, match="HEF path not configured"):
        backend.load()


def test_factory_selects_hailo_and_falls_back():
    cfg = InferenceConfig(
        backend="hailo",
        hef_path="/nonexistent/model.hef",
        batch=1,
        input_width=320,
        input_height=320,
        postprocess="yolo_nms",
        fallback_to_cpu=True,
    )
    backend = create_inference_backend(cfg)
    assert isinstance(backend, HailoBackend)
    backend.load()
    assert backend.fallback_active is True
    assert backend.cfg.postprocess == "yolo_nms"
    frame = np.zeros((240, 320, 3), dtype=np.uint8) + 40
    assert isinstance(backend.predict(frame), list)
    backend.close()


def test_yaml_hailo_config_roundtrip(tmp_path):
    yml = tmp_path / "device.yaml"
    yml.write_text(
        yaml.dump(
            {
                "inference": {
                    "backend": "hailo",
                    "hef_path": "/opt/livestock-weight/models/detect.hef",
                    "batch": 2,
                    "input_size": [640, 640, 3],
                    "postprocess_hooks": ["yolo_nms"],
                    "fallback_to_cpu": True,
                    "confidence_threshold": 0.35,
                }
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(yml)
    assert cfg.inference.backend == "hailo"
    assert cfg.inference.hef_path.endswith("detect.hef")
    assert cfg.inference.batch == 2
    assert cfg.inference.input_width == 640
    assert cfg.inference.input_height == 640
    assert cfg.inference.input_channels == 3
    assert cfg.inference.postprocess == "yolo_nms"
    assert cfg.inference.confidence_threshold == 0.35


def test_yolo_nms_hook_decodes_boxes():
    hook = POSTPROCESS_HOOKS["yolo_nms"]
    raw = np.array(
        [
            [0.1, 0.1, 0.5, 0.5, 0.9, 0],
            [0.2, 0.2, 0.3, 0.3, 0.1, 0],  # below thr
        ],
        dtype=np.float32,
    )
    dets = hook(
        raw,
        {
            "confidence_threshold": 0.4,
            "labels": ["livestock"],
            "input_width": 100,
            "input_height": 100,
        },
    )
    assert len(dets) == 1
    assert isinstance(dets[0], Detection)
    assert dets[0].confidence == pytest.approx(0.9)
    assert dets[0].x2 == pytest.approx(50.0)


def test_hef_present_but_no_sdk(tmp_path):
    """HEF file exists but SDK missing → clear error + cpu fallback."""
    hef = tmp_path / "fake.hef"
    hef.write_bytes(b"not-a-real-hef")
    backend = HailoBackend(hef_path=str(hef), fallback_to_cpu=True)
    backend.load()
    assert backend.hailo_ready is False
    assert backend.fallback_active is True
    assert any("SDK" in e or "import" in e.lower() for e in backend.load_errors)
