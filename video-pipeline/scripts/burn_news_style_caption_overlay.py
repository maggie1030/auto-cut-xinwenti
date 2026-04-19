#!/usr/bin/env python3
"""
在已有竖屏成片上叠加「新闻体」固定四块文案：Pillow 生成全帧透明 PNG + ffmpeg overlay。
字体探测与 render_fixed_fullscreen_overlay.discover_overlay_font 一致（新青年体 / XINQING_FONT）。
可变文案推荐写在 JSON 里，用 --job copy/caption-jobs/xxx.json 调用（路径相对当前工作目录）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要 Pillow: pip install -r requirements-bake.txt", file=sys.stderr)
    sys.exit(1)

_SCRIPTS = Path(__file__).resolve().parent


def _load_overlay_font_module():
    spec = importlib.util.spec_from_file_location(
        "rfo_overlay_fonts",
        _SCRIPTS / "render_fixed_fullscreen_overlay.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def measure_text_w(draw: ImageDraw.ImageDraw, text: str, font, stroke_w: int = 0) -> float:
    # textlength 在部分 Pillow 版本不支持 stroke_width；统一用 textbbox 更稳
    bb = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    return float(bb[2] - bb[0])


def wrap_to_max_px(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_px: int,
    stroke_w: int = 0,
) -> list[str]:
    text = text.replace("\n", "").strip()
    if not text:
        return [""]
    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        w = measure_text_w(draw, trial, font, stroke_w)
        if w <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def line_height(draw: ImageDraw.ImageDraw, text: str, font, stroke_w: int = 0) -> int:
    bb = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
    return int(bb[3] - bb[1])


def ffprobe_wh(path: Path) -> tuple[int, int]:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    s = (json.loads(r.stdout).get("streams") or [{}])[0]
    return int(s["width"]), int(s["height"])


def ffprobe_has_audio(path: Path) -> bool:
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


def draw_news_overlay(
    size: tuple[int, int],
    font_path: Path,
    *,
    line1: str,
    line2: str,
    line3: str,
    bottom: str,
) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w / 2.0

    # 字号：主块按字高约 H 的 3.15%；二略大、三略小；底块约主标题的 87%
    fs1 = max(36, int(round(h * 0.0315)))
    fs2 = int(round(fs1 * 1.02))
    fs3 = int(round(fs1 * 0.98))
    fs_bot = int(round(fs1 * 0.87))

    try:
        font1 = ImageFont.truetype(str(font_path), fs1)
        font2 = ImageFont.truetype(str(font_path), fs2)
        font3 = ImageFont.truetype(str(font_path), fs3)
        font_b = ImageFont.truetype(str(font_path), fs_bot)
    except OSError:
        font1 = font2 = font3 = font_b = ImageFont.load_default()

    max_text_w = int(w * 0.90)
    line_gap_main = int(round(fs1 * 0.28))
    stroke_white = max(2, int(round(fs1 / 7.0)))
    stroke_bot = max(3, int(round(fs_bot / 6.0)))

    lines1 = wrap_to_max_px(draw, line1, font1, max_text_w, 0)
    lines2 = wrap_to_max_px(draw, line2, font2, max_text_w, stroke_white)
    lines3 = wrap_to_max_px(draw, line3, font3, max_text_w, stroke_white)

    # —— 第一行块：白底圆角 + 黑字，首行中心 y ≈ 0.075H
    lh1 = [line_height(draw, ln, font1, 0) for ln in lines1]
    y1_first_center = h * 0.075
    centers1: list[float] = [y1_first_center]
    for i in range(1, len(lh1)):
        centers1.append(
            centers1[-1] + lh1[i - 1] / 2.0 + line_gap_main + lh1[i] / 2.0
        )

    max_tw = 0
    for ln in lines1:
        max_tw = max(max_tw, int(measure_text_w(draw, ln, font1, 0)))
    pad = int(round(fs1 * 0.38))
    radius = max(8, int(round(fs1 * 0.22)))
    box_top = centers1[0] - lh1[0] / 2.0 - pad
    box_bot = centers1[-1] + lh1[-1] / 2.0 + pad
    box_l = cx - max_tw / 2.0 - pad
    box_r = cx + max_tw / 2.0 + pad
    draw.rounded_rectangle(
        (box_l, box_top, box_r, box_bot),
        radius=radius,
        fill=(255, 255, 255, 255),
    )
    for ln, cy in zip(lines1, centers1, strict=True):
        draw.text((cx, cy), ln, font=font1, fill=(0, 0, 0, 255), anchor="mm")

    row1_bottom = centers1[-1] + lh1[-1] / 2.0
    block_gap = int(round(fs1 * 0.42))

    # —— 第二行：橘黄 + 白描边
    lh2 = [line_height(draw, ln, font2, stroke_white) for ln in lines2]
    y2_target = h * 0.125
    y2_first_center = max(y2_target, row1_bottom + block_gap + lh2[0] / 2.0)
    centers2: list[float] = [y2_first_center]
    for i in range(1, len(lh2)):
        centers2.append(
            centers2[-1] + lh2[i - 1] / 2.0 + line_gap_main + lh2[i] / 2.0
        )
    orange = (255, 154, 0, 255)
    for ln, cy in zip(lines2, centers2, strict=True):
        draw.text(
            (cx, cy),
            ln,
            font=font2,
            fill=orange,
            stroke_width=stroke_white,
            stroke_fill=(255, 255, 255, 255),
            anchor="mm",
        )
    row2_bottom = centers2[-1] + lh2[-1] / 2.0

    # —— 第三行：墨蓝 + 白描边
    lh3 = [line_height(draw, ln, font3, stroke_white) for ln in lines3]
    y3_target = h * 0.17
    y3_first_center = max(y3_target, row2_bottom + block_gap + lh3[0] / 2.0)
    centers3: list[float] = [y3_first_center]
    for i in range(1, len(lh3)):
        centers3.append(
            centers3[-1] + lh3[i - 1] / 2.0 + line_gap_main + lh3[i] / 2.0
        )
    ink = (0, 64, 80, 255)
    for ln, cy in zip(lines3, centers3, strict=True):
        draw.text(
            (cx, cy),
            ln,
            font=font3,
            fill=ink,
            stroke_width=stroke_white,
            stroke_fill=(255, 255, 255, 255),
            anchor="mm",
        )

    # —— 底部块：白字黑描边，左对齐；整块垂直中心距顶约 0.79H
    margin_l = w * 0.065
    lines_b = wrap_to_max_px(draw, bottom, font_b, int(w * 0.92), stroke_bot)
    gap_b = int(round(fs_bot * 0.30))
    lh_b = [line_height(draw, ln, font_b, stroke_bot) for ln in lines_b]
    total_b = sum(lh_b) + (len(lines_b) - 1) * gap_b
    y_center_block = h * 0.79
    y_top_block = y_center_block - total_b / 2.0
    y = y_top_block
    for i, ln in enumerate(lines_b):
        draw.text(
            (margin_l, y),
            ln,
            font=font_b,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_bot,
            stroke_fill=(0, 0, 0, 255),
        )
        y += lh_b[i] + gap_b

    return img


def _resolve_media_path(p: str | Path | None, cwd: Path) -> Path | None:
    if p is None or (isinstance(p, str) and not p.strip()):
        return None
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _load_job(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"找不到 job 文件: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"job JSON 无效: {path}: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit("job 文件顶层须为 JSON 对象")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(
        description="在竖屏 MP4 上叠加新闻体固定文案（CLI 或 --job JSON）"
    )
    ap.add_argument(
        "--job",
        type=Path,
        default=None,
        help="任务 JSON：含 in/out/line1/line2/line3/bottom，可选 workdir；路径相对当前工作目录",
    )
    ap.add_argument("--in", dest="inp", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--line1", type=str, default=None)
    ap.add_argument("--line2", type=str, default=None)
    ap.add_argument("--line3", type=str, default=None)
    ap.add_argument("--bottom", type=str, default=None)
    ap.add_argument("--workdir", type=Path, default=None)
    args = ap.parse_args()

    cwd = Path.cwd()
    job: dict = {}
    if args.job is not None:
        job = _load_job(args.job.resolve())

    def pick_str(key: str, cli: str | None, default: str) -> str:
        if cli is not None:
            return cli
        v = job.get(key)
        if isinstance(v, str) and v.strip():
            return v
        return default

    inp = args.inp
    if inp is None and isinstance(job.get("in"), str):
        inp = _resolve_media_path(job["in"], cwd)
    elif inp is not None:
        inp = _resolve_media_path(inp, cwd)
    else:
        inp = None

    out = args.out
    if out is None and isinstance(job.get("out"), str):
        out = _resolve_media_path(job["out"], cwd)
    elif out is not None:
        out = _resolve_media_path(out, cwd)
    else:
        out = None

    if inp is None:
        raise SystemExit("缺少输入成片：请在 job 中写 in 或传 --in")
    if out is None:
        raise SystemExit("缺少输出路径：请在 job 中写 out 或传 --out")

    workdir_arg = args.workdir
    if workdir_arg is None and job.get("workdir"):
        workdir_arg = _resolve_media_path(str(job["workdir"]), cwd)
    elif workdir_arg is not None:
        workdir_arg = _resolve_media_path(workdir_arg, cwd)

    line1 = pick_str(
        "line1",
        args.line1,
        "老公为了不被裁员去线下学AI了",
    )
    line2 = pick_str(
        "line2",
        args.line2,
        "一天就上手，能写文案能做短视频。",
    )
    line3 = pick_str(
        "line3",
        args.line3,
        "老师手把手带练才发现AI其实没有那么难。",
    )
    bottom = pick_str(
        "bottom",
        args.bottom,
        "学员：早知道不在网上报那种乱七八糟的课程，线下手把手带练上手更快。",
    )

    inp = inp.resolve()
    out = out.resolve()
    if not inp.is_file():
        raise SystemExit(f"找不到输入: {inp}")

    vw, vh = ffprobe_wh(inp)
    rfo = _load_overlay_font_module()
    font_path = rfo.discover_overlay_font()

    workdir = workdir_arg or (inp.parent / "_work" / "news_caption_burn")
    workdir.mkdir(parents=True, exist_ok=True)
    png_path = workdir / "overlay_news.png"

    im = draw_news_overlay(
        (vw, vh),
        font_path,
        line1=line1,
        line2=line2,
        line3=line3,
        bottom=bottom,
    )
    im.save(png_path)

    has_a = ffprobe_has_audio(inp)
    out.parent.mkdir(parents=True, exist_ok=True)

    fc = "[0:v][1:v]overlay=0:0:shortest=1[outv]"
    cmd: list[str | Path] = [
        "ffmpeg",
        "-y",
        "-noautorotate",
        "-i",
        str(inp),
        "-loop",
        "1",
        "-i",
        str(png_path),
        "-filter_complex",
        fc,
        "-map",
        "[outv]",
    ]
    if has_a:
        cmd.extend(["-map", "0:a:0", "-c:a", "copy"])
    else:
        cmd.append("-an")
    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    subprocess.run(cmd, check=True)
    print(f"已导出: {out}（叠加 PNG: {png_path}）")


if __name__ == "__main__":
    main()
