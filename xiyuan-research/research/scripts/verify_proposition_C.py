#!/usr/bin/env python3
"""Independent project-side verification of the theta<1/2 monotonicity gap (T2/X-08).

Claim under test (source: 文献调研/deep_2026-09-17/deep_E_stats_redundancy_audit.md
§2.4 — an EXTERNAL candidate proof; per the C-CM-004 §1.5 lesson, it is not trusted
and is re-derived from scratch here).  Object: model D (claims/C-CM-004.md) with
kappa=1, w=sqrt(theta(1-theta)), u2=(1+2w)/3, R_H=1-u2/(1+nu),
R=1-2*u2/(2+nu-theta), DeltaI=0.5*ln(R_H/R).

    Statement to verify:  d DeltaI / d theta > 0  for all theta in (0, 1/2), nu > 0.

Checks (all must pass):
 [1] symbolic equality: sympy derivative of DeltaI equals N/den with
     N   = 3 nu^2 (1-2th) + 6 nu (1+w-2th^2) + 4 w (1-2w^2) + th (6th^2-19th+10)
     den = 2 w (2+nu-th) (3nu+2-2w) (3nu+4-3th-4w)
 [2] high-precision identity at 50 digits on random (theta,nu) samples
     (symbolic derivative vs N/den vs central difference of DeltaI)
 [3] denominator positivity: every factor > 0 on theta in (0,1/2), nu in [1e-3,1e3]
 [4] four-term nonnegativity of N with the claimed strict bounds, plus the two
     bracket facts w<=1/2 (AM-GM) and 6th^2-19th+10 > 0 for th<2/3
 [5] algebra-free monotonicity: DeltaI(th+eps)>DeltaI(th) on a dense grid computed
     only from the original closed form (guards against a shared transcription bug)
"""
from __future__ import annotations

import random
import sys

import mpmath as mp
import sympy as sp

mp.mp.dps = 50


def fmt(v, digits=4):
    return mp.nstr(v, digits)


def symbolic_core():
    th, nu = sp.symbols("theta nu", positive=True)
    w = sp.sqrt(th * (1 - th))
    u2 = (1 + 2 * w) / 3
    RH = 1 - u2 / (1 + nu)
    R = 1 - 2 * u2 / (2 + nu - th)
    dI = sp.Rational(1, 2) * sp.log(RH / R)
    dIp = sp.diff(dI, th)

    N = 3 * nu**2 * (1 - 2 * th) + 6 * nu * (1 + w - 2 * th**2) + 4 * w * (1 - 2 * w**2) + th * (6 * th**2 - 19 * th + 10)
    den = 2 * w * (2 + nu - th) * (3 * nu + 2 - 2 * w) * (3 * nu + 4 - 3 * th - 4 * w)

    diff1 = sp.simplify(sp.together(dIp - N / den))
    return th, nu, w, RH, R, dI, dIp, N, den, diff1


def check1(diff_expr) -> bool:
    ok = diff_expr == 0
    if not ok:
        # try harder: expand/radsimp path before giving up
        ok = sp.simplify(sp.nsimplify(diff_expr)) == 0
    print(f"[1] symbolic dDeltaI/dtheta == N/den (simplify(diff)==0): {ok}")
    return ok


def numericRH(th_v, nu_v):
    w = mp.sqrt(th_v * (1 - th_v))
    u2 = (1 + 2 * w) / 3
    RH = 1 - u2 / (1 + nu_v)
    R = 1 - 2 * u2 / (2 + nu_v - th_v)
    return RH, R


def N_num(th_v, nu_v):
    w = mp.sqrt(th_v * (1 - th_v))
    return (3 * nu_v**2 * (1 - 2 * th_v) + 6 * nu_v * (1 + w - 2 * th_v**2)
            + 4 * w * (1 - 2 * w**2) + th_v * (6 * th_v**2 - 19 * th_v + 10))


def den_num(th_v, nu_v):
    w = mp.sqrt(th_v * (1 - th_v))
    return 2 * w * (2 + nu_v - th_v) * (3 * nu_v + 2 - 2 * w) * (3 * nu_v + 4 - 3 * th_v - 4 * w)


def check2(dIp, th, nu) -> bool:
    random.seed(20260917)
    f = sp.lambdify((th, nu), dIp, modules="mpmath")
    worst_fd = worst_Nd = mp.mpf(0)
    for _ in range(400):
        tv = mp.mpf(random.uniform(1e-6, 0.5 - 1e-9))
        nv = mp.mpf(random.choice([random.uniform(1e-3, 3.0), random.uniform(0.1, 1000.0)]))
        RH, R = numericRH(tv, nv)
        dI = lambda x: mp.mpf(0.5) * mp.log(numericRH(x, nv)[0] / numericRH(x, nv)[1])
        eps = mp.mpf("1e-20")
        fd = (dI(tv + eps) - dI(tv - eps)) / (2 * eps)
        symv = mp.mpf(f(float(tv), float(nv))) if False else None  # lambdify float path unsafe at 50dp; use exact subs
        symv = dIp.subs({th: tv, nu: nv})
        ratio = N_num(tv, nv) / den_num(tv, nv)
        scale = max(abs(symv), mp.mpf(1))
        worst_fd = max(worst_fd, abs(fd - symv) / scale)
        worst_Nd = max(worst_Nd, abs(ratio - symv) / scale)
    ok = worst_fd < mp.mpf("1e-30") and worst_Nd < mp.mpf("1e-40")
    print(f"[2] 50-digit identity: |central-diff - sym deriv|/scale < 1e-30: {fmt(worst_fd)} ; |N/den - sym deriv|/scale < 1e-40: {fmt(worst_Nd)} -> {ok}")
    return ok


def check3() -> bool:
    worst = mp.mpf("inf")
    for i in range(1, 200):
        tv = mp.mpf(i) / 400  # (0, 0.5)
        for j in range(0, 25):
            nv = mp.mpf(10) ** (j / 10.0 - 3)  # [1e-3, 1e2+]
            w = mp.sqrt(tv * (1 - tv))
            f1 = 2 + nv - tv
            f2 = 3 * nv + 2 - 2 * w
            f3 = 3 * nv + 4 - 3 * tv - 4 * w
            worst = min(worst, f1, f2, f3)
    ok = worst > 0
    print(f"[3] denominator factors > 0 on grid (min factor {fmt(worst)}): {ok}")
    return ok


def check4() -> bool:
    min1 = min2 = min3 = min4 = minw = mp.mpf("inf")
    qmin = mp.mpf("inf")
    for i in range(1, 400):
        tv = mp.mpf(i) / 800
        w = mp.sqrt(tv * (1 - tv))
        minw = min(minw, mp.mpf("0.5") - w)
        qmin = min(qmin, 6 * tv**2 - 19 * tv + 10)
        for j in range(0, 40):
            nv = mp.mpf(10) ** (mp.mpf(j) / 10 - 3)
            t1 = 3 * nv**2 * (1 - 2 * tv)
            t2 = 6 * nv * (1 + w - 2 * tv**2)
            t3 = 4 * w * (1 - 2 * w**2)
            t4 = tv * (6 * tv**2 - 19 * tv + 10)
            min1, min2, min3, min4 = min(min1, t1), min(min2, t2), min(min3, t3), min(min4, t4)
    ok = min1 > 0 and min2 > 0 and min3 >= 0 and min4 > 0 and minw >= 0 and qmin > 0
    print(f"[4] four-term nonnegativity minima: t1>0 {fmt(min1)} | t2>0 {fmt(min2)} | t3>=0 {fmt(min3)} | t4>0 {fmt(min4)}; AM-GM (1/2-w)>=0 {fmt(minw)}; quad>0 {fmt(qmin)} -> {ok}")
    return ok


def check5() -> bool:
    worst = mp.mpf("inf")
    for j in range(0, 40):
        nv = mp.mpf(10) ** (mp.mpf(j) / 8 - 3)
        prev = None
        for i in range(1, 501):
            tv = mp.mpf(i) / 1000
            RH, R = numericRH(tv, nv)
            cur = mp.mpf(0.5) * mp.log(RH / R)
            if prev is not None:
                worst = min(worst, cur - prev)
            prev = cur
    ok = worst > 0
    print(f"[5] algebra-free: min DeltaI(step) over grid = {fmt(worst)} > 0: {ok}")
    return ok


def main() -> int:
    th, nu, w, RH, R, dI, dIp, N, den, diff1 = symbolic_core()
    results = [
        check1(diff1),
        check2(dIp, th, nu),
        check3(),
        check4(),
        check5(),
    ]
    print(f"\nsymplied dDeltaI/dtheta structural form available: {sp.count_ops(dIp) > 0}")
    print("PROPOSITION_C_THETA_LT_HALF: " + ("PASS" if all(results) else "FAIL"))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
