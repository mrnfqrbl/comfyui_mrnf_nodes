# utils/output_down_utils.py
import asyncio
import io

import os
import datetime
import hashlib
import re
import logging
import subprocess

import folder_paths
import PIL

# logger = logging.getLogger("mrnf")
from loguru import logger
时间间隔 = datetime.timedelta(hours=12)  # 定义时间间隔（12小时）


# 获取文件 MD5 校验值
def 获取文件_md5(文件路径):
    """计算文件的 MD5 校验值"""
    哈希_md5 = hashlib.md5()
    try:
        with open(文件路径, "rb") as 文件:
            for 数据块 in iter(lambda: 文件.read(4096), b""):
                哈希_md5.update(数据块)
        return 哈希_md5.hexdigest()
    except Exception as 异常:
        logger.error(f"计算 MD5 出错: {异常}")
        return None


# 获取目录下的 PNG 图片列表和 MD5 校验值
def 获取_png_文件列表_带_md5(目录):
    """获取目录下所有 PNG 图片的文件路径和 MD5 校验值"""
    png_文件列表 = []
    if not os.path.exists(目录):
        return png_文件列表  # 如果目录不存在，直接返回空列表

    for 文件名 in os.listdir(目录):
        if 文件名.lower().endswith(".png"):
            文件路径 = os.path.join(目录, 文件名)
            md5_哈希值 = 获取文件_md5(文件路径)
            if md5_哈希值:
                png_文件列表.append({"filename": 文件名, "path": 文件路径, "md5": md5_哈希值})
    return png_文件列表


# 从文件名中提取时间戳
def 提取时间戳_从文件名(文件名):
    """从文件名中提取时间戳，在文件名任意位置搜索年月日和时分秒或者二者在一起的-形式"""
    时间戳 = None
    # 优先匹配包含时分秒的完整时间戳
    时间戳匹配 = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", 文件名)
    if 时间戳匹配:
        时间戳字符串 = 时间戳匹配.group(1)
        try:
            时间戳 = datetime.datetime.strptime(时间戳字符串, "%Y-%m-%d-%H-%M-%S")
            return 时间戳
        except ValueError as e:
            logger.warning(f"完整时间戳解析失败: {文件名}, 错误信息: {e}")
    else:
        # 如果没有找到完整时间戳，则匹配只包含年月日的日期
        日期匹配 = re.search(r"(\d{4}-\d{2}-\d{2})", 文件名)
        if 日期匹配:
            日期字符串 = 日期匹配.group(1)
            try:
                时间戳 = datetime.datetime.strptime(日期字符串, "%Y-%m-%d")
                return 时间戳
            except ValueError as e:
                logger.warning(f"日期解析失败: {文件名}, 错误信息: {e}")
    if 时间戳 is None:
        logger.warning(f"文件名中未找到时间戳或日期: {文件名}")  # 记录日志
    return 时间戳


# 提取日期（从文件名、目录名、文件修改时间）
def 提取日期(文件完整路径, 目录路径=None):
    """
    从文件完整路径和目录路径中提取日期，依次尝试以下方法：
    1. 从文件名中提取日期（支持多种格式：YYYY-MM-DD, YYYY-M-D, YYYY年MM月DD日, YYYY MM DD）。
    2. 从目录名中提取日期（支持多种格式：YYYY-MM-DD, YYYY-M-D, YYYY年MM月DD日, YYYY MM DD）。
    3. 从文件修改时间获取日期。
    """
    文件名 = os.path.basename(文件完整路径)

    # 1. 从文件名中提取日期
    日期 = 提取日期_从名称(文件名)
    if 日期:
        return 日期

    # 2. 从目录名中提取日期
    if 目录路径:
        目录名 = os.path.basename(目录路径)
        日期 = 提取日期_从名称(目录名)
        if 日期:
            return 日期

    # 3. 从文件修改时间获取日期
    日期 = 提取日期_从文件修改时间(文件完整路径)
    if 日期:
        return 日期

    return None


# 从名称中提取日期
def 提取日期_从名称(名称):
    """
    从名称（文件名或目录名）中提取日期，支持以下格式：
    - YYYY-MM-DD
    - YYYY-M-D
    - YYYY年MM月DD日
    - YYYY MM DD
    """
    # 1. 匹配 YYYY-MM-DD 格式
    日期匹配 = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", 名称)
    if 日期匹配:
        日期字符串 = 日期匹配.group(1)
        日期 = 验证日期(日期字符串, "%Y-%m-%d")
        if 日期:
            return 日期

    # 2. 匹配 YYYY年MM月DD日 格式
    日期匹配 = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", 名称)
    if 日期匹配:
        日期字符串 = 日期匹配.group(1)
        日期 = 验证日期(日期字符串, "%Y年%m月%d日")
        if 日期:
            return 日期

    # 3. 匹配 YYYY MM DD 格式
    日期匹配 = re.search(r"(\d{4}\s\d{1,2}\s\d{1,2})", 名称)
    if 日期匹配:
        日期字符串 = 日期匹配.group(1)
        日期 = 验证日期(日期字符串, "%Y %m %d")
        if 日期:
            return 日期

    return None


# 从文件修改时间获取日期
def 提取日期_从文件修改时间(文件路径):
    """从文件修改时间获取日期"""
    try:
        时间戳 = os.path.getmtime(文件路径)
        日期 = datetime.datetime.fromtimestamp(时间戳).strftime("%Y-%m-%d")
        return 日期
    except Exception as e:
        logger.error(f"获取文件修改时间失败: {e}")
        return None


# 验证日期字符串是否有效
def 验证日期(日期字符串, 格式):
    """
    验证日期字符串是否有效，并返回 YYYY-MM-DD 格式的日期字符串。
    """
    try:
        日期对象 = datetime.datetime.strptime(日期字符串, 格式)
        return 日期对象.strftime("%Y-%m-%d")  # 返回 YYYY-MM-DD 格式
    except ValueError:
        return None  # 日期无效


# 检查目录是否包含最近的时间
def 包含_最近文件(目录, 时间差=时间间隔, 现在=None):
    """检查目录下的 PNG 文件是否包含最近的时间差内的文件，并只考虑序号最大的文件名的时间"""
    最近时间戳 = None
    最大序号 = -1  # 初始化最大序号

    if 现在 is None:
        现在 = datetime.datetime.now()

    if not os.path.exists(目录):
        return False  # 如果目录不存在，直接返回 False

    for 文件名 in os.listdir(目录):
        if 文件名.lower().endswith(".png"):
            时间戳 = 提取时间戳_从文件名(文件名)
            if 时间戳:
                # 提取文件名中的序号 (假设文件名格式为 "序号-其他信息.png")
                try:
                    序号 = int(文件名.split("-")[0])  # 提取序号
                except (ValueError, IndexError):
                    序号 = 0  # 如果无法提取序号，则默认为 0

                if 序号 > 最大序号:  # 如果当前序号大于最大序号
                    最大序号 = 序号
                    最近时间戳 = 时间戳  # 更新最近时间戳

    if 最近时间戳:
        时间差值 = 现在 - 最近时间戳
        return 时间差值 <= 时间差
    else:
        return False


# 查找最近输出目录
def 查找_最近输出目录(基础目录, 现在):
    """
    查找包含最近12小时内文件的子目录，并返回当前输出目录和昨天输出目录。
    如果没有找到符合条件的子目录，则返回 "", ""。
    """
    当前输出目录 = ""
    昨天输出目录 = ""
    今天 = 现在.date()
    昨天 = 今天 - datetime.timedelta(days=1)

    # 获取所有子目录
    子目录列表 = [
        os.path.join(基础目录, 目录)
        for 目录 in os.listdir(基础目录)
        if os.path.isdir(os.path.join(基础目录, 目录))
    ]

    for 子目录 in 子目录列表:
        # 使用正则表达式匹配包含日期的目录名
        目录名 = os.path.basename(子目录)
        日期匹配 = re.search(r"(\d{4}-\d{2}-\d{2})", 目录名)  # 匹配 YYYY-MM-DD 格式的日期
        if 日期匹配:
            目录日期字符串 = 日期匹配.group(1)
            try:
                目录日期 = datetime.datetime.strptime(目录日期字符串, "%Y-%m-%d").date()
                if 今天 == 目录日期:
                    当前输出目录 = 子目录
                elif 昨天 == 目录日期:
                    昨天输出目录 = 子目录
            except ValueError:
                logger.warning(f"目录名日期解析失败: {目录名}")  # 记录日志

    return 当前输出目录, 昨天输出目录


# 增量更新文件列表
def 增量更新文件列表(目录, 现有列表):
    """
    增量更新文件列表，只添加新的文件项到现有列表中，并移除已删除的文件。
    """
    新增文件列表 = []
    已删除文件列表 = []

    if not os.path.exists(目录):
        # 如果目录不存在，则认为所有文件都已删除
        已删除文件列表 = 现有列表[:]  # 复制现有列表
        return 新增文件列表, 已删除文件列表

    # 构建当前目录的文件路径集合
    当前目录文件路径集合 = {
        os.path.join(目录, 文件名)
        for 文件名 in os.listdir(目录)
        if 文件名.lower().endswith(".png")
    }

    # 检查新增的文件
    for 文件路径 in 当前目录文件路径集合:
        if not any(
                文件项["path"] == 文件路径 for 文件项 in 现有列表
        ):  # 检查是否已存在于现有列表
            文件名 = os.path.basename(文件路径)
            修改时间戳 = os.path.getmtime(文件路径)


            时间 = datetime.datetime.fromtimestamp(修改时间戳)

            #变量时间差位当前时间减去变量时间精确到秒。
            现在时间 = datetime.datetime.now()
            # 现在时间 = datetime.datetime(2025, 4, 17, 5, 31, 10)




            时间差 = 现在时间 - 时间

            if 时间差.total_seconds() > 5:
                新增文件列表.append(
                    {"filename": 文件名, "path": 文件路径}
                )

    # 检查已删除的文件
    for 文件项 in 现有列表:
        if 文件项["path"] not in 当前目录文件路径集合:
            已删除文件列表.append(文件项)

    return 新增文件列表, 已删除文件列表


# 获取保存目录
def 获取保存目录():
    """获取 ComfyUI 的保存目录"""
    return folder_paths.get_output_directory()

async def 异步逐行读取(进程):
    """异步逐行读取进程的输出"""
    while True:
        行 = await 进程.stdout.readline()
        if not 行:
            break
        行 = 行.decode('utf-8').strip()
        logger.info(f"子进程输出: {行}")
# 检查图片文件完整性
def 检查图片完整性(文件路径):
    """
    检查图片文件是否完整。
    检测完整覆盖一条边，并覆盖部分跳变相邻的两条边的一部分，且这块黑色时完整的，或者检测图中是否存在空的地方。
    """
    try:
        logger.info(f"检查图片完整性:{文件路径}")
        # 代码=f"""
        # import loguru import logger
        # from PIL import Image, ImageStat  # 用于图片完整性检测
        # 文件路径={文件路径}
        #
        # 图片 = Image.open(文件路径)
        # logger.info(f"加载成功")
        # """
        # 安装命令=["python", "-m","pip", "install", "pillow","loguru"]
        # 启动命令=["python", "-c",代码]
        # 安
        图片=PIL.Image.open(文件路径)
        logger.info(f"加载成功")

        if 图片.mode != "RGB":
            logger.warning(f"图片格式不正确: {文件路径}")
            return False
        # 图片.verify()  # 验证文件是否损坏

        宽度, 高度 = 图片.size
        像素数据 = 图片.load()

        # 检查完整覆盖一条边 (例如，顶部)
        for x in range(宽度):
            r, g, b = 像素数据[x, 0]
            if r == 0 and g == 0 and b == 0:  # 检查黑色像素
                pass  # 黑色像素，继续检查
            else:
                logger.warning(f"顶部边缘不完整: {文件路径} ({x}, 0)")
                return False  # 顶部边缘不完整

        # 检查覆盖部分跳变相邻的两条边的一部分 (例如，左侧和右侧)
        for y in range(高度 // 4):  # 只检查一部分
            r, g, b = 像素数据[0, y]  # 左侧
            if r == 0 and g == 0 and b == 0:  # 检查黑色像素
                pass  # 黑色像素，继续检查
            else:
                logger.warning(f"左侧边缘不完整: {文件路径} (0, {y})")
                return False  # 左侧边缘不完整

            r, g, b = 像素数据[宽度 - 1, y]  # 右侧
            if r == 0 and g == 0 and b == 0:  # 检查黑色像素
                pass  # 黑色像素，继续检查
            else:
                logger.warning(f"右侧边缘不完整: {文件路径} ({宽度 - 1}, {y})")
                return False  # 右侧边缘不完整

        # 检查图中是否存在空的地方 (使用图像统计)
        统计 = ImageStat.Stat(图片.convert("L"))  # 转换为灰度图像
        平均亮度 = 统计.mean[0]
        if 平均亮度 > 240:  # 如果平均亮度很高，可能存在大面积空白
            logger.warning(f"图像可能存在大面积空白: {文件路径}, 平均亮度: {平均亮度}")
            return False  # 可能存在大面积空白

        return True  # 所有检查通过，认为完整

    except Exception as e:
        raise
        return False


# 查找最近目录
def 查找最近目录(日期字符串, 所有目录):
    """
    查找与给定日期最接近的目录。
    """
    目标日期 = datetime.datetime.strptime(日期字符串, "%Y-%m-%d").date()
    最近目录 = None
    最小日期差 = float('inf')

    for 目录 in 所有目录:
        try:
            目录日期 = datetime.datetime.strptime(os.path.basename(目录), "%Y-%m-%d").date()  # 假设目录名是日期
            日期差 = abs((目标日期 - 目录日期).days)
            if 日期差 < 最小日期差:
                最小日期差 = 日期差
                最近目录 = 目录
        except ValueError:
            # 忽略无法解析为日期的目录
            pass

    return 最近目录
