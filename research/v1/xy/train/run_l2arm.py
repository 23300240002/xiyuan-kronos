"""L2 三臂消融（短上下文版）——真正的 L2 预测头实验。

**为什么需要这个脚本**：L2 只有 18 天且分散在 2024–2026，
`lookback=240`（一整天）的窗口跨不过 L2 日期之间的空隙 → 有效窗口为 0。
本脚本用短上下文（默认 L=24 根=2 小时, H=12 根=1 小时），
并**直接从 L2 张量向量化地算出有效窗口**，避免遍历 1100 万个无效候选。

切分按 L2 日期（时间序）：前 12 天训练 / 中 3 天验证 / 后 3 天测试，
无日期泄漏。三臂与主实验同一套 NULL-token 受控设计。

用法：
    python -m xy.train.run_l2arm --arm 3 --seeds 0 1 2
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from xy.eval.ic import pooled_ic
from xy.model.backbone import FrozenKronos
from xy.paths import RUNS
from xy.train.run_arm import Arm


def valid_windows(xm: np.ndarray, lookback: int, horizon: int, stride: int = 1):
    """向量化找出微观窗口全有限的 (code_idx, t)。

    xm: [n_code, n_time, F]，NaN 表示无 L2 数据。
    返回按 L2 日期分组的信息，供按日切分使用。
    """
    bad = ~np.isfinite(xm).all(axis=2)               # [C, T]
    cs = np.concatenate([np.zeros((bad.shape[0], 1), dtype=np.int32),
                         np.cumsum(bad, axis=1)], axis=1)   # cs[:,t] = 前 t 列坏点数
    n_time = xm.shape[1]
    ts = np.arange(lookback - 1, n_time - horizon, stride)
    ok_cols = cs[:, ts] - cs[:, ts - lookback + 1] == 0      # [C, len(ts)]
    # 同时要求标签端（未来 horizon 根）也全有限
    fut_bad = cs[:, np.minimum(ts + horizon, n_time - 1)] - cs[:, ts] == 0
    ok = ok_cols & fut_bad
    cc, tt = np.nonzero(ok)
    return cc, ts[tt]


def day_of(t_idx: int, times_per_day: int = 48) -> int:
    return t_idx // times_per_day


def run(arm: int, seeds, device, lookback: int, horizon: int, batch: int,
        lr: float, head_hidden: int, dropout: float, wd: float, stride: int,
        epochs: int, fusion: str = "xattn"):
    x = np.load(RUNS / "tensor" / "5min" / "x.npy", mmap_mode="r")
    k_meta = json.loads((RUNS / "tensor" / "5min" / "meta.json").read_text())
    xm = np.load(RUNS / "tensor" / "micro_l2_5min" / "x.npy", mmap_mode="r")
    m_meta = json.loads((RUNS / "tensor" / "micro_l2_5min" / "meta.json").read_text())
    n_micro = int(m_meta["shape"][2])
    assert m_meta["n_code"] == k_meta["n_code"] and m_meta["n_time"] == k_meta["n_time"]

    cc, tt = valid_windows(xm, lookback, horizon, stride)
    days = tt // 48
    uniq_days = np.unique(days)
    print(f"[l2arm] 有效窗口 {len(cc):,}  覆盖 L2 日 {len(uniq_days)} 个", flush=True)
    if len(uniq_days) < 5:
        raise RuntimeError(f"L2 日太少（{len(uniq_days)}），无法按日切分")

    n_tr = int(len(uniq_days) * 12 / 18)
    n_va = int(len(uniq_days) * 3 / 18)
    tr_days = set(uniq_days[:n_tr].tolist())
    va_days = set(uniq_days[n_tr:n_tr + n_va].tolist())
    te_days = set(uniq_days[n_tr + n_va:].tolist())
    print(f"[l2arm] 切分：训练 {len(tr_days)} 日 / 验证 {len(va_days)} 日 / "
          f"测试 {len(te_days)} 日", flush=True)

    def subset(dset):
        m = np.isin(days, list(dset))
        return list(zip(cc[m].tolist(), tt[m].tolist()))

    train_idx, val_idx, test_idx = subset(tr_days), subset(va_days), subset(te_days)
    print(f"[l2arm] 窗口：train={len(train_idx):,} val={len(val_idx):,} "
          f"test={len(test_idx):,}", flush=True)

    def make_batch(idx):
        xs, ms, ys = [], [], []
        for c, t in idx:
            win = np.asarray(x[c, t - lookback + 1: t + 1], dtype=np.float32)
            if not np.isfinite(win).all():
                continue
            mwin = np.asarray(xm[c, t - lookback + 1: t + 1], dtype=np.float32)
            if not np.isfinite(mwin).all():
                continue
            cur, fut = float(x[c, t, 3]), float(x[c, t + horizon, 3])
            if cur <= 0 or not np.isfinite(fut):
                continue
            xs.append(win)
            ms.append(mwin)
            ys.append(fut / cur - 1)
        if not xs:
            return None
        return (torch.from_numpy(np.stack(xs)),
                torch.from_numpy(np.stack(ms)),
                torch.tensor(ys, dtype=torch.float32))

    def evaluate(model, backbone, idx, tag, dev):
        model.eval()
        ps, rs = [], []
        with torch.no_grad():
            for i in range(0, len(idx), batch * 4):
                b = make_batch(idx[i:i + batch * 4])
                if b is None:
                    continue
                xb, mb, yb = b
                xb, mb, yb = xb.to(dev), mb.to(dev), yb.to(dev)
                h = backbone.hidden(xb)
                ps.append(model(h, mb)[:, -1].cpu().numpy())
                rs.append(yb.cpu().numpy())
        if not ps:
            return None
        p, r = np.concatenate(ps), np.concatenate(rs)
        ic = pooled_ic(p, r, rank=False)
        ric = pooled_ic(p, r, rank=True)
        print(f"[l2arm] {tag}: n={len(p):,} IC={ic:+.5f} RankIC={ric:+.5f}",
              flush=True)
        return {"n": int(len(p)), "ic": float(ic), "rank_ic": float(ric)}

    results = []
    for seed in seeds:
        torch.manual_seed(seed)
        np.random.seed(seed)
        backbone = FrozenKronos(size="small", device=device)
        dev = str(backbone.device)
        model = Arm(arm, d_model=backbone.d_model, horizon=horizon,
                    n_micro=n_micro, head_hidden=head_hidden,
                    dropout=dropout, fusion=fusion).to(dev)
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                lr=lr, weight_decay=wd)
        best, best_state, bad, hist = -9e9, None, 0, []
        for ep in range(epochs):
            model.train()
            perm = np.random.permutation(len(train_idx))
            tot, nb = 0.0, 0
            t0 = time.time()
            for i in range(0, len(perm), batch):
                b = make_batch([train_idx[j] for j in perm[i:i + batch]])
                if b is None:
                    continue
                xb, mb, yb = b
                xb, mb, yb = xb.to(dev), mb.to(dev), yb.to(dev)
                with torch.no_grad():
                    h = backbone.hidden(xb)
                loss = nn.functional.mse_loss(model(h, mb)[:, -1], yb)
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 3.0)
                opt.step()
                tot += float(loss)
                nb += 1
            model.eval()
            ps, rs = [], []
            with torch.no_grad():
                for i in range(0, len(val_idx), batch * 4):
                    b = make_batch(val_idx[i:i + batch * 4])
                    if b is None:
                        continue
                    xb, mb, yb = b
                    xb, mb, yb = xb.to(dev), mb.to(dev), yb.to(dev)
                    h = backbone.hidden(xb)
                    ps.append(model(h, mb)[:, -1].cpu().numpy())
                    rs.append(yb.cpu().numpy())
            if not ps:
                break
            ic = float(np.corrcoef(np.concatenate(ps), np.concatenate(rs))[0, 1])
            hist.append({"epoch": ep, "train_loss": tot / max(nb, 1),
                         "val_ic": ic, "sec": round(time.time() - t0, 1)})
            print(f"  ep{ep:02d} loss={tot / max(nb, 1):.6f} val_IC={ic:+.4f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            if ic > best + 1e-4:
                best, bad = ic, 0
                best_state = {k: v.detach().cpu().clone()
                              for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= 3:
                    print(f"  早停（best={best:+.4f}）", flush=True)
                    break
        if best_state is not None:
            model.load_state_dict(best_state)

        te = evaluate(model, backbone, test_idx, f"test(arm{arm},s{seed})", dev)
        va = evaluate(model, backbone, val_idx, f"val (arm{arm},s{seed})", dev)
        row = {"arm": arm, "seed": seed, "lookback": lookback, "horizon": horizon,
               "fusion": fusion,
               "best_val_ic": best, "history": hist,
               "n_train": len(train_idx), "n_val": len(val_idx),
               "n_test": len(test_idx),
               "test": te, "val": va,
               "n_params": int(sum(p.numel() for p in model.parameters()
                                   if p.requires_grad)),
               "split": {"train_days": len(tr_days), "val_days": len(va_days),
                         "test_days": len(te_days)}}
        d = RUNS / "l2arm" / f"arm{arm}_L{lookback}_H{horizon}_{fusion}_s{seed}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text(json.dumps(row, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        results.append(row)
        print(f"[l2arm] -> {d}/result.json", flush=True)

    if results:
        (RUNS / "l2arm" / f"summary_L{lookback}_H{horizon}_{fusion}.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\n=== 跨种子汇总（测试段 IC）===")
        for arm_ in sorted({r["arm"] for r in results}):
            ics = [r["test"]["ic"] for r in results
                   if r["arm"] == arm_ and r.get("test")]
            rcs = [r["test"]["rank_ic"] for r in results
                   if r["arm"] == arm_ and r.get("test")]
            if ics:
                print(f"arm-{arm_}: IC {np.mean(ics):+.5f} ± {np.std(ics):.5f} "
                      f"RankIC {np.mean(rcs):+.5f} (n={len(ics)})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--device", default=None)
    ap.add_argument("--lookback", type=int, default=24)
    ap.add_argument("--horizon", type=int, default=12)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--head-hidden", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.3)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--fusion", default="xattn", choices=["xattn", "concat", "gate_res"])
    a = ap.parse_args()
    for arm in a.arm:
        run(arm, a.seeds, a.device, a.lookback, a.horizon, a.batch, a.lr,
            a.head_hidden, a.dropout, a.wd, a.stride, a.epochs, a.fusion)


if __name__ == "__main__":
    main()
