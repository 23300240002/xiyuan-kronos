"""三臂统一训练入口。

arm 定义（NULL-token 受控，三臂参数量完全相同）：
    arm-1  仅 K 线：微观输入替换为可学习 [NULL]，门控 g≡0
    arm-2  仅微观：K 线输入替换为 [NULL]，门控 g≡0
    arm-3  融合：  两路都真输入，g 可学习（初值 0）

为什么用 NULL-token 而不是 mask：mask 会让该路梯度恒为 0，
三臂的梯度覆盖不同，增益就无法归因到"输入"这一个变量。

用法：
    python -m xy.train.run_arm --arm 1 --freq daily --epochs 20
    python -m xy.train.run_arm --arm 3 --freq 5min --seeds 0 1 2
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, asdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from xy.eval.ic import summarize
from xy.model.backbone import FrozenKronos
from xy.paths import RUNS


# ------------------------------------------------------------------ 组件
class Head(nn.Module):
    def __init__(self, d_in: int = 1536, d_hidden: int = 256, horizon: int = 5, p: float = 0.1):
        super().__init__()
        if d_hidden and d_hidden > 0:
            self.net = nn.Sequential(
                nn.Linear(d_in, d_hidden), nn.GELU(), nn.Dropout(p),
                nn.Linear(d_hidden, horizon),
            )
        else:                       # 线性探针
            self.net = nn.Linear(d_in, horizon)

    def forward(self, x):
        return self.net(x)


class MicroEncoder(nn.Module):
    """1min 微观 token → 与 K 线同维的表示（2 层 Transformer）。"""

    def __init__(self, d_in: int = 12, d_model: int = 128, n_layers: int = 2, n_heads: int = 4):
        super().__init__()
        self.proj = nn.Linear(d_in, d_model)
        layer = nn.TransformerEncoderLayer(d_model, n_heads, 4 * d_model,
                                           batch_first=True, dropout=0.1, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, n_layers)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x):                      # [B, T, F]
        return self.norm(self.enc(self.proj(x)))


class Fusion(nn.Module):
    """两路合并，三种模式（L2 实验证明 xattn 在短上下文+小数据下有害）：

    xattn     σ 门控交叉注意力（原始实现，K 线 query / 微观 key-value）
    concat    取 K 线末点 token 与微观序列的均值池化拼接（无注意力，最稳）
    gate_res  h + tanh(g)·W(m_mean)（标量门控残差，无注意力）
    """

    def __init__(self, d_k: int = 512, d_m: int = 128, n_heads: int = 4,
                 mode: str = "xattn"):
        super().__init__()
        self.mode = mode
        self.d_k = d_k
        if mode == "xattn":
            self.q = nn.Linear(d_k, d_k)
            self.kv = nn.Linear(d_m, d_k)
            self.attn = nn.MultiheadAttention(
                d_k, n_heads, batch_first=True, dropout=0.1)
            self.gate = nn.Parameter(torch.zeros(1))
            self.ln = nn.LayerNorm(d_k)
        elif mode == "concat":
            self.proj_m = nn.Linear(d_m, d_k)
            self.ln = nn.LayerNorm(d_k * 2)
        elif mode == "gate_res":
            self.proj_m = nn.Linear(d_m, d_k)
            self.gate = nn.Parameter(torch.zeros(1))
            self.ln = nn.LayerNorm(d_k)
        else:
            raise ValueError(mode)

    def forward(self, h, m):
        if self.mode == "xattn":
            q = self.q(h)
            kv = self.kv(m)
            a, _ = self.attn(q, kv, kv, need_weights=False)
            return self.ln(h + torch.tanh(self.gate) * a)
        m_pool = self.proj_m(m.mean(dim=1))           # [B, d_k]
        if self.mode == "concat":
            return self.ln(torch.cat([h[:, -1], m_pool], dim=-1))   # [B, 2*d_k]
        # gate_res
        return self.ln(h + torch.tanh(self.gate) * m_pool.unsqueeze(1))


class Arm(nn.Module):
    def __init__(self, arm: int, d_model: int = 512, horizon: int = 5,
                 n_micro: int = 12, n_micro_tok: int = 60,
                 head_hidden: int = 256, dropout: float = 0.1,
                 fusion: str = "xattn"):
        super().__init__()
        self.arm = arm
        self.n_micro = n_micro
        self.fusion_mode = fusion
        self.null_k = nn.Parameter(torch.zeros(1, 1, d_model))
        self.null_m = nn.Parameter(torch.zeros(1, 1, n_micro))   # 与微观特征同维，过编码器
        self.fusion = Fusion(d_model, 128, mode=fusion)
        # concat 模式融合结果是一个 [B, 2*d_model] 向量（无时间维），Head 直接吃它；
        # 其余模式保留时间维，用「末点+尾部均值+尾部标准差」三拼
        if fusion == "concat":
            self.head = Head(d_model * 2, head_hidden, horizon, dropout)
        else:
            self.head = Head(d_model * 3, head_hidden, horizon, dropout)
        # 三臂都建编码器：arm-1 让 NULL token 过编码器，保证参数量与 arm-2/3 完全相同
        self.micro_enc = MicroEncoder(n_micro)

    def forward(self, h, m=None):
        B, T, D = h.shape
        if self.arm == 1:
            m = self.null_m.expand(B, 1, self.n_micro).contiguous()   # expand 非连续，view 会失败
        elif self.arm == 2:
            h = self.null_k.expand(B, T, D).contiguous()             # 同上
            m = self.null_m.expand(B, 1, self.n_micro).contiguous() if m is None else m
        elif self.arm == 3:
            if m is None:
                raise ValueError("arm-3 需要真实微观输入；m=None 会静默退化成 arm-1")

        m = self.micro_enc(m)
        fused = self.fusion(h, m)

        if self.fusion_mode == "concat":
            return self.head(fused)          # fused: [B, 2*d_model]

        last = fused[:, -1]
        tail = fused[:, -60:]
        feat = torch.cat([last, tail.mean(1), tail.std(1)], dim=-1)
        return self.head(feat)


def rank_loss(pred: torch.Tensor, true: torch.Tensor) -> torch.Tensor:
    """RankNet 式 pairwise 损失（batch 内两两比较）。

    pred/true: [B]（已取末点）。对每对 (i,j)：
        s_ij = sign(r_i - r_j)，损失 log(1 + exp(-(p_i - p_j) * s_ij))
    直接优化排序，与 RankIC 口径一致；MSE 则被少数大涨跌主导。
    """
    p = pred.unsqueeze(0) - pred.unsqueeze(1)          # [B,B]
    r = true.unsqueeze(0) - true.unsqueeze(1)
    s = torch.sign(r)
    mask = (s != 0).float()
    loss = torch.nn.functional.logsigmoid(p * s) * mask
    return -loss.sum() / mask.sum().clamp(min=1.0)


# ------------------------------------------------------------------ 数据
@dataclass
class Batch:
    x: torch.Tensor       # [B, L, 6]
    m: torch.Tensor       # [B, Lm, F]
    y: torch.Tensor       # [B]
    date: np.ndarray


def load_tensor(freq: str):
    d = RUNS / "tensor" / freq
    x = np.load(d / "x.npy", mmap_mode="r")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    return x, meta


def load_micro(freq: str, feature_set: str = "m1"):
    """载入与 K 线对齐的微观张量；freq=daily 时返回 None。

    feature_set: m1（12 维成交流）/ sde（6 维波动率族）/ m1sde（18 维并联）
    """
    key = f"micro_{feature_set}_5min" if freq == "5min" else None
    if key is None:
        return None, None
    d = RUNS / "tensor" / key
    if not (d / "x.npy").exists():
        raise FileNotFoundError(f"缺少微观张量 {d}，先跑 xy.data.micro_tensor --set {feature_set}")
    x = np.load(d / "x.npy", mmap_mode="r")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    assert meta["n_code"] == json.loads((RUNS / "tensor" / freq / "meta.json").read_text())["n_code"], \
        "微观张量与 K 线张量票池不一致"
    return x, meta


def xsec_label(x: np.ndarray, horizon: int) -> np.ndarray:
    """截面 z-score 标签（MASTER, AAAI-24）。

    对每个时间点 t，把未来 horizon 根收益在**所有票之间**做 z-score：
        y[c,t] = (r_fwd[c,t] − mean_c(r_fwd[:,t])) / std_c(r_fwd[:,t])

    为什么这么做（本项目的实测依据）：
    - 我们的指标是截面 RankIC，但原来用原始收益做标签，被少数大涨跌主导
      → arm-1 的 RankIC(+0.060) 是 IC(+0.003) 的 18 倍，说明模型学到了排序、
        但幅度被噪声吃掉；
    - 截面标准化把标签变成"相对强弱"，与 RankIC 口径直接对齐；
    - 同时天然做了市场 beta 剔除（每个 t 减去全市场均值）。

    返回 [n_code, n_time]，未来不足 horizon 的位置为 NaN。
    """
    close = np.asarray(x[:, :, 3], dtype=np.float32)
    n_code, n_time = close.shape
    fut = np.full((n_code, n_time), np.nan, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        fut[:, :n_time - horizon] = (close[:, horizon:] /
                                     close[:, :n_time - horizon] - 1)
    mu = np.nanmean(fut, axis=0, keepdims=True)
    sd = np.nanstd(fut, axis=0, keepdims=True)
    return (fut - mu) / (sd + 1e-8)


def sample_windows(meta, lookback: int, horizon: int, stride: int, lo: str, hi: str):
    """返回 [(code_idx, t_idx, date_str)]，只保留上下文与标签都完整的窗口。"""
    times = meta["times"] if "times" in meta else None
    n_code, n_time = meta["n_code"], meta["n_time"]
    idx = []
    for c in range(n_code):
        for t in range(lookback - 1, n_time - horizon, stride):
            idx.append((c, t))
    return idx


# ------------------------------------------------------------------ 训练
def run(arm: int, freq: str, epochs: int, seed: int, device: str,
        lookback: int, horizon: int, batch: int, lr: float,
        head_hidden: int = 256, dropout: float = 0.1, wd: float = 0.01,
        stride: int = 5, loss_type: str = "mse", lam: float = 1.0,
        micro: str = "m1", size: str = "small", fusion: str = "xattn",
        label: str = "raw") -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)

    x, meta = load_tensor(freq)
    xm, mmeta = load_micro(freq, micro)
    backbone = FrozenKronos(size=size, device=device)
    device = str(backbone.device)          # 以主干实际落地的设备为准
    # daily 频段没有微观张量，用默认 12 维占位（NULL_M 路径仍可跑）
    n_micro = int(mmeta["shape"][2]) if xm is not None else 12
    model = Arm(arm, d_model=backbone.d_model, horizon=horizon, n_micro=n_micro,
                head_hidden=head_hidden, dropout=dropout, fusion=fusion).to(device)
    print(f"[arm{arm}] device={device}")

    n_code, n_time = meta["n_code"], meta["n_time"]
    n_train_time = int(n_time * 0.7)
    train_idx = [(c, t) for c in range(n_code)
                 for t in range(lookback - 1, n_train_time - horizon, stride)]
    val_idx = [(c, t) for c in range(n_code)
               for t in range(n_train_time, n_time - horizon, max(stride * 4, 20))]
    print(f"[arm{arm}] train={len(train_idx):,} val={len(val_idx):,} "
          f"n_code={n_code} n_time={n_time}")

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=lr, weight_decay=wd)

    yz = xsec_label(x, horizon) if label == "xsec_z" else None
    if yz is not None:
        print(f"[arm] 标签=截面 z-score（MASTER 口径），有效值 "
              f"{np.isfinite(yz).mean():.1%}", flush=True)

    def make_batch(idx):
        xs, ms, ys = [], [], []
        for c, t in idx:
            win = np.asarray(x[c, t - lookback + 1: t + 1], dtype=np.float32)
            if not np.isfinite(win).all():
                continue
            close_now = win[-1, 3]
            close_fut = float(x[c, t + horizon, 3])
            if not np.isfinite(close_fut) or close_now <= 0:
                continue
            mwin = None
            if xm is not None:
                mwin = np.asarray(xm[c, t - lookback + 1: t + 1], dtype=np.float32)
                if not np.isfinite(mwin).all():
                    continue          # 必须在 append 之前剔除，否则 xs/ms 长度不一致
            xs.append(win)
            if yz is not None:
                z = float(yz[c, t])
                if not np.isfinite(z):
                    continue
                ys.append(z)
            else:
                ys.append(close_fut / close_now - 1)
            if mwin is not None:
                ms.append(mwin)
        if not xs:
            return None
        xb = torch.from_numpy(np.stack(xs)).to(device)
        yb = torch.tensor(ys, dtype=torch.float32, device=device)
        mb = torch.from_numpy(np.stack(ms)).to(device) if ms else None
        return xb, yb, mb

    best = -9e9
    best_state = None
    bad = 0
    patience = 3
    hist = []
    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(len(train_idx))
        tot, nb = 0.0, 0
        t0 = time.time()
        for i in range(0, len(perm), batch):
            sel = [train_idx[j] for j in perm[i:i + batch]]
            b = make_batch(sel)
            if b is None:
                continue
            xb, yb, mb = b
            with torch.no_grad():
                h = backbone.hidden(xb)
            pred = model(h, mb)
            pl = pred[:, -1]
            if loss_type == "mse":
                loss = F.mse_loss(pl, yb)
            elif loss_type == "rank":
                loss = rank_loss(pl, yb)
            else:                                   # mse+rank 混合
                loss = F.mse_loss(pl, yb) + lam * rank_loss(pl, yb)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], 3.0)
            opt.step()
            tot += float(loss)
            nb += 1
        # 验证
        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for i in range(0, len(val_idx), batch * 4):
                b = make_batch(val_idx[i:i + batch * 4])
                if b is None:
                    continue
                xb, yb, mb = b
                h = backbone.hidden(xb)
                preds.append(model(h, mb)[:, -1].cpu().numpy())
                trues.append(yb.cpu().numpy())
        if not preds:
            break
        p = np.concatenate(preds)
        r = np.concatenate(trues)
        ic = float(np.corrcoef(p, r)[0, 1])
        hist.append({"epoch": ep, "train_loss": tot / max(nb, 1), "val_ic": ic,
                     "sec": round(time.time() - t0, 1)})
        print(f"  ep{ep:02d} loss={tot / max(nb, 1):.5f} val_IC={ic:+.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)

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
        sd = RUNS / "arm" / f"arm{arm}_{freq}_s{seed}_h{head_hidden}_d{dropout}_w{wd}_{loss_type}_{micro}_{size}_{fusion}_{label}"
        sd.mkdir(parents=True, exist_ok=True)
        torch.save(best_state, sd / "best_state.pt")

    out = {
        "arm": arm, "freq": freq, "seed": seed, "epochs": epochs,
        "lookback": lookback, "horizon": horizon,
        "best_val_ic": best, "history": hist,
        "n_train": len(train_idx), "n_val": len(val_idx),
        "n_params": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
        "head_hidden": head_hidden, "dropout": dropout, "wd": wd, "stride": stride,
        "loss": loss_type, "lam": lam, "micro": micro, "size": size, "fusion": fusion,
        "label": label,
    }
    d = RUNS / "arm" / f"arm{arm}_{freq}_s{seed}_h{head_hidden}_d{dropout}_w{wd}_{loss_type}_{micro}_{size}_{fusion}_{label}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[arm{arm}] -> {d}/result.json")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", type=int, default=1, choices=[1, 2, 3])
    ap.add_argument("--freq", default="5min",
                    choices=["daily", "5min", "1min", "15min"])
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--device", default=None)
    ap.add_argument("--lookback", type=int, default=None)
    ap.add_argument("--horizon", type=int, default=None)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--head-hidden", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--wd", type=float, default=0.01)
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--loss", default="mse", choices=["mse", "rank", "mix"])
    ap.add_argument("--lam", type=float, default=1.0)
    ap.add_argument("--micro", default="m1", choices=["m1", "sde", "m1sde"],
                    help="微观特征集：m1=成交流12维 / sde=波动率族6维 / m1sde=18维并联")
    ap.add_argument("--size", default="small", choices=["small", "base"],
                    help="Kronos 主干：small=24.7M / base=102M")
    ap.add_argument("--fusion", default="xattn", choices=["xattn", "concat", "gate_res"],
                    help="两路合并方式：xattn=交叉注意力 / concat=拼接 / gate_res=门控残差")
    ap.add_argument("--label", default="raw", choices=["raw", "xsec_z"],
                    help="标签口径：raw=原始未来收益 / xsec_z=截面 z-score（MASTER 做法，对齐 RankIC）")
    a = ap.parse_args()

    lb = a.lookback or (128 if a.freq == "daily" else 480)
    hz = a.horizon or (5 if a.freq == "daily" else 48)
    for s in a.seeds:
        run(a.arm, a.freq, a.epochs, s, a.device, lb, hz, a.batch, a.lr,
            a.head_hidden, a.dropout, a.wd, a.stride, a.loss, a.lam, a.micro,
            a.size, a.fusion, a.label)


if __name__ == "__main__":
    main()
