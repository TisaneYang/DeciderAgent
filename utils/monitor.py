#!/usr/bin/env python3
"""
监控工具：实时监控API服务状态
"""

import requests
import time
import sys
from datetime import datetime


class ServiceMonitor:
    """服务监控器"""

    def __init__(self, base_url: str, interval: int = 5):
        self.base_url = base_url
        self.interval = interval
        self.session = requests.Session()
        self.session.trust_env = False

    def check_status(self) -> dict:
        """检查服务状态"""
        try:
            start = time.time()
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            elapsed = time.time() - start

            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'healthy',
                    'response_time': elapsed,
                    'backend': data.get('backend'),
                    'model': data.get('model'),
                    'memory_enabled': data.get('memory_enabled')
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': f"HTTP {response.status_code}"
                }
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': '请求超时'}
        except requests.exceptions.ConnectionError:
            return {'status': 'down', 'error': '无法连接'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def get_history_info(self) -> dict:
        """获取历史信息"""
        try:
            response = self.session.get(
                f"{self.base_url}/history/summary",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def print_status(self, status: dict, history: dict):
        """打印状态信息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 清屏（可选）
        # print("\033[2J\033[H", end="")

        print(f"\n{'='*60}")
        print(f"DeciderAgent 服务监控 - {timestamp}")
        print(f"{'='*60}")

        if status['status'] == 'healthy':
            print(f"\n✓ 服务状态: 正常运行")
            print(f"  响应时间: {status['response_time']*1000:.0f}ms")
            print(f"  后端: {status['backend']}")
            print(f"  模型: {status['model']}")
            print(f"  记忆: {'启用' if status['memory_enabled'] else '禁用'}")

            if history:
                print(f"\n历史记录:")
                print(f"  对话轮数: {history.get('total_conversations', 0)}")
                print(f"  最大历史: {history.get('max_history_size', 0)}")
                print(f"  图像轮数: {history.get('image_rounds_stored', 0)}")
        else:
            print(f"\n✗ 服务状态: {status['status'].upper()}")
            print(f"  错误: {status.get('error', '未知错误')}")

        print(f"\n{'='*60}")
        print(f"下次检查: {self.interval}秒后 (Ctrl+C 退出)")

    def monitor(self):
        """开始监控"""
        print(f"开始监控服务: {self.base_url}")
        print(f"检查间隔: {self.interval}秒")

        try:
            while True:
                status = self.check_status()
                history = self.get_history_info() if status['status'] == 'healthy' else {}
                self.print_status(status, history)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="DeciderAgent API监控工具")
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="API服务地址"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="检查间隔（秒，默认: 5）"
    )

    args = parser.parse_args()

    monitor = ServiceMonitor(args.url, args.interval)
    monitor.monitor()


if __name__ == "__main__":
    main()
