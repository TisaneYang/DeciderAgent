"""
完整的使用示例：展示如何在实际项目中使用DeciderAgent API
"""

import requests
import time
from pathlib import Path
from typing import Dict, List, Optional


class DeciderAPIClient:
    """
    DeciderAgent API客户端封装类

    使用示例:
        client = DeciderAPIClient("http://localhost:8080")
        result = client.analyze_images(
            front="test_images/front.png",
            left="test_images/left.png",
            right="test_images/right.png",
            rear="test_images/rear.png"
        )
        print(f"决策: {result['decision']}")
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        初始化客户端

        Args:
            base_url: API服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # 创建session并禁用代理（避免localhost走代理）
        self.session = requests.Session()
        self.session.trust_env = False

    def check_health(self) -> Dict:
        """
        检查服务健康状态

        Returns:
            包含服务状态信息的字典
        """
        response = self.session.get(
            f"{self.base_url}/health",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_valid_decisions(self) -> List[str]:
        """
        获取所有有效的决策指令

        Returns:
            决策指令列表
        """
        response = self.session.get(
            f"{self.base_url}/decisions",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()['valid_decisions']

    def analyze_images(
        self,
        front: str,
        left: str,
        right: str,
        rear: str
    ) -> Dict:
        """
        分析四个摄像头图像并获取驾驶决策

        Args:
            front: 前置摄像头图像路径
            left: 左侧摄像头图像路径
            right: 右侧摄像头图像路径
            rear: 后置摄像头图像路径

        Returns:
            包含decision和analysis的字典
        """
        # 检查文件是否存在
        for name, path in [('front', front), ('left', left),
                          ('right', right), ('rear', rear)]:
            if not Path(path).exists():
                raise FileNotFoundError(f"{name}摄像头图像不存在: {path}")

        # 准备文件
        files = {
            'front': open(front, 'rb'),
            'left': open(left, 'rb'),
            'right': open(right, 'rb'),
            'rear': open(rear, 'rb')
        }

        try:
            response = self.session.post(
                f"{self.base_url}/decide/upload",
                files=files,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        finally:
            # 确保关闭所有文件
            for f in files.values():
                f.close()

    def clear_history(self) -> Dict:
        """
        清空决策历史记录

        Returns:
            操作结果
        """
        response = self.session.post(
            f"{self.base_url}/history/clear",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_history_summary(self) -> Dict:
        """
        获取历史记录摘要

        Returns:
            历史记录统计信息
        """
        response = self.session.get(
            f"{self.base_url}/history/summary",
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


def example_basic_usage():
    """示例1：基本使用"""
    print("\n" + "=" * 60)
    print("示例1：基本使用")
    print("=" * 60)

    # 创建客户端
    client = DeciderAPIClient("http://localhost:8080")

    # 检查服务状态
    health = client.check_health()
    print(f"\n✓ 服务状态: {health['status']}")
    print(f"  后端: {health['backend']}")
    print(f"  模型: {health['model']}")

    # 执行决策分析
    print("\n正在分析图像...")
    result = client.analyze_images(
        front="test_images/front.png",
        left="test_images/left.png",
        right="test_images/right.png",
        rear="test_images/rear.png"
    )

    print(f"\n【决策指令】{result['decision']}")
    print(f"\n【场景分析】\n{result['analysis']}")


def example_multiple_requests():
    """示例2：连续多次请求（测试记忆功能）"""
    print("\n" + "=" * 60)
    print("示例2：连续多次请求（测试记忆功能）")
    print("=" * 60)

    client = DeciderAPIClient("http://localhost:8080")

    # 清空历史
    client.clear_history()
    print("\n✓ 已清空历史记录")

    # 执行3次决策
    for i in range(3):
        print(f"\n--- 第 {i+1} 次决策 ---")
        result = client.analyze_images(
            front="test_images/front.png",
            left="test_images/left.png",
            right="test_images/right.png",
            rear="test_images/rear.png"
        )
        print(f"决策: {result['decision']}")

        # 查看历史摘要
        summary = client.get_history_summary()
        print(f"历史记录: {summary['total_conversations']} 轮对话")

        time.sleep(1)  # 避免请求过快


def example_error_handling():
    """示例3：错误处理"""
    print("\n" + "=" * 60)
    print("示例3：错误处理")
    print("=" * 60)

    client = DeciderAPIClient("http://localhost:8080")

    try:
        # 尝试使用不存在的图像
        result = client.analyze_images(
            front="nonexistent.png",
            left="test_images/left.png",
            right="test_images/right.png",
            rear="test_images/rear.png"
        )
    except FileNotFoundError as e:
        print(f"\n✓ 正确捕获文件不存在错误: {e}")

    try:
        # 尝试连接错误的端口
        wrong_client = DeciderAPIClient("http://localhost:9999")
        wrong_client.check_health()
    except requests.exceptions.RequestException as e:
        print(f"✓ 正确捕获连接错误: {type(e).__name__}")


def example_batch_processing():
    """示例4：批量处理多组图像"""
    print("\n" + "=" * 60)
    print("示例4：批量处理（模拟）")
    print("=" * 60)

    client = DeciderAPIClient("http://localhost:8080")

    # 模拟处理多组图像（这里用同一组图像演示）
    image_sets = [
        {
            'name': '场景1',
            'front': 'test_images/front.png',
            'left': 'test_images/left.png',
            'right': 'test_images/right.png',
            'rear': 'test_images/rear.png'
        },
        # 实际使用时可以添加更多场景
    ]

    results = []
    for idx, image_set in enumerate(image_sets, 1):
        print(f"\n处理 {image_set['name']}...")
        try:
            result = client.analyze_images(
                front=image_set['front'],
                left=image_set['left'],
                right=image_set['right'],
                rear=image_set['rear']
            )
            results.append({
                'scene': image_set['name'],
                'decision': result['decision'],
                'analysis': result['analysis']
            })
            print(f"✓ 决策: {result['decision']}")
        except Exception as e:
            print(f"✗ 处理失败: {e}")

    # 汇总结果
    print(f"\n{'='*60}")
    print(f"批量处理完成，共处理 {len(results)} 个场景")
    print(f"{'='*60}")


def example_with_context_manager():
    """示例5：使用上下文管理器"""
    print("\n" + "=" * 60)
    print("示例5：推荐的使用模式")
    print("=" * 60)

    class DeciderSession:
        """带上下文管理的客户端"""
        def __init__(self, base_url: str):
            self.client = DeciderAPIClient(base_url)

        def __enter__(self):
            # 进入时检查服务状态
            health = self.client.check_health()
            print(f"✓ 连接到服务: {health['backend']} ({health['model']})")
            return self.client

        def __exit__(self, exc_type, exc_val, exc_tb):
            # 退出时清理（如果需要）
            if exc_type is None:
                print("✓ 会话正常结束")
            else:
                print(f"✗ 会话异常结束: {exc_type.__name__}")
            return False

    # 使用上下文管理器
    with DeciderSession("http://localhost:8080") as client:
        result = client.analyze_images(
            front="test_images/front.png",
            left="test_images/left.png",
            right="test_images/right.png",
            rear="test_images/rear.png"
        )
        print(f"\n决策: {result['decision']}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("DeciderAgent API 完整使用示例")
    print("=" * 60)

    try:
        # 运行各个示例
        example_basic_usage()
        example_multiple_requests()
        example_error_handling()
        example_batch_processing()
        example_with_context_manager()

        print("\n" + "=" * 60)
        print("✓ 所有示例运行完成!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n✗ 无法连接到服务，请确保服务已启动:")
        print("  python server.py --backend qwen --port 8080")
    except Exception as e:
        print(f"\n✗ 运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
