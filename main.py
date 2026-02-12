"""
入口文件：示例用法和命令行接口
"""

import argparse
from pathlib import Path

from decider_agent import DeciderAgent
from config import VALID_DECISIONS


def main():
    parser = argparse.ArgumentParser(
        description="驾驶决策Agent - 基于多模态LLM分析摄像头图像并输出驾驶决策"
    )
    parser.add_argument(
        "--backend", "-b",
        type=str,
        default="anthropic",
        choices=["anthropic", "openai", "gemini", "qwen", "deepseek"],
        help="LLM后端类型 (默认: anthropic)"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="模型名称 (可选，使用后端默认模型)"
    )
    parser.add_argument(
        "--front", "-f",
        type=str,
        required=True,
        help="前置摄像头图像路径"
    )
    parser.add_argument(
        "--left", "-l",
        type=str,
        required=True,
        help="左侧摄像头图像路径"
    )
    parser.add_argument(
        "--right", "-r",
        type=str,
        required=True,
        help="右侧摄像头图像路径"
    )
    parser.add_argument(
        "--rear", "-e",
        type=str,
        required=True,
        help="后置摄像头图像路径"
    )
    parser.add_argument(
        "--api-key", "-k",
        type=str,
        default=None,
        help="API密钥 (可选，默认从环境变量读取)"
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="禁用上下文记忆功能"
    )
    parser.add_argument(
        "--history-size",
        type=int,
        default=5,
        help="滑动窗口大小，保留最近N次决策 (默认: 5)"
    )

    args = parser.parse_args()

    # 验证图像文件存在
    for name, path in [("front", args.front), ("left", args.left),
                       ("right", args.right), ("rear", args.rear)]:
        if not Path(path).exists():
            print(f"错误: {name}摄像头图像文件不存在: {path}")
            return 1

    # 创建Agent
    try:
        agent = DeciderAgent(
            backend_type=args.backend,
            api_key=args.api_key,
            model=args.model,
            enable_memory=not args.no_memory,
            max_history_size=args.history_size
        )
        print(f"已初始化: {agent}")
    except ValueError as e:
        print(f"初始化失败: {e}")
        return 1

    # 执行决策
    print("\n正在分析摄像头图像...")
    try:
        result = agent.decide_from_paths(
            front_path=args.front,
            left_path=args.left,
            right_path=args.right,
            rear_path=args.rear
        )
    except Exception as e:
        print(f"API调用失败: {e}")
        return 1

    # 输出结果
    print("\n" + "=" * 50)
    print("驾驶场景分析结果")
    print("=" * 50)
    print(f"\n【场景分析】\n{result.analysis}")
    print(f"\n【决策指令】{result.decision}")
    print("=" * 50)

    return 0


def demo():
    """演示用法（使用测试图像）"""
    test_dir = Path(__file__).parent / "test_images"

    if not test_dir.exists():
        print(f"请创建测试图像目录: {test_dir}")
        print("并放入以下图像文件: front.jpg, left.jpg, right.jpg, rear.jpg")
        return

    print("可用的决策指令:")
    for i, decision in enumerate(VALID_DECISIONS, 1):
        print(f"  {i}. {decision}")

    print("\n示例代码:")
    print("""
        from decider_agent import DeciderAgent

        # 使用Anthropic Claude (默认，启用记忆)
        agent = DeciderAgent()

        # 或使用其他后端
        # agent = DeciderAgent(backend_type="openai")
        # agent = DeciderAgent(backend_type="gemini")
        # agent = DeciderAgent(backend_type="qwen")
        # agent = DeciderAgent(backend_type="deepseek")

        # 禁用记忆功能
        # agent = DeciderAgent(enable_memory=False)

        # 自定义滑动窗口大小
        # agent = DeciderAgent(max_history_size=10)

        # 执行决策（多次调用会保留上下文）
        result1 = agent.decide_from_paths(
            front_path="test_images/front.jpg",
            left_path="test_images/left.jpg",
            right_path="test_images/right.jpg",
            rear_path="test_images/rear.jpg"
        )
        print(f"第1次决策: {result1.decision}")

        result2 = agent.decide_from_paths(
            front_path="test_images/front.jpg",
            left_path="test_images/left.jpg",
            right_path="test_images/right.jpg",
            rear_path="test_images/rear.jpg"
        )
        print(f"第2次决策: {result2.decision}")

        # 查看历史记录摘要
        print(agent.get_history_summary())

        # 清空历史记录
        agent.clear_history()
    """)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # 无参数时显示演示
        demo()
    else:
        sys.exit(main())
