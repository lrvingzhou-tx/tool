# HR 数据处理工具

本仓库包含一个基于 Streamlit 的小型 HR 数据处理工具，支持员工入转调离数据合并、各级组织年度“月度沟通经费”计算和经费余额管理。以下文档对项目结构、安装、运行及使用流程进行了详细梳理。

**快速索引**
- **项目主页**: [ui/streamlimit_cal_ui.py](ui/streamlimit_cal_ui.py)
- **依赖清单**: [requirements.txt](requirements.txt)
- **启动脚本**: [scripts/run.sh](scripts/run.sh)
- **Makefile**: [Makefile](Makefile)
- **服务模块**: [service/cal_fee.py](service/cal_fee.py), [service/merge_info.py](service/merge_info.py)

## 一、项目简介

该工具面向 HR 数据处理场景，包含：
- 员工入转调离数据合并（识别正常/异常员工调动并导出 Excel）
- 根据员工薪资数据计算年度“月度沟通经费”明细与汇总
- 经费余额动态管理（手动登记多笔支出并计算余额）

前端为 Streamlit 单页应用，业务逻辑封装在 `service` 目录下，便于单元测试和复用。

## 二、仓库结构

- [ui/streamlimit_cal_ui.py](ui/streamlimit_cal_ui.py) — Streamlit UI 主程序
- [service/cal_fee.py](service/cal_fee.py) — 经费计算逻辑（入职/离职/调入/调出处理）
- [service/merge_info.py](service/merge_info.py) — 员工入转调离数据合并逻辑与导出
- [requirements.txt](requirements.txt) — Python 依赖列表
- [scripts/run.sh](scripts/run.sh) — 启动脚本（可配置 PORT/ADDRESS）
- [Makefile](Makefile) — 常用命令快捷入口（install/run）

## 三、环境与依赖

先决条件：系统需有 Python 3.8+（建议 3.10+），并能访问 PyPI 以安装依赖。

安装依赖：

```bash
make install
# 或者
python3 -m pip install -r requirements.txt
```

主要依赖：`streamlit`、`pandas`、`openpyxl`、`xlsxwriter`（参见 `requirements.txt`）。

## 四、启动应用

本地开发或容器内运行：

```bash
# 使用 Makefile
make run

# 或直接运行脚本（可通过 PORT 环境变量指定端口）：
PORT=8502 ./scripts/run.sh
```

默认监听地址为 `0.0.0.0:8501`（可通过环境变量 `ADDRESS`/`PORT` 覆盖）。启动后在浏览器打开：

$BROWSER http://localhost:8501

> 注意：在某些远程开发环境（Codespaces、DevContainer）中，需将端口映射/公开。

## 五、UI 使用说明（分 Tab 说明）

1) 员工入转调离数据合并（导航：📁 员工入转调离数据合并）
- 功能：把在职、离职、调转三份花名册合并为按组织维度的“入/转/调/离”记录，并把异常（仅出现在调动表但不在在职/离职表）单列出来。
- 输入文件：支持 `.xlsx` / `.xls`，上传顺序无关。字段要求（至少需包含）：`工号`、`姓名`、`入职日期`、`离职日期`、`调动日期`、`调动前一级组织` 等（详见 `service/merge_info.py` 中字段使用）。
- 选择组织层级：下拉选择 `一级组织/二级组织/三级组织/四级组织`，工具会根据选择判断是否为跨组织调转并生成“调离/调入”记录。
- 输出：可在页面下载合并结果与异常员工列表（Excel）。

2) 组织年度“月度沟通经费”计算（导航：💰 组织年度"月度沟通经费"计算）
- 功能：基于上传的员工表（含 `月薪` 或可识别的薪资列），按规则计算每位员工在年度内应分摊的“月度沟通经费”（默认 50 元/月，具体请查看 `service/cal_fee.py`）。
- 输入文件：支持 `.xlsx` / `.xls`，需包含 `工号`、`入职日期`、`离职日期`、`调离日期`、`调入日期`、`月薪/月度相关字段`（代码中按 `月薪` 字段或自行扩展）。
- 设置年度：在界面输入要计算的 `核算年度`（例如 2025），点击 “计算年度月度沟通经费” 即可得到明细与年度总额，并可导出 Excel。

3) 经费余额计算（导航：🧾 经费余额计算）
- 功能：手工登记多笔“已使用金额”，实时计算剩余额度或超支金额。支持添加/删除条目、重置所有数据。

## 六、主要实现说明（给开发者）

- 合并逻辑核心在 [service/merge_info.py](service/merge_info.py)：
  - `read_file(transfer_file, zai_file, li_file)`：读取三份 Excel 数据并做列名适配
  - `process_employee_data(dep_level, all_employees_set, df_tiaodong, df_zai, df_li, output_file)`：处理正常员工（含是否跨组织判断）
  - `process_abnormal_employee_data(...)`：处理调动但不在在职/离职名单中的异常员工

- 经费计算逻辑在 [service/cal_fee.py](service/cal_fee.py)：
  - `calculate_in_annual_allowance(hire_date, target_year)`：入职/调入人员计算
  - `calculate_out_annual_allowance(join_date, leave_date, target_year)`：离职/调出人员计算
  - `cal_fee(cal_file, target_year)`：从 Excel 读取数据并为每个员工计算 `计算月数` 与 `年度经费`

扩展点与注意事项：
- 如果需要不同的经费标准（非 50 元），可将 `calculate_*` 函数的 `monthly_rate` 参数作为可配置项并在 UI 中暴露。
- 当前代码对“有多条记录的同一工号”采用跳过处理（需人工核查），见 `service/cal_fee.py` 中对重复 `工号` 的判断。

## 七、调试与开发

- 在本地调试 Streamlit 页面时，推荐使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make run
```

- 代码修改后，Streamlit 会自动热重载页面（除非修改了依赖环境）。

## 八、常见问题与排错

- Q: 页面无法访问或端口被占用？
  - A: 确认端口是否已被其他进程占用，或尝试更换端口 `PORT=8502 ./scripts/run.sh`。
- Q: 上传 Excel 报错读取失败？
  - A: 检查文件是否为 Excel 格式（`.xlsx`），以及列名是否与代码期望列名匹配（可在 `service` 中查看）。
- Q: 运行时报错缺少包？
  - A: 运行 `pip install -r requirements.txt` 安装依赖。

## 九、贡献与许可证

欢迎提交 issues 或 PR 提供改进建议。当前仓库未附带许可证文件，若用于开源发布请补充 `LICENSE`。

---

如果你希望我把此 README 提交到仓库并推送，我现在可以完成并提交。也可以根据你要求把示例输入文件、单元测试或 CI 配置补充进去。
# tool
个人工具
