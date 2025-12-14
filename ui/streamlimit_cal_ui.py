import streamlit as st
import pandas as pd
import sys
import os
from io import BytesIO
import traceback


# 添加项目根目录到模块搜索路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from service.merge_info import read_file, process_employee_data, process_abnormal_employee_data, rank_clo
from service.cal_fee import cal_fee


ORG_LEVEL_MAP = {
    "一级组织": 1,
    "二级组织": 2,
    "三级组织": 3,
    "四级组织": 4
}


# 合并函数
def merge_employee_files(onboard, resigned, transferred, org_level):
    # 当前实际时间: Friday, December 12, 2025
    print(f"开始处理数据")
    print(f"正在读取源文件... {onboard} \n {resigned} \n {transferred} \n {org_level}")
    df_tiaodong, df_zai, df_li = read_file(transferred, onboard, resigned)

    # 创建一个包含所有员工的集合 （在职 + 离职 = 全量员工）
    all_employees_set = set()

    if not df_zai.empty:
        all_employees_set.update(df_zai['工号'].dropna().astype(str).tolist())
    if not df_li.empty:
        all_employees_set.update(df_li['工号'].dropna().astype(str).tolist())

    # 调用函数处理数据
    employee_df = process_employee_data(org_level, all_employees_set, df_tiaodong, df_zai, df_li, None)
    employee_df = rank_clo(employee_df)

    # 调用函数处理异常员工数据
    abnormal_employee_df = process_abnormal_employee_data(org_level, all_employees_set, df_tiaodong, None)
    abnormal_employee_df = rank_clo(abnormal_employee_df)
    return employee_df, abnormal_employee_df


def calculate_budget(cal_file, target_year):
    if not cal_file:
        raise ValueError("请上传员工入转调离数据文件。")

    df = cal_fee(cal_file, target_year)

    return df, df["年度经费"].sum()


def render_budget_balance_tab():
    st.subheader("📊 年度\"月度沟通经费\"总金额")

    # ====== 保持当前 tab 激活状态 ======
    # 使用 query params 或 session_state 记住当前 tab（推荐 query params，更可靠）
    # 我们通过 URL 参数 active_tab 来控制
    if "active_tab" not in st.query_params:
        st.query_params["active_tab"] = "tab3"
    # （可选）你也可以在主页切换 tab 时设置这个参数）

    # ====== 初始化 session_state ======
    if 'total_amount' not in st.session_state:
        st.session_state['total_amount'] = 0.0
    if 'used_entries' not in st.session_state:
        st.session_state['used_entries'] = []  # 存储每个条目的唯一 key
    if 'used_values' not in st.session_state:
        # 为每个条目存储其数值（避免仅靠 widget key 取值不稳定）
        st.session_state['used_values'] = {}

    # 1. 总金额输入
    total = st.number_input(
        "组织年度“月度沟通费”总金额（元）",
        min_value=0.0,
        value=st.session_state['total_amount'],
        step=1000.0,
        format="%.2f"
    )
    st.session_state['total_amount'] = total

    st.markdown("### 💸 已登记的使用金额")

    # 如果还没有使用记录，显示提示
    if not st.session_state['used_entries']:
        st.info("点击下方“添加使用金额”开始记录支出。")

    # 动态渲染所有使用金额输入框 + 删除按钮
    used_amounts = []
    entries_to_remove = None

    for i, key in enumerate(st.session_state['used_entries']):
        col1, col2 = st.columns([3, 2])
        with col1:
            # 从 session_state 中读取值（更可靠），默认 0.0
            current_val = st.session_state['used_values'].get(key, 0.0)
            val = st.number_input(
                f"使用金额（#{i + 1}笔）",
                min_value=0.0,
                value=float(current_val),
                step=100.0,
                key=f"input_{key}",  # 避免与 used_entries 中的 key 冲突
                format="%.2f"
            )
            # 实时保存到 session_state
            st.session_state['used_values'][key] = val
            used_amounts.append(val)
        with col2:
            # 删除按钮
            if st.button("🗑️", key=f"del_{key}"):
                entries_to_remove = key  # 标记要删除的 key

    # 执行删除（不能在循环中直接修改 list）
    if entries_to_remove is not None:
        st.session_state['used_entries'].remove(entries_to_remove)
        st.session_state['used_values'].pop(entries_to_remove, None)
        st.rerun()

    # 2. 添加使用金额按钮
    if st.button("➕ 添加使用金额"):
        # 生成唯一 key（用时间戳或计数器更安全，避免重复）
        new_key = f"used_{len(st.session_state['used_entries'])}_{int(st.session_state.get('_entry_counter', 0))}"
        st.session_state['_entry_counter'] = st.session_state.get('_entry_counter', 0) + 1
        st.session_state['used_entries'].append(new_key)
        st.session_state['used_values'][new_key] = 0.0  # 初始化值
        st.rerun()  # 刷新以显示新输入框

    # 3. 计算并展示结果
    total_used = sum(used_amounts)
    balance = total - total_used

    st.markdown("### 📌 计算结果")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总经费（元）", f"{total:,.2f}")
    with col2:
        st.metric("已使用（元）", f"{total_used:,.2f}")
    with col3:
        if balance >= 0:
            st.metric("剩余余额（元）", f"{balance:,.2f}")
        else:
            st.metric("超支金额（元）", f"{abs(balance):,.2f}", delta="超支", delta_color="inverse")

    # 重置按钮
    if st.button("🔄 重置所有数据"):
        st.session_state['total_amount'] = 0.0
        st.session_state['used_entries'] = []
        st.session_state['used_values'] = {}
        st.session_state['_entry_counter'] = 0
        st.rerun()


# 主界面
st.set_page_config(page_title="HR 数据工具", layout="centered")
st.title("HR 数据处理工具")
st.caption("本工具支持**员工入转调离数据合并**，**各级组织年度\"月度沟通经费\"计算**等等。")

tab_options = {
    "📁 员工入转调离数据合并": "tab1",
    "💰 组织年度\"月度沟通经费\"计算": "tab2",
    "🧾 经费余额计算": "tab3"
}

# 从 query_params 或 session_state 获取当前 tab
current_tab_key = st.query_params.get("active_tab", "tab1")
current_tab_name = [k for k, v in tab_options.items() if v == current_tab_key]
current_tab_name = current_tab_name[0] if current_tab_name else list(tab_options.keys())[0]

selected_tab = st.radio(
    "导航",
    options=list(tab_options.keys()),
    index=list(tab_options.keys()).index(current_tab_name),
    horizontal=True,
    label_visibility="collapsed"
)

# 更新 query_params 当切换 tab
if tab_options[selected_tab] != st.query_params.get("active_tab"):
    st.query_params["active_tab"] = tab_options[selected_tab]


# 渲染对应内容
if tab_options[selected_tab] == "tab1":
    st.subheader("📎 上传员工花名册")
    st.caption("请上传 Excel 文件（.xlsx 或 .xls）")
    st.query_params["active_tab"] = "tab1"

    col1, col2, col3 = st.columns(3)
    with col1:
        # 标签文字已作为按钮主文字，无额外 label
        onboard_file = st.file_uploader("**在职员工花名册**", type=["xlsx", "xls"])
    with col2:
        resigned_file = st.file_uploader("**离职员工花名册**", type=["xlsx", "xls"])
    with col3:
        transferred_file = st.file_uploader("**调转员工花名册**", type=["xlsx", "xls"])

    st.subheader("🏢 选择统计组织层级")
    st.caption("明确合并统计组织层级，自动忽略原组织之间的调转")
    org_level = st.selectbox(
        "组织层级",  # 这个 label 会显示在下拉框上方（Streamlit 必需）
        options=list(ORG_LEVEL_MAP.keys()),
        index=0
    )

    st.write("")
    if st.button("开始合并", use_container_width=True):
        try:
            # 清除之前的缓存
            if 'employee_df' in st.session_state:
                del st.session_state['employee_df']
            if 'abnormal_employee_df' in st.session_state:
                del st.session_state['abnormal_employee_df']

            employee_df, abnormal_employee_df = merge_employee_files(onboard_file, resigned_file, transferred_file,
                                                                     ORG_LEVEL_MAP[org_level])
            st.session_state['employee_df'] = employee_df
            st.session_state['abnormal_employee_df'] = abnormal_employee_df

            if not abnormal_employee_df.empty:
                st.success(f"✅ 合并成功！员工入转调离信息共 {len(employee_df)} 条记录，异常员工入转调离信息共 {len(abnormal_employee_df)} 条记录。")
            else:
                st.success(f"✅ 合并成功！员工入转调离信息共 {len(employee_df)} 条记录。")
        except Exception as e:
            st.error(f"❌ 合并失败：{e}")

    if 'employee_df' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as w:
            st.session_state['employee_df'].to_excel(w, index=False, sheet_name="合并结果")
        st.download_button(
            "📥 下载员工入转调离数据（Excel）",
            data=output.getvalue(),
            file_name=f"员工入转调离数据_{org_level}.xlsx",
            use_container_width=False
        )

    if 'abnormal_employee_df' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as w:
            st.session_state['abnormal_employee_df'].to_excel(w, index=False, sheet_name="合并结果")
        st.download_button(
            "📥 下载异常员工入转调离数据（Excel）",
            data=output.getvalue(),
            file_name=f"异常员工入转调离数据_{org_level}.xlsx",
            use_container_width=False
        )
elif tab_options[selected_tab] == "tab2":
    st.subheader("📎 上传部门员工入转调离数据")
    st.caption("文件需包含“月薪”列（单位：元），支持 .xlsx 格式")
    st.query_params["active_tab"] = "tab2"

    budget_file = st.file_uploader("员工薪资数据文件", type=["xlsx", "xls"])

    st.subheader("📅 设置核算年度")
    budget_year = st.text_input("核算年度", value="2025", placeholder="例如：2025")

    st.write("")
    if st.button("🧮 计算年度月度沟通经费", use_container_width=True):
        if not budget_year.strip():
            st.error("❌ 请输入有效的核算年度。")
        else:
            try:
                detail_df, total = calculate_budget(budget_file, int(budget_year))
                st.session_state['budget_df'] = detail_df
                st.session_state['total_budget'] = total
                st.success(f"✅ 计算完成！年度总经费：**{total:,.2f} 元**")
            except Exception as e:
                st.error(f"❌ 计算失败：{traceback.format_exc()}")

    if 'budget_df' in st.session_state:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as w:
            st.session_state['budget_df'].to_excel(w, index=False, sheet_name="经费明细")
        st.download_button(
            "📥 下载经费结果（Excel）",
            data=output.getvalue(),
            file_name=f"年度经费核算_{budget_year}.xlsx",
            use_container_width=False
        )
elif tab_options[selected_tab] == "tab3":
    st.query_params["active_tab"] = "tab3"
    render_budget_balance_tab()


#tab1, tab2, tab3 = st.tabs(["📁 员工入转调离数据合并", "💰 组织年度\"月度沟通经费\"计算", "🧾 经费余额计算"])

# =============== Tab 1: 合并 ===============
# with tab1:
#     st.subheader("📎 上传员工花名册")
#     st.caption("请上传 Excel 文件（.xlsx 或 .xls）")
#     st.query_params["active_tab"] = "tab1"
#
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         # 标签文字已作为按钮主文字，无额外 label
#         onboard_file = st.file_uploader("**在职员工花名册**", type=["xlsx", "xls"])
#     with col2:
#         resigned_file = st.file_uploader("**离职员工花名册**", type=["xlsx", "xls"])
#     with col3:
#         transferred_file = st.file_uploader("**调转员工花名册**", type=["xlsx", "xls"])
#
#     st.subheader("🏢 选择统计组织层级")
#     st.caption("明确合并统计组织层级，自动忽略原组织之间的调转")
#     org_level = st.selectbox(
#         "组织层级",  # 这个 label 会显示在下拉框上方（Streamlit 必需）
#         options=list(ORG_LEVEL_MAP.keys()),
#         index=0
#     )
#
#     st.write("")
#     if st.button("开始合并", use_container_width=True):
#         try:
#             # 清除之前的缓存
#             if 'employee_df' in st.session_state:
#                 del st.session_state['employee_df']
#             if 'abnormal_employee_df' in st.session_state:
#                 del st.session_state['abnormal_employee_df']
#
#             employee_df, abnormal_employee_df = merge_employee_files(onboard_file, resigned_file, transferred_file, ORG_LEVEL_MAP[org_level])
#             st.session_state['employee_df'] = employee_df
#             st.session_state['abnormal_employee_df'] = abnormal_employee_df
#
#             if not abnormal_employee_df.empty:
#                 st.success(f"✅ 合并成功！员工入转调离信息共 {len(employee_df)} 条记录，异常员工入转调离信息共 {len(abnormal_employee_df)} 条记录。")
#             else:
#                 st.success(f"✅ 合并成功！员工入转调离信息共 {len(employee_df)} 条记录。")
#         except Exception as e:
#             st.error(f"❌ 合并失败：{e}")
#
#     if 'employee_df' in st.session_state:
#         output = BytesIO()
#         with pd.ExcelWriter(output, engine='xlsxwriter') as w:
#             st.session_state['employee_df'].to_excel(w, index=False, sheet_name="合并结果")
#         st.download_button(
#             "📥 下载员工入转调离数据（Excel）",
#             data=output.getvalue(),
#             file_name=f"员工入转调离数据_{org_level}.xlsx",
#             use_container_width=False
#         )
#
#     if 'abnormal_employee_df' in st.session_state:
#         output = BytesIO()
#         with pd.ExcelWriter(output, engine='xlsxwriter') as w:
#             st.session_state['abnormal_employee_df'].to_excel(w, index=False, sheet_name="合并结果")
#         st.download_button(
#             "📥 下载异常员工入转调离数据（Excel）",
#             data=output.getvalue(),
#             file_name=f"异常员工入转调离数据_{org_level}.xlsx",
#             use_container_width=False
#         )
#
# # =============== Tab 2: 经费 ===============
# with tab2:
#     st.subheader("📎 上传部门员工入转调离数据")
#     st.caption("文件需包含“月薪”列（单位：元），支持 .xlsx 格式")
#     st.query_params["active_tab"] = "tab2"
#
#     budget_file = st.file_uploader("员工薪资数据文件", type=["xlsx", "xls"])
#
#     st.subheader("📅 设置核算年度")
#     budget_year = st.text_input("核算年度", value="2025", placeholder="例如：2025")
#
#     st.write("")
#     if st.button("🧮 计算年度月度沟通经费", use_container_width=True):
#         if not budget_year.strip():
#             st.error("❌ 请输入有效的核算年度。")
#         else:
#             try:
#                 detail_df, total = calculate_budget(budget_file, int(budget_year))
#                 st.session_state['budget_df'] = detail_df
#                 st.session_state['total_budget'] = total
#                 st.success(f"✅ 计算完成！年度总经费：**{total:,.2f} 元**")
#             except Exception as e:
#                 st.error(f"❌ 计算失败：{traceback.format_exc()}")
#
#     if 'budget_df' in st.session_state:
#         output = BytesIO()
#         with pd.ExcelWriter(output, engine='xlsxwriter') as w:
#             st.session_state['budget_df'].to_excel(w, index=False, sheet_name="经费明细")
#         st.download_button(
#             "📥 下载经费结果（Excel）",
#             data=output.getvalue(),
#             file_name=f"年度经费核算_{budget_year}.xlsx",
#             use_container_width=False
#         )
#
# # =============== Tab 3: 经费余额 ===============
# with tab3:
#     st.query_params["active_tab"] = "tab3"
#     render_budget_balance_tab()
