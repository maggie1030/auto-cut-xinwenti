#!/usr/bin/env python3
"""
竖屏 9:16：逐段转正（-noautorotate + transpose）→ 统一缩放留边 → 拼接全部素材
→ 默认按统一倍速 D/T 压缩/拉伸整条画面至口播时长（D=拼接总时长，T=口播有效时长）
→ 默认不加任何画面文案；需要全屏固定 PNG 字幕时显式传 --overlay。
→ 可选 --video-speed 手动倍速时仍可用 apad/atrim 对齐音画。
→ 成片末尾经 yuv4mpegpipe 重封装视频轨，去除 Display Matrix，避免播放器把竖屏再转横。
→ --overlay 时的字幕绘制见 draw_full_overlay（字体：XINQING_FONT / 自动探测）。
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

# 与 bake_overlay_subtitles 一致的字体探测
def discover_font_file(name_hint: str) -> Path:
    import os

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
        fname = "NotoSansCJKsc-Bold.otf"
    for d in dirs:
        if not d or not d.is_dir():
            continue
        p = d / fname
        if p.is_file():
            return p
    raise FileNotFoundError(f"找不到字体文件 {fname}，请安装 Noto Sans CJK SC 或设置 FONT_DIR")


def discover_overlay_font() -> Path:
    """
    成片固定字幕：优先「新青年体」。
    可设置环境变量 XINQING_FONT=/path/to/字体.ttf 强制指定；否则在常见字体目录按文件名探测。
    找不到时回退 Noto Sans CJK SC Medium（并在 stderr 提示安装新青年体）。
    """
    import os

    env = os.environ.get("XINQING_FONT", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    dirs: list[Path] = []
    fd = os.environ.get("FONT_DIR")
    if fd:
        dirs.append(Path(fd))
    dirs.extend(
        [
            Path.home() / "Library" / "Fonts",
            Path("/Library/Fonts"),
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
        ]
    )
    candidates = [
        "新青年体.ttf",
        "新青年体.otf",
        "Aa新青年体.ttf",
        "Aa新青年体.otf",
        "XinQingNian.ttf",
        "XinQingNian.otf",
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for name in candidates:
            p = d / name
            if p.is_file():
                return p
    print(
        "提示: 未找到新青年体，已用 Noto Sans CJK SC Medium 代替；"
        "安装字体或设置 XINQING_FONT / FONT_DIR",
        file=sys.stderr,
    )
    return discover_font_file("Medium")


def probe_stream_rotation(path: Path) -> int:
    """ffprobe 的 Display Matrix rotation 或 tags.rotate（度）。无则 0。"""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(r.stdout)
    streams = data.get("streams") or []
    if not streams:
        return 0
    s = streams[0]
    tags = s.get("tags") or {}
    if "rotate" in tags:
        try:
            return int(tags["rotate"])
        except ValueError:
            pass
    for sd in s.get("side_data_list") or []:
        if sd.get("side_data_type") == "Display Matrix" and "rotation" in sd:
            try:
                return int(sd["rotation"])
            except (TypeError, ValueError):
                pass
    return 0


def rotation_to_transpose_chain(rotation: int) -> str:
    """
    在 -noautorotate 下对「存储像素」施加 transpose，与常见播放器按 Display Matrix 显示一致。
    映射经本机 ffprobe + 抽帧对比校正：rotation=90（如 iPhone MOV）用 transpose=2；
    rotation=-90（如部分微信导出）用 transpose=1。
    """
    r = int(rotation) % 360
    if r > 180:
        r -= 360
    if r == 0:
        return ""
    if r in (90, -270):
        return "transpose=2,"
    if r in (-90, 270):
        return "transpose=1,"
    if r in (180, -180):
        return "transpose=1,transpose=1,"
    return ""


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


def ffprobe_audio_duration(path: Path) -> float:
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
    if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "N/A":
        try:
            d = float(r.stdout.strip())
            if d > 0:
                return d
        except ValueError:
            pass
    return ffprobe_duration(path)


def remux_video_strip_display_matrix(src: Path, dst: Path) -> None:
    """
    去掉 MP4 视频轨上的 Display Matrix（播放器不再二次旋转）。
    直接 libx264 重编码会继承矩阵；经 yuv4mpegpipe 断开后再编码即可得到「干净」竖屏。
    """
    qs = shlex.quote(str(src))
    qd = shlex.quote(str(dst))
    # 管道第一段只出原始 YUV 序列，第二段从 stdin 读 yuv4mpeg、从原文件 copy 音轨
    bash = (
        f"ffmpeg -y -noautorotate -i {qs} -an -f yuv4mpegpipe - 2>/dev/null | "
        f"ffmpeg -y -f yuv4mpegpipe -i - -i {qs} -map_chapters -1 -map_metadata -1 "
        f"-map 0:v:0 -map 1:a:0 -c:v libx264 -pix_fmt yuv420p -preset medium -crf 23 "
        f"-c:a copy -shortest -movflags +faststart {qd}"
    )
    subprocess.run(bash, shell=True, check=True)


def normalize_segment(
    src: Path,
    dst: Path,
    w: int,
    h: int,
) -> None:
    rot = probe_stream_rotation(src)
    pre = rotation_to_transpose_chain(rot)
    vf = (
        f"{pre}scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-noautorotate",
            "-i",
            str(src),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dst),
        ],
        check=True,
    )


def atempo_filter_segments(aspeed: float) -> list[str]:
    """口播变速的 atempo 链（0 段表示不变速）。"""
    if abs(aspeed - 1.0) <= 1e-6:
        return []
    segs: list[str] = []
    r = float(aspeed)
    while r > 2.0 + 1e-6:
        segs.append("atempo=2.0")
        r /= 2.0
    while r < 0.5 - 1e-6:
        segs.append("atempo=0.5")
        r /= 0.5
    segs.append(f"atempo={r:.6f}")
    return segs


def build_audio_chain_fit_voiceover(aspeed: float) -> str:
    """仅 atempo + 时间戳重置，不 apad/atrim（画面已按 D/T 对齐口播长度）。"""
    parts = atempo_filter_segments(aspeed)
    parts.append("asetpts=PTS-STARTPTS")
    return ",".join(parts)


def build_audio_chain(aspeed: float, video_out_dur: float, audio_src_dur: float) -> str:
    """手动画面倍速时：atempo 后再 apad/atrim 对齐视频轨时长。"""
    parts = atempo_filter_segments(aspeed)
    a_eff = audio_src_dur / aspeed
    eps = 0.04
    if a_eff + eps < video_out_dur:
        parts.append(f"apad=pad_dur={video_out_dur - a_eff:.6f}")
    elif a_eff > video_out_dur + eps:
        parts.append(f"atrim=0:{video_out_dur:.6f}")
    parts.append("asetpts=PTS-STARTPTS")
    return ",".join(parts)


def wrap_cjk(text: str, width: int) -> list[str]:
    lines: list[str] = []
    for block in text.split("\n"):
        if not block:
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(block, width=width, break_long_words=False, break_on_hyphens=False)
        )
    return lines if lines else [""]


def draw_full_overlay(
    size: tuple[int, int],
    font_path: Path,
):
    """
    固定字幕（相对画布：X 以水平居中；中间三行 Y 为从上边缘向下的像素坐标；
    「底部」块：约定用户 Y=-900 表示自画面中心向下 900px 处为块垂直中心）。
    字号按用户要求为 12 / 11（Pillow fontsize，接近像素高）。
    仅在使用 --overlay 时调用；需 Pillow。
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("叠加文案需要 Pillow: pip install -r requirements-bake.txt", file=sys.stderr)
        sys.exit(1)

    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = w / 2.0

    line1 = "【老公为了不被裁员就去线下学AI了】"
    line2 = "【一天就上手，能写文章能做短视频】"
    line3 = "【老师手把手带练才发现AI没有那么难】"
    bottom_lines = [
        "【网友：",
        "早知道不在网上学那些乱七八糟的课程了",
        "线下学效率更高、上手更快】",
    ]

    fs_mid = 12
    fs_bot = 11
    pad_bg = 6
    try:
        font_mid = ImageFont.truetype(str(font_path), fs_mid)
        font_bot = ImageFont.truetype(str(font_path), fs_bot)
    except OSError:
        font_mid = ImageFont.load_default()
        font_bot = font_mid

    gap_bot = 5
    stroke_bot = 2

    # 第三行：Y=960 墨蓝描黑边
    y3 = 960
    ink_blue = (27, 58, 95, 255)
    for ln in wrap_cjk(line3, max(8, int(24 * (w / 1080)))):
        draw.text(
            (cx, y3),
            ln,
            font=font_mid,
            fill=ink_blue,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 255),
            anchor="mm",
        )
        bb = draw.textbbox((0, 0), ln, font=font_mid, stroke_width=1)
        y3 += (bb[3] - bb[1]) + 6

    # 第二行：Y=1100 红褐描白边
    y2 = 1100
    red_brown = (160, 82, 45, 255)
    for ln in wrap_cjk(line2, max(8, int(24 * (w / 1080)))):
        draw.text(
            (cx, y2),
            ln,
            font=font_mid,
            fill=red_brown,
            stroke_width=2,
            stroke_fill=(255, 255, 255, 255),
            anchor="mm",
        )
        bb = draw.textbbox((0, 0), ln, font=font_mid, stroke_width=2)
        y2 += (bb[3] - bb[1]) + 6

    # 第一行：Y=1400 白底黑字（多行时每行独立白底）
    y1_cur = 1400.0
    for ln in wrap_cjk(line1, max(8, int(24 * (w / 1080)))):
        bb = draw.textbbox((0, 0), ln, font=font_mid)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        bx0 = cx - tw / 2 - pad_bg
        by0 = y1_cur - th / 2 - pad_bg
        bx1 = cx + tw / 2 + pad_bg
        by1 = y1_cur + th / 2 + pad_bg
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=4, fill=(255, 255, 255, 255))
        draw.text((cx, y1_cur), ln, font=font_mid, fill=(0, 0, 0, 255), anchor="mm")
        y1_cur += th + 6

    # 底部块：最后绘制，压在中间三行之上；中心在画面中线之下 900px（Y=-900 相对中心、向下为正）
    y_bottom_center = h // 2 + 900
    wrapped_bottom: list[str] = []
    for block in bottom_lines:
        wrapped_bottom.extend(wrap_cjk(block, max(8, int(22 * (w / 1080)))))
    heights_b = []
    for ln in wrapped_bottom:
        bb = draw.textbbox((0, 0), ln, font=font_bot, stroke_width=stroke_bot)
        heights_b.append(bb[3] - bb[1])
    total_b = sum(heights_b) + (len(wrapped_bottom) - 1) * gap_bot
    y0 = y_bottom_center - total_b / 2.0
    cy = y0
    for ln in wrapped_bottom:
        bb = draw.textbbox((0, 0), ln, font=font_bot, stroke_width=stroke_bot)
        lh = bb[3] - bb[1]
        mid_y = cy + lh / 2.0
        draw.text(
            (cx, mid_y),
            ln,
            font=font_bot,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_bot,
            stroke_fill=(0, 0, 0, 255),
            anchor="mm",
        )
        cy += lh + gap_bot

    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--videos",
        nargs="+",
        type=Path,
        required=True,
        help="画面文件路径列表（按顺序拼接）",
    )
    ap.add_argument("--audio", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workdir", type=Path, default=None)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument(
        "--video-speed",
        type=float,
        default=None,
        help="固定画面倍速；省略时自动使用 D/T（拼接时长/口播有效时长），多段全用且口播不断",
    )
    ap.add_argument(
        "--audio-speed",
        type=float,
        default=1.0,
        help="口播 atempo 倍率（默认 1.0）；T = 源口播时长 / 此值，用于计算 D/T",
    )
    ap.add_argument(
        "--overlay",
        action="store_true",
        help="叠加全屏固定 PNG 文案（默认关闭，不把文案写入默认工序）",
    )
    args = ap.parse_args()

    root = args.root
    workdir = args.workdir or (root / "out" / "_work" / "vertical_montage_run")
    workdir.mkdir(parents=True, exist_ok=True)

    for p in args.videos:
        if not p.is_file():
            raise SystemExit(f"缺少画面: {p}")
    if not args.audio.is_file():
        raise SystemExit(f"缺少音频: {args.audio}")

    norm_dir = workdir / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_paths: list[Path] = []
    for i, p in enumerate(args.videos):
        dst = norm_dir / f"seg_{i:03d}.mp4"
        normalize_segment(p.resolve(), dst, args.w, args.h)
        norm_paths.append(dst)

    concat_list = workdir / "concat.txt"
    with concat_list.open("w", encoding="utf-8") as f:
        for p in norm_paths:
            abs_p = p.resolve()
            esc = str(abs_p).replace("'", "'\\''")
            f.write(f"file '{esc}'\n")

    concat_mp4 = workdir / "concat_raw.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            # 规范化片段像素已是竖屏，但文件里常仍带 Display Matrix；concat 解码默认会再旋转一次，必须关掉
            "-noautorotate",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            "-movflags",
            "+faststart",
            str(concat_mp4),
        ],
        check=True,
    )

    overlay_png: Path | None = None
    if args.overlay:
        font_path = discover_overlay_font()
        overlay_png = workdir / "overlay_full.png"
        im = draw_full_overlay((args.w, args.h), font_path)
        im.save(overlay_png)

    concat_dur = ffprobe_duration(concat_mp4)
    audio_src_dur = ffprobe_audio_duration(args.audio)

    aspeed = float(args.audio_speed)
    if aspeed <= 0:
        raise SystemExit("audio-speed 须 > 0")

    t_voice = audio_src_dur / aspeed
    if t_voice <= 0.01:
        raise SystemExit("口播有效时长过短，无法计算 D/T")
    if concat_dur <= 0.01:
        raise SystemExit("拼接画面时长过短")

    if args.video_speed is None:
        vs = concat_dur / t_voice
        video_out_dur = t_voice
        a_chain = build_audio_chain_fit_voiceover(aspeed)
        mode = "auto D/T"
    else:
        vs = max(0.05, float(args.video_speed))
        video_out_dur = concat_dur / vs
        a_chain = build_audio_chain(aspeed, video_out_dur, audio_src_dur)
        mode = f"manual {vs}x + apad/atrim"

    # 仅对拼接结果做倍速（单段已统一分辨率）
    vf = f"setpts=PTS/{vs:.9f}"

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.overlay:
        if overlay_png is None:
            raise SystemExit("内部错误: --overlay 但未生成 overlay PNG")
        fc = (
            f"[0:v]{vf}[v0];"
            f"[v0][1:v]overlay=0:0:shortest=1[outv];"
            f"[2:a]{a_chain}[outa]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-noautorotate",
            "-i",
            str(concat_mp4),
            "-loop",
            "1",
            "-i",
            str(overlay_png),
            "-i",
            str(args.audio),
            "-filter_complex",
            fc,
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(out),
        ]
    else:
        fc = f"[0:v]{vf}[outv];[1:a]{a_chain}[outa]"
        cmd = [
            "ffmpeg",
            "-y",
            "-noautorotate",
            "-i",
            str(concat_mp4),
            "-i",
            str(args.audio),
            "-filter_complex",
            fc,
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(out),
        ]
    subprocess.run(cmd, check=True)

    strip_tmp = out.with_suffix(".strip-tmp.mp4")
    try:
        remux_video_strip_display_matrix(out, strip_tmp)
        strip_tmp.replace(out)
    except subprocess.CalledProcessError:
        if strip_tmp.exists():
            strip_tmp.unlink()
        raise
    ol = "全屏 PNG 文案" if args.overlay else "无画面文案"
    print(
        f"已导出: {out}（{ol}；{mode}；D={concat_dur:.3f}s T={t_voice:.3f}s 画面倍速≈{vs:.4f}x；"
        f"口播源 {audio_src_dur:.3f}s × {aspeed}；已去除 Display Matrix）"
    )


if __name__ == "__main__":
    main()
