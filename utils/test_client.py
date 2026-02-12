"""
测试客户端：用于测试HTTP API服务
"""

import requests
import base64
import sys
from pathlib import Path
from typing import Optional, Union
import numpy as np
import cv2


class DeciderClient:
    """驾驶决策API客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        # 创建session并禁用代理（避免localhost请求走代理）
        self.session = requests.Session()
        self.session.trust_env = False

    def health_check(self) -> dict:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_valid_decisions(self) -> dict:
        """获取有效决策列表"""
        response = self.session.get(f"{self.base_url}/decisions")
        response.raise_for_status()
        return response.json()

    def decide_from_files(
        self,
        front: str,
        left: str,
        right: str,
        rear: str,
        timestamp: Optional[str] = None
    ) -> dict:
        """通过文件上传进行决策"""
        files = {
            'front': open(front, 'rb'),
            'left': open(left, 'rb'),
            'right': open(right, 'rb'),
            'rear': open(rear, 'rb')
        }
        data = {}
        if timestamp:
            data['timestamp'] = timestamp

        try:
            response = self.session.post(
                f"{self.base_url}/decide/upload",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
        finally:
            for f in files.values():
                f.close()

    def decide_from_base64(
        self,
        front: str,
        left: str,
        right: str,
        rear: str,
        timestamp: Optional[str] = None
    ) -> dict:
        """通过Base64编码进行决策"""
        def encode(path: str) -> str:
            with open(path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode()
                return f"data:image/jpeg;base64,{encoded}"

        data = {
            'front_image': encode(front),
            'left_image': encode(left),
            'right_image': encode(right),
            'rear_image': encode(rear)
        }
        if timestamp:
            data['timestamp'] = timestamp

        response = self.session.post(f"{self.base_url}/decide/base64", json=data)
        response.raise_for_status()
        return response.json()

    def decide_from_numpy(
        self,
        front: np.ndarray,
        left: np.ndarray,
        right: np.ndarray,
        rear: np.ndarray,
        use_base64: bool = True,
        timestamp: Optional[str] = None
    ) -> dict:
        """
        通过numpy数组进行决策

        Args:
            front: 前置摄像头图像 (H, W, 3) BGR格式
            left: 左侧摄像头图像 (H, W, 3) BGR格式
            right: 右侧摄像头图像 (H, W, 3) BGR格式
            rear: 后置摄像头图像 (H, W, 3) BGR格式
            use_base64: 是否使用Base64模式（True）或文件上传模式（False）
            timestamp: 客户端提供的时间戳（可选）

        Returns:
            决策结果字典
        """
        def numpy_to_base64(img: np.ndarray) -> str:
            """将numpy数组转换为base64字符串"""
            # 编码为JPEG格式
            success, buffer = cv2.imencode('.jpg', img)
            if not success:
                raise ValueError("图像编码失败")

            # 转换为base64
            encoded = base64.b64encode(buffer).decode()
            return f"data:image/jpeg;base64,{encoded}"

        def numpy_to_bytes(img: np.ndarray) -> bytes:
            """将numpy数组转换为JPEG字节流"""
            success, buffer = cv2.imencode('.jpg', img)
            if not success:
                raise ValueError("图像编码失败")
            return buffer.tobytes()

        if use_base64:
            # Base64模式
            data = {
                'front_image': numpy_to_base64(front),
                'left_image': numpy_to_base64(left),
                'right_image': numpy_to_base64(right),
                'rear_image': numpy_to_base64(rear)
            }
            if timestamp:
                data['timestamp'] = timestamp

            response = self.session.post(f"{self.base_url}/decide/base64", json=data)
            response.raise_for_status()
            return response.json()
        else:
            # 文件上传模式
            files = {
                'front': ('front.jpg', numpy_to_bytes(front), 'image/jpeg'),
                'left': ('left.jpg', numpy_to_bytes(left), 'image/jpeg'),
                'right': ('right.jpg', numpy_to_bytes(right), 'image/jpeg'),
                'rear': ('rear.jpg', numpy_to_bytes(rear), 'image/jpeg')
            }
            data = {}
            if timestamp:
                data['timestamp'] = timestamp

            response = self.session.post(
                f"{self.base_url}/decide/upload",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()

    def clear_history(self) -> dict:
        """清空历史记录"""
        response = self.session.post(f"{self.base_url}/history/clear")
        response.raise_for_status()
        return response.json()

    def get_history_summary(self) -> dict:
        """获取历史摘要"""
        response = self.session.get(f"{self.base_url}/history/summary")
        response.raise_for_status()
        return response.json()


def test_numpy_api(
    base_url: str = "http://localhost:8000",
    test_dir: str = "test_images",
    use_base64: bool = True
):
    """
    测试使用numpy数组的API功能

    Args:
        base_url: API服务地址
        test_dir: 测试图像目录
        use_base64: 是否使用Base64模式（True）或文件上传模式（False）
    """
    client = DeciderClient(base_url)

    print("=" * 60)
    print("驾驶决策Agent API 测试 (Numpy数组模式)")
    print("=" * 60)

    # 1. 健康检查
    print("\n[1] 健康检查...")
    try:
        health = client.health_check()
        print(f"✓ 服务状态: {health['status']}")
        print(f"  后端: {health['backend']}")
        print(f"  模型: {health['model']}")
        print(f"  记忆功能: {'启用' if health['memory_enabled'] else '禁用'}")
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return

    # 2. 检查测试图像
    test_path = Path(test_dir)
    required_images = ['front.png', 'left.png', 'right.png', 'rear.png']
    missing_images = [img for img in required_images if not (test_path / img).exists()]

    if missing_images:
        print(f"\n⚠ 缺少测试图像: {', '.join(missing_images)}")
        print(f"请在 {test_dir}/ 目录下准备以下图像文件:")
        for img in required_images:
            print(f"  - {img}")
        return

    # 3. 加载图像为numpy数组
    print(f"\n[2] 加载图像为numpy数组...")
    try:
        front_img = cv2.imread(str(test_path / 'front.png'))
        left_img = cv2.imread(str(test_path / 'left.png'))
        right_img = cv2.imread(str(test_path / 'right.png'))
        rear_img = cv2.imread(str(test_path / 'rear.png'))

        if any(img is None for img in [front_img, left_img, right_img, rear_img]):
            print("✗ 图像加载失败")
            return

        print(f"✓ 图像加载成功")
        print(f"  前置: {front_img.shape}, dtype={front_img.dtype}")
        print(f"  左侧: {left_img.shape}, dtype={left_img.dtype}")
        print(f"  右侧: {right_img.shape}, dtype={right_img.dtype}")
        print(f"  后置: {rear_img.shape}, dtype={rear_img.dtype}")

    except Exception as e:
        print(f"✗ 图像加载失败: {e}")
        return

    # 4. 执行决策分析
    mode_str = "Base64模式" if use_base64 else "文件上传模式"
    print(f"\n[3] 执行决策分析 ({mode_str})...")
    try:
        result = client.decide_from_numpy(
            front=front_img,
            left=left_img,
            right=right_img,
            rear=rear_img,
            use_base64=use_base64
        )

        print("✓ 决策分析完成")
        print(f"\n【决策指令】{result['decision']}")
        print(f"\n【场景分析】\n{result['analysis']}")

    except Exception as e:
        print(f"✗ 决策分析失败: {e}")
        return

    # 5. 查看历史摘要
    print("\n[4] 查看历史摘要...")
    try:
        summary = client.get_history_summary()
        print(f"✓ 历史记录统计:")
        print(f"  总对话轮数: {summary['total_conversations']}")
        print(f"  最大历史大小: {summary['max_history_size']}")
        print(f"  保留图像轮数: {summary['max_image_history']}")
        print(f"  当前图像轮数: {summary['image_rounds_stored']}")
    except Exception as e:
        print(f"✗ 获取历史摘要失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


def test_api(
    base_url: str = "http://localhost:8000",
    test_dir: str = "test_images",
    use_base64: bool = False
):
    """测试API功能"""
    client = DeciderClient(base_url)

    print("=" * 60)
    print("驾驶决策Agent API 测试")
    print("=" * 60)

    # 1. 健康检查
    print("\n[1] 健康检查...")
    try:
        health = client.health_check()
        print(f"✓ 服务状态: {health['status']}")
        print(f"  后端: {health['backend']}")
        print(f"  模型: {health['model']}")
        print(f"  记忆功能: {'启用' if health['memory_enabled'] else '禁用'}")
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return

    # 2. 获取有效决策列表
    print("\n[2] 获取有效决策列表...")
    try:
        decisions = client.get_valid_decisions()
        print(f"✓ 支持的决策指令 ({decisions['count']}个):")
        for i, decision in enumerate(decisions['valid_decisions'], 1):
            print(f"  {i}. {decision}")
    except Exception as e:
        print(f"✗ 获取决策列表失败: {e}")

    # 3. 检查测试图像
    test_path = Path(test_dir)
    required_images = ['front.png', 'left.png', 'right.png', 'rear.png']
    missing_images = [img for img in required_images if not (test_path / img).exists()]

    if missing_images:
        print(f"\n⚠ 缺少测试图像: {', '.join(missing_images)}")
        print(f"请在 {test_dir}/ 目录下准备以下图像文件:")
        for img in required_images:
            print(f"  - {img}")
        return

    # 4. 执行决策分析
    print(f"\n[3] 执行决策分析 ({'Base64模式' if use_base64 else '文件上传模式'})...")
    try:
        if use_base64:
            result = client.decide_from_base64(
                front=str(test_path / 'front.png'),
                left=str(test_path / 'left.png'),
                right=str(test_path / 'right.png'),
                rear=str(test_path / 'rear.png')
            )
        else:
            result = client.decide_from_files(
                front=str(test_path / 'front.png'),
                left=str(test_path / 'left.png'),
                right=str(test_path / 'right.png'),
                rear=str(test_path / 'rear.png')
            )

        print("✓ 决策分析完成")
        print(f"\n【决策指令】{result['decision']}")
        print(f"\n【场景分析】\n{result['analysis']}")

    except Exception as e:
        print(f"✗ 决策分析失败: {e}")
        return

    # 5. 查看历史摘要
    print("\n[4] 查看历史摘要...")
    try:
        summary = client.get_history_summary()
        print(f"✓ 历史记录统计:")
        print(f"  总对话轮数: {summary['total_conversations']}")
        print(f"  最大历史大小: {summary['max_history_size']}")
        print(f"  保留图像轮数: {summary['max_image_history']}")
        print(f"  当前图像轮数: {summary['image_rounds_stored']}")
    except Exception as e:
        print(f"✗ 获取历史摘要失败: {e}")

    # 6. 清空历史
    print("\n[5] 清空历史记录...")
    try:
        result = client.clear_history()
        print(f"✓ {result['message']}")
    except Exception as e:
        print(f"✗ 清空历史失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="驾驶决策Agent API测试客户端")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API服务地址 (默认: http://localhost:8000)"
    )
    parser.add_argument(
        "--test-dir",
        default="test_images",
        help="测试图像目录 (默认: test_images)"
    )
    parser.add_argument(
        "--base64",
        action="store_true",
        help="使用Base64编码模式（默认使用文件上传模式）"
    )
    parser.add_argument(
        "--numpy",
        action="store_true",
        help="使用numpy数组模式（从文件加载为numpy数组后传输）"
    )

    args = parser.parse_args()

    try:
        if args.numpy:
            # 使用numpy数组模式
            test_numpy_api(
                base_url=args.url,
                test_dir=args.test_dir,
                use_base64=args.base64
            )
        else:
            # 使用传统文件模式
            test_api(
                base_url=args.url,
                test_dir=args.test_dir,
                use_base64=args.base64
            )
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
