# DeciderAgent - 驾驶决策Agent

基于多模态LLM的智能驾驶决策系统，支持分析四个摄像头图像并输出驾驶决策指令。

## 特性

- 🚗 **多摄像头分析**: 同时分析前、左、右、后四个摄像头图像
- 🧠 **多模态LLM**: 支持多种LLM后端（Anthropic Claude、OpenAI GPT-4o、Google Gemini、通义千问、DeepSeek）
- 💾 **上下文记忆**: 可选的滑动窗口记忆功能，保持决策连贯性
- ⏱️ **时间戳感知**: 自动跟踪请求时间，帮助模型理解场景变化速度
- 🌐 **HTTP API**: 基于FastAPI的RESTful API服务
- 📝 **标准化输出**: 六种标准驾驶决策指令

## 支持的决策指令

1. **Lane follow** - 沿车道线行驶
2. **Left change lane** - 左变道
3. **Right change lane** - 右变道
4. **Left turn** - 路口左转
5. **Right turn** - 路口右转
6. **Straight** - 路口直行

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置API密钥

根据使用的后端设置相应的环境变量：

```bash
# Anthropic Claude (默认)
export ANTHROPIC_API_KEY="your-api-key"

# OpenAI GPT-4o
export OPENAI_API_KEY="your-api-key"

# Google Gemini
export GOOGLE_API_KEY="your-api-key"

# 阿里云通义千问
export DASHSCOPE_API_KEY="your-api-key"

# DeepSeek
export DEEPSEEK_API_KEY="your-api-key"
```

### 3. 使用方式

#### 方式一：命令行工具

```bash
python main.py \
  --backend anthropic \
  --front test_images/front.png \
  --left test_images/left.png \
  --right test_images/right.png \
  --rear test_images/rear.png
```

#### 方式二：Python API

```python
from decider_agent import DeciderAgent

# 创建Agent
agent = DeciderAgent(backend_type="anthropic")

# 执行决策
result = agent.decide_from_paths(
    front_path="test_images/front.png",
    left_path="test_images/left.png",
    right_path="test_images/right.png",
    rear_path="test_images/rear.png"
)

print(f"决策: {result.decision}")
print(f"分析: {result.analysis}")
```

#### 方式三：HTTP API服务

**启动服务：**

```bash
# 使用启动脚本
./start_server.sh

# 或直接运行
python server.py --backend anthropic --port 8000
```

**调用API（文件上传）：**

```python
import requests

# 创建session并禁用代理
session = requests.Session()
session.trust_env = False

url = "http://localhost:8000/decide/upload"
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
```

**调用API（Numpy数组）：**

```python
import cv2
from utils.test_client import DeciderClient

# 初始化客户端
client = DeciderClient(base_url="http://localhost:8000")

# 从OpenCV读取图像（numpy数组格式）
front_img = cv2.imread("test_images/front.png")  # shape: (H, W, 3), dtype: uint8
left_img = cv2.imread("test_images/left.png")
right_img = cv2.imread("test_images/right.png")
rear_img = cv2.imread("test_images/rear.png")

# 传输到API（Base64模式）
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True  # 或 False 使用文件上传模式
)

print(f"决策: {result['decision']}")
print(f"分析: {result['analysis']}")
```

**查看API文档：**

服务启动后访问 http://localhost:8000/docs 查看交互式API文档。

## 项目结构

```
DeciderAgent/
├── main.py              # 命令行入口
├── server.py            # HTTP API服务
├── decider_agent.py     # 核心Agent类
├── backends.py          # LLM后端实现
├── config.py            # 配置文件
├── prompts.py           # 提示词模板
├── requirements.txt     # 依赖列表
├── start_server.sh      # 服务启动脚本
├── benchmark.py         # 性能测试工具
├── test_numpy_integration.py  # Numpy集成测试
├── test_timestamp.py    # 时间戳功能测试
├── demo_timestamp.py    # 时间戳功能演示
├── utils/
│   ├── test_client.py   # API测试客户端（支持numpy）
│   └── numpy_example.py # Numpy使用示例
├── docs/
│   ├── numpy_usage.md   # Numpy详细使用文档
│   └── timestamp_feature.md  # 时间戳功能说明
└── test_images/         # 测试图像目录
    ├── front.png
    ├── left.png
    ├── right.png
    └── rear.png
```

## Numpy数组支持

### 输入格式

- **存储格式**: `numpy.ndarray`
- **数据类型**: `uint8`
- **形状**: `(height, width, 3)`
- **颜色空间**: BGR（OpenCV默认）

### 传输方式

1. **Base64模式**（推荐用于网络传输）
   - 自动将numpy数组编码为JPEG格式
   - 转换为base64字符串通过JSON传输
   - 适合远程API调用

2. **文件上传模式**（适合本地API）
   - 将numpy数组编码为JPEG字节流
   - 通过multipart/form-data传输
   - 传输效率更高，无编码开销

### 快速示例

```python
import cv2
from utils.test_client import DeciderClient

client = DeciderClient(base_url="http://localhost:8000")

# 从摄像头读取
cap = cv2.VideoCapture(0)
ret, front_img = cap.read()  # numpy数组: (H, W, 3), uint8, BGR

# 或从文件读取
front_img = cv2.imread("front.png")

# 传输到API
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True  # Base64模式或False使用文件上传
)

print(f"决策: {result['decision']}")
```

### 详细文档

- **[Numpy使用指南](docs/numpy_usage.md)** - 完整的使用说明、API参考和常见问题
- **[时间戳功能说明](docs/timestamp_feature.md)** - 时间戳功能的详细说明和使用示例
- **[示例代码](utils/numpy_example.py)** - 5个实用场景示例（摄像头、预处理、批量处理等）

### 测试工具

```bash
# 运行Numpy集成测试
python test_numpy_integration.py

# 运行时间戳功能测试
python test_timestamp.py

# 运行时间戳功能演示
python demo_timestamp.py

# 运行示例代码
python utils/numpy_example.py --example 2

# 使用numpy模式测试API
python utils/test_client.py --numpy --base64
```

## 配置选项

### 命令行参数

**main.py (命令行工具):**
```bash
python main.py [选项]

选项:
  --backend, -b         LLM后端类型 (anthropic/openai/gemini/qwen/deepseek)
  --model, -m           模型名称 (可选)
  --front, -f           前置摄像头图像路径
  --left, -l            左侧摄像头图像路径
  --right, -r           右侧摄像头图像路径
  --rear, -e            后置摄像头图像路径
  --api-key, -k         API密钥 (可选)
  --no-memory           禁用上下文记忆功能
  --history-size        滑动窗口大小 (默认: 5)
```

**server.py (HTTP服务):**
```bash
python server.py [选项]

选项:
  --host                监听地址 (默认: 0.0.0.0)
  --port                监听端口 (默认: 8000)
  --backend, -b         LLM后端类型
  --model, -m           模型名称 (可选)
  --api-key, -k         API密钥 (可选)
  --no-memory           禁用记忆功能
  --reload              启用热重载（开发模式）
```

### 环境变量

- `ANTHROPIC_API_KEY`: Anthropic API密钥
- `OPENAI_API_KEY`: OpenAI API密钥
- `GOOGLE_API_KEY`: Google Gemini API密钥
- `DASHSCOPE_API_KEY`: 阿里云通义千问API密钥
- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `DECIDER_BACKEND`: 默认后端类型
- `DECIDER_MODEL`: 默认模型名称
- `DECIDER_MEMORY`: 是否启用记忆功能 (true/false)

## HTTP API接口

### 基础接口

- `GET /` - 根路径
- `GET /health` - 健康检查
- `GET /decisions` - 获取有效决策列表

### 决策分析接口

- `POST /decide/upload` - 文件上传方式
- `POST /decide/base64` - Base64编码方式

### 历史管理接口

- `POST /history/clear` - 清空历史记录
- `GET /history/summary` - 获取历史摘要

详细的API文档请查看 [API_USAGE.md](API_USAGE.md)

## 测试

### 运行测试客户端

```bash
# 确保服务已启动
python server.py --backend anthropic

# 在另一个终端运行测试
python utils/test_client.py --url http://localhost:8000

# 测试Base64模式
python utils/test_client.py --base64

# 测试Numpy数组模式
python utils/test_client.py --numpy --base64
```

### 运行Numpy集成测试

```bash
# 完整的numpy功能测试
python test_numpy_integration.py
```

### 运行示例代码

```bash
# Numpy使用示例
python utils/numpy_example.py --example 2

# 性能测试
python benchmark.py
```

## 常见问题

### 1. 502 Bad Gateway 错误

如果你的环境设置了HTTP代理，访问localhost时可能会出现502错误。

**解决方案：**

```python
# 使用Session禁用代理
session = requests.Session()
session.trust_env = False
response = session.post(url, files=files)
```

或者设置环境变量：

```bash
export no_proxy=localhost,127.0.0.1
```

### 2. API密钥未设置

确保设置了相应后端的API密钥环境变量，或通过 `--api-key` 参数传入。

### 3. 图像格式支持

支持常见的图像格式（JPEG、PNG等），具体取决于所使用的LLM后端。

**Numpy数组支持：**
- 支持OpenCV的numpy数组格式（BGR, uint8）
- 支持RGB格式（可自动转换或直接使用）
- 支持灰度图像（需转换为3通道）

```python
# RGB转BGR
front_bgr = cv2.cvtColor(front_rgb, cv2.COLOR_RGB2BGR)

# 灰度转BGR
if len(gray_img.shape) == 2:
    bgr_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
```

### 4. 记忆功能说明

- 启用记忆后，Agent会保留最近N次决策的上下文
- 可以通过 `--no-memory` 禁用记忆功能
- 记忆功能会增加API调用的token消耗

### 5. 时间戳功能

系统会自动为每次请求添加时间戳，帮助模型理解场景变化：

```
[时间戳: 2026-02-11 22:52:42.134] (距上次请求: 0.501秒)
```

**时间戳的作用：**
- **连续帧（< 0.1秒）**: 模型保持决策稳定性，避免频繁变更
- **正常间隔（0.1-1秒）**: 综合当前和历史信息做决策
- **长间隔（> 1秒）**: 重新评估场景，减少对历史的依赖

详细说明请查看 [时间戳功能文档](docs/timestamp_feature.md)

```bash
# 测试时间戳功能
python test_timestamp.py

# 查看时间戳演示
python demo_timestamp.py
```

## 性能优化建议

1. **选择合适的后端**: 根据精度和速度需求选择不同的LLM后端
2. **调整历史窗口大小**: 减小 `max_history_size` 可以降低API成本
3. **禁用记忆功能**: 如果不需要上下文连续性，可以禁用记忆功能
4. **使用文件上传**: `/decide/upload` 接口比Base64方式更高效

## 部署建议

### Docker部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]
```

构建和运行：

```bash
docker build -t decider-agent .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key \
  decider-agent
```

### 生产环境部署

使用Gunicorn + Uvicorn workers：

```bash
pip install gunicorn
gunicorn server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 开发

### 添加新的LLM后端

1. 在 [backends.py](backends.py) 中实现新的后端类
2. 在 [config.py](config.py) 中添加配置
3. 更新文档

### 修改提示词

编辑 [prompts.py](prompts.py) 中的提示词模板。

## 许可证

请参考项目根目录的LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请通过Issue联系。
