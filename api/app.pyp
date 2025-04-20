from aiohttp import web
from server import PromptServer
import folder_paths
import os
import datetime
import hashlib
import json
import re
import logging

logger = logging.getLogger(__name__)

# 全局变量定义
时间间隔 = datetime.timedelta(hours=12)  # 定义时间间隔（12小时）
当前输出目录 = ""  # 当前输出目录
昨天输出目录 = ""  # 昨天输出目录
保存目录 = ""  # 保存目录
上次更新时间 = None  # 上次更新目录信息的时间
当前输出目录_png_文件列表 = []  # 存储当前输出目录的 PNG 文件列表
昨天输出目录_png_文件列表 = []  # 存储昨天输出目录的 PNG 文件列表


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
        print(f"计算 MD5 出错: {异常}")
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
            print(f"完整时间戳解析失败: {文件名}, 错误信息: {e}")
    else:
        # 如果没有找到完整时间戳，则匹配只包含年月日的日期
        日期匹配 = re.search(r"(\d{4}-\d{2}-\d{2})", 文件名)
        if 日期匹配:
            日期字符串 = 日期匹配.group(1)
            try:
                时间戳 = datetime.datetime.strptime(日期字符串, "%Y-%m-%d")
                return 时间戳
            except ValueError as e:
                print(f"日期解析失败: {文件名}, 错误信息: {e}")
    if 时间戳 is None:
        print(f"文件名中未找到时间戳或日期: {文件名}")  # 记录日志
    return 时间戳

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
    子目录列表 = [os.path.join(基础目录, 目录) for 目录 in os.listdir(基础目录) if os.path.isdir(os.path.join(基础目录, 目录))]

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
                print(f"目录名日期解析失败: {目录名}")  # 记录日志

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
    当前目录文件路径集合 = {os.path.join(目录, 文件名) for 文件名 in os.listdir(目录) if 文件名.lower().endswith(".png")}

    # 检查新增的文件
    for 文件路径 in 当前目录文件路径集合:
        if not any(文件项["path"] == 文件路径 for 文件项 in 现有列表):  # 检查是否已存在于现有列表
            文件名 = os.path.basename(文件路径)
            md5_哈希值 = 获取文件_md5(文件路径)
            if md5_哈希值:
                新增文件列表.append({"filename": 文件名, "path": 文件路径, "md5": md5_哈希值})

    # 检查已删除的文件
    for 文件项 in 现有列表:
        if 文件项["path"] not in 当前目录文件路径集合:
            已删除文件列表.append(文件项)

    return 新增文件列表, 已删除文件列表

# 更新全局目录信息
def 更新全局目录信息(现在=None):
    """更新全局变量中的目录信息"""
    global 当前输出目录, 昨天输出目录, 保存目录, 上次更新时间, 当前输出目录_png_文件列表, 昨天输出目录_png_文件列表

    if 现在 is None:
        现在 = datetime.datetime.now()

    保存目录 = folder_paths.get_output_directory()
    if not os.path.exists(保存目录):
        os.makedirs(保存目录)
    新的当前输出目录, 新的昨天输出目录 = 查找_最近输出目录(保存目录, 现在)

    # 检查目录是否发生变化
    目录已更改 = (新的当前输出目录 != 当前输出目录) or (新的昨天输出目录 != 昨天输出目录)

    当前输出目录 = 新的当前输出目录
    昨天输出目录 = 新的昨天输出目录
    上次更新时间 = 现在

    # 如果目录发生变化，则清空文件列表，重新扫描
    if 目录已更改:
        当前输出目录_png_文件列表 = []
        昨天输出目录_png_文件列表 = []
        logger.info("目录已更改，重新扫描文件列表")
    else:
        logger.info("目录未更改，增量更新文件列表")

    # 增量更新文件列表
    新增当前输出目录_文件, 已删除当前输出目录_文件 = 增量更新文件列表(当前输出目录, 当前输出目录_png_文件列表)
    新增昨天输出目录_文件, 已删除昨天输出目录_文件 = 增量更新文件列表(昨天输出目录, 昨天输出目录_png_文件列表)

    # 添加新增的文件
    当前输出目录_png_文件列表.extend(新增当前输出目录_文件)
    昨天输出目录_png_文件列表.extend(新增昨天输出目录_文件)

    # 移除已删除的文件
    for 文件项 in 已删除当前输出目录_文件:
        if 文件项 in 当前输出目录_png_文件列表:  # 确保文件项存在于列表中
            当前输出目录_png_文件列表.remove(文件项)
            logger.info(f"文件已删除: {文件项['path']}")

    for 文件项 in 已删除昨天输出目录_文件:
        if 文件项 in 昨天输出目录_png_文件列表:  # 确保文件项存在于列表中
            昨天输出目录_png_文件列表.remove(文件项)
            logger.info(f"文件已删除: {文件项['path']}")


# API 路由函数
@PromptServer.instance.routes.get("/mrnf/get")
async def mrnf_api(request):
    """
    API 接口，返回当前输出目录和昨天输出目录下的 PNG 图片列表和 MD5 校验值。
    如果昨天的目录不包含12小时内的图时不再需要昨天的目录了。
    """
    global 当前输出目录, 昨天输出目录, 保存目录, 上次更新时间, 当前输出目录_png_文件列表, 昨天输出目录_png_文件列表

    # 现在 = datetime.datetime.now()
    # 模拟现在为2025-04-18-05--30-30
    现在 = datetime.datetime(2025, 4, 18, 5, 30, 30)

    # 检查是否需要更新目录信息 (例如，每隔一段时间更新一次)

    更新全局目录信息(现在)
    logger.info("更新全局目录信息")

    logger.info(f"当前输出目录: {当前输出目录}")
    logger.info(f"昨天输出目录: {昨天输出目录}")

    # 构造 JSON 响应
    响应数据 = {
        "当前输出目录": 当前输出目录,
        "当前输出目录_png_files": 当前输出目录_png_文件列表,
        "保存目录": 保存目录,
    }

    # 只有当昨天输出目录不为空时才添加
    if 昨天输出目录:
        响应数据["昨天输出目录"] = 昨天输出目录
        响应数据["昨天输出目录_png_files"] = 昨天输出目录_png_文件列表

    return web.json_response(响应数据)


@PromptServer.instance.routes.get("/mrnf/down")
async def mrnf_dowm(request):
    """
    API 接口，提供文件下载。
    通过文件名从对应的目录中查找文件并提供下载。
    """
    global 当前输出目录, 昨天输出目录, 保存目录, 当前输出目录_png_文件列表, 昨天输出目录_png_文件列表

    文件名 = request.rel_url.query.get("filename")
    if not 文件名:
        raise web.HTTPBadRequest(text="缺少文件名参数")

    文件路径 = None

    # 先在当前输出目录查找
    if 当前输出目录:
        尝试路径 = os.path.join(当前输出目录, 文件名)
        if os.path.isfile(尝试路径):
            文件路径 = 尝试路径

    # 如果当前目录没找到，再在昨天输出目录查找
    if not 文件路径 and 昨天输出目录:
        尝试路径 = os.path.join(昨天输出目录, 文件名)
        if os.path.isfile(尝试路径):
            文件路径 = 尝试路径

    if not 文件路径:
        raise web.HTTPNotFound(text=f"文件未找到: {文件名}")

    try:
        # 构建响应头，设置 Content-Disposition 为 attachment，以便浏览器下载文件
        响应头 = {
            "Content-Disposition": f"attachment; filename=\"{文件名}\""
        }
        return web.FileResponse(文件路径, headers=响应头)
    except Exception as e:
        logger.error(f"下载文件出错: {e}")
        raise web.HTTPInternalServerError(text=f"下载文件出错: {e}")
