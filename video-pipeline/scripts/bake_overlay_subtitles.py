#!/usr/bin/env python3
"""
在无 subtitles/drawtext 滤镜的 ffmpeg 构建上，用全帧透明 PNG + overlay 按时间段烧录槽位文案。
用法:
  python3 scripts/bake_overlay_subtitles.py <episode.json> <concat.mp4> <audio> <out.mp4> <workdir>
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要 Pillow: pip install -r requirements-bake.txt", file=sys.stderr)
    sys.exit(1)

SLOT_ORDER = ("hook", "benefit", "pivot", "close")


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def discover_font_file(name_hint: str) -> Path:
    dirs = [
        Path.home() / "Library" / "Fonts",
        Path("/Library/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
    ]
    fd = os.environ.get("FONT_DIR")
    if fd:
        dirs.insert(0, Path(fd))
    mapping = [
        ("Bold", "NotoSansCJKsc-Bold.otf"),
        ("Medium", "NotoSansCJKsc-Medium.otf"),
        ("Black", "NotoSansCJKsc-Black.otf"),
        ("Regular", "NotoSansCJKsc-Regular.otf"),
    ]
    fname = None
    for key, fn in mapping:
        if key.lower() in name_hint.lower():
            fname = fn
            break
    if fname is None:
        fname = "NotoSansCJKsc-Medium.otf"
    for d in dirs:
        if not d or not d.is_dir():
            continue
        p = d / fname
        if p.is_file():
            return p
    raise FileNotFoundError(f"找不到字体文件 {fname}，请安装 Noto Sans CJK SC 或设置 FONT_DIR")


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) >= 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 255, 255, 255


def compute_segment_lengths(total: float, slots: dict, timing_mode: str) -> list[float]:
    texts = [slots.get(k, "") or "" for k in SLOT_ORDER]
    if timing_mode == "equal_by_slot":
        n = len(SLOT_ORDER)
        return [total / n] * n
    if timing_mode == "by_char_weight":
        weights = [max(1, len(t)) for t in texts]
        s = float(sum(weights))
        return [total * (w / s) for w in weights]
    raise ValueError(f"未知 timing_mode: {timing_mode}")


def wrap_cjk(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for block in text.split("\n"):
        if not block:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(block, width=width, break_long_words=False, break_on_hyphens=False))
    return lines if lines else [""]


def draw_slot_card(
    size: tuple[int, int],
    lines: list[str],
    preset: dict,
    font_path: Path,
) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_size = int(preset.get("fontSize", 44))
    try:
        font = ImageFont.truetype(str(font_path), font_size)
    except OSError:
        font = ImageFont.load_default()

    fill = hex_to_rgb(preset.get("primary", "#FFFFFF"))
    stroke_w = int(preset.get("outlineWidth", 3))
    stroke = hex_to_rgb(preset.get("outline", "#000000"))
    margin_v = int(preset.get("marginV", 140))
    box = bool(preset.get("box"))
    box_color = preset.get("boxColor", "#F5E6A3CC")
    pad = int(preset.get("boxBorderW", 16))

    line_heights = []
    line_widths = []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke_w)
        line_heights.append(bbox[3] - bbox[1])
        line_widths.append(bbox[2] - bbox[0])

    total_h = sum(line_heights) + (len(lines) - 1) * int(font_size * 0.25)
    max_w = max(line_widths) if line_widths else 0
    y0 = h - margin_v - total_h
    x0 = (w - max_w) / 2

    if box and lines and lines != [""]:
        bx0 = x0 - pad
        by0 = y0 - pad
        bx1 = x0 + max_w + pad
        by1 = y0 + total_h + pad
        rgba = hex_to_rgb(box_color[:7])
        alpha = 204
        if len(box_color) >= 9:
            alpha = int(box_color[7:9], 16)
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=12, fill=(*rgba, min(alpha, 255)))

    y = y0
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke_w)
        tw = bbox[2] - bbox[0]
        x = (w - tw) / 2
        draw.text((x, y), ln, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke)
        y += line_heights[i] + int(font_size * 0.25)

    return img


def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def ffprobe_has_audio_stream(path: Path) -> bool:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=index",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and bool(r.stdout.strip())


def ffprobe_first_audio_duration(path: Path) -> float:
    """取第一条音轨时长；适用于 MP4/MOV 等带画面的文件（仅用于对齐口播，不输出画面）。"""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        s = r.stdout.strip()
        if s and s != "N/A":
            try:
                d = float(s)
                if d > 0:
                    return d
            except ValueError:
                pass
    return ffprobe_duration(path)


def main() -> None:
    if len(sys.argv) < 6:
        print(
            "用法: python3 scripts/bake_overlay_subtitles.py <episode.json> <concat.mp4> <audio> <out.mp4> <workdir>",
            file=sys.stderr,
        )
        sys.exit(2)

    ep_path = Path(sys.argv[1])
    concat_mp4 = Path(sys.argv[2])
    audio = Path(sys.argv[3])
    out_mp4 = Path(sys.argv[4])
    workdir = Path(sys.argv[5])
    workdir.mkdir(parents=True, exist_ok=True)

    root = Path(__file__).resolve().parents[1]
    episode = load_json(ep_path)
    presets = load_json(root / "copy" / "presets.json")
    preset_name = episode.get("style_preset") or "default"
    preset = presets.get(preset_name)
    if not isinstance(preset, dict):
        raise SystemExit(f"找不到 preset: {preset_name}")

    if not ffprobe_has_audio_stream(audio):
        raise SystemExit(f"口播/音频文件没有可识别的音轨: {audio}")

    v_dur = ffprobe_duration(concat_mp4)
    a_dur = ffprobe_first_audio_duration(audio)
    total = min(v_dur, a_dur)
    lengths = compute_segment_lengths(total, episode.get("slots") or {}, episode.get("timing_mode") or "equal_by_slot")

    font_path = discover_font_file(str(preset.get("fontName", "")))

    # 竖屏默认720x1280；若与源不一致，以源视频为准
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(concat_mp4),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    wh = probe.stdout.strip().split("x")
    vw, vh = int(wh[0]), int(wh[1])
    wrap_chars = max(8, int(22 * (vw / 720)))

    png_paths: list[Path] = []
    for i, key in enumerate(SLOT_ORDER):
        text = str(episode.get("slots", {}).get(key, ""))
        lines = wrap_cjk(text, wrap_chars)
        im = draw_slot_card((vw, vh), lines, preset, font_path)
        p = workdir / f"slot-{i}.png"
        im.save(p)
        png_paths.append(p)

    t0 = 0.0
    chains: list[str] = []
    cur = "[0:v]"
    for i, ln in enumerate(lengths):
        t1 = t0 + float(ln)
        # 略微缩短末端，避免边界 flicker
        eps = 1e-3
        start = max(0.0, t0)
        end = max(start, t1 - eps)
        nxt = f"v{i+1}"
        expr = f"between(t\\,{start:.6f}\\,{end:.6f})"
        chains.append(f"{cur}[{i+1}:v]overlay=0:0:enable='{expr}'[{nxt}]")
        cur = f"[{nxt}]"
        t0 = t1

    fg = ";".join(chains)
    last_label = re.sub(r"^\[|\]$", "", cur)
    # 输入顺序: 0=拼接画面, 1..N=PNG, N+1=口播（可为纯音频或带画面的 MP4/MOV，仅取 a:0）
    audio_input_index = len(png_paths) + 1

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(concat_mp4),
    ]
    for p in png_paths:
        cmd += ["-loop", "1", "-i", str(p)]
    cmd += [
        "-i",
        str(audio),
        "-filter_complex",
        fg,
        "-map",
        f"[{last_label}]",
        "-map",
        f"{audio_input_index}:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
