"""三个 full-shot 基线：DLinear / PatchTST / iTransformer。

设计纪律（对齐论文 `Appendix.tex:236-256`）：
- 输入与 arm-1 完全一致（同一批 [B, L, 6] 窗口、同一个 split、同一条 label）；
- 层数/维度用论文表里的小档（3 层 / 128）；
- 只报 pooled IC，与 arm-1 同口径比较。

用法：
    python -m xy.train.run_baseline --model dlinear
    python -m xy.train.run_baseline --model patchtst itransformer
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import torch
import torch.nn as nn

from xy.paths import RUNS


# --------------------------------------------------------------- 模型
class moving_avg(nn.Module):
    def __init__(self, k=25):
        super().__init__()
        self.k = k

    def forward(self, x):
        # x: [B, L, C]
        pad = self.k // 2
        front = x[:, :1, :].repeat(1, pad, 1)
        end = x[:, -1:, :].repeat(1, pad, 1)
        xp = torch.cat([front, x, end], dim=1)
        return nn.functional.avg_pool1d(xp.transpose(1, 2), self.k, 1).transpose(1, 2)


class DLinear(nn.Module):
    def __init__(self, seq_len: int, pred_len: int, n_ch: int = 6, k: int = 25):
        super().__init__()
        self.mv = moving_avg(k)
        self.ls = nn.Linear(seq_len, pred_len)
        self.lt = nn.Linear(seq_len, pred_len)

    def forward(self, x):                      # [B, L, C]
        tr = self.mv(x)
        se = x - tr
        out = self.ls(se.transpose(1, 2)) + self.lt(tr.transpose(1, 2))
        return out.transpose(1, 2)             # [B, H, C]


class PatchTST(nn.Module):
    def __init__(self, seq_len: int, pred_len: int, n_ch: int = 6,
                 patch: int = 16, stride: int = 8, d: int = 128,
                 layers: int = 3, heads: int = 4):
        super().__init__()
        self.p, self.s = patch, stride
        self.n_patch = (seq_len - patch) // stride + 1
        self.embed = nn.Linear(patch, d)
        enc = nn.TransformerEncoderLayer(d, heads, 4 * d, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers)
        self.head = nn.Linear(d * self.n_patch, pred_len)

    def forward(self, x):                      # [B, L, C]
        B, L, C = x.shape
        # 通道独立：把 C 当 batch
        z = x.permute(0, 2, 1).reshape(B * C, L, 1)
        patches = z.unfold(1, self.p, self.s).squeeze(2)    # [B*C, n_patch, p]
        h = self.enc(self.embed(patches))
        out = self.head(h.reshape(B * C, -1))               # [B*C, H]
        return out.reshape(B, C, -1).permute(0, 2, 1)       # [B, H, C]


class iTransformer(nn.Module):
    def __init__(self, seq_len: int, pred_len: int, n_ch: int = 6,
                 d: int = 128, layers: int = 3, heads: int = 4):
        super().__init__()
        self.embed = nn.Linear(seq_len, d)
        enc = nn.TransformerEncoderLayer(d, heads, 4 * d, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.enc = nn.TransformerEncoder(enc, layers)
        self.head = nn.Linear(d, pred_len)

    def forward(self, x):                      # [B, L, C] → 每个变量一个 token
        h = self.enc(self.embed(x.transpose(1, 2)))         # [B, C, d]
        return self.head(h).transpose(1, 2)                 # [B, H, C]


MODELS = {"dlinear": DLinear, "patchtst": PatchTST, "itransformer": iTransformer}


# --------------------------------------------------------------- 数据
def load(freq: str):
    x = np.load(RUNS / "tensor" / freq / "x.npy", mmap_mode="r")
    meta = json.loads((RUNS / "tensor" / freq / "meta.json").read_text(encoding="utf-8"))
    return x, meta


def batches(x, meta, lookback, horizon, lo, hi, stride=5, bs=128, seed=0):
    n_code, n_time = meta["n_code"], meta["n_time"]
    idx = [(c, t) for c in range(n_code)
           for t in range(max(lookback - 1, lo), min(n_time - horizon, hi), stride)]
    rng = np.random.default_rng(seed)
    while True:
        rng.shuffle(idx)
        for i in range(0, len(idx), bs):
            sel = idx[i:i + bs]
            xs, ys = [], []
            for c, t in sel:
                w = np.asarray(x[c, t - lookback + 1: t + 1], dtype=np.float32)
                if not np.isfinite(w).all():
                    continue
                f = float(x[c, t + horizon, 3])
                if not np.isfinite(f) or w[-1, 3] <= 0:
                    continue
                xs.append(w)
                ys.append(f / w[-1, 3] - 1)
            if len(xs) < 8:
                continue
            yield (torch.from_numpy(np.stack(xs)),
                   torch.tensor(ys, dtype=torch.float32))


def run(model_name: str, freq: str, epochs: int, seed: int, device: str,
        lookback: int, horizon: int, bs: int = 128, lr: float = 1e-3,
        stride: int = 5) -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)
    x, meta = load(freq)
    n_time = meta["n_time"]
    n_tr = int(n_time * 0.7)

    dev = torch.device(device or ("cuda:0" if torch.cuda.is_available() else "cpu"))
    model = MODELS[model_name](lookback, horizon).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    tr = batches(x, meta, lookback, horizon, 0, n_tr, stride=stride, bs=bs, seed=seed)
    va = batches(x, meta, lookback, horizon, n_tr, n_time, stride=20, bs=256, seed=99)

    best, best_state, bad, hist = -9e9, None, 0, []
    patience = 3
    for ep in range(epochs):
        model.train()
        tot, nb = 0.0, 0
        t0 = time.time()
        for _ in range(400):                     # 固定步数，避免 generator 无限
            try:
                xb, yb = next(tr)
            except StopIteration:
                break
            xb, yb = xb.to(dev), yb.to(dev)
            pred = model(xb)[:, -1, 3]           # 取 close 通道末点
            loss = nn.functional.mse_loss(pred, yb)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            opt.step()
            tot += float(loss)
            nb += 1
        model.eval()
        ps, rs = [], []
        with torch.no_grad():
            for _ in range(20):
                xb, yb = next(va)
                ps.append(model(xb.to(dev))[:, -1, 3].cpu().numpy())
                rs.append(yb.numpy())
        ic = float(np.corrcoef(np.concatenate(ps), np.concatenate(rs))[0, 1])
        hist.append({"epoch": ep, "loss": tot / max(nb, 1), "val_ic": ic,
                     "sec": round(time.time() - t0, 1)})
        print(f"  ep{ep:02d} loss={tot / max(nb, 1):.5f} val_IC={ic:+.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)
        # 与 arm-1 相同的早停纪律：patience=3，恢复最优状态
        if ic > best + 1e-4:
            best = ic
            bad = 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                print(f"  早停：val_IC 连续 {bad} 轮未改善（best={best:+.4f}）", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    out = {"model": model_name, "freq": freq, "seed": seed, "best_val_ic": best,
           "history": hist, "lookback": lookback, "horizon": horizon,
           "n_params": int(sum(p.numel() for p in model.parameters()))}
    d = RUNS / "baseline" / f"{model_name}_{freq}_s{seed}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{model_name}] -> {d}/result.json")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", nargs="+", default=["dlinear"],
                    choices=list(MODELS))
    ap.add_argument("--freq", default="daily", choices=["daily", "5min"])
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--device", default=None)
    ap.add_argument("--lookback", type=int, default=None,
                    help="默认 daily=128 / 5min=480；显式传入可覆盖")
    ap.add_argument("--horizon", type=int, default=None,
                    help="默认 daily=5 / 5min=48")
    ap.add_argument("--stride", type=int, default=40)
    a = ap.parse_args()
    lb = a.lookback if a.lookback else (128 if a.freq == "daily" else 480)
    hz = a.horizon if a.horizon else (5 if a.freq == "daily" else 48)
    for m in a.model:
        for s in a.seeds:
            run(m, a.freq, a.epochs, s, a.device, lb, hz, stride=a.stride)


if __name__ == "__main__":
    main()
