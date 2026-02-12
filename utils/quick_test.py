#!/usr/bin/env python3
"""
快速测试脚本：验证HTTP API服务是否正常工作
"""

import requests
import sys

def test_api():
    """快速测试API"""

    # 创建session并禁用代理
    session = requests.Session()
    session.trust_env = False

    base_url = "http://localhost:8080"  # 根据实际端口修改

    print("=" * 60)
    print("DeciderAgent API 快速测试")
    print("=" * 60)

    # 1. 健康检查
    print("\n[1/3] 测试健康检查接口...")
    try:
        response = session.get(f"{base_url}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✓ 服务正常运行")
            print(f"  - 后端: {health['backend']}")
            print(f"  - 模型: {health['model']}")
            print(f"  - 记忆: {'启用' if health['memory_enabled'] else '禁用'}")
        else:
            print(f"✗ 健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n提示:")
        print("  1. 确保服务已启动: python server.py")
        print("  2. 检查端口是否正确（默认8000，当前测试8080）")
        return False

    # 2. 获取决策列表
    print("\n[2/3] 测试决策列表接口...")
    try:
        response = session.get(f"{base_url}/decisions")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 支持 {data['count']} 种决策指令:")
            for i, decision in enumerate(data['valid_decisions'], 1):
                print(f"  {i}. {decision}")
        else:
            print(f"✗ 获取决策列表失败: HTTP {response.status_code}")
    except Exception as e:
        print(f"✗ 请求失败: {e}")

    # 3. 测试决策分析
    print("\n[3/3] 测试决策分析接口...")
    try:
        files = {
            'front': open('test_images/front.png', 'rb'),
            'left': open('test_images/left.png', 'rb'),
            'right': open('test_images/right.png', 'rb'),
            'rear': open('test_images/rear.png', 'rb')
        }

        print("  正在上传图像并分析...")
        response = session.post(f"{base_url}/decide/upload", files=files)

        # 关闭文件
        for f in files.values():
            f.close()

        if response.status_code == 200:
            result = response.json()
            print(f"✓ 决策分析成功!")
            print(f"\n{'='*60}")
            print(f"【决策指令】{result['decision']}")
            print(f"\n【场景分析】")
            print(f"{result['analysis']}")
            print(f"{'='*60}")
            return True
        else:
            print(f"✗ 决策分析失败: HTTP {response.status_code}")
            print(f"  响应: {response.text[:200]}")
            return False

    except FileNotFoundError as e:
        print(f"✗ 图像文件不存在: {e}")
        print("\n请确保 test_images/ 目录下有以下文件:")
        print("  - front.png")
        print("  - left.png")
        print("  - right.png")
        print("  - rear.png")
        return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("\n提示: 如果遇到502错误，说明请求走了代理")
    print("      本脚本已自动禁用代理，应该可以正常工作\n")

    success = test_api()

    print("\n" + "=" * 60)
    if success:
        print("✓ 所有测试通过!")
        print("\n你现在可以在Python中这样使用:")
        print("""
import requests

session = requests.Session()
session.trust_env = False  # 禁用代理

url = "http://localhost:8080/decide/upload"
files = {
    'front': open('test_images/front.png', 'rb'),
    'left': open('test_images/left.png', 'rb'),
    'right': open('test_images/right.png', 'rb'),
    'rear': open('test_images/rear.png', 'rb')
}

response = session.post(url, files=files)
result = response.json()

print(f"决策: {result['decision']}")
print(f"分析: {result['analysis']}")

# 关闭文件
for f in files.values():
    f.close()
        """)
    else:
        print("✗ 测试失败，请检查上述错误信息")
        sys.exit(1)
    print("=" * 60)
