#!/usr/bin/env python3
"""
可选：用 faster-whisper 从音频生成 SRT（便于你对齐画面或回填 slots）。
用法:
  python3 scripts/transcribe_whisper.py assets/audio/voice.wav out/voice.srt

需先: pip install -r requirements-whisper.txt
"""
from __future__ import annotations

import argparse
import sys


def main() -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("未安装 faster-whisper，请执行: pip install -r requirements-whisper.txt", file=sys.stderr)
        sys.exit(1)

    p = argparse.ArgumentParser()
    p.add_argument("audio", help="输入音频路径")
    p.add_argument("out_srt", help="输出 .srt")
    p.add_argument("--model", default="small", help="模型尺寸，如 tiny/base/small/medium/large-v3")
    p.add_argument("--device", default="auto", help="auto/cpu/cuda")
    args = p.parse_args()

    model = WhisperModel(args.model, device=args.device)
    segments, _ = model.transcribe(args.audio, language="zh")

    def fmt_ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")

    with open(args.out_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("已写入:", args.out_srt)


if __name__ == "__main__":
    main()
