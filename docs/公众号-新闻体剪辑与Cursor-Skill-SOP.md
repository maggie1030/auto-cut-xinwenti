# 新手照着做：新闻体竖屏剪辑一条龙（超简版）

**一句话：** 先从 GitHub 把项目下载下来，装好环境，再按顺序「拼画面 → 叠四行字」，就能得到常见的「新闻体」竖屏成片。

**开源项目地址（复制给读者）：**  
[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)

---

## 开始前，你需要有什么

在电脑上先装好（不会装就搜教程，或问 Cursor 里 AI）：

- **Cursor**（推荐）或任意能打开文件夹的编辑器 + **终端**  
- **Git**  
- **Node.js**（官网下 LTS 版即可）  
- **Python 3**  
- **FFmpeg**（Mac 常用：`brew install ffmpeg`）

---

## 第一步：把项目下载到电脑

打开终端，执行（可以改最后一行文件夹名）：

```bash
git clone https://github.com/maggie1030/auto-cut-xinwenti.git
cd auto-cut-xinwenti
```

用 **Cursor** 打开 **`auto-cut-xinwenti` 整个文件夹**（不要只打开里面的 `video-pipeline` 小文件夹，否则自带的「技能说明」可能用不上）。

---

## 第二步：装剪辑环境（只做一次）

终端里依次执行：

```bash
cd video-pipeline
npm install
npm run setup
pip3 install -r requirements-bake.txt
npm run check
```

- **`npm run setup`**：会尝试帮你装系统里的 ffmpeg 等；有的电脑要你自己按提示用管理员权限装。  
- **`npm run check`**：检查还缺什么；**尽量看到没有报错**再继续。

想确认「真的能出片」，可以再跑（会生成演示小素材，**只用来试机器**）：

```bash
npm run bootstrap-demo
npm run render:demo
```

若最后生成了 `out` 里的演示 mp4，说明大方向没问题。

---

## 第三步：多段竖屏 + 一条口播 → 先拼出一条成片

把你的竖屏视频放进：`video-pipeline/assets/video/`  
把口播放进：`video-pipeline/assets/audio/`（可以是 mp4，只要有声音）

仍然在 **`video-pipeline` 目录里**，执行（把文件名改成你自己的）：

```bash
cd video-pipeline

python3 scripts/render_fixed_fullscreen_overlay.py \
  --videos assets/video/第一段.mov assets/video/第二段.mov \
  --audio assets/audio/我的口播.mp4 \
  --out out/成片第一步.mp4 \
  --workdir out/_work/任务1
```

**你要记住的三件事：**

1. 命令一定要在 **`video-pipeline` 文件夹里**跑。  
2. **`--videos` 谁先谁后，成片里就按这个顺序接。**  
3. **`--workdir` 每次换个名字**，避免和上次任务混在一起。

跑完后，到 `video-pipeline/out/` 里找 **`成片第一步.mp4`**。

---

## 第四步：在成片上叠「四行新闻体字」

版式已经写在程序里了（白底大标题、下面两行彩色描边字、最下面一块「学员」式旁白），**你只要改字**。

1. 复制这个文件，改个名：  
   `video-pipeline/copy/caption-jobs/caption-job.example.json`  
   例如改成：`copy/caption-jobs/我的文案.json`

2. 用记事本 / Cursor 打开你的 json，改这几项（路径按你实际文件名写）：

   - **`in`**：上一步生成的成片，例如 `out/成片第一步.mp4`  
   - **`out`**：叠字后的新文件，例如 `out/成片最终.mp4`  
   - **`line1`、`line2`、`line3`、`bottom`**：你的四段话

3. 还在 **`video-pipeline` 目录**，执行：

```bash
cd video-pipeline

python3 scripts/burn_news_style_caption_overlay.py \
  --job copy/caption-jobs/我的文案.json
```

终端里出现 **「已导出」** 一类提示，就去 **`out`** 里打开 **`成片最终.mp4`** 看效果。

**字体小提示：** 想更像海报上的粗字，可以自己装「新青年体」；不装也能跑，程序会用系统里的 Noto 中文字体代替。

---

## Cursor 里的「Skill」是干嘛的？（不用背）

这个项目里带了三个「技能说明」文件夹，在 **`.cursor/skills/`** 里。你可以把它们理解成：**给 AI 看的操作说明书**。

你在 Cursor 里用中文说「帮我按仓库里竖屏口播对齐的方式拼一下」「帮我在成片上加新闻体那种四行叠字」，AI 更容易按说明书里的命令帮你填路径、检查缺啥。

**你自己完全不用打开这些文件也能照上面四步做完**；Skill 主要是方便「问 AI 代劳」。

---

## 还不行时，先看哪里

1. 终端红色报错 → 把最后几行复制下来搜，或贴给 Cursor 里的 AI。  
2. 更细的说明在项目里：**`video-pipeline/README.md`**。

---

**仓库地址再贴一次：**  
[https://github.com/maggie1030/auto-cut-xinwenti](https://github.com/maggie1030/auto-cut-xinwenti)
