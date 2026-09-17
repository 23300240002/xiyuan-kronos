"""Extract a deployment-time context vector from the real KronosLocal model.

The adapter intentionally stops before fusion or alignment.  It makes the
low-frequency object in X-10 explicit and carries the cutoff metadata needed
to pair it with a high-frequency representation later.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import torch


KDATA = ("open", "high", "low", "close", "volume", "amount")
MAX_CONTEXT_FALLBACK = 512
# KronosLocal lives OUTSIDE this repo (a sibling checkout).  Point KRONOS_DIR
# at it; there is intentionally no machine-specific default (portability +
# privacy: no absolute home paths are shipped).
_root_env = os.environ.get("KRONOS_DIR")
if not _root_env:
    raise RuntimeError("set KRONOS_DIR to the local KronosLocal checkout root "
                       "(the directory containing deps/Kronos and kronos_small/weights)")
ROOT = Path(_root_env)
REPO = ROOT / "deps" / "Kronos"
TOKENIZER_DIR = ROOT / "deps" / "tokenizer_base"
MODEL_DIR = ROOT / "kronos_small" / "weights"


def _model_max_context(model) -> int:
    v = getattr(model, "max_context", None) or \
        getattr(getattr(model, "config", None), "max_context", None)
    return int(v) if v else MAX_CONTEXT_FALLBACK


@dataclass(frozen=True)
class ContextBatch:
    """A context tensor plus the keys needed for later cross-modal pairing."""

    context: torch.Tensor       # [B, d_model], last observed token
    asset_ids: tuple[str, ...]
    cutoff_times: tuple[pd.Timestamp, ...]
    means: np.ndarray            # [B, 6], fitted on each observed window
    stds: np.ndarray             # [B, 6], fitted on each observed window
    model_name: str
    d_model: int


def _stamp_frame(timestamps: Iterable[pd.Timestamp]) -> np.ndarray:
    ts = pd.DatetimeIndex(pd.to_datetime(list(timestamps)))
    return np.column_stack([
        ts.minute.to_numpy(),
        ts.hour.to_numpy(),
        ts.weekday.to_numpy(),
        ts.day.to_numpy(),
        ts.month.to_numpy(),
    ]).astype(np.float32)


def _validate_frame(frame: pd.DataFrame, timestamps: Iterable[pd.Timestamp], asset_id: str,
                    cutoff_time: pd.Timestamp) -> tuple[np.ndarray, pd.DatetimeIndex]:
    if not asset_id:
        raise ValueError("asset_id must be non-empty")
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    missing = [c for c in KDATA if c not in frame.columns]
    if missing:
        raise ValueError(f"missing OHLCVA columns: {missing}")
    ts = pd.DatetimeIndex(pd.to_datetime(list(timestamps)))
    if len(ts) != len(frame) or len(ts) == 0:
        raise ValueError("timestamps and frame must have the same non-zero length")
    if not ts.is_monotonic_increasing or ts.has_duplicates:
        raise ValueError("timestamps must be strictly increasing")
    cutoff = pd.Timestamp(cutoff_time)
    if ts[-1] != cutoff:
        raise ValueError(f"last observed timestamp {ts[-1]} != cutoff_time {cutoff}")
    values = frame.loc[:, KDATA].to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("OHLCVA contains NaN or infinite values")
    return values, ts


def extract_context(model, tokenizer, frames: list[pd.DataFrame], timestamps: list[Iterable[pd.Timestamp]],
                    asset_ids: Iterable[str], cutoff_times: Iterable[pd.Timestamp],
                    clip: float = 5.0) -> ContextBatch:
    """Extract one last-token context per window without using future values.

    ``frames[i]`` must end exactly at ``cutoff_times[i]``.  Normalization is
    fitted independently on that observed window, matching KronosPredictor's
    existing zero-shot convention.  The function never calls autoregressive
    generation and never reads a label or future timestamp.  Windows longer
    than the model's ``max_context`` (512 for Kronos-small) are truncated to
    their last ``max_context`` bars WITH a warning: deeper windows would feed
    a sequence length the AR inference never uses (out-of-distribution, deep_D
    §5 D1); truncation must be declared in pre-registration (C-X10-001 §7).
    """
    asset_ids = tuple(str(x) for x in asset_ids)
    cutoff_times = tuple(pd.Timestamp(x) for x in cutoff_times)
    timestamps = list(timestamps)
    if not (len(frames) == len(timestamps) == len(asset_ids) == len(cutoff_times)):
        raise ValueError("frames, timestamps, asset_ids and cutoff_times must have equal lengths")
    if not frames:
        raise ValueError("at least one window is required")

    normalized, stamps, means, stds = [], [], [], []
    for frame, ts_values, aid, cutoff in zip(frames, timestamps, asset_ids, cutoff_times):
        values, ts = _validate_frame(frame, ts_values, aid, cutoff)
        mean = values.mean(axis=0)
        std = values.std(axis=0)
        norm = np.clip((values - mean) / (std + 1e-5), -clip, clip)
        normalized.append(norm)
        stamps.append(_stamp_frame(ts))
        means.append(mean)
        stds.append(std)

    lengths = {x.shape[0] for x in normalized}
    if len(lengths) != 1:
        raise ValueError(f"batched windows must have equal lengths, got {sorted(lengths)}")
    max_ctx = _model_max_context(model)
    if normalized[0].shape[0] > max_ctx:
        import warnings
        warnings.warn(f"window length {normalized[0].shape[0]} > max_context {max_ctx}: "
                      f"context computed on the last {max_ctx} bars only; declare this "
                      "truncation in pre-registration (C-X10-001 §7)", stacklevel=2)
        normalized = [a[-max_ctx:] for a in normalized]
        stamps = [s[-max_ctx:] for s in stamps]

    device = next(model.parameters()).device
    x = torch.from_numpy(np.stack(normalized).astype(np.float32)).to(device)
    stamp = torch.from_numpy(np.stack(stamps).astype(np.float32)).to(device)
    with torch.no_grad():
        s1_ids, s2_ids = tokenizer.encode(x, half=True)
        _, context = model.decode_s1(s1_ids, s2_ids, stamp=stamp)
    context_last = context[:, -1, :].detach().cpu()
    return ContextBatch(
        context=context_last,
        asset_ids=asset_ids,
        cutoff_times=cutoff_times,
        means=np.stack(means),
        stds=np.stack(stds),
        model_name="kronos-small",
        d_model=int(context_last.shape[-1]),
    )


def load_local_small(device: str = "cpu"):
    """Load the checked-in local tokenizer and Kronos-small weights."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    sys.path.insert(0, str(REPO))
    from model import Kronos, KronosTokenizer  # noqa: WPS433

    tokenizer = KronosTokenizer.from_pretrained(str(TOKENIZER_DIR)).to(device).eval()
    model = Kronos.from_pretrained(str(MODEL_DIR)).to(device).eval()
    return model, tokenizer


def _smoke() -> None:
    torch.manual_seed(0)
    model, tokenizer = load_local_small("cpu")
    ts = pd.date_range("2026-01-01 09:30", periods=8, freq="min")
    frame = pd.DataFrame(np.arange(8 * 6).reshape(8, 6) / 10.0, columns=KDATA)
    out = extract_context(model, tokenizer, [frame], [ts], ["demo"], [ts[-1]])
    assert out.context.shape == (1, model.d_model)
    assert out.asset_ids == ("demo",)
    assert out.cutoff_times == (ts[-1],)
    assert np.isfinite(out.context.numpy()).all()
    print(f"context_last: {tuple(out.context.shape)}")
    print(f"pair_key: {(out.asset_ids[0], out.cutoff_times[0].isoformat())}")
    print(f"normalization: means={out.means.shape}, stds={out.stds.shape}")
    print("KRONOS_CONTEXT_ADAPTER_SMOKE: PASS")


if __name__ == "__main__":
    _smoke()

