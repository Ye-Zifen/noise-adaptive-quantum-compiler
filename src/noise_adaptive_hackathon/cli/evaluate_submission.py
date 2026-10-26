from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from noise_adaptive_hackathon.common.io import write_json
from noise_adaptive_hackathon.evaluator.submission import evaluate_submission_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="在双赛道公开 benchmark 上评测一个提交命令。")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--shots-a", type=int, default=256)
    parser.add_argument("--shots-b", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--timeout-sec", type=int, default=30)
    parser.add_argument("--out", type=Path, help="可选 JSON summary 输出路径")
    parser.add_argument("--command", nargs=argparse.REMAINDER, required=True, help="提交命令及其固定参数")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.command:
        raise SystemExit("submission command is required")

    summary = evaluate_submission_command(
        root=args.root,
        command=args.command,
        shots_a=args.shots_a,
        shots_b=args.shots_b,
        seed=args.seed,
        timeout_sec=args.timeout_sec,
    )
    if args.out is not None:
        write_json(args.out, asdict(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
