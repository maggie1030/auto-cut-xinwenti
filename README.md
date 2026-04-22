# 新闻体视频剪辑流水线

竖屏素材拼接、口播 **D/T** 对齐、固定转场、响度归一、新闻体四行叠字等脚本，以及 **Cursor 项目技能**（`.cursor/skills/`）。

## 功能与使用说明（主文档）

技术与流程的完整说明（技能对照、一键脚本、JSON 字段、自检与排错）见：

**[`docs/新闻体竖屏剪辑-Skill与流水线说明.md`](docs/新闻体竖屏剪辑-Skill与流水线说明.md)**

## 克隆后

1. 用 Cursor 打开本仓库，技能会随项目加载。
2. 渲染与目录约定见子目录 **`video-pipeline/`**（其内 [`README.md`](video-pipeline/README.md)、环境自检 `npm run check`）。
3. 将自有画面/口播放入 `video-pipeline/assets/`，勿提交大文件；演示素材见各目录下的 `_demo/`。

## 技能一览（`.cursor/skills/`）

| 技能 | 用途 |
|------|------|
| `final-news-video` | 视频列表 + 口播 + 四行文案，按技能串联出 **`out/<job>-final.mp4`** |
| `vertical-montage-dt-fit` | 多段竖屏 + 口播，**D/T** 对齐；推荐配合 `scripts/render_fixed_transitions_maxvol.sh` |
| `news-caption-overlay` | 已有成片上叠新闻体四行文案（`--job` JSON 或 CLI） |
| `video-pipeline-env-init` | 新机器环境与依赖自检 |
