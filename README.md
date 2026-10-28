# Madrid Voice

基于西班牙语评论的住宿体验分析与运营诊断。南开大学西班牙语与数据科学双学位本科生的个人作品，采用模拟业务场景，没有企业合作或真实运营效果。

帮助住宿运营人员发现体验问题、查看西语原文依据，并整理需要核查的事项。网页第一版已完成：**首页、评论分析、主题分析、核查清单、方法说明**。

![西语评论分析首页](docs/images/home.jpg)

## 真实案例

> lo unico el aire acondicionado que tenia un ruido extraño, de resto todo perfecto

空调异响案例中，整体好评包含具体设施与噪音问题。作者人工参考为负面；关键词规则对设施情绪不确定，本地 AI 对设施判为正面。页面并列展示原文、中文释义、判断依据与模拟核查建议。中文释义均标为“AI辅助，尚未经作者复核”。

[评论分析截图](docs/images/review.jpg) · [主题分析截图](docs/images/topics.jpg) · [五个公开短片段案例](examples/reviewed_cases.json)

核查清单支持添加、去重、移除及 CSV 导出，只保存在当前浏览器会话，刷新可能丢失。建议属于待核查事项，不表示已派单或已解决。

## 技术与数据

Python 3.12、SQLite、Streamlit、Plotly。六个主题为清洁、噪音、入住、设施、沟通和位置；主题提及与情绪分开，允许多标签、混合及不确定判断。

- 来源：[Inside Airbnb Madrid](https://insideairbnb.com/get-the-data/)，2026-09-17 快照目录；实际采集日期为 2026-09-19 至 22。
- 分析窗口：2025-09-01 至 2026-08-31。固定抽样 10,000 条，隔离 879 条归属冲突记录，保留 9,121 条；保守语言识别得到 3,763 条西语候选，覆盖 2,770 套房源。“候选”未经全量人工确认。
- 规则：`rules-v1.0.0`。本地 AI：`minilm-prototypes-v1.0.0`，MiniLM 句向量与 36 个西语原型匹配，没有付费 API，也不是自行训练的大模型。
- 数据许可：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。本项目进行了抽样、清洗、语言筛选、主题分析及片段选择，不代表来源方背书。详见 [来源与许可](DATA_LICENSE.md)。

## 实际评估

作者完成 30 条试标、20 条开发、30 条独立测试，共 80 条。属于单人参考标注；部分边界借助 AI 核对指南，再由作者确认，不是双人金标准。测试预测在标注前冻结，没有据测试答案调整方法。

30 条测试中，设施负面内容（含混合情绪）有 5 条：规则检出 0 条，本地 AI 检出 1 条。保留漏判结果，小样本不足以证明方法普遍可靠。[完整评估](docs/TEST_EVALUATION.md) · [错误分析](docs/TEST_ERROR_ANALYSIS.md) · [72 行原始聚合指标](results/metrics.json)。

预测线索不等于真实投诉率；评论数量不等于订单量，不可预订天数不等于入住天数，不作运营改善或因果推断。五个展示案例为有目的选择，不能用于估计总体频率。

## 使用方式

**公开仓库提供源码、截图、真实短片段与聚合评估，不包含完整网页所需的私有数据库和冻结人工输入。克隆后不能直接启动完整看板。**

无需第三方依赖，即可读取经过检查的真实示例与保存的判断（不会运行模型，也不会重新评估）：

```powershell
python examples/read_cases.py
```

安装基础语言依赖后，可运行不依赖私有输入的既有 SQL 与规则软件测试：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stage2_sql.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stage3_rules.py
```

完整看板环境安装、私有输入恢复与官方数据准备步骤见 [RUN_LOCAL.md](RUN_LOCAL.md)。原冻结校验完整保留；公开示例不能替换原数据库或人工答案，也不能复原本次完整 30 条评估。

本机已有完整输入时，安装 `requirements-dashboard.txt` 后，双击 `start_dashboard.cmd`；或：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

`http://127.0.0.1:8501/` 仅是本机地址，不是在线演示。本次未部署公网网站。

## 作者与 AI 分工

作者确定项目方向、选择视觉方案，完成 80 条人工参考标注并确认边界修订。AI 辅助编写代码、SQL、测试、文档、界面与中文释义，并协助按指南复核部分标注边界。模型预测、作者人工参考与 AI 辅助译文分别标识；AI 生成的解释不算新增人工核验。

## 验证与发布范围

2026-10-28 原项目完整 38 项既有软件测试通过（12.689 秒）。这是软件功能验证，不是模型准确率或用户计时结果。公开仓库可独立运行的检查见上述两条命令；其余测试依赖保留在作者本机的冻结输入。

详见 [发布审查](docs/RELEASE_AUDIT.md)、[交付索引](DELIVERY.md)。源代码暂未单独授予开源软件许可；数据片段许可见 DATA_LICENSE.md。
