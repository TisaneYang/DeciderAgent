"""
DeciderAgent: 基于多模态LLM的驾驶决策Agent
核心类，封装后端调用逻辑
"""

from typing import Optional, List, Dict, Any
from collections import deque
import time

from backends import CameraImages, DecisionResult, LLMBackend, create_backend
from config import DEFAULT_BACKEND, API_KEYS, DEFAULT_MODELS, MAX_HISTORY_SIZE, ENABLE_MEMORY, MAX_IMAGE_HISTORY, VALID_DECISIONS


class DeciderAgent:
    """驾驶决策Agent"""

    def __init__(
        self,
        backend_type: str = DEFAULT_BACKEND,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_memory: bool = ENABLE_MEMORY,
        max_history_size: int = MAX_HISTORY_SIZE,
        max_image_history: int = MAX_IMAGE_HISTORY
    ):
        """
        初始化DeciderAgent

        Args:
            backend_type: LLM后端类型 ("anthropic", "openai", "gemini", "qwen", "deepseek")
            api_key: API密钥，不提供则从环境变量读取
            model: 模型名称，不提供则使用默认模型
            enable_memory: 是否启用上下文记忆功能
            max_history_size: 滑动窗口大小，保留最近N次决策的对话历史
            max_image_history: 保留最近N轮的图像数据（更早的历史只保留文本）
        """
        self.backend_type = backend_type
        self.enable_memory = enable_memory
        self.max_history_size = max_history_size
        self.max_image_history = max_image_history

        # 使用deque实现滑动窗口
        self.conversation_history: deque = deque(maxlen=max_history_size * 2)  # *2因为每次包含user和assistant

        # 待处理的用户指令队列
        self.pending_instructions: List[str] = []

        # 持久化的上游任务拓扑上下文（仅用于每轮注入，不做状态机维护）
        self.current_mermaid: str = ""
        self.task_context_meta: Dict[str, Any] = {
            "updated_at": None,
            "source": "none",
        }

        # 记录上次请求的时间戳（用于计算时间间隔）
        self.last_timestamp: Optional[str] = None

        # 获取API密钥
        if api_key is None:
            api_key = API_KEYS.get(backend_type, "")
            if not api_key:
                raise ValueError(
                    f"未提供API密钥，请设置环境变量或传入api_key参数。"
                    f"后端 '{backend_type}' 需要的环境变量请参考config.py"
                )

        # 创建后端实例
        self.backend: LLMBackend = create_backend(
            backend_type=backend_type,
            api_key=api_key,
            model=model
        )

        self.model = model or DEFAULT_MODELS[backend_type]

    @staticmethod
    def _build_allowed_decisions_instruction(allowed_decisions: Optional[List[str]]) -> str:
        """构造本轮决策硬约束文本。"""
        if not allowed_decisions:
            return ""
        valid_allowed = [d for d in allowed_decisions if d in VALID_DECISIONS]
        if not valid_allowed:
            return ""
        joined = ", ".join(f'"{d}"' for d in valid_allowed)
        return (
            "本轮决策硬约束：allowed_decisions = "
            f"[{joined}]。你必须且只能从该集合中选择decision。"
        )

    def decide(self, images: CameraImages) -> DecisionResult:
        """
        根据四个摄像头图像做出驾驶决策

        Args:
            images: 四个摄像头的图像（可包含客户端提供的Unix时间戳）

        Returns:
            DecisionResult: 包含analysis, decision, raw_response
        """
        # 构建时间信息（使用客户端提供的Unix时间戳）
        time_info = ""
        if images.timestamp:
            try:
                # 将Unix时间戳字符串转换为浮点数
                current_timestamp = float(images.timestamp)

                # 转换为可读的时间格式
                from datetime import datetime
                dt = datetime.fromtimestamp(current_timestamp)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                time_info = f"[时间戳: {time_str}]"

                # 如果有上次时间戳，计算时间间隔
                if self.last_timestamp:
                    try:
                        last_timestamp = float(self.last_timestamp)
                        time_delta = current_timestamp - last_timestamp
                        time_info += f" (距上次请求: {time_delta:.3f}秒)"
                    except (ValueError, TypeError):
                        pass

                # 更新上次时间戳
                self.last_timestamp = images.timestamp

            except (ValueError, TypeError):
                # 如果时间戳格式无法解析，只显示原始值
                time_info = f"[时间戳: {images.timestamp}]"
                self.last_timestamp = images.timestamp

        # 准备历史记录（如果启用记忆功能）
        history = None
        if self.enable_memory:
            # 构建历史记录，只保留最近max_image_history轮的图像数据
            history = []
            total_conversations = len(self.conversation_history) // 2

            for i, msg in enumerate(self.conversation_history):
                # 计算这条消息属于第几轮对话（从0开始）
                conversation_index = i // 2
                # 计算距离当前的轮数
                rounds_ago = total_conversations - conversation_index

                # 如果是用户消息且包含图像数据
                if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                    # 如果超过max_image_history轮，移除图像数据，只保留文本
                    if rounds_ago > self.max_image_history:
                        # 提取文本部分
                        text_content = []
                        for item in msg["content"]:
                            if item.get("type") == "text":
                                text_content.append(item["text"])

                        # 只保留文本摘要
                        history.append({
                            "role": "user",
                            "content": " ".join(text_content) if text_content else "请分析当前四个摄像头的图像并给出驾驶决策。"
                        })
                    else:
                        # 保留完整的图像数据
                        history.append(msg)
                else:
                    # 助手响应或纯文本消息，直接保留
                    history.append(msg)

        # 构建当前任务上下文指令，并消费待处理指令
        instructions = self.consume_instructions()
        task_context = self.build_task_context_instruction()
        if task_context:
            instructions.insert(0, task_context)

        # 调用后端进行决策（传入时间信息和指令）
        result = self.backend.decide(images, history, time_info, instructions)

        # 要求LLM单独输出自然语言意图字段；若缺失则做保底生成，避免下游出现空值。
        intention_nl = str(result.parsed_response.get("intention_nl", "")).strip()
        if not intention_nl:
            intention_nl = self._build_fallback_intention_nl(decision=result.decision)
        result.intention_nl = intention_nl
        result.parsed_response["intention_nl"] = intention_nl

        # 更新对话历史（如果启用记忆功能）
        if self.enable_memory:
            # 先将指令消息加入历史（在图像消息之前）
            from prompts import USER_INSTRUCTION_MESSAGE
            for inst in instructions:
                self.conversation_history.append({
                    "role": "user",
                    "content": USER_INSTRUCTION_MESSAGE.format(instruction=inst)
                })

            # 构建包含图像数据和时间戳的用户消息
            user_message_content = self.backend.build_image_content(images, time_info)

            # 添加用户消息（包含完整图像数据）
            self.conversation_history.append({
                "role": "user",
                "content": user_message_content
            })
            # 添加助手响应
            self.conversation_history.append({
                "role": "assistant",
                "content": result.raw_response
            })

        return result

    def decide_with_constraints(
        self,
        images: CameraImages,
        allowed_decisions: Optional[List[str]] = None
    ) -> DecisionResult:
        """
        根据四个摄像头图像做出驾驶决策（带本轮动作约束）。

        Args:
            images: 四个摄像头的图像
            allowed_decisions: 本轮允许的决策集合（可选）

        Returns:
            DecisionResult
        """
        if not allowed_decisions:
            return self.decide(images)

        allowed_instruction = self._build_allowed_decisions_instruction(allowed_decisions)
        if allowed_instruction:
            self.pending_instructions.insert(0, allowed_instruction)

        return self.decide(images)

    def decide_from_paths(
        self,
        front_path: str,
        left_path: str,
        right_path: str,
        rear_path: str,
        timestamp: Optional[str] = None,
        allowed_decisions: Optional[List[str]] = None
    ) -> DecisionResult:
        """
        便捷方法：直接传入四个图像路径

        Args:
            front_path: 前置摄像头图像路径
            left_path: 左侧摄像头图像路径
            right_path: 右侧摄像头图像路径
            rear_path: 后置摄像头图像路径
            timestamp: 客户端提供的时间戳（可选）
            allowed_decisions: 本轮允许的决策集合（可选）

        Returns:
            DecisionResult: 包含analysis, decision, raw_response
        """
        images = CameraImages(
            front=front_path,
            left=left_path,
            right=right_path,
            rear=rear_path,
            timestamp=timestamp
        )
        return self.decide_with_constraints(images, allowed_decisions)

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.last_timestamp = None

    def add_instruction(self, instruction: str) -> None:
        """添加用户自然语言指令（兼容接口：覆盖当前mermaid上下文）。"""
        self.replace_task_plan({
            "instruction": instruction,
            "plan": {"summary": instruction, "execution_mode": "manual_instruction"},
        })

    def get_pending_instructions(self) -> List[str]:
        """获取待处理指令（兼容接口）"""
        return self.pending_instructions.copy()

    def clear_instructions(self) -> None:
        """清除待处理指令与当前任务拓扑上下文。"""
        self.pending_instructions.clear()
        self.current_mermaid = ""
        self.task_context_meta = {"updated_at": None, "source": "none"}

    def consume_instructions(self) -> List[str]:
        """获取并清空待处理指令（一次性消费）"""
        instructions = self.pending_instructions.copy()
        self.pending_instructions.clear()
        return instructions

    @staticmethod
    def _extract_task_topology(payload: Dict[str, Any]) -> str:
        """提取上游任务拓扑文本（优先mermaid原文，其次结构化任务清单）。"""
        plan = payload.get("plan")
        candidates: List[Any] = []
        if isinstance(plan, dict):
            candidates.extend([
                plan.get("mermaid"),
                plan.get("topology"),
                plan.get("task_topology"),
                plan.get("graph"),
                plan.get("raw"),
            ])
        elif isinstance(plan, str):
            candidates.append(plan)

        for candidate in candidates:
            text = str(candidate or "").strip()
            if text:
                return text

        # 若上游未提供mermaid原文，使用结构化任务生成稳定文本
        source_tasks = payload.get("tasks") or []
        lines = []
        for index, task in enumerate(source_tasks, start=1):
            task_id = str(task.get("task_id", f"t{index}")).strip()
            desc = str(task.get("description", "")).strip()
            if not desc:
                continue
            lines.append(f"{task_id}:{desc}")
        return " -> ".join(lines)

    def replace_task_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """覆盖式刷新任务上下文（仅保留mermaid/任务文本，不做状态迁移）。"""
        mermaid = self._extract_task_topology(payload)
        self.current_mermaid = mermaid
        self.task_context_meta = {
            "updated_at": time.time(),
            "source": "instruct",
        }

        # 新任务上下文到达后，清空待处理指令，避免旧指令污染。
        self.pending_instructions.clear()
        return self.get_task_plan_state()

    def get_task_plan_state(self) -> Dict[str, Any]:
        """获取当前任务上下文状态快照（轻量）。"""
        return {
            "mermaid_context": self.current_mermaid,
            "has_mermaid_context": bool(self.current_mermaid.strip()),
            "updated_at": self.task_context_meta.get("updated_at"),
            "source": self.task_context_meta.get("source", "none"),
        }

    def build_task_context_instruction(self) -> str:
        """构建当前任务上下文（每轮注入LLM，仅用于推理参考）。"""
        mermaid = self.current_mermaid.strip()
        if not mermaid:
            return ""

        return (
            "当前上游任务拓扑（仅供参考，不是代码侧状态机）："
            f"{mermaid}。"
            "task_update字段仅作为本轮推理说明，不作为系统真实状态源。"
            "请严格输出task_update字段，且只包含status/reason/confidence/progress_score。"
            "请额外输出intention_nl字段，内容必须包含：当前驾驶意图、本轮请求来源。"
        )

    def _build_fallback_intention_nl(self, decision: str) -> str:
        """当LLM未返回intention_nl时，提供稳定保底文本。"""
        source = "上游mermaid任务" if self.current_mermaid.strip() else "当前视觉场景"
        return f"当前驾驶意图：{decision}；本轮请求来源：{source}。"

    def get_history_summary(self) -> Dict[str, Any]:
        """
        获取历史记录摘要

        Returns:
            包含历史记录统计信息的字典
        """
        total_conversations = len(self.conversation_history) // 2

        # 统计包含图像的轮数
        image_rounds = 0
        for i, msg in enumerate(self.conversation_history):
            if msg.get("role") == "user" and isinstance(msg.get("content"), list):
                # 检查是否包含图像
                has_image = any(
                    item.get("type") in ["image", "image_url"]
                    for item in msg["content"]
                    if isinstance(item, dict)
                )
                if has_image:
                    image_rounds += 1

        return {
            "total_conversations": total_conversations,
            "max_history_size": self.max_history_size,
            "max_image_history": self.max_image_history,
            "image_rounds_stored": image_rounds,
            "memory_enabled": self.enable_memory,
            "task_context": self.get_task_plan_state(),
            "history": list(self.conversation_history)
        }

    def __repr__(self) -> str:
        memory_status = f", memory={'on' if self.enable_memory else 'off'}"
        if self.enable_memory:
            total = len(self.conversation_history) // 2
            memory_status += f"({total}/{self.max_history_size}, img:{self.max_image_history})"
        return f"DeciderAgent(backend={self.backend_type}, model={self.model}{memory_status})"
