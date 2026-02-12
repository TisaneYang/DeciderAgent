#!/usr/bin/env python3
"""
性能测试工具：测试API的响应时间和吞吐量
"""

import requests
import time
import statistics
from typing import List, Dict
import argparse


class PerformanceTester:
    """API性能测试器"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.trust_env = False

    def test_single_request(self) -> float:
        """测试单次请求的响应时间"""
        files = {
            'front': open('test_images/front.png', 'rb'),
            'left': open('test_images/left.png', 'rb'),
            'right': open('test_images/right.png', 'rb'),
            'rear': open('test_images/rear.png', 'rb')
        }

        try:
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/decide/upload",
                files=files,
                timeout=60
            )
            end_time = time.time()

            if response.status_code == 200:
                return end_time - start_time
            else:
                raise Exception(f"HTTP {response.status_code}")
        finally:
            for f in files.values():
                f.close()

    def run_performance_test(self, num_requests: int = 5) -> Dict:
        """
        运行性能测试

        Args:
            num_requests: 测试请求次数

        Returns:
            性能统计信息
        """
        print(f"\n开始性能测试 (共 {num_requests} 次请求)...")
        print("=" * 60)

        response_times: List[float] = []
        failed_requests = 0

        for i in range(num_requests):
            print(f"\n请求 {i+1}/{num_requests}...", end=" ")
            try:
                elapsed = self.test_single_request()
                response_times.append(elapsed)
                print(f"✓ {elapsed:.2f}秒")
            except Exception as e:
                failed_requests += 1
                print(f"✗ 失败: {e}")

        # 计算统计信息
        if response_times:
            stats = {
                'total_requests': num_requests,
                'successful_requests': len(response_times),
                'failed_requests': failed_requests,
                'min_time': min(response_times),
                'max_time': max(response_times),
                'avg_time': statistics.mean(response_times),
                'median_time': statistics.median(response_times),
            }

            if len(response_times) > 1:
                stats['std_dev'] = statistics.stdev(response_times)
            else:
                stats['std_dev'] = 0

            return stats
        else:
            return {
                'total_requests': num_requests,
                'successful_requests': 0,
                'failed_requests': failed_requests,
                'error': '所有请求都失败了'
            }

    def print_results(self, stats: Dict):
        """打印测试结果"""
        print("\n" + "=" * 60)
        print("性能测试结果")
        print("=" * 60)

        if 'error' in stats:
            print(f"\n✗ {stats['error']}")
            return

        print(f"\n总请求数: {stats['total_requests']}")
        print(f"成功: {stats['successful_requests']}")
        print(f"失败: {stats['failed_requests']}")
        print(f"成功率: {stats['successful_requests']/stats['total_requests']*100:.1f}%")

        print(f"\n响应时间统计:")
        print(f"  最小值: {stats['min_time']:.2f}秒")
        print(f"  最大值: {stats['max_time']:.2f}秒")
        print(f"  平均值: {stats['avg_time']:.2f}秒")
        print(f"  中位数: {stats['median_time']:.2f}秒")
        print(f"  标准差: {stats['std_dev']:.2f}秒")

        print(f"\n吞吐量: {stats['successful_requests']/sum([stats['min_time'], stats['max_time'], stats['avg_time']])*3:.2f} 请求/秒 (估算)")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="DeciderAgent API性能测试")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="API服务地址"
    )
    parser.add_argument(
        "--requests", "-n",
        type=int,
        default=5,
        help="测试请求次数 (默认: 5)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("DeciderAgent API 性能测试工具")
    print("=" * 60)
    print(f"\n服务地址: {args.url}")
    print(f"测试次数: {args.requests}")

    # 检查测试图像
    from pathlib import Path
    test_dir = Path("test_images")
    required = ['front.png', 'left.png', 'right.png', 'rear.png']
    missing = [img for img in required if not (test_dir / img).exists()]

    if missing:
        print(f"\n✗ 缺少测试图像: {', '.join(missing)}")
        return

    # 运行测试
    tester = PerformanceTester(args.url)

    # 先测试连接
    print("\n检查服务连接...")
    try:
        response = tester.session.get(f"{args.url}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✓ 服务正常")
            print(f"  后端: {health['backend']}")
            print(f"  模型: {health['model']}")
        else:
            print(f"✗ 服务异常: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"✗ 无法连接到服务: {e}")
        return

    # 运行性能测试
    stats = tester.run_performance_test(args.requests)
    tester.print_results(stats)


if __name__ == "__main__":
    main()
