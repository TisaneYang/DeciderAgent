# Numpy数组传输指南

本文档说明如何将OpenCV的numpy数组格式图像传输给驾驶决策Agent API。

## 图像格式说明

### 输入格式
- **存储格式**: `numpy.ndarray`
- **数据类型**: `uint8`
- **形状**: `(height, width, 3)`
- **颜色空间**: BGR（OpenCV默认）

### 支持的传输方式

1. **Base64编码模式**（推荐用于网络传输）
2. **文件上传模式**（适合本地API调用）

---

## 快速开始

### 1. 安装依赖

```bash
pip install opencv-python numpy requests
```

### 2. 基本使用

```python
import cv2
from utils.test_client import DeciderClient

# 初始化客户端
client = DeciderClient(base_url="http://localhost:8000")

# 读取图像（BGR格式的numpy数组）
front_img = cv2.imread("front.png")  # shape: (H, W, 3), dtype: uint8
left_img = cv2.imread("left.png")
right_img = cv2.imread("right.png")
rear_img = cv2.imread("rear.png")

# 方式1：Base64模式（推荐）
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True  # 使用Base64编码
)

# 方式2：文件上传模式
result = client.decide_from_numpy(
    front=front_img,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=False  # 使用文件上传
)

print(f"决策: {result['decision']}")
print(f"分析: {result['analysis']}")
```

---

## 详细说明

### Base64模式工作原理

```python
def numpy_to_base64(img: np.ndarray) -> str:
    """将numpy数组转换为base64字符串"""
    # 1. 将numpy数组编码为JPEG格式
    success, buffer = cv2.imencode('.jpg', img)

    # 2. 转换为base64字符串
    encoded = base64.b64encode(buffer).decode()

    # 3. 添加Data URL前缀
    return f"data:image/jpeg;base64,{encoded}"
```

**优点**:
- 适合远程API调用
- 无需创建临时文件
- 可以直接通过JSON传输

**缺点**:
- Base64编码会增加约33%的数据量
- 编码/解码有一定CPU开销

### 文件上传模式工作原理

```python
def numpy_to_bytes(img: np.ndarray) -> bytes:
    """将numpy数组转换为JPEG字节流"""
    success, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()

# 构造multipart/form-data请求
files = {
    'front': ('front.jpg', numpy_to_bytes(front), 'image/jpeg'),
    'left': ('left.jpg', numpy_to_bytes(left), 'image/jpeg'),
    'right': ('right.jpg', numpy_to_bytes(right), 'image/jpeg'),
    'rear': ('rear.jpg', numpy_to_bytes(rear), 'image/jpeg')
}
```

**优点**:
- 传输效率高（无Base64编码开销）
- 适合大图像传输

**缺点**:
- 需要构造multipart/form-data请求
- 不如Base64方式简洁

---

## 使用场景示例

### 场景1: 从摄像头实时读取

```python
import cv2
from utils.test_client import DeciderClient

client = DeciderClient()

# 打开摄像头
cap_front = cv2.VideoCapture(0)
cap_left = cv2.VideoCapture(1)
cap_right = cv2.VideoCapture(2)
cap_rear = cv2.VideoCapture(3)

while True:
    # 读取一帧
    ret_front, front_img = cap_front.read()
    ret_left, left_img = cap_left.read()
    ret_right, right_img = cap_right.read()
    ret_rear, rear_img = cap_rear.read()

    if all([ret_front, ret_left, ret_right, ret_rear]):
        # 进行决策
        result = client.decide_from_numpy(
            front=front_img,
            left=left_img,
            right=right_img,
            rear=rear_img,
            use_base64=True
        )

        print(f"决策: {result['decision']}")
```

### 场景2: 图像预处理

```python
import cv2
import numpy as np
from utils.test_client import DeciderClient

client = DeciderClient()

# 读取原始图像
front_img = cv2.imread("front.png")

# 预处理：调整大小（减少传输数据量）
front_resized = cv2.resize(front_img, (640, 480))

# 预处理：亮度调整
front_adjusted = cv2.convertScaleAbs(front_resized, alpha=1.2, beta=10)

# 预处理：去噪
front_denoised = cv2.fastNlMeansDenoisingColored(front_adjusted)

# 传输预处理后的图像
result = client.decide_from_numpy(
    front=front_denoised,
    left=left_img,
    right=right_img,
    rear=rear_img,
    use_base64=True
)
```

### 场景3: 批量处理

```python
import cv2
from pathlib import Path
from utils.test_client import DeciderClient

client = DeciderClient()

# 遍历数据集
dataset_dir = Path("dataset")
for scene_dir in dataset_dir.iterdir():
    if scene_dir.is_dir():
        # 读取四个视角的图像
        front = cv2.imread(str(scene_dir / "front.png"))
        left = cv2.imread(str(scene_dir / "left.png"))
        right = cv2.imread(str(scene_dir / "right.png"))
        rear = cv2.imread(str(scene_dir / "rear.png"))

        # 进行决策
        result = client.decide_from_numpy(
            front=front, left=left, right=right, rear=rear,
            use_base64=True
        )

        print(f"{scene_dir.name}: {result['decision']}")
```

---

## 性能优化建议

### 1. 图像尺寸优化

```python
# 调整图像大小以减少传输数据量
target_size = (640, 480)  # 根据实际需求调整
front_resized = cv2.resize(front_img, target_size)
```

### 2. JPEG质量调整

```python
# 自定义JPEG编码质量（0-100）
encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]  # 默认95
success, buffer = cv2.imencode('.jpg', img, encode_param)
```

### 3. 使用连接池

```python
# DeciderClient内部已使用requests.Session
# 自动复用TCP连接，提升性能
client = DeciderClient()
```

### 4. 异步处理（高级）

```python
import asyncio
import aiohttp

async def async_decide(session, images):
    # 使用aiohttp进行异步请求
    # 可以并发处理多个决策请求
    pass
```

---

## 测试工具

### 命令行测试

```bash
# 测试numpy数组模式（Base64）
python utils/test_client.py --numpy --base64

# 测试numpy数组模式（文件上传）
python utils/test_client.py --numpy

# 运行示例代码
python utils/numpy_example.py --example 2
```

### 可用示例

```bash
# 示例1: 从摄像头读取
python utils/numpy_example.py --example 1

# 示例2: 从文件读取（推荐先运行此示例）
python utils/numpy_example.py --example 2

# 示例3: 图像预处理
python utils/numpy_example.py --example 3

# 示例4: 连续决策
python utils/numpy_example.py --example 4

# 示例5: 批量处理
python utils/numpy_example.py --example 5
```

---

## API参考

### DeciderClient.decide_from_numpy()

```python
def decide_from_numpy(
    self,
    front: np.ndarray,
    left: np.ndarray,
    right: np.ndarray,
    rear: np.ndarray,
    use_base64: bool = True
) -> dict
```

**参数**:
- `front`: 前置摄像头图像，numpy数组 (H, W, 3) BGR格式
- `left`: 左侧摄像头图像，numpy数组 (H, W, 3) BGR格式
- `right`: 右侧摄像头图像，numpy数组 (H, W, 3) BGR格式
- `rear`: 后置摄像头图像，numpy数组 (H, W, 3) BGR格式
- `use_base64`: 是否使用Base64模式（True）或文件上传模式（False）

**返回**:
```python
{
    "decision": "Lane follow",  # 决策指令
    "analysis": "前方道路畅通...",  # 场景分析
    "success": True  # 请求是否成功
}
```

**异常**:
- `ValueError`: 图像编码失败
- `requests.HTTPError`: HTTP请求失败
- `requests.ConnectionError`: 连接失败

---

## 常见问题

### Q1: 图像是RGB格式怎么办？

OpenCV默认使用BGR格式，如果你的图像是RGB格式：

```python
# 方式1: 转换为BGR
front_bgr = cv2.cvtColor(front_rgb, cv2.COLOR_RGB2BGR)

# 方式2: 直接使用（API会自动处理）
# 大多数情况下，颜色顺序不会严重影响决策结果
```

### Q2: 支持PNG格式吗？

支持，但内部会转换为JPEG传输：

```python
# 可以指定编码格式
success, buffer = cv2.imencode('.png', img)  # 使用PNG
success, buffer = cv2.imencode('.jpg', img)  # 使用JPEG（默认）
```

### Q3: 如何处理灰度图像？

需要转换为3通道：

```python
# 灰度图转BGR
if len(gray_img.shape) == 2:
    bgr_img = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
```

### Q4: 图像尺寸有限制吗？

建议：
- 最小尺寸: 320x240
- 推荐尺寸: 640x480 或 1280x720
- 最大尺寸: 1920x1080（更大的图像会增加传输时间）

### Q5: Base64和文件上传哪个更快？

- **本地API**: 文件上传模式更快（无编码开销）
- **远程API**: Base64模式更简洁，性能差异不大
- **大图像**: 文件上传模式更优

---

## 完整示例代码

```python
#!/usr/bin/env python3
"""完整的numpy数组使用示例"""

import cv2
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from utils.test_client import DeciderClient


def main():
    # 1. 初始化客户端
    client = DeciderClient(base_url="http://localhost:8000")

    # 2. 健康检查
    try:
        health = client.health_check()
        print(f"✓ 服务状态: {health['status']}")
    except Exception as e:
        print(f"✗ 服务不可用: {e}")
        return

    # 3. 读取图像
    front = cv2.imread("test_images/front.png")
    left = cv2.imread("test_images/left.png")
    right = cv2.imread("test_images/right.png")
    rear = cv2.imread("test_images/rear.png")

    if any(img is None for img in [front, left, right, rear]):
        print("✗ 图像加载失败")
        return

    print(f"✓ 图像加载成功: {front.shape}, {front.dtype}")

    # 4. 进行决策（Base64模式）
    try:
        result = client.decide_from_numpy(
            front=front,
            left=left,
            right=right,
            rear=rear,
            use_base64=True
        )

        print(f"\n【决策指令】{result['decision']}")
        print(f"\n【场景分析】\n{result['analysis']}")

    except Exception as e:
        print(f"✗ 决策失败: {e}")


if __name__ == "__main__":
    main()
```

---

## 总结

使用numpy数组传输图像的关键步骤：

1. **读取图像**: 使用`cv2.imread()`或摄像头读取
2. **选择模式**: Base64（远程）或文件上传（本地）
3. **调用API**: 使用`client.decide_from_numpy()`
4. **处理结果**: 获取决策指令和场景分析

两种传输方式都已完全实现并测试通过，可根据实际场景选择使用。
