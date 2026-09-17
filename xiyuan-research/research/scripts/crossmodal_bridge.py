#!/usr/bin/env python3
"""crossmodal_bridge — the theory↔code join for X-10 / DS-CM-001 (2026-09-17).

Consumes:
  * ``kronos_context_adapter.ContextBatch``-like object (asset_ids, cutoff_times,
    context matrix) — the low-frequency (LF) side, pre-generation context;
  * ``hf_data_pipeline`` v2 aligned output (kline + bounded-freshness HF features
    + ``event_time_max`` / ``feature_age_ms`` / ``hf_available``) — the
    high-frequency (HF) side;
  * ``make_future_labels`` outputs (contiguity-checked future windows).

Produces:
  1. ``PairKey`` contract — the STRUCTURE of the pair schema X-10 demands; the
     project group only has to fill VALUES (session windows, label horizon).
  2. ``temporal_audit`` — machine-checkable no-lookahead evidence (deep_C R8–R11,
     §3.a-6 assertions; C-X10-001 §7 item 2's "fourth test" that neither module
     can run alone).
  3. ``interface_bit_audit`` — per-bit evidence for DS-CM-001's P/A/H/B/S where
     the DATA layer can already answer; H (and final loss choice) is marked
     "needs deployment answer", never guessed.
  4. ``provisional_d_pair`` — a frozen-seed placeholder projection to materialise
     D_pair = ‖Ẑ_H − Z_L‖² for INTERFACE audit only. Explicitly NOT a design
     basis (deep_B C1 conditions; C-CM-001 §4.4 "squared distance is ablation
     only"). Computing it trains nothing and claims nothing predictive.

This module adds no learnable objective and no model. It emits evidence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
import pandas as pd

PROVISIONAL_NOTE = ("provisional: frozen random projection (seed fixed), "
                    "ablation-only interface audit, NOT a design basis "
                    "(deep_B C1; C-CM-001 §4.4)")


@dataclass(frozen=True)
class PairKey:
    """Canonical pairing unit: same asset, same prediction instant.

    Invariants are enforced in __post_init__; the VALUES (session calendar,
    horizon) are the project group's side of the X-10 contract.
    """
    asset_id: str
    cutoff_time: pd.Timestamp

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("asset_id must be non-empty")
        ts = pd.Timestamp(self.cutoff_time)
        if ts.tz is None:
            raise ValueError("cutoff_time must be tz-aware (UTC)")
        object.__setattr__(self, "cutoff_time", ts)


def _as_matrix(context) -> np.ndarray:
    arr = getattr(context, "context", context)
    try:
        arr = arr.detach().cpu().numpy()      # torch tensor without importing torch
    except AttributeError:
        pass
    return np.asarray(arr, dtype=np.float64)


def build_pair_table(context_batch, aligned: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Exact-equality join of LF contexts and aligned HF rows on PairKey.

    ``aligned`` must come from ``align_features_to_kline`` (v2) and carry
    ``asset_id, cutoff_time``; a context is valid only for its own cutoff —
    no as-of fallback, staleness on the LF side is a contract violation.
    Returns (pair_table, ctx_matrix aligned to its rows).
    """
    _ = PairKey  # contract symbol exported for downstream typing
    ctx = _as_matrix(context_batch)
    lf = pd.DataFrame({
        "asset_id": [str(a) for a in context_batch.asset_ids],
        "cutoff_time": pd.to_datetime(list(context_batch.cutoff_times), utc=True),
    })
    lf["ctx_row"] = range(len(lf))
    a = aligned.copy()
    a["cutoff_time"] = pd.to_datetime(a["cutoff_time"], utc=True)
    merged = lf.merge(a, on=["asset_id", "cutoff_time"], how="left", validate="one_to_one")
    if merged["ctx_row"].isna().any():
        raise ValueError("context rows without matching kline cutoff (pair contract violation)")
    hf_cols = [c for c in a.columns if c not in {"asset_id", "cutoff_time"}]
    merged["lf_available"] = True                      # adapter-validated windows
    merged["hf_available_pair"] = merged["hf_available"] if "hf_available" in merged else False
    merged["pair_complete"] = merged["lf_available"] & merged["hf_available_pair"].astype(bool)
    ordered = merged.sort_values(["asset_id", "cutoff_time"]).reset_index(drop=True)
    return ordered, ctx[ordered["ctx_row"].to_numpy()]


def temporal_audit(pair_table: pd.DataFrame, ctx_matrix: np.ndarray,
                   feature_window: str = "1min") -> dict:
    """No-lookahead + shape + determinism evidence (C-X10-001 §7 item 2)."""
    t = pair_table
    out: dict[str, object] = {}
    if "event_time_max" in t.columns:
        ok = t.loc[t["hf_available_pair"], :].copy()
        viol = int((pd.to_datetime(ok["event_time_max"], utc=True, errors="coerce").dropna()
                    > ok.loc[ok["event_time_max"].notna(), "cutoff_time"]).sum()) if len(ok) else 0
        out["T1_hf_event_le_cutoff_violations"] = viol
    else:
        out["T1_hf_event_le_cutoff_violations"] = "no event_time_max column (v2 pipeline required)"
    if "feature_age_ms" in t.columns:
        ages = pd.to_numeric(t["feature_age_ms"], errors="coerce")
        out["T2_feature_age_ms_max"] = float(np.nanmax(ages)) if np.isfinite(ages).any() else None
        out["T2_nonzero_lag_share"] = float((ages.fillna(0) > 0).mean())
    mono = t.groupby("asset_id")["cutoff_time"].apply(lambda s: s.is_monotonic_increasing and s.is_unique)
    out["T3_cutoff_strictly_monotonic_per_asset"] = bool(mono.all())
    if {"label_ok_contiguity"} & set(t.columns):
        out["T4_label_contiguity_share"] = float(t["label_ok_contiguity"].mean())
    out["T5_ctx_shape"] = list(ctx_matrix.shape)
    out["T6_ctx_finite"] = bool(np.isfinite(ctx_matrix).all())
    out["T7_pair_key_duplicates"] = int(t.duplicated(["asset_id", "cutoff_time"]).sum())
    return out


def interface_bit_audit(pair_table: pd.DataFrame, ctx_matrix: np.ndarray,
                        hf_cols: Sequence[str], train_cutoff: pd.Timestamp,
                        label_dims: dict[str, int]) -> dict:
    """DS-CM-001 five-bit EVIDENCE from the data layer (never the verdict).

    P/A/B/S get machine-checkable evidence + a provisional reading; H is always
    "needs deployment answer". A verdict becomes final only after the group
    fills DS-CM-001's five slots with these evidence strings.
    """
    t = pair_table
    ev: dict[str, dict] = {}
    complete = int(t["pair_complete"].sum())
    ev["P"] = {
        "evidence": f"paired at identical cutoff: {complete}/{len(t)} rows; "
                    "loss = pairwise squared distance at same prediction instant is constructible",
        "provisional": "1 (after A_r freeze, read as 11110 per deep_B §2-C1; S caveat below)",
        "blockers": "final loss form must be the project's; A_r preprocessing must be declared",
    }
    train_mask = t["cutoff_time"] <= pd.Timestamp(train_cutoff).tz_convert("UTC")
    rms_hf, rms_lf = {}, float(np.sqrt((ctx_matrix ** 2).mean()))
    for c in hf_cols:
        col = pd.to_numeric(t.loc[train_mask, c], errors="coerce") if c in t else pd.Series(dtype=float)
        mu, sd = col.mean(), col.std(ddof=0)
        rms_hf[c] = {"train_mean": None if pd.isna(mu) else float(mu),
                     "train_std": None if pd.isna(sd) or sd == 0 else float(sd)}
    anchored = all(v["train_std"] for v in rms_hf.values())
    ev["A"] = {
        "evidence": f"Z_H side: train-only standardization stats emitted (frozen anchor candidate); "
                    f"Z_L raw RMS={rms_lf:.4g} — LayerNorm/RMS logging must live in the training loop",
        "provisional": "0.5 (data side anchored; scale-escape check A→sA·A_r/s must run in training code)",
        "blockers": "training-side RMS log + freeze audit (deep_B C1 cond.1–3)",
    }
    lf_cov = float(t["lf_available"].mean())
    hf_cov = float(t["hf_available_pair"].astype(bool).mean())
    ev["B"] = {
        "evidence": f"data-layer availability: LF={lf_cov:.2f}, HF={hf_cov:.2f}, joint={complete/max(len(t),1):.2f}; "
                    "fallback rows (HF missing) kept as NA per v2 contract",
        "provisional": "0.5 (deployment-time availability needs replay logs; deep_C R10 source_delay)",
        "blockers": "deployment replay + source_delay measurement (deep_C §3.a-2)",
    }
    ev["S"] = {
        "evidence": f"label dims: {label_dims}",
        "provisional": 1 if set(label_dims.values()) == {1} else 0,
        "blockers": "if vector labels persist, route 11110/F-S per DS-CM-001 §1",
    }
    ev["H"] = {
        "evidence": "not auditable at data layer (needs deployed head vs Bayes-affine risk probe; deep_B C1 cond/H)",
        "provisional": "?",
        "blockers": "project/deployment answer",
    }
    if not anchored:
        ev["A"]["provisional"] = "0 (unanchored std available in train range)"
    return ev


def provisional_d_pair(ctx_matrix: np.ndarray, z_h_std: np.ndarray,
                       seed: int = 20260917) -> dict:
    """D_pair = mean‖proj(Z_H_std) − Z_L‖² with a frozen-seed projection.

    ``z_h_std`` must already be standardized with TRAIN-ONLY stats (run_bridge).
    Audit-only: trains nothing, claims nothing predictive (PROVISIONAL_NOTE).
    """
    n, d_hf = z_h_std.shape
    d_model = ctx_matrix.shape[1]
    stats = {"n_pairs": int(n), "d_model": int(d_model), "d_hf": int(d_hf),
             "seed": seed, "status": PROVISIONAL_NOTE}
    if n == 0:
        stats.update(d_pair_mean=None)
        return stats
    rng = np.random.default_rng(seed)
    proj = rng.normal(size=(d_hf, d_model)) / np.sqrt(d_hf)
    dh = z_h_std @ proj
    d = ((dh - ctx_matrix) ** 2).sum(axis=1)
    stats.update(d_pair_mean=float(d.mean()), d_pair_median=float(np.median(d)),
                 d_pair_min=float(d.min()), d_pair_max=float(d.max()))
    return stats


def run_bridge(context_batch, pair_table: pd.DataFrame, ctx_matrix: np.ndarray,
               hf_cols: Sequence[str], train_cutoff: pd.Timestamp,
               label_dims: dict[str, int], window: str = "1min",
               out_path: Optional[str] = None) -> dict:
    report = {
        "temporal_audit": temporal_audit(pair_table, ctx_matrix, window),
        "interface_bits": interface_bit_audit(pair_table, ctx_matrix, hf_cols,
                                              train_cutoff, label_dims),
    }
    t = pair_table
    complete = t["pair_complete"].to_numpy(dtype=bool)
    cols = [c for c in hf_cols if c in t.columns]
    if cols and complete.any():
        sub = t.loc[complete, ["cutoff_time", *cols]].reset_index(drop=True)
        Z = np.column_stack([pd.to_numeric(sub[c], errors="coerce").to_numpy(float) for c in cols])
        ok = np.isfinite(Z).all(axis=1) & np.isfinite(ctx_matrix[complete]).all(axis=1)
        if ok.any():
            in_train = sub["cutoff_time"] <= pd.Timestamp(train_cutoff).tz_convert("UTC")
            means, stds = [], []
            for j in range(len(cols)):
                col_tr = Z[in_train & ok][:, j]
                means.append(float(col_tr.mean()) if len(col_tr) else 0.0)
                sd = float(col_tr.std(ddof=0)) if len(col_tr) else 0.0
                stds.append(sd if sd > 0 else 1.0)
            Zs = (Z[ok] - np.array(means)) / np.array(stds)
            report["standardization"] = {"train_rows": int((in_train & ok).sum()),
                                         "columns": cols}
            report["provisional_d_pair"] = provisional_d_pair(
                ctx_matrix[complete][ok], Zs)
    if out_path:
        with open(out_path, "w") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    return report


def _smoke() -> None:
    """Deterministic self-test: contract, audits, bit evidence, provisional D."""
    class Ctx:
        pass

    rng = np.random.default_rng(7)
    n, d = 12, 512
    ts = pd.date_range("2026-01-05 09:31", periods=n, freq="1min", tz="UTC")
    assets = ["A", "B"] * (n // 2)
    ctx = Ctx(); ctx.context = rng.normal(size=(n, d)); ctx.asset_ids = tuple(assets)
    ctx.cutoff_times = tuple(ts)

    hf_feats = pd.DataFrame({"asset_id": assets, "cutoff_time": ts,
                             "event_ofi": np.arange(n, dtype=float),
                             "rv_sqrt": np.full(n, 0.001),
                             "event_time_max": ts})
    kl = pd.DataFrame({"asset_id": assets, "cutoff_time": ts,
                       "close": 100.0 + np.arange(n) * 0.01,
                       "target_log_return": 0.001, "target_rv": 1e-6,
                       "label_ok_contiguity": True,
                       "hf_available": True, "feature_age_ms": 0.0})
    table, ctxm = build_pair_table(ctx, kl.merge(hf_feats, on=["asset_id", "cutoff_time"]))
    assert len(table) == n and table["pair_complete"].all()
    ta = temporal_audit(table, ctxm)
    assert ta["T3_cutoff_strictly_monotonic_per_asset"] and ta["T7_pair_key_duplicates"] == 0
    assert ta["T1_hf_event_le_cutoff_violations"] == 0
    staler = hf_feats.copy(); staler["event_time_max"] = ts + pd.Timedelta("5min")
    t2, _ = build_pair_table(ctx, kl.merge(staler, on=["asset_id", "cutoff_time"]))
    assert temporal_audit(t2, ctxm)["T1_hf_event_le_cutoff_violations"] == n   # caught
    bits = interface_bit_audit(table, ctxm, ["event_ofi", "rv_sqrt"], ts[5],
                               {"target_log_return": 1, "target_rv": 1})
    assert set(bits) == {"P", "A", "B", "S", "H"} and bits["H"]["provisional"] == "?"
    assert bits["S"]["provisional"] == 1
    rep = run_bridge(ctx, table, ctxm, ["event_ofi", "rv_sqrt"], ts[5],
                     {"target_log_return": 1, "target_rv": 1})
    assert np.isfinite(rep["provisional_d_pair"]["d_pair_mean"])
    assert rep["provisional_d_pair"]["status"].startswith("provisional")
    # staleness bounded by align (v2) surfaces via pair_complete + age
    assert float(table["feature_age_ms"].max()) == 0.0
    print("pair rows:", len(table), "| ctx shape:", ctxm.shape)
    print("temporal:", {k: v for k, v in ta.items() if isinstance(v, (int, float, bool))})
    print("bits:", {k: v["provisional"] for k, v in bits.items()})
    print("d_pair provisional:", {k: round(v, 3) if isinstance(v, float) else v
                                  for k, v in rep["provisional_d_pair"].items() if k != "status"})
    print("CROSSMODAL_BRIDGE: PASS")


if __name__ == "__main__":
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--context-json")
    ap.add_argument("--aligned-parquet")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.smoke or not (args.context_json and args.aligned_parquet):
        _smoke()
        sys.exit(0)
    raise SystemExit("real-data mode requires a ContextBatch dump; use research/scripts/"
                     "kronos_context_adapter.py to produce contexts, then call run_bridge()")
