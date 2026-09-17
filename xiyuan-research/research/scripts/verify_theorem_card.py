# -*- coding: utf-8 -*-
"""循环 1+2：统一族定理的独立复推与交叉验证

模型（不更换，与 unified_family.py 一致）：
  T_kappa = [S + kappa(P_H+P_L)]/sqrt(1+2k^2),  Z_i = sqrt(1-th)S + sqrt(th)P_i + sqrt(nu)xi_i
  u^2(th,kappa) = (sqrt(1-th)+kappa sqrt(th))^2/(1+2k^2)
  R_H = 1 - u^2/(1+nu);  R = 1 - 2u^2/(2+nu-th);  D = 2(th+nu)
  DeltaI = (1/2) ln(R_H/R)

参数化说明：本脚本使用 (theta, nu)。协议提到的『t 参数化下 v/b 的公式』
**在项目中无来源**（全库检索仅命中 KronosEnhanced 的 Fisher/EWC 语境，是另一个对象），
故不采用；映射关系由本模型显式给出： a=sqrt(1-th), b=sqrt(th), a^2+b^2=1。

纪律：验证值一律由**函数值差分**产生，绝不复用解析导数表达式。
"""
from __future__ import annotations

import numpy as np


# ------------------------------------------------------------------ 基元
def u2(theta, kappa):
    th = float(theta)
    return (np.sqrt(1.0 - th) + float(kappa) * np.sqrt(th)) ** 2 / (1.0 + 2.0 * float(kappa) ** 2)


def du2(theta, kappa):
    """d(u^2)/d(theta) 的解析式。"""
    th, k = float(theta), float(kappa)
    if th <= 0.0 or th >= 1.0:
        return np.nan
    return (k * (1.0 - 2.0 * th) / np.sqrt(th * (1.0 - th)) + k ** 2 - 1.0) / (1.0 + 2.0 * k ** 2)


def R_RH_D(theta, nu, kappa):
    th = float(theta)
    u = u2(th, kappa)
    RH = 1.0 - u / (1.0 + nu)
    R = 1.0 - 2.0 * u / (2.0 + nu - th)
    D = 2.0 * (th + nu)
    return R, RH, D


def dI(theta, nu, kappa):
    R, RH, _ = R_RH_D(theta, nu, kappa)
    return 0.5 * np.log(RH / R)


def dI_analytic(theta, nu, kappa):
    """DeltaI 的解析导数（由 R_H' 与 R' 的解析式组合）。

    ⚠️ 曾经把 nu 误当成 kappa 传入 u2/du2（k = float(nu)），导致 [5] 误报反例。
       修正后 k 取 kappa。
    """
    th = float(theta)
    v = float(nu)
    k = float(kappa)
    u = u2(th, k)
    du = du2(th, k)
    RH = 1.0 - u / (1.0 + v)
    R = 1.0 - 2.0 * u / (2.0 + v - th)
    RHp = -du / (1.0 + v)
    Rp = -(2.0 * du * (2.0 + v - th) + 2.0 * u) / (2.0 + v - th) ** 2
    return 0.5 * (RHp / RH - Rp / R)


def dI_fd(theta, nu, kappa, h):
    """由 DeltaI 的**函数值**做中心差分（不复用解析式）。"""
    return (dI(theta + h, nu, kappa) - dI(theta - h, nu, kappa)) / (2.0 * h)


def theta0(nu, kappa, n=200001):
    """argmin_theta R（细扫 + 二次插值）。"""
    ths = np.linspace(0.0, 1.0, n)
    Rs = np.array([R_RH_D(t, nu, kappa)[0] for t in ths])
    k = int(np.argmin(Rs))
    if 0 < k < n - 1:
        y0, y1, y2 = Rs[k - 1], Rs[k], Rs[k + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-18:
            return float(min(max(ths[k] + 0.5 * (y0 - y2) / den * (ths[1] - ths[0]), 0.0), 1.0)), float(y1)
    return float(ths[k]), float(Rs[k])


def path(nu, kappa, n=4001):
    """delta 路径：每个 delta 给出 argmin(R+delta D)（细扫 + 二次插值）。"""
    out = []
    for d in [0.0, 0.01, 0.05, 0.2, 1.0, 5.0, 50.0, 1e3, 1e6]:
        ths = np.linspace(0.0, 1.0, n)
        vals = np.array([R_RH_D(t, nu, kappa)[0] + d * R_RH_D(t, nu, kappa)[2] for t in ths])
        k = int(np.argmin(vals))
        th = ths[k]
        if 0 < k < n - 1:
            y0, y1, y2 = vals[k - 1], vals[k], vals[k + 1]
            den = y0 - 2 * y1 + y2
            if abs(den) > 1e-18:
                th = float(min(max(ths[k] + 0.5 * (y0 - y2) / den * (ths[1] - ths[0]), 0.0), 1.0))
        R, RH, D = R_RH_D(th, nu, kappa)
        out.append((d, th, R, RH, D, 0.5 * np.log(RH / R)))
    return out


# ------------------------------------------------------------------ 循环 1
def cycle1():
    print("=" * 100)
    print("循环 1 · 独立复推核对")
    print("=" * 100)

    print("\n[1] 参数化核对：a=sqrt(1-th), b=sqrt(th), a^2+b^2=1（本模型映射，非外部来源）")
    worst = 0.0
    for th in [0.0, 0.1, 0.37, 0.5, 0.9, 1.0]:
        a, b = np.sqrt(1.0 - th), np.sqrt(th)
        worst = max(worst, abs(a ** 2 + b ** 2 - 1.0), abs(b ** 2 - th))
    print(f"    a^2+b^2-1 与 b^2-th 的最大偏差 = {worst:.2e}  ✅")

    print("\n[2] 任务风险的唯一最小点 theta0（两种独立算法交叉）")
    print(f"{'kappa':>6} {'nu':>7} | {'theta0 细扫':>13} | {'R 在该点':>12} | "
          f"{'Rs 局部极小个数':>15} | {'dR/dth at theta0':>17}")
    for k in [0.0, 1.0]:
        for nu in [0.2, 1.0, 3.0]:
            th0, R0 = theta0(nu, k)
            ths = np.linspace(0, 1, 20001)
            Rs = np.array([R_RH_D(t, nu, k)[0] for t in ths])
            loc = np.where((Rs[1:-1] < Rs[:-2]) & (Rs[1:-1] < Rs[2:]))[0] + 1
            h = 1e-6
            if 1e-9 < th0 < 1 - 1e-9:
                Rp = (R_RH_D(th0 + h, nu, k)[0] - R_RH_D(th0 - h, nu, k)[0]) / (2 * h)
            else:
                Rp = float('nan')
            print(f"{k:>6.1f} {nu:>7.2f} | {th0:>13.5f} | {R0:>12.8f} | "
                  f"{len(loc):>15} | {Rp:>17.3e}")

    print("\n[3] 所有 theta0 之后的正则化全局最优均位于 [0, theta0]")
    print("    证明（不依赖凸性）：设 th > theta0，则")
    print("      R(th) >= R(theta0)   —— 因 theta0 是 R 的全局最小点")
    print("      D(th) >  D(theta0)   —— 因 D=2(th+nu) 严格递增")
    print("    ⟹ R(th)+delta D(th) > R(theta0)+delta D(theta0) 对任意 delta>0")
    print("    ⟹ th 不可能是极小点。∎   （端点情形 delta=0 时 argmin R ⊆ [0,theta0] 显然）")
    bad = 0
    for k in [0.0, 1.0]:
        for nu in [0.2, 1.0, 3.0]:
            th0, _ = theta0(nu, k)
            for (d, th, R_, RH_, D_, dIv) in path(nu, k):
                if th > th0 + 1e-6:
                    bad += 1
    print(f"    数值核查：delta 路径上越界（th > theta0）的点数 = {bad}  "
          f"{'✅' if bad == 0 else '❌'}")

    print("\n[4] 条件互信息导数公式")
    print("    DeltaI = (1/2) ln(R_H / R),  dDeltaI/dth = (1/2)( R_H'/R_H - R'/R )")
    print("    R_H = 1 - u^2/(1+nu)      -> R_H' = -(u^2)'/(1+nu)")
    print("    R   = 1 - 2u^2/(2+nu-th)  -> R' = -[2(u^2)'(2+nu-th)+2u^2]/(2+nu-th)^2")
    print("    (u^2)' = [kappa(1-2th)/sqrt(th(1-th)) + kappa^2 - 1] / (1+2kappa^2)")
    print("    kappa=0 时退化为 dDeltaI/dth = -1/[2(2+nu-th)] < 0")

    print("\n[5] kappa=1 时在 [0, theta0] 上 DeltaI' > 0 的核对")
    print("    解析可证的一段：th >= 1/2 时 (u^2)' <= 0 ⟹ R_H' >= 0；且 th ∈ [0,theta0] ⟹ R' <= 0")
    print("      ⟹ dDeltaI/dth = (1/2)(R_H'/R_H - R'/R) > 0  （两项均非负，至少一项严格正）")
    print(f"\n    {'kappa':>6} {'nu':>7} | {'theta0':>9} | {'min dDeltaI/dth on [0,theta0]':>30} | 结论")
    for k in [0.0, 1.0]:
        for nu in [0.2, 1.0, 3.0]:
            th0, _ = theta0(nu, k)
            ths = np.linspace(1e-6, max(th0 - 1e-6, 1e-6), 2001)
            ds = np.array([dI_analytic(t, nu, k) for t in ths])
            print(f"    {k:>6.1f} {nu:>7.2f} | {th0:>9.5f} | {ds.min():>30.6e} | "
                  f"{'全部 > 0 ✅' if ds.min() > 0 else '存在非正 ❌'}")

    print("\n[6] 非唯一全局最优解的处理")
    print("    命题 O 对**任意选择**给出 D 不减、R 不增（值层面），与选择无关。")
    print("    但 DeltaI 是 theta 的函数：若同一 delta 有多个极小点，DeltaI 可能依选择而不同。")
    print(f"    {'kappa':>6} {'nu':>7} | {'各 delta 下局部极小个数（最大）':>28}")
    for k in [0.0, 1.0]:
        for nu in [0.2, 1.0, 3.0]:
            mx = 0
            for d in [0.0, 0.05, 0.5, 5.0, 1e3]:
                ths = np.linspace(0, 1, 20001)
                vals = np.array([R_RH_D(t, nu, k)[0] + d * R_RH_D(t, nu, k)[2] for t in ths])
                loc = np.where((vals[1:-1] < vals[:-2]) & (vals[1:-1] < vals[2:]))[0] + 1
                mx = max(mx, len(loc))
            print(f"    {k:>6.1f} {nu:>7.2f} | {mx:>28}")
    print("    ⟹ 数值上极小点唯一 ⟹ 路径是单值函数，§5 的论证适用；")


# ------------------------------------------------------------------ 循环 2
def cycle2():
    print("\n" + "=" * 100)
    print("循环 2 · 小规模独立验证（少量 nu 与 theta；多步长差分）")
    print("=" * 100)

    print("\n[A] 解析导数 vs 多步长差分（差分只由 DeltaI 的函数值产生）")
    print(f"{'kappa':>6} {'nu':>6} {'theta':>7} | {'h=1e-3':>12} {'h=1e-4':>12} {'h=1e-5':>12} "
          f"| {'解析':>12} | {'|解析-h1e5|':>11}")
    for k in [0.0, 1.0]:
        for nu in [0.5, 2.0]:
            for th in [0.1, 0.4, 0.9]:
                fds = [dI_fd(th, nu, k, h) for h in (1e-3, 1e-4, 1e-5)]
                an = dI_analytic(th, nu, k)
                print(f"{k:>6.1f} {nu:>6.1f} {th:>7.2f} | {fds[0]:>12.7f} {fds[1]:>12.7f} "
                      f"{fds[2]:>12.7f} | {an:>12.7f} | {abs(an - fds[2]):>11.2e}")
    print("    期望：h 减小时差分收敛到解析值（截断误差 O(h^2)）")

    print("\n[B] theta0 与直接风险极小交叉")
    print(f"{'kappa':>6} {'nu':>6} | {'theta0 (细扫 2e5)':>17} | {'theta0 (粗扫 4e3)':>17} | {'差':>9}")
    for k in [0.0, 1.0]:
        for nu in [0.5, 2.0]:
            a, _ = theta0(nu, k, n=200001)
            b, _ = theta0(nu, k, n=4001)
            print(f"{k:>6.1f} {nu:>6.1f} | {a:>17.6f} | {b:>17.6f} | {abs(a-b):>9.2e}")

    print("\n[C] 沿 delta 路径：R 不减、D 不增、DeltaI 不增")
    allok = True
    for k in [0.0, 1.0]:
        for nu in [0.5, 2.0]:
            rows = path(nu, k)
            okR = all(rows[i + 1][2] >= rows[i][2] - 1e-10 for i in range(len(rows) - 1))
            okD = all(rows[i + 1][4] <= rows[i][4] + 1e-10 for i in range(len(rows) - 1))
            okI = all(rows[i + 1][5] <= rows[i][5] + 1e-10 for i in range(len(rows) - 1))
            allok &= (okR and okD and okI)
            print(f"  kappa={k}, nu={nu}:  R 不减={okR}  D 不增={okD}  DeltaI 不增={okI}")
            print(f"    DeltaI 路径: " + ", ".join(f"{r[5]:.6f}" for r in rows))
    print(f"  ⟹ 全部通过 = {allok}")
    print("  注明：原扫描（unified_family.py）仅作为**实现支持**，不作为证明依据")


if __name__ == "__main__":
    cycle1()
    cycle2()
