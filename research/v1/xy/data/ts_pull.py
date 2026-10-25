"""tushare 基础数据拉取（P0）。

用法：
    python -m xy.data.ts_pull ref                 # 交易日历 / 股票列表 / 更名
    python -m xy.data.ts_pull daily               # daily + daily_basic（按日）
    python -m xy.data.ts_pull limit               # stk_limit（按日）
    python -m xy.data.ts_pull suspend             # suspend_d（按日）
    python -m xy.data.ts_pull adj                 # adj_factor（按日）
    python -m xy.data.ts_pull index               # 指数成分与权重
    python -m xy.data.ts_pull status              # 已落盘情况

设计要点：
- 按「年」落 parquet，manifest 记录已完成交易日，可断点续跑。
- 每次调用之间 sleep，遇限流自动退避。
- 不打印 token。
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from xy.paths import RAW, rel, tushare_token

SLEEP = 0.13          # 调用间隔（秒）
MAX_RETRY = 4


def api():
    import tushare as ts
    ts.set_token(tushare_token())
    return ts.pro_api()


def _call(fn, **kw) -> pd.DataFrame:
    """带退避重试的单次调用。"""
    last = None
    for i in range(MAX_RETRY):
        try:
            df = fn(**kw)
            return df if df is not None else pd.DataFrame()
        except Exception as e:  # noqa: BLE001
            last = e
            msg = str(e)
            wait = 60 if ("每分钟" in msg or "频率" in msg or "limit" in msg.lower()) else 2 ** i
            print(f"    ! retry {i + 1}/{MAX_RETRY} after {wait}s: {msg[:120]}")
            time.sleep(wait)
    raise RuntimeError(f"调用失败: {kw}") from last


def _manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"done": []}


def _save_manifest(path: Path, m: dict) -> None:
    path.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


def trade_dates(pro, start: str, end: str) -> list[str]:
    df = _call(pro.trade_cal, exchange="SSE", start_date=start, end_date=end)
    df = df[df["is_open"] == 1].sort_values("cal_date")
    return df["cal_date"].astype(str).tolist()


# ---------------------------------------------------------------- ref
def pull_ref(pro) -> None:
    out = RAW / "ref"
    out.mkdir(parents=True, exist_ok=True)

    cal = _call(pro.trade_cal, exchange="SSE", start_date="20150101", end_date="20261231")
    cal.to_parquet(out / "trade_cal.parquet", index=False)
    print(f"  trade_cal      {len(cal):>7} 行")

    basics = []
    for st in ("L", "D", "P"):
        df = _call(pro.stock_basic, exchange="", list_status=st,
                   fields="ts_code,symbol,name,area,industry,market,exchange,"
                          "list_status,list_date,delist_date,is_hs")
        if len(df):
            basics.append(df)
        time.sleep(SLEEP)
    basic = pd.concat(basics, ignore_index=True)
    basic.to_parquet(out / "stock_basic.parquet", index=False)
    print(f"  stock_basic    {len(basic):>7} 行（L/D/P）")

    nc = _call(pro.namechange, start_date="20150101", end_date="20261231")
    nc.to_parquet(out / "namechange.parquet", index=False)
    print(f"  namechange     {len(nc):>7} 行")


# ---------------------------------------------------------------- 按日接口
DAILY_SPECS = {
    "daily": ("daily", "trade_date"),
    "daily_basic": ("daily_basic", "trade_date"),
    "limit": ("stk_limit", "trade_date"),
    "adj": ("adj_factor", "trade_date"),
    "suspend": ("suspend_d", "suspend_date"),
}


def pull_by_date(pro, kind: str, start: str, end: str) -> None:
    func_name, date_arg = DAILY_SPECS[kind]
    fn = getattr(pro, func_name)
    out = RAW / kind
    out.mkdir(parents=True, exist_ok=True)
    man_path = out / "_manifest.json"
    man = _manifest(man_path)
    done = set(man["done"])

    dates = [d for d in trade_dates(pro, start, end) if d not in done]
    print(f"  {kind}: 待拉 {len(dates)} 个交易日（已完成 {len(done)}）")
    if not dates:
        return

    by_year: dict[str, list[pd.DataFrame]] = {}
    for i, d in enumerate(dates, 1):
        df = _call(fn, **{date_arg: d})
        if len(df):
            by_year.setdefault(d[:4], []).append(df)
        done.add(d)
        if i % 40 == 0 or i == len(dates):
            print(f"    {i}/{len(dates)}  {d}  累计 {sum(len(v) for v in by_year.values())} 行")
            man["done"] = sorted(done)
            _save_manifest(man_path, man)
        time.sleep(SLEEP)

    for y, parts in by_year.items():
        f = out / f"{y}.parquet"
        new = pd.concat(parts, ignore_index=True)
        if f.exists():
            old = pd.read_parquet(f)
            new = pd.concat([old, new], ignore_index=True)
            new = new.drop_duplicates(subset=["ts_code", date_arg], keep="last")
        new.to_parquet(f, index=False)
        print(f"    -> {rel(f)}  {len(new)} 行")


# ---------------------------------------------------------------- index
def pull_index(pro) -> None:
    out = RAW / "index"
    out.mkdir(parents=True, exist_ok=True)
    codes = {"000300.SH": "hs300", "000905.SH": "zz500", "000852.SH": "zz1000"}
    for code, name in codes.items():
        df = _call(pro.index_weight, index_code=code,
                   start_date="20240101", end_date="20261031")
        if len(df):
            df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"  {code} -> {name}: {len(df)} 行")
        time.sleep(SLEEP)


# ---------------------------------------------------------------- status
def status() -> None:
    print(f"{'目录':<14}{'文件':<34}{'行数':>12}")
    for d in sorted(RAW.iterdir()):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.parquet")):
            try:
                n = len(pd.read_parquet(f, columns=None).index)
            except Exception:  # noqa: BLE001
                n = -1
            print(f"{d.name:<14}{f.name:<34}{n:>12,}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["ref", "daily", "daily_basic", "limit", "suspend", "adj", "index", "status"])
    ap.add_argument("--start", default="20240102")
    ap.add_argument("--end", default="20261015")
    a = ap.parse_args()

    if a.what == "status":
        status()
        return

    pro = api()
    if a.what == "ref":
        pull_ref(pro)
    elif a.what == "index":
        pull_index(pro)
    else:
        pull_by_date(pro, a.what, a.start, a.end)


if __name__ == "__main__":
    main()
