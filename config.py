"""
配置文件：API密钥、模型选择等
"""

import os
from typing import Literal

# 支持的LLM后端类型
BackendType = Literal["anthropic", "openai", "gemini", "qwen", "deepseek"]

# 默认后端
DEFAULT_BACKEND: BackendType = "qwen"

# API密钥配置（优先从环境变量读取）
API_KEYS = {
    "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
    "openai": os.getenv("OPENAI_API_KEY", ""),
    "gemini": os.getenv("GOOGLE_API_KEY", ""),
    "qwen": os.getenv("DASHSCOPE_API_KEY", "sk-2ba18455e015465c9aea9048161aa766"),  # 阿里云通义千问
    "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
}

# 各后端默认模型
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "gemini": "gemini-1.5-pro",
    "qwen": "qwen3.6-35b-a3b",
    "deepseek": "deepseek-vl",
}

# 有效的决策指令
VALID_DECISIONS = [
    "PADDING",           # 上层明确要求停车/刹停时使用
    "Lane follow",       # 沿车道线行驶
    "Left change lane",  # 左变道
    "Right change lane", # 右变道
    "Left turn",         # 路口左转
    "Right turn",        # 路口右转
    "Straight",          # 路口直行
]

# 默认决策（当解析失败时使用）
DEFAULT_DECISION = "Lane follow"

# API调用配置
MAX_TOKENS = 1024

# 上下文记忆配置
MAX_HISTORY_SIZE = 5  # 滑动窗口大小，保留最近N次决策的对话历史
ENABLE_MEMORY = True  # 是否启用上下文记忆功能
MAX_IMAGE_HISTORY = 2  # 保留最近N轮的图像数据（更早的历史只保留文本）
