# 驾驶决策Agent HTTP API 使用文档

## 概述

这是一个基于FastAPI的HTTP服务，提供驾驶决策分析功能。服务接收四个摄像头（前、左、右、后）的图像数据，通过多模态LLM进行分析，返回驾驶决策结果。

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

### 3. 启动服务

**方式一：使用启动脚本**

```bash
chmod +x start_server.sh
./start_server.sh
```

**方式二：直接运行Python**

```bash
python server.py
```

**方式三：自定义配置**

```bash
# 指定端口和后端
python server.py --port 8080 --backend openai

# 使用启动脚本
./start_server.sh -p 8080 -b openai

# 开发模式（热重载）
python server.py --reload
```

### 4. 访问API文档

服务启动后，访问以下地址查看交互式API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口说明

### 基础接口

#### GET / - 根路径

返回服务基本信息。

**响应示例：**
```json
{
  "message": "驾驶决策Agent API服务",
  "docs": "/docs",
  "health": "/health"
}
```

#### GET /health - 健康检查

检查服务状态和配置信息。

**响应示例：**
```json
{
  "status": "healthy",
  "backend": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "memory_enabled": true,
  "valid_decisions": [
    "Lane follow",
    "Left change lane",
    "Right change lane",
    "Left turn",
    "Right turn",
    "Straight"
  ]
}
```

#### GET /decisions - 获取有效决策列表

返回所有支持的驾驶决策指令。

**响应示例：**
```json
{
  "valid_decisions": [
    "Lane follow",
    "Left change lane",
    "Right change lane",
    "Left turn",
    "Right turn",
    "Straight"
  ],
  "count": 6
}
```

### 决策分析接口

#### POST /decide/upload - 文件上传方式

通过multipart/form-data上传四个摄像头图像文件。

**请求参数：**
- `front`: 前置摄像头图像文件
- `left`: 左侧摄像头图像文件
- `right`: 右侧摄像头图像文件
- `rear`: 后置摄像头图像文件

**cURL示例：**
```bash
curl -X POST "http://localhost:8000/decide/upload" \
  -F "front=@test_images/front.png" \
  -F "left=@test_images/left.png" \
  -F "right=@test_images/right.png" \
  -F "rear=@test_images/rear.png"
```

**Python示例：**
```python
import requests

# 创建session并禁用代理（避免localhost请求走代理）
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

# 关闭文件
for f in files.values():
    f.close()
```

> **注意**: 如果你的环境设置了HTTP代理（如`http_proxy`环境变量），访问localhost时可能会出现502错误。使用`session.trust_env = False`可以禁用代理，或者设置`export no_proxy=localhost,127.0.0.1`。

**响应示例：**
```json
{
  "decision": "Lane follow",
  "analysis": "前方道路畅通，车道线清晰可见。左右两侧无车辆，后方安全距离充足。建议保持当前车道继续行驶。",
  "success": true
}
```

#### POST /decide/base64 - Base64编码方式

通过JSON传递Base64编码的图像数据。

**请求体：**
```json
{
  "front_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "left_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "right_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "rear_image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Python示例：**
```python
import requests
import base64

def encode_image(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

url = "http://localhost:8000/decide/base64"
data = {
    'front_image': f"data:image/jpeg;base64,{encode_image('test_images/front.jpg')}",
    'left_image': f"data:image/jpeg;base64,{encode_image('test_images/left.jpg')}",
    'right_image': f"data:image/jpeg;base64,{encode_image('test_images/right.jpg')}",
    'rear_image': f"data:image/jpeg;base64,{encode_image('test_images/rear.jpg')}"
}

response = requests.post(url, json=data)
result = response.json()
print(f"决策: {result['decision']}")
print(f"分析: {result['analysis']}")
```

### 历史管理接口

#### POST /history/clear - 清空历史记录

清空Agent的决策历史记录。

**cURL示例：**
```bash
curl -X POST "http://localhost:8000/history/clear"
```

**响应示例：**
```json
{
  "message": "历史记录已清空",
  "success": true
}
```

#### GET /history/summary - 获取历史摘要

获取当前历史记录的统计信息。

**cURL示例：**
```bash
curl "http://localhost:8000/history/summary"
```

**响应示例：**
```json
{
  "total_conversations": 3,
  "max_history_size": 5,
  "max_image_history": 2,
  "image_rounds_stored": 2,
  "memory_enabled": true
}
```

## 配置选项

### 命令行参数

```bash
python server.py [选项]

选项:
  --host HOST           监听地址 (默认: 0.0.0.0)
  --port PORT           监听端口 (默认: 8000)
  --backend, -b         LLM后端类型 (anthropic/openai/gemini/qwen/deepseek)
  --model, -m           模型名称 (可选)
  --api-key, -k         API密钥 (可选，优先从环境变量读取)
  --no-memory           禁用上下文记忆功能
  --reload              启用热重载（开发模式）
```

### 环境变量

- `DECIDER_BACKEND`: 默认后端类型
- `DECIDER_MODEL`: 默认模型名称
- `DECIDER_MEMORY`: 是否启用记忆功能 (true/false)
- `ANTHROPIC_API_KEY`: Anthropic API密钥
- `OPENAI_API_KEY`: OpenAI API密钥
- `GOOGLE_API_KEY`: Google Gemini API密钥
- `DASHSCOPE_API_KEY`: 阿里云通义千问API密钥
- `DEEPSEEK_API_KEY`: DeepSeek API密钥

## 完整示例

### Python客户端示例

```python
import requests
import base64
from pathlib import Path

class DeciderClient:
    """驾驶决策API客户端"""

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def decide_from_files(self, front, left, right, rear):
        """通过文件上传进行决策"""
        files = {
            'front': open(front, 'rb'),
            'left': open(left, 'rb'),
            'right': open(right, 'rb'),
            'rear': open(rear, 'rb')
        }
        response = requests.post(f"{self.base_url}/decide/upload", files=files)
        return response.json()

    def decide_from_base64(self, front, left, right, rear):
        """通过Base64编码进行决策"""
        def encode(path):
            with open(path, 'rb') as f:
                return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"

        data = {
            'front_image': encode(front),
            'left_image': encode(left),
            'right_image': encode(right),
            'rear_image': encode(rear)
        }
        response = requests.post(f"{self.base_url}/decide/base64", json=data)
        return response.json()

    def clear_history(self):
        """清空历史记录"""
        response = requests.post(f"{self.base_url}/history/clear")
        return response.json()

    def get_history_summary(self):
        """获取历史摘要"""
        response = requests.get(f"{self.base_url}/history/summary")
        return response.json()

# 使用示例
if __name__ == "__main__":
    client = DeciderClient()

    # 健康检查
    health = client.health_check()
    print(f"服务状态: {health['status']}")
    print(f"后端: {health['backend']}, 模型: {health['model']}")

    # 执行决策
    result = client.decide_from_files(
        front="test_images/front.jpg",
        left="test_images/left.jpg",
        right="test_images/right.jpg",
        rear="test_images/rear.jpg"
    )

    print(f"\n决策结果: {result['decision']}")
    print(f"场景分析: {result['analysis']}")

    # 查看历史
    summary = client.get_history_summary()
    print(f"\n历史记录: {summary['total_conversations']}次对话")
```

### JavaScript/Node.js示例

```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

class DeciderClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async healthCheck() {
        const response = await axios.get(`${this.baseUrl}/health`);
        return response.data;
    }

    async decideFromFiles(front, left, right, rear) {
        const form = new FormData();
        form.append('front', fs.createReadStream(front));
        form.append('left', fs.createReadStream(left));
        form.append('right', fs.createReadStream(right));
        form.append('rear', fs.createReadStream(rear));

        const response = await axios.post(
            `${this.baseUrl}/decide/upload`,
            form,
            { headers: form.getHeaders() }
        );
        return response.data;
    }

    async clearHistory() {
        const response = await axios.post(`${this.baseUrl}/history/clear`);
        return response.data;
    }
}

// 使用示例
(async () => {
    const client = new DeciderClient();

    const health = await client.healthCheck();
    console.log(`服务状态: ${health.status}`);

    const result = await client.decideFromFiles(
        'test_images/front.jpg',
        'test_images/left.jpg',
        'test_images/right.jpg',
        'test_images/rear.jpg'
    );

    console.log(`决策: ${result.decision}`);
    console.log(`分析: ${result.analysis}`);
})();
```

## 错误处理

API使用标准HTTP状态码：

- `200`: 请求成功
- `400`: 请求参数错误（如Base64解码失败）
- `500`: 服务器内部错误（如LLM API调用失败）
- `503`: 服务不可用（Agent未初始化）
- `502`: 代理错误（通常是localhost请求走了代理）

**错误响应示例：**
```json
{
  "detail": "Agent未初始化"
}
```

### 常见错误及解决方案

#### 1. 502 Bad Gateway 错误

**问题**: 环境中设置了HTTP代理，导致localhost请求也走代理。

**解决方案**:

```python
# 方法1：使用Session禁用代理（推荐）
session = requests.Session()
session.trust_env = False
response = session.post(url, files=files)

# 方法2：使用proxies参数
response = requests.post(url, files=files, proxies={'http': None, 'https': None})

# 方法3：设置环境变量
import os
os.environ['no_proxy'] = 'localhost,127.0.0.1'
```

#### 2. Connection Refused 错误

**问题**: 服务未启动或端口不正确。

**解决方案**:
- 检查服务是否运行: `ps aux | grep server.py`
- 确认端口号是否正确
- 启动服务: `python server.py`

#### 3. JSON Decode 错误

**问题**: 响应不是有效的JSON（通常是502或其他HTTP错误）。

**解决方案**:
```python
response = session.post(url, files=files)
if response.status_code != 200:
    print(f"HTTP错误: {response.status_code}")
    print(f"响应内容: {response.text}")
else:
    result = response.json()
```

## 性能优化建议

1. **使用文件上传方式** (`/decide/upload`) 比Base64方式更高效
2. **启用记忆功能** 可以提供更连贯的决策，但会增加API调用成本
3. **定期清空历史** 如果不需要上下文连续性，可以定期调用 `/history/clear`
4. **选择合适的模型** 根据精度和速度需求选择不同的后端和模型

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

## 常见问题

**Q: 如何切换不同的LLM后端？**

A: 使用 `--backend` 参数或设置 `DECIDER_BACKEND` 环境变量。

**Q: 记忆功能是如何工作的？**

A: 启用记忆后，Agent会保留最近N次决策的上下文，使决策更连贯。可以通过 `--no-memory` 禁用。

**Q: 支持哪些图像格式？**

A: 支持常见的图像格式（JPEG、PNG等），具体取决于所使用的LLM后端。

**Q: API调用失败怎么办？**

A: 检查API密钥是否正确设置，网络连接是否正常，以及查看服务日志获取详细错误信息。

## 许可证

请参考项目根目录的LICENSE文件。
