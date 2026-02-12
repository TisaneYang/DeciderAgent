# 时间戳功能说明

## 功能概述

在驾驶决策系统中，时间信息对于理解场景变化至关重要。本功能支持客户端传递图像采集时的Unix时间戳，帮助模型理解：

- **场景变化速度**：时间间隔短说明是连续帧，间隔长说明场景可能已变化
- **车辆移动距离**：根据时间间隔推断车辆可能的移动距离
- **决策紧急程度**：连续请求可能表示复杂场景需要持续关注

## 时间戳格式

客户端提供的时间戳应使用 **Unix时间戳字符串**格式：

```
"1707734562.134"
```

服务端会自动将其转换为可读格式并计算时间间隔：

```
[时间戳: 2024-02-12 18:42:42.134] (距上次请求: 0.501秒)
```

- 格式：Unix时间戳字符串（秒，浮点数）
- 精度：毫秒级
- 如果是首次请求，不显示时间间隔

## 实现细节

### 1. 客户端传递时间戳

时间戳由客户端在**图像采集时**生成，而不是在发送请求时生成。这样可以准确反映图像的真实采集时间。

**Python客户端示例：**

```python
import time
from backends import CameraImages

# 采集图像时记录Unix时间戳
timestamp = str(time.time())  # 例如: "1707734562.134"

# 创建图像对象时传入时间戳
images = CameraImages(
    front="front.png",
    left="left.png",
    right="right.png",
    rear="rear.png",
    timestamp=timestamp  # 客户端提供的Unix时间戳字符串
)

# 执行决策
result = agent.decide(images)
```

### 2. HTTP API 接口

#### Base64 模式

```python
import requests
import time

data = {
    "front_image": "data:image/jpeg;base64,...",
    "left_image": "data:image/jpeg;base64,...",
    "right_image": "data:image/jpeg;base64,...",
    "rear_image": "data:image/jpeg;base64,...",
    "timestamp": str(time.time())  # Unix时间戳字符串
}

response = requests.post("http://localhost:8000/decide/base64", json=data)
```

#### 文件上传模式

```python
import requests
import time

files = {
    'front': open('front.png', 'rb'),
    'left': open('left.png', 'rb'),
    'right': open('right.png', 'rb'),
    'rear': open('rear.png', 'rb')
}

data = {
    'timestamp': str(time.time())  # Unix时间戳字符串
}

response = requests.post(
    "http://localhost:8000/decide/upload",
    files=files,
    data=data
)
```

### 3. 系统提示更新

在 `prompts.py` 中，系统提示已更新为包含时间戳说明：

```python
SYSTEM_PROMPT = """你是一个专业的自动驾驶决策系统。...

每次请求都会包含时间戳信息，格式为"[时间戳: YYYY-MM-DD HH:MM:SS.mmm]"。
请注意时间戳之间的间隔，这有助于你理解：
- 场景变化的速度（间隔短说明连续帧，间隔长说明场景可能已变化）
- 车辆可能的移动距离（根据时间间隔推断）
- 决策的紧急程度（连续请求可能表示复杂场景）
...
"""
```

### 4. DeciderAgent 处理逻辑

在 `decider_agent.py` 中：

- 从 `CameraImages` 对象中读取客户端提供的Unix时间戳字符串
- 将Unix时间戳转换为可读的日期时间格式
- 如果有上次时间戳，计算时间间隔
- 将时间信息传递给后端

```python
def decide(self, images: CameraImages) -> DecisionResult:
    # 构建时间信息（使用客户端提供的Unix时间戳）
    time_info = ""
    if images.timestamp:
        try:
            # 将Unix时间戳字符串转换为浮点数
            current_timestamp = float(images.timestamp)

            # 转换为可读的时间格式
            from datetime import datetime
            dt = datetime.fromtimestamp(current_timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            time_info = f"[时间戳: {time_str}]"

            # 如果有上次时间戳，计算时间间隔
            if self.last_timestamp:
                try:
                    last_timestamp = float(self.last_timestamp)
                    time_delta = current_timestamp - last_timestamp
                    time_info += f" (距上次请求: {time_delta:.3f}秒)"
                except (ValueError, TypeError):
                    pass

            # 更新上次时间戳
            self.last_timestamp = images.timestamp

        except (ValueError, TypeError):
            # 如果时间戳格式无法解析，只显示原始值
            time_info = f"[时间戳: {images.timestamp}]"
            self.last_timestamp = images.timestamp

    # 调用后端进行决策
    result = self.backend.decide(images, history, time_info)
    ...
```

## 使用示例

### 基本使用（Python API）

```python
import time
from decider_agent import DeciderAgent
from backends import CameraImages

agent = DeciderAgent(backend_type="anthropic", enable_memory=True)

# 第一次请求（无时间间隔）
timestamp1 = str(time.time())
images1 = CameraImages(
    front="test_images/front.png",
    left="test_images/left.png",
    right="test_images/right.png",
    rear="test_images/rear.png",
    timestamp=timestamp1
)
result1 = agent.decide(images1)
# 模型收到: [时间戳: 2024-02-12 18:42:42.134]

# 等待一段时间后的第二次请求（显示时间间隔）
import time as time_module
time_module.sleep(1.5)

timestamp2 = str(time.time())
images2 = CameraImages(
    front="test_images/front.png",
    left="test_images/left.png",
    right="test_images/right.png",
    rear="test_images/rear.png",
    timestamp=timestamp2
)
result2 = agent.decide(images2)
# 模型收到: [时间戳: 2024-02-12 18:42:43.634] (距上次请求: 1.500秒)
```

### HTTP API 使用（Numpy数组）

```python
import cv2
import time
from utils.test_client import DeciderClient

client = DeciderClient(base_url="http://localhost:8000")

# 从摄像头采集图像
cap = cv2.VideoCapture(0)
ret, front_img = cap.read()

# 记录采集时的Unix时间戳
timestamp = str(time.time())

# 传输到API（带时间戳）
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True,
    timestamp=timestamp  # 传递Unix时间戳字符串
)

print(f"决策: {result['decision']}")
```

### 实时视频流处理

```python
import cv2
import time
from utils.test_client import DeciderClient

client = DeciderClient(base_url="http://localhost:8000")

# 打开摄像头
cap_front = cv2.VideoCapture(0)
cap_left = cv2.VideoCapture(1)
cap_right = cv2.VideoCapture(2)
cap_rear = cv2.VideoCapture(3)

while True:
    # 同时采集四个摄像头的图像
    ret_front, front_img = cap_front.read()
    ret_left, left_img = cap_left.read()
    ret_right, right_img = cap_right.read()
    ret_rear, rear_img = cap_rear.read()

    # 记录采集时的Unix时间戳（所有图像使用同一时间戳）
    timestamp = str(time.time())

    if all([ret_front, ret_left, ret_right, ret_rear]):
        # 发送决策请求
        result = client.decide_from_numpy(
            front=front_img,
            left=left_img,
            right=right_img,
            rear=rear_img,
            use_base64=True,
            timestamp=timestamp
        )

        print(f"[{timestamp}] 决策: {result['decision']}")

    # 控制帧率（例如10fps）
    time.sleep(0.1)
```

## 模型如何使用时间信息

模型可以根据时间戳做出更智能的决策：

### 场景1：连续帧（间隔 < 0.1秒）
```
[时间戳: 2024-02-12 18:42:42.100] (距上次请求: 0.033秒)
```
- 说明：这是30fps视频流的连续帧
- 模型理解：场景变化很小，可以参考上一帧的决策
- 决策策略：保持稳定，避免频繁变更指令

### 场景2：正常间隔（0.1-1秒）
```
[时间戳: 2024-02-12 18:42:42.500] (距上次请求: 0.500秒)
```
- 说明：正常的决策频率
- 模型理解：场景可能有一定变化
- 决策策略：综合当前图像和历史信息做决策

### 场景3：长间隔（> 1秒）
```
[时间戳: 2024-02-12 18:42:47.000] (距上次请求: 5.000秒)
```
- 说明：场景可能已经完全不同
- 模型理解：需要重新评估整个场景
- 决策策略：更多依赖当前图像，减少对历史的依赖

## 测试

运行测试脚本验证功能：

```bash
conda activate dc9
python test_timestamp.py
```

## 注意事项

1. **时间戳由客户端生成**：时间戳应在图像采集时生成，而不是在发送请求时生成
2. **时间戳格式**：使用Unix时间戳字符串格式（如 `"1707734562.134"`）
3. **时间戳可选**：如果不提供时间戳，系统仍可正常工作，只是不会显示时间信息
4. **历史记录保留**：时间戳信息会保存在对话历史中
5. **清空历史**：调用 `clear_history()` 会重置时间戳记录
6. **所有后端支持**：所有LLM后端都支持时间戳功能

## 时间戳格式说明

**Unix时间戳（当前实现）：**
- ✅ 标准格式，跨平台兼容
- ✅ 易于计算时间间隔
- ✅ 不受时区影响
- ✅ 精度可达毫秒级

**生成方式：**

Python:
```python
import time
timestamp = str(time.time())  # "1707734562.134"
```

JavaScript:
```javascript
const timestamp = String(Date.now() / 1000);  // "1707734562.134"
```

C++:
```cpp
#include <chrono>
auto now = std::chrono::system_clock::now();
auto timestamp = std::chrono::duration<double>(now.time_since_epoch()).count();
```

## 未来改进方向

1. **时间戳验证**：验证时间戳的合理性（不能是未来时间）
2. **时间戳统计**：提供平均请求间隔等统计信息
3. **异常检测**：检测异常的时间间隔（如过长或过短）
4. **时间戳可视化**：在历史摘要中显示时间线
5. **高精度支持**：支持纳秒级精度的时间戳
