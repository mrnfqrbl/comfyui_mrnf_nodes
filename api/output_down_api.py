# api/output_down_api.py
import concurrent
import threading
import PIL
# import gec
import time

from aiohttp import web
from server import PromptServer
import os
import datetime
import logging
import asyncio  # 导入 asyncio
import random
import string
from ..utils.output_down_utils import (  # 导入工具函数
    获取保存目录,
    查找_最近输出目录,
    增量更新文件列表,
    检查图片完整性,  # 导入图片完整性检测函数
    获取文件_md5  # 导入获取文件 MD5 函数
)
from loguru import logger
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger("mrnf")



# 全局变量定义
当前输出目录 = ""  # 当前输出目录
昨天输出目录 = ""  # 昨天输出目录
保存目录 = ""  # 保存目录
上次更新时间 = None  # 上次更新目录信息的时间
当前输出目录_png_文件列表 = []  # 存储当前输出目录的 PNG 文件列表
昨天输出目录_png_文件列表 = []  # 存储昨天输出目录的 PNG 文件列表
文件序号计数器 = 1  # 文件序号计数器
# 定义线程池大小
图像验证线程池大小 = 10

# 创建图像验证线程池
图像验证线程池 = concurrent.futures.ThreadPoolExecutor(max_workers=图像验证线程池大小)

# 创建一个线程锁，用于保护对 Pillow 库的访问
图片锁 = threading.Lock()
# 生成随机 ID
def 生成随机_id():
    """生成随机 ID，由顺序序号 + 3 位随机字母组成"""
    global 文件序号计数器
    随机字母 = ''.join(random.choices(string.ascii_lowercase, k=3))
    id = str(文件序号计数器) + 随机字母
    文件序号计数器 += 1
    return id

# 更新全局目录信息
def 更新全局目录信息(现在=None):
    """更新全局变量中的目录信息"""
    global 当前输出目录, 昨天输出目录, 保存目录, 上次更新时间, 当前输出目录_png_文件列表, 昨天输出目录_png_文件列表
    # 模拟现在是2025-04-18
    # 现在= datetime.datetime(2025, 4, 18)
    if 现在 is None:
        现在 = datetime.datetime.now()

    保存目录 = 获取保存目录()
    if not os.path.exists(保存目录):
        os.makedirs(保存目录)
    新的当前输出目录, 新的昨天输出目录 = 查找_最近输出目录(保存目录, 现在)
    # logger.info(f"更新全局目录信息: 当前输出目录={新的当前输出目录}, 昨天输出目录={新的昨天输出目录}")
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
    for 文件项 in 新增当前输出目录_文件:
        文件项['id'] = 生成随机_id()  # 生成随机 ID
        文件项['状态'] = '不完整'  # 初始状态为不完整
        当前输出目录_png_文件列表.append(文件项)
        # 异步检测图片完整性
        asyncio.create_task(异步检测图片完整性(文件项))

    for 文件项 in 新增昨天输出目录_文件:
        文件项['id'] = 生成随机_id()  # 生成随机 ID
        文件项['状态'] = '不完整'  # 初始状态为不完整
        昨天输出目录_png_文件列表.append(文件项)
        # 异步检测图片完整性
        asyncio.create_task(异步检测图片完整性(文件项))

    # 移除已删除的文件
    for 文件项 in 已删除当前输出目录_文件:
        if 文件项 in 当前输出目录_png_文件列表:  # 确保文件项存在于列表中
            当前输出目录_png_文件列表.remove(文件项)
            logger.info(f"文件已删除: {文件项['path']}")

    for 文件项 in 已删除昨天输出目录_文件:
        if 文件项 in 昨天输出目录_png_文件列表:  # 确保文件项存在于列表中
            昨天输出目录_png_文件列表.remove(文件项)
            logger.info(f"文件已删除: {文件项['path']}")


# 异步检测图片完整性

async def 异步检测图片完整性(文件项):
    """异步检测图片完整性，并在检测通过后更新状态和 MD5"""
    文件路径 = 文件项['path']

    if 检查图片完整性(文件路径):
        文件项['状态'] = '完整'
        文件项['md5'] = 获取文件_md5(文件路径)  # 确定完整后再生成 MD5
        logger.info(f"文件完整性检测通过: {文件路径}")
    else:
        文件项['状态'] = '损坏'
        logger.warning(f"文件完整性检测失败: {文件路径}")

# 后台任务：定期更新目录信息
async def 定期更新目录信息():
    """定期更新目录信息"""
    while True:
        现在 = datetime.datetime.now()
        更新全局目录信息(现在)
        await asyncio.sleep(20)  # 每隔 10 秒更新一次
        logger.info("图片列表已更新")

# 启动后台任务
async def 启动后台任务():
    """启动后台任务"""
    asyncio.create_task(定期更新目录信息())


i=0
重试次数 = 5
for i in range(重试次数):
    try:
        from server import PromptServer  # 导入放在 try 块中，以便处理 PromptServer 未定义的情况
        if PromptServer.instance:
            循环=asyncio.get_event_loop()
            loop = PromptServer.instance.loop
            logger.info(f"当前读取事件循环对象为:{循环}")
            logger.info(f"服务器事件循环对象为:{loop}")
            # gec.安装异步钩子(loop)
            loop.create_task(启动后台任务())
            logger.info("后台更新列表已启动")

            break

        else:
            logger.warning("PromptServer 尚未初始化，等待 {} 秒后重试...".format(5))
    except Exception as e:
        logger.error(f"尝试启动后台更新列表失败 (第 {i+1} 次): {e}")

        time.sleep(5)
        if i == 重试次数 - 1:
            logger.error("重试 {} 次后，启动后台更新列表仍然失败，放弃启动。".format(重试次数))






# API 路由函数
@PromptServer.instance.routes.get("/mrnf/get")
async def mrnf_api(request):
    """
    API 接口，返回当前输出目录和昨天输出目录下的 PNG 图片列表和 MD5 校验值。
    如果昨天的目录不包含12小时内的图时不再需要昨天的目录了。
    """
    global 当前输出目录, 昨天输出目录, 当前输出目录_png_文件列表, 昨天输出目录_png_文件列表

    # 构造 JSON 响应
    响应数据 = {
        "当前输出目录": 当前输出目录,
        "当前输出目录_png_files": [
            {k: v for k, v in 文件项.items() if k != 'path'}
            for 文件项 in 当前输出目录_png_文件列表
        ],
    }

    # 只有当昨天输出目录不为空时才添加
    if 昨天输出目录:
        响应数据["昨天输出目录"] = 昨天输出目录
        响应数据["昨天输出目录_png_files"] = [
            {k: v for k, v in 文件项.items() if k != 'path'}
            for 文件项 in 昨天输出目录_png_文件列表
        ]

    return web.json_response(响应数据)


@PromptServer.instance.routes.get("/mrnf/down")
async def mrnf_dowm(request):
    """
    API 接口，提供文件下载。
    通过文件名从对应的目录中查找文件并提供下载。
    直接使用文件列表中的完整路径，无需搜索。
    """
    文件名 = request.rel_url.query.get("filename")
    if not 文件名:
        raise web.HTTPBadRequest(text="缺少文件名参数")

    文件路径 = None

    # 在当前输出目录列表中查找文件
    for 文件项 in 当前输出目录_png_文件列表:
        if 文件项["filename"] == 文件名:
            文件路径 = 文件项["path"]
            break

    # 如果当前目录没找到，再在昨天输出目录列表中查找
    if not 文件路径 and 昨天输出目录:
        for 文件项 in 昨天输出目录_png_文件列表:
            if 文件项["filename"] == 文件名:
                文件路径 = 文件项["path"]
                break

    if not 文件路径 or not os.path.isfile(文件路径):
        raise web.HTTPNotFound(text=f"文件未找到: {文件名}")

    try:
        # 构建响应头，设置 Content-Disposition 为 attachment，以便浏览器下载文件
        响应头 = {
            "Content-Disposition": f"attachment; filename=\"{文件名}\""
        }
        # 使用 aiohttp.FileResponse 直接提供文件下载，提高效率
        return web.FileResponse(文件路径, headers=响应头)
    except Exception as e:
        logger.error(f"下载文件出错: {e}")
        raise web.HTTPInternalServerError(text=f"下载文件出错: {e}")


@PromptServer.instance.routes.delete("/mrnf/del_item")
async def mrnf_del_item(request):
    """
    API 接口，删除指定文件。
    接收请求体为 JSON，包含文件名和删除原因。
    """
    try:
        请求体 = await request.json()
        文件名 = 请求体.get("filename")
        删除原因 = 请求体.get("删除原因", "未提供")  # 默认删除原因

        if not 文件名:
            raise web.HTTPBadRequest(text="缺少文件名参数")

        文件路径 = None

        # 在当前输出目录列表中查找文件
        for 文件项 in 当前输出目录_png_文件列表:
            if 文件项["filename"] == 文件名:
                文件路径 = 文件项["path"]
                break

        # 如果当前目录没找到，再在昨天输出目录列表中查找
        if not 文件路径 and 昨天输出目录:
            for 文件项 in 昨天输出目录_png_文件列表:
                if 文件项["filename"] == 文件名:
                    文件路径 = 文件项["path"]
                    break

        if not 文件路径 or not os.path.isfile(文件路径):
            raise web.HTTPNotFound(text=f"文件未找到: {文件名}")

        try:
            os.remove(文件路径)  # 删除文件
            logger.info(f"文件已删除: {文件路径}, 删除原因: {删除原因}")

            # 从文件列表中移除已删除的文件
            for 文件列表 in [当前输出目录_png_文件列表, 昨天输出目录_png_文件列表]:
                for 文件项 in 文件列表:
                    if 文件项["filename"] == 文件名:
                        文件列表.remove(文件项)
                        break

            return web.json_response({"status": "success", "message": f"文件 {文件名} 已成功删除"})

        except Exception as e:
            logger.error(f"删除文件出错: {e}")
            raise web.HTTPInternalServerError(text=f"删除文件出错: {e}")

    except Exception as e:
        logger.error(f"处理删除请求出错: {e}")
        raise web.HTTPBadRequest(text=f"无效的请求: {e}")

# 在 PromptServer 启动时启动后台任务


