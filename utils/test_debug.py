"""
Debug script to test the upload endpoint
"""
import cv2
import requests
import numpy as np
from pathlib import Path
import sys

# Load test images
test_path = Path('test_images')
front_img = cv2.imread(str(test_path / 'front.png'))

if front_img is None:
    print("Failed to load image")
    sys.exit(1)

print(f'Loaded front image: {front_img.shape}')

# Encode to JPEG bytes
success, buffer = cv2.imencode('.jpg', front_img)
print(f'Encode success: {success}')

# Convert to bytes
img_bytes = buffer.tobytes()
print(f'Bytes length: {len(img_bytes)}')

# Try to upload
files = {
    'front': ('front.jpg', img_bytes, 'image/jpeg'),
    'left': ('left.jpg', img_bytes, 'image/jpeg'),
    'right': ('right.jpg', img_bytes, 'image/jpeg'),
    'rear': ('rear.jpg', img_bytes, 'image/jpeg')
}

session = requests.Session()
session.trust_env = False

print("\nSending request to server...")
try:
    response = session.post('http://localhost:8000/decide/upload', files=files, timeout=60)
    print(f'Status code: {response.status_code}')
    print(f'Response: {response.text}')
except requests.exceptions.Timeout:
    print("Request timed out after 60 seconds")
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
