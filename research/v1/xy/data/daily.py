"""cn_tick（3 秒成交流）→ 日频 OHLCVA 面板。

口径：
- open/close 用 arg_min/arg_max(price, seq)，seq 是当日累计序号，可靠定序；
- high/low 取当日极值；
- volume 单位「手」，amount = Σ(price × volume × 100)（精确，不用 close×vol 近似）；
- 只保留 A 股前缀 60/00/30/68，其余（B 股/ETF/转债）由票池白名单再过滤一次。

用法：
    python -m xy.data.daily                 # 全量 2024-01 → 2026-10
    python -m xy.data.daily --start 20240101 --end 20240630
"""
from __future__ import annotations

import argparse
import time

import duckdb

from xy.paths import CN_TICK, PANEL, rel

PREFIX = "('60','00','30','68')"


def build(start: str = "20240101", end: str = "20261231") -> None:
    src = str(CN_TICK / "*.parquet")
    out = PANEL / "daily_all.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)

    d0 = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    d1 = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    con.execute("PRAGMA memory_limit='8GB'")

    t0 = time.time()
    con.execute(f"""
        COPY (
            SELECT
                code,
                trade_date,
                arg_min(price, seq)              AS open,
                max(price)                       AS high,
                min(price)                       AS low,
                arg_max(price, seq)              AS close,
                sum(volume)                      AS volume,
                sum(price * volume * 100.0)      AS amount,
                count(*)                         AS n_trades
            FROM read_parquet('{src}')
            WHERE substr(code, 1, 2) IN {PREFIX}
              AND price > 0
              AND volume > 0
              AND trade_date BETWEEN DATE '{d0}' AND DATE '{d1}'
            GROUP BY code, trade_date
            ORDER BY trade_date, code
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """)

    n, nd, nc = con.execute(
        f"SELECT count(*), count(DISTINCT trade_date), count(DISTINCT code) FROM '{out}'"
    ).fetchone()
    print(f"[daily] {rel(out)}")
    print(f"[daily] rows={n:,} days={nd} codes={nc} elapsed={time.time() - t0:.1f}s")
    print(f"[daily] size={out.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="20240101")
    ap.add_argument("--end", default="20261231")
    a = ap.parse_args()
    build(a.start, a.end)


if __name__ == "__main__":
    main()
