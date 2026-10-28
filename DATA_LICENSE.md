# 数据来源与许可

来源：Inside Airbnb，Madrid，2026-09-17 快照目录。官方下载页：https://insideairbnb.com/get-the-data/ 。数据政策：https://insideairbnb.com/data-policies/ 。原始文件 URL、字节数与 SHA-256 见 results/source_manifest.json。目录日期不同于数据行内实际采集日期（2026-09-19 至 22）。

公开评论片段与派生数据按 CC BY 4.0 标注来源：https://creativecommons.org/licenses/by/4.0/ 。本项目独立完成筛选、抽样、清洗、语言识别、主题和情绪分析、片段选择，并添加 AI 辅助中文释义；不代表来源方背书。

examples/reviewed_cases.json 仅保留五个已逐段检查的西语短片段、必要上下文、展示编号、保存的判断与模拟建议，不含姓名、联系方式、精确地址、原始评论或房源 ID。片段仍可能通过公开搜索关联原评论，不能声称不可重识别。TS 编号是展示用标注编号。

完整原始文件、数据库、评论全文、私有标注、ID 映射与模型权重不随仓库分发。请自行从官方取得来源文件，遵守数据政策。MiniLM 模型源仓库为 sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2，下载脚本固定 revision；模型许可为 Apache-2.0。第三方依赖保留各自许可。本文件不为项目源代码授予软件许可。
