import pandas as pd
import numpy as np
from xlwt import Workbook
import xlrd
from xlrd import book
from xlutils.copy import copy


def merge(intervals):
    if len(intervals) == 0:
        return intervals
    intervals.sort(key=lambda x: x[0])
    result = []
    result.append(intervals[0])
    for i in range(1, len(intervals)):
        last = result[-1]
        if last[1] >= intervals[i][0]:
            result[-1] = [last[0], max(last[1], intervals[i][1])]
        else:
            result.append(list(intervals[i]))
    return result


def findMissingRanges(nums, lower, upper):
    """
    :type nums: List[int]
    :type lower: int
    :type upper: int
    :rtype: List[str]
    """
    x, y = [], []
    start, end = lower, lower
    res = []
    for i in range(len(nums)):
        if nums[i] == end:  # 没有缺失区间
            start, end = nums[i] + 1, nums[i] + 1

        elif nums[i] > end:  # 真的缺失了区间
            end = max(end, nums[i] - 1)
            if end != start:
                res.append(str(start) + "->" + str(end + 1))
                x.append(start)
                y.append(end + 1)
            start, end = nums[i] + 1, nums[i] + 1

    if start < upper:  # 处理最后一段
        res.append(str(start - 1) + "->" + str(upper + 1))
        x.append(start)
        y.append(end + 1)

    return res, x, y


######  需要更改路径的地方
yuanwenjian_path = r'C:\Users\bupt\Desktop\control_behavior_8_2.xlsx'
data = pd.read_excel(yuanwenjian_path, header=None)  # 默认读取第一个sheet
# 用于copy的路径，也是填源文件的路径，表单默认为sheet1，可修改
file_name = yuanwenjian_path
sheet_name = 'Sheet1'
# 用于保存的路径
save_path = r'C:\Users\bupt\Desktop\control_behavior_8_2.xls'
######

start = np.array([])  # ndarray
end = np.array([])
for i in range(6):
    start = np.append(start, data[2 * i][2:].values)
    end = np.append(end, data[2 * i + 1][2:].values)

start = start[~pd.isna(start)]
end = end[~pd.isna(end)]

s = np.min(start)
e = np.max(end)
# print('起止时间节点：', s, e)

# 合并区间
intervals = list(zip(start, end))
# print('待合并的区间：',intervals)
result = merge(intervals)
# print('合并后的区间', result)
# print(len(result))

# 双指针取补
nums = []
for i in range(len(result)):
    nums.extend(list(range(result[i][0], result[i][1])))

lower = s
upper = e
res, x, y = findMissingRanges(nums, lower, upper)
# print(x)
# print(y)


readbook = xlrd.open_workbook(file_name)
sheet = readbook.sheet_by_name(sheet_name)
nrows = sheet.nrows  # 获取excel的行数
book1 = xlrd.open_workbook(file_name)
book2 = copy(book1)  # 由于xlrd只能读不能写，xlwt只能写不能读，所以如果通过xlrd读出的表格内容是没办法进行操作的，因此需要拷贝一份原来的excel
sheet1 = book2.get_sheet(0)  # 获取第几个sheet页，book2现在的是xlutils里的方法，不是xlrd的
for i in range(len(x)):
    sheet1.write(i + 2, 12, x[i])
    sheet1.write(i + 2, 13, y[i])
book2.save(save_path)
