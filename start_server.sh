#!/bin/bash
# 驾驶决策Agent HTTP服务启动脚本

# 默认配置
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
BACKEND="${DECIDER_BACKEND:-anthropic}"
MODEL="${DECIDER_MODEL:-}"
RELOAD="${RELOAD:-false}"

# 显示帮助信息
show_help() {
    echo "驾驶决策Agent HTTP服务启动脚本"
    echo ""
    echo "用法: ./start_server.sh [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示帮助信息"
    echo "  -H, --host HOST         监听地址 (默认: 0.0.0.0)"
    echo "  -p, --port PORT         监听端口 (默认: 8000)"
    echo "  -b, --backend BACKEND   LLM后端 (anthropic/openai/gemini/qwen/deepseek)"
    echo "  -m, --model MODEL       模型名称"
    echo "  --no-memory             禁用记忆功能"
    echo "  --reload                启用热重载（开发模式）"
    echo ""
    echo "环境变量:"
    echo "  ANTHROPIC_API_KEY       Anthropic API密钥"
    echo "  OPENAI_API_KEY          OpenAI API密钥"
    echo "  GOOGLE_API_KEY          Google Gemini API密钥"
    echo "  DASHSCOPE_API_KEY       阿里云通义千问API密钥"
    echo "  DEEPSEEK_API_KEY        DeepSeek API密钥"
    echo ""
    echo "示例:"
    echo "  ./start_server.sh"
    echo "  ./start_server.sh -p 8080 -b openai"
    echo "  ./start_server.sh --reload"
}

# 解析命令行参数
ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -b|--backend)
            BACKEND="$2"
            shift 2
            ;;
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        --no-memory)
            ARGS="$ARGS --no-memory"
            shift
            ;;
        --reload)
            RELOAD="true"
            shift
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 构建启动命令
CMD="python server.py --host $HOST --port $PORT --backend $BACKEND"

if [ -n "$MODEL" ]; then
    CMD="$CMD --model $MODEL"
fi

if [ "$RELOAD" = "true" ]; then
    CMD="$CMD --reload"
fi

CMD="$CMD $ARGS"

# 启动服务
echo "启动命令: $CMD"
echo ""
exec $CMD
