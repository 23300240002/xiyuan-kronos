"""SDE 特征：从 cn_tick 3 秒价格提取价格过程的 σ_t 与跳跃成分。

**明确不做的事**：不估计瞬时漂移 μ。5min 尺度上 μ̂ 的信噪比约为 1/20
（信号随 t 线性增长、噪声随 √t 增长），任何"漂移特征" 97% 是噪声、
剩下 3% 就是收益率本身（已由 M2 分析证实 ret_today 的 IC=+0.4357 且为反转）。
这是高频计量经济学的标准结论，不是实现限制。

特征（6 维，全部是 OHLCV 无法精确揭示的 tick 独有信息）：
    1  dsv          下行已实现半方差 Σ min(r_i, 0)²（缩放 1e6）
    2  usv          上行已实现半方差 Σ max(r_i, 0)²（缩放 1e6）
    3  bv           双幂变差 (π/2)·Σ|r_i|·|r_{i-1}|（缩放 1e6）——连续波动部分
    4  jump_ratio   跳跃占比 (rv − bv) / rv ∈ [0,1]——离散冲击强度
    5  rskew        已实现偏度（3 秒收益的三阶矩/方差^1.5）
    6  rkurt        已实现峰度（四阶矩/方差²）

文献依据：Andersen-Bollerslev-Diebold 的已实现波动率族；Barndorff-Nielsen
& Shephard 的双幂变差；Lee & Mykland 的跳跃检验。

用法：
    python -m xy.data.sde --selftest              # 只跑 2024-02-05
    python -m xy.data.sde                         # 全量（与 M1 同票池同时间轴）
"""
from __future__ import annotations

import argparse
import time

import duckdb

from xy.paths import CN_TICK, PANEL, rel

PREFIX = "('60','00','30','68')"
M0, M1 = 570, 690        # 分钟数：09:30–11:30
A0, A1 = 780, 900        # 13:00–15:00
FREQ = 5                 # 与 K 线侧一致的 5min bar


def build(start: str = "20240101", end: str = "20261231",
          out_name: str = "micro_sde_5min") -> None:
    src = str(CN_TICK / "*.parquet")
    daily = PANEL / "daily_all.parquet"
    out = PANEL / out_name / "all.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA memory_limit='10GB'")

    # 票池与 K 线侧一致（2024H1 成交额前 500）
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

    con.execute(f"""
        COPY (
            WITH base AS (
                SELECT code, trade_date, seq, price,
                       CAST(split_part(t, ':', 1) AS INT) * 60
                       + CAST(split_part(t, ':', 2) AS INT) AS mod
                FROM read_parquet('{src}')
                WHERE substr(code, 1, 2) IN {PREFIX} AND price > 0
                  AND trade_date BETWEEN DATE '{d0}' AND DATE '{d1}'
                  AND code IN (SELECT code FROM pool)
            ),
            filt AS (
                SELECT *,
                       (mod // {FREQ}) * {FREQ} AS bucket
                FROM base
                WHERE (mod BETWEEN {M0} AND {M1}) OR (mod BETWEEN {A0} AND {A1})
            ),
            lagged AS (
                SELECT *,
                       price / lag(price) OVER (
                           PARTITION BY code, trade_date, bucket ORDER BY seq) - 1 AS r
                FROM filt
            ),
            agg AS (
                SELECT code, trade_date, bucket,
                       count(*) - 1 AS n_ret,
                       sum(r * r) AS rv,
                       sum(CASE WHEN r < 0 THEN r * r ELSE 0 END) AS dsv,
                       sum(CASE WHEN r > 0 THEN r * r ELSE 0 END) AS usv,
                       sum(pow(r, 3)) AS m3,
                       sum(pow(r, 4)) AS m4,
                       sum(abs(r)) AS abs_sum
                FROM lagged
                WHERE r IS NOT NULL
                GROUP BY code, trade_date, bucket
            ),
            lagged2 AS (
                SELECT *,
                       lag(r) OVER (
                           PARTITION BY code, trade_date, bucket ORDER BY seq) AS r_prev
                FROM lagged
                WHERE r IS NOT NULL
            ),
            bv AS (
                SELECT code, trade_date, bucket,
                       sum(abs(r) * abs(r_prev)) AS bv_raw
                FROM lagged2
                GROUP BY code, trade_date, bucket
            )
            SELECT a.code, a.trade_date,
                   a.bucket AS bucket,
                   a.n_ret,
                   a.dsv * 1e6 AS dsv,
                   a.usv * 1e6 AS usv,
                   COALESCE(b.bv_raw, 0) * 1.5707963 * 1e6 AS bv,
                   CASE WHEN a.rv > 0
                        THEN greatest((a.rv - COALESCE(b.bv_raw, 0) * 1.5707963) / a.rv, 0)
                        ELSE NULL END AS jump_ratio,
                   CASE WHEN a.rv > 0 AND a.n_ret > 2
                        THEN a.m3 / pow(a.rv, 1.5) ELSE NULL END AS rskew,
                   CASE WHEN a.rv > 0 AND a.n_ret > 2
                        THEN a.m4 / (a.rv * a.rv) ELSE NULL END AS rkurt
            FROM agg a LEFT JOIN bv b USING (code, trade_date, bucket)
            WHERE a.n_ret >= 5
        ) TO '{out}' (FORMAT PARQUET);
    """)
    n = con.execute(f"SELECT count(*) FROM '{out}'").fetchone()[0]
    print(f"[sde] {n:,} 行 → {rel(out)}  ({time.time() - t0:.0f}s)")


def selftest() -> None:
    build("20240205", "20240205", "micro_sde_5min_probe")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--start", default="20240101")
    ap.add_argument("--end", default="20261231")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        import pandas as pd
        d = pd.read_parquet(PANEL / "micro_sde_5min_probe" / "all.parquet")
        print(d[["dsv", "usv", "bv", "jump_ratio", "rskew", "rkurt"]].describe()
              .to_string())
    else:
        build(a.start, a.end)


if __name__ == "__main__":
    main()
