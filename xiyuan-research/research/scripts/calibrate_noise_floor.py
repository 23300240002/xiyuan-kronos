#!/usr/bin/env python3
"""Noise-floor calibration (sigma2_per_min, 2*omega2) via the RV signature plot.

Method (project 推论 1.1, classical in the literature; citation wording
pending the literature audit tracked in claims/C-X03-001.md):

Under A1 (log-price random walk, per-minute variance sigma2_min) and A2
(iid observation noise of variance omega2 on each bar close), the variance
of a return aggregated over Delta minutes is

    Var(r_Delta) = sigma2_min * Delta + 2 * omega2,

so realized variance over a fixed T-minute span satisfies

    RV(Delta) = sigma2_min * T + 2 * omega2 * (T / Delta).

RV(Delta) is therefore linear in T/Delta with slope 2*omega2 and intercept
sigma2_min * T.  Two or more sampling frequencies pin down both parameters
without any model of the signal beyond A1/A2.

Caveats (printed with every run):
  - Bar CLOSES are used, not trades: the estimated omega is the EFFECTIVE
    close-price noise (last-trade + bounce), not a pure bid-ask bounce.
  - sigma is assumed constant within the sample; intraday clustering biases
    both parameters.  A half-span stability check reports the drift.
  - A2 (iid noise) is exactly what the signature plot is designed to
    circumvent; residual 1-min return AR(1) is reported as a diagnostic.
  - Ordinary least squares is used (no weights); WLS is the documented
    refinement for multi-day samples.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

DEFAULT_DELTAS = (1, 2, 5, 10, 15, 30, 60, 120)
MIN_BLOCKS = 10


def load_closes(path: str, ts_col: str = "timestamp", close_col: str = "close") -> pd.Series:
    df = pd.read_parquet(path)
    ts = pd.DatetimeIndex(pd.to_datetime(df[ts_col]))
    close = pd.to_numeric(df[close_col], errors="coerce")
    s = pd.Series(close.to_numpy(), index=ts, name="close").dropna()
    if s.index.has_duplicates:
        raise ValueError("duplicate timestamps in kline; dedupe before calibrating")
    return s.sort_index()


def rv_rows(r: np.ndarray, deltas: list[int], min_blocks: int) -> list[tuple[int, int, float, bool]]:
    """Non-overlapping block RV at each aggregation frequency.

    Returns (delta_min, n_blocks, RV, included) rows.
    """
    n1 = len(r)
    rows = []
    for d in deltas:
        nb = n1 // d
        if nb < min_blocks:
            rows.append((d, nb, float("nan"), False))
            continue
        blocks = r[: nb * d].reshape(-1, d).sum(axis=1)
        rows.append((d, nb, float(np.sum(blocks ** 2)), True))
    return rows


def fit(rows: list[tuple[int, int, float, bool]], span_min: int) -> dict | None:
    """WLS of RV on T/Delta (weights = n_blocks, since Var(RV) ~ 1/n_blocks).

    slope = 2*omega2, intercept = sigma2_min*T.
    """
    inc = [row for row in rows if row[3]]
    if len(inc) < 3:
        return None
    x = np.array([span_min / row[0] for row in inc], dtype=float)
    y = np.array([row[2] for row in inc], dtype=float)
    w = np.array([row[1] for row in inc], dtype=float)
    slope, intercept = np.polyfit(x, y, 1, w=w)
    slope_u, intercept_u = np.polyfit(x, y, 1)
    yhat_u = slope_u * x + intercept_u
    ss_tot_u = float(np.sum((y - y.mean()) ** 2))
    r2_u = 1.0 - float(np.sum((y - yhat_u) ** 2)) / ss_tot_u if ss_tot_u > 0 else float("nan")
    yhat = slope * x + intercept
    ss_res = float(np.sum(w * (y - yhat) ** 2))
    ybar = float(np.sum(w * y) / np.sum(w))
    ss_tot = float(np.sum(w * (y - ybar) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "n_freqs": len(inc),
        "slope_2omega2": float(slope),
        "intercept": float(intercept),
        "r2": r2,
        "omega2": max(float(slope), 0.0) / 2.0,
        "sigma2_per_min": max(float(intercept), 0.0) / span_min,
        "slope_2omega2_unweighted": float(slope_u),
        "intercept_unweighted": float(intercept_u),
        "r2_unweighted": r2_u,
        "omega2_unweighted": max(float(slope_u), 0.0) / 2.0,
        "sigma2_per_min_unweighted": max(float(intercept_u), 0.0) / span_min,
    }


def ar1(r: np.ndarray) -> float:
    if len(r) < 3:
        return float("nan")
    return float(np.corrcoef(r[:-1], r[1:])[0, 1])


def rho_table(sigma2_min: float, omega2: float) -> list[dict]:
    out = []
    for name, delta_min in (("1min", 1.0), ("5min", 5.0), ("10s", 1.0 / 6.0)):
        sig = sigma2_min * delta_min
        den = sig + 2.0 * omega2
        out.append({"horizon": name, "delta_min": delta_min,
                    "rho": sig / den if den > 0 else float("nan")})
    return out


def calibrate(path: str, deltas: tuple[int, ...] = DEFAULT_DELTAS,
              min_blocks: int = MIN_BLOCKS) -> dict:
    closes = load_closes(path)
    r = np.log(closes.to_numpy()[1:] / closes.to_numpy()[:-1])
    span_min = len(r)
    if span_min < 3 * min_blocks:
        raise ValueError(f"sample too short: {span_min} one-min returns")

    full = fit(rv_rows(r, list(deltas), min_blocks), span_min)
    if full is None:
        raise ValueError("fewer than 3 usable frequencies after min_blocks filter")
    half = span_min // 2
    h1 = fit(rv_rows(r[:half], list(deltas), min_blocks // 2), half)
    h2 = fit(rv_rows(r[half:], list(deltas), min_blocks // 2), span_min - half)

    omega = np.sqrt(full["omega2"])
    sigma_min = np.sqrt(full["sigma2_per_min"])
    return {
        "path": path,
        "span": f"{closes.index[0]} .. {closes.index[-1]} ({span_min} one-min returns)",
        "rows": rv_rows(r, list(deltas), min_blocks),
        "full": full,
        "half1": h1,
        "half2": h2,
        "omega": float(omega),
        "sigma_per_min": float(sigma_min),
        "sigma_per_24h": float(sigma_min * np.sqrt(1440.0)),
        "ar1_1min": ar1(r),
        "rho": rho_table(full["sigma2_per_min"], full["omega2"]),
    }


def report(res: dict) -> bool:
    full, h1, h2 = res["full"], res["half1"], res["half2"]
    print(f"# 噪声地板标定（RV 签名图法）— {res['path']}")
    print(f"span: {res['span']}")
    print()
    print("| Δ(min) | n_blocks | RV(Δ) | 入拟合 |")
    print("|---:|---:|---:|:--:|")
    for d, nb, rv, inc in res["rows"]:
        rvs = f"{rv:.4e}" if np.isfinite(rv) else "—"
        print(f"| {d} | {nb} | {rvs} | {'✓' if inc else ''} |")
    print()
    print(f"WLS(weights=n_blocks): RV(Δ) = {full['intercept']:.4e} + {full['slope_2omega2']:.4e}·(T/Δ),  R² = {full['r2']:.3f}")
    print(f"  ω² = {full['omega2']:.4e},  σ²/min = {full['sigma2_per_min']:.4e}")
    print(f"OLS(未加权对照):         RV(Δ) = {full['intercept_unweighted']:.4e} + {full['slope_2omega2_unweighted']:.4e}·(T/Δ),  R² = {full['r2_unweighted']:.3f}")
    print(f"  ω² = {full['omega2_unweighted']:.4e},  σ²/min = {full['sigma2_per_min_unweighted']:.4e}")
    print(f"omega = {res['omega']:.4e} (WLS, 绝对价格尺度);  sigma/24h = {res['sigma_per_24h']:.3e} (WLS)")
    print(f"1min 收益 AR(1) 诊断 = {res['ar1_1min']:+.4f}")
    if h1 and h2:
        drift = abs(h1["omega2"] - h2["omega2"]) / max(h1["omega2"], h2["omega2"], 1e-300)
        print(f"半段稳定性: ω²(h1) = {h1['omega2']:.4e}, ω²(h2) = {h2['omega2']:.4e} (相对漂移 {drift:.0%})")
    print()
    print("ρ(Δ) = σ²Δ/(σ²Δ + 2ω²)  [WLS 口径]:")
    for row in res["rho"]:
        print(f"  {row['horizon']:>5} (Δ = {row['delta_min']:.2f} min): ρ = {row['rho']:.4f}")
    rho_u = rho_table(full["sigma2_per_min_unweighted"], full["omega2_unweighted"])
    print("  [OLS 口径]: " + ", ".join(f"{r['horizon']} ρ = {r['rho']:.4f}" for r in rho_u))
    print()
    print("注意事项：K线收盘价的*有效*观测噪声（含最后一笔成交价噪声，非纯 bid-ask bounce）；")
    print("单一样本日内 σ 非平稳、A2(iid 噪声)为方法前提；主估计为 WLS，未加权口径一并输出构成区间。")
    ok = full["slope_2omega2"] > 0 and full["intercept"] > 0
    warn = not ok or (np.isfinite(full["r2"]) and full["r2"] < 0.5)
    print(f"\nNOISE_FLOOR_CALIBRATION: {'PASS' if ok else 'FAIL'}" + (" (WARN: R² 偏低)" if ok and np.isfinite(full["r2"]) and full["r2"] < 0.5 else ""))
    return not warn


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kline", help="1-min kline parquet with timestamp/close columns")
    ap.add_argument("--deltas", default=",".join(map(str, DEFAULT_DELTAS)))
    ap.add_argument("--min-blocks", type=int, default=MIN_BLOCKS)
    args = ap.parse_args()
    deltas = tuple(int(x) for x in args.deltas.split(","))
    try:
        res = calibrate(args.kline, deltas, args.min_blocks)
    except (ValueError, KeyError) as exc:
        print(f"NOISE_FLOOR_CALIBRATION: ERROR ({exc})")
        return 1
    ok = report(res)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
