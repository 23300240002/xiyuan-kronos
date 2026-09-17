# -*- coding: utf-8 -*-
"""循环 2+3：统一高斯族（T_kappa + 固定表示机制）

禁止为匹配预期关系更换模型。本脚本的模型由**结构**定义，不由任何待验证关系定义：

  S, P_H, P_L, xi_H, xi_L  iid  N(0,1)
  T_kappa = [S + kappa (P_H + P_L)] / sqrt(1 + 2 kappa^2)     目标（Var = 1）
  Z_H = sqrt(1-theta) S + sqrt(theta) P_H + sqrt(nu) xi_H      表示（固定机制）
  Z_L = sqrt(1-theta) S + sqrt(theta) P_L + sqrt(nu) xi_L

  kappa = 0 → 控制组（私有成分与目标无关）
  kappa = 1 → 目标相关模型（私有成分进目标）

全部量由协方差矩阵闭式给出，不使用积分、不使用蒙特卡洛、不做网格搜索。
"""
from __future__ import annotations

import numpy as np


def quantities(theta, nu, kappa):
    """由协方差矩阵闭式给出全部量。"""
    th, v, k = float(theta), float(nu), float(kappa)
    # 目标与表示：T_kappa 与 Z_i
    u = (np.sqrt(1.0 - th) + k * np.sqrt(th)) / np.sqrt(1.0 + 2.0 * k ** 2)   # Cov(T,Z_i)
    v1 = 1.0 + v                       # Var(Z_i)
    c12 = 1.0 - th                     # Cov(Z_H, Z_L)

    D = 2.0 * (th + v)
    R_H = 1.0 - u ** 2 / v1
    R = 1.0 - 2.0 * u ** 2 / (2.0 + v - th)

    I_single = -0.5 * np.log(R_H)
    I_joint = -0.5 * np.log(R)
    dI = I_joint - I_single            # == 0.5 * log(R_H / R)
    return dict(theta=th, nu=v, kappa=k, u=u, v1=v1, c12=c12,
                D=D, R=R, R_H=R_H, I_single=I_single, I_joint=I_joint, dI=dI)


def d_dI_dtheta(theta, nu, kappa, h=1e-6):
    """Delta I 对 theta 的中心差分（供核验解析式用）。"""
    a = quantities(theta + h, nu, kappa)["dI"]
    b = quantities(theta - h, nu, kappa)["dI"]
    return (a - b) / (2 * h)


def cov3(theta, nu, kappa):
    """(T_kappa, Z_H, Z_L) 的 3x3 协方差矩阵。"""
    q = quantities(theta, nu, kappa)
    return np.array([
        [1.0, q["u"], q["u"]],
        [q["u"], q["v1"], q["c12"]],
        [q["u"], q["c12"], q["v1"]],
    ])


def theta_star(delta, nu, kappa, n=2001):
    """argmin_theta [ R + delta D ]，粗扫 + 有界标量极小（全闭式，无积分）。"""
    ths = np.linspace(0.0, 1.0, n)
    vals = np.array([quantities(t, nu, kappa)["R"] + delta * quantities(t, nu, kappa)["D"]
                     for t in ths])
    k = int(np.argmin(vals))
    lo, hi = ths[max(k - 1, 0)], ths[min(k + 1, n - 1)]
    # 二次插值精化（R+delta D 在局部光滑）
    if 0 < k < n - 1:
        y0, y1, y2 = vals[k - 1], vals[k], vals[k + 1]
        denom = (y0 - 2 * y1 + y2)
        if abs(denom) > 1e-18:
            shift = 0.5 * (y0 - y2) / denom
            return float(min(max(ths[k] + shift * (ths[1] - ths[0]), 0.0), 1.0)), float(y1)
    return float(ths[k]), float(vals[k])


# ------------------------------------------------------------------ 主流程
def main():
    print("=" * 100)
    print("循环 2 · 统一高斯族：闭式推导与交叉核验")
    print("=" * 100)
    print("  T_kappa = [S + kappa(P_H+P_L)]/sqrt(1+2k^2)；Z_i = sqrt(1-th)S + sqrt(th)P_i + sqrt(nu)xi_i")
    print("  u := Cov(T,Z_i) = [sqrt(1-th) + kappa sqrt(th)] / sqrt(1+2 kappa^2)")
    print("  R_H = 1 - u^2/(1+nu)；R = 1 - 2u^2/(2+nu-th)；D = 2(th+nu)")
    print("  Delta I = (1/2) ln(R_H / R)")

    # [2.1] 闭式 vs 2x2 线性求解（交叉核验）
    print("\n[2.1] 标量闭式 vs 协方差线性求解（2x2 求逆）")
    print(f"{'kappa':>6} {'nu':>6} {'theta':>7} | {'R 闭式':>12} | {'R 线性求解':>12} | "
          f"{'R_H 闭式':>11} | {'R_H 定义':>11} | 最大差")
    worst = 0.0
    for k in [0.0, 0.5, 1.0]:
        for v in [0.1, 1.0, 3.0]:
            for th in [0.0, 0.3, 0.7, 1.0]:
                q = quantities(th, v, k)
                SZ = np.array([[q["v1"], q["c12"]], [q["c12"], q["v1"]]])
                cv = np.array([q["u"], q["u"]])
                R_lin = 1.0 - float(cv @ np.linalg.solve(SZ, cv))
                d = max(abs(R_lin - q["R"]), abs((1 - q["u"] ** 2 / q["v1"]) - q["R_H"]))
                worst = max(worst, d)
    print(f"  全部 (kappa,nu,theta) 组合上的最大差 = {worst:.2e}")

    # [2.2] kappa=0 时退化为 C-CM-002 的控制模型
    print("\n[2.2] kappa=0 是否复现控制模型（C-CM-002）")
    ok = True
    for v in [0.25, 1.0, 4.0]:
        for th in [0.0, 0.5, 1.0]:
            q = quantities(th, v, 0.0)
            R_cf = (v + th) / (2 + v - th)
            RH_cf = (v + th) / (1 + v)
            dI_cf = 0.5 * np.log((2 + v - th) / (1 + v))
            good = (abs(q["R"] - R_cf) < 1e-12 and abs(q["R_H"] - RH_cf) < 1e-12
                    and abs(q["dI"] - dI_cf) < 1e-12)
            ok &= good
    print(f"  kappa=0 复现 R=(nu+th)/(2+nu-th)、R_H=(nu+th)/(1+nu)、"
          f"dI=0.5ln[(2+nu-th)/(1+nu)]：{'PASS' if ok else 'FAIL'}")

    # [2.3] 正观测噪声下的有限性界
    print("\n[2.3] 正观测噪声下的有限性界：R_min(nu) = min_theta R")
    print(f"{'nu':>7} | {'R_min(nu)':>12} | {'argmin theta':>13} | {'1/R_min':>10} | "
          f"{'dI 上界 = 0.5 ln(R_Hmax/R_min)':>28}")
    for v in [0.01, 0.05, 0.2, 1.0, 5.0]:
        ths = np.linspace(0, 1, 4001)
        Rs = np.array([quantities(t, v, 1.0)["R"] for t in ths])
        Rmin = float(Rs.min())
        RHmax = float(max(quantities(t, v, 1.0)["R_H"] for t in ths))
        print(f"{v:>7.2f} | {Rmin:>12.8f} | {ths[int(np.argmin(Rs))]:>13.4f} | "
              f"{1/Rmin:>10.3e} | {0.5*np.log(RHmax/Rmin):>28.6f}")
    print("  ⟹ nu>0 时 R_min(nu)>0，Delta I 有限；nu→0+ 时 R_min→0，Delta I→∞（无噪声退化）")

    # [2.4] 完整 3x3 协方差 + 半正定 + 族归属（循环 1 第 6 项）
    print("\n[2.4] 完整 3x3 协方差矩阵、半正定性与族归属")
    cases = [("族内 kappa=0 th=0.5 nu=1", 0.5, 1.0, 0.0),
             ("族内 kappa=1 th=0.5 nu=1", 0.5, 1.0, 1.0)]
    for name, th, v, k in cases:
        M = cov3(th, v, k)
        ev = np.linalg.eigvalsh(M)
        print(f"  [{name}]")
        print(f"    [[1, u, u], [u, 1+nu, 1-th], [u, 1-th, 1+nu]]  u={quantities(th,v,k)['u']:.6f}")
        print(f"    特征值 = {np.round(ev, 8)}  半正定 = {bool(ev.min() > -1e-10)}")
    # T5 的两个用例（来自 C-CM-002）
    print("  [T5 用例 A] Var(Z)=2, Cov(T,Z)=1, Cov(ZH,ZL)=1")
    MA = np.array([[1.0, 1.0, 1.0], [1.0, 2.0, 1.0], [1.0, 1.0, 2.0]])
    evA = np.linalg.eigvalsh(MA)
    print(f"    特征值 = {np.round(evA, 8)}  半正定 = {bool(evA.min() > -1e-10)}")
    print(f"    族归属：Cov(T,Z)^2 = 1 与 Cov(ZH,ZL) = 1 一致，且 Var(Z)=1+nu=2 ⟹ nu=1，")
    print(f"            Cov(ZH,ZL)=1-th=1 ⟹ th=0 ⟹ **属本族**（kappa 由 u=1 反推需 u<=1；u=1 对应 th=0）")
    print("  [T5 用例 B] Var(Z)=2, Cov(T,Z)=1, Cov(ZH,ZL)=0")
    MB = np.array([[1.0, 1.0, 1.0], [1.0, 2.0, 0.0], [1.0, 0.0, 2.0]])
    evB = np.linalg.eigvalsh(MB)
    print(f"    特征值 = {np.round(evB, 8)}  半正定 = {bool(evB.min() > -1e-10)}"
          f"（最小特征值 0 ⟹ 奇异但半正定）")
    print("    族归属：Cov(T,Z)^2 = 1 但 Cov(ZH,ZL) = 0 ⟹ 1 != 0 ⟹ **不属本族**")
    print("            （B 是『两路看的是相互独立的两个目标副本』，与本族的共享结构不同）")

    # [2.5] T=S 的联合风险（循环 1 第 2 项）
    print("\n[2.5] T=S（目标只含共享成分）时的联合风险")
    print("  Z_H = aS+bP_H, Z_L = aS+bP_L, a^2+b^2=1, th=b^2")
    print("  Cov(S,Z_i)=a, Var(Z_i)=1, Cov(ZH,ZL)=a^2")
    print("  ⟹ c'Sigma^{-1}c = 2a^2/(1+a^2) ⟹ R = (1-a^2)/(1+a^2) = th/(2-th)")
    print(f"{'theta':>7} | {'R 闭式 th/(2-th)':>18} | {'R 线性求解':>12} | {'R_H = th':>10} | {'D = 2th':>8}")
    for th in [0.0, 0.25, 0.5, 0.75, 1.0]:
        a2 = 1 - th
        R_cf = th / (2 - th)
        SZ = np.array([[1.0, a2], [a2, 1.0]])
        cv = np.array([np.sqrt(a2), np.sqrt(a2)])
        # theta=0 时 a^2=1 ⟹ SZ 奇异（Z_H=Z_L），用伪逆；伪逆给出的解释方差恰为 1，R=0
        R_lin = 1 - float(cv @ np.linalg.pinv(SZ) @ cv)
        print(f"{th:>7.2f} | {R_cf:>18.8f} | {R_lin:>12.8f} | {th:>10.4f} | {2*th:>8.4f}")
    print("  ⟹ 原表述『R_joint = 0』错误；正确为 th/(2-th)。三者随 theta 同增 ⟹ theta*=0 的结论不变")


def cycle3():
    print("\n" + "=" * 100)
    print("循环 3 · 未决命题： Delta I 沿 delta 路径是否不增")
    print("=" * 100)
    print("  Delta I(theta) = (1/2) ln[ R_H(theta) / R(theta) ]；theta_delta ∈ argmin [R + delta D]")

    # [3.1] kappa=0 的解析导数（应恒为负）
    print("\n[3.1] kappa=0 的解析导数")
    print("  R_H = (nu+th)/(1+nu), R = (nu+th)/(2+nu-th)")
    print("  dDeltaI/dth = (1/2)[ R_H'/R_H - R'/R ]")
    print("              = (1/2)[ 1/(nu+th) - 2(1+nu)/((2+nu-th)(nu+th)) ]")
    print("              = -1 / [ 2(2+nu-th) ]   < 0   恒成立")
    worst = 0.0
    for v in [0.1, 1.0, 3.0]:
        for th in [0.0, 0.25, 0.6, 0.9]:
            an = -1.0 / (2.0 * (2 + v - th))
            nu_ = d_dI_dtheta(th, v, 0.0)
            worst = max(worst, abs(an - nu_))
    print(f"  解析式 vs 中心差分（12 组）最大偏差 = {worst:.2e}")
    print("  且 kappa=0 时 R 与 D 都随 theta 严格增 ⟹ theta_delta ≡ 0 ⟹ DeltaI 恒定")
    print("  ⟹ 【kappa=0：命题成立，且以『恒定』的退化形式成立】")

    # [3.2] kappa=1 的 delta 路径
    print("\n[3.2] kappa=1 的 delta 路径：theta_delta、R、R_H、DeltaI")
    for v in [0.2, 1.0, 3.0]:
        print(f"\n  nu = {v}")
        print(f"  {'delta':>9} | {'theta*':>9} | {'R':>9} | {'R_H':>9} | {'DeltaI':>10} "
              f"| {'单调':>6}")
        prev = None
        mono = True
        rows = []
        for d in [0.0, 0.05, 0.2, 0.5, 1.0, 2.0, 5.0, 20.0, 100.0, 1000.0]:
            th, _ = theta_star(d, v, 1.0)
            q = quantities(th, v, 1.0)
            rows.append((d, th, q["R"], q["R_H"], q["dI"]))
        for i, (d, th, R, RH, dI) in enumerate(rows):
            flag = ""
            if prev is not None and dI > prev + 1e-12:
                flag = "↑ 反例"
                mono = False
            prev = dI
            print(f"  {d:>9.2f} | {th:>9.5f} | {R:>9.6f} | {RH:>9.6f} | {dI:>10.6f} "
                  f"| {flag:>6}")
        print(f"  ⟹ nu={v}: DeltaI 沿 delta 路径单调不增 = {mono}")
        # theta* 单调性
        ths = [r[1] for r in rows]
        print(f"     theta* 单调不增 = {all(ths[i+1] <= ths[i] + 1e-12 for i in range(len(ths)-1))}")

    # [3.3] 扫描 nu 找非单调区间
    print("\n[3.3] 扫描 nu，找 DeltaI 沿 delta 路径的非单调区间")
    print(f"{'nu':>7} | {'theta*(0)':>10} | {'DeltaI(0)':>11} | {'DeltaI(inf)':>12} | "
          f"{'非单调?':>9}")
    found = []
    for v in [0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]:
        dls = [0.0, 0.02, 0.1, 0.3, 1.0, 3.0, 10.0, 100.0, 1e4]
        ys = []
        for d in dls:
            th, _ = theta_star(d, v, 1.0)
            ys.append(quantities(th, v, 1.0)["dI"])
        th0, _ = theta_star(0.0, v, 1.0)
        bad = any(ys[i + 1] > ys[i] + 1e-12 for i in range(len(ys) - 1))
        if bad:
            found.append(v)
        print(f"{v:>7.2f} | {th0:>10.5f} | {ys[0]:>11.6f} | {ys[-1]:>12.6f} | "
              f"{str(bad):>9}")
    print(f"  ⟹ 找到非单调的 nu: {found if found else '（无）'}")


if __name__ == "__main__":
    main()
    cycle3()
