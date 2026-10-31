# GitHub 动画检索与选型

核对日期：2026-10-31。针对现有原生 JavaScript 静态页面选型，生产环境不增加框架或 CDN。

| 候选与一手来源 | 判断 |
|---|---|
| [Motion](https://github.com/motiondivision/motion)、[animate 官方文档](https://motion.dev/docs/animate)、[MIT 许可](https://github.com/motiondivision/motion/blob/main/LICENSE.md) | 选定。`motion/mini` 直接控制浏览器原生动画，适合本次 transform/opacity 和可中断的导航标记。 |
| [Animate.css](https://github.com/animate-css/animate.css)、[当前许可](https://github.com/animate-css/animate.css/blob/main/LICENSE) | 适合预设入场。当前上游为 Hippocratic License，不能沿用旧印象写成 MIT；本次也需要由 JS 管理快速切换和动画取消，因此不选。 |
| [Anime.js](https://github.com/juliangarnier/anime)、[官方文档](https://animejs.com/documentation/) | 可做更复杂时间线，本次简单样式动画用不到这些能力，不增加另一套引擎。 |

选用锁定版本 `motion@14.9.0`，用 `esbuild@0.28.2` 仅打包 `animate` 导出。开发工具、锁文件与构建输入在 `tools/`、`research/motion-bundle-inputs.json`；运行文件为 `app/assets/vendor/motion-mini-14.9.0.min.js`，实际未 gzip 大小 **8,771 bytes**。官方 mini 体积口径与实际未压缩交付文件不能直接混写。MIT 声明连同被打包的 motion、framer-motion、motion-dom、motion-utils 版权声明保存到同目录 LICENSE 文件。

每次 Pages 发布使用已提交的本地脚本，不访问外部动画 CDN，也不在 CI 下载 npm 包。复现打包可运行：

```sh
npm ci --prefix optimization/type-motion-v2/tools --ignore-scripts
node optimization/type-motion-v2/scripts/bundle-motion.mjs
```

没有使用 Motion+ 付费示例代码，也没有执行检索仓库中的安装脚本。减少动态效果、页面隐藏、重复触发的处理属于本项目控制层，需要实际浏览器验收，不能因为引用库就默认正确。
