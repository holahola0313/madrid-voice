# 运行与复现

## 公开示例

Python 3.12 下执行 `python examples/read_cases.py`，无需安装依赖。输出五个已检查的真实短片段和原来保存的主题/情绪判断。标签基于原整条评论，不能把短片段重新推理结果当作原模型输出。示例没有原始 ID、精确地址、完整正文或 Excel，不能连接回完整看板。

## 本机完整网页

作者本机已有完整输入，日常双击 start_dashboard.cmd，或在项目目录执行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

地址 http://127.0.0.1:8501/ 仅限本机，关闭进程即停止；不是公开演示链接。

新机器安装界面依赖：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
```

这只安装软件，不能生成缺失的私有输入。完整网页必须恢复：

- data/processed/madrid_voice.sqlite。
- data/stage4/compact/scope.json、development_accepted_v1.json、test_accepted_v1.json、test_blind.json、test_predictions_frozen_v1.json。
- outputs/stage4/compact_method_freeze.json、development_diagnostics.json、evaluation/metrics.json；outputs/stage3/run_manifest.json；outputs/stage5/input_manifest.json。
- compact_method_freeze.json 与 input_manifest.json 中 hashes 列出的所有其他文件，逐个满足原 SHA-256。其代码、配置和协议已经保留在仓库。

上述数据来自作者原工作目录的私有备份，不随公开仓库提供，也不承诺提供。不要删除 manifest、修改哈希、用示例代替全文、重新生成“人工答案”，或反复运行冻结脚本来让校验通过。原校验失败会停止网页，这是保留的保护行为。精确恢复后可用 `python -c "from dashboard.data import verify_frozen; verify_frozen()"` 检查，再运行完整测试。

## 从官方数据准备研究输入

在新的独立克隆目录执行，不能覆盖作者现有项目。此路径可以重做阶段一至三的输入处理与预测，不能重建作者人工标注、随机 ID 密钥或相同字节的原 SQLite。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-stage3.txt
.\.venv\Scripts\python.exe scripts/download.py
.\.venv\Scripts\python.exe scripts/audit.py
.\.venv\Scripts\python.exe scripts/check_duplicates.py
.\.venv\Scripts\python.exe scripts/finalise_audit.py
.\.venv\Scripts\python.exe scripts/verify_outputs.py
.\.venv\Scripts\python.exe scripts/build_stage2.py
.\.venv\Scripts\python.exe scripts/download_stage3_model.py
.\.venv\Scripts\python.exe scripts/run_stage3.py
.\.venv\Scripts\python.exe scripts/verify_stage3.py
```

首次下载约 186 MB 压缩数据，另需固定 MiniLM 模型及依赖。数据下载后先对照 results/source_manifest.json 的字节数与 SHA-256，任何差异都应停止，不能将不同快照冒充原实验。发布整理本轮没有重新联网下载或全量重跑这条流水线；如同一快照下架，应记录无法取得。下载脚本固定官方 URL；模型下载脚本固定 revision。

build_stage2.py 为 ID 映射生成新的随机私有密钥，因此独立重建的 ID 和数据库指纹不同；人工参考无法程序再生。阶段一至三输出不足以启动本次依赖冻结人工输入的完整看板，不能靠重跑 prepare_stage5.py 解决。公开聚合指标用于查看已报告结果；公开示例用于检查真实案例，不宣称完整评估可独立复算。

## 软件测试

公开副本无需私有数据的既有检查：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stage2_sql.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_stage3_rules.py
```

其余测试依赖作者私有输入、冻结文件或历史产物，不应在干净克隆中期待完整 38 项通过。作者原项目本轮完整 38 项通过；公开副本单独验证 SQL 与规则测试。这些测试使用软件夹具，不是新增人工标注或模型效果。

## 依赖

requirements-dashboard.txt：网页最小直接依赖。requirements.txt：语言识别。requirements-stage3.txt：ONNX CPU 推理。requirements-stage4.txt：Excel 校验。requirements-stage5.txt：历史网页与报告依赖（本次不制作报告）。版本清单保留，未绕过冻结链改写旧依赖文件。没有付费 API，不需要配置令牌。独立环境安装本轮未重新执行；原环境及公开示例检查结果见发布审查。
