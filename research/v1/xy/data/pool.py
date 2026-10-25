"""票池白名单 + 复权 + 收益标签。

输入：
    v1/runs/panel/daily_all.parquet        cn_tick 聚合出的未复权日频
    v1/raw/ref/stock_basic.parquet          上市/退市日（票池白名单）
    v1/raw/adj/*.parquet                    复权因子
输出：
    v1/runs/panel/daily_pool.parquet        复权后 + 白名单 + 收益标签

用法：
    python -m xy.data.pool --horizon 5
    python -m xy.data.pool --horizon 5 --audit
"""
from __future__ import annotations

import argparse

import duckdb
import pandas as pd

from xy.paths import PANEL, RAW, rel


def build(horizon: int = 5) -> None:
    daily = PANEL / "daily_all.parquet"
    basic = RAW / "ref" / "stock_basic.parquet"
    adj_glob = str(RAW / "adj" / "*.parquet")
    out = PANEL / "daily_pool.parquet"

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")

    con.execute(f"""
        CREATE OR REPLACE VIEW v_daily AS
        SELECT code, trade_date, open, high, low, close, volume, amount
        FROM read_parquet('{daily}');

        CREATE OR REPLACE VIEW v_cal AS
        SELECT CAST(strptime(cal_date, '%Y%m%d') AS DATE) AS d,
               row_number() OVER (ORDER BY cal_date) AS cal_idx
        FROM read_parquet('{RAW / "ref" / "trade_cal.parquet"}')
        WHERE is_open = 1;

        CREATE OR REPLACE VIEW v_basic AS
        SELECT symbol AS code,
               exchange,
               market,
               list_status,
               CASE WHEN list_date IS NULL OR list_date = '' THEN NULL
                    ELSE CAST(strptime(list_date, '%Y%m%d') AS DATE) END AS list_date,
               CASE WHEN delist_date IS NULL OR delist_date = '' THEN NULL
                    ELSE CAST(strptime(delist_date, '%Y%m%d') AS DATE) END AS delist_date
        FROM read_parquet('{basic}');

        CREATE OR REPLACE VIEW v_adj AS
        SELECT substr(ts_code, 1, 6) AS code,
               CAST(strptime(trade_date, '%Y%m%d') AS DATE) AS trade_date,
               adj_factor
        FROM read_parquet('{adj_glob}');
    """)

    n0, c0 = con.execute("SELECT count(*), count(DISTINCT code) FROM v_daily").fetchone()

    # 白名单：上市日 ≤ 当日 ≤ 退市日；交易所只留 SSE/SZSE/BSE
    con.execute(f"""
        COPY (
            WITH j AS (
                SELECT d.*,
                       b.list_date, b.delist_date, b.exchange, b.market,
                       a.adj_factor
                FROM v_daily d
                JOIN v_basic b USING (code)
                LEFT JOIN v_adj a ON a.code = d.code AND a.trade_date = d.trade_date
                WHERE b.exchange IN ('SSE', 'SZSE', 'BSE')
                  AND d.trade_date >= b.list_date
                  AND (b.delist_date IS NULL OR d.trade_date <= b.delist_date)
            ),
            anchored AS (
                SELECT *,
                       first_value(adj_factor) OVER (
                           PARTITION BY code ORDER BY trade_date
                       ) AS adj0
                FROM j
            ),
            adj AS (
                SELECT j.code, j.trade_date, j.list_date, j.delist_date, j.exchange, j.market,
                       j.open  * j.adj_factor / j.adj0 AS open,
                       j.high  * j.adj_factor / j.adj0 AS high,
                       j.low   * j.adj_factor / j.adj0 AS low,
                       j.close * j.adj_factor / j.adj0 AS close,
                       j.volume, j.amount,
                       j.adj_factor / j.adj0 AS adj_ratio,
                       c.cal_idx
                FROM anchored j
                LEFT JOIN v_cal c ON c.d = j.trade_date
                WHERE j.adj_factor IS NOT NULL AND j.adj0 IS NOT NULL
            )
            SELECT * EXCLUDE (cal_idx),
                   close / lag(close) OVER (PARTITION BY code ORDER BY trade_date) - 1 AS ret1,
                   lead(close, {horizon}) OVER (PARTITION BY code ORDER BY trade_date)
                       / close - 1 AS fwd_ret,
                   cal_idx - lag(cal_idx) OVER (PARTITION BY code ORDER BY trade_date) AS td_gap
            FROM adj
            ORDER BY trade_date, code
        ) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """)

    n1, c1 = con.execute(
        f"SELECT count(*), count(DISTINCT code) FROM '{out}'"
    ).fetchone()
    print(f"[pool] 输入 {n0:,} 行 / {c0:,} 票  →  输出 {n1:,} 行 / {c1:,} 票")
    print(f"[pool] 保留率 {n1 / n0:.1%}（剔除：非 A 股、未上市、已退市、无复权因子）")
    print(f"[pool] -> {rel(out)}  {out.stat().st_size / 1e6:.1f} MB")


def audit(horizon: int = 5) -> None:
    out = PANEL / "daily_pool.parquet"
    df = pd.read_parquet(out, columns=["code", "trade_date", "close", "ret1", "fwd_ret", "td_gap"])
    print("=== 审计 ===")
    print(f"日期范围   {df.trade_date.min()} → {df.trade_date.max()}  交易日 {df.trade_date.nunique()}")
    print(f"票数       {df.code.nunique():,}")
    print(f"每日票数   中位 {df.groupby('trade_date').size().median():.0f}")
    print(f"ret1 缺失  {df.ret1.isna().mean():.2%}")
    print(f"fwd_ret 缺失 {df.fwd_ret.isna().mean():.2%}")
    print(f"ret1 分位  1%={df.ret1.quantile(.01):.4f}  50%={df.ret1.median():.4f}  99%={df.ret1.quantile(.99):.4f}")
    print(f"|ret1|>0.11 占比 {(df.ret1.abs() > 0.11).mean():.4%}（含 20% 涨跌幅板块，正常）")
    print(f"|ret1|>0.25 占比 {(df.ret1.abs() > 0.25).mean():.5%}（±20% 制度下不应出现；>0 即复权有问题）")
    g = df.td_gap.dropna()
    print(f"交易日间隔  >1 天 {(g > 1).mean():.2%}  >5 天 {(g > 5).mean():.2%}  max {int(g.max())} 天"
          f"（>1 = 停牌/缺日，窗口需按 td_gap==1 过滤）")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--audit", action="store_true")
    a = ap.parse_args()
    if a.audit:
        audit(a.horizon)
    else:
        build(a.horizon)
        audit(a.horizon)


if __name__ == "__main__":
    main()
