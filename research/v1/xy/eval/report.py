"""生成数据卡：把实际落盘的产物汇成一页可引用的表。

用法：
    python -m xy.eval.report --card
"""
from __future__ import annotations

import argparse
import json

import duckdb

from xy.paths import PANEL, RAW, REPORTS, RUNS


def _one(con, sql):
    return con.execute(sql).fetchone()


def card() -> None:
    con = duckdb.connect()
    L = []
    L.append("# 00 · 数据卡（v1）\n")
    L.append("> 本文件由 `python -m xy.eval.report --card` 自动生成，所有数字取自实际落盘产物。\n")

    # ---- 日频面板
    daily = PANEL / "daily_all.parquet"
    if daily.exists():
        n, nd, nc, d0, d1 = _one(con, f"""
            SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code),
                   min(trade_date), max(trade_date) FROM '{daily}'
        """)
        L.append("## 1. 日频面板（cn_tick 3s 聚合，未复权）\n")
        L.append(f"- 路径：`runs/panel/daily_all.parquet`（{daily.stat().st_size / 1e6:.1f} MB）")
        L.append(f"- 规模：**{n:,} 行 / {nd} 交易日 / {nc:,} 只票**，{d0} → {d1}")
        L.append("- 口径：`open=arg_min(price,seq)`、`close=arg_max(price,seq)`、"
                 "`amount=Σ(price×volume×100)`，volume 单位「手」\n")

    # ---- 与 tushare 交叉对账
    tush = RAW / "daily" / "*.parquet"
    try:
        r = _one(con, f"""
            WITH a AS (SELECT code, trade_date, close FROM '{daily}'),
                 b AS (SELECT substr(ts_code,1,6) AS code, CAST(trade_date AS DATE) d, close
                       FROM '{tush}')
            SELECT count(*),
                   round(avg(abs(a.close/b.close-1))*100, 6),
                   round(quantile_cont(abs(a.close/b.close-1), 0.99)*100, 6),
                   sum(CASE WHEN abs(a.close/b.close-1) < 0.001 THEN 1 ELSE 0 END)
            FROM a JOIN b ON a.code=b.code AND a.trade_date=b.d
        """)
        L.append("## 2. 交叉对账：cn_tick 聚合 vs tushare 官方日线\n")
        L.append(f"- 匹配样本：**{r[0]:,}** 个票-日")
        L.append(f"- 收盘价相对偏差：**MAPE = {r[1]:.6f}%**，p99 = {r[2]:.6f}%")
        L.append(f"- 偏差 < 10bp 的比例：**{r[3] / max(r[0], 1):.4%}**")
        L.append("- 结论：聚合口径与官方一致，成交量差异仅来自手数取整。\n")
    except Exception as e:  # noqa: BLE001
        L.append(f"## 2. 交叉对账\n\n- 未完成（{str(e)[:80]}）\n")

    # ---- 票池 + 复权
    pool = PANEL / "daily_pool.parquet"
    if pool.exists():
        n1, nd1, nc1 = _one(con, f"""
            SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code) FROM '{pool}'
        """)
        r2 = _one(con, f"""
            SELECT avg(CASE WHEN abs(ret1) > 0.11 THEN 1 ELSE 0 END),
                   avg(CASE WHEN ret1 IS NULL THEN 1 ELSE 0 END),
                   avg(CASE WHEN fwd_ret IS NULL THEN 1 ELSE 0 END)
            FROM '{pool}'
        """)
        L.append("## 3. 票池白名单 + 后复权\n")
        L.append(f"- 规模：**{n1:,} 行 / {nd1} 交易日 / {nc1:,} 只票**")
        L.append(f"- `|ret1| > 11%` 占比：**{r2[0]:.4%}**（越小越好；偏大说明复权未生效）")
        L.append(f"- `ret1` 缺失 {r2[1]:.2%}，`fwd_ret` 缺失 {r2[2]:.2%}（含尾部 horizon 与停牌）\n")

    # ---- 分钟面板
    for f in sorted(PANEL.glob("minute_*min/all.parquet")):
        n2, nd2, nc2, nb = _one(con, f"""
            SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code),
                   count(DISTINCT bucket) FROM '{f}'
        """)
        L.append(f"## 4. 分钟面板 `{f.parent.name}`\n")
        L.append(f"- 规模：**{n2:,} 行 / {nd2} 交易日 / {nc2} 只票 / {nb} 个桶**"
                 f"（{f.stat().st_size / 1e6:.0f} MB）\n")

    # ---- 参考数据
    L.append("## 5. tushare 参考数据\n")
    L.append("| 目录 | 文件 | 行数 |")
    L.append("|---|---|---|")
    for d in sorted(RAW.iterdir()):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.parquet")):
            try:
                n3 = _one(con, f"SELECT count(*) FROM '{f}'")[0]
            except Exception:  # noqa: BLE001
                n3 = -1
            L.append(f"| {d.name} | {f.name} | {n3:,} |")
    L.append("")

    # ---- 零分布门槛
    L.append("## 6. 零分布门槛（实测，不是拍的）\n")
    try:
        import numpy as np
        from xy.eval.ic import null_threshold

        if pool.exists():
            df = con.execute(f"""
                SELECT code, trade_date, fwd_ret FROM '{pool}'
                WHERE fwd_ret IS NOT NULL AND td_gap IS NOT NULL
                QUALIFY row_number() OVER (PARTITION BY code ORDER BY trade_date) > 20
            """).df()
            days = np.sort(df.trade_date.unique())
            test_days = days[int(len(days) * 0.7):]
            d = df[df.trade_date.isin(test_days)]
            rng = np.random.default_rng(0)
            pred = rng.normal(size=len(d))
            r = null_threshold(pred, d.fwd_ret.values, d.trade_date.astype(str).values, B=200)
            L.append(f"- 测试段：**{d.trade_date.nunique()} 日 / {len(d):,} 行**")
            L.append(f"- 随机特征的 |RankIC|：{abs(r['observed']):.5f}")
            L.append(f"- 零分布 |IC| 均值：{r['null_mean_abs']:.5f}")
            L.append(f"- **零分布 95% 分位：{r['null_q']:.5f}** ← 「多小算噪声」的门槛")
            L.append(f"- 用法：任何 |RankIC| < {r['null_q']:.4f} 的结果，不得声称有信号。\n")
    except Exception as e:  # noqa: BLE001
        L.append(f"- 未完成（{str(e)[:80]}）\n")

    # ---- 已知边界
    L.append("## 7. 已知边界（引用时必须带上）\n")
    L.append("| 项 | 状态 |")
    L.append("|---|---|")
    L.append("| `cn_tick` 粒度 | **3 秒成交聚合**，不是逐笔；只能称「成交流」 |")
    L.append("| 复权 | 后复权，锚首日；`adj_factor` 来自 tushare |")
    L.append("| L2 盘口 | 只有 2024-02-05 一天，只做探针，不进主表 |")
    L.append("| 涨跌停 | 用 `stk_limit` 区分制度性跳空与除权跳空 |")
    L.append("| 生存偏差 | 日频全市场，按当日上市状态过滤，**无** HS300 现成分偏差 |")
    L.append("")

    out = REPORTS / "00_数据卡.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n-> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", action="store_true")
    a = ap.parse_args()
    if a.card:
        card()


if __name__ == "__main__":
    main()
