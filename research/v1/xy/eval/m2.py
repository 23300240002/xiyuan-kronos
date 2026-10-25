"""M2（L2 盘口特征）单日截面分析。

输入：
    l2/parsed/*.parquet        xy/data/l2 产出的逐票盘口特征
    runs/panel/daily_pool.parquet  复权后日频（取次日收益）

做三件事：
    1) 覆盖率审计：多少票有有效盘口特征；
    2) 逐特征算「当日盘口 → 次日收益」的截面 RankIC（全市场）；
    3) 明确标注 n_days=1，只报点估计与零分布对比，**不下结论**。

用法：
    python -m xy.eval.m2 --parsed l2/parsed --date 20240205
"""
from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = ["ofi", "imb1", "imb5", "imb10", "slope5", "spread", "dmid", "bid_sz10", "ask_sz10"]


def load_parsed(parsed: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(parsed, "*.parquet")))
    if not files:
        raise FileNotFoundError(f"没有 parquet：{parsed}")
    parts = []
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception:  # noqa: BLE001
            continue
        if len(d) == 0:
            continue
        # 只取连续竞价时段（当日秒数：09:30–11:30 = 34200–41400；13:00–15:00 = 46800–54000）
        t = d["t"]
        d = d[((t >= 34200) & (t <= 41400)) | ((t >= 46800) & (t <= 54000))]
        if len(d) == 0:
            continue
        parts.append(d)
    if not parts:
        raise RuntimeError("所有 parquet 都没有有效时段数据")
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed", default="l2/parsed")
    ap.add_argument("--date", default="20240205")
    ap.add_argument("--pool", default="runs/panel/daily_pool.parquet")
    a = ap.parse_args()

    L = ["# M2 · L2 盘口特征单日截面分析\n",
         f"> 日期 {a.date}，数据源 `{a.parsed}`。**n_days=1，只报点估计，不作任何结论。**\n"]

    print("读取盘口特征 ...", flush=True)
    d = load_parsed(a.parsed)
    d["code"] = d["code"].astype(str)
    n_stock = d.code.nunique()
    print(f"票数 {n_stock:,}  快照 {len(d):,}")
    L.append(f"- 覆盖：**{n_stock:,} 只票**，快照 {len(d):,} 条")

    # 逐票日度聚合（成交量加权）
    def agg(g):
        w = g["bid_sz10"] + g["ask_sz10"]
        w = w.fillna(0)
        out = {}
        for f in FEATURES:
            v = g[f]
            m = np.isfinite(v.to_numpy())
            if m.sum() == 0:
                out[f] = np.nan
            elif w[m].sum() > 0:
                out[f] = float(np.average(v.to_numpy()[m], weights=w.to_numpy()[m]))
            else:
                out[f] = float(v.to_numpy()[m].mean())
        out["n_snap"] = int(len(g))
        return pd.Series(out)

    daily = d.groupby("code").apply(agg, include_groups=False).reset_index()
    daily = daily[daily["n_snap"] >= 100]          # 至少 100 个有效快照
    L.append(f"- 有效票（≥100 快照）：**{len(daily):,}**")

    # 次日收益（注意：面板里 trade_date 是 'YYYY-MM-DD'，必须同格式比较）
    pool = pd.read_parquet(a.pool, columns=["code", "trade_date", "ret1", "td_gap"])
    pool["code"] = pool["code"].astype(str)
    pool["trade_date"] = pool["trade_date"].astype(str)
    d0 = pd.Timestamp(a.date).strftime("%Y-%m-%d")
    nxt = pool[pool.trade_date > d0].sort_values("trade_date")
    nxt = nxt.groupby("code").first().reset_index()
    nxt = nxt.rename(columns={"trade_date": "next_date", "ret1": "fwd1"})
    nxt["next_date"] = nxt["next_date"].astype(str)
    if len(nxt):
        L.append(f"- 次日：**{nxt.next_date.min()}**，可用 {nxt.fwd1.notna().sum():,} 只")

    m = daily.merge(nxt[["code", "fwd1", "next_date"]], on="code", how="inner")
    m = m[np.isfinite(m["fwd1"])]

    # 对照：当日收益（ret1）作为「价格动量」基线。
    # 若某盘口特征的 IC ≈ ret1 的 IC，说明它只是当日涨跌的代理，没有增量信息。
    same = pool[pool.trade_date == d0][["code", "ret1"]]
    m = m.merge(same, on="code", how="left")
    m = m.rename(columns={"ret1": "ret_today"})
    L.append(f"- 可配对：**{len(m):,} 只票**\n")

    # 逐特征截面 RankIC（含对照）+ 增量 IC
    L.append("| 特征 | 有效样本 | 截面 RankIC | 增量 RankIC（扣掉当日动量后） | 说明 |")
    L.append("|---|---|---|---|---|")
    from scipy.stats import spearmanr

    def rank01(s):
        r = s.rank(pct=True)
        return (r - r.mean()) / r.std()

    ctrl_r = rank01(m["ret_today"]) if "ret_today" in m else None
    rows = []
    for f in FEATURES + ["ret_today"]:
        sub_mask = np.isfinite(m[f])
        if ctrl_r is not None:
            sub_mask = sub_mask & np.isfinite(m["ret_today"])
        if sub_mask.sum() < 50:
            continue
        rho = spearmanr(m.loc[sub_mask, f], m.loc[sub_mask, "fwd1"]).statistic
        # 增量：把特征对当日动量做截面回归，取残差再算 IC
        if ctrl_r is not None and f != "ret_today":
            y = rank01(m.loc[sub_mask, f])
            x = ctrl_r[sub_mask]
            b = float((x * y).sum() / (x * x).sum())
            resid = y - b * x
            rho_inc = spearmanr(resid, m.loc[sub_mask, "fwd1"]).statistic
        else:
            rho_inc = float("nan")
        rows.append((f, int(sub_mask.sum()), rho, rho_inc))
        tag = " ← 对照" if f == "ret_today" else ""
        L.append(f"| {f}{tag} | {int(sub_mask.sum()):,} | {rho:+.4f} | {rho_inc:+.4f} |  |")
    L.append("")
    L.append("**读法**：")
    L.append(f"- 单日截面，|RankIC| 的噪声量级约 1/√N ≈ "
             f"{1 / np.sqrt(max(len(m), 1)):.4f}（N={len(m):,}）；")
    L.append("- **增量 RankIC 才是 P2 的证据**：它把「当日价格动量」"
             "（由 OHLCV 完全可算）扣掉之后，盘口特征还剩多少预测力；")
    L.append("- 单日样本无法区分信号与行情（2024-02-05 是急跌日、02-06 反弹，"
             "全市场同向运动会让任何与当日跌幅相关的特征都显出高 IC）；")
    L.append("- **禁止**把这张表写进任何结论，只能写「符号为 X，待 ≥20 日验证」。")

    out = Path("reports/02_M2单日截面.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:14]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
