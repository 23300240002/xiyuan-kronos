"""cn_tick（3 秒）→ 1min / 5min K 线面板（仅 500 票冻结票池）。

口径：
- 时段只留连续竞价 09:30–11:30 + 13:00–15:00（09:25 集合竞价与 15:00 后盘后剔除）；
- 5min 桶按分钟数向下取整（09:30–09:34 → 09:30）；
- OHLC 用 arg_min/arg_max(price, seq)；
- volume 单位「手」，amount = Σ(price × volume × 100)。

票池：按 2024H1 日均成交额取前 N（默认 500），名单冻结，避免生存偏差。

用法：
    python -m xy.data.minute --freq 5 --topn 500
    python -m xy.data.minute --freq 1 --topn 500
"""
from __future__ import annotations

import argparse
import time

import duckdb

from xy.paths import CN_TICK, PANEL, rel

PREFIX = "('60','00','30','68')"
M0, M1 = 570, 690      # 09:30–11:30
A0, A1 = 780, 900      # 13:00–15:00
PER = 24               # 每半场桶数（5min=24，1min=120，运行时按 freq 覆盖）


def build(freq: int = 5, topn: int = 500, start: str = "2024-01-01", end: str = "2026-12-31") -> None:
    per = 120 // freq      # 每半场桶数：5min→24，1min→120
    out_dir = PANEL / f"minute_{freq}min"
    out_dir.mkdir(parents=True, exist_ok=True)
    src = str(CN_TICK / "*.parquet")
    daily = PANEL / "daily_all.parquet"

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA memory_limit='10GB'")

    # 票池：2024H1 日均成交额前 topn
    con.execute(f"""
        CREATE OR REPLACE TABLE pool AS
        SELECT code FROM (
            SELECT code, avg(amount) AS adv
            FROM read_parquet('{daily}')
            WHERE trade_date BETWEEN DATE '2024-01-01' AND DATE '2024-06-30'
            GROUP BY code
        ) WHERE adv IS NOT NULL
        ORDER BY adv DESC LIMIT {topn};
    """)
    n_pool = con.execute("SELECT count(*) FROM pool").fetchone()[0]
    print(f"[minute] 票池 {n_pool} 只（2024H1 日均成交额前 {topn}）")

    t0 = time.time()
    out = out_dir / "all.parquet"
    con.execute(f"""
        COPY (
            WITH base AS (
                SELECT code, trade_date, seq, price, volume,
                       CAST(split_part(t, ':', 1) AS INT) * 60
                       + CAST(split_part(t, ':', 2) AS INT) AS mod
                FROM read_parquet('{src}')
                WHERE substr(code, 1, 2) IN {PREFIX}
                  AND price > 0 AND volume > 0
                  AND trade_date BETWEEN DATE '{start}' AND DATE '{end}'
            ),
            filt AS (
                SELECT *,
                       CASE
                         WHEN mod BETWEEN {M0} AND {M1}
                           THEN {M0} + LEAST((mod - {M0}) // {freq}, {per} - 1) * {freq}
                         ELSE {A0} + LEAST((mod - {A0}) // {freq}, {per} - 1) * {freq}
                       END AS bucket
                FROM base
                WHERE (mod BETWEEN {M0} AND {M1})
                   OR (mod BETWEEN {A0} AND {A1})
            )
            SELECT
                f.code,
                f.trade_date,
                f.bucket,
                arg_min(f.price, f.seq)          AS open,
                max(f.price)                     AS high,
                min(f.price)                     AS low,
                arg_max(f.price, f.seq)          AS close,
                sum(f.volume)                    AS volume,
                sum(f.price * f.volume * 100.0)  AS amount,
                count(*)                         AS n_trades
            FROM filt f
            WHERE f.code IN (SELECT code FROM pool)
            GROUP BY f.code, f.trade_date, f.bucket
            ORDER BY f.trade_date, f.code, f.bucket
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """)

    n, nd, nc, nb = con.execute(
        f"SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code), "
        f"count(DISTINCT bucket) FROM '{out}'"
    ).fetchone()
    print(f"[minute] rows={n:,} days={nd} codes={nc} buckets={nb} "
          f"elapsed={time.time() - t0:.0f}s size={out.stat().st_size / 1e6:.1f} MB")
    print(f"[minute] -> {rel(out)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", type=int, default=5, choices=[1, 5, 15])
    ap.add_argument("--topn", type=int, default=500)
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2026-12-31")
    a = ap.parse_args()
    build(a.freq, a.topn, a.start, a.end)


if __name__ == "__main__":
    main()
