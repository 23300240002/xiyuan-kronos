# -*- coding: utf-8 -*-
"""循环 1 回归测试 + 循环 3 最小跨模态模型（全部闭式，无万级网格）

循环 1 回归测试（解析基线）：
  R1  I(0) = 0
  R2  I(r)/r -> 1/2  (nats)，即 I = m^2/(8 sigma^2) + o(m^2)
  R3  mmse(0) = 1
  R4  参数换算 r = m^2/(4 sigma^2),  m = 2 sigma sqrt(r)
  R5  条件 KL 闭式系数： KL(N(mu,s^2)||N(0,t^2)) = (1/2)[s^2/t^2 + mu^2/t^2 - 1 - ln(s^2/t^2)]
      B = (1/2)(s^2/t^2 - 1 - ln(s^2/t^2)) + c^2/(2 t^2) + m^2/(8 t^2)

循环 3 最小跨模态模型（共享 + 目标相关私有 + 噪声）：
  S, P_H, P_L ~ iid N(0,1)
  T = (S + P_H + P_L)/sqrt(3)                 目标，Var(T)=1
  X_H = (S, P_H),  X_L = (S, P_L)             两个模态
  Z_H = (a S + b P_H)/sqrt(a^2+b^2)           单位方差编码（尺度归一化）
  Z_L = (a S + b P_L)/sqrt(a^2+b^2)
  一致性损失 D = E[(Z_H - Z_L)^2] = 2 b^2/(a^2+b^2) =: 2 theta
  任务风险   R = 1 - 4(a+b)^2 / [3(4a^2+2b^2)]      （线性头，Bayes 最优）
  互补信息   dI = I(T;Z_H,Z_L) - I(T;Z_H)
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize_scalar
from scipy.stats import norm

TAU = 1.0
LOG2 = float(np.log(2.0))


# ---------------------------------------------------------------- 基元
def I_bpsk(r: float) -> float:
    if r <= 0:
        return 0.0
    s = np.sqrt(float(r))

    def g(n):
        p = 1.0 / (1.0 + np.exp(-2.0 * (float(r) + s * n)))
        p = min(max(p, 1e-15), 1.0 - 1e-15)
        return -norm.pdf(n) * (p * np.log(p) + (1.0 - p) * np.log(1.0 - p))

    h, _ = quad(g, -40.0, 40.0, points=[-s], limit=300, epsabs=1e-15, epsrel=1e-13)
    return float(LOG2 - h)


def mmse_bpsk(r: float) -> float:
    if r <= 0:
        return 1.0
    s = np.sqrt(float(r))

    def g(n):
        return norm.pdf(n) * np.tanh(float(r) + s * n) ** 2

    v, _ = quad(g, -40.0, 40.0, points=[-s], limit=300, epsabs=1e-15, epsrel=1e-13)
    return float(min(max(1.0 - v, 0.0), 1.0))


def kl_gauss(mu, s, tau=TAU):
    """KL(N(mu,s^2)||N(0,tau^2))，闭式。"""
    return 0.5 * (s ** 2 / tau ** 2 + mu ** 2 / tau ** 2 - 1.0 - np.log(s ** 2 / tau ** 2))


def B_closed(m, c, s, tau=TAU):
    """E_Y KL(q(Z|Y)||N(0,tau^2))，闭式（Y 平衡二元）。"""
    mu0, mu1 = c - 0.5 * m, c + 0.5 * m
    return 0.5 * (kl_gauss(mu0, s, tau) + kl_gauss(mu1, s, tau))


def B_direct(m, c, s, tau=TAU):
    """同上的直接积分（混合物? 不 —— B 是条件 KL 的平均，可逐项积分为闭式，这里只做数值校验）"""
    mu0, mu1 = c - 0.5 * m, c + 0.5 * m
    out = 0.0
    for mu in (mu0, mu1):
        f = lambda z: norm.pdf(z, mu, s) * (norm.logpdf(z, mu, s) - norm.logpdf(z, 0.0, tau))
        v, _ = quad(f, mu - 20.0, mu + 20.0, limit=200, epsabs=1e-14, epsrel=1e-12)
        out += 0.5 * v
    return float(out)


# ---------------------------------------------------------------- 循环 1
def regression_tests():
    print("=" * 94)
    print("循环 1 · 解析回归测试")
    print("=" * 94)
    ok = True

    # R1
    v = I_bpsk(0.0)
    print(f"R1  I(0) = {v:.1e}         期望 0             {'PASS' if v == 0.0 else 'FAIL'}")
    ok &= (v == 0.0)

    # R2
    print("R2  I(r)/r -> 1/2  ⟹  I = m^2/(8 sigma^2) + o(m^2)")
    for r in [1e-6, 1e-4, 1e-2, 1e-1]:
        ratio = I_bpsk(r) / r
        print(f"      r={r:<8g}  I(r)/r = {ratio:.8f}")
    r_small = 1e-6
    ratio = I_bpsk(r_small) / r_small
    good = abs(ratio - 0.5) < 1e-4
    print(f"      r=1e-6 时 I/r = {ratio:.10f}，|I/r-1/2| = {abs(ratio-0.5):.2e}  "
          f"{'PASS' if good else 'FAIL'}")
    ok &= good

    # R3
    v = mmse_bpsk(0.0)
    print(f"R3  mmse(0) = {v:.10f}   期望 1             "
          f"{'PASS' if abs(v-1.0) < 1e-12 else 'FAIL'}")
    ok &= (abs(v - 1.0) < 1e-12)

    # R4
    print("R4  参数换算 r = m^2/(4 sigma^2)  ⟺  m = 2 sigma sqrt(r)")
    for s, m in [(0.5, 1.2), (0.2, 0.3), (1.5, 0.7)]:
        r_a = m ** 2 / (4 * s ** 2)
        m_b = 2 * s * np.sqrt(r_a)
        print(f"      sigma={s}, m={m}:  r={r_a:.10f} -> m={m_b:.10f}  "
              f"|Δm|={abs(m_b-m):.2e}")
        ok &= abs(m_b - m) < 1e-12

    # R5
    print("R5  条件 KL 闭式系数（对 (m,c,sigma) 与直接积分比对）")
    worst = 0.0
    for s in [0.2, 0.5, 1.0]:
        for m, c in [(0.0, 0.0), (1.0, 0.0), (0.8, 0.25)]:
            b_c = B_closed(m, c, s)
            b_d = B_direct(m, c, s)
            worst = max(worst, abs(b_c - b_d))
            print(f"      sigma={s}, m={m}, c={c}: 闭式={b_c:.10f} 直接积分={b_d:.10f} "
                  f"|Δ|={abs(b_c-b_d):.1e}")
    print(f"      最大偏差 {worst:.2e}  {'PASS' if worst < 1e-9 else 'FAIL'}")
    ok &= (worst < 1e-9)

    print(f"\n  回归测试总判定: {'全部通过' if ok else '存在失败'}")
    return ok


# ---------------------------------------------------------------- 循环 3
def crossmodal_closed(theta):
    """单位方差编码下的闭式量。theta = b^2/(a^2+b^2) ∈ [0,1]。"""
    th = float(theta)
    a = np.sqrt(max(1.0 - th, 0.0))
    b = np.sqrt(th)
    D = 2.0 * th
    R = 1.0 - 4.0 * (a + b) ** 2 / (3.0 * (4.0 * a ** 2 + 2.0 * b ** 2))
    # I(T;Z_H) = -1/2 ln(1 - rho^2),  rho = (a+b)/sqrt(3)  （单位方差下）
    rho2 = (a + b) ** 2 / 3.0
    I_single = -0.5 * np.log(max(1.0 - rho2, 1e-300))
    I_both = -0.5 * np.log(max(R, 1e-300))       # 因 Var(T)=1, I = -1/2 ln(1-R2), R2 = 1-R
    dI = I_both - I_single
    return dict(theta=th, a=a, b=b, D=D, R=R, I_single=I_single, I_both=I_both, dI=dI)


def crossmodal_analysis():
    print("\n" + "=" * 94)
    print("循环 3 · 最小跨模态模型（闭式）")
    print("=" * 94)
    print("  模型：T=(S+P_H+P_L)/sqrt3；Z_H=(aS+bP_H)/||·||, Z_L=(aS+bP_L)/||·||（单位方差）")
    print("       theta := b^2/(a^2+b^2) ∈ [0,1]   （私有成分占比）")
    print("       D = E[(Z_H−Z_L)^2] = 2 theta；  R = 任务风险（线性头最优）")
    print("       ΔI = I(T;Z_H,Z_L) − I(T;Z_H)     互补信息\n")
    print(f"{'theta':>7} | {'a':>7} {'b':>7} | {'D':>8} | {'R':>8} | "
          f"{'I(T;Z_H)':>9} | {'I(T;Z_H,Z_L)':>12} | {'dI':>9}")
    print("-" * 94)
    rows = []
    for th in np.linspace(0.0, 1.0, 11):
        r = crossmodal_closed(th)
        rows.append(r)
        print(f"{r['theta']:>7.2f} | {r['a']:>7.4f} {r['b']:>7.4f} | {r['D']:>8.4f} "
              f"| {r['R']:>8.5f} | {r['I_single']:>9.5f} | {r['I_both']:>12.5f} "
              f"| {r['dI']:>9.5f}")

    print("\n  [闭式核查] theta=0: dI 应为 0； theta=1/2: dI 应为 (1/2)ln3 = "
          f"{0.5*np.log(3):.6f}")
    print(f"    实测 theta=0   dI = {crossmodal_closed(0.0)['dI']:.2e}")
    print(f"    实测 theta=0.5 dI = {crossmodal_closed(0.5)['dI']:.6f}")
    print(f"    theta=0 时 R = {crossmodal_closed(0.0)['R']:.6f}（= 2/3，私有信息全丢）")
    print(f"    R 最小的 theta* = ", end="")
    res = minimize_scalar(lambda t: crossmodal_closed(t)["R"], bounds=(0.0, 1.0),
                          method="bounded", options={"xatol": 1e-10})
    print(f"{res.x:.6f}，R* = {res.fun:.6f}")

    print("\n  [delta 路径]  argmin_theta  R(theta) + delta*D(theta)")
    print(f"{'delta':>8} | {'theta*':>9} | {'D':>8} | {'R':>9} | {'dI':>9}")
    print("-" * 94)
    for d in [0.0, 0.1, 0.5, 1.0, 5.0, 50.0]:
        f = lambda t: crossmodal_closed(t)["R"] + d * crossmodal_closed(t)["D"]
        rr = minimize_scalar(f, bounds=(0.0, 1.0), method="bounded",
                             options={"xatol": 1e-10})
        c = crossmodal_closed(rr.x)
        print(f"{d:>8.2f} | {rr.x:>9.6f} | {c['D']:>8.5f} | {c['R']:>9.5f} "
              f"| {c['dI']:>9.5f}")

    print("\n  [反例边界] 若私有成分与 T 无关（P_H,P_L 不进 T），则 D 可自由降为 0 而 R 不变")
    print("    构造：T = S（只用共享成分）。同一族下：")
    for th in [0.0, 0.5, 1.0]:
        a, b = np.sqrt(max(1 - th, 0)), np.sqrt(th)
        rho2 = a ** 2 / 1.0            # Cov(T,Z_H)=a, Var(Z_H)=1
        R0 = 1.0 - rho2
        print(f"      theta={th}: D={2*th:.3f}  R={R0:.5f}  "
              f"→ R 与 theta 无关，D 单调升；delta>0 时最优必然 theta=0")


if __name__ == "__main__":
    ok = regression_tests()
    crossmodal_analysis()
    print("\n" + "=" * 94)
    print(f"循环 1 回归: {'通过' if ok else '失败'}；循环 3 见上")
    print("=" * 94)
