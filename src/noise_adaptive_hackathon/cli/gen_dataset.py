from __future__ import annotations

import argparse
from pathlib import Path

from noise_adaptive_hackathon.public_assets import generate_public_assets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成公开 benchmark 和后端快照。")
    parser.add_argument("--out", required=True, type=Path, help="写入 benchmarks/ 和 backends/ 的根目录")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    generate_public_assets(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
