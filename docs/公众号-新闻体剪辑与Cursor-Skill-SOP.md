# 从 0 到可复用：新闻体竖屏剪辑流水线 + Cursor Skill 搭建 SOP

> 本文根据**新闻体竖屏成片**的实际搭建过程整理：如何把「环境安装 → 多段素材与口播对齐 → 固定版式叠字」固化成**可复制的工作流**，并用 **Cursor 项目级 Skill** 让 AI 助手按同一套规范执行。  
> 读者按步骤操作，即可在本地复现；**克隆开源仓库即可带走全部 Skill 与脚本**。

---

## 一、先把仓库地址给你（别人下载也能用）

**GitHub 开源地址（请收藏、转发时附上）：**

**[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)**

克隆一行命令：

```bash
git clone https://github.com/maggie1030/auto-cut-xinwenti.git
```

用 **Cursor** 打开克隆下来的文件夹，项目里的 **`.cursor/skills/`** 会随工程一起存在；与 AI 对话时，只要描述「竖屏拼接」「口播对齐」「新闻体叠字」等，模型会按 Skill 说明去跑对应脚本（具体触发取决于 Cursor 对 Skill 的匹配机制）。

---

## 二、这套方案到底解决了什么问题（核心理念）

在做「新闻体」短视频时，常见需求可以拆成三块：

| 模块 | 要解决的事 |
|------|------------|
| **环境** | `ffmpeg`、中文字体、Python、Node 等装齐，避免「换电脑就崩」。 |
| **画面与口播** | 多段竖屏 B-roll 按顺序用完，**整条画面时长对齐一条口播**，口播不中断、不靠大量静音去凑时长。 |
| **画面字** | 在**已有成片**上叠一层「主标题 + 两行强调 + 底部引语」固定版式，**每条片子文案不同**，但版式一致。 |

对应的设计原则（也是后面 Skill 要写的「规矩」）：

1. **工程路径与口播对齐**：用 `ffmpeg` + Python 脚本做主路径，不依赖浏览器渲染；部分 Homebrew 版 `ffmpeg` 没有 `drawtext`，因此采用 **Pillow 生成透明 PNG + overlay** 烧字，兼容面更广。  
2. **口播不断、画面一次变速对齐**：拼接总时长为 \(D\)，口播有效时长为 \(T\)，默认对整条画面做 **`setpts=PTS/(D/T)`**，不把静音当主手段拉长口播。  
3. **「写文案」和「把字焊进视频」分开**：可变内容放进 **JSON 任务文件**；烧录用 **一条命令** 读 JSON，便于版本管理和复跑。  
4. **Skill 只描述「何时、怎么跑」**：不把某一条广告的逐字稿写死在 Skill 里；具体句子放在 **job JSON** 或对话里由人/模型填写。

---

## 三、仓库里有什么（别人克隆后看到什么）

```
auto-cut-xinwenti/
├── README.md                 # 仓库总览
├── .gitignore                # 忽略大体积 out、个人 assets 等
├── .cursor/skills/           # Cursor 项目技能（核心「说明书」）
│   ├── video-pipeline-env-init/
│   ├── vertical-montage-dt-fit/
│   └── news-caption-overlay/
└── video-pipeline/           # 剪辑脚本、copy 配置、npm 自检等
    ├── scripts/
    ├── copy/
    │   └── caption-jobs/      # 叠字任务 JSON 模板与自建任务
    └── README.md
```

说明：为控制仓库体积，**个人大素材与 `out/` 成片默认不进 Git**；克隆后请把画面、口播放到本地 `video-pipeline/assets/`，成片输出在本地 `video-pipeline/out/`。

---

## 四、标准操作流程（SOP）：按顺序做即可

### 步骤 0：准备软件

- 安装 **Cursor**（或你惯用的 IDE + 终端）。  
- 安装 **Git**，能执行 `git clone`。  
- 建议安装 **Node LTS**、**Python 3**、**FFmpeg**（含 `ffprobe`、`libx264`）。

### 步骤 1：克隆并打开工程

```bash
git clone https://github.com/maggie1030/auto-cut-xinwenti.git
cd auto-cut-xinwenti
```

用 **Cursor** 打开 **`auto-cut-xinwenti` 根目录**（不要只打开 `video-pipeline` 子目录，否则 `.cursor/skills` 可能不在工作区根，Skill 行为因 Cursor 版本/设置而异）。

### 步骤 2：初始化剪辑环境（对应 Skill：`video-pipeline-env-init`）

在终端执行：

```bash
cd video-pipeline
npm install
npm run setup      # 按脚本提示安装系统依赖（部分系统需自行 sudo）
pip3 install -r requirements-bake.txt
npm run check
```

- **`requirements-bake.txt`**：含 **Pillow**，叠字与部分字幕路径需要。  
- **`npm run check`**：自检 Node、ffmpeg、Python、字体等；按输出逐项补齐。

验收（二选一即可）：

- **演示链**：`npm run bootstrap-demo` → `npm run render:demo`（会生成/覆盖演示素材，仅用于验证环境）。  
- **自有素材**：把文件放入 `assets/video/`、`assets/audio/`，复制 `copy/examples/episode-001.json` 改路径与槽位，再按 `video-pipeline/README.md` 走 `validate` + `render`。

### 步骤 3：多段竖屏 + 口播 D/T 成片（对应 Skill：`vertical-montage-dt-fit`）

**入口脚本：** `video-pipeline/scripts/render_fixed_fullscreen_overlay.py`

**硬性习惯：**

1. 必须先 **`cd video-pipeline`**，再用相对路径传 `--videos`、`--audio`、`--out`。  
2. **`--videos` 顺序 = 镜头顺序**；每段尽量已是或可规范为竖屏。  
3. **`--audio`** 用口播文件（可为带画面的 `.mp4`，脚本只用 **第一条音轨 `a:0`** 算时长 \(T\)）。  
4. **`--workdir`** 每次任务单独一个目录，避免中间文件互相覆盖。  
5. **默认不要加 `--overlay`**：那是另一套「脚本内写死的全屏文案」；新闻体营销叠字请用步骤 4 的专用脚本。

**推荐命令模板：**

```bash
cd /你的路径/auto-cut-xinwenti/video-pipeline

python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos assets/video/镜头1.mov assets/video/镜头2.mov \
  --audio assets/audio/口播.mp4 \
  --out out/我的成片.mp4 \
  --workdir out/_work/我的任务名
```

**默认逻辑：** 省略 `--video-speed` 时，自动 **\(D/T\)** 对齐口播；口播链不做「静音补满」式硬凑（与 Skill 文档一致）。

### 步骤 4：在成片上叠「新闻体」四块固定文案（对应 Skill：`news-caption-overlay`）

**入口脚本：** `video-pipeline/scripts/burn_news_style_caption_overlay.py`

**版式要点（与需求一致，便于你写教程或给客户看）：**

- 成片分辨率 **1080×1920**。  
- **主三行**：水平居中；竖直位置用「距顶比例」控制（脚本内已按该思路落版）。  
- **主标题**：白底圆角矩形 + 黑字。  
- **第二行**：橘黄色 + 白描边。  
- **第三行**：墨蓝 / 青蓝色 + 白描边。  
- **底部块**：白字 + 黑描边，**左对齐**，多行；文案常带「学员：」前缀。  
- **字体**：优先「新青年体」；未安装时脚本会回退 **Noto Sans CJK**，也可设置环境变量 **`XINQING_FONT`** 指向 `.ttf/.otf` 绝对路径。

**推荐用法：两文件、一条命令**

1. 复制模板：  
   `video-pipeline/copy/caption-jobs/caption-job.example.json`  
   另存为例如 `copy/caption-jobs/我的单集.json`。  
2. 编辑 JSON 里的 **`in`**（输入成片）、**`out`**（输出成片）、**`line1`～`line3`、`bottom`**，可选 **`workdir`**。  
3. 在 **`video-pipeline` 目录下**执行：

```bash
cd /你的路径/auto-cut-xinwenti/video-pipeline

python3 scripts/burn_news_style_caption_overlay.py \
  --job copy/caption-jobs/我的单集.json
```

**可选：** 不用 JSON 时，也可直接用 `--in` / `--out` / `--line1`…；**同一字段若 CLI 与 JSON 同时存在，以 CLI 为准**（方便临时试一句）。

**注意：** 本叠字是「**整条视频盖一层静态 PNG**」，与 `bake_overlay_subtitles.py` 那种「按时间段切换槽位」的字幕不是同一条链路；不要混用概念写教程。

### 步骤 5：自检与交付

- 终端出现 **`已导出:`** 即烧录命令成功；用播放器抽查字边、断行、与画面遮挡关系。  
- D/T 成片日志中应含 **Display Matrix 已处理** 等说明（以脚本实际输出为准）。  
- 交付客户时：成片 MP4 +（可选）本次使用的 **caption job JSON**，便于以后只改字再出片。

---

## 五、三套 Cursor Skill 分工一览（写进公众号的「速查表」）

| Skill 目录名 | 一句话用途 |
|--------------|------------|
| `video-pipeline-env-init` | 新机器 / 克隆后：**装依赖、`npm run check`、演示或自有 JSON 出片**。 |
| `vertical-montage-dt-fit` | **多段竖屏 + 一条口播**，\(D/T\) **整条 setpts** 对齐，默认不加 `--overlay`。 |
| `news-caption-overlay` | **已有竖屏成片**上叠 **四块新闻体固定文案**；推荐 **`--job` JSON**。 |

Skill 本质是 **Markdown 说明书**：告诉 AI「什么时候读哪条命令、注意哪些坑」；**不会替你执行命令**，执行仍在本地终端或由 Agent 代跑。

---

## 六、写公众号时可以加的「贴心提示」

1. **不要把账号密码发到聊天或文章里**；Git 推送用 **SSH** 或 **GitHub 登录 / PAT**，且 Token 仅保存在本机凭据管理器。  
2. **大素材不要进 Git**：仓库已用 `.gitignore` 忽略常见大文件路径；教程里提醒读者「素材只放本地 `assets/`」。  
3. **字体版权**：新青年体等商业字体需自行取得授权；教程可写明「演示用 Noto，商用换自有授权字体」。  
4. **口播与画面权利**：素材与口播的著作权、肖像权由使用者自行负责。

---

## 七、结语

把「环境 → 拼接对齐 → 叠字」拆成清晰步骤，再用 **Cursor Skill** 把步骤与命令模板写进仓库，任何人 **clone 同一地址** 都能得到同一套操作说明；你只需在 JSON 里换文案、在命令里换路径，就能稳定批量产出**版式统一、工程可复现**的新闻体竖屏视频。

**再次附上开源地址：**  
**[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)**

---

*文档版本：与仓库 `main` 分支内容对应；若脚本参数有更新，以仓库内 `SKILL.md` 与 `video-pipeline/README.md` 为准。*
