from datetime import date
from typing import Union
import pandas as pd


# 输出文件
def output_result_file(df_final, output_file):
    df_output = df_final.copy()

    print(f"数据处理完毕，准备写入文件: {output_file}")
    # --- 6. 保存结果 ---
    try:
        df_output.to_excel(output_file, index=False, engine='openpyxl')
        print(f"成功生成汇总表: {output_file}")
    except Exception as e:
        print(f"写入文件时出错: {e}")


def calculate_in_annual_allowance(
        hire_date: Union[date, str],
        target_year: int,
        monthly_rate: float = 50.0,
        cutoff_day: int = 15
):
    """
    计算某员工在目标年份（target_year）应享有的年度活动经费 ----- 入职/调入情况。

    规则说明：
    - 若员工入职年份 < target_year（跨年）：享有全年 12 个月经费（即 12 * monthly_rate）。
    - 若员工入职年份 == target_year（同年）：
        - 若入职日期 <= 当月 cutoff_day（含）：首月算整月；
        - 否则：首月算 0.5 个月；
        - 总月数 = 首月折算 + (12 - 入职月份)
        - 若入职月份为12月，则剩余月数为0。
    - 若员工入职年份 > target_year：尚未入职，返回 0.0。

    参数:
        hire_date (date or str): 员工入职日期/调入，支持 'YYYY-MM-DD' 字符串或 date 对象。
        target_year (int): 统计年份（例如 2013、2014）。
        monthly_rate (float): 月度经费标准，默认 50.0 元。
        cutoff_day (int): 判断首月是否计整月的截止日（含），默认 15。

    返回:
        float: 应享有的年度经费（保留两位小数，符合财务习惯）。

    示例:
        >>> calculate_in_annual_allowance('2013-11-21', 2014)
        600.0
        >>> calculate_in_annual_allowance('2013-02-21', 2013)
        525.0
        >>> calculate_in_annual_allowance('2013-02-10', 2013)
        550.0
        >>> calculate_in_annual_allowance('2015-01-01', 2013)
        0.0
    """
    # 标准化 hire_date 为 date 对象
    if isinstance(hire_date, str):
        try:
            hire_date = date.fromisoformat(hire_date)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {hire_date}. Expected YYYY-MM-DD.") from e
    elif not isinstance(hire_date, date):
        raise TypeError("hire_date must be a date object or 'YYYY-MM-DD' string.")

    hire_year = hire_date.year
    hire_month = hire_date.month
    hire_day = hire_date.day

    # 情况1: 员工在统计年份之后入职 → 0
    if hire_year > target_year:
        return 0, 0.0

    # 情况2: 跨年（入职年 < 统计年）→ 全年12个月
    if hire_year < target_year:
        return 12, round(12 * monthly_rate, 2)

    # 情况3: 同年（hire_year == target_year）
    # 判断首月折算
    if hire_day <= cutoff_day:
        first_month_factor = 1.0
    else:
        first_month_factor = 0.5

    # 剩余完整月份：从 (hire_month + 1) 到 12 月，共 (12 - hire_month) 个月
    remaining_full_months = 12 - hire_month

    total_months = first_month_factor + remaining_full_months

    # 边界保护：防止因逻辑错误导致负数（理论上不会发生）
    total_months = max(0.0, total_months)

    return total_months, round(total_months * monthly_rate, 2)


def calculate_out_annual_allowance(
    join_date: date,
    leave_date: date,
    target_year: int,
    monthly_rate: float = 50.0,
    cutoff_day: int = 15
):
    """
       计算员工在指定年份的年度活动经费（适用于离职或调离员工）。

       规则：
         - 若 leave_date 所属年份 < target_year，则经费为 0。
         - 否则，经费 = (在职完整月数 + 离职当月折算月数) * 50
           - 离职当月：leave_date.day <= 15 → 0.5 月；否则 1 月
           - 在职完整月数：从 target_year 年 1 月 1 日 到 leave_date 所在月的前一个月
             但不能早于 join_date。

       Args:
           join_date (date): 入职日期
           leave_date (date): 离职或调离日期
           target_year (int): 统计的年度（如 2024）

       Returns:
           float: 年度活动经费（单位：元）

       Examples:
           >>> calculate_out_annual_allowance(date(2023,1,1), date(2024,3,1), 2024)
           125.0
           >>> calculate_out_annual_allowance(date(2024,2,1), date(2024,5,16), 2024)
           200.0
           >>> calculate_out_annual_allowance(date(2023,1,1), date(2024,3,1), 2023)
           600.0
       """
    if leave_date.year < target_year:
        return 0.0, 0.0

    if leave_date.year > target_year:
        return 12.0, round(12 * monthly_rate, 2)

    # Only consider target_year
    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 31)

    # Actual period in target_year
    actual_join = max(join_date, year_start)
    actual_leave = min(leave_date, year_end)

    if actual_join > actual_leave:
        return 0.0, 0.0

    join_month = actual_join.month
    leave_month = actual_leave.month

    # --- Calculate fraction for join month (only if joined in target_year)
    if join_date.year == target_year:
        if actual_join.day <= cutoff_day:
            join_frac = 1.0
        else:
            join_frac = 0.5
    else:
        # Joined before target_year → January is full month
        join_frac = 1.0

    # --- Calculate fraction for leave month (always in target_year here)
    if actual_leave.day < cutoff_day:
        leave_frac = 0.5
    else:
        leave_frac = 1.0

    # --- Handle same month
    if join_month == leave_month:
        # Only one month
        if join_date.year == target_year and leave_date.year == target_year:
            # Both in same year and same month
            if actual_join.day <= cutoff_day and actual_leave.day > cutoff_day:
                total_months = 1.0
            else:
                total_months = 0.5
        else:
            # Joined before target_year, so this month is full if leave after 15th
            total_months = leave_frac
    else:
        # Different months
        # Full months between join and leave (excluding both)
        full_months = leave_month - join_month - 1
        if full_months < 0:
            full_months = 0

        total_months = join_frac + full_months + leave_frac

    total_months = max(0.0, total_months)
    allowance = round(total_months * monthly_rate, 2)
    return total_months, allowance


# 计算部门经费
def cal_fee(cal_file, target_year):
    print(f"开始计算组织{target_year}经费")
    dep_data_df = pd.read_excel(cal_file)
    # 确保日期列是datetime类型
    date_cols = ['入职日期', '离职日期', '调离日期', '调入日期']
    for col in date_cols:
        if col in dep_data_df.columns:
            dep_data_df[col] = pd.to_datetime(dep_data_df[col], errors='coerce').dt.date

    # 初始化结果列
    dep_data_df['计算月数'] = 0.0
    dep_data_df['年度经费'] = 0.0

    # 频繁调度少数场景计算
    # 同时存在调入/调出情况，人工计算（需要结合入职时间计算）
    # 同时存在离职/调转情况，人工计算

    duplicated_mask = dep_data_df.duplicated(subset=['工号'], keep=False)  # keep=False 表示所有重复行都标记为 True

    print(f"开始遍历员工信息")
    for idx, row in dep_data_df.iterrows():
        # TODO 排除员工有多条记录的情况，人工计算
        is_dup = duplicated_mask.loc[idx]
        if is_dup:
            continue

        hire_date = row['入职日期']
        leave_date = row['离职日期']
        transfer_out_date = row['调离日期']
        transfer_in_date = row['调入日期']

        # 在职/调入 人员计算
        if hire_date and (leave_date is None or leave_date == '' or pd.isna(leave_date)) \
                and (transfer_out_date is None or transfer_out_date == '' or pd.isna(transfer_out_date)) \
                and (transfer_in_date is None or transfer_in_date == '' or pd.isna(transfer_in_date)):
            total_months, fee = calculate_in_annual_allowance(hire_date, target_year)

            dep_data_df.at[idx, '计算月数'] = total_months
            dep_data_df.at[idx, '年度经费'] = fee
            continue

        if hire_date and transfer_in_date \
                and (leave_date is None or leave_date == '' or pd.isna(leave_date)) \
                and (transfer_out_date is None or transfer_out_date == '' or pd.isna(transfer_out_date)):
            total_months, fee = calculate_in_annual_allowance(transfer_in_date, target_year)

            dep_data_df.at[idx, '计算月数'] = total_months
            dep_data_df.at[idx, '年度经费'] = fee
            continue

        # 离职/调入 人员计算
        if hire_date and leave_date \
                and (transfer_out_date is None or transfer_out_date == '' or pd.isna(transfer_out_date)) \
                and (transfer_in_date is None or transfer_in_date == '' or pd.isna(transfer_in_date)):
            total_months, fee = calculate_out_annual_allowance(hire_date, leave_date, target_year)

            dep_data_df.at[idx, '计算月数'] = total_months
            dep_data_df.at[idx, '年度经费'] = fee
            continue

        if hire_date and transfer_out_date \
                and (leave_date is None or leave_date == '' or pd.isna(leave_date)) \
                and (transfer_in_date is None or transfer_in_date == '' or pd.isna(transfer_in_date)):
            total_months, fee = calculate_out_annual_allowance(hire_date, transfer_out_date, target_year)

            dep_data_df.at[idx, '计算月数'] = total_months
            dep_data_df.at[idx, '年度经费'] = fee
            continue

    print(f"组织计费计算完成，一共{len(dep_data_df)}")
    return dep_data_df


if __name__ == '__main__':
    # print(calculate_out_annual_allowance(date(2023,1,1), date(2024,3,1), 2024))
    # print(calculate_out_annual_allowance(date(2024,2,1), date(2024,5,16), 2024))
    # print(calculate_out_annual_allowance(date(2024,5,10), date(2024,9,16), 2024))
    # print(calculate_out_annual_allowance(date(2024, 5, 16), date(2024, 9, 10), 2024))
    # print(calculate_out_annual_allowance(date(2024, 5, 10), date(2024, 9, 10), 2024))
    #
    # print(calculate_out_annual_allowance(date(2023,1,1), date(2024,3,1), 2023))

    CAL_FILE = "/Users/shengjiang.zw/Desktop/cal_file_2.xlsx"

    OUT_CAL_FILE = "/Users/shengjiang.zw/PycharmProjects/pythonProject/custom_eval/zhao/file/result.xlsx"

    result = cal_fee(CAL_FILE, 2025)

    output_result_file(result, OUT_CAL_FILE)

