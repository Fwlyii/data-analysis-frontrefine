# GitHub Pages 部署

## 工作原理

源码保存在 GitHub 仓库。每次推送到 `main`，GitHub Actions 在临时机器上运行现有 Python 构建器，将 HTML、CSS、JavaScript、SVG 和匿名展示数据整理到 `app/dist/`，再交给 GitHub Pages 托管。用户浏览器从固定 HTTPS 网址下载这些文件并执行前端交互。

这不占用当前工作环境的 8766 端口，也不需要当前环境一直开机。Python 只在构建阶段运行；线上没有业务 API、数据库或模型请求。网站部署范围是 `app/dist/`，不是整个项目目录。

## 首次启用

1. 确认使用账号对目标仓库具有管理 Pages 的权限，并且账号方案和仓库可见性支持 Pages。不要为启用 Pages 自动更改仓库可见性。
2. 将 `.github/workflows/pages.yml` 与相关源码推送到目标仓库的 `main` 分支。
3. 打开仓库 **Settings → Pages → Build and deployment**，将 **Source** 设为 **GitHub Actions**。
4. 在 **Actions → Deploy visualization to GitHub Pages** 选择 **Run workflow**，分支选 `main`。
5. 等待工作流成功，从部署结果或 **Settings → Pages** 打开实际网址。

当前 Git 远程仓库为 `Fwlyii/data-analysis-frontrefine`，默认项目网址预计为 `https://fwlyii.github.io/data-analysis-frontrefine/`。自定义域名或仓库迁移可能改变地址，以 GitHub 实际部署结果为准。

## 日常更新

修改 `app/src/`、`app/styles.css`、`app/story.css`、HTML 或现有网页数据文件，提交并推送到 `main`。Actions 会重新构建和发布，无需手动维护 `dist` 内的生成文件。工作流成功后刷新页面；必要时强制刷新缓存。

本地预览仍可运行：

```bash
python3 app/launch.py --port 8766
```

服务器运行期间，本地修改后的手动构建命令：

```bash
python3 app/pipeline/scripts/system/build_web_app.py
```

## 仅在当前仓库使用的 SSH 凭据

当前工作环境为这个仓库生成了专用 Ed25519 密钥，保存在 `.git/keys/github-pages-ed25519`，公钥为同名 `.pub` 文件。私钥不在版本控制内。`.git/config` 中的 `core.sshCommand` 只让本仓库使用这个密钥，`origin` 使用 SSH 地址；未修改全局 Git 配置或 `~/.ssh/config`。

仓库管理员需打开 GitHub 仓库 **Settings → Deploy keys → Add deploy key**，粘贴 `.pub` 文件中的完整公钥，并勾选 **Allow write access**，使当前环境能够推送部署工作流。公钥可以展示；私钥不应复制到 GitHub、项目源码或聊天。

授权后在仓库根目录执行 `git ls-remote origin HEAD` 检查连接。这个部署密钥只能访问授权的单个仓库；Pages 的首次 Source 设置仍需由仓库管理员在 GitHub 网页完成。密钥限制 GitHub 仓库访问范围，操作系统的目录权限控制本机私钥文件访问。

配置使用当前目录的绝对路径；移动项目目录后需更新本仓库的 `core.sshCommand`。要撤销服务器访问，在仓库的 Deploy keys 中删除对应公钥即可。本地变更前的连接配置保存在 `.git/keys/github-config-before.json`。

## 部署检查

- 工作流只需要 Python 标准库，不安装分析依赖，也不重新采集模型回答或执行生成代码。
- 发布目录约 60 MB，包含完整图表库的匿名记录。大数据脚本首次打开可能比首页慢。
- 页面和资源使用相对路径，可以从项目子目录访问；项目网址末尾保留 `/`。
- 如果配置 Pages 阶段报错，检查 Pages 是否已启用、Source 是否为 GitHub Actions，以及账号方案与组织策略。
- 如果推送报权限错误，先在当前环境连接有仓库写权限的 GitHub 账号。不要把令牌写入代码、工作流或聊天。
- 若网页仍旧，确认最新提交对应的工作流已经成功，并检查实际部署网址与浏览器缓存。

官方文档：[GitHub Pages 概述](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[自定义部署工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。
