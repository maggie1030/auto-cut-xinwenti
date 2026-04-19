#!/usr/bin/env bash
# 依赖安装辅助：按常见发行版选用包管理器；需管理员权限的命令已单独标注。
set -euo pipefail

info() { echo "[setup] $*"; }
warn() { echo "[setup][warn] $*" >&2; }

detect_os() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "macos"
    return
  fi
  if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    . /etc/os-release
    case "${ID:-}" in
      ubuntu | debian | pop) echo "debian" ;;
      fedora | rhel | centos | rocky | almalinux) echo "rhel" ;;
      *) echo "linux-unknown:${ID:-unknown}" ;;
    esac
    return
  fi
  echo "unknown"
}

OS="$(detect_os)"
info "识别为: $OS（uname: $(uname -s)）"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

case "$OS" in
  macos)
    if need_cmd brew; then
      brew install ffmpeg jq || true
      brew list --cask font-noto-sans-cjk-sc >/dev/null 2>&1 || brew install --cask font-noto-sans-cjk-sc || true
    else
      warn "未找到 Homebrew。请安装 https://brew.sh 后重试，或手动安装 ffmpeg / jq / Noto CJK。"
    fi
    ;;
  debian)
    info "建议执行（需 sudo）："
    echo "  sudo apt-get update && sudo apt-get install -y ffmpeg jq python3 python3-pip python3-venv fonts-noto-cjk"
    ;;
  rhel)
    info "建议执行（需 sudo）："
    echo "  sudo dnf install -y ffmpeg jq python3 python3-pip google-noto-sans-cjk-sc-fonts || sudo yum install -y ffmpeg jq python3"
    ;;
  *)
    warn "无法唯一映射到安装命令。请手动安装: ffmpeg、ffprobe、jq、python3、pip、Noto CJK（或兼容中文字体）。"
    ;;
esac

if ! need_cmd node; then
  warn "未检测到 Node.js。macOS/Linux 建议使用 nvm 或官方安装包安装 LTS（本工程已在 Node 22 验证）。"
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
info "安装 Python 依赖（当前用户，无需 sudo）…"
pip3 install -r "$ROOT/requirements-bake.txt" || warn "Pillow 安装失败，请检查 pip。"
pip3 install -r "$ROOT/requirements-whisper.txt" || warn "faster-whisper 可选，安装失败可忽略。"

info "完成。请运行: cd \"$ROOT\" && npm run check"
