"""路径与凭据解析。所有模块只从这里取路径，不写死绝对路径。"""
from __future__ import annotations

import os
from pathlib import Path

# v1/xy/paths.py -> v1/xy -> v1 -> 课题根
ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "v1"

RAW = V1 / "raw"            # tushare 原始落盘
PANEL = V1 / "runs" / "panel"
RUNS = V1 / "runs"
REPORTS = V1 / "reports"
CONFIGS = V1 / "configs"

CN_TICK = ROOT / "tick数据" / "QDCData" / "cn_tick" / "full"
L2_DIR = ROOT / "tick数据" / "QDCData" / "L2"
KRONOS_LOCAL = ROOT / "KronosLocal"
TOKEN_FILE = ROOT / ".secrets" / "tushare_token"

for _p in (RAW, PANEL, RUNS, REPORTS):
    _p.mkdir(parents=True, exist_ok=True)


def tushare_token() -> str:
    """从 .secrets 读取；也允许环境变量覆盖。"""
    env = os.environ.get("TUSHARE_TOKEN")
    if env:
        return env.strip()
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"缺少 tushare token：{TOKEN_FILE}")
    return TOKEN_FILE.read_text(encoding="utf-8").strip()


def rel(p: Path) -> str:
    """日志里打印相对路径，避免把本机绝对路径写进产物。"""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)
