# 我做了一套「新闻体竖屏」剪辑 Skill：不用背命令，四步出片

大家好，我是 Maggie。

之前我在做**新闻体短视频**的时候，发现几件特别耗神的事：

- 手里好几段竖屏素材，**口播只有一条**，成片时长要跟口播对齐，在剪辑软件里**一截一截调速**，很容易对不准。  
- **同一套画面大字**（主标题、两行强调色、底部「学员」引语），每条片子字不一样，但版式想固定——**每次手调坐标、字号，太费时间**。  
- 真正跑起来全是 **`ffmpeg` + 小脚本**，**命令一长串**，换台电脑就忘，也没法交给 AI 稳定复现。

所以我把整条链路**固化成了一仓库脚本 + 三个 Cursor 项目 Skill**：环境怎么装、多段怎么拼、字怎么叠，都写在 **`.cursor/skills/`** 里。你在 Cursor 里用自然语言描述需求，更容易对上「该跑哪条命令、注意哪些坑」。

下面只写**有效、且我后面还会保留**的部分；试错过又扔掉的过程，就不占篇幅了。

---

## 先放地址：克隆就能用

**开源仓库（含全部 Skill 与脚本）：**  
[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)

```bash
git clone https://github.com/maggie1030/auto-cut-xinwenti.git
```

用 **Cursor** 打开 **`auto-cut-xinwenti` 整个文件夹**（不要只打开里面的 `video-pipeline`），这样项目自带的 Skill 才会跟着工程走。

---

## 这套 Skill 组合，到底能帮你干什么？

可以概括成三件事（对应仓库里三个 Skill）：

**1. 新机器不懵：`video-pipeline-env-init`**  
告诉你先 `cd video-pipeline`，再 `npm install`、`npm run setup`、装 Pillow、`npm run check`——**先把「能出片」的环境对齐**，避免缺这缺那。

**2. 多段竖屏 + 一条口播，时长一次对齐：`vertical-montage-dt-fit`**  
多段素材按顺序接成一条竖屏成片，**用口播长度定成片时长**，画面用 **`setpts` 做 D/T 对齐**，**口播不断、不靠一大段静音硬凑**。顺带处理竖屏里常见的 **旋转 / Display Matrix**，减少「手机上正、导出又歪」的坑。

**3. 成片上叠「新闻体」四块固定字：`news-caption-overlay`**  
在**已经有的竖屏成片**上，叠一层**整段不变**的版式：**白底主标题、橘黄第二行、墨蓝第三行、底部白字黑边左对齐**（文案每条不同，版式一致）。用 **Pillow 画透明 PNG + ffmpeg overlay**，不依赖带 `drawtext` 的 ffmpeg。文案推荐写进 **`copy/caption-jobs/*.json`**，**一条 `--job` 命令**出带字成片。

---

## 关键设计（我刻意坚持的几点）

**1. 文案和「焊进视频」分开**  
可变内容放在 **JSON 任务文件**里；脚本只负责版式和合成。以后改一句字，**改文件再跑一条命令**，不用在 Skill 里改广告词。

**2. 叠字和时间轴「槽位字幕」不是一条路**  
仓库里另有按时间段换文案的烧录链路；**新闻体这种「盖一整条」**，单独脚本 **`burn_news_style_caption_overlay.py`**，避免概念混在一块。

**3. Skill 不写死某一条片的台词**  
Skill 只写：**什么时候用、进哪个目录、跑哪条命令、自检什么**。具体句子永远在 **JSON** 或你和 AI 的对话里。

---

## 实际操作：大概 15 分钟能跑通第一遍

（时间按「素材已准备好、网络正常」粗估；你熟的话可以更快。）

### 第 1 步：下载项目（约 1 分钟）

```bash
git clone https://github.com/maggie1030/auto-cut-xinwenti.git
cd auto-cut-xinwenti
```

用 **Cursor** 打开 **`auto-cut-xinwenti` 根目录**。

### 第 2 步：装环境（约 5 分钟，只做一次）

```bash
cd video-pipeline
npm install
npm run setup
pip3 install -r requirements-bake.txt
npm run check
```

`npm run check` 里若还有红字，按提示把 **Node / ffmpeg / Python / 字体** 补齐即可。

### 第 3 步：拼出一条竖屏成片（约 5 分钟）

把竖屏视频放进 `assets/video/`，口播放进 `assets/audio/`（可以是带画面的 mp4，脚本用里面的**声音**）。

仍在 `video-pipeline` 目录下执行（文件名换成你自己的）：

```bash
python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos assets/video/第一段.mov assets/video/第二段.mov \
  --audio assets/audio/口播.mp4 \
  --out out/第一步成片.mp4 \
  --workdir out/_work/任务1
```

到 `out/` 里找 **`第一步成片.mp4`**。

### 第 4 步：叠上新闻体四行字（约 3 分钟）

1. 复制 `copy/caption-jobs/caption-job.example.json`，改个名，例如 `我的单集.json`。  
2. 编辑里面的 **`in`**（上一步的 mp4）、**`out`**（输出文件名）、**`line1`～`line3`、`bottom`**。  
3. 执行：

```bash
python3 scripts/burn_news_style_caption_overlay.py \
  --job copy/caption-jobs/我的单集.json
```

终端出现 **已导出** 一类提示，就在 `out/` 里打开**带叠字**的成片。

---

## 和 Cursor 怎么配合？

你不用背上面每一条命令。在 Cursor 里说清楚，例如：

- 「按仓库里竖屏口播对齐的方式，帮我拼一下这几段素材」  
- 「在 `out/xxx.mp4` 上加新闻体那种四行叠字，文案是……」

AI 会优先去读 **`.cursor/skills/`** 里的说明，帮你补路径、提醒先 `cd video-pipeline`。

---

## 小结

- **没有**「先下几个 G 本地模型」这种门槛；核心是 **ffmpeg + Python +（叠字时）Pillow**。  
- **没有**「在文档里一行行抠口误」这种流程；这条线是 **工程向的剪接与固定版式叠字**，口播内容你自己把控即可。  
- **有**的是：**可克隆的仓库 + 三个 Skill + JSON 改字**，适合想**批量、可复现**做新闻体竖屏的人。

如果你已经 clone 跑过一遍，欢迎在评论区说说**哪一步最卡**、你希望下一步加什么能力（例如更多版式参数化），我后面迭代会优先参考真实反馈。

---

**仓库再贴一次：**  
[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)
