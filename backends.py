"""
LLM后端抽象基类和各提供商实现
"""

import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from config import VALID_DECISIONS, DEFAULT_DECISION, MAX_TOKENS
from prompts import SYSTEM_PROMPT, CAMERA_LABELS, ANALYSIS_REQUEST, USER_INSTRUCTION_MESSAGE


@dataclass
class CameraImages:
    """四个摄像头的图像数据"""
    front: str  # 前置摄像头图像路径
    left: str   # 左侧摄像头图像路径
    right: str  # 右侧摄像头图像路径
    rear: str   # 后置摄像头图像路径
    timestamp: Optional[str] = None  # 客户端提供的Unix时间戳字符串（秒，可选）


@dataclass
class DecisionResult:
    """决策结果"""
    analysis: str       # 场景分析
    decision: str       # 决策指令
    raw_response: str   # 原始响应


class LLMBackend(ABC):
    """LLM后端抽象基类"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @staticmethod
    def encode_image(image_path: str) -> tuple[str, str]:
        """
        将图像文件编码为base64

        Args:
            image_path: 图像文件路径

        Returns:
            (base64编码的图像数据, 媒体类型)
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图像文件不存在: {image_path}")

        suffix = path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_type_map.get(suffix, "image/jpeg")

        with open(path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return image_data, media_type

    @abstractmethod
    def build_image_content(self, images: CameraImages, time_info: str = "") -> Any:
        """
        构建包含图像的消息内容（用于保存到历史记录）

        Args:
            images: 四个摄像头的图像
            time_info: 时间戳信息

        Returns:
            消息内容（格式取决于具体后端）
        """
        pass

    @staticmethod
    def parse_response(response_text: str) -> tuple[str, str]:
        """
        解析LLM的响应，提取分析和决策

        Args:
            response_text: LLM的原始响应文本

        Returns:
            (分析文本, 决策指令)
        """
        try:
            text = response_text.strip()
            # 处理markdown代码块
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            result = json.loads(text)
            analysis = result.get("analysis", "")
            decision = result.get("decision", "")

            if decision not in VALID_DECISIONS:
                raise ValueError(f"无效的决策指令: {decision}")

            return analysis, decision

        except (json.JSONDecodeError, KeyError, ValueError):
            # 尝试从文本中提取决策
            for valid_decision in VALID_DECISIONS:
                if valid_decision in response_text:
                    return response_text, valid_decision
            return response_text, DEFAULT_DECISION

    @abstractmethod
    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        """
        调用LLM API

        Args:
            images: 四个摄像头的图像
            history: 对话历史记录（可选）
            time_info: 时间戳信息
            instructions: 用户自然语言指令列表（可选）

        Returns:
            LLM的原始响应文本
        """
        pass

    def decide(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> DecisionResult:
        """
        根据图像做出决策

        Args:
            images: 四个摄像头的图像
            history: 对话历史记录（可选）
            time_info: 时间戳信息
            instructions: 用户自然语言指令列表（可选）

        Returns:
            决策结果
        """
        raw_response = self.call_api(images, history, time_info, instructions)
        analysis, decision = self.parse_response(raw_response)
        return DecisionResult(
            analysis=analysis,
            decision=decision,
            raw_response=raw_response
        )


class AnthropicBackend(LLMBackend):
    """Anthropic Claude 后端"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model)
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)

    def build_image_content(self, images: CameraImages, time_info: str = "") -> List[Dict[str, Any]]:
        """构建包含图像的消息内容"""
        content = []

        # 添加时间戳信息（如果提供）
        if time_info:
            content.append({
                "type": "text",
                "text": time_info
            })

        camera_data = [
            ("front", images.front),
            ("left", images.left),
            ("right", images.right),
            ("rear", images.rear),
        ]

        for cam_id, image_path in camera_data:
            image_data, media_type = self.encode_image(image_path)
            content.append({
                "type": "text",
                "text": f"【{CAMERA_LABELS[cam_id]}】"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data
                }
            })

        content.append({"type": "text", "text": ANALYSIS_REQUEST})
        return content

    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        content = self.build_image_content(images, time_info)

        # 构建消息列表（包含历史记录）
        messages = []
        if history:
            messages.extend(history)

        # 在历史之后、当前图像消息之前，插入指令消息
        if instructions:
            for inst in instructions:
                messages.append({
                    "role": "user",
                    "content": USER_INSTRUCTION_MESSAGE.format(instruction=inst)
                })

        messages.append({"role": "user", "content": content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return response.content[0].text


class OpenAIBackend(LLMBackend):
    """OpenAI GPT-4o 后端"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    def build_image_content(self, images: CameraImages, time_info: str = "") -> List[Dict[str, Any]]:
        """构建包含图像的消息内容"""
        content = []

        # 添加时间戳信息（如果提供）
        if time_info:
            content.append({
                "type": "text",
                "text": time_info
            })

        camera_data = [
            ("front", images.front),
            ("left", images.left),
            ("right", images.right),
            ("rear", images.rear),
        ]

        for cam_id, image_path in camera_data:
            image_data, media_type = self.encode_image(image_path)
            content.append({
                "type": "text",
                "text": f"【{CAMERA_LABELS[cam_id]}】"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}"
                }
            })

        content.append({"type": "text", "text": ANALYSIS_REQUEST})
        return content

    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        content = self.build_image_content(images, time_info)

        # 构建消息列表（包含历史记录）
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)

        # 在历史之后、当前图像消息之前，插入指令消息
        if instructions:
            for inst in instructions:
                messages.append({
                    "role": "user",
                    "content": USER_INSTRUCTION_MESSAGE.format(instruction=inst)
                })

        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=messages
        )
        return response.choices[0].message.content


class GeminiBackend(LLMBackend):
    """Google Gemini 后端"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        super().__init__(api_key, model)
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai

    def build_image_content(self, images: CameraImages, time_info: str = "") -> str:
        """Gemini使用不同的格式，返回图像路径的字符串表示"""
        # Gemini的图像内容在call_api中直接处理
        result = f"front:{images.front},left:{images.left},right:{images.right},rear:{images.rear}"
        if time_info:
            result = f"{time_info}|{result}"
        return result

    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        import PIL.Image

        model = self.genai.GenerativeModel(self.model)

        # 构建内容：文本和图像交替
        content_parts = []
        camera_data = [
            ("front", images.front),
            ("left", images.left),
            ("right", images.right),
            ("rear", images.rear),
        ]

        # 添加系统提示
        content_parts.append(SYSTEM_PROMPT + "\n\n")

        # 添加历史记录（仅文本部分）
        if history:
            for msg in history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, str):
                    content_parts.append(f"[{role}]: {content}\n")

        # 添加指令消息
        if instructions:
            for inst in instructions:
                content_parts.append(f"[user]: {USER_INSTRUCTION_MESSAGE.format(instruction=inst)}\n")

        # 添加时间戳信息（如果提供）
        if time_info:
            content_parts.append(f"{time_info}\n")

        for cam_id, image_path in camera_data:
            content_parts.append(f"【{CAMERA_LABELS[cam_id]}】\n")
            img = PIL.Image.open(image_path)
            content_parts.append(img)

        content_parts.append(ANALYSIS_REQUEST)

        response = model.generate_content(content_parts)
        return response.text


class QwenVLBackend(LLMBackend):
    """阿里云通义千问VL后端"""

    def __init__(self, api_key: str, model: str = "qwen-vl-max"):
        super().__init__(api_key, model)
        from openai import OpenAI
        # 通义千问使用OpenAI兼容接口
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

    def build_image_content(self, images: CameraImages, time_info: str = "") -> List[Dict[str, Any]]:
        """构建包含图像的消息内容"""
        content = []

        # 添加时间戳信息（如果提供）
        if time_info:
            content.append({
                "type": "text",
                "text": time_info
            })

        camera_data = [
            ("front", images.front),
            ("left", images.left),
            ("right", images.right),
            ("rear", images.rear),
        ]

        for cam_id, image_path in camera_data:
            image_data, media_type = self.encode_image(image_path)
            content.append({
                "type": "text",
                "text": f"【{CAMERA_LABELS[cam_id]}】"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}"
                }
            })

        content.append({"type": "text", "text": ANALYSIS_REQUEST})
        return content

    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        content = self.build_image_content(images, time_info)

        # 构建消息列表（包含历史记录）
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)

        # 在历史之后、当前图像消息之前，插入指令消息
        if instructions:
            for inst in instructions:
                messages.append({
                    "role": "user",
                    "content": USER_INSTRUCTION_MESSAGE.format(instruction=inst)
                })

        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=messages
        )
        return response.choices[0].message.content


class DeepSeekBackend(LLMBackend):
    """DeepSeek后端"""

    def __init__(self, api_key: str, model: str = "deepseek-vl"):
        super().__init__(api_key, model)
        from openai import OpenAI
        # DeepSeek使用OpenAI兼容接口
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def build_image_content(self, images: CameraImages, time_info: str = "") -> List[Dict[str, Any]]:
        """构建包含图像的消息内容"""
        content = []

        # 添加时间戳信息（如果提供）
        if time_info:
            content.append({
                "type": "text",
                "text": time_info
            })

        camera_data = [
            ("front", images.front),
            ("left", images.left),
            ("right", images.right),
            ("rear", images.rear),
        ]

        for cam_id, image_path in camera_data:
            image_data, media_type = self.encode_image(image_path)
            content.append({
                "type": "text",
                "text": f"【{CAMERA_LABELS[cam_id]}】"
            })
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}"
                }
            })

        content.append({"type": "text", "text": ANALYSIS_REQUEST})
        return content

    def call_api(self, images: CameraImages, history: Optional[List[Dict[str, Any]]] = None, time_info: str = "", instructions: Optional[List[str]] = None) -> str:
        content = self.build_image_content(images, time_info)

        # 构建消息列表（包含历史记录）
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)

        # 在历史之后、当前图像消息之前，插入指令消息
        if instructions:
            for inst in instructions:
                messages.append({
                    "role": "user",
                    "content": USER_INSTRUCTION_MESSAGE.format(instruction=inst)
                })

        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            messages=messages
        )
        return response.choices[0].message.content


# 后端工厂函数
def create_backend(
    backend_type: str,
    api_key: str,
    model: Optional[str] = None
) -> LLMBackend:
    """
    创建LLM后端实例

    Args:
        backend_type: 后端类型 ("anthropic", "openai", "gemini", "qwen", "deepseek")
        api_key: API密钥
        model: 模型名称（可选，使用默认值）

    Returns:
        LLMBackend实例
    """
    from config import DEFAULT_MODELS

    backends = {
        "anthropic": AnthropicBackend,
        "openai": OpenAIBackend,
        "gemini": GeminiBackend,
        "qwen": QwenVLBackend,
        "deepseek": DeepSeekBackend,
    }

    if backend_type not in backends:
        raise ValueError(f"不支持的后端类型: {backend_type}，支持: {list(backends.keys())}")

    backend_class = backends[backend_type]
    model = model or DEFAULT_MODELS[backend_type]

    return backend_class(api_key=api_key, model=model)
