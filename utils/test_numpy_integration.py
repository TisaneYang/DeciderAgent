#!/usr/bin/env python3
"""
快速测试numpy数组集成功能

测试从numpy数组到API的完整流程
"""

import sys
import numpy as np
import cv2
from pathlib import Path

# 添加utils到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.test_client import DeciderClient


def create_test_image(color, size=(480, 640, 3)):
    """创建测试图像"""
    img = np.zeros(size, dtype=np.uint8)
    img[:, :] = color

    # 添加一些文字标识
    text_color = (255, 255, 255) if sum(color) < 384 else (0, 0, 0)
    cv2.putText(img, f"Test Image", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 2, text_color, 3)

    return img


def test_numpy_encoding():
    """测试1: numpy数组编码功能"""
    print("\n" + "="*60)
    print("测试1: Numpy数组编码功能")
    print("="*60)

    # 创建测试图像
    test_img = create_test_image((100, 150, 200))
    print(f"✓ 创建测试图像: shape={test_img.shape}, dtype={test_img.dtype}")

    # 测试JPEG编码
    success, buffer = cv2.imencode('.jpg', test_img)
    if success:
        print(f"✓ JPEG编码成功: {len(buffer)} bytes")
    else:
        print("✗ JPEG编码失败")
        return False

    # 测试base64编码
    import base64
    encoded = base64.b64encode(buffer).decode()
    print(f"✓ Base64编码成功: {len(encoded)} chars")

    # 测试解码
    decoded = base64.b64decode(encoded)
    print(f"✓ Base64解码成功: {len(decoded)} bytes")

    return True


def test_numpy_to_api_base64():
    """测试2: Numpy数组通过Base64传输到API"""
    print("\n" + "="*60)
    print("测试2: Numpy数组 -> Base64 -> API")
    print("="*60)

    client = DeciderClient(base_url="http://localhost:8000")

    # 健康检查
    try:
        health = client.health_check()
        print(f"✓ API服务正常: {health['status']}")
        print(f"  后端: {health['backend']}")
        print(f"  模型: {health['model']}")
    except Exception as e:
        print(f"✗ API服务不可用: {e}")
        print("  请先启动服务: python server.py")
        return False

    # 创建测试图像
    front = create_test_image((255, 0, 0))    # 蓝色
    left = create_test_image((0, 255, 0))     # 绿色
    right = create_test_image((0, 0, 255))    # 红色
    rear = create_test_image((128, 128, 128)) # 灰色

    print(f"✓ 创建4张测试图像")

    # 通过Base64传输
    try:
        result = client.decide_from_numpy(
            front=front,
            left=left,
            right=right,
            rear=rear,
            use_base64=True
        )

        print(f"✓ Base64传输成功")
        print(f"  决策: {result['decision']}")
        print(f"  分析长度: {len(result['analysis'])} chars")
        return True

    except Exception as e:
        print(f"✗ Base64传输失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_numpy_to_api_upload():
    """测试3: Numpy数组通过文件上传传输到API"""
    print("\n" + "="*60)
    print("测试3: Numpy数组 -> 文件上传 -> API")
    print("="*60)

    client = DeciderClient(base_url="http://localhost:8000")

    # 创建测试图像
    front = create_test_image((255, 100, 100))
    left = create_test_image((100, 255, 100))
    right = create_test_image((100, 100, 255))
    rear = create_test_image((200, 200, 200))

    print(f"✓ 创建4张测试图像")

    # 通过文件上传传输
    try:
        result = client.decide_from_numpy(
            front=front,
            left=left,
            right=right,
            rear=rear,
            use_base64=False
        )

        print(f"✓ 文件上传传输成功")
        print(f"  决策: {result['decision']}")
        print(f"  分析长度: {len(result['analysis'])} chars")
        return True

    except Exception as e:
        print(f"✗ 文件上传传输失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_real_images():
    """测试4: 使用真实图像文件"""
    print("\n" + "="*60)
    print("测试4: 真实图像文件 -> Numpy -> API")
    print("="*60)

    test_dir = Path("test_images")
    required_images = ['front.png', 'left.png', 'right.png', 'rear.png']

    # 检查图像文件
    missing = [img for img in required_images if not (test_dir / img).exists()]
    if missing:
        print(f"⚠ 缺少测试图像: {', '.join(missing)}")
        print(f"  跳过此测试")
        return None

    # 读取图像
    try:
        front = cv2.imread(str(test_dir / 'front.png'))
        left = cv2.imread(str(test_dir / 'left.png'))
        right = cv2.imread(str(test_dir / 'right.png'))
        rear = cv2.imread(str(test_dir / 'rear.png'))

        if any(img is None for img in [front, left, right, rear]):
            print("✗ 图像加载失败")
            return False

        print(f"✓ 图像加载成功")
        print(f"  前置: {front.shape}, {front.dtype}")
        print(f"  左侧: {left.shape}, {left.dtype}")
        print(f"  右侧: {right.shape}, {right.dtype}")
        print(f"  后置: {rear.shape}, {rear.dtype}")

    except Exception as e:
        print(f"✗ 图像加载失败: {e}")
        return False

    # 传输到API
    client = DeciderClient(base_url="http://localhost:8000")

    try:
        # 测试Base64模式
        print("\n  [Base64模式]")
        result = client.decide_from_numpy(
            front=front, left=left, right=right, rear=rear,
            use_base64=True
        )
        print(f"  ✓ 决策: {result['decision']}")

        # 测试文件上传模式
        print("\n  [文件上传模式]")
        result = client.decide_from_numpy(
            front=front, left=left, right=right, rear=rear,
            use_base64=False
        )
        print(f"  ✓ 决策: {result['decision']}")

        return True

    except Exception as e:
        print(f"✗ API调用失败: {e}")
        return False


def test_image_preprocessing():
    """测试5: 图像预处理"""
    print("\n" + "="*60)
    print("测试5: 图像预处理")
    print("="*60)

    # 创建原始图像
    original = create_test_image((150, 150, 150), size=(1080, 1920, 3))
    print(f"✓ 原始图像: {original.shape}")

    # 调整大小
    resized = cv2.resize(original, (640, 480))
    print(f"✓ 调整大小: {resized.shape}")

    # 亮度调整
    brightened = cv2.convertScaleAbs(resized, alpha=1.2, beta=10)
    print(f"✓ 亮度调整: {brightened.shape}")

    # 测试传输
    client = DeciderClient(base_url="http://localhost:8000")

    try:
        result = client.decide_from_numpy(
            front=brightened,
            left=resized,
            right=resized,
            rear=resized,
            use_base64=True
        )
        print(f"✓ 预处理后传输成功")
        print(f"  决策: {result['decision']}")
        return True

    except Exception as e:
        print(f"✗ 传输失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("Numpy数组集成测试")
    print("="*60)

    results = {}

    # 测试1: 编码功能（不需要API）
    results['encoding'] = test_numpy_encoding()

    # 测试2-5: 需要API服务
    results['base64_api'] = test_numpy_to_api_base64()

    if results['base64_api']:
        results['upload_api'] = test_numpy_to_api_upload()
        results['real_images'] = test_real_images()
        results['preprocessing'] = test_image_preprocessing()
    else:
        print("\n⚠ 跳过后续测试（API服务不可用）")
        results['upload_api'] = None
        results['real_images'] = None
        results['preprocessing'] = None

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    for name, result in results.items():
        if result is True:
            status = "✓ 通过"
        elif result is False:
            status = "✗ 失败"
        else:
            status = "⊘ 跳过"

        print(f"{status} - {name}")

    # 统计
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\n通过: {passed}, 失败: {failed}, 跳过: {skipped}")

    if failed > 0:
        print("\n⚠ 部分测试失败，请检查错误信息")
        sys.exit(1)
    else:
        print("\n✓ 所有测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(130)
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
