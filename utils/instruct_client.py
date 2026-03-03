#!/usr/bin/env python3
"""指令发送客户端 - 从另一个终端发送自然语言指令"""

import argparse
import requests


class InstructClient:
    """指令客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def send(self, instruction: str) -> dict:
        """发送指令"""
        resp = requests.post(
            f"{self.base_url}/instruct",
            json={"instruction": instruction}
        )
        resp.raise_for_status()
        return resp.json()

    def list(self) -> dict:
        """列出当前待处理指令"""
        resp = requests.get(f"{self.base_url}/instruct")
        resp.raise_for_status()
        return resp.json()

    def clear(self) -> dict:
        """清除所有待处理指令"""
        resp = requests.delete(f"{self.base_url}/instruct")
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict:
        """检查服务健康状态"""
        resp = requests.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()


def main():
    parser = argparse.ArgumentParser(description="发送自然语言指令到DeciderAgent")
    parser.add_argument("instruction", nargs="?", help="要发送的指令")
    parser.add_argument("--server", "-s", default="http://localhost:8000", help="服务器地址")
    parser.add_argument("--list", "-l", action="store_true", help="列出当前待处理指令")
    parser.add_argument("--clear", "-c", action="store_true", help="清除所有待处理指令")
    parser.add_argument("--health", action="store_true", help="检查服务健康状态")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()
    client = InstructClient(args.server)

    try:
        if args.health:
            result = client.health()
            print(f"服务状态: {result['status']}")
            print(f"后端: {result['backend']}")
            print(f"模型: {result['model']}")
        elif args.list:
            result = client.list()
            if result['count'] == 0:
                print("当前没有待处理指令")
            else:
                print(f"待处理指令 ({result['count']}条):")
                for i, inst in enumerate(result['instructions']):
                    print(f"  {i+1}. {inst}")
        elif args.clear:
            result = client.clear()
            print(result['message'])
        elif args.interactive:
            print("交互模式 (输入 'quit' 退出, 'list' 查看, 'clear' 清除)")
            print(f"服务器: {args.server}")
            print()
            while True:
                try:
                    cmd = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n退出")
                    break

                if not cmd:
                    continue
                elif cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "list":
                    result = client.list()
                    if result['count'] == 0:
                        print("当前没有待处理指令")
                    else:
                        print(f"待处理指令 ({result['count']}条):")
                        for i, inst in enumerate(result['instructions']):
                            print(f"  {i+1}. {inst}")
                elif cmd == "clear":
                    result = client.clear()
                    print(result['message'])
                elif cmd == "help":
                    print("命令: quit/exit, list, clear, help")
                    print("其他输入将作为指令发送")
                else:
                    result = client.send(cmd)
                    print(f"✓ 指令已添加 (待处理: {result['pending_count']}条)")
        elif args.instruction:
            result = client.send(args.instruction)
            print(f"✓ 指令已添加: {result['instruction']}")
            print(f"  待处理指令数: {result['pending_count']}")
        else:
            parser.print_help()

    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {args.server}")
        print("请确保DeciderAgent服务已启动")
    except requests.exceptions.HTTPError as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
