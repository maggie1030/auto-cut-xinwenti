# Cursor Skill 套件：能做什么 & 我是怎么一步步做出来的

本文是**总结性说明**：先说明本仓库里**每个 Skill 能帮用户/AI 完成什么**；再按**真实搭建顺序**，记录从想法到「可写进 `.cursor/skills/`」的路径，方便你以后复刻或改稿发公众号。

**项目仓库：** [https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)

---

## 一、本仓库里这三个 Skill，分别能实现什么

Cursor 的 Skill 本质是：**项目里的一份 Markdown 说明书**（带 YAML 头），让 AI 在匹配到场景时，按同一套规范去跑命令、少踩坑。下面说的是**背后脚本/流程能做什么**，Skill 负责把这些「何时用、怎么跑」写清楚。

### 1. `video-pipeline-env-init`（环境初始化）

**能实现：**

- 新电脑或刚 `git clone` 之后，把 **video-pipeline** 跑通所需依赖对齐：Node、`ffmpeg`/`ffprobe`、`jq`、Python、**Pillow**（叠字/字幕 PNG 用）、中文字体（如 Noto）等。  
- 按顺序执行：`cd video-pipeline` → `npm install` → `npm run setup` → `pip3 install -r requirements-bake.txt` → **`npm run check`**，根据自检结果补漏。  
- 用 **`npm run bootstrap-demo` + `npm run render:demo`** 做「第一条演示成片」冒烟；或用 **`copy/` 下单集 JSON** 走 `validate` + `npm run render` 出自有素材成片。  
- 明确告诉 AI：**不要无故删用户 `assets/` 里已有素材**；Whisper 可选、Pillow 不可缺等边界。

**一句话：** 解决「机器装好了没有、能不能先出一条片」。

---

### 2. `vertical-montage-dt-fit`（竖屏多段 + 口播整条对齐）

**能实现：**

- 把**多段竖屏（或带旋转信息的）视频**按 **`--videos` 顺序**整段接成一条；统一 **1080×1920**，处理旋转与 **Display Matrix**，避免播放器二次转歪。  
- 用**一条口播**定成片时长：拼接总时长为 **D**、口播有效时长为 **T**，默认对整条画面做一次 **`setpts`**，使画面与口播 **D/T 对齐**，**口播不断、不靠静音硬凑满时长**（默认不传 `--video-speed` 时自动算倍速）。  
- 每次任务用独立 **`--workdir`**，中间文件不互相踩。  
- **默认不加 `--overlay`**：成片可以只有画面+口播；叠营销大字用另一条链路（见下一条）。

**一句话：** 解决「多段 B-roll + 一条口播，时长对齐、竖屏规范导出」。

---

### 3. `news-caption-overlay`（已有成片上叠「新闻体」四块固定字）

**能实现：**

- 在**已经有的竖屏成片**（常见 **1080×1920**）上，叠一层**整段不变**的版式字（不是按时间轴一句句换的那种字幕）：  
  - **主标题**：白底圆角条 + 黑字、居中靠上；  
  - **第二行**：橘黄字 + 白描边、居中；  
  - **第三行**：墨蓝字 + 白描边、居中；  
  - **底部**：白字 + 黑描边、左对齐，多行（常写「学员：……」）。  
- 技术路线：**Pillow 画全帧透明 PNG + ffmpeg overlay**（兼容没有 `drawtext` 的 ffmpeg 构建）。  
- **文案可变、版式固定**：推荐用 **`copy/caption-jobs/*.json`** 写 `in` / `out` / 四段字，一条命令 **`--job`** 出片；有音轨则 **audio copy**。  
- 字体：优先**新青年体**（环境变量 **`XINQING_FONT`**）；没有则回退 **Noto Sans CJK**。

**一句话：** 解决「同一条视觉模板，每条片子只改字、一键烧进成片」。

---

## 二、Skill 在工程里长什么样（共用知识）

每个 Skill 一个文件夹，里面至少一个 **`SKILL.md`**，开头类似：

```yaml
---
name: 英文短名
description: >-
  一段话：做什么、何时用、关键词（方便 Cursor 匹配）
---
```

正文里写：**何时用、依赖、入口脚本路径、推荐命令、跑前跑后自检、常见报错**。  
**不要把某一条广告的逐字稿写死在 Skill 里**——可变内容放在 **JSON** 或对话里由人/AI 填。

---

## 三、我是怎样一步步做成这套 Skill 的（制作回顾）

下面按**逻辑顺序**写「从 0 到有」，其中 **「加新闻体叠字」** 是你后来重点迭代的一条，步骤写得最细；另外两条是**同一仓库里、与主 README 配套的 Agent 操作摘要**，制作思路一致：**先有稳定脚本，再把「怎么调用」固化成 Skill**。

### 第 0 步：先有「能跑的流水线」，再谈 Skill

- 仓库里 **`video-pipeline/`** 已经有一套 **ffmpeg + Python** 的主路径：拼接、音轨、用 PNG 烧字幕（`bake_overlay_subtitles.py` 等）、以及竖屏 **`render_fixed_fullscreen_overlay.py`**。  
- **Skill 不能代替脚本**：Skill 只是教 AI/人「去哪跑、注意什么」；所以一定是 **脚本先能跑通**，再写 Skill。

### 第 1 步：把「新机器 / 克隆后」固定成 `video-pipeline-env-init`

- **动机：** 每次换电脑都要重复：装 Node、ffmpeg、Pillow、`npm run check`，容易漏步。  
- **做法：** 把 **`video-pipeline/README.md`** 里的顺序，浓缩成 Agent 可执行的 checklist（`cd`、install、setup、pip、check、演示链 vs 自有 JSON），并写清**禁止乱删 `assets/`** 等。  
- **产出：** `.cursor/skills/video-pipeline-env-init/SKILL.md`（可加 `reference.md` 放各系统安装命令表）。  
- **结果：** 用户说「克隆了 / 环境装不好 / check 挂了」，AI 能按一条线排查。

### 第 2 步：把「竖屏多段 + 口播 D/T」固定成 `vertical-montage-dt-fit`

- **动机：** `render_fixed_fullscreen_overlay.py` 参数多（`--videos`、`--audio`、`--workdir`、是否 `--overlay`、是否手调 `--video-speed`），最容易错的是**工作目录**和**误加 overlay**。  
- **做法：** 在 Skill 里写死约定：**必须先 `cd video-pipeline`**；**默认不加 `--overlay`**；**`--workdir` 每任务单独目录**；默认 **D/T** 与「口播不断」的对应关系。  
- **产出：** `.cursor/skills/vertical-montage-dt-fit/SKILL.md`。  
- **结果：** 用户说「竖屏拼接、口播对齐、D/T、test1 那种成片」，AI 能直接套命令模板。

### 第 3 步：明确「新闻体叠字」和「槽位时间轴字幕」不是一回事

- **动机：** 仓库里已有 **按时间段换槽位** 的 `bake_overlay_subtitles.py`；你要的是**整条片盖一层固定版式**（主三行 + 底部块），版式、坐标、字号比例都有视觉稿级的要求。  
- **做法：** 单独做脚本，**不混进** `bake_overlay_subtitles` 的时间轴逻辑；Skill 里也写一句「与按槽位切换的字幕不同」，避免以后 AI 选错脚本。

### 第 4 步：实现 `burn_news_style_caption_overlay.py`（能力先于 Skill）

- **动机：** 把「白底标题 / 橘黄行 / 墨蓝行 / 底部学员块」画在一张 **与视频同分辨率的透明 PNG** 上，再 **ffmpeg overlay** 全程盖住。  
- **做法要点：**  
  - 字号按**画面高度比例**算，避免「手机 12px」那种和成片不匹配。  
  - 主三行居中、底部左对齐；多行用**像素宽度**折行。  
  - 字体复用 **`render_fixed_fullscreen_overlay.py`** 里的 **`discover_overlay_font()`**（新青年体 + 回退 Noto），避免两套探测逻辑。  
- **产出：** `video-pipeline/scripts/burn_news_style_caption_overlay.py`。

### 第 5 步：把「写文案」和「烧进视频」拆开——加 `--job` JSON

- **动机：** 每条片子字不同，但不想每次手拼一长串 CLI；希望**一个 JSON 文件 = 一条任务**，方便保存、对比、复跑。  
- **做法：**  
  - 约定 JSON 字段：`in`、`out`、`line1`～`line3`、`bottom`，可选 `workdir`。  
  - 脚本支持 **`--job path.json`**；路径**相对执行命令时的当前目录**（约定在 `video-pipeline` 下跑）。  
  - 提供模板 **`copy/caption-jobs/caption-job.example.json`**。  
- **产出：** 脚本扩展 + 示例 JSON；以后新单集 = **复制模板改字**。

### 第 6 步：写 `news-caption-overlay` 这个 Skill

- **动机：** 让 Cursor 在用户说「新闻体叠字、四行标题、学员块、`--job`」时，自动读**正确脚本**和**自检项**（Pillow、`XINQING_FONT`、`in` 是否存在等）。  
- **做法：** 新建 `.cursor/skills/news-caption-overlay/SKILL.md`：`description` 里堆触发词；正文里写**唯一入口脚本**、**推荐 `--job` 命令**、可选纯 CLI、跑前跑后、常见错误表。  
- **产出：** 与 `vertical-montage-dt-fit` 同一风格，Agent 行为一致。

### 第 7 步：进 Git、上 GitHub，别人 `clone` 就能用同一套 Skill

- **动机：** 换电脑、分享给别人，**一句话克隆**即可拿到 `.cursor/skills/` + 脚本。  
- **做法：** 仓库根 `.gitignore` 忽略大 **`out/`** 和个人 **`assets`** 素材，只推代码与 Skill；根 **`README.md`** 里链到进阶文档。  
- **产出：** 例如 [maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)。

### 第 8 步（可选）：再写「给新手看的公众号版 SOP」

- **动机：** Skill 是给 AI 的；公众号读者需要**更短、更少术语**的操作清单。  
- **做法：** 单独一篇 **`docs/公众号-新闻体剪辑与Cursor-Skill-SOP.md`**，只保留：下载 → 装环境 → 拼片 → 叠字，四步。  
- **与本文关系：** **本文**偏「我做了什么能力 + 我怎么做成 Skill」；**公众号那篇**偏「读者照着点哪里」。

---

## 四、以后你要再做「第 N 个 Skill」时可以照抄的清单

1. **脚本或命令先能稳定跑一遍**（最好一条命令 + 明确工作目录）。  
2. **可变内容**尽量 **JSON / 环境变量 / CLI**，不要写死在 Skill 正文。  
3. 在 **`.cursor/skills/名字/SKILL.md`** 写：`description`（触发词写全）+ 依赖 + 入口路径 + 推荐命令 + 自检 + 报错表。  
4. 和现有 Skill **分工写清楚**（像 `env-init` vs `vertical-montage` 那样），避免 AI 混用两条链路。  
5. **推 Git**，别人克隆整个仓库即带走 Skill。

---

**仓库地址：** [https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)
