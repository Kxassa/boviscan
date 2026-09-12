"""Backward-compatible import path; implementation lives in hailo.py. """

from .hailo import HailoBackend, HailoRuntimeConfig, POSTPROCESS_HOOKS, probe_hailo_sdk

__all__ = [
    "HailoBackend",
    "HailoRuntimeConfig",
    "POSTPROCESS_HOOKS",
    "probe_hailo_sdk",
]
