"""M1：cn_tick（3 秒成交流）→ 5min bar 的 12 维微观特征。

**命名纪律**：这里只有成交流，没有委托簿。所以叫「成交流不平衡」，
不叫「订单流不平衡」（OFI 是订单簿概念，已在 L2 模块单独实现）。

特征（12 维）：
    1  vol_imb      主动买卖量不平衡 (buy_vol - sell_vol) / (buy_vol + sell_vol)
    2  big_ratio    大单占比（单笔量 > 全样本 90 分位）
    3  n_trades     成交笔数（对数）
    4  avg_size     平均单笔量（对数）
    5  rv           bar 内已实现波动 Σ(log r)²
    6  path_eff     路径效率 |Δp_net| / Σ|Δp|
    7  vwap_dev     VWAP 偏离 (vwap/close - 1)
    8  amihud       |ret| / amount（流动性冲击）
    9  corr_pv      量价相关（bar 内）
   10  hhi          成交额集中度 Σ share²
   11  open_pos     开盘位置 (open - low) / (high - low)
   12  tail_pos     尾盘位置 (close - low) / (high - low)

用法：
    python -m xy.data.micro_m1 --selftest            # 只跑 2024-02-05 验证
    python -m xy.data.micro_m1 --start 20240101 --end 20261231
"""
from __future__ import annotations

import argparse
import time

import duckdb

from xy.paths import CN_TICK, PANEL, rel

PREFIX = "('60','00','30','68')"
M0, M1 = 570, 690        # 分钟数：09:30–11:30
A0, A1 = 780, 900        # 13:00–15:00


def build(start: str = "20240101", end: str = "20261231", out_name: str = "micro_m1_5min") -> None:
    src = str(CN_TICK / "*.parquet")
    daily = PANEL / "daily_all.parquet"
    out = PANEL / out_name / "all.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA memory_limit='10GB'")

    # 票池：与 K 线侧一致（2024H1 成交额前 500），保证两路同票池
    con.execute(f"""
        CREATE OR REPLACE TABLE pool AS
        SELECT code FROM (
            SELECT code, avg(amount) AS adv FROM read_parquet('{daily}')
            WHERE trade_date BETWEEN DATE '2024-01-01' AND DATE '2024-06-30'
            GROUP BY code ORDER BY adv DESC LIMIT 500);
    """)

    t0 = time.time()
    d0 = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    d1 = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    # 先算大单阈值（单独一次聚合，避免全局窗口函数拖慢主查询）
    thr = con.execute(f"""
        SELECT quantile_cont(volume, 0.9) FROM read_parquet('{src}')
        WHERE substr(code, 1, 2) IN {PREFIX} AND price > 0 AND volume > 0
          AND trade_date BETWEEN DATE '{d0}' AND DATE '{d1}'
          AND code IN (SELECT code FROM pool)
    """).fetchone()[0]
    print(f"[m1] 大单阈值（volume 90 分位）= {thr:.1f} 手", flush=True)

    con.execute(f"""
        COPY (
            WITH base AS (
                SELECT code, trade_date, seq, price, volume, bs,
                       CAST(split_part(t, ':', 1) AS INT) * 60
                       + CAST(split_part(t, ':', 2) AS INT) AS mod
                FROM read_parquet('{src}')
                WHERE substr(code, 1, 2) IN {PREFIX}
                  AND price > 0 AND volume > 0
                  AND trade_date BETWEEN DATE '{d0}' AND DATE '{d1}'
                  AND code IN (SELECT code FROM pool)
            ),
            filt AS (
                SELECT *,
                       CASE WHEN mod BETWEEN {M0} AND {M1}
                            THEN {M0} + LEAST((mod - {M0}) // 5, 23) * 5
                            ELSE {A0} + LEAST((mod - {A0}) // 5, 23) * 5 END AS bucket
                FROM base
                WHERE (mod BETWEEN {M0} AND {M1}) OR (mod BETWEEN {A0} AND {A1})
            ),
            lagged AS (
                SELECT *,
                       lag(price) OVER (PARTITION BY code, trade_date ORDER BY seq) AS p_prev,
                       price * volume * 100.0 AS trade_amt,
                       CAST({thr} AS DOUBLE) AS big_thr
                FROM filt
            ),
            sized AS (
                SELECT *,
                       sum(trade_amt) OVER (PARTITION BY code, trade_date, bucket) AS bar_amt
                FROM lagged
            ),
            agg AS (
                SELECT code, trade_date, bucket,
                       sum(volume)                                        AS vol,
                       sum(price * volume * 100.0)                        AS amt,
                       count(*)                                           AS n_trades,
                       sum(CASE WHEN bs = 0 THEN volume ELSE 0 END)       AS buy_vol,
                       sum(CASE WHEN bs = 1 THEN volume ELSE 0 END)       AS sell_vol,
                       sum(CASE WHEN bs = 2 THEN volume ELSE 0 END)       AS auc_vol,
                       sum(CASE WHEN bs = 5 THEN volume ELSE 0 END)       AS oth_vol,
                       arg_min(price, seq)                                AS open,
                       arg_max(price, seq)                                AS close,
                       max(price)                                         AS high,
                       min(price)                                         AS low,
                       sum(abs(price - p_prev))                           AS sum_abs_dp,
                       sum(CASE WHEN p_prev IS NULL THEN 0 ELSE price END) AS dp_sum,
                       count(CASE WHEN p_prev IS NOT NULL THEN 1 END)      AS n_dp,
                       sum(CASE WHEN volume > big_thr THEN volume ELSE 0 END) AS big_vol,
                       sum(price * volume)                            AS pv,
                       sum(price * price)                             AS pp,
                       sum(volume * volume)                           AS vv,
                       sum(pow(trade_amt / NULLIF(bar_amt, 0), 2))     AS hhi
                FROM sized
                GROUP BY code, trade_date, bucket
            )
            SELECT *,
                   (buy_vol - sell_vol) / NULLIF(buy_vol + sell_vol, 0)      AS vol_imb,
                   ln(1 + n_trades)                                          AS ln_trades,
                   ln(1 + vol / NULLIF(n_trades, 0))                         AS ln_avg_size,
                   CASE WHEN open > 0 THEN ln(close / NULLIF(open, 0)) ELSE NULL END AS ret,
                   sum_abs_dp / NULLIF(vol, 0)                               AS path_eff_raw,
                   big_vol / NULLIF(vol, 0)                                AS big_ratio,
                   amt / NULLIF(vol, 0) / 100.0                               AS vwap
            FROM agg
            ORDER BY trade_date, code, bucket
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """)

    n, nd, nc = con.execute(
        f"SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code) FROM '{out}'"
    ).fetchone()
    print(f"[m1] rows={n:,} days={nd} codes={nc} elapsed={time.time() - t0:.0f}s "
          f"size={out.stat().st_size / 1e6:.0f}MB -> {rel(out)}")

    # 特征派生（在 pandas 里做，SQL 太绕）
    import pandas as pd
    d = pd.read_parquet(out)
    d["vwap_dev"] = d["vwap"] / d["close"] - 1
    d["path_eff"] = (d["close"] - d["open"]).abs() / (d["sum_abs_dp"] + 1e-12)
    d["open_pos"] = (d["open"] - d["low"]) / (d["high"] - d["low"] + 1e-12)
    d["tail_pos"] = (d["close"] - d["low"]) / (d["high"] - d["low"] + 1e-12)
    d["amihud"] = d["ret"].abs() / (d["amt"] + 1e-12)
    n, sp, sv = d["n_dp"], d["pv"], d["vol"]
    cov = n * sp / n.clip(lower=1) - (d["close"] * sv) / n.clip(lower=1)
    cov = (sp - d["close"] * sv / n.clip(lower=1)) / n.clip(lower=1)
    var_p = (d["pp"] - d["close"] ** 2 / n.clip(lower=1)) / n.clip(lower=1)
    var_v = (d["vv"] - sv ** 2 / n.clip(lower=1)) / n.clip(lower=1)
    d["corr_pv"] = cov / (var_p.clip(lower=1e-18) ** 0.5 * var_v.clip(lower=1e-18) ** 0.5)
    d = d.drop(columns=["pv", "pp", "vv"], errors="ignore")
    d.to_parquet(out, index=False)
    print(f"[m1] 派生特征完成，最终 {len(d):,} 行")


def selftest() -> None:
    build("20240205", "20240205", "micro_m1_5min_probe")
    import pandas as pd
    d = pd.read_parquet(PANEL / "micro_m1_5min_probe" / "all.parquet")
    print("\n=== bs 字段实证（不靠猜）===")
    tot = d[["buy_vol", "sell_vol", "auc_vol", "oth_vol"]].sum()
    print(tot.to_string())
    print(f"\n买卖占比：买 {tot.buy_vol / (tot.buy_vol + tot.sell_vol):.3f}  "
          f"卖 {tot.sell_vol / (tot.buy_vol + tot.sell_vol):.3f}")
    print("\n=== 派生特征描述统计 ===")
    cols = ["vol_imb", "ln_trades", "ln_avg_size", "ret", "path_eff", "vwap_dev",
            "open_pos", "tail_pos", "amihud"]
    print(d[cols].describe().T[["mean", "std", "min", "max"]].to_string())
    print(f"\n缺失率：{d[cols].isna().mean().mean():.3%}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20240101")
    ap.add_argument("--end", default="20261231")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    else:
        build(a.start, a.end)


if __name__ == "__main__":
    main()
