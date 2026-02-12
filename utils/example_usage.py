"""
简单的使用示例：展示如何调用驾驶决策API
"""

import requests

# 方法1：使用Session禁用代理（推荐）
def example_with_session():
    """使用Session对象，禁用代理"""
    print("=" * 60)
    print("示例1：使用Session对象（推荐方法）")
    print("=" * 60)

    # 创建session并禁用代理
    session = requests.Session()
    session.trust_env = False  # 不使用环境变量中的代理设置

    # 注意：根据你的服务端口修改URL（默认8000，你的是8080）
    url = "http://localhost:8080/decide/upload"

    files = {
        'front': open('test_images/front.png', 'rb'),
        'left': open('test_images/left.png', 'rb'),
        'right': open('test_images/right.png', 'rb'),
        'rear': open('test_images/rear.png', 'rb')
    }

    try:
        response = session.post(url, files=files)
        response.raise_for_status()  # 检查HTTP错误
        result = response.json()

        print(f"\n✓ 请求成功!")
        print(f"决策: {result['decision']}")
        print(f"分析: {result['analysis']}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
    finally:
        # 关闭文件
        for f in files.values():
            f.close()


# 方法2：使用proxies参数
def example_with_proxies():
    """使用proxies参数禁用代理"""
    print("\n" + "=" * 60)
    print("示例2：使用proxies参数")
    print("=" * 60)

    url = "http://localhost:8080/decide/upload"

    files = {
        'front': open('test_images/front.png', 'rb'),
        'left': open('test_images/left.png', 'rb'),
        'right': open('test_images/right.png', 'rb'),
        'rear': open('test_images/rear.png', 'rb')
    }

    try:
        # 显式设置不使用代理
        response = requests.post(url, files=files, proxies={'http': None, 'https': None})
        response.raise_for_status()
        result = response.json()

        print(f"\n✓ 请求成功!")
        print(f"决策: {result['decision']}")
        print(f"分析: {result['analysis']}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {e}")
    finally:
        for f in files.values():
            f.close()


# 方法3：先测试健康检查
def example_health_check():
    """先测试健康检查接口"""
    print("\n" + "=" * 60)
    print("示例3：健康检查")
    print("=" * 60)

    session = requests.Session()
    session.trust_env = False

    try:
        response = session.get("http://localhost:8080/health")
        response.raise_for_status()
        health = response.json()

        print(f"\n✓ 服务健康!")
        print(f"状态: {health['status']}")
        print(f"后端: {health['backend']}")
        print(f"模型: {health['model']}")
        print(f"记忆功能: {'启用' if health['memory_enabled'] else '禁用'}")
        print(f"\n支持的决策指令:")
        for i, decision in enumerate(health['valid_decisions'], 1):
            print(f"  {i}. {decision}")

    except requests.exceptions.RequestException as e:
        print(f"\n✗ 健康检查失败: {e}")


# 方法4：使用test_client模块
def example_with_client():
    """使用封装好的客户端"""
    print("\n" + "=" * 60)
    print("示例4：使用test_client模块（最简单）")
    print("=" * 60)

    try:
        from test_client import DeciderClient

        # 创建客户端（已自动处理代理问题）
        client = DeciderClient(base_url="http://localhost:8080")

        # 健康检查
        health = client.health_check()
        print(f"\n✓ 服务状态: {health['status']}")

        # 执行决策
        result = client.decide_from_files(
            front='test_images/front.png',
            left='test_images/left.png',
            right='test_images/right.png',
            rear='test_images/rear.png'
        )

        print(f"\n✓ 决策完成!")
        print(f"决策: {result['decision']}")
        print(f"分析: {result['analysis']}")

    except ImportError:
        print("\n⚠ 请确保test_client.py在当前目录")
    except Exception as e:
        print(f"\n✗ 请求失败: {e}")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 检查测试图像是否存在
    test_dir = Path("test_images")
    required_images = ['front.png', 'left.png', 'right.png', 'rear.png']
    missing = [img for img in required_images if not (test_dir / img).exists()]

    if missing:
        print(f"⚠ 缺少测试图像: {', '.join(missing)}")
        print(f"请在 test_images/ 目录下准备这些图像文件")
        sys.exit(1)

    # 运行所有示例
    example_health_check()
    example_with_session()
    # example_with_proxies()  # 可选
    # example_with_client()   # 可选

    print("\n" + "=" * 60)
    print("所有示例完成!")
    print("=" * 60)
