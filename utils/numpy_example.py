"""
使用numpy数组调用驾驶决策API的示例代码

展示如何从OpenCV摄像头或图像文件读取numpy数组，
并通过Base64或文件上传方式传输给Agent API
"""

import cv2
import numpy as np
from test_client import DeciderClient


def example_from_opencv_camera():
    """示例1：从OpenCV摄像头读取并进行决策"""

    # 初始化客户端
    client = DeciderClient(base_url="http://localhost:8000")

    # 模拟从4个摄像头读取图像
    # 实际应用中，这里应该是真实的摄像头设备
    cap_front = cv2.VideoCapture(0)  # 前置摄像头
    cap_left = cv2.VideoCapture(1)   # 左侧摄像头
    cap_right = cv2.VideoCapture(2)  # 右侧摄像头
    cap_rear = cv2.VideoCapture(3)   # 后置摄像头

    try:
        # 读取一帧图像
        ret_front, front_img = cap_front.read()
        ret_left, left_img = cap_left.read()
        ret_right, right_img = cap_right.read()
        ret_rear, rear_img = cap_rear.read()

        if all([ret_front, ret_left, ret_right, ret_rear]):
            print(f"图像格式:")
            print(f"  前置: shape={front_img.shape}, dtype={front_img.dtype}")
            print(f"  左侧: shape={left_img.shape}, dtype={left_img.dtype}")
            print(f"  右侧: shape={right_img.shape}, dtype={right_img.dtype}")
            print(f"  后置: shape={rear_img.shape}, dtype={rear_img.dtype}")

            # 方式1：使用Base64传输（推荐用于网络传输）
            print("\n使用Base64模式传输...")
            result = client.decide_from_numpy(
                front=front_img,
                left=left_img,
                right=right_img,
                rear=rear_img,
                use_base64=True
            )

            print(f"决策结果: {result['decision']}")
            print(f"场景分析: {result['analysis']}")

    finally:
        cap_front.release()
        cap_left.release()
        cap_right.release()
        cap_rear.release()


def example_from_image_files():
    """示例2：从图像文件读取numpy数组并进行决策"""

    # 初始化客户端
    client = DeciderClient(base_url="http://localhost:8000")

    # 从文件读取图像（BGR格式）
    front_img = cv2.imread("test_images/front.png")
    left_img = cv2.imread("test_images/left.png")
    right_img = cv2.imread("test_images/right.png")
    rear_img = cv2.imread("test_images/rear.png")

    if all(img is not None for img in [front_img, left_img, right_img, rear_img]):
        print(f"图像加载成功:")
        print(f"  前置: {front_img.shape}, dtype={front_img.dtype}")
        print(f"  左侧: {left_img.shape}, dtype={left_img.dtype}")
        print(f"  右侧: {right_img.shape}, dtype={right_img.dtype}")
        print(f"  后置: {rear_img.shape}, dtype={rear_img.dtype}")

        # 方式1：Base64模式（适合远程API调用）
        print("\n[方式1] Base64模式...")
        result = client.decide_from_numpy(
            front=front_img,
            left=left_img,
            right=right_img,
            rear=rear_img,
            use_base64=True
        )
        print(f"✓ 决策: {result['decision']}")

        # 方式2：文件上传模式（适合本地API调用）
        print("\n[方式2] 文件上传模式...")
        result = client.decide_from_numpy(
            front=front_img,
            left=left_img,
            right=right_img,
            rear=rear_img,
            use_base64=False
        )
        print(f"✓ 决策: {result['decision']}")
    else:
        print("图像加载失败，请检查文件路径")


def example_with_preprocessing():
    """示例3：对图像进行预处理后再传输"""

    client = DeciderClient(base_url="http://localhost:8000")

    # 读取原始图像
    front_img = cv2.imread("test_images/front.png")
    left_img = cv2.imread("test_images/left.png")
    right_img = cv2.imread("test_images/right.png")
    rear_img = cv2.imread("test_images/rear.png")

    if all(img is not None for img in [front_img, left_img, right_img, rear_img]):
        # 预处理：调整大小（减少传输数据量）
        target_size = (640, 480)
        front_resized = cv2.resize(front_img, target_size)
        left_resized = cv2.resize(left_img, target_size)
        right_resized = cv2.resize(right_img, target_size)
        rear_resized = cv2.resize(rear_img, target_size)

        print(f"图像预处理:")
        print(f"  原始大小: {front_img.shape}")
        print(f"  调整后: {front_resized.shape}")

        # 可选：其他预处理操作
        # - 亮度/对比度调整
        # - 去噪
        # - 色彩校正等

        # 传输预处理后的图像
        result = client.decide_from_numpy(
            front=front_resized,
            left=left_resized,
            right=right_resized,
            rear=rear_resized,
            use_base64=True
        )

        print(f"\n决策结果: {result['decision']}")
        print(f"场景分析: {result['analysis']}")


def example_continuous_decision():
    """示例4：连续决策（模拟实时驾驶场景）"""

    client = DeciderClient(base_url="http://localhost:8000")

    # 模拟视频流
    cap = cv2.VideoCapture("test_video.mp4")  # 或使用摄像头: cv2.VideoCapture(0)

    frame_count = 0
    decision_interval = 30  # 每30帧进行一次决策

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            # 每隔一定帧数进行一次决策
            if frame_count % decision_interval == 0:
                # 实际应用中，这里应该从4个摄像头分别读取
                # 这里简化为使用同一帧模拟
                front_img = frame
                left_img = frame
                right_img = frame
                rear_img = frame

                try:
                    result = client.decide_from_numpy(
                        front=front_img,
                        left=left_img,
                        right=right_img,
                        rear=rear_img,
                        use_base64=True
                    )

                    print(f"帧 {frame_count}: {result['decision']}")

                except Exception as e:
                    print(f"决策失败: {e}")

            # 显示图像（可选）
            cv2.imshow('Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


def example_batch_processing():
    """示例5：批量处理多组图像"""

    client = DeciderClient(base_url="http://localhost:8000")

    # 模拟多组图像数据
    image_sets = [
        {
            'front': cv2.imread('dataset/scene1/front.png'),
            'left': cv2.imread('dataset/scene1/left.png'),
            'right': cv2.imread('dataset/scene1/right.png'),
            'rear': cv2.imread('dataset/scene1/rear.png'),
        },
        {
            'front': cv2.imread('dataset/scene2/front.png'),
            'left': cv2.imread('dataset/scene2/left.png'),
            'right': cv2.imread('dataset/scene2/right.png'),
            'rear': cv2.imread('dataset/scene2/rear.png'),
        },
        # ... 更多场景
    ]

    results = []

    for i, images in enumerate(image_sets, 1):
        if all(img is not None for img in images.values()):
            try:
                result = client.decide_from_numpy(
                    front=images['front'],
                    left=images['left'],
                    right=images['right'],
                    rear=images['rear'],
                    use_base64=True
                )

                results.append({
                    'scene_id': i,
                    'decision': result['decision'],
                    'analysis': result['analysis']
                })

                print(f"场景 {i}: {result['decision']}")

            except Exception as e:
                print(f"场景 {i} 处理失败: {e}")
        else:
            print(f"场景 {i} 图像加载失败")

    # 保存结果
    import json
    with open('batch_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n批量处理完成，共处理 {len(results)} 个场景")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Numpy数组使用示例")
    parser.add_argument(
        "--example",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=2,
        help="选择示例: 1=摄像头, 2=文件, 3=预处理, 4=连续决策, 5=批量处理"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("驾驶决策Agent - Numpy数组使用示例")
    print("=" * 60)

    try:
        if args.example == 1:
            print("\n示例1: 从OpenCV摄像头读取")
            example_from_opencv_camera()
        elif args.example == 2:
            print("\n示例2: 从图像文件读取")
            example_from_image_files()
        elif args.example == 3:
            print("\n示例3: 图像预处理")
            example_with_preprocessing()
        elif args.example == 4:
            print("\n示例4: 连续决策")
            example_continuous_decision()
        elif args.example == 5:
            print("\n示例5: 批量处理")
            example_batch_processing()

    except Exception as e:
        print(f"\n示例执行失败: {e}")
        import traceback
        traceback.print_exc()
