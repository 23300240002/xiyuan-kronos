"""pooled IC / RankIC 与零分布门槛。

口径（对齐论文 Appendix.tex:315）：
    IC = corr(pred, ret)，在 (freq, split) 内把所有 (date, code) 样本摊平后计算。
    —— 不是「按日截面 IC 再平均」。

重叠样本警告：H 步收益在相邻样本间重叠，IC 的朴素 t = IC·sqrt(N-2) 会严重高估。
本模块一律同时给出：
    1) block bootstrap（按日分块，块长 = ceil(H / bars_per_day)）
    2) Newey-West t（lag = 块长 + 1）
    3) n_eff 与不重叠样本数

零分布：按日打乱 label（保留当日截面分布、破坏 pred-ret 关联），重复 B 次，
取 |IC| 的 95 分位作为「多小算噪声」的门槛。

自检：
    python -m xy.eval.ic --selftest
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ 基础统计
def _rank(a: np.ndarray) -> np.ndarray:
    """平均秩（与 scipy.stats.rankdata 一致），O(n log n)。"""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=np.float64)
    ranks[order] = np.arange(1, len(a) + 1, dtype=np.float64)
    # 处理并列
    s = a[order]
    i = 0
    n = len(a)
    while i < n:
        j = i + 1
        while j < n and s[j] == s[i]:
            j += 1
        if j - i > 1:
            ranks[order[i:j]] = ranks[order[i:j]].mean()
        i = j
    return ranks


def pooled_ic(pred: np.ndarray, ret: np.ndarray, rank: bool = True) -> float:
    m = np.isfinite(pred) & np.isfinite(ret)
    p, r = pred[m], ret[m]
    if len(p) < 10:
        return float("nan")
    if rank:
        p, r = _rank(p), _rank(r)
    p = p - p.mean()
    r = r - r.mean()
    den = np.sqrt((p * p).sum() * (r * r).sum())
    return float((p * r).sum() / den) if den > 0 else float("nan")


# ------------------------------------------------------------------ 分块工具
def _day_blocks(dates: np.ndarray, block_days: int) -> list[np.ndarray]:
    """按交易日切成连续块，返回每块的索引数组。"""
    ud = np.unique(dates)
    idx_by_day = {d: np.where(dates == d)[0] for d in ud}
    blocks = []
    for i in range(0, len(ud), block_days):
        chunk = ud[i:i + block_days]
        blocks.append(np.concatenate([idx_by_day[d] for d in chunk]))
    return blocks


def block_bootstrap_ic(
    pred: np.ndarray, ret: np.ndarray, dates: np.ndarray,
    block_days: int = 2, B: int = 2000, seed: int = 0,
) -> dict:
    """按日分块重采样，返回 IC 的均值/标准误/95% 区间。"""
    rng = np.random.default_rng(seed)
    blocks = _day_blocks(dates, block_days)
    vals = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(blocks), len(blocks))
        idx = np.concatenate([blocks[i] for i in pick])
        vals[b] = pooled_ic(pred[idx], ret[idx])
    vals = vals[np.isfinite(vals)]
    return {
        "mean": float(vals.mean()),
        "se": float(vals.std(ddof=1)),
        "lo": float(np.percentile(vals, 2.5)),
        "hi": float(np.percentile(vals, 97.5)),
    }


def newey_west_t(x: np.ndarray, lag: int) -> float:
    """单序列均值的 NW t（用于逐日 IC 序列）。"""
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean()
    e = x - mu
    var = (e * e).sum() / n
    for l in range(1, min(lag, n - 1) + 1):
        w = 1 - l / (lag + 1)
        var += 2 * w * (e[l:] * e[:-l]).sum() / n
    return float(mu / np.sqrt(var / n)) if var > 0 else float("nan")


# ------------------------------------------------------------------ 零分布
def null_threshold(
    pred: np.ndarray, ret: np.ndarray, dates: np.ndarray,
    B: int = 500, q: float = 0.95, seed: int = 0, rank: bool = True,
) -> dict:
    """按日打乱 label，得到 |IC| 的零分布，返回 q 分位。"""
    rng = np.random.default_rng(seed)
    ud = np.unique(dates)
    idx_by_day = {d: np.where(dates == d)[0] for d in ud}
    obs = pooled_ic(pred, ret, rank=rank)
    null = np.empty(B)
    for b in range(B):
        r = ret.copy()
        for d in ud:
            ii = idx_by_day[d]
            r[ii] = rng.permutation(r[ii])
        null[b] = pooled_ic(pred, r, rank=rank)
    null = np.abs(null[np.isfinite(null)])
    return {
        "observed": obs,
        "null_mean_abs": float(null.mean()),
        "null_q": float(np.percentile(null, q * 100)),
        "q": q,
        "B": B,
    }


def summarize(pred, ret, dates, horizon_bars: int = 30, bars_per_day: int = 240,
              B: int = 500) -> dict:
    """一次给出论文口径 + 三条不确定性 + 零分布门槛。"""
    block_days = max(1, int(np.ceil(horizon_bars / bars_per_day)))
    per_day = (
        pd.DataFrame({"d": dates, "p": pred, "r": ret})
        .groupby("d")[["p", "r"]]
        .apply(lambda g: pooled_ic(g["p"].values, g["r"].values))
        .values
    )
    nw_lag = block_days + 1
    n_eff = len(np.unique(dates)) * 1.0  # 保守：按日计有效样本
    return {
        "n": int(len(pred)),
        "n_days": int(len(np.unique(dates))),
        "ic_pooled": pooled_ic(pred, ret, rank=False),
        "rankic_pooled": pooled_ic(pred, ret, rank=True),
        "ic_per_day_mean": float(np.nanmean(per_day)),
        "ic_per_day_nw_t": newey_west_t(per_day, nw_lag),
        "blockboot": block_bootstrap_ic(pred, ret, dates, block_days, B),
        "null": null_threshold(pred, ret, dates, B=max(200, B // 2)),
        "block_days": block_days,
        "n_eff_lower_bound": n_eff,
    }


# ------------------------------------------------------------------ 自检
def selftest() -> None:
    rng = np.random.default_rng(42)
    n_days, n_stock, H = 40, 200, 30
    rows = []
    for d in range(n_days):
        sig = rng.normal(size=n_stock)
        ret = 0.02 * sig + rng.normal(scale=1.0, size=n_stock) * 0.05
        rows.append(pd.DataFrame({"d": d, "p": sig, "r": ret}))
    df = pd.concat(rows, ignore_index=True)

    print("=== 场景 A：真实信号 IC=0.02 量级 ===")
    s = summarize(df.p.values, df.r.values, df.d.values, B=200)
    print(f"  pooled IC   {s['ic_pooled']:+.4f}")
    print(f"  pooled RankIC {s['rankic_pooled']:+.4f}")
    print(f"  逐日 IC 均值 {s['ic_per_day_mean']:+.4f}  NW t={s['ic_per_day_nw_t']:+.2f}")
    print(f"  block boot  [{s['blockboot']['lo']:+.4f}, {s['blockboot']['hi']:+.4f}]")
    print(f"  零分布 95%  {s['null']['null_q']:.4f}（观测 |IC|={abs(s['null']['observed']):.4f}）")

    print("=== 场景 B：纯噪声（应落在零分布内）===")
    noise = rng.normal(size=len(df))
    s2 = summarize(noise, df.r.values, df.d.values, B=200)
    print(f"  pooled RankIC {s2['rankic_pooled']:+.4f}  零分布 95% {s2['null']['null_q']:.4f}")

    assert abs(s["rankic_pooled"]) > s["null"]["null_q"], "自检失败：真实信号未超过零分布"
    assert abs(s2["rankic_pooled"]) < s2["null"]["null_q"] * 1.5, "自检失败：噪声被误判为信号"
    print("SELFTEST PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
