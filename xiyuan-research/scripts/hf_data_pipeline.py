#!/usr/bin/env python3
"""Leakage-safe high-frequency data preparation (v2, 2026-09-17).

Revision basis: deep_A_microstructure_code_audit.md (per-function deviations
R1–R8) + deep_C_finml_methodology.md (pipeline audit), both independently
converging; project re-verifications in crosswalk R-6.  Breaking changes vs
v1 are listed in claims/C-CODE-HF-001.md.

v2 contract summary
  * Right-closed / right-labelled windows (c-Δ, c]; a FULL bin grid is emitted
    so feature rows correspond one-to-one with bars; under-filled windows keep
    NaN features instead of disappearing or reporting fake zeros.
  * OFI window sums include every valid in-window event (CKS 2014 definition,
    arXiv:1011.6402 §2.1); only the global first snapshot and post-gap
    snapshots are excluded via ``ofi_valid`` (NaN, never 0).
  * ``mid_return`` is bar close-to-close (last mid of this window vs last mid
    of the previous window); RV is computed on a previous-tick sub-grid
    (default 5 s) with a minimum observation count — same boundary convention
    as OFI and mid_return.
  * Explicit vendor semantics are REQUIRED arguments: ``assume_tz``
    everywhere, ``timestamp_semantics`` for bars, ``side_semantics`` for
    trades (Binance's ``m`` flag means buyer-is-MAKER — a sign trap).
  * Alignment is bounded: per-asset merge, default staleness cap
    (2 × median feature spacing) and ``feature_age_ms`` output; no unlimited
    backward search.
  * Labels: RV convention sqrt(sum r²) over exactly (t, t+h] on the TIME grid;
    non-contiguous futures are NaN, not silent span stretching; h=1 is
    meaningful (=|r_{t+1}|) and never a fake zero.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal, Optional

import numpy as np
import pandas as pd


BOOK_LEVELS = 5
KLINE_COLUMNS = ["open", "high", "low", "close", "volume"]


def _book_columns(levels: int) -> list[str]:
    return [
        *(f"bid_price_{i}" for i in range(levels)),
        *(f"bid_volume_{i}" for i in range(levels)),
        *(f"ask_price_{i}" for i in range(levels)),
        *(f"ask_volume_{i}" for i in range(levels)),
    ]


@dataclass
class CleaningReport:
    input_rows: int
    output_rows: int
    dropped_duplicate_time: int = 0
    dropped_bad_timestamp: int = 0
    dropped_nonfinite: int = 0
    dropped_bad_price: int = 0
    dropped_bad_volume: int = 0
    dropped_locked: int = 0
    dropped_crossed: int = 0
    gap_flags: int = 0
    zero_volume_trades: int = 0
    id_duplicates: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_times(values: Iterable, assume_tz: str, *, allow_invalid: bool = False) -> pd.DatetimeIndex:
    """Parse timestamps to UTC-aware values; naive input REQUIRES assume_tz."""
    if not assume_tz:
        raise ValueError("assume_tz is required for naive timestamps (never guessed)")
    parsed = pd.to_datetime(values, errors="coerce")
    idx = pd.DatetimeIndex(parsed)
    if idx.isna().any() and not allow_invalid:
        raise ValueError("timestamp contains unparseable values")
    if idx.tz is None:
        idx = idx.tz_localize(assume_tz, ambiguous="NaT", nonexistent="NaT")
    return idx.tz_convert("UTC")


def _require_columns(df: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _full_bin_index(t0: pd.Timestamp, t1: pd.Timestamp, window: str) -> pd.DatetimeIndex:
    """Right-labelled bin edges covering [t0, t1]; bin (e-Δ, e] holds its events."""
    first_end = t0.ceil(window)   # an event exactly ON the boundary belongs to the bin ending there
    last_end = t1.ceil(window)
    return pd.date_range(first_end, last_end, freq=window, tz=str(t0.tz))


def clean_orderbook(
    orderbook: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    assume_tz: str,
    levels: int = BOOK_LEVELS,
    max_gap: Optional[str] = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean top-of-book snapshots; no filling, no silent destruction.

    Per-row depth is TRUNCATED at the first padded/invalid level (0-filled
    empty levels are vendor convention, not dirty data); only violations
    INSIDE the populated depth (negative price, disorder, crossed book) drop
    a row.  Locked books (bid==ask) are counted separately and dropped.
    ``max_gap`` flags the first snapshot after a quiet interval so OFI does
    not treat a data hole as one event.
    """
    required = _book_columns(levels)
    _require_columns(orderbook, [timestamp_col, *required], "orderbook")
    raw = orderbook.copy()
    report = CleaningReport(input_rows=len(raw), output_rows=0)
    raw["event_time"] = _utc_times(raw[timestamp_col], assume_tz, allow_invalid=True)
    report.dropped_bad_timestamp = int(raw["event_time"].isna().sum())
    raw = raw.dropna(subset=["event_time"])

    values = raw[required].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(values.to_numpy()).all(axis=1)
    report.dropped_nonfinite = int((~finite).sum())
    raw = raw.loc[finite].copy()
    values = values.loc[finite]

    bid_p = values[[f"bid_price_{i}" for i in range(levels)]].to_numpy()
    ask_p = values[[f"ask_price_{i}" for i in range(levels)]].to_numpy()
    bid_v = values[[f"bid_volume_{i}" for i in range(levels)]].to_numpy()
    ask_v = values[[f"ask_volume_{i}" for i in range(levels)]].to_numpy()

    def truncate_depth(prices: np.ndarray) -> np.ndarray:
        """Boolean mask of populated levels: leading prefix with price > 0."""
        ok = (prices > 0).astype(np.int64)
        return np.cumprod(ok, axis=1).astype(bool)

    bp_keep = truncate_depth(bid_p)
    ap_keep = truncate_depth(ask_p)

    def depth_violations(prices: np.ndarray, vols: np.ndarray, side: str) -> np.ndarray:
        keep = np.cumprod((prices > 0).astype(int), axis=1).astype(bool)
        n = keep.sum(axis=1)
        bad = np.zeros(prices.shape[0], dtype=bool)
        for i in range(prices.shape[0]):
            k = int(n[i])
            if k == 0:
                bad[i] = True
                continue
            p = prices[i, :k]
            v = vols[i, :k]
            if (v < 0).any():
                bad[i] = True
            if k > 1:
                mono = (p[:-1] >= p[1:]).all() if side == "bid" else (p[:-1] <= p[1:]).all()
                if not mono:
                    bad[i] = True
        return bad

    bad_bid = depth_violations(bid_p, bid_v, "bid")
    bad_ask = depth_violations(ask_p, ask_v, "ask")
    bad_price = bad_bid | bad_ask
    report.dropped_bad_price = int(bad_price.sum())
    report.dropped_bad_volume = 0  # negative volumes inside populated depth are counted under bad_price

    crossed = np.where(bp_keep.any(axis=1) & ap_keep.any(axis=1),
                       (bid_p[:, 0] >= ask_p[:, 0]), np.zeros(len(raw), dtype=bool))
    locked = np.where(bp_keep.any(axis=1) & ap_keep.any(axis=1),
                      bid_p[:, 0] == ask_p[:, 0], np.zeros(len(raw), dtype=bool))
    report.dropped_locked = int((locked & ~bad_price).sum())
    report.dropped_crossed = int((crossed & ~bad_price & ~locked).sum())
    keep = ~bad_price & ~crossed

    raw = raw.loc[keep].copy()
    vals = values.loc[keep]
    # normalize: padded levels beyond truncated depth become NaN (missing), not fake 0-price
    bp_k, ap_k = bp_keep[keep], ap_keep[keep]
    for i in range(levels):
        raw[f"bid_price_{i}"] = np.where(bp_k[:, i], vals[f"bid_price_{i}"].to_numpy(), np.nan)
        raw[f"bid_volume_{i}"] = np.where(bp_k[:, i], vals[f"bid_volume_{i}"].to_numpy(), np.nan)
        raw[f"ask_price_{i}"] = np.where(ap_k[:, i], vals[f"ask_price_{i}"].to_numpy(), np.nan)
        raw[f"ask_volume_{i}"] = np.where(ap_k[:, i], vals[f"ask_volume_{i}"].to_numpy(), np.nan)
    raw["levels"] = bp_k.sum(axis=1)

    raw = raw.sort_values("event_time", kind="stable")
    before = len(raw)
    raw = raw.drop_duplicates(subset=["event_time"], keep="last")   # vendor order preserved by stable sort
    report.dropped_duplicate_time = before - len(raw)
    raw = raw.reset_index(drop=True)

    if max_gap is not None:
        diffs = raw["event_time"].diff()
        raw["gap_flag"] = (diffs > pd.Timedelta(max_gap)).fillna(False).to_numpy()
        report.gap_flags = int(raw["gap_flag"].sum())
    else:
        raw["gap_flag"] = False
    raw["timestamp"] = raw.pop("event_time")
    report.output_rows = len(raw)
    return raw, report


def add_event_ofi(book: pd.DataFrame) -> pd.DataFrame:
    """Top-of-book event OFI per CKS 2014 (arXiv:1011.6402 §2.1), e_n formula.

    e_n = 1[b_n>=b_{n-1}]q_b,n - 1[b_n<=b_{n-1}]q_b,n-1
          -1[a_n<=a_{n-1}]q_a,n + 1[a_n>=a_{n-1}]q_a,n-1

    ASSUMPTION (inherited from the snapshot input): between two snapshots many
    order events may cancel each other; |e_n| underestimates gross flow.  A
    snapshot following a data gap or the global first snapshot gets
    ``event_ofi = NaN`` and ``ofi_valid = False`` — "unmeasurable" is never
    written as "zero impact".
    """
    _require_columns(book, _book_columns(BOOK_LEVELS), "book")
    out = book.copy().sort_values("timestamp", kind="stable").reset_index(drop=True)
    bp = out["bid_price_0"].to_numpy(float)
    bq = out["bid_volume_0"].to_numpy(float)
    ap = out["ask_price_0"].to_numpy(float)
    aq = out["ask_volume_0"].to_numpy(float)
    prev_bp, prev_bq = np.roll(bp, 1), np.roll(bq, 1)
    prev_ap, prev_aq = np.roll(ap, 1), np.roll(aq, 1)
    prev_bp[0] = bp[0]; prev_bq[0] = bq[0]
    prev_ap[0] = ap[0]; prev_aq[0] = aq[0]
    ofi = (
        (bp >= prev_bp) * bq - (bp <= prev_bp) * prev_bq
        - (ap <= prev_ap) * aq + (ap >= prev_ap) * prev_aq
    )
    valid = np.arange(len(out)) > 0
    if "gap_flag" in out.columns:
        valid &= ~out["gap_flag"].to_numpy(dtype=bool)
    ofi = np.where(valid, ofi, np.nan)
    out["event_ofi"] = ofi
    out["ofi_valid"] = valid
    return out


def clean_trades(
    trades: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    price_col: str = "price",
    volume_col: str = "volume",
    side_col: Optional[str],
    side_semantics: Literal["aggressor", "maker", "absent"],
    assume_tz: str,
    id_col: Optional[str] = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean trades; canonical output column ``aggressor_side`` ∈ {buy, sell}.

    ``side_semantics`` is REQUIRED (never guessed): "aggressor" means the raw
    side names the taker; "maker" means it names the resting side (Binance
    aggTrade ``m``=buyer-is-market-maker is this case) and is FLIPPED here.
    "absent" (or side_col=None) yields no signed columns at all.  Duplicate
    timestamps are kept (they are distinct events); ``id_col`` dedups repeated
    exports.
    """
    _require_columns(trades, [timestamp_col, price_col, volume_col], "trades")
    if side_semantics not in {"aggressor", "maker", "absent"}:
        raise ValueError("side_semantics must be 'aggressor', 'maker' or 'absent'")
    raw = trades.copy()
    report = CleaningReport(input_rows=len(raw), output_rows=0)
    raw["event_time"] = _utc_times(raw[timestamp_col], assume_tz, allow_invalid=True)
    report.dropped_bad_timestamp = int(raw["event_time"].isna().sum())
    raw = raw.dropna(subset=["event_time"]).copy()
    numeric = raw[[price_col, volume_col]].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy()).all(axis=1)
    report.dropped_nonfinite = int((~finite).sum())
    raw = raw.loc[finite].copy()
    numeric = numeric.loc[finite]
    good_price = numeric[price_col].to_numpy() > 0
    report.dropped_bad_price = int((~good_price).sum())
    good_volume = numeric[volume_col].to_numpy() >= 0
    report.dropped_bad_volume = int((~good_volume).sum())
    report.zero_volume_trades = int((numeric[volume_col].to_numpy() == 0).sum())
    keep = good_price & good_volume
    raw = raw.loc[keep].copy()
    raw[price_col] = numeric.loc[keep, price_col].to_numpy()
    raw[volume_col] = numeric.loc[keep, volume_col].to_numpy()
    if id_col is not None and id_col in raw.columns:
        before = len(raw)
        raw = raw.drop_duplicates(subset=[id_col], keep="first")
        report.id_duplicates = before - len(raw)
    if side_semantics != "absent" and side_col is not None and side_col in raw.columns:
        side = raw[side_col].astype(str).str.lower().str.strip()
        side = side.where(side.isin({"buy", "sell", "b", "s"})).replace({"b": "buy", "s": "sell"})
        if side_semantics == "maker":
            side = side.map({"buy": "sell", "sell": "buy"})
        raw["aggressor_side"] = side
    raw["timestamp"] = raw.pop("event_time")
    raw = raw.sort_values("timestamp", kind="stable").reset_index(drop=True)
    report.output_rows = len(raw)
    return raw, report


def aggregate_trades(
    trades: pd.DataFrame,
    window: str = "1min",
    *,
    price_col: str = "price",
    volume_col: str = "volume",
    min_trades: int = 1,
) -> pd.DataFrame:
    """Right-labelled full-grid trade windows; imbalance uses CLASSIFIED volume."""
    _require_columns(trades, ["timestamp", price_col, volume_col], "trades")
    work = trades.copy().set_index("timestamp").sort_index()
    work["notional"] = work[price_col] * work[volume_col]
    if "aggressor_side" in work.columns:
        sgn = np.where(work["aggressor_side"].eq("buy"), 1.0,
                       np.where(work["aggressor_side"].eq("sell"), -1.0, np.nan))
        work["signed_volume"] = sgn * work[volume_col]
        work["classified_volume"] = np.where(np.isfinite(sgn), work[volume_col], 0.0)
    rows = []
    for cutoff in _full_bin_index(work.index.min(), work.index.max(), window):
        group = work.loc[(work.index > cutoff - pd.Timedelta(window)) & (work.index <= cutoff)]
        row = {"cutoff_time": cutoff, "trade_count": len(group),
               "event_time_max": group.index.max() if len(group) else pd.NaT}
        if len(group) < min_trades:
            row.update({c: np.nan for c in ["volume_sum", "notional_sum", "vwap",
                                            "price_first", "price_last"]})
            if "signed_volume" in work.columns:
                row.update({"signed_volume": np.nan, "signed_volume_imbalance": np.nan,
                            "classified_volume_share": np.nan})
            rows.append(row)
            continue
        vol = group[volume_col].sum()
        row.update({
            "volume_sum": vol,
            "notional_sum": group["notional"].sum(),
            "vwap": group["notional"].sum() / vol if vol > 0 else np.nan,
            "price_first": group[price_col].iloc[0],
            "price_last": group[price_col].iloc[-1],
        })
        if "signed_volume" in group:
            signed = group["signed_volume"].sum(min_count=1)
            classified = group["classified_volume"].sum()
            row["signed_volume"] = signed
            row["signed_volume_imbalance"] = (signed / classified) if classified > 0 and signed == signed else np.nan
            row["classified_volume_share"] = classified / vol if vol > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("cutoff_time").reset_index(drop=True) if rows else pd.DataFrame(columns=["cutoff_time"])


def aggregate_orderbook(
    book: pd.DataFrame,
    window: str = "1min",
    *,
    min_snapshots: int = 4,
    rv_grid: Optional[str] = "5s",
    min_rv_points: int = 4,
) -> pd.DataFrame:
    """Full-grid order-book features with ONE boundary convention everywhere.

    v2 semantics (deep_A R3 fixes):
      * every bin between first and last event appears; under-filled bins have
        NaN features (never fabricated zeros);
      * ``event_ofi`` sums ALL valid in-window e_n (CKS definition);
      * ``mid_return`` = ln(this window's last mid / previous window's last
        mid) — bar close-to-close, chained across windows;
      * ``rv``/``rv_sqrt`` from previous-tick mid sampled on a fixed sub-grid
        (rv_grid; None = per-snapshot pairs, non-standard);
      * book_slope renamed: v1's formula carries only PRICE distance between
        level 0 and level 4 in spread units (no depth information) — it is
        named ``book_span_spreads_mean`` accordingly, not ``book_slope``.
    """
    _require_columns(book, ["timestamp", *_book_columns(BOOK_LEVELS)], "book")
    work = add_event_ofi(book)
    work = work.set_index("timestamp").sort_index()
    best_bid = work["bid_price_0"]
    best_ask = work["ask_price_0"]
    mid = (best_bid + best_ask) / 2.0
    work = work.assign(
        mid_price=mid,
        spread_bps=(best_ask - best_bid) / mid.replace(0, np.nan) * 1e4,
        depth_imbalance=(
            (work[[f"bid_volume_{i}" for i in range(BOOK_LEVELS)]].sum(axis=1)
             - work[[f"ask_volume_{i}" for i in range(BOOK_LEVELS)]].sum(axis=1))
            / (work[[f"bid_volume_{i}" for i in range(BOOK_LEVELS)]].sum(axis=1)
               + work[[f"ask_volume_{i}" for i in range(BOOK_LEVELS)]].sum(axis=1)).replace(0, np.nan)
        ),
        book_span_spreads=(
            ((work["bid_price_0"] - work["bid_price_4"]) + (work["ask_price_4"] - work["ask_price_0"]))
            / 2.0 / (best_ask - best_bid).replace(0, np.nan)
        ),
    )
    ts = work.index.tz_convert("UTC").values.astype("datetime64[ns]").astype("int64")  # ns epoch
    mid_v = work["mid_price"].to_numpy(float)
    bins = _full_bin_index(work.index.min(), work.index.max(), window)
    step = pd.Timedelta(window)
    step_ns = step.value
    prev_last_mid = np.nan
    rows = []
    for cutoff in bins:
        right = int(np.searchsorted(ts, cutoff.value, side="right"))
        left = int(np.searchsorted(ts, cutoff.value - step_ns, side="right"))
        g = work.iloc[left:right]
        row = {"cutoff_time": cutoff, "snapshot_count": len(g),
               "event_time_max": g.index.max() if len(g) else pd.NaT}
        features = ["event_ofi", "event_ofi_abs", "spread_bps_mean", "spread_bps_std",
                    "mid_price_last", "mid_return", "rv", "rv_sqrt", "depth_imbalance_mean",
                    "book_span_spreads_mean", "ofi_contributing"]
        if len(g) < min_snapshots:
            row.update({c: np.nan for c in features})
            row["snapshot_count"] = len(g)
            prev_last_mid = g["mid_price"].iloc[-1] if len(g) else prev_last_mid
            rows.append(row)
            continue
        valid_ofi = g.loc[g["ofi_valid"], "event_ofi"]
        row["event_ofi"] = float(valid_ofi.sum()) if len(valid_ofi) else np.nan
        row["event_ofi_abs"] = float(valid_ofi.abs().sum()) if len(valid_ofi) else np.nan
        row["ofi_contributing"] = int(len(valid_ofi))
        row["spread_bps_mean"] = g["spread_bps"].mean()
        row["spread_bps_std"] = g["spread_bps"].std(ddof=1) if len(g) > 1 else np.nan
        last_mid = float(g["mid_price"].iloc[-1])
        row["mid_price_last"] = last_mid
        row["mid_return"] = np.log(last_mid / prev_last_mid) if prev_last_mid == prev_last_mid and prev_last_mid > 0 and last_mid > 0 else np.nan
        prev_last_mid = last_mid
        row["depth_imbalance_mean"] = g["depth_imbalance"].mean()
        row["book_span_spreads_mean"] = g["book_span_spreads"].mean()
        if rv_grid is not None:
            grid = pd.date_range(cutoff - step + pd.Timedelta(rv_grid), cutoff, freq=rv_grid).tz_convert("UTC")
            grid_ns = grid.values.astype("datetime64[ns]").astype("int64")
            idx = np.searchsorted(ts, grid_ns, side="right") - 1
            samples = np.array([mid_v[i] if i >= 0 else np.nan for i in idx], dtype=float)
            ok = np.isfinite(samples)
            r = np.diff(samples[ok])
            rv = float(np.square(r).sum()) if ok.sum() >= min_rv_points else np.nan
        else:
            r = g["mid_price"].to_numpy(float)
            rr = np.diff(r)
            rv = float(np.square(rr).sum()) if len(rr) >= min_rv_points else np.nan
        row["rv"] = rv
        row["rv_sqrt"] = np.sqrt(rv) if rv == rv else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("cutoff_time").reset_index(drop=True) if rows else pd.DataFrame(columns=["cutoff_time"])


def normalise_kline(
    kline: pd.DataFrame,
    *,
    timestamp_col: str = "timestamp",
    assume_tz: str,
    timestamp_semantics: Literal["bar_start", "bar_end"],
    bar_frequency: str = "1min",
    asset_id: Optional[str] = None,
    asset_col: Optional[str] = None,
) -> pd.DataFrame:
    """Standardise an exported K-line table.  tz AND bar semantics are REQUIRED
    declarations (Tushare stk_mins is bar_end / Asia/Shanghai naive; Binance
    kline open_time is bar_start / UTC — the caller states which)."""
    if timestamp_semantics not in {"bar_start", "bar_end"}:
        raise ValueError("timestamp_semantics must be 'bar_start' or 'bar_end'")
    required = [timestamp_col, *KLINE_COLUMNS]
    if asset_col is not None:
        required.append(asset_col)
    _require_columns(kline, required, "kline")
    out = kline.copy()
    out["bar_time"] = _utc_times(out[timestamp_col], assume_tz, allow_invalid=True)
    nat_drop = int(out["bar_time"].isna().sum())
    out = out.dropna(subset=["bar_time"])
    numeric = out[KLINE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    out[KLINE_COLUMNS] = numeric
    good = np.isfinite(numeric.to_numpy()).all(axis=1)
    good &= (numeric[["open", "high", "low", "close"]] > 0).all(axis=1).to_numpy()
    good &= (numeric["volume"] >= 0).to_numpy()
    good &= (numeric["high"] >= numeric[["open", "close"]].max(axis=1)).to_numpy()
    good &= (numeric["low"] <= numeric[["open", "close"]].min(axis=1)).to_numpy()
    out = out.loc[good].sort_values("bar_time", kind="stable").drop_duplicates("bar_time", keep="last")
    if timestamp_semantics == "bar_start":
        out["cutoff_time"] = out["bar_time"] + pd.Timedelta(bar_frequency)
    else:
        out["cutoff_time"] = out["bar_time"]
    if asset_id is not None:
        out["asset_id"] = asset_id
    elif asset_col is not None:
        out["asset_id"] = out[asset_col].astype(str)
    elif "asset_id" not in out.columns:
        out["asset_id"] = "asset"
    out = out.reset_index(drop=True)
    step = pd.Timedelta(bar_frequency)
    expected = int((out["cutoff_time"].max() - out["cutoff_time"].min()) / step) + 1 if len(out) else 0
    out.attrs["expected_bars"] = expected
    out.attrs["actual_bars"] = len(out)
    out.attrs["missing_bars"] = expected - len(out)
    out.attrs["dropped_nat"] = nat_drop
    return out


def align_features_to_kline(
    kline: pd.DataFrame,
    features: pd.DataFrame,
    *,
    max_staleness: Optional[str] = None,
) -> pd.DataFrame:
    """Per-asset past-only alignment with a BOUNDED staleness cap.

    merge_asof requires the on-key globally sorted (multi-asset panel fix);
    default cap = 2 × median feature spacing; ``feature_age_ms`` is always
    emitted and ``hf_available`` = within cap AND ≥1 non-NaN feature.
    """
    _require_columns(kline, ["asset_id", "cutoff_time"], "kline")
    _require_columns(features, ["cutoff_time"], "features")
    if len(kline) == 0:
        raise ValueError("kline is empty")
    if len(features) == 0:
        raise ValueError("features are empty")
    left = kline.sort_values("cutoff_time", kind="stable").copy()
    right = features.copy()
    if "asset_id" not in right.columns:
        if left["asset_id"].nunique() > 1:
            raise ValueError("multi-asset kline requires features with an asset_id column")
        right["asset_id"] = left["asset_id"].iloc[0]
    right = right.sort_values("cutoff_time", kind="stable")
    right = right.drop_duplicates(["asset_id", "cutoff_time"], keep="last")
    right["feature_cutoff"] = right["cutoff_time"]
    if max_staleness is None:
        spacings = right.groupby("asset_id", sort=False)["cutoff_time"].apply(
            lambda s: s.sort_values().diff().median())
        med = pd.to_timedelta(pd.Series(spacings).dropna().median())
        tol = pd.Timedelta(2 * med) if med == med and med > pd.Timedelta(0) else None
    else:
        tol = pd.Timedelta(max_staleness)
    if tol is None:
        raise ValueError("cannot infer feature spacing for staleness cap; pass max_staleness explicitly")
    out = pd.merge_asof(left, right, on="cutoff_time", by="asset_id",
                        direction="backward", tolerance=tol, suffixes=("", "_hf"))
    out["feature_age_ms"] = (out["cutoff_time"] - out["feature_cutoff"]).dt.total_seconds() * 1000.0
    hf_cols = [c for c in right.columns if c not in {"asset_id", "cutoff_time", "feature_cutoff"}]
    present = out[hf_cols].notna().sum(axis=1) if hf_cols else pd.Series(0, index=out.index)
    out["n_features_present"] = present
    out["n_features_total"] = len(hf_cols)
    out["hf_available"] = (present > 0) & out["feature_age_ms"].notna()
    return out.sort_values(["asset_id", "cutoff_time"]).reset_index(drop=True)


def make_future_labels(kline: pd.DataFrame, *, horizon: int) -> pd.DataFrame:
    """Time-grid-checked forward labels: log return + RV (sqrt of sum r²).

    The future window is (cutoff, cutoff + h·Δ] where Δ = median cutoff
    spacing PER ASSET; a row whose h-th future bar is not exactly h·Δ ahead
    (missing bars inside the label window) gets NaN labels instead of a
    silently stretched horizon.  h=1 label = |r_{t+1}| (never a fake 0).
    """
    if horizon < 1:
        raise ValueError("horizon must be positive")
    _require_columns(kline, ["asset_id", "cutoff_time", "close"], "kline")
    out = kline.sort_values(["asset_id", "cutoff_time"]).copy()
    out["target_log_return"] = np.nan
    out["target_rv"] = np.nan
    out["target_rv_sqrt"] = np.nan
    out["label_ok_contiguity"] = False
    for _, idx in out.groupby("asset_id", sort=False).groups.items():
        idx = np.sort(np.asarray(idx))
        ts = pd.DatetimeIndex(out["cutoff_time"].iloc[idx].to_numpy()).tz_convert("UTC").values.astype("datetime64[ns]").astype("int64")
        close = out["close"].iloc[idx].to_numpy(float)
        step = int(np.median(np.diff(ts))) if len(ts) > 1 else 60_000_000_000
        n = len(ts)
        span_ok = np.zeros(n, dtype=bool)
        contig = np.zeros(n, dtype=bool)
        fut_ret = np.full(n, np.nan)
        fut_rv = np.full(n, np.nan)
        for i in range(n):
            target = ts[i] + step * horizon
            j = int(np.searchsorted(ts, target))
            if j < n and ts[j] == target and close[i] > 0 and close[j] > 0:
                span_ok[i] = True
                contig[i] = (j - i == horizon)   # no bars missing/extra inside (t, t+h]
                fut_ret[i] = np.log(close[j] / close[i])
                seg = close[i:j + 1]
                r = np.diff(np.log(seg))
                r = r[np.isfinite(r)]
                if len(r) == horizon:
                    fut_rv[i] = float(np.square(r).sum())
        out.loc[idx, "target_log_return"] = fut_ret
        out.loc[idx, "target_rv"] = fut_rv
        out.loc[idx, "target_rv_sqrt"] = np.sqrt(fut_rv)
        out.loc[idx, "label_ok_contiguity"] = contig
    return out


def run_sample(orderbook_path: str, output_path: Optional[str] = None) -> pd.DataFrame:
    book = pd.read_parquet(orderbook_path)
    clean, report = clean_orderbook(book, assume_tz="UTC")   # Binance exports are UTC
    features = aggregate_orderbook(clean, window="1min", min_snapshots=4)
    print("cleaning_report", report.to_dict())
    print("feature_rows", len(features))
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        features.to_parquet(output_path, index=False)
    return features


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--orderbook", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    run_sample(args.orderbook, args.output)
