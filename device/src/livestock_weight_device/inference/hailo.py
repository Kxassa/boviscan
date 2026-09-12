"""Hailo-8 production inference backend.

Loads an HEF from config and runs inference via HailoRT / hailo_platform when
the SDK and model file are present. Without SDK or HEF, falls back cleanly to
CPUMockBackend with structured status/errors (no fabricated detections from
Hailo). Proprietary SDK binaries are never committed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .base import Detection, InferenceBackend
from .mock import CPUMockBackend

logger = logging.getLogger(__name__)

# Optional postprocess hooks keyed by config name (extend as models land).
PostprocessFn = Callable[[Any, dict[str, Any]], list[Detection]]


@dataclass
class HailoRuntimeConfig:
    """Runtime knobs for the Hailo backend (from YAML / InferenceConfig)."""

    hef_path: str | None = None
    model_path: str | None = None  # legacy alias for hef_path
    batch: int = 1
    input_width: int = 640
    input_height: int = 640
    input_channels: int = 3
    confidence_threshold: float = 0.4
    postprocess: str = "passthrough"  # passthrough | yolo_nms | none
    fallback_to_cpu: bool = True
    labels: list[str] = field(default_factory=lambda: ["livestock"])

    @property
    def resolved_hef(self) -> str | None:
        return self.hef_path or self.model_path or os.environ.get("LW_HEF_PATH")


def _postprocess_passthrough(raw: Any, ctx: dict[str, Any]) -> list[Detection]:
    """Accept list[Detection] or empty; no invented boxes."""
    if raw is None:
        return []
    if isinstance(raw, list) and (not raw or isinstance(raw[0], Detection)):
        return list(raw)
    return []


def _postprocess_yolo_nms(raw: Any, ctx: dict[str, Any]) -> list[Detection]:
    """
    Decode a flat Nx6 (or Nx85-style) numpy array into boxes when present.

    Expected layout when array is provided by SDK decode helpers:
      [x1, y1, x2, y2, score, class_id] per row, normalized or pixel coords.
    Without a real tensor layout from HEF metadata this returns [].
    """
    thr = float(ctx.get("confidence_threshold", 0.4))
    labels: list[str] = ctx.get("labels") or ["livestock"]
    iw = int(ctx.get("input_width", 640))
    ih = int(ctx.get("input_height", 640))
    if not isinstance(raw, np.ndarray) or raw.size == 0:
        return []
    arr = np.asarray(raw)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2 or arr.shape[1] < 6:
        return []
    out: list[Detection] = []
    for row in arr:
        score = float(row[4])
        if score < thr:
            continue
        cls_i = int(row[5]) if len(row) > 5 else 0
        label = labels[cls_i] if 0 <= cls_i < len(labels) else labels[0]
        x1, y1, x2, y2 = map(float, row[:4])
        # If normalized [0,1], scale to configured input size (caller may remap)
        if max(abs(x1), abs(y1), abs(x2), abs(y2)) <= 1.5:
            x1, x2 = x1 * iw, x2 * iw
            y1, y2 = y1 * ih, y2 * ih
        out.append(Detection(label=label, confidence=score, x1=x1, y1=y1, x2=x2, y2=y2))
    return out


def _postprocess_none(_raw: Any, _ctx: dict[str, Any]) -> list[Detection]:
    return []


POSTPROCESS_HOOKS: dict[str, PostprocessFn] = {
    "passthrough": _postprocess_passthrough,
    "yolo_nms": _postprocess_yolo_nms,
    "none": _postprocess_none,
}


def probe_hailo_sdk() -> dict[str, Any]:
    """Report whether Hailo Python bindings / device node appear available."""
    info: dict[str, Any] = {
        "sdk_importable": False,
        "sdk_module": None,
        "device_node": None,
        "error": None,
    }
    for mod_name in ("hailo_platform", "hailort"):
        try:
            __import__(mod_name)
            info["sdk_importable"] = True
            info["sdk_module"] = mod_name
            break
        except ImportError as e:
            info["error"] = f"import {mod_name}: {e}"
    for node in ("/dev/hailo0", "/dev/hailo"):
        if Path(node).exists():
            info["device_node"] = node
            break
    return info


class HailoBackend(InferenceBackend):
    """
    Production Hailo-8 path with explicit fallback.

    Status fields (readable after load):
      hailo_ready, fallback_active, load_errors, sdk_info
    """

    name = "hailo"

    def __init__(
        self,
        model_path: str | None = None,
        *,
        hef_path: str | None = None,
        batch: int = 1,
        input_width: int = 640,
        input_height: int = 640,
        input_channels: int = 3,
        confidence_threshold: float = 0.4,
        postprocess: str = "passthrough",
        fallback_to_cpu: bool = True,
        labels: list[str] | None = None,
        runtime: HailoRuntimeConfig | None = None,
    ) -> None:
        if runtime is not None:
            self.cfg = runtime
        else:
            self.cfg = HailoRuntimeConfig(
                hef_path=hef_path,
                model_path=model_path,
                batch=max(1, int(batch)),
                input_width=int(input_width),
                input_height=int(input_height),
                input_channels=int(input_channels),
                confidence_threshold=float(confidence_threshold),
                postprocess=postprocess or "passthrough",
                fallback_to_cpu=fallback_to_cpu,
                labels=list(labels) if labels else ["livestock"],
            )
        self._fallback = CPUMockBackend()
        self.hailo_ready = False
        self.fallback_active = False
        self.load_errors: list[str] = []
        self.sdk_info: dict[str, Any] = {}
        self._hef = None
        self._network_group = None
        self._vdevice = None
        self._infer_model = None
        self._hook = POSTPROCESS_HOOKS.get(self.cfg.postprocess, _postprocess_passthrough)

    def load(self) -> None:
        self.load_errors.clear()
        self.hailo_ready = False
        self.fallback_active = False
        self.sdk_info = probe_hailo_sdk()

        hef = self.cfg.resolved_hef
        if not hef:
            self._fail(
                "Hailo HEF path not configured (set inference.hef_path / model_path or LW_HEF_PATH)"
            )
            return
        hef_path = Path(hef)
        if not hef_path.is_file():
            self._fail(f"Hailo HEF not found at {hef_path}")
            return
        if not self.sdk_info.get("sdk_importable"):
            self._fail(
                "Hailo SDK not importable "
                f"(tried hailo_platform/hailort): {self.sdk_info.get('error')}"
            )
            return

        try:
            self._init_hailort(hef_path)
            self.hailo_ready = True
            logger.info("HailoBackend ready: hef=%s batch=%s", hef_path, self.cfg.batch)
        except Exception as exc:  # noqa: BLE001 — surface any SDK/runtime failure
            self._fail(f"Hailo Runtime init failed: {exc}")

    def _fail(self, message: str) -> None:
        self.load_errors.append(message)
        logger.warning("HailoBackend: %s", message)
        if self.cfg.fallback_to_cpu:
            self._fallback.load()
            self.fallback_active = True
            logger.warning("HailoBackend: falling back to cpu_mock (%s)", message)
        else:
            raise RuntimeError(message)

    def _init_hailort(self, hef_path: Path) -> None:
        """
        Bind HEF via hailo_platform when available.

        Hailo API surfaces evolve; this uses the common HEF + VDevice configure
        pattern and keeps a narrow surface so CI stays SDK-free.
        """
        try:
            from hailo_platform import (  # type: ignore
                HEF,
                ConfigureParams,
                FormatType,
                HailoStreamInterface,
                InferVStreams,
                InputVStreamParams,
                OutputVStreamParams,
                VDevice,
            )
        except ImportError:
            # Older / alternate package name
            from hailort import HEF, VDevice  # type: ignore

            self._hef = HEF(str(hef_path))
            self._vdevice = VDevice()
            self._infer_model = True
            return

        self._vdevice = VDevice()
        self._hef = HEF(str(hef_path))
        configure_params = ConfigureParams.create_from_hef(
            self._hef, interface=HailoStreamInterface.PCIe
        )
        network_groups = self._vdevice.configure(self._hef, configure_params)
        self._network_group = network_groups[0]
        self._network_group_name = self._network_group.name
        self._input_vstream_params = InputVStreamParams.make(
            self._network_group, format_type=FormatType.UINT8
        )
        self._output_vstream_params = OutputVStreamParams.make(
            self._network_group, format_type=FormatType.FLOAT32
        )
        self._InferVStreams = InferVStreams
        self._infer_model = True

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Resize / pad to configured input tensor shape (NHWC uint8)."""
        h, w = self.cfg.input_height, self.cfg.input_width
        img = image
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        if img.shape[2] > self.cfg.input_channels:
            img = img[:, :, : self.cfg.input_channels]
        # Lightweight resize without requiring OpenCV / PIL
        if img.shape[0] != h or img.shape[1] != w:
            ys = (np.linspace(0, img.shape[0] - 1, h)).astype(np.int32)
            xs = (np.linspace(0, img.shape[1] - 1, w)).astype(np.int32)
            img = img[ys][:, xs]
        if img.dtype != np.uint8:
            img = np.clip(img, 0, 255).astype(np.uint8)
        batch = np.expand_dims(img, axis=0)
        if self.cfg.batch > 1:
            batch = np.repeat(batch, self.cfg.batch, axis=0)
        return batch

    def _infer_sdk(self, batch: np.ndarray) -> Any:
        if getattr(self, "_InferVStreams", None) is not None and self._network_group is not None:
            with self._network_group.activate():
                with self._InferVStreams(
                    self._network_group,
                    self._input_vstream_params,
                    self._output_vstream_params,
                ) as infer_pipeline:
                    input_dict = {}
                    for name in infer_pipeline.get_input_vstream_infos():
                        # name may be VStreamInfo; prefer .name
                        key = getattr(name, "name", name)
                        input_dict[key] = batch
                    # Prefer first input only when mapping fails
                    if not input_dict:
                        infos = list(infer_pipeline.get_input_vstream_infos())
                        if infos:
                            key = getattr(infos[0], "name", str(infos[0]))
                            input_dict = {key: batch}
                    results = infer_pipeline.infer(input_dict)
                    # Return first output tensor
                    if isinstance(results, dict) and results:
                        return next(iter(results.values()))
                    return results
        raise RuntimeError("Hailo infer path not fully configured on this SDK build")

    def predict(self, image: np.ndarray) -> list[Detection]:
        if self.hailo_ready:
            try:
                batch = self._preprocess(image)
                raw = self._infer_sdk(batch)
                ctx = {
                    "confidence_threshold": self.cfg.confidence_threshold,
                    "labels": self.cfg.labels,
                    "input_width": self.cfg.input_width,
                    "input_height": self.cfg.input_height,
                    "image_shape": image.shape,
                }
                return self._hook(raw, ctx)
            except Exception as exc:  # noqa: BLE001
                msg = f"Hailo infer failed: {exc}"
                self.load_errors.append(msg)
                logger.error(msg)
                if self.cfg.fallback_to_cpu:
                    if not self.fallback_active:
                        self._fallback.load()
                        self.fallback_active = True
                    return self._fallback.predict(image)
                raise
        if self.fallback_active:
            return self._fallback.predict(image)
        raise RuntimeError(
            "HailoBackend not ready and fallback disabled: "
            + ("; ".join(self.load_errors) or "not loaded")
        )

    def status(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "hailo_ready": self.hailo_ready,
            "fallback_active": self.fallback_active,
            "hef_path": self.cfg.resolved_hef,
            "batch": self.cfg.batch,
            "input_size": [self.cfg.input_width, self.cfg.input_height, self.cfg.input_channels],
            "postprocess": self.cfg.postprocess,
            "load_errors": list(self.load_errors),
            "sdk": self.sdk_info,
        }

    def close(self) -> None:
        self._infer_model = None
        self._network_group = None
        self._hef = None
        if self._vdevice is not None:
            try:
                closer = getattr(self._vdevice, "release", None) or getattr(self._vdevice, "close", None)
                if callable(closer):
                    closer()
            except Exception:  # noqa: BLE001
                pass
            self._vdevice = None
        self._fallback.close()
        self.hailo_ready = False
