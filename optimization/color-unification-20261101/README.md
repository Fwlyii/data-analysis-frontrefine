# LENS · 深海蓝、雾蓝灰与香槟金配色统一

本轮针对开场/球体入口与研究页、图表库的暖米色风格断层，进行适中的颜色调整。电脑录制优先，1920×1080为主；保留上一轮已经优化的字体、布局、图表和开场。

[详细配色与检查报告](REPORT.md) · [逐页对照画廊](gallery.html) · [真实生图与完整提示](design/provenance.json) · [逐页账本](coverage-table.json) · [进度](STATUS.md)

## 设计角色

| 用途 | 颜色 | 使用方式 |
|---|---|---|
| 深海蓝 | `#071E30` / `#103347` | 沿用开场基调，用于原有研究标题区、图表库导航与选中状态 |
| 雾蓝灰 | `#EAF0F2` | 长内容阅读背景，减少原来的黄褐色倾向 |
| 冷白 | `#F8FAFB` | 方法、筛选、统计、详情卡片 |
| 蓝灰线 | `#CBD8E0` | 边框与分隔，降低杂乱感 |
| 香槟金 | `#D2BB96` | 深色区域中的少量序号、光学细节和选中提示 |
| 深金棕 | `#7A603E` | 浅底上需要可读对比度的小强调文字 |

科学图面继续使用原来的纸白/纯白和原有数据颜色。图表类别、坐标、科学高亮与导出不会被重涂成主题色。原有六份布局/样式文件和原JS、数据、字体、资产共533文件固定SHA-256；新配色集中在`app/palette.css`。

## 执行与复现

当前服务为8838端口，冻结d80769d基线为8839端口。冻结产物在`.git/color-unification/baseline-dist`，不写入产品。其他机器可用独立工作树构建d80769d并提供相同基线服务。

```sh
python3 scripts/system/build_web_app.py
python3 -m http.server 8838 --bind 127.0.0.1 --directory app/dist
```

完整检查入口：

```sh
python3 optimization/color-unification-20261101/scripts/run-review.py
```

依赖沿用`optimization/homepage-pilot/tools`中的锁定Playwright/Axe/Lighthouse、`/snap/bin/chromium`与FFmpeg。脚本不会推送。真实生图调用的原始记录已保存，普通截图不能冒充生图。

生产修改为新增配色层、两个真实入口接入和构建指纹。研究页只使用现有标题区承接深蓝，不增加旧侧栏或新导航。新增发布门禁检查颜色角色、实际字号/几何不变、科学SVG/样式/标准位置像素一致，以及真正的全路由浏览器证据。
