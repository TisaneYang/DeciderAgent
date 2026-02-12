"""
测试客户端时间戳功能
"""
import time
from datetime import datetime
from decider_agent import DeciderAgent
from backends import CameraImages

def test_timestamp_feature():
    """测试客户端时间戳功能是否正常工作"""
    print("=" * 60)
    print("客户端时间戳功能测试")
    print("=" * 60)

    # 测试时间戳格式
    print("\n[测试1] 验证时间戳格式")
    current_time = datetime.now()
    timestamp_iso = current_time.isoformat()
    print(f"✓ ISO 8601格式: {timestamp_iso}")

    # 测试时间间隔计算
    print("\n[测试2] 验证时间间隔计算")
    time1 = datetime.now()
    time.sleep(0.5)
    time2 = datetime.now()
    time_delta = (time2 - time1).total_seconds()
    print(f"✓ 时间间隔: {time_delta:.3f}秒 (预期约0.5秒)")

    # 测试CameraImages带时间戳
    print("\n[测试3] 验证CameraImages时间戳参数")
    images = CameraImages(
        front="test_images/front.png",
        left="test_images/left.png",
        right="test_images/right.png",
        rear="test_images/rear.png",
        timestamp=datetime.now().isoformat()
    )
    print(f"✓ 图像对象创建成功")
    print(f"  时间戳: {images.timestamp}")

    # 测试时间戳解析
    print("\n[测试4] 验证时间戳解析")
    try:
        ts1 = "2026-02-11T22:52:42.134"
        ts2 = "2026-02-11T22:52:42.634"
        t1 = datetime.fromisoformat(ts1)
        t2 = datetime.fromisoformat(ts2)
        delta = (t2 - t1).total_seconds()
        print(f"✓ 时间戳解析成功")
        print(f"  时间戳1: {ts1}")
        print(f"  时间戳2: {ts2}")
        print(f"  时间间隔: {delta:.3f}秒")
    except Exception as e:
        print(f"✗ 时间戳解析失败: {e}")

    print("\n" + "=" * 60)
    print("客户端时间戳功能测试完成!")
    print("=" * 60)
    print("\n说明:")
    print("- 客户端在采集图像时生成时间戳")
    print("- 时间戳格式: ISO 8601 (YYYY-MM-DDTHH:MM:SS.mmm)")
    print("- 服务端接收时间戳并计算时间间隔")
    print("- 模型可以根据时间间隔理解场景变化速度")

if __name__ == "__main__":
    test_timestamp_feature()
