import io
import base64
from PIL import Image
import numpy as np
import torch
import re

class 图像加载API:
    """
    自定义节点：图像加载API

    接收 Base64 编码的图像数据，并将其转换为 ComfyUI 中标准的
    IMAGE 类型 (torch.Tensor, float32, 0.0 到 1.0, RGB, (batch, height, width, channels))。
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "base64_图像": ("STRING", {
                    "multiline": True, # 允许长字符串
                    "default": ""
                })  # 添加 Base64 图像输入，并设置默认值
            },
        }

    RETURN_TYPES = ("IMAGE",)  # 只返回 ComfyUI 图像格式
    RETURN_NAMES = ("图像",)
    FUNCTION = "加载图像"
    CATEGORY = "我的节点"  # 自定义分类
    OUTPUT_NODE = True  # 声明这是一个输出节点

    def 加载图像(self, base64_图像):
        """
        加载 Base64 编码的图像数据并转换为 ComfyUI 中标准的 IMAGE 类型。

        Args:
            base64_图像 (str): Base64 编码的图像数据。

        Returns:
            tuple: 包含 ComfyUI 图像格式的张量。
        """
        image_tensor = None
        image = None

        try:
            # 直接处理包含 Data URL 前缀的 Base64 字符串
            图像数据 = base64.b64decode(base64_图像.split(',')[1])
            image = Image.open(io.BytesIO(图像数据))

            # 转换为 NumPy 数组，并缩放到 0.0 到 1.0 范围
            图像_np = np.array(image).astype(np.float32) / 255.0

            # 转换为 ComfyUI 图像格式 (torch.Tensor)
            图像_tensor = torch.from_numpy(图像_np).unsqueeze(0)  # 添加批次维度

            # 调整维度顺序为 (batch, height, width, channels)
            图像_tensor = 图像_tensor.permute(0, 1, 2, 3)

        except Exception as e:
            print(f"图像加载失败: {e}")
            return (torch.zeros([64,64,3]),)  # 返回一个黑色图像

        return (图像_tensor,)  # 返回 ComfyUI 图像格式的张量

    @classmethod
    def VALIDATE_INPUTS(s, base64_图像):
        # 在这里可以添加输入验证逻辑
        # 例如，检查 Base64 字符串是否有效
        try:
            # 直接处理包含 Data URL 前缀的 Base64 字符串
            base64.b64decode(base64_图像.split(',')[1])
        except Exception as e:
            return "Base64 字符串无效"
        return True

# ComfyUI 注册信息
NODE_CLASS_MAPPINGS = {
    "图像加载API": 图像加载API
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "图像加载API": "图像加载 API (Base64 输入 - 默认值)"
}
