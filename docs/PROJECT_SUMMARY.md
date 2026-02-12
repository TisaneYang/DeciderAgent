# DeciderAgent HTTP服务 - 项目总结

## 问题解决方案

### 原始问题
你遇到了502 Bad Gateway错误，原因是环境中设置了HTTP代理（`http_proxy=http://192.168.16.1:7890`），导致访问localhost时也走了代理。

### 解决方案
在Python代码中禁用代理：

```python
import requests

# 方法1：使用Session（推荐）
session = requests.Session()
session.trust_env = False  # 不使用环境变量中的代理

response = session.post(url, files=files)
```

## 项目文件清单

### 核心文件
- **server.py** - FastAPI HTTP服务主文件
- **decider_agent.py** - 核心Agent类
- **backends.py** - LLM后端实现
- **config.py** - 配置文件
- **prompts.py** - 提示词模板
- **main.py** - 命令行工具

### 服务相关
- **start_server.sh** - 服务启动脚本（已添加执行权限）
- **requirements.txt** - 依赖列表（已添加FastAPI等）

### 测试和示例
- **quick_test.py** - 快速测试脚本（已验证通过）
- **test_client.py** - 完整的API测试客户端
- **example_usage.py** - 基础使用示例
- **complete_example.py** - 完整使用示例（包含多种场景）

### 工具脚本
- **monitor.py** - 服务监控工具
- **benchmark.py** - 性能测试工具

### 文档
- **README.md** - 项目主文档
- **API_USAGE.md** - API详细使用文档（包含代理问题解决方案）

## 服务状态

### 当前运行状态
- ✓ 服务正在运行
- ✓ 端口: 8080
- ✓ 后端: qwen (qwen-vl-max)
- ✓ 记忆功能: 启用
- ✓ 测试通过

### 测试结果
```
[1/3] 健康检查 - ✓ 通过
[2/3] 决策列表 - ✓ 通过
[3/3] 决策分析 - ✓ 通过

决策结果: Lane follow
场景分析: 前置摄像头显示车辆在多车道城市道路上行驶...
```

## API接口总览

### 基础接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 根路径 |
| GET | /health | 健康检查 |
| GET | /decisions | 获取有效决策列表 |

### 决策分析接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /decide/upload | 文件上传方式（推荐） |
| POST | /decide/base64 | Base64编码方式 |

### 历史管理接口
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /history/clear | 清空历史记录 |
| GET | /history/summary | 获取历史摘要 |

## 使用示例

### 1. 基础使用（解决代理问题）

```python
import requests

# 创建session并禁用代理
session = requests.Session()
session.trust_env = False

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
```

### 2. 使用封装的客户端

```python
from test_client import DeciderClient

# 创建客户端（已自动处理代理问题）
client = DeciderClient(base_url="http://localhost:8080")

# 执行决策
result = client.decide_from_files(
    front='test_images/front.png',
    left='test_images/left.png',
    right='test_images/right.png',
    rear='test_images/rear.png'
)

print(f"决策: {result['decision']}")
print(f"分析: {result['analysis']}")
```

### 3. 使用完整示例

```bash
# 运行完整示例（包含多种使用场景）
python complete_example.py
```

## 测试工具使用

### 快速测试
```bash
python quick_test.py
```

### 性能测试
```bash
# 测试5次请求
python benchmark.py --url http://localhost:8080 --requests 5

# 测试10次请求
python benchmark.py -n 10
```

### 服务监控
```bash
# 每5秒检查一次
python monitor.py --url http://localhost:8080

# 每10秒检查一次
python monitor.py --interval 10
```

## 常见问题和解决方案

### 1. 502 Bad Gateway
**原因**: 环境设置了HTTP代理，localhost请求走了代理

**解决方案**:
```python
session = requests.Session()
session.trust_env = False
```

### 2. Connection Refused
**原因**: 服务未启动或端口错误

**解决方案**:
```bash
# 检查服务是否运行
ps aux | grep server.py

# 启动服务
python server.py --backend qwen --port 8080
```

### 3. JSON Decode Error
**原因**: 响应不是有效的JSON（通常是HTTP错误）

**解决方案**:
```python
response = session.post(url, files=files)
if response.status_code != 200:
    print(f"HTTP错误: {response.status_code}")
    print(f"响应: {response.text}")
else:
    result = response.json()
```

## 配置说明

### 环境变量
```bash
# API密钥
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export DASHSCOPE_API_KEY="your-key"
export DEEPSEEK_API_KEY="your-key"

# 服务配置
export DECIDER_BACKEND="qwen"
export DECIDER_MODEL="qwen-vl-max"
export DECIDER_MEMORY="true"

# 代理配置（如果需要排除localhost）
export no_proxy="localhost,127.0.0.1"
```

### 启动参数
```bash
# 基础启动
python server.py

# 自定义配置
python server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --backend qwen \
  --model qwen-vl-max \
  --no-memory

# 开发模式（热重载）
python server.py --reload
```

## 性能优化建议

1. **使用文件上传方式** - `/decide/upload` 比Base64方式更高效
2. **调整历史窗口** - 减小 `max_history_size` 降低API成本
3. **禁用记忆功能** - 如果不需要上下文，使用 `--no-memory`
4. **选择合适的模型** - 根据精度和速度需求选择后端

## 部署建议

### Docker部署
```bash
# 构建镜像
docker build -t decider-agent .

# 运行容器
docker run -p 8080:8080 \
  -e DASHSCOPE_API_KEY=your-key \
  decider-agent
```

### 生产环境
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080
```

## 下一步建议

1. **添加认证** - 为API添加Token认证
2. **添加日志** - 记录所有请求和决策结果
3. **添加缓存** - 对相同图像缓存决策结果
4. **添加限流** - 防止API被滥用
5. **添加监控** - 集成Prometheus/Grafana
6. **添加测试** - 编写单元测试和集成测试

## 项目亮点

✓ **完整的HTTP API服务** - 基于FastAPI，支持Swagger文档
✓ **多种使用方式** - 命令行、Python API、HTTP API
✓ **代理问题解决** - 自动处理localhost代理问题
✓ **丰富的示例** - 提供多种使用场景示例
✓ **实用工具** - 测试、监控、性能测试工具
✓ **详细文档** - README、API文档、问题解决方案
✓ **已验证可用** - 所有功能已测试通过

## 联系和支持

- 查看文档: [README.md](README.md)
- API文档: [API_USAGE.md](API_USAGE.md)
- 运行测试: `python quick_test.py`
- 查看示例: `python complete_example.py`

---

**最后更新**: 2026-02-09
**状态**: ✓ 已完成并测试通过
