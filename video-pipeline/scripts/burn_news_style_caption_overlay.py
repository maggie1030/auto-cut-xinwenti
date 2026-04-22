#!/usr/bin/env python3
"""
在已有竖屏成片上叠加四块营销文案：Pillow 生成全帧透明 PNG + ffmpeg overlay。
颜色一律从脚本内置商务/活泼分槽池随机抽样（可 seed 复现），描边随字色亮度自动黑/白。
字体探测与 render_fixed_fullscreen_overlay.discover_overlay_font 一致（新青年体 / XINQING_FONT）。
可变文案写在 JSON 里，用 --job copy/caption-jobs/xxx.json 调用（路径相对当前工作目录）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要 Pillow: pip install -r requirements-bake.txt", file=sys.stderr)
    sys.exit(1)

_SCRIPTS = Path(__file__).resolve().parent

# 商务 / 活泼 分槽配色池（HEX），随机时从各槽抽样；描边由字色亮度自动选黑或白。
_PALETTE_BUSINESS = {
    "line1": ["#C47F2C", "#B85C38", "#8B5E3C", "#D4A017", "#C0392B"],
    "line2": ["#2E6BC6", "#1F6F8B", "#1B7F7A", "#3A6EA5", "#2C6E85"],
    "line3": ["#0F172A", "#111111", "#1F2937", "#0B3D2E"],
    "bottom": ["#F5F5F7", "#EDEDED", "#F6F1E8", "#EAF2FF"],
}
_FALLBACK_BUSINESS = ["#D4A017", "#2E6BC6", "#111111", "#F5F5F7"]

_PALETTE_PLAYFUL = {
    "line1": ["#FFD400", "#FF8A00", "#FF5A5F", "#FF2D95", "#FFC107"],
    "line2": ["#2D9CDB", "#00CEC9", "#6C5CE7", "#26C6DA", "#00B894"],
    "line3": ["#0A0A0A", "#1B5E20", "#4A148C", "#004D40"],
    "bottom": ["#FFFFFF", "#FFF8E1", "#F0FFF4", "#E8F7FF"],
}
_FALLBACK_PLAYFUL = ["#FFD400", "#2D9CDB", "#0A0A0A", "#FFFFFF"]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    s = h.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(h)
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _rgb_dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return float(
        (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    ) ** 0.5


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def _stroke_rgb_for_fill(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    # 深色字用白描边，浅色字用黑描边（与技能说明一致）
    return (255, 255, 255) if _luma(rgb) < 140 else (0, 0, 0)


def _sample_random_palette(
    tone: str, rng: random.Random, *, min_dist: float = 85.0, max_try: int = 40
) -> tuple[str, list[tuple[int, int, int]]]:
    if tone == "business":
        pools, fb = _PALETTE_BUSINESS, _FALLBACK_BUSINESS
    elif tone == "playful":
        pools, fb = _PALETTE_PLAYFUL, _FALLBACK_PLAYFUL
    else:
        raise SystemExit(f"未知 tone: {tone}")

    for _ in range(max_try):
        h1 = rng.choice(pools["line1"])
        h2 = rng.choice(pools["line2"])
        h3 = rng.choice(pools["line3"])
        h4 = rng.choice(pools["bottom"])
        if len({h1, h2, h3, h4}) < 4:
            continue
        c1, c2, c3, c4 = map(_hex_to_rgb, (h1, h2, h3, h4))
        cols = [c1, c2, c3, c4]
        ok = True
        for i in range(4):
            for j in range(i + 1, 4):
                if _rgb_dist(cols[i], cols[j]) < min_dist:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return tone, [c1, c2, c3, c4]
    return tone, [_hex_to_rgb(h) for h in fb]


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
    line1_y_pct: float,
    line2_y_pct: float,
    line3_y_pct: float,
    bottom_center_y_pct: float,
    stroke_scale: float,
    font_scale: float,
    palette_rgb: list[tuple[int, int, int]],
) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w / 2.0

    # 字号：主块按字高约 H 的 3.15%；二略大、三略小；底块约主标题的 87%
    fs1 = max(20, int(round(h * 0.0315 * font_scale)))
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
    stroke_white = max(1, int(round((fs1 / 7.0) * stroke_scale)))
    stroke_bot = max(1, int(round((fs_bot / 6.0) * stroke_scale)))
    if len(palette_rgb) != 4:
        raise SystemExit("需要恰好 4 个 RGB 颜色（line1…line3、bottom）")

    def _rgba(c: tuple[int, int, int]) -> tuple[int, int, int, int]:
        return (*c, 255)

    def _sw_main(fs: int) -> int:
        return max(1, int(round((fs / 7.0) * stroke_scale)))

    lines1 = wrap_to_max_px(
        draw,
        line1,
        font1,
        max_text_w,
        _sw_main(fs1),
    )
    lines2 = wrap_to_max_px(draw, line2, font2, max_text_w, stroke_white)
    lines3 = wrap_to_max_px(draw, line3, font3, max_text_w, stroke_white)

    lh1 = [line_height(draw, ln, font1, _sw_main(fs1)) for ln in lines1]
    y1_first_center = h * line1_y_pct
    centers1: list[float] = [y1_first_center]
    for i in range(1, len(lh1)):
        centers1.append(
            centers1[-1] + lh1[i - 1] / 2.0 + line_gap_main + lh1[i] / 2.0
        )

    c1 = palette_rgb[0]
    sw1 = _sw_main(fs1)
    sk1 = _stroke_rgb_for_fill(c1)
    for ln, cy in zip(lines1, centers1, strict=True):
        draw.text(
            (cx, cy),
            ln,
            font=font1,
            fill=_rgba(c1),
            stroke_width=sw1,
            stroke_fill=(*sk1, 255),
            anchor="mm",
        )

    row1_bottom = centers1[-1] + lh1[-1] / 2.0
    block_gap = int(round(fs1 * 0.42))

    # —— 第二行：池色 + 自动描边
    lh2 = [line_height(draw, ln, font2, stroke_white) for ln in lines2]
    y2_target = h * line2_y_pct
    y2_first_center = max(y2_target, row1_bottom + block_gap + lh2[0] / 2.0)
    centers2: list[float] = [y2_first_center]
    for i in range(1, len(lh2)):
        centers2.append(
            centers2[-1] + lh2[i - 1] / 2.0 + line_gap_main + lh2[i] / 2.0
        )
    c2 = palette_rgb[1]
    sk2 = _stroke_rgb_for_fill(c2)
    for ln, cy in zip(lines2, centers2, strict=True):
        draw.text(
            (cx, cy),
            ln,
            font=font2,
            fill=_rgba(c2),
            stroke_width=stroke_white,
            stroke_fill=(*sk2, 255),
            anchor="mm",
        )
    row2_bottom = centers2[-1] + lh2[-1] / 2.0

    # —— 第三行
    lh3 = [line_height(draw, ln, font3, stroke_white) for ln in lines3]
    y3_target = h * line3_y_pct
    y3_first_center = max(y3_target, row2_bottom + block_gap + lh3[0] / 2.0)
    centers3: list[float] = [y3_first_center]
    for i in range(1, len(lh3)):
        centers3.append(
            centers3[-1] + lh3[i - 1] / 2.0 + line_gap_main + lh3[i] / 2.0
        )
    c3 = palette_rgb[2]
    sk3 = _stroke_rgb_for_fill(c3)
    for ln, cy in zip(lines3, centers3, strict=True):
        draw.text(
            (cx, cy),
            ln,
            font=font3,
            fill=_rgba(c3),
            stroke_width=stroke_white,
            stroke_fill=(*sk3, 255),
            anchor="mm",
        )

    # —— 底部块
    # 底部文案保持靠左，但避免过于贴边
    margin_l = w * 0.10
    lines_b = wrap_to_max_px(draw, bottom, font_b, int(w * 0.92), stroke_bot)
    gap_b = int(round(fs_bot * 0.30))
    lh_b = [line_height(draw, ln, font_b, stroke_bot) for ln in lines_b]
    total_b = sum(lh_b) + (len(lines_b) - 1) * gap_b
    y_center_block = h * bottom_center_y_pct
    y_top_block = y_center_block - total_b / 2.0
    y = y_top_block
    c4 = palette_rgb[3]
    sk4 = _stroke_rgb_for_fill(c4)
    for i, ln in enumerate(lines_b):
        draw.text(
            (margin_l, y),
            ln,
            font=font_b,
            fill=_rgba(c4),
            stroke_width=stroke_bot,
            stroke_fill=(*sk4, 255),
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


def _coerce_float(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="在竖屏 MP4 上叠加四行营销文案（商务/活泼颜色池 + CLI 或 --job JSON）"
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
    ap.add_argument("--line1-y-pct", type=float, default=None)
    ap.add_argument("--line2-y-pct", type=float, default=None)
    ap.add_argument("--line3-y-pct", type=float, default=None)
    ap.add_argument("--bottom-center-y-pct", type=float, default=None)
    ap.add_argument(
        "--stroke-scale",
        type=float,
        default=None,
        help="描边缩放系数，默认 1.0；如 0.75 表示描边更细",
    )
    ap.add_argument(
        "--font-scale",
        type=float,
        default=None,
        help="字号缩放系数，默认 1.0；如 0.78 表示整体字号更小以减少换行",
    )
    ap.add_argument(
        "--tone",
        choices=("business", "playful", "random"),
        default=None,
        help="配色气质：商务池/活泼池/随机二选一；默认 job 或 random",
    )
    ap.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="可选，固定后可复现同一套颜色",
    )
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

    def pick_float(key: str, cli: float | None, default: float) -> float:
        if cli is not None:
            v = cli
        else:
            v = _coerce_float(job.get(key))
            if v is None:
                return default
        if not 0.0 < v < 1.0:
            raise SystemExit(f"{key} 必须在 0~1 之间（开区间），当前值: {v}")
        return v

    def pick_stroke_scale() -> float:
        if args.stroke_scale is not None:
            v = float(args.stroke_scale)
        else:
            v_raw = _coerce_float(job.get("stroke_scale"))
            v = 1.0 if v_raw is None else float(v_raw)
        if v <= 0:
            raise SystemExit(f"stroke_scale 必须大于 0，当前值: {v}")
        return v

    def pick_font_scale() -> float:
        if args.font_scale is not None:
            v = float(args.font_scale)
        else:
            v_raw = _coerce_float(job.get("font_scale"))
            v = 1.0 if v_raw is None else float(v_raw)
        if v <= 0:
            raise SystemExit(f"font_scale 必须大于 0，当前值: {v}")
        return v

    def pick_tone() -> str:
        if args.tone is not None:
            return args.tone
        v = job.get("tone")
        if isinstance(v, str) and v.strip() in ("business", "playful", "random"):
            return v.strip()
        return "random"

    def pick_seed() -> int | None:
        if args.random_seed is not None:
            return int(args.random_seed)
        v = job.get("random_seed")
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float) and v == int(v):
            return int(v)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return int(v.strip())
        return None

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
    line1_y_pct = pick_float("line1_y_pct", args.line1_y_pct, 0.075)
    line2_y_pct = pick_float("line2_y_pct", args.line2_y_pct, 0.125)
    line3_y_pct = pick_float("line3_y_pct", args.line3_y_pct, 0.17)
    bottom_center_y_pct = pick_float(
        "bottom_center_y_pct", args.bottom_center_y_pct, 0.79
    )
    stroke_scale = pick_stroke_scale()
    font_scale = pick_font_scale()
    tone_arg = pick_tone()
    seed = pick_seed()
    rng = random.Random(seed) if seed is not None else random.Random()
    if tone_arg == "random":
        tone_resolved = rng.choice(("business", "playful"))
    else:
        tone_resolved = tone_arg
    _, pal_rgb = _sample_random_palette(tone_resolved, rng)
    print(
        f"配色（颜色池）: tone={tone_resolved}"
        + (f" seed={seed}" if seed is not None else "")
        + f" RGB={pal_rgb}",
        flush=True,
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
        line1_y_pct=line1_y_pct,
        line2_y_pct=line2_y_pct,
        line3_y_pct=line3_y_pct,
        bottom_center_y_pct=bottom_center_y_pct,
        stroke_scale=stroke_scale,
        font_scale=font_scale,
        palette_rgb=pal_rgb,
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
