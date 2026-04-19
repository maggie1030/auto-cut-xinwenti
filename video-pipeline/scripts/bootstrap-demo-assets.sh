#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VDIR="$ROOT/assets/video/_demo"
ADIR="$ROOT/assets/audio/_demo"
mkdir -p "$VDIR" "$ADIR"

# 两段竖屏占位画面（H.264 + AAC静音轨，便于 concat）
ffmpeg -y -f lavfi -i "testsrc=duration=3:size=720x1280:rate=30" -f lavfi -i "anullsrc=r=48000:cl=stereo" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$VDIR/demo-clip-a.mp4"
ffmpeg -y -f lavfi -i "color=c=darkblue:s=720x1280:d=3:r=30" -f lavfi -i "anullsrc=r=48000:cl=stereo" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$VDIR/demo-clip-b.mp4"

# 占位配音（正弦波，6 秒）
ffmpeg -y -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=6" -c:a pcm_s16le "$ADIR/demo-voiceover.wav"

echo "已生成演示素材:"
echo "  $VDIR/demo-clip-a.mp4"
echo "  $VDIR/demo-clip-b.mp4"
echo "  $ADIR/demo-voiceover.wav"
echo "然后运行: npm run render:demo"
