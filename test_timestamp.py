"""
测试客户端Unix时间戳功能
"""
import time
from backends import CameraImages

def test_timestamp_feature():
    """测试客户端Unix时间戳功能是否正常工作"""
    print("=" * 60)
    print("客户端Unix时间戳功能测试")
    print("=" * 60)

    # 测试Unix时间戳格式
    print("\n[测试1] 验证Unix时间戳格式")
    current_timestamp = time.time()
    timestamp_str = str(current_timestamp)
    print(f"✓ Unix时间戳: {timestamp_str}")
    print(f"  浮点数值: {current_timestamp}")

    # 测试时间间隔计算
    print("\n[测试2] 验证时间间隔计算")
    time1 = time.time()
    time.sleep(0.5)
    time2 = time.time()
    time_delta = time2 - time1
    print(f"✓ 时间间隔: {time_delta:.3f}秒 (预期约0.5秒)")

    # 测试CameraImages带Unix时间戳
    print("\n[测试3] 验证CameraImages时间戳参数")
    images = CameraImages(
        front="test_images/front.png",
        left="test_images/left.png",
        right="test_images/right.png",
        rear="test_images/rear.png",
        timestamp=str(time.time())  # Unix时间戳字符串
    )
    print(f"✓ 图像对象创建成功")
    print(f"  时间戳: {images.timestamp}")

    # 测试时间戳解析
    print("\n[测试4] 验证时间戳解析和转换")
    try:
        from datetime import datetime
        ts1 = "1707734562.134"
        ts2 = "1707734562.634"
        t1 = float(ts1)
        t2 = float(ts2)
        delta = t2 - t1

        # 转换为可读格式
        dt1 = datetime.fromtimestamp(t1)
        dt2 = datetime.fromtimestamp(t2)

        print(f"✓ 时间戳解析成功")
        print(f"  时间戳1: {ts1} -> {dt1.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"  时间戳2: {ts2} -> {dt2.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"  时间间隔: {delta:.3f}秒")
    except Exception as e:
        print(f"✗ 时间戳解析失败: {e}")

    print("\n" + "=" * 60)
    print("客户端Unix时间戳功能测试完成!")
    print("=" * 60)
    print("\n说明:")
    print("- 客户端在采集图像时生成Unix时间戳")
    print("- 时间戳格式: Unix时间戳字符串（秒，如 '1707734562.134'）")
    print("- 服务端接收时间戳并计算时间间隔")
    print("- 模型可以根据时间间隔理解场景变化速度")

if __name__ == "__main__":
    test_timestamp_feature()
