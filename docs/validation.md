# MVP 验证记录

日期：2026-10-15。环境：Windows，Python 3.14.2，项目独立 `.venv`。

- `python -m pytest -q`：11 passed。覆盖投影距离单位、风险叠置、预算、风险开关、数值规划、基线一致性、空结果、参数拒绝、API 和 GeoJSON。
- `python evaluate.py`：单角色 6/6，多角色 6/6，均为合成规则用例，非真实行业任务准确率。
- `node --check app/static/app.js`：通过。
- 网页实测：默认分析 12 个铺位，4 个符合条件；预算改为 1000 元后变成 0 个；恢复 20000 元后回到 4 个。
- 网页实测：执行轨迹显示 Planner、DataAgent、SpatialAgent、Verifier。
- GeoJSON 后端结构验证通过；浏览器下载事件验证超时，实际下载文件落盘未确认。
- Docker 构建和 GitHub Actions 未执行，本机没有可用 Docker 命令。
- 测试依赖产生一条 Starlette 关于 httpx TestClient 的弃用提示；不影响本次测试通过。

运行服务监听 `127.0.0.1:8765`。后续可双击项目内 `start.cmd`。不包含 API Key 或外部模型调用。
