# 新闻体视频剪辑流水线

竖屏素材拼接、口播 D/T 对齐、新闻体固定叠字等脚本与 **Cursor 项目技能**（`.cursor/skills/`）。

## 克隆后

1. 用 Cursor 打开本仓库，技能会随项目加载。  
2. 剪辑与渲染见子目录 **`video-pipeline/`**（`README.md`、环境自检 `npm run check`）。  
3. 将自有画面/口播放入 `video-pipeline/assets/`，勿提交大文件；演示素材见各目录下的 `_demo/`。

## 技能一览（`.cursor/skills/`）

| 技能 | 用途 |
|------|------|
| `vertical-montage-dt-fit` | 多段竖屏 + 口播，`D/T` 画面变速对齐 |
| `news-caption-overlay` | 已有成片上叠新闻体四块固定文案（`--job` JSON） |
| `video-pipeline-env-init` | 新机器环境与依赖自检 |
