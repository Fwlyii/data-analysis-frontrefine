# 答辩材料

- `defense_slides.pdf`：12页，覆盖研究问题、实验设计、五条发现、系统与解释范围。
- `research_demo_340s.mp4`：约5分40秒、1920×1080、25fps的研究结果汇报；画面使用实际图稿，旁白由本机语音合成，不是网页录屏。
- `research_demo.srt`：与章节对应的标题字幕。
- `current_slide_content.json`、`defense_slides.md`：页面内容与讲稿。
- `current_video.json`：视频与来源信息。

制作脚本：scripts/delivery/build_course_documents.py、scripts/delivery/build_course_video.py。文档依赖requirements/documents.txt，视频依赖requirements/video.txt与Poppler；本机旁白生成使用macOS say。
