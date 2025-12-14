import pandas as pd


def rank_clo(df_final):
    # 选择并重排所需的列
    required_columns = [
        '姓名', '工号', '一级组织', '二级组织', '三级组织', '四级组织',
        '入职日期', '离职日期', '调离日期', '调入日期', '跨组织调转'
    ]

    # 检查列是否存在，以防某些文件为空导致列缺失
    missing_cols = [col for col in required_columns if col not in df_final.columns]
    for col in missing_cols:
        if col in ['姓名', '一级组织', '二级组织', '三级组织', '四级组织', '跨组织调转']:
            df_final[col] = None
        elif col in ['入职日期', '调离日期', '调入日期', '离职日期']:
            df_final[col] = pd.NaT

    df_output = df_final[required_columns].copy()

    # 将 NaT (Not a Time) 转换为 None 或空白字符串以便在Excel中显示为空白
    date_columns = ['入职日期', '调离日期', '调入日期', '离职日期']
    for col in date_columns:
        df_output[col] = df_output[col].dt.strftime('%Y-%m-%d')  # 先格式化为字符串
        df_output[col] = df_output[col].replace('NaT', '')  # 再替换 NaT 字符串

    df_output = df_output[required_columns]
    return df_output


# 输出文件
def output_result_file(df_final, output_file):
    # 选择并重排所需的列
    required_columns = [
        '姓名', '工号', '一级组织', '二级组织', '三级组织', '四级组织',
        '入职日期', '离职日期', '调离日期', '调入日期', '跨组织调转'
    ]

    # 检查列是否存在，以防某些文件为空导致列缺失
    missing_cols = [col for col in required_columns if col not in df_final.columns]
    for col in missing_cols:
        if col in ['姓名', '一级组织', '二级组织', '三级组织', '四级组织', '跨组织调转']:
            df_final[col] = None
        elif col in ['入职日期', '调离日期', '调入日期', '离职日期']:
            df_final[col] = pd.NaT

    df_output = df_final[required_columns].copy()

    # 将 NaT (Not a Time) 转换为 None 或空白字符串以便在Excel中显示为空白
    date_columns = ['入职日期', '调离日期', '调入日期', '离职日期']
    for col in date_columns:
        df_output[col] = df_output[col].dt.strftime('%Y-%m-%d')  # 先格式化为字符串
        df_output[col] = df_output[col].replace('NaT', '')  # 再替换 NaT 字符串

    df_output = df_output[required_columns]

    print(f"数据处理完毕，准备写入文件: {output_file}")
    # --- 6. 保存结果 ---
    try:
        df_output.to_excel(output_file, index=False, engine='openpyxl')
        print(f"成功生成汇总表: {output_file}")
    except Exception as e:
        print(f"写入文件时出错: {e}")


# 修改列名
def rename_df(df, col_name, target_col_name):
    df = df.copy()
    if col_name in df.columns:
        df = df.rename(columns={col_name: target_col_name})
    else:
        df[target_col_name] = None  # 或 pd.NA

    return df


# 判断是否跨组织调转
def is_cross_dep(dep_level, latest):
    msg = ''
    # 若本部门调转，则无需设置调转时间信息
    if (dep_level == 1) and latest['调动前一级组织'] == latest['调动后一级组织']:
        msg = "一级组织内调转"
    elif (dep_level == 2) and latest['调动前一级组织'] == latest['调动后一级组织'] and latest['调动前二级组织'] == latest['调动后二级组织']:
        msg = "二级组织内调转"
    elif (dep_level == 3) and latest['调动前一级组织'] == latest['调动后一级组织'] and latest['调动前二级组织'] == latest['调动后二级组织'] and \
            latest['调动前三级组织'] == latest['调动后三级组织']:
        msg = "三级组织内调转"
    elif (dep_level == 4) and latest['调动前一级组织'] == latest['调动后一级组织'] and latest['调动前二级组织'] == latest['调动后二级组织'] and \
            latest['调动前三级组织'] == latest['调动后三级组织'] and latest['调动前部门'] == latest['调动后部门']:
        msg = "四级组织内调转"

    return msg


# 读取员工信息文件
def read_file(transfer_file, zai_file, li_file):
    df_tiaodong = pd.read_excel(transfer_file)

    df_zai = pd.read_excel(zai_file) if zai_file else pd.DataFrame()

    df_li = pd.read_excel(li_file) if li_file else pd.DataFrame()
    df_li = rename_df(df_li, "最后工作日", "离职日期")
    df_li = rename_df(df_li, "部门", "四级组织")

    return df_tiaodong, df_zai, df_li


# 合并处理正常员工数据
def process_employee_data(dep_level, all_employees_set, df_tiaodong, df_zai, df_li, output_file):
    # --- 2. 初始化最终表 ---
    print("正在初始化员工列表...")
    # 将集合转换为 DataFrame，方便后续操作
    df_final = pd.DataFrame(list(all_employees_set), columns=['工号'])

    # 合并在职员工信息（入职时间）
    df_join_time = (
        pd.concat([
            df_zai[['工号', '入职日期', '姓名', '一级组织', '二级组织', '三级组织', '四级组织']].drop_duplicates(
                '工号') if not df_zai.empty else pd.DataFrame(),
            df_li[['工号', '入职日期', '姓名', '一级组织', '二级组织', '三级组织', '四级组织']].drop_duplicates(
                '工号') if not df_li.empty else pd.DataFrame()
        ], ignore_index=True).drop_duplicates('工号', keep='first')
    )

    if not df_join_time.empty:
        df_final = df_final.merge(df_join_time, on='工号', how='left')
    else:
        df_final['入职日期'] = pd.NaT  # 如果没有在职员工，入职日期为空

    # 合并离职员工信息（离职时间）
    if not df_li.empty:
        df_final = df_final.merge(df_li[['工号', '离职日期']], on='工号', how='left')
    else:
        df_final['最后工作日'] = pd.NaT  # 如果没有离职员工，离职日期为空

    # 添加其他必要列
    df_final['调离日期'] = pd.NaT
    df_final['调入日期'] = pd.NaT
    df_final['跨组织调转'] = ""

    print(f"初始员工列表处理完成，共 {len(df_final)} 名员工。")

    # --- 3. 处理调动记录 ---
    print("正在处理调动记录...")

    # 首先，按工号和调动日期排序
    df_tiaodong_sorted = df_tiaodong.sort_values(['工号', '调动日期']).reset_index(drop=True)

    transfer_final = []
    for idx, row in df_final.iterrows():
        emp_id = row['工号']
        # 获取该员工的所有调动记录
        emp_transfers = df_tiaodong_sorted[df_tiaodong_sorted['工号'] == emp_id]

        if emp_transfers.empty:
            # 没有调动：保留原行
            transfer_final.append(row.copy())
        else:
            before_row = row.copy()

            # 有调动：取最新的一条（你已经按日期排序）
            latest = emp_transfers.iloc[-1]
            transfer_date = latest['调动日期']

            # 构造调动前的记录（复制原 row，只更新组织和调离时间）
            before_row['一级组织'] = latest['调动前一级组织']
            before_row['二级组织'] = latest['调动前二级组织']
            before_row['三级组织'] = latest['调动前三级组织']
            before_row['四级组织'] = latest['调动前部门']
            before_row['调入日期'] = pd.NaT

            msg = is_cross_dep(dep_level, latest)
            if msg != '':
                before_row['跨组织调转'] = msg
                transfer_final.append(before_row)
                continue

            before_row['跨组织调转'] = f"跨{dep_level}组织调转"
            before_row['调离日期'] = transfer_date
            # 构造调动后的记录
            after_row = row.copy()
            after_row['一级组织'] = latest['调动后一级组织']
            after_row['二级组织'] = latest['调动后二级组织']
            after_row['三级组织'] = latest['调动后三级组织']
            after_row['四级组织'] = latest['调动后部门']
            after_row['调入日期'] = transfer_date
            after_row['调离日期'] = pd.NaT
            after_row['跨组织调转'] = f"跨{dep_level}组织调转"

            # 添加两条记录
            transfer_final.extend([before_row, after_row])

    # 合并成新的 DataFrame
    transfer_final_df = pd.DataFrame(transfer_final).reset_index(drop=True)

    print("调动记录处理完成。")

    print("正在准备输出数据...")

    # 输出文件
    if output_file:
        output_result_file(transfer_final_df, output_file)

    return transfer_final_df


# 合并处理正常员工数据
def process_abnormal_employee_data(dep_level, all_employees_set, df_tiaodong, output_file):
    # --- 2. 初始化最终表 ---
    print("正在异常初始化员工列表...")
    # 将集合转换为 DataFrame，方便后续操作
    df_final = pd.DataFrame(list(all_employees_set), columns=['工号'])

    # 创建一个异常员工的集合 （调动人员 = 不在全量员工名单中）
    diaodong_employees_set = set()
    if not df_tiaodong.empty:
        diaodong_employees_set.update(df_tiaodong['工号'].dropna().astype(str).tolist())

    abnormal_employees_set = diaodong_employees_set - all_employees_set
    abnormal_df_final = pd.DataFrame(list(abnormal_employees_set), columns=['工号'])

    print(f"初始异常员工列表处理完成，共 {len(abnormal_df_final)} 名员工。")

    # --- 3. 处理调动记录 ---
    print("正在处理异常调动记录...")
    print("异常调动记录处理开始。")

    df_tiaodong_sorted = df_tiaodong.sort_values(['工号', '调动日期']).reset_index(drop=True)

    abnormal_transfer_res = []

    for idx, row in abnormal_df_final.iterrows():
        emp_id = row['工号']
        # 获取该员工的所有调动记录
        emp_transfers = df_tiaodong_sorted[df_tiaodong_sorted['工号'] == emp_id]

        latest = emp_transfers.iloc[-1]

        transfer_date = latest['调动日期']

        before_row = {
            '工号': latest['工号'],
            '姓名': latest['姓名'],
            '一级组织': latest['调动前一级组织'],
            '二级组织': latest['调动前二级组织'],
            '三级组织': latest['调动前三级组织'],
            '四级组织': latest['调动前部门'],
            '入职日期': latest['入职日期'],
            '离职日期': pd.NaT,
            '调入日期': pd.NaT,
            '调离日期': pd.NaT
        }

        msg = is_cross_dep(dep_level, latest)
        if msg != '':
            before_row['跨组织调转'] = msg
            abnormal_transfer_res.append(before_row)
            continue

        before_row['调离日期'] = transfer_date
        before_row['跨组织调转'] = f"跨{dep_level}组织调转"

        # 构造调动后的记录
        after_row = {
            '工号': latest['工号'],
            '姓名': latest['姓名'],
            '一级组织': latest['调动后一级组织'],
            '二级组织': latest['调动后二级组织'],
            '三级组织': latest['调动后三级组织'],
            '四级组织': latest['调动后部门'],
            '入职日期': latest['入职日期'],
            '离职日期': pd.NaT,
            '调入日期': transfer_date,
            '调离日期': pd.NaT,
            '跨组织调转': f"跨{dep_level}组织调转"
        }

        # 添加两条记录
        abnormal_transfer_res.extend([before_row, after_row])

        # 合并成新的 DataFrame
    transfer_final_df = pd.DataFrame(abnormal_transfer_res).reset_index(drop=True)
    print("异常调动记录处理完成。")
    # --- 5. 格式化和筛选最终输出列 ---
    print("正在准备输出异常员工数据...")

    # 输出文件
    if output_file:
        output_result_file(transfer_final_df, output_file)

    return transfer_final_df


if __name__ == "__main__":
    # 定义文件路径
    TIAODONG_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/20251211140224.xlsx"
    ZAI_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/20251211140150.xlsx"
    LI_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/20251211140206.xlsx"

    OUTPUT_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/员工入转调离信息汇总表.xlsx"
    ABNORMAL_OUTPUT_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/异常员工入转调离信息汇总表.xlsx"

    # 当前实际时间: Friday, December 12, 2025
    print(f"开始处理数据，当前时间参考: Friday, December 12, 2025")
    print("正在读取源文件...")
    df_tiaodong, df_zai, df_li = read_file(TIAODONG_FILE, ZAI_FILE, LI_FILE)

    # 创建一个包含所有员工的集合 （在职 + 离职 = 全量员工）
    all_employees_set = set()

    if not df_zai.empty:
        all_employees_set.update(df_zai['工号'].dropna().astype(str).tolist())
    if not df_li.empty:
        all_employees_set.update(df_li['工号'].dropna().astype(str).tolist())

    # 调用函数处理数据
    process_employee_data(3, all_employees_set, df_tiaodong, df_zai, df_li, OUTPUT_FILE)

    # 调用函数处理异常员工数据
    process_abnormal_employee_data(3, all_employees_set, df_tiaodong, ABNORMAL_OUTPUT_FILE)
