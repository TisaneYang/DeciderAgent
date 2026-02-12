"""
Unix时间戳功能演示：展示如何在实际场景中使用Unix时间戳
"""
import time
from pathlib import Path
from backends import CameraImages


def demo_unix_timestamp():
    """演示Unix时间戳功能"""
    print("=" * 70)
    print("Unix时间戳功能演示")
    print("=" * 70)

    # 检查测试图像
    test_path = Path("test_images")
    required_images = ['front.png', 'left.png', 'right.png', 'rear.png']
    missing_images = [img for img in required_images if not (test_path / img).exists()]

    if missing_images:
        print(f"\n⚠ 缺少测试图像: {', '.join(missing_images)}")
        print(f"请在 test_images/ 目录下准备以下图像文件:")
        for img in required_images:
            print(f"  - {img}")
        return

    # 场景1: 首次请求（无时间间隔）
    print("\n" + "=" * 70)
    print("场景1: 首次决策请求（带Unix时间戳）")
    print("=" * 70)
    print("说明: 客户端在图像采集时生成Unix时间戳")

    # 模拟图像采集
    timestamp1 = str(time.time())
    print(f"\n✓ 图像采集完成")
    print(f"  Unix时间戳: {timestamp1}")

    # 转换为可读格式显示
    from datetime import datetime
    dt1 = datetime.fromtimestamp(float(timestamp1))
    print(f"  可读格式: {dt1.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

    images1 = CameraImages(
        front=str(test_path / 'front.png'),
        left=str(test_path / 'left.png'),
        right=str(test_path / 'right.png'),
        rear=str(test_path / 'rear.png'),
        timestamp=timestamp1  # Unix时间戳字符串
    )
    print(f"\n✓ CameraImages对象创建成功")
    print(f"  模型会收到: [时间戳: {dt1.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}]")

    # 场景2: 短间隔请求（模拟30fps视频流）
    print("\n" + "=" * 70)
    print("场景2: 连续帧决策（模拟30fps视频流）")
    print("=" * 70)
    print("说明: 等待约0.033秒后再次采集图像，模拟连续视频帧")

    time.sleep(0.033)

    timestamp2 = str(time.time())
    dt2 = datetime.fromtimestamp(float(timestamp2))
    time_delta = float(timestamp2) - float(timestamp1)

    print(f"\n✓ 图像采集完成")
    print(f"  Unix时间戳: {timestamp2}")
    print(f"  可读格式: {dt2.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"  时间间隔: {time_delta:.3f}秒")

    images2 = CameraImages(
        front=str(test_path / 'front.png'),
        left=str(test_path / 'left.png'),
        right=str(test_path / 'right.png'),
        rear=str(test_path / 'rear.png'),
        timestamp=timestamp2
    )
    print(f"\n✓ CameraImages对象创建成功")
    print(f"  模型会收到: [时间戳: {dt2.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] (距上次请求: {time_delta:.3f}秒)")
    print(f"  模型理解: 这是连续帧，场景变化很小")

    # 场景3: 正常间隔请求
    print("\n" + "=" * 70)
    print("场景3: 正常决策间隔")
    print("=" * 70)
    print("说明: 等待0.5秒后再次采集图像，模拟正常决策频率")

    time.sleep(0.5)

    timestamp3 = str(time.time())
    dt3 = datetime.fromtimestamp(float(timestamp3))
    time_delta = float(timestamp3) - float(timestamp2)

    print(f"\n✓ 图像采集完成")
    print(f"  Unix时间戳: {timestamp3}")
    print(f"  可读格式: {dt3.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"  时间间隔: {time_delta:.3f}秒")

    images3 = CameraImages(
        front=str(test_path / 'front.png'),
        left=str(test_path / 'left.png'),
        right=str(test_path / 'right.png'),
        rear=str(test_path / 'rear.png'),
        timestamp=timestamp3
    )
    print(f"\n✓ CameraImages对象创建成功")
    print(f"  模型会收到: [时间戳: {dt3.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] (距上次请求: {time_delta:.3f}秒)")
    print(f"  模型理解: 正常决策频率，场景可能有一定变化")

    # 场景4: 长间隔请求
    print("\n" + "=" * 70)
    print("场景4: 长时间间隔决策")
    print("=" * 70)
    print("说明: 等待2秒后再次采集图像，模拟场景可能已完全改变")

    time.sleep(2.0)

    timestamp4 = str(time.time())
    dt4 = datetime.fromtimestamp(float(timestamp4))
    time_delta = float(timestamp4) - float(timestamp3)

    print(f"\n✓ 图像采集完成")
    print(f"  Unix时间戳: {timestamp4}")
    print(f"  可读格式: {dt4.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"  时间间隔: {time_delta:.3f}秒")

    images4 = CameraImages(
        front=str(test_path / 'front.png'),
        left=str(test_path / 'left.png'),
        right=str(test_path / 'right.png'),
        rear=str(test_path / 'rear.png'),
        timestamp=timestamp4
    )
    print(f"\n✓ CameraImages对象创建成功")
    print(f"  模型会收到: [时间戳: {dt4.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] (距上次请求: {time_delta:.3f}秒)")
    print(f"  模型理解: 长时间间隔，场景可能已完全不同")

    # 场景5: 不提供时间戳
    print("\n" + "=" * 70)
    print("场景5: 不提供时间戳（可选功能）")
    print("=" * 70)
    print("说明: 时间戳是可选的，不提供时也能正常工作")

    images5 = CameraImages(
        front=str(test_path / 'front.png'),
        left=str(test_path / 'left.png'),
        right=str(test_path / 'right.png'),
        rear=str(test_path / 'rear.png')
        # 不提供timestamp参数
    )
    print(f"\n✓ CameraImages对象创建成功")
    print(f"  模型不会收到时间戳信息，系统正常工作")

    # 总结
    print("\n" + "=" * 70)
    print("演示总结")
    print("=" * 70)
    print("\nUnix时间戳功能的优势:")
    print("1. 标准格式，跨平台兼容")
    print("2. 易于计算时间间隔（直接相减）")
    print("3. 不受时区影响")
    print("4. 精度可达毫秒级")
    print("5. 反映图像真实采集时间，不受网络延迟影响")

    print("\n应用场景:")
    print("- 实时视频流处理（高频请求，连续帧）")
    print("- 间歇性决策（正常频率，场景变化）")
    print("- 离线批量处理（可以使用历史时间戳）")
    print("- 场景切换检测（长时间间隔）")

    print("\n时间戳生成方式:")
    print("- Python: str(time.time())")
    print("- JavaScript: String(Date.now() / 1000)")
    print("- C++: std::chrono::duration<double>(now.time_since_epoch()).count()")

    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


def demo_http_api_examples():
    """演示HTTP API中使用Unix时间戳"""
    print("\n" + "=" * 70)
    print("HTTP API Unix时间戳使用示例")
    print("=" * 70)

    print("\n1. Base64模式（Python）:")
    print("""
import requests
import time

data = {
    "front_image": "data:image/jpeg;base64,...",
    "left_image": "data:image/jpeg;base64,...",
    "right_image": "data:image/jpeg;base64,...",
    "rear_image": "data:image/jpeg;base64,...",
    "timestamp": str(time.time())  # Unix时间戳字符串
}

response = requests.post("http://localhost:8000/decide/base64", json=data)
result = response.json()
    """)

    print("\n2. 文件上传模式（Python）:")
    print("""
import requests
import time

files = {
    'front': open('front.png', 'rb'),
    'left': open('left.png', 'rb'),
    'right': open('right.png', 'rb'),
    'rear': open('rear.png', 'rb')
}

data = {
    'timestamp': str(time.time())  # Unix时间戳字符串
}

response = requests.post(
    "http://localhost:8000/decide/upload",
    files=files,
    data=data
)
result = response.json()
    """)

    print("\n3. 使用测试客户端（Numpy数组）:")
    print("""
import cv2
import time
from utils.test_client import DeciderClient

client = DeciderClient(base_url="http://localhost:8000")

# 从摄像头采集图像
cap = cv2.VideoCapture(0)
ret, front_img = cap.read()

# 记录采集时的Unix时间戳
timestamp = str(time.time())

# 传输到API
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True,
    timestamp=timestamp  # 传递Unix时间戳字符串
)
    """)


def main():
    """主函数"""
    import sys

    try:
        demo_unix_timestamp()
        demo_http_api_examples()

    except KeyboardInterrupt:
        print("\n\n演示已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
