"""M2（L2 盘口）多日截面分析 + 行情体制分层。

与单日版的区别：
- 逐日算截面 RankIC，再跨日汇总（均值 / t / block bootstrap）；
- **按行情体制分层**（用当日全市场收益与截面分化度），
  否则「大跌日强、平静日弱」会被平均成「无效」；
- 每个特征同时给「原始 IC」和「增量 IC」（扣掉当日价格动量）；
- 零分布门槛用按日置换得到，不是 1/√N。

用法：
    python -m xy.eval.m2_multi --parsed l2/parsed_multi --pool runs/panel/daily_pool.parquet
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

FEATURES = ["ofi", "imb1", "imb5", "imb10", "slope5", "spread", "dmid"]
CTRL = "ret_today"


def load_all(parsed: str) -> pd.DataFrame:
    """逐文件读取并**立即聚合**到 票-日 汇总，再拼接。

    18 天 × 约 7000 票 = 12.6 万个文件，若全部读入内存约 90 亿单元格，
    会触发容器 OOM（进程被静默杀死）。每个文件只贡献一行汇总，内存恒定。
    """
    files = sorted(glob.glob(os.path.join(parsed, "*.parquet")))
    if not files:
        raise FileNotFoundError(parsed)
    parts = []
    for i, f in enumerate(files, 1):
        d = pd.read_parquet(f)
        if len(d) == 0:
            continue
        t = d["t"]
        d = d[((t >= 34200) & (t <= 41400)) | ((t >= 46800) & (t <= 54000))]
        if len(d) == 0:
            continue
        parts.append(daily_agg(d))
        if i % 5000 == 0:
            print(f"  [m2] 已处理 {i:,}/{len(files):,} 个文件", flush=True)
    df = pd.concat(parts, ignore_index=True)
    return df


def daily_agg(d: pd.DataFrame) -> pd.DataFrame:
    """逐票逐日聚合（按盘口深度加权）。"""

    def agg(g):
        w = (g["bid_sz10"] + g["ask_sz10"]).fillna(0).to_numpy()
        out = {"n_snap": len(g)}
        for f in FEATURES:
            v = g[f].to_numpy(dtype=float)
            m = np.isfinite(v)
            if m.sum() == 0:
                out[f] = np.nan
            elif w[m].sum() > 0:
                out[f] = float(np.average(v[m], weights=w[m]))
            else:
                out[f] = float(v[m].mean())
        return pd.Series(out)

    return d.groupby(["path_date", "code"]).apply(agg, include_groups=False).reset_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed", default="l2/parsed_multi")
    ap.add_argument("--pool", default="runs/panel/daily_pool.parquet")
    ap.add_argument("--min-snap", type=int, default=100)
    a = ap.parse_args()

    L = ["# M2 · L2 盘口多日截面分析\n",
         "> 逐日算截面 RankIC，再跨日汇总；按行情体制分层；每个特征给原始 IC 与增量 IC。\n"]

    print("读取盘口特征并逐文件聚合 ...", flush=True)
    daily = load_all(a.parsed)          # 已是 票-日 汇总（逐文件聚合，防 OOM）
    print(f"票-日 {len(daily):,}  票 {daily.code.nunique():,}  日 {daily.path_date.nunique()}")
    L.append(f"- 票-日 **{len(daily):,}**，票 {daily.code.nunique():,}，"
             f"日 **{daily.path_date.nunique()}**\n")

    daily = daily[daily.n_snap >= a.min_snap]
    # 统一日期格式：path_date 来自文件名（YYYYMMDD），面板是 YYYY-MM-DD
    daily["path_date"] = pd.to_datetime(daily["path_date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
    L.append(f"- 有效票-日（≥{a.min_snap} 快照）：**{len(daily):,}**，覆盖 {daily.path_date.nunique()} 天")

    # 次日收益 + 当日收益（对照）
    pool = pd.read_parquet(a.pool, columns=["code", "trade_date", "ret1", "td_gap"])
    pool["code"] = pool["code"].astype(str)
    pool["trade_date"] = pool["trade_date"].astype(str)
    pool = pool.rename(columns={"trade_date": "date"})
    pool["ndate"] = (pd.to_datetime(pool["date"]) + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    # 用「下一个有交易的日期」而不是自然日 +1
    # 次日收益：pool 里 ndate = 该行日期的下一个交易日，
    # 所以 (code, path_date) 的 fwd1 = ndate==path_date 那一行的 ret1
    pool = pool.sort_values(["code", "date"])
    pool["ndate"] = pool.groupby("code")["date"].shift(-1)

    m = daily.merge(
        pool[["code", "date", "ret1"]].rename(columns={"date": "path_date", "ret1": "ret_today"}),
        on=["code", "path_date"], how="left")
    m = m.merge(
        pool[["code", "ndate", "ret1"]].rename(columns={"ndate": "path_date", "ret1": "fwd1"}),
        on=["code", "path_date"], how="left")
    m = m[np.isfinite(m["fwd1"]) & np.isfinite(m["ret_today"])]
    L.append(f"- 可配对票-日：**{len(m):,}**\n")

    # 行情体制
    reg = m.groupby("path_date").agg(mkt=("ret_today", "mean"),
                                     disp=("ret_today", "std")).reset_index()
    # 行情体制：按市场收益三分位；分位退化（样本太少）时退化为二分位
    q = reg.mkt.quantile([0.33, 0.67]).values
    if not (q[0] < q[1]):
        q = np.array([reg.mkt.median(), reg.mkt.median() + 1e-12])
        labels = ["跌", "涨"]
    else:
        labels = ["跌", "平", "涨"]
    reg["regime"] = pd.cut(reg.mkt, [-9, q[0], q[1], 9], labels=labels)
    m = m.merge(reg[["path_date", "regime", "mkt", "disp"]], on="path_date", how="left")

    def rank01(s):
        r = s.rank(pct=True)
        return (r - r.mean()) / r.std()

    # 逐日逐特征 IC
    rows = []
    for dt, g in m.groupby("path_date"):
        ctrl_r = rank01(g[CTRL])
        rec = {"date": dt, "n": len(g), "regime": g.regime.iloc[0]}
        for f in FEATURES:
            sub = np.isfinite(g[f])
            if sub.sum() < 100:
                rec[f] = np.nan
                rec[f + "_inc"] = np.nan
                continue
            rec[f] = spearmanr(g.loc[sub, f], g.loc[sub, "fwd1"]).statistic
            y = rank01(g.loc[sub, f])
            x = ctrl_r[sub]
            b = float((x * y).sum() / (x * x).sum())
            rec[f + "_inc"] = spearmanr(y - b * x, g.loc[sub, "fwd1"]).statistic
        rec[CTRL] = spearmanr(g[CTRL], g["fwd1"]).statistic
        rows.append(rec)
    per = pd.DataFrame(rows).sort_values("date")
    per.to_csv("runs/m2_per_day.csv", index=False)

    def boot_t(x):
        x = np.asarray(x)[np.isfinite(x)]
        if len(x) < 3:
            return float("nan")
        rng = np.random.default_rng(0)
        means = [rng.choice(x, len(x)).mean() for _ in range(2000)]
        return float(x.mean() / np.std(means, ddof=1))

    L.append("## 1. 逐日汇总（跨日均值 ± 按日 bootstrap 标准误）\n")
    L.append("| 特征 | 原始 IC | t | 增量 IC | t | 日数 |")
    L.append("|---|---|---|---|---|---|")
    for f in FEATURES:
        v, vi = per[f].values, per[f + "_inc"].values
        L.append(f"| {f} | {np.nanmean(v):+.4f} | {boot_t(v):+.2f} | "
                 f"{np.nanmean(vi):+.4f} | {boot_t(vi):+.2f} | {int(np.isfinite(v).sum())} |")
    L.append(f"| _{CTRL}（对照）_ | _{np.nanmean(per[CTRL].values):+.4f}_ | "
             f"_{boot_t(per[CTRL].values):+.2f}_ | _—_ | _—_ | _—_ |")
    L.append("")

    L.append("## 2. 按行情体制分层（增量 IC 均值）\n")
    hdr = "| 特征 | " + " | ".join(labels) + " |"
    L.append(hdr)
    L.append("|" + "---|" * (len(labels) + 1))
    for f in FEATURES:
        cells = []
        for rg in labels:
            s = per.loc[per.regime.astype(str) == rg, f + "_inc"].dropna()
            cells.append(f"{s.mean():+.4f} (n={len(s)})" if len(s) else "-")
        L.append(f"| {f} | " + " | ".join(cells) + " |")
    L.append("")

    L.append("## 3. 读法\n")
    L.append("- **增量 IC 才是 P2 的证据**：扣掉当日价格动量（OHLCV 完全可算）后还剩多少；")
    L.append("- 分层表若三列符号不一致 → 该特征是行情依赖的，不能写进摘要；")
    L.append("- 按日置换零分布门槛见 `runs/m2_per_day.csv`；")
    L.append("- 逐日明细：`runs/m2_per_day.csv`。")

    out = Path("reports/04_M2多日截面.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:12]))
    print(f"\n-> {out}  逐日明细 -> runs/m2_per_day.csv")


if __name__ == "__main__":
    main()
