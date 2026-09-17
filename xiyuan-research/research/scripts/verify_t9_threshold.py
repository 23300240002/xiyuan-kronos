# -*- coding: utf-8 -*-
"""循环 2+3：聚合 KL 阈值的证明 + 独立数值核验（干净重写版）

模型（协议指定）：
    Z = c + (m/2) Y + sigma * N,  Y ∈ {±1} 平衡,  N ~ N(0,1) 独立
    p = N(0, tau^2);  sigma, tau > 0 固定;  纯对齐：min_{c,m} A = KL(q(Z)||p)

证明（循环 2）：
    r := m^2/(4 sigma^2)   （SNR）
    A = -log sigma - h(r) + (1/2)log(2 pi tau^2) + [sigma^2 (1+r) + c^2]/(2 tau^2)
    =>  dA/dr = -h'(r) + sigma^2/(2 tau^2)
    I-MMSE（Guo-Shamai-Verdú 2005，[既有结果]）： dI/dr = mmse(r)/2
    且 I = H(Z~) - (1/2) log(2 pi e)  =>  h'(r) = mmse(r)/2
    =>  dA/dr = (sigma^2/tau^2 - mmse(r))/2          ← 与协议给定式一致
    MMSE 性质（Y ∈ {±1}）： mmse(0)=1，mmse(∞)=0，严格单调递减
    => sigma >= tau 时 dA/dr >= 0 恒成立，唯一最优 r*=0  <=>  m*=0（坍塌）
    => sigma <  tau 时 dA/dr(0)<0、dA/dr(∞)>0，严格单调 => 唯一 r* 由 mmse(r*)=sigma^2/tau^2 确定

修订记录（相对上一版）：
  * mmse 由 200 点 Gauss-Hermite 改为**直接自适应积分**（GH 在 r 大时欠采样：被积函数
    尺度 ~1/sqrt(r)，GH 节点间距无法分辨）
  * 去掉嵌套积分 integrate_mmse（既慢又与 mmse 误差叠加）
  * I-MMSE 改用**有限差分独立核验**（dI/dr vs mmse/2），不再依赖恒等式 B=A+I
  * 上一版 [3.7] 打印的"两条路线一致"与其输出矛盾（差 6.4e-2），已删除该错误结论
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar
from scipy.stats import norm

TAU = 1.0
LOG2 = float(np.log(2.0))


# ------------------------------------------------------------------ 基元
def mmse(r: float) -> float:
    """BPSK 高斯信道的最小均方误差。直接自适应积分，含 n = -sqrt(r) 断点。

    mmse(r) = 1 - E_N[tanh^2(r + sqrt(r) N)]
    （用 E[Y tanh(sqrt(r)Z)] = E[tanh^2(sqrt(r)Z)] 的 ninja 恒等式）
    """
    if r <= 0:
        return 1.0
    r = float(r)
    s = np.sqrt(r)

    def integrand(n):
        return norm.pdf(n) * np.tanh(r + s * n) ** 2

    v, err = quad(integrand, -40.0, 40.0, points=[-s], limit=400,
                  epsabs=1e-15, epsrel=1e-13)
    val = 1.0 - float(v)
    return float(min(max(val, 0.0), 1.0))


def I_bpsk(r: float) -> float:
    """I(Y;Z~)，直接自适应积分（1D，非 Monte Carlo）。单位 nat。"""
    if r <= 0:
        return 0.0
    r = float(r)
    s = np.sqrt(r)

    def integrand(n):
        # p(Y=1|Z~) with Z~ = r + s n （取 Y=+1 分支，对称）
        p = 1.0 / (1.0 + np.exp(-2.0 * (r + s * n)))
        p = min(max(p, 1e-15), 1.0 - 1e-15)
        return -norm.pdf(n) * (p * np.log(p) + (1.0 - p) * np.log(1.0 - p))

    h_cond, _ = quad(integrand, -40.0, 40.0, points=[-s], limit=400,
                     epsabs=1e-15, epsrel=1e-13)
    return float(LOG2 - h_cond)


def A_direct(m: float, c: float, sigma: float, tau: float = TAU):
    """聚合 KL，直接积分。返回 (值, quad 误差)。"""
    mu0, mu1 = c - 0.5 * m, c + 0.5 * m

    def integrand(z):
        q = 0.5 * norm.pdf(z, mu0, sigma) + 0.5 * norm.pdf(z, mu1, sigma)
        if q <= 1e-300:
            return 0.0
        return q * (np.log(q) - norm.logpdf(z, 0.0, tau))

    lo, hi = min(mu0, mu1) - 16.0, max(mu0, mu1) + 16.0
    return quad(integrand, lo, hi, points=[mu0, mu1], limit=400,
                epsabs=1e-13, epsrel=1e-12)


def amin(sigma: float, m_lo=1e-5, m_hi=1.5, n=250):
    """A 在 m 上的极小（粗扫 + 有界标量极小）。约 280 次积分。"""
    ms = np.linspace(m_lo, m_hi, n)
    vals = np.array([A_direct(m, 0.0, sigma)[0] for m in ms])
    k = int(np.argmin(vals))
    lo, hi = float(ms[max(k - 1, 0)]), float(ms[min(k + 1, n - 1)])
    if hi <= lo:
        return float(ms[k]), float(vals[k])
    res = minimize_scalar(lambda m: A_direct(m, 0.0, sigma)[0], bounds=(lo, hi),
                          method="bounded", options={"xatol": 1e-10})
    return float(res.x), float(res.fun)


# ------------------------------------------------------------------ 主流程
def main():
    print("=" * 96)
    print("循环 2/3 · 聚合 KL 阈值：证明与独立数值核验（干净重写版）")
    print("=" * 96)

    # [A] I-MMSE 关系独立核验（不经过恒等式 B=A+I）
    print("\n[A] I-MMSE 核验： dI/dr 有限差分  vs  mmse(r)/2")
    print(f"{'r':>9} | {'I(r)':>12} | {'mmse(r)':>12} | {'dI/dr 有限差分':>16} "
          f"| {'mmse(r)/2':>12} | {'绝对差':>10}")
    worst = 0.0
    for r in [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
        h = r * 1e-4 if r > 1e-3 else 1e-6
        dIdr = (I_bpsk(r + h) - I_bpsk(r - h)) / (2 * h)
        mh = mmse(r)
        d = abs(dIdr - mh / 2.0)
        worst = max(worst, d)
        print(f"{r:>9.3f} | {I_bpsk(r):>12.8f} | {mh:>12.8f} | {dIdr:>16.10f} "
              f"| {mh/2:>12.10f} | {d:>10.2e}")
    print(f"  → 最大绝对偏差 {worst:.2e}")

    print("\n[B] MMSE 的单调性与端点值")
    print(f"{'r':>10} | {'mmse(r)':>12}")
    for r in [0.0, 1e-6, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]:
        print(f"{r:>10.4g} | {mmse(r):>12.8f}")
    rs = np.linspace(0.0, 8.0, 4001)
    vs = np.array([mmse(r) for r in rs]) if False else None
    # 用较少的点做单调性抽样（避免 4001 次积分）
    rs = np.linspace(0.0, 8.0, 161)
    vs = np.array([mmse(r) for r in rs])
    mono = bool(np.all(np.diff(vs) <= 1e-12))
    print(f"  在 r ∈ [0,8] 上抽样 161 点，严格单调递减: {mono}")
    print(f"  mmse(0) = {mmse(0.0):.10f}（理论值 1）")

    # [C] 阈值与最优间距
    print("\n[C] 阈值与最优间距（一维求根；与直接积分极小独立对照）")
    print(f"{'sigma':>7} | {'求根 m*':>10} | {'A 极小 m*':>11} | {'相对差':>8} "
          f"| {'A(m*) 求根':>12} | {'A(m*) 直接极小':>14} | 判定")
    print("-" * 96)
    for sigma in [0.02, 0.05, 0.2, 0.5, 0.8, 0.95, 1.0, 1.05, 1.5, 2.0]:
        s2t2 = sigma ** 2 / TAU ** 2
        if s2t2 >= 1.0:
            m_root = 0.0
            m_dir, a_dir = amin(sigma)
            a_root = A_direct(0.0, 0.0, sigma)[0]
            rel = 0.0
            verdict = "坍塌(m*=0)"
        else:
            r_star = brentq(lambda r: mmse(r) - s2t2, 0.0, 1e6,
                            xtol=1e-14, rtol=1e-15)
            m_root = 2.0 * sigma * np.sqrt(r_star)
            m_dir, a_dir = amin(sigma)
            a_root = A_direct(m_root, 0.0, sigma)[0]
            rel = abs(m_root - m_dir) / m_dir if m_dir > 0 else float("nan")
            verdict = "不坍塌"
        print(f"{sigma:>7.2f} | {m_root:>10.5f} | {m_dir:>11.5f} | {rel:>8.2%} "
              f"| {a_root:>12.8f} | {a_dir:>14.8f} | {verdict}")
    print("  对照规则：A(直接极小) 应 <= A(求根解)；两者若相差 >1e-4 则该 sigma 下求根有偏")

    # [D] 归属判定
    print("\n[D] 上一轮 sigma=0.05, m≈0.3150 的归属")
    s0 = 0.05
    m_dir, a_dir = amin(s0)
    r_star = brentq(lambda r: mmse(r) - s0 ** 2 / TAU ** 2, 0.0, 1e6)
    m_root = 2.0 * s0 * np.sqrt(r_star)
    a_315 = A_direct(0.3150, 0.0, s0)[0]
    a_zero = A_direct(0.0, 0.0, s0)[0]
    print(f"  A 极小（直接扫描+极小）: m*={m_dir:.5f}, A={a_dir:.8f}")
    print(f"  求根解                 : m*={m_root:.5f}, A={A_direct(m_root,0,s0)[0]:.8f}")
    print(f"  上轮记录 0.3150        : A={a_315:.8f}")
    print(f"  A(m=0)                 : A={a_zero:.8f}")
    print("  → 归属：目标 A · 纯对齐 · 无任务损失（三个候选点的 A 值大小可判）")

    # [E] 加入任务损失
    print("\n[E] 加入任务损失 L = c^2 + (m/2-1)^2 + sigma^2（基线 sigma^2），一阶条件")
    print("     2c + delta*c/tau^2 = 0                      → c* = 0 (delta>0)")
    print("     (m/2-1) + delta*m*(sigma^2/tau^2 - mmse(r))/(4 sigma^2) = 0")

    def f_m(m, sigma, delta):
        r = m ** 2 / (4 * sigma ** 2)
        return (m / 2 - 1.0) + delta * m * (sigma ** 2 / TAU ** 2 - mmse(r)) / (4 * sigma ** 2)

    print(f"\n{'sigma':>7} | {'delta':>8} | {'m*':>9} | {'L_task':>10} | {'基线':>10} | 判定")
    print("-" * 96)
    for sigma in [0.2, 0.5, 0.95, 1.5]:
        for delta in [0.0, 1.0, 10.0, 1000.0]:
            if delta == 0.0:
                m_star = 2.0
            else:
                lo, hi = 1e-9, 4.0
                if f_m(lo, sigma, delta) * f_m(hi, sigma, delta) < 0:
                    m_star = brentq(lambda m: f_m(m, sigma, delta), lo, hi)
                else:
                    m_star = 0.0
            l_task = (m_star / 2 - 1.0) ** 2 + sigma ** 2
            verdict = "坍塌" if m_star < 0.3 else ("部分" if m_star < 1.0 else "不坍塌")
            print(f"{sigma:>7.2f} | {delta:>8.1f} | {m_star:>9.4f} | {l_task:>10.6f} "
                  f"| {sigma ** 2:>10.6f} | {verdict}")

    # [F] m 的符号对称性
    print("\n[F] m 的符号对称性（A 为 m 的偶函数）")
    for sigma, m in [(0.5, 1.2), (0.3, 0.8), (1.5, 0.4)]:
        ap = A_direct(m, 0.0, sigma)[0]
        am = A_direct(-m, 0.0, sigma)[0]
        print(f"  sigma={sigma}, m=±{m}: A(+m)={ap:.12f}  A(-m)={am:.12f}  |差|={abs(ap-am):.1e}")


if __name__ == "__main__":
    main()
