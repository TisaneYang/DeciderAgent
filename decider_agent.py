"""
DeciderAgent: 基于多模态LLM的驾驶决策Agent
核心类，封装后端调用逻辑
"""

from typing import Optional, List, Dict, Any
from collections import deque
import copy
import time
import uuid

from backends import CameraImages, DecisionResult, LLMBackend, create_backend
from config import DEFAULT_BACKEND, API_KEYS, DEFAULT_MODELS, MAX_HISTORY_SIZE, ENABLE_MEMORY, MAX_IMAGE_HISTORY


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

        # 任务执行状态（由代码维护，LLM每轮只输出状态更新建议）
        self.plan_version: int = 0
        self.active_task_plan: Dict[str, Any] = self._empty_task_plan()

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

        # 根据LLM输出尝试更新任务状态
        self.apply_task_update(result.task_update)

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

    def decide_from_paths(
        self,
        front_path: str,
        left_path: str,
        right_path: str,
        rear_path: str,
        timestamp: Optional[str] = None
    ) -> DecisionResult:
        """
        便捷方法：直接传入四个图像路径

        Args:
            front_path: 前置摄像头图像路径
            left_path: 左侧摄像头图像路径
            right_path: 右侧摄像头图像路径
            rear_path: 后置摄像头图像路径
            timestamp: 客户端提供的时间戳（可选）

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
        return self.decide(images)

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.last_timestamp = None

    def add_instruction(self, instruction: str) -> None:
        """添加用户自然语言指令（兼容接口：会重置任务列表为单任务）。"""
        self.replace_task_plan({
            "instruction": instruction,
            "tasks": [{"description": instruction, "time_limit": 15}],
            "plan": {"summary": instruction, "execution_mode": "manual_instruction"},
        })

    def get_pending_instructions(self) -> List[str]:
        """获取待处理指令（兼容接口）"""
        return self.pending_instructions.copy()

    def clear_instructions(self) -> None:
        """清除所有待处理指令和任务计划"""
        self.pending_instructions.clear()
        self.active_task_plan = self._empty_task_plan()

    def consume_instructions(self) -> List[str]:
        """获取并清空待处理指令（一次性消费）"""
        instructions = self.pending_instructions.copy()
        self.pending_instructions.clear()
        return instructions

    def _empty_task_plan(self) -> Dict[str, Any]:
        """返回空任务计划。"""
        return {
            "plan_id": "",
            "plan_version": self.plan_version,
            "scene_type": None,
            "risk_level": None,
            "should_intervene": None,
            "traffic_command": None,
            "plan": {},
            "tasks": [],
            "current_task_index": 0,
            "global_status": "idle",
            "updated_at": None,
        }

    def replace_task_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """覆盖式刷新任务列表（新指令到达时替换，不追加）。"""
        self.plan_version += 1
        now_ts = time.time()

        source_tasks = payload.get("tasks") or []
        if not source_tasks:
            instruction = (
                payload.get("instruction")
                or payload.get("description")
                or payload.get("advice")
                or payload.get("traffic_command")
            )
            if instruction:
                source_tasks = [{"description": instruction, "time_limit": 15}]

        tasks: List[Dict[str, Any]] = []
        for index, task in enumerate(source_tasks):
            description = str(task.get("description", "")).strip()
            if not description:
                continue
            try:
                time_limit = max(1, int(task.get("time_limit", 15)))
            except (TypeError, ValueError):
                time_limit = 15
            tasks.append({
                "task_id": f"t{index + 1}",
                "description": description,
                "time_limit": time_limit,
                "status": "pending",
                "start_ts": None,
                "elapsed": 0.0,
                "progress_score": 0.0,
                "completion_confidence": 0.0,
                "completion_reason": "",
                "evidence": [],
            })

        if tasks:
            tasks[0]["status"] = "running"
            tasks[0]["start_ts"] = now_ts

        self.active_task_plan = {
            "plan_id": payload.get("plan_id") or f"plan_{uuid.uuid4().hex[:8]}",
            "plan_version": self.plan_version,
            "scene_type": payload.get("scene_type"),
            "risk_level": payload.get("risk_level"),
            "should_intervene": payload.get("should_intervene"),
            "traffic_command": payload.get("traffic_command"),
            "plan": payload.get("plan", {}),
            "tasks": tasks,
            "current_task_index": 0,
            "global_status": "running" if tasks else "idle",
            "updated_at": now_ts,
        }

        # 新计划到达后，历史文本队列清空，避免旧上下文污染。
        self.pending_instructions.clear()
        return self.get_task_plan_state()

    def get_task_plan_state(self) -> Dict[str, Any]:
        """获取任务计划状态快照。"""
        plan = copy.deepcopy(self.active_task_plan)
        tasks = plan.get("tasks", [])
        idx = plan.get("current_task_index", 0)
        if tasks and 0 <= idx < len(tasks):
            plan["current_task"] = copy.deepcopy(tasks[idx])
        else:
            plan["current_task"] = None
        return plan

    def build_task_context_instruction(self) -> str:
        """构建当前任务上下文（每轮注入LLM）。"""
        state = self.get_task_plan_state()
        tasks = state.get("tasks", [])
        if not tasks:
            return ""

        current = state.get("current_task")
        if current and current.get("start_ts"):
            current["elapsed"] = max(0.0, time.time() - float(current["start_ts"]))
        remaining = [
            f"{task['task_id']}:{task['description']}"
            for task in tasks[state["current_task_index"] + 1:]
        ]
        completed = [
            f"{task['task_id']}:{task['description']}"
            for task in tasks
            if task.get("status") == "done"
        ]

        return (
            "当前任务计划上下文："
            f"plan_version={state.get('plan_version')}；"
            f"current_task={current.get('task_id') if current else 'none'}；"
            f"current_description={current.get('description') if current else 'none'}；"
            f"current_status={current.get('status') if current else 'none'}；"
            f"current_elapsed={current.get('elapsed') if current else 0:.2f}s；"
            f"current_time_limit={current.get('time_limit') if current else 0}s；"
            f"completed={completed if completed else 'none'}；"
            f"remaining={remaining if remaining else 'none'}。"
            "请严格输出task_update字段，且只包含status/reason/confidence/progress_score。"
        )

    def apply_task_update(self, task_update: Optional[Dict[str, Any]]) -> None:
        """应用LLM返回的任务状态更新。"""
        if not task_update:
            return

        tasks = self.active_task_plan.get("tasks", [])
        idx = self.active_task_plan.get("current_task_index", 0)
        if not tasks or idx >= len(tasks):
            return

        current_task = tasks[idx]
        now_ts = time.time()
        if current_task.get("start_ts") is None:
            current_task["start_ts"] = now_ts
        current_task["elapsed"] = max(0.0, now_ts - float(current_task.get("start_ts") or now_ts))

        def _safe_float(value: Any, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        status = str(task_update.get("status", "")).strip().lower()
        confidence = _safe_float(task_update.get("confidence", 0.0), 0.0)
        progress_score = _safe_float(task_update.get("progress_score", 0.0), 0.0)
        reason = str(task_update.get("reason", "")).strip()

        if reason:
            current_task["completion_reason"] = reason
        current_task["completion_confidence"] = max(0.0, min(1.0, confidence))
        current_task["progress_score"] = max(0.0, min(1.0, progress_score))

        if status in {"running", "pending", "done", "blocked", "failed", "timeout"}:
            current_task["status"] = status
        elif current_task.get("status") == "pending":
            current_task["status"] = "running"

        # 后端根据status自行推进：仅当当前任务done时进入下一任务。
        advance_to_next = current_task.get("status") == "done"
        if advance_to_next and idx < len(tasks) - 1:
            self.active_task_plan["current_task_index"] = idx + 1
            next_task = tasks[idx + 1]
            if next_task.get("status") == "pending":
                next_task["status"] = "running"
                next_task["start_ts"] = now_ts
                next_task["elapsed"] = 0.0
        elif advance_to_next and idx == len(tasks) - 1:
            self.active_task_plan["global_status"] = "completed"

        # 如果所有任务都完成，则全局完成。
        if tasks and all(task.get("status") == "done" for task in tasks):
            self.active_task_plan["global_status"] = "completed"
        elif tasks:
            self.active_task_plan["global_status"] = "running"

        self.active_task_plan["updated_at"] = now_ts

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
            "task_plan": self.get_task_plan_state(),
            "history": list(self.conversation_history)
        }

    def __repr__(self) -> str:
        memory_status = f", memory={'on' if self.enable_memory else 'off'}"
        if self.enable_memory:
            total = len(self.conversation_history) // 2
            memory_status += f"({total}/{self.max_history_size}, img:{self.max_image_history})"
        return f"DeciderAgent(backend={self.backend_type}, model={self.model}{memory_status})"
