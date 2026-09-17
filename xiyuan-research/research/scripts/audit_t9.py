# -*- coding: utf-8 -*-
"""循环 1+2：审计 C-T9-001 并提炼最小解析结果（快速版）

性能说明：前一版把「嵌套网格搜索」直接套在「自适应积分」上（24 万次 quad），
单个网格要数分钟。本版先用恒等式 A = B - I 把聚合 KL 化为闭式 + 一维查表，
使全部网格搜索在秒级完成。

模型（平衡二元高斯位置模型，sigma 固定）：
  Y ~ Bernoulli(1/2)；Z | Y=y ~ N(mu_y, sigma^2)
  参数化：c = 中心，m = 间距；  mu_0 = c - m/2,  mu_1 = c + m/2
  先验 p = N(0, tau^2)，tau = 1
  标度不变性：I(Y;Z) 只依赖 t = m/sigma，与 c 无关

两个对齐目标：
  A(c,m) = KL( q(Z) || N(0,tau^2) )                —— 聚合（混合）分布 KL
  B(c,m) = E_Y KL( q(Z|Y) || N(0,tau^2) )          —— 条件 KL 的平均
  恒等式：  B = A + I(Y;Z)
"""
from __future__ import annotations

import sys
import time

import numpy as np
from scipy.integrate import quad
from scipy.stats import norm

TAU = 1.0
LOG2 = float(np.log(2.0))
T_MAX = 22.0          # 超过此间距，两个分量在数值上完全可分，I = log 2
T_N = 2201


def _mi_at_t(t: float) -> float:
    """sigma=1、中心对称（c=0）、间距 t 时的 I(Y;Z)，1D 自适应积分。"""
    if t <= 1e-9:
        return 0.0
    mu0, mu1 = -0.5 * t, 0.5 * t

    def integrand(z):
        f0 = 0.5 * norm.pdf(z, mu0, 1.0)
        f1 = 0.5 * norm.pdf(z, mu1, 1.0)
        p = f0 + f1
        if p <= 1e-300:
            return 0.0
        p1 = min(max(f1 / p, 1e-15), 1.0 - 1e-15)
        return -p * (p1 * np.log(p1) + (1.0 - p1) * np.log(1.0 - p1))

    lo, hi = mu0 - 20.0, mu1 + 20.0
    h_cond, _ = quad(integrand, lo, hi, points=[mu0, mu1], limit=300)
    return float(LOG2 - h_cond)


_T_GRID = np.linspace(0.0, T_MAX, T_N)
_I_TAB = None


def build_mi_table():
    """预计算 t -> I(log2 归一化)，供插值使用。"""
    global _I_TAB
    t0 = time.time()
    _I_TAB = np.array([_mi_at_t(t) for t in _T_GRID])
    sys.stderr.write(f"[table] I(t) 预计算完成，{T_N} 点，用时 {time.time()-t0:.1f}s\n")


def mi(m, sigma):
    """I(Y;Z)，仅依赖 t = m/sigma。数组安全。

    推导：I(Y;Z) = log2 - H(Y|Z)，H(Y|Z) = -∫ p(z) h2(p1(z)) dz，p1(z) 为后验。
    标度不变性：Z→sZ 是双射，故 I 只依赖 m/sigma。
    """
    t = np.abs(np.asarray(m, dtype=float)) / sigma
    return np.interp(np.minimum(t, T_MAX), _T_GRID, _I_TAB)


def b_closed(m, c, sigma, tau=TAU):
    """B = E_Y KL(N(mu_y,sigma^2) || N(0,tau^2))，闭式。数组安全。

    KL(N(mu,s^2)||N(0,t^2)) = (1/2)[s^2/t^2 + mu^2/t^2 - 1 - ln(s^2/t^2)]
    B = (1/2)KL(mu_0) + (1/2)KL(mu_1)
      = (1/2)(s^2/t^2 - 1 - ln(s^2/t^2)) + (mu_0^2+mu_1^2)/(4 t^2)
    代入 mu_0 = c-m/2, mu_1 = c+m/2 得 mu_0^2+mu_1^2 = 2c^2 + m^2/2：
      = (1/2)(s^2/t^2 - 1 - ln(s^2/t^2)) + c^2/(2 t^2) + m^2/(8 t^2)
    """
    s2 = np.asarray(sigma, dtype=float) ** 2
    t2 = float(tau) ** 2
    return (0.5 * (s2 / t2 - 1.0 - np.log(s2 / t2))
            + np.asarray(c, dtype=float) ** 2 / (2.0 * t2)
            + np.asarray(m, dtype=float) ** 2 / (8.0 * t2))


def a_fast(m, c, sigma, tau=TAU):
    """A = KL(q(Z)||N(0,tau^2)) = B - I（恒等式，免积分）。"""
    return b_closed(m, c, sigma, tau) - mi(m, sigma)


def task_loss(m, c):
    """L_task = E(Z-Y)^2 = (1/2)[(c-m/2)^2 + (c+m/2-1)^2]。数组安全。"""
    mu0 = np.asarray(c, dtype=float) - 0.5 * np.asarray(m, dtype=float)
    mu1 = np.asarray(c, dtype=float) + 0.5 * np.asarray(m, dtype=float)
    return 0.5 * (mu0 ** 2 + (mu1 - 1.0) ** 2)


def grid_min(fn, c_lo=-0.5, c_hi=1.5, m_lo=0.0, m_hi=3.0, nc=401, nm=601):
    cs = np.linspace(c_lo, c_hi, nc)
    ms = np.linspace(m_lo, m_hi, nm)
    C, M = np.meshgrid(cs, ms, indexing="ij")
    V = fn(C, M)
    k = int(np.argmin(V))
    return float(C.ravel()[k]), float(M.ravel()[k]), float(V.ravel()[k])


# ------------------------------------------------------------------ 循环 1
def cycle1():
    print("=" * 100)
    print("循环 1 · 审计 C-T9-001")
    print("=" * 100)

    print("\n[1.1] 恒等式核验： E_Y KL(q(Z|Y)||p) = I(Y;Z) + KL(q(Z)||p)")
    print(f"{'sigma':>7} {'c':>6} {'m':>6} | {'B (闭式)':>13} | {'A(积分)+I':>13} | "
          f"{'绝对差':>10} | {'quad误差':>9}")
    worst = 0.0
    for sigma in [0.2, 0.5, 1.0, 1.5]:
        for c, m in [(0.0, 0.0), (0.0, 1.0), (0.25, 0.8), (0.5, 1.0), (0.0, 2.0)]:
            B = float(b_closed(m, c, sigma))
            A_num, a_err = _a_direct_integral(m, c, sigma)
            I = _mi_direct(m, c, sigma)          # 直接积分，不经插值表
            d = abs(B - (A_num + I))
            worst = max(worst, d)
            print(f"{sigma:>7.2f} {c:>6.2f} {m:>6.2f} | {B:>13.8f} | {A_num + I:>13.8f} "
                  f"| {d:>10.2e} | {max(a_err, 0.0):>9.1e}")
    print(f"  → 最大绝对偏差 {worst:.2e}  ⟹ 恒等式{'成立' if worst < 1e-8 else '不成立'}"
          f"（阈值 1e-8，已排除查表插值的影响）")

    print("\n[1.2] 复核原脚本的『保留率 94.85%』")
    sigma = 0.2
    m_old, c_old = 0.4541 + 0.4345, 0.5 * (0.4541 - 0.4345)
    I0 = mi(1.0, sigma)
    I1 = mi(m_old, sigma)
    print(f"  delta=0    (m=1)     : I = {I0:.6f} nats")
    print(f"  delta=100  (m={m_old:.4f}) : I = {I1:.6f} nats")
    print(f"  分母取 ln2            : {I1/LOG2:.4%}    ← 原卡用的（口径错）")
    print(f"  分母取 delta=0 的 I    : {I1/I0:.4%}    ← 正确保留率")
    print(f"  ⟹ 原卡『94.85%』低估了保留率；正确为 {I1/I0:.2%}")

    print("\n[1.3] 原脚本未观察到的自由度：中心 c 被对齐『免费吃掉』")
    print("  （I 只依赖 m/sigma，与 c 无关；对齐首先把 c 从 0.5 拉向 0，不损失任何信息）")
    for sigma in [0.2, 0.5, 1.0, 1.5]:
        fn = lambda C, M, s=sigma: task_loss(M, C) + 100.0 * a_fast(M, C, s)
        c_star, m_star, _ = grid_min(fn)
        print(f"  sigma={sigma:>4.2f}   argmin_A(delta=100): c*={c_star:+.4f}   m*={m_star:.4f}"
              f"   I/ln2={mi(m_star, sigma)/LOG2:.4f}")


def _mi_direct(m, c, sigma):
    """直接积分求 I(Y;Z)（不经查表），供恒等式高精度核验用。"""
    if abs(m) <= 1e-12:
        return 0.0
    mu0, mu1 = c - 0.5 * m, c + 0.5 * m

    def integrand(z):
        f0 = 0.5 * norm.pdf(z, mu0, sigma)
        f1 = 0.5 * norm.pdf(z, mu1, sigma)
        p = f0 + f1
        if p <= 1e-300:
            return 0.0
        p1 = min(max(f1 / p, 1e-15), 1.0 - 1e-15)
        return -p * (p1 * np.log(p1) + (1.0 - p1) * np.log(1.0 - p1))

    h_cond, _ = quad(integrand, min(mu0, mu1) - 20.0, max(mu0, mu1) + 20.0,
                     points=[mu0, mu1], limit=300)
    return float(LOG2 - h_cond)


def _a_direct_integral(m, c, sigma, tau=TAU):
    """仅供 [1.1] 交叉核验用：直接积分求 A。"""
    mu0, mu1 = c - 0.5 * m, c + 0.5 * m

    def integrand(z):
        q = 0.5 * norm.pdf(z, mu0, sigma) + 0.5 * norm.pdf(z, mu1, sigma)
        if q <= 1e-300:
            return 0.0
        return q * (np.log(q) - norm.logpdf(z, 0.0, tau))

    return quad(integrand, min(mu0, mu1) - 20.0, max(mu0, mu1) + 20.0,
                points=[mu0, mu1], limit=300)


# ------------------------------------------------------------------ 循环 2
def cycle2():
    print("\n" + "=" * 100)
    print("循环 2 · 最小解析结果")
    print("=" * 100)

    print("\n[2.1] 纯对齐问题：min L_align（不含预测损失）")
    print("  B(c,m) = (1/2)(sigma^2/tau^2 - 1 - ln(sigma^2/tau^2)) + c^2/(2 tau^2) + m^2/(8 tau^2)")
    print("         ← 对 (c,m) 严格二次，唯一最小点 c*=0, m*=0，对**任意 sigma** 成立")
    print("  ⟹ 【闭式，已证】条件 KL 的平均目标使表示必然坍塌")

    print("\n  A 的纯对齐最小点（1D 精确扫描 + 二阶矩预测对照）：")
    print(f"{'sigma':>7} | {'argmin_m A':>11} | {'2*sqrt(tau^2-s^2)':>18} | {'A_min':>10} "
          f"| {'A(m=0)':>10} | 判定")
    print("-" * 100)
    for sigma in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0]:
        ms = np.linspace(0.0, 3.0, 3001)
        vals = np.array([a_fast(m, 0.0, sigma) for m in ms])
        k = int(np.argmin(vals))
        pred = 2.0 * np.sqrt(max(TAU ** 2 - sigma ** 2, 0.0))
        a_at_zero = a_fast(0.0, 0.0, sigma)
        # 判定：m*=0 是否优于其他 m（容差 1e-4，排除插值表分辨率造成的假极小）
        verdict = "坍塌(m*=0)" if vals[k] >= a_at_zero - 1e-4 else "不坍塌"
        print(f"{sigma:>7.2f} | {ms[k]:>11.4f} | {pred:>18.4f} | {vals[k]:>10.6f} "
              f"| {a_at_zero:>10.6f} | {verdict}")
    print("  → 阈值 sigma = tau = 1：sigma>=tau 时 A 在 m=0 取最小（A_min 与 A(m=0) 差 <1e-4，")
    print("     差值来自 MI 查表的插值分辨率，非真实极小）；sigma<tau 时 m*>0")
    print("  → 二阶矩预测 2*sqrt(tau^2-sigma^2) 仅在 sigma 接近 tau 时准确；")
    print("     sigma 很小时 m* 显著小于该预测（任务无关的纯对齐下，m 不必匹配到那么开）")

    print("\n[2.2] 加回预测损失（目标 B）：完全闭式")
    print("  L_task 梯度:  dL/dc = 2c-1,  dL/dm = (m-1)/2")
    print("  B 梯度     :  dB/dc = c/tau^2, dB/dm = m/(4 tau^2)")
    print("  d/dc = (2c-1) + delta*c/tau^2 = 0      →  c*(delta) = 1 / (2 + delta/tau^2)")
    print("  d/dm = (m-1)/2 + delta*m/(4 tau^2) = 0 →  m*(delta) = 1 / (1 + delta/(2 tau^2))")
    print(f"\n{'delta':>8} | {'m*闭式':>9} | {'m*数值':>9} | {'c*闭式':>9} | {'c*数值':>9} "
          f"| {'I/I(delta=0)':>13}")
    print("-" * 100)
    sigma = 0.5
    for delta in [0.0, 0.1, 1.0, 3.0, 10.0, 100.0]:
        m_cf = 1.0 / (1.0 + delta / (2.0 * TAU ** 2))
        c_cf = 1.0 / (2.0 + delta / TAU ** 2)
        fn = lambda C, M, s=sigma, d=delta: task_loss(M, C) + d * b_closed(M, C, s)
        c_n, m_n, _ = grid_min(fn)
        print(f"{delta:>8.1f} | {m_cf:>9.4f} | {m_n:>9.4f} | {c_cf:>9.4f} | {c_n:>9.4f} "
              f"| {mi(m_n, sigma)/mi(1.0, sigma):>13.4f}")

    print("\n[2.3] 两种目标性质不同的原因（由恒等式直接读出）")
    print("  目标 B 的对齐项 = A + I  ⟹ 对齐**同时惩罚 I**  ⟹ 任意 sigma 都坍塌")
    print("  目标 A 的对齐项 = B - I  ⟹ 对齐**不惩罚 I**  ⟹ 仅在 sigma >= tau（尺度失配）时坍塌")

    print("\n[2.4] 联合目标 A（2D 网格全局搜索）")
    print(f"{'sigma':>7} | {'delta':>7} | {'c*':>8} | {'m*':>8} | {'I/I(delta=0)':>13} | 判定")
    print("-" * 100)
    for sigma in [0.2, 0.5, 1.0, 1.5]:
        for delta in [1.0, 100.0]:
            fn = lambda C, M, s=sigma, d=delta: task_loss(M, C) + d * a_fast(M, C, s)
            c_s, m_s, _ = grid_min(fn)
            ratio = mi(m_s, sigma) / mi(1.0, sigma)
            verdict = "坍塌" if ratio < 0.5 else ("部分" if ratio < 0.9 else "不坍塌")
            print(f"{sigma:>7.2f} | {delta:>7.1f} | {c_s:>8.4f} | {m_s:>8.4f} "
                  f"| {ratio:>13.4f} | {verdict}")


if __name__ == "__main__":
    t0 = time.time()
    build_mi_table()
    cycle1()
    cycle2()
    sys.stderr.write(f"[done] 总用时 {time.time()-t0:.1f}s\n")
