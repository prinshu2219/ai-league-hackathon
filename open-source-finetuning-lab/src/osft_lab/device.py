"""Device selection helpers for interview-visible PyTorch behavior."""

from typing import Any, Dict, Optional


def _load_torch(torch_module: Optional[Any] = None) -> Any:
    if torch_module is not None:
        return torch_module
    import torch

    return torch


def _mps_available(torch_module: Any) -> bool:
    backends = getattr(torch_module, "backends", None)
    mps = getattr(backends, "mps", None)
    if mps is None:
        return False
    is_available = getattr(mps, "is_available", None)
    return bool(is_available and is_available())


def select_best_device(torch_module: Optional[Any] = None) -> str:
    """Return cuda, mps, or cpu based on the available runtime."""
    torch_module = _load_torch(torch_module)

    if torch_module.cuda.is_available():
        return "cuda"
    if _mps_available(torch_module):
        return "mps"
    return "cpu"


def torch_device(torch_module: Optional[Any] = None):
    """Return a real torch.device for scripts that need model placement."""
    torch_module = _load_torch(torch_module)
    return torch_module.device(select_best_device(torch_module=torch_module))


def describe_device(torch_module: Optional[Any] = None) -> Dict[str, Any]:
    """Return details that can be shown in logs or the Streamlit demo."""
    torch_module = _load_torch(torch_module)
    cuda_available = bool(torch_module.cuda.is_available())
    mps_available = _mps_available(torch_module)
    selected = select_best_device(torch_module=torch_module)
    cuda_name = None

    if cuda_available:
        try:
            cuda_name = torch_module.cuda.get_device_name(0)
        except Exception:
            cuda_name = "CUDA device"

    return {
        "selected_device": selected,
        "cuda_available": cuda_available,
        "mps_available": mps_available,
        "cuda_name": cuda_name,
    }
