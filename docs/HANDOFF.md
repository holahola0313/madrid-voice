# 发布交接

2026-10-28：从既有网页整理公开副本，未重新开发。目标为 holahola0313/madrid-voice（公开）。已完成文件白名单、README、依赖说明、三张截图、五个真实短片段与72行聚合评估。完整网页的私有输入与冻结校验保留，不承诺克隆即可启动。

验证：作者原项目38项软件测试通过；公开副本6项SQL与10项规则测试通过，示例读取成功。没有重跑模型或修改人工参考。上传状态以GitHub仓库实际文件为准。


## 2026-10-28 上传状态

已创建公开仓库 https://github.com/holahola0313/madrid-voice 。GitHub连接器能读取仓库，但create_file/create_blob返回403 Resource not accessible by integration；installed_accounts为空。本地Git推送连接被重置，没有确认上传成功。待用户将GitHub应用授权到该新仓库后继续提交，不能把空仓库写成已发布。

本地发布副本为相邻的madrid-voice-github目录，main分支，origin已设置，71个审查后的文件。作者原项目不初始化Git，以免误上传私有数据。发布范围、测试及完整网页不可直接克隆运行的限制见README、RUN_LOCAL和RELEASE_AUDIT。
