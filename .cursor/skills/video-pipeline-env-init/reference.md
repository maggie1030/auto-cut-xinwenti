# video-pipeline 环境初始化 — 参考

## `setup-env.sh` 行为摘要

| 识别结果 | 行为 |
|----------|------|
| `macos` | 若有 `brew`：`brew install ffmpeg jq`；尝试 `brew install --cask font-noto-sans-cjk-sc` |
| `debian`（ubuntu/debian/pop） | 仅打印 `sudo apt-get install …` 建议 |
| `rhel`（fedora/rhel/centos/rocky/almalinux） | 仅打印 `sudo dnf install …` 建议 |
| 其他 | 打印通用依赖列表 |

脚本末尾会对当前用户执行：`pip3 install -r requirements-bake.txt` 与 `pip3 install -r requirements-whisper.txt`（后者失败仅警告）。

## 手动安装命令（无 brew / 无自动脚本时）

### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg jq python3 python3-pip python3-venv fonts-noto-cjk
```

### Fedora / RHEL 系（包名以实际仓库为准）

```bash
sudo dnf install -y ffmpeg jq python3 python3-pip google-noto-sans-cjk-sc-fonts
```

### macOS（无 Homebrew 时）

1. 安装 [Homebrew](https://brew.sh)，或从 [ffmpeg.org](https://ffmpeg.org/download.html) 等渠道安装 ffmpeg。
2. 字体：App Store / 字体册安装 Noto Sans CJK SC，或使用 `brew install --cask font-noto-sans-cjk-sc`。

## Node 版本

- 使用 **当前 LTS** 即可；README 记载 Node 22 已验证。
- 若仅用 **D/T 竖屏脚本** `render_fixed_fullscreen_overlay.py`，理论上可不装 Node，但 **`npm run check` / `npm run setup` / `render.sh` 主路径** 依赖 Node，仍建议安装。

## Python 与 venv（推荐）

避免系统包冲突：

```bash
cd video-pipeline
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-bake.txt
pip install -r requirements-whisper.txt   # 可选
```

若使用 venv，**`npm run check`** 里 `pip3 show Pillow` 可能仍指向全局 pip；可再用 `which python3` / `.venv/bin/pip show Pillow` 人工确认。

## 自检失败时

| 现象 | 方向 |
|------|------|
| 无 ffmpeg | 按上表安装；确认 `ffmpeg -version` |
| 无 jq | `apt/brew/dnf install jq` |
| 无 Pillow | `pip install -r requirements-bake.txt` |
| fc-list 无 Noto | 安装 `fonts-noto-cjk` 或 cask；或 `export FONT_DIR=...` |
| ffmpeg 冒烟失败 | 查磁盘权限、是否缺 libx264 |

## 与「竖屏 D/T 单脚本」依赖的差异

`render_fixed_fullscreen_overlay.py`：**默认成片**仅需系统 **ffmpeg/ffprobe + python3**；**`--overlay`** 时需 Pillow。  
**槽位字幕主路径**（`render.sh` 等）：需 **Node + jq + ffmpeg + Pillow + 字体**，以 `npm run check` 为准。
