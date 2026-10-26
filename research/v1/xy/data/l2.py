"""L2 十档快照 → 盘口特征（M2）。

设计决策：**不重建订单簿**，直接从 3 秒十档快照算特征。
理由：重建的天花板只有 96–98%（前次实测），且依赖每票的对齐延迟 δ；
而 OFI / 深度斜率 / 盘口失衡 / 有效价差都能从快照直接算，误差不累积。

字段（QDC 口径）：
    时间 HHMMSSmmm；申买价/申卖价 1..10（整数，万分之一元）；
    申买量/申卖量 1..10（股）；当日累计成交量。

输出：每票一个 parquet，列 = 时间 + 12 个特征。

用法：
    python -m xy.data.l2 --archive l2/20240205.7z --out l2/parsed
"""
from __future__ import annotations

import argparse
import pathlib
import re
import time

import numpy as np
import pandas as pd

BID_PX = re.compile(r"^申买价(\d+)$")
ASK_PX = re.compile(r"^申卖价(\d+)$")
BID_SZ = re.compile(r"^申买量(\d+)$")
ASK_SZ = re.compile(r"^申卖量(\d+)$")


def _read_csv(p: pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(p, encoding="gb18030", low_memory=False)
    return df.loc[:, ~df.columns.str.startswith("Unnamed")]


def _sec(s: pd.Series) -> pd.Series:
    """HHMMSSmmm → 当日秒数。"""
    s = pd.to_numeric(s, errors="coerce")
    txt = s.astype("int64").astype(str).str.zfill(9)
    hh = txt.str[0:2].astype(int)
    mm = txt.str[2:4].astype(int)
    ss = txt.str[4:6].astype(int)
    ms = txt.str[6:9].astype(int)
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


# 连续竞价时段（当日秒数）：09:30–11:30、13:00–15:00
M0, M1 = 34200, 41400
A0, A1 = 46800, 54000


def snapshot_features(q: pd.DataFrame, keep_raw: bool = False) -> pd.DataFrame:
    """从十档快照算盘口特征。q 为已排序的行情表。

    keep_raw=True 时额外输出 40 个**无量纲**原始档位特征（DeepLOB 路线用）：
        bdist1..10 = (mid − bid_px_k)/mid    买档相对距离（正、随档位递增）
        adist1..10 = (ask_px_k − mid)/mid    卖档相对距离
        blog1..10  = log1p(bid_sz_k)         买档挂单量对数
        alog1..10  = log1p(ask_sz_k)         卖档挂单量对数
    价格用相对距离而非绝对值（绝对价格无跨票可比性），量取对数压尾。
    """
    bid_px = sorted([c for c in q.columns if BID_PX.match(c)], key=lambda c: int(BID_PX.match(c).group(1)))
    ask_px = sorted([c for c in q.columns if ASK_PX.match(c)], key=lambda c: int(ASK_PX.match(c).group(1)))
    bid_sz = sorted([c for c in q.columns if BID_SZ.match(c)], key=lambda c: int(BID_SZ.match(c).group(1)))
    ask_sz = sorted([c for c in q.columns if ASK_SZ.match(c)], key=lambda c: int(ASK_SZ.match(c).group(1)))
    if not (bid_px and ask_px and bid_sz and ask_sz):
        raise KeyError(f"未识别盘口列，现有列样例：{list(q.columns)[:12]}")

    t = _sec(q["时间"]).to_numpy()
    bp = q[bid_px].to_numpy(dtype=np.float64) / 1e4
    ap = q[ask_px].to_numpy(dtype=np.float64) / 1e4
    bs = q[bid_sz].to_numpy(dtype=np.float64)
    as_ = q[ask_sz].to_numpy(dtype=np.float64)

    valid = (bp[:, 0] > 0) & (ap[:, 0] > 0)
    mid = np.where(valid, (bp[:, 0] + ap[:, 0]) / 2, np.nan)
    spread = np.where(valid, (ap[:, 0] - bp[:, 0]) / np.where(mid > 0, mid, np.nan), np.nan)

    def imb(k):
        b = bs[:, :k].sum(1)
        a = as_[:, :k].sum(1)
        return (b - a) / np.where(b + a > 0, b + a, np.nan)

    # 深度斜率：前 5 档挂单量对价格距离的回归斜率（越陡=越薄）
    d = np.arange(1, 6)
    dist = np.where(valid[:, None], (mid[:, None] - bp[:, :5]) / np.where(mid[:, None] > 0, mid[:, None], np.nan), np.nan)
    slope = np.nanmean(bs[:, :5] / np.where(dist > 0, dist, np.nan), axis=1)

    # OFI（Cont–Kukanov–Stoikov, L1 标准式）：
    #   e_bid = 1{b_t>=b_{t-1}}*q_t - 1{b_t<=b_{t-1}}*q_{t-1}
    #   e_ask = 1{a_t<=a_{t-1}}*q_t - 1{a_t>=a_{t-1}}*q_{t-1}
    #   OFI   = e_bid - e_ask
    bp0, ap0 = bp[:, 0], ap[:, 0]
    bs0, as0 = bs[:, 0], as_[:, 0]
    bp_p = np.r_[bp0[0], bp0[:-1]]
    ap_p = np.r_[ap0[0], ap0[:-1]]
    bs_p = np.r_[bs0[0], bs0[:-1]]
    as_p = np.r_[as0[0], as0[:-1]]

    e_bid = np.where(bp0 >= bp_p, bs0, 0.0) - np.where(bp0 <= bp_p, bs_p, 0.0)
    e_ask = np.where(ap0 <= ap_p, as0, 0.0) - np.where(ap0 >= ap_p, as_p, 0.0)
    ofi = e_bid - e_ask
    scale = np.where((bs0 + as0) > 0, bs0 + as0, np.nan)     # 用当档挂单量归一，去掉量纲
    ofi = ofi / scale

    out = pd.DataFrame({
        "t": t,
        "mid": mid,
        "spread": spread,
        "imb1": imb(1),
        "imb5": imb(5),
        "imb10": imb(10),
        "slope5": slope,
        "ofi": ofi,
        "bid_sz1": bs[:, 0],
        "ask_sz1": as_[:, 0],
        "bid_sz10": bs.sum(1),
        "ask_sz10": as_.sum(1),
    })
    out["dmid"] = out["mid"].pct_change()

    if keep_raw:
        # 40 个无量纲原始档位特征（DeepLOB 路线）
        safe_mid = np.where(mid > 0, mid, np.nan)
        for k in range(10):
            out[f"bdist{k + 1}"] = (safe_mid - bp[:, k]) / safe_mid
            out[f"adist{k + 1}"] = (ap[:, k] - safe_mid) / safe_mid
            out[f"blog{k + 1}"] = np.log1p(np.maximum(bs[:, k], 0))
            out[f"alog{k + 1}"] = np.log1p(np.maximum(as_[:, k], 0))
    return out


def process_stock(stock_dir: pathlib.Path, keep_raw: bool = False) -> pd.DataFrame | None:
    f = stock_dir / "行情.csv"
    if not f.exists():
        return None
    q = _read_csv(f)
    if len(q) < 10:
        return None
    q = q.sort_values("时间").reset_index(drop=True)
    feat = snapshot_features(q, keep_raw=keep_raw)
    feat.insert(0, "code", stock_dir.name.split(".")[0])
    return feat


def _worker(args):
    """多进程 worker：处理单只票，返回 (文件名, DataFrame 或 None)。"""
    sd_str, date_tag, keep_raw = args
    sd = pathlib.Path(sd_str)
    try:
        feat = process_stock(sd, keep_raw=keep_raw)
    except Exception as e:  # noqa: BLE001
        return (sd.name, None, str(e)[:80])
    if feat is None:
        return (sd.name, None, None)
    feat.insert(0, "path_date", date_tag)
    return (sd.name, feat, None)


def run(archive: str, out_dir: str, limit: int | None = None,
        keep_raw: bool = False, workers: int = 8) -> None:
    date_tag = pathlib.Path(archive).stem[:8]
    import py7zr

    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[l2] 解压 {archive} → {out}")
    with py7zr.SevenZipFile(archive, mode="r") as z:
        names = z.getnames()
        targets = [n for n in names if n.endswith("行情.csv")]   # 深度无关：有的归档没有顶层日期目录
        print(f"[l2] 归档内 {len(names)} 个条目，行情表 {len(targets)} 个")
        if limit:
            keep = {n.rsplit("/", 1)[0] for n in targets[:limit]}
            targets = [n for n in names if n.rsplit("/", 1)[0] in keep]
        z.extract(path=str(out), targets=targets)
    print(f"[l2] 解压完成 {time.time() - t0:.0f}s")

    stocks = sorted([p.parent for p in out.rglob("行情.csv")])
    print(f"[l2] 待处理 {len(stocks)} 只票")
    ok = 0
    # 多进程并行（单线程实测约 1 小时/天，8 进程降到 8 分钟量级）
    import multiprocessing as mp
    jobs = [(str(sd), date_tag, keep_raw) for sd in stocks]
    with mp.Pool(processes=min(workers, 12)) as pool:
        for i, (name, feat, err) in enumerate(
                pool.imap_unordered(_worker, jobs, chunksize=8), 1):
            if err:
                print(f"  ! {name}: {err}")
            elif feat is not None:
                feat.to_parquet(out / f"{date_tag}_{name}.parquet", index=False)
                ok += 1
            if i % 500 == 0 or i == len(stocks):
                print(f"  {i}/{len(stocks)}  ok={ok}", flush=True)
    print(f"[l2] 完成 {ok} 只票，{time.time() - t0:.0f}s → {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=None, help="单个 7z 文件")
    ap.add_argument("--dir", default=None, help="存放多个 YYYYMMDD.7z 的目录")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dates", default=None, help="逗号分隔，只处理这些日期")
    ap.add_argument("--keep-raw", action="store_true",
                    help="额外保存 40 个无量纲原始十档特征（DeepLOB 路线）")
    ap.add_argument("--workers", type=int, default=8, help="并行进程数")
    a = ap.parse_args()

    if a.dir:
        import glob
        import os
        want = set(a.dates.split(",")) if a.dates else None
        arcs = sorted(glob.glob(os.path.join(a.dir, "*.7z")))
        if want:
            arcs = [p for p in arcs if os.path.basename(p)[:8] in want]
        if a.limit:
            arcs = arcs[: a.limit]
        print(f"[l2] 目录模式：{len(arcs)} 个归档")
        for i, arc in enumerate(arcs, 1):
            print(f"[l2] ({i}/{len(arcs)}) {os.path.basename(arc)}", flush=True)
            run(arc, a.out, a.limit, keep_raw=a.keep_raw, workers=a.workers)
    else:
        run(a.archive, a.out, a.limit, keep_raw=a.keep_raw, workers=a.workers)


if __name__ == "__main__":
    main()
