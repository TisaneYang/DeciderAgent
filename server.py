"""
HTTP服务：基于FastAPI的驾驶决策API服务
支持接收四个摄像头图像并返回决策结果
"""

import io
import base64
from typing import Any, Dict, List, Optional
from pathlib import Path
import tempfile
import os

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from decider_agent import DeciderAgent
from backends import CameraImages
from config import VALID_DECISIONS, DEFAULT_BACKEND, DEFAULT_MODELS


# 数据模型
class DecisionResponse(BaseModel):
    """决策响应模型"""
    decision: str = Field(..., description="驾驶决策指令")
    control_override: Optional[str] = Field(None, description="控制覆盖指令，如 full_brake")
    analysis: str = Field(..., description="场景分析结果")
    intention_nl: str = Field("", description="Agent输出的自然语言意图（含请求来源与任务进度）")
    task_update: Dict[str, Any] = Field(default_factory=dict, description="LLM返回的任务状态更新建议")
    task_state: Dict[str, Any] = Field(default_factory=dict, description="服务端维护的轻量任务上下文状态")
    success: bool = Field(default=True, description="请求是否成功")

    class Config:
        json_schema_extra = {
            "example": {
                "decision": "Lane follow",
                "control_override": None,
                "analysis": "前方道路畅通，车道线清晰，建议保持车道行驶。",
                "intention_nl": "当前驾驶意图：保持车道行驶；本轮请求来源：执行当前巡航任务；前一组任务完成情况：已完成1/2，剩余任务进行中。",
                "task_update": {},
                "task_state": {},
                "success": True
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    backend: str
    model: str
    memory_enabled: bool
    valid_decisions: list[str]


class Base64DecisionRequest(BaseModel):
    """Base64图像决策请求模型"""
    front_image: str = Field(..., description="前置摄像头图像(base64编码)")
    left_image: str = Field(..., description="左侧摄像头图像(base64编码)")
    right_image: str = Field(..., description="右侧摄像头图像(base64编码)")
    rear_image: str = Field(..., description="后置摄像头图像(base64编码)")
    timestamp: Optional[str] = Field(None, description="客户端提供的Unix时间戳字符串（秒）")
    allowed_decisions: Optional[List[str]] = Field(None, description="本轮允许的决策集合（可选）")

    class Config:
        json_schema_extra = {
            "example": {
                "front_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
                "left_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
                "right_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
                "rear_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
                "timestamp": "1707734562.134"
            }
        }


from typing import List, Dict, Any, Optional

# --- 子模型定义 ---

class CameraCoverage(BaseModel):
    """摄像头覆盖范围详情"""
    in_blind_spot: bool = Field(True, description="是否处于盲区")
    visible_cameras: List[str] = Field(default_factory=list, description="可见摄像头列表")
    blind_spot_info: Optional[Any] = Field(None, description="盲区详细信息")

class ManeuverAction(BaseModel):
    """单步机动动作描述"""
    step: int = Field(..., description="步骤序号")
    action: str = Field(..., description="动作类型，如 change_lane_left, go_straight")
    description: str = Field(..., description="动作的详细描述")

class ManeuverSequence(BaseModel):
    """机动动作序列及其决策理由"""
    reasoning: str = Field("", description="决策推理过程")
    action_sequence: List[ManeuverAction] = Field(default_factory=list, description="具体的动作步骤列表")

# --- 主模型定义 ---

class InstructionRequest(BaseModel):
    """指令请求模型，支持旧版兼容、摄像头监控及结构化机动规划。"""

    # 1. 基础信息与旧版兼容
    instruction: Optional[str] = Field(None, description="自然语言指令（旧版兼容）")
    advice: Optional[str] = Field(None, description="总体建议")
    description: Optional[str] = Field(None, description="总体说明")
    # traffic_command: Optional[str] = Field(None, description="交通管理指令")
    scene_type: Optional[str] = Field(None, description="场景类型")
    
    # 2. 状态与评估
    risk_level: str = Field("medium", description="风险等级")
    should_intervene: bool = Field(False, description="是否建议干预")
    confidence: float = Field(0.0, description="置信度")
    
    # 3. 摄像头与感知
    camera_coverage: Optional[CameraCoverage] = Field(None, description="摄像头覆盖情况")
    
    # 4. 决策与规划 (重点完善部分)
    maneuver_sequence: Optional[ManeuverSequence] = Field(None, description="机动动作序列详情")
    validation_result: Dict[str, Any] = Field(default_factory=dict, description="验证结果")
    
    # 5. 任务列表与总体规划
    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="结构化任务列表")
    plan: Any = Field(default_factory=dict, description="总体规划（可包含mermaid/topology等字段）")


def extract_instructions_from_payload(request: InstructionRequest) -> List[str]:
    """仅提取plan中的mermaid字符串。"""
    if not isinstance(request.plan, dict):
        return []
    mermaid = request.plan.get("mermaid")
    if not isinstance(mermaid, str):
        return []
    text = mermaid.strip()
    return [text] if text else []


def build_task_payload(request: InstructionRequest) -> Dict[str, Any]:
    """将HTTP请求转换为任务计划payload。"""
    return {
        "instruction": request.instruction,
        "advice": request.advice,
        "description": request.description,
        # "traffic_command": request.traffic_command,
        "scene_type": request.scene_type,
        "risk_level": request.risk_level,
        "should_intervene": request.should_intervene,
        "tasks": request.tasks,
        "plan": request.plan,
    }


# 创建FastAPI应用
app = FastAPI(
    title="驾驶决策Agent API",
    description="基于多模态LLM的驾驶决策服务，支持分析四个摄像头图像并输出驾驶决策",
    version="1.0.0"
)

# 全局Agent实例
agent: Optional[DeciderAgent] = None


def initialize_agent(
    backend_type: str = DEFAULT_BACKEND,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    enable_memory: bool = True,
    max_history_size: int = 5
):
    """初始化DeciderAgent"""
    global agent
    agent = DeciderAgent(
        backend_type=backend_type,
        api_key=api_key,
        model=model,
        enable_memory=enable_memory,
        max_history_size=max_history_size
    )
    print(f"✓ Agent初始化成功: {agent}")


def decode_base64_image(base64_str: str) -> bytes:
    """解码base64图像字符串"""
    # 移除data URL前缀（如果存在）
    if ',' in base64_str:
        base64_str = base64_str.split(',', 1)[1]

    try:
        return base64.b64decode(base64_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base64解码失败: {str(e)}")


def save_temp_image(image_data: bytes, suffix: str = ".jpg") -> str:
    """保存临时图像文件并返回路径"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(image_data)
        return tmp_file.name


@app.on_event("startup")
async def startup_event():
    """服务启动时初始化Agent"""
    # 从环境变量读取配置
    backend = os.getenv("DECIDER_BACKEND", DEFAULT_BACKEND)
    model = os.getenv("DECIDER_MODEL", None)
    enable_memory = os.getenv("DECIDER_MEMORY", "true").lower() == "true"

    try:
        initialize_agent(
            backend_type=backend,
            model=model,
            enable_memory=enable_memory
        )
    except Exception as e:
        print(f"⚠ Agent初始化失败: {e}")
        print("服务将启动，但需要在首次请求时重新初始化")


@app.get("/", tags=["基础"])
async def root():
    """根路径"""
    return {
        "message": "驾驶决策Agent API服务",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["基础"])
async def health_check():
    """健康检查接口"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    return HealthResponse(
        status="healthy",
        backend=agent.backend_type,
        model=agent.model,
        memory_enabled=agent.enable_memory,
        valid_decisions=VALID_DECISIONS
    )


@app.post("/decide/upload", response_model=DecisionResponse, tags=["决策"])
async def decide_from_upload(
    front: UploadFile = File(..., description="前置摄像头图像"),
    left: UploadFile = File(..., description="左侧摄像头图像"),
    right: UploadFile = File(..., description="右侧摄像头图像"),
    rear: UploadFile = File(..., description="后置摄像头图像"),
    timestamp: Optional[str] = Form(None, description="客户端提供的Unix时间戳字符串（秒）"),
    allowed_decisions: Optional[str] = Form(None, description="本轮允许的决策集合(JSON字符串)")
):
    """
    通过上传文件进行决策分析

    接收四个摄像头的图像文件，返回驾驶决策结果
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    temp_files = []

    try:
        # 保存上传的图像到临时文件
        front_path = save_temp_image(await front.read())
        left_path = save_temp_image(await left.read())
        right_path = save_temp_image(await right.read())
        rear_path = save_temp_image(await rear.read())

        temp_files = [front_path, left_path, right_path, rear_path]

        # 执行决策
        parsed_allowed_decisions = None
        if allowed_decisions:
            try:
                import json
                parsed = json.loads(allowed_decisions)
                if isinstance(parsed, list):
                    parsed_allowed_decisions = [str(item) for item in parsed]
            except Exception:
                parsed_allowed_decisions = None

        result = agent.decide_from_paths(
            front_path=front_path,
            left_path=left_path,
            right_path=right_path,
            rear_path=rear_path,
            timestamp=timestamp,
            allowed_decisions=parsed_allowed_decisions
        )

        return DecisionResponse(
            decision=result.decision,
            control_override=result.parsed_response.get("control_override"),
            analysis=result.analysis,
            intention_nl=result.intention_nl,
            task_update=result.task_update,
            task_state=agent.get_task_plan_state(),
            success=True
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"决策分析失败: {str(e)}")

    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass


@app.post("/decide/base64", response_model=DecisionResponse, tags=["决策"])
async def decide_from_base64(request: Base64DecisionRequest):
    """
    通过Base64编码图像进行决策分析

    接收四个摄像头的Base64编码图像，返回驾驶决策结果
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    temp_files = []

    try:
        # 解码并保存图像
        front_data = decode_base64_image(request.front_image)
        left_data = decode_base64_image(request.left_image)
        right_data = decode_base64_image(request.right_image)
        rear_data = decode_base64_image(request.rear_image)

        front_path = save_temp_image(front_data)
        left_path = save_temp_image(left_data)
        right_path = save_temp_image(right_data)
        rear_path = save_temp_image(rear_data)

        temp_files = [front_path, left_path, right_path, rear_path]

        # 执行决策
        result = agent.decide_from_paths(
            front_path=front_path,
            left_path=left_path,
            right_path=right_path,
            rear_path=rear_path,
            timestamp=request.timestamp,
            allowed_decisions=request.allowed_decisions
        )

        return DecisionResponse(
            decision=result.decision,
            control_override=result.parsed_response.get("control_override"),
            analysis=result.analysis,
            intention_nl=result.intention_nl,
            task_update=result.task_update,
            task_state=agent.get_task_plan_state(),
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"决策分析失败: {str(e)}")

    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass


@app.post("/history/clear", tags=["历史管理"])
async def clear_history():
    """清空决策历史记录"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    agent.clear_history()
    return {"message": "历史记录已清空", "success": True}


@app.get("/history/summary", tags=["历史管理"])
async def get_history_summary():
    """获取历史记录摘要"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    summary = agent.get_history_summary()
    # 移除完整历史记录（可能包含大量图像数据）
    summary_without_history = {k: v for k, v in summary.items() if k != "history"}
    return summary_without_history


@app.get("/decisions", tags=["基础"])
async def get_valid_decisions():
    """获取所有有效的决策指令"""
    return {
        "valid_decisions": VALID_DECISIONS,
        "count": len(VALID_DECISIONS)
    }


@app.post("/instruct", tags=["指令"])
async def add_instruction(request: InstructionRequest):
    """仅接收plan.mermaid并覆盖刷新任务上下文。"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    instructions = extract_instructions_from_payload(request)
    if not instructions:
        raise HTTPException(status_code=404, detail="未找到有效的plan.mermaid字符串")

    task_payload = {
        "plan": {"mermaid": instructions[0]}
    }

    task_state = agent.replace_task_plan(task_payload)

    return {
        "success": True,
        "mode": "replace",
        "instruction": instructions[0] if instructions else "",
        "instructions": instructions,
        "added_count": len(instructions),
        "task_state": task_state
    }


@app.get("/instruct", tags=["指令"])
async def get_instructions():
    """获取待处理指令和当前任务计划状态"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    task_state = agent.get_task_plan_state()
    return {
        "instructions": agent.get_pending_instructions(),
        "count": len(agent.get_pending_instructions()),
        "task_state": task_state
    }


@app.delete("/instruct", tags=["指令"])
async def clear_instructions():
    """清除所有待处理指令和任务计划"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent未初始化")

    agent.clear_instructions()
    return {"success": True, "message": "所有指令与任务计划已清除"}


def start_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    backend: str = DEFAULT_BACKEND,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    enable_memory: bool = True,
    reload: bool = False
):
    """
    启动HTTP服务

    Args:
        host: 监听地址
        port: 监听端口
        backend: LLM后端类型
        model: 模型名称
        api_key: API密钥
        enable_memory: 是否启用记忆功能
        reload: 是否启用热重载（开发模式）
    """
    # 设置环境变量供startup_event使用
    os.environ["DECIDER_BACKEND"] = backend
    if model:
        os.environ["DECIDER_MODEL"] = model
    os.environ["DECIDER_MEMORY"] = "true" if enable_memory else "false"

    print(f"🚀 启动驾驶决策Agent HTTP服务")
    print(f"   地址: http://{host}:{port}")
    print(f"   后端: {backend}")
    print(f"   模型: {model or DEFAULT_MODELS.get(backend, 'default')}")
    print(f"   记忆: {'启用' if enable_memory else '禁用'}")
    print(f"   文档: http://{host}:{port}/docs")
    print()

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="驾驶决策Agent HTTP服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--backend", "-b", default=DEFAULT_BACKEND,
                       choices=["anthropic", "openai", "gemini", "qwen", "deepseek"],
                       help="LLM后端类型")
    parser.add_argument("--model", "-m", default=None, help="模型名称")
    parser.add_argument("--api-key", "-k", default=None, help="API密钥")
    parser.add_argument("--no-memory", action="store_true", help="禁用记忆功能")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")

    args = parser.parse_args()

    start_server(
        host=args.host,
        port=args.port,
        backend=args.backend,
        model=args.model,
        api_key=args.api_key,
        enable_memory=not args.no_memory,
        reload=args.reload
    )
