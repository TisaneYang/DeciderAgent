#!/usr/bin/env python3
"""指令发送客户端 - 从另一个终端发送自然语言指令"""

import argparse
import json
import requests


class InstructClient:
    """指令客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def send(self, instruction: str) -> dict:
        """发送指令"""
        return self.send_payload({"instruction": instruction})

    def send_payload(self, payload: dict) -> dict:
        """发送结构化任务/指令payload。"""
        resp = requests.post(
            f"{self.base_url}/instruct",
            json=payload
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
    parser.add_argument("--tasks-file", help="发送结构化任务JSON文件（会覆盖当前任务列表）")

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
        elif args.tasks_file:
            with open(args.tasks_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            result = client.send_payload(payload)
            print(f"✓ 任务列表已刷新: task_count={result.get('task_count', 0)}")
            print(f"  plan_version={result.get('task_state', {}).get('plan_version')}")
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
                    task_state = result.get("task_state", {})
                    if task_state:
                        print(
                            f"  当前任务: index={task_state.get('current_task_index')} "
                            f"status={task_state.get('global_status')}"
                        )
                elif cmd == "clear":
                    result = client.clear()
                    print(result['message'])
                elif cmd == "help":
                    print("命令: quit/exit, list, clear, help")
                    print("其他输入将作为指令发送")
                else:
                    result = client.send(cmd)
                    print(
                        "✓ 任务列表已刷新 "
                        f"(task_count={result.get('task_count', 0)}, "
                        f"plan_version={result.get('task_state', {}).get('plan_version')})"
                    )
        elif args.instruction:
            result = client.send(args.instruction)
            print(f"✓ 任务列表已刷新: {result['instruction']}")
            print(f"  task_count: {result.get('task_count', 0)}")
            print(f"  plan_version: {result.get('task_state', {}).get('plan_version')}")
        else:
            parser.print_help()

    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {args.server}")
        print("请确保DeciderAgent服务已启动")
    except requests.exceptions.HTTPError as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
