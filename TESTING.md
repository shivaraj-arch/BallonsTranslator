# BallonsTranslator API - Testing Guide

## Overview

This guide covers testing the API backend and desktop frontend locally before deploying to Render.

---

## Part 1: Testing API Server

### 1.1 Start API Server

```bash
# Terminal 1
cd /path/to/BallonsTranslator
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
Uvicorn running on http://0.0.0.0:8000
Press CTRL+C to quit
```

### 1.2 Basic Health Check

```bash
# Terminal 2
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "BallonsTranslator API",
  "version": "1.0.0",
  "models_available": true
}
```

### 1.3 API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Both provide interactive endpoint testing.

---

## Part 2: Testing Individual Endpoints

### 2.1 List Available Models

**cURL:**
```bash
curl http://localhost:8000/models
```

**Expected Response:**
```json
{
  "detectors": ["craft", "craft_fast", "..."],
  "ocr_engines": ["easyocr", "paddleocr", "..."],
  "translators": ["chatgpt", "google", "deepl", "..."],
  "inpainters": ["lama", "propainter", "..."]
}
```

### 2.2 Load Models

**cURL:**
```bash
curl -X POST http://localhost:8000/models/load \
  -H "Content-Type: application/json" \
  -d '{
    "detector": "craft",
    "ocr": "easyocr",
    "translator": "google",
    "inpainter": "lama"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Models loaded successfully"
}
```

### 2.3 Text Detection

**Prepare image:**
```python
import base64
with open("test_image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()
```

**cURL:**
```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "'$img_base64'",
    "detector": "craft"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "detections": [
    {
      "text": "detected text",
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "confidence": 0.95
    }
  ],
  "processing_time_ms": 1250
}
```

### 2.4 OCR (Text Recognition)

**cURL:**
```bash
curl -X POST http://localhost:8000/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image": "'$img_base64'",
    "ocr_engine": "easyocr",
    "languages": ["en", "ja"]
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "texts": [
    {
      "text": "recognized text",
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "confidence": 0.92,
      "language": "ja"
    }
  ],
  "processing_time_ms": 3400
}
```

### 2.5 Translation

**cURL:**
```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["みなさん、こんにちは"],
    "translator": "google",
    "source_lang": "ja",
    "target_lang": "en"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "translations": [
    {
      "original": "みなさん、こんにちは",
      "translated": "Everyone, hello",
      "confidence": 0.95
    }
  ],
  "processing_time_ms": 890
}
```

### 2.6 Full Pipeline

**Prepare test image first:**
```bash
# Use a manga page screenshot
cp /path/to/manga_page.jpg test_image.jpg
```

**Python test:**
```python
import base64
import requests

with open("test_image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "http://localhost:8000/pipeline/full",
    json={
        "image": img_base64,
        "detector": "craft",
        "ocr": "easyocr",
        "translator": "google",
        "inpainter": "lama",
        "source_lang": "ja",
        "target_lang": "en"
    }
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Total time: {result['total_processing_time_ms']}ms")
```

**Expected Response:**
```json
{
  "success": true,
  "detections": [...],
  "ocr_results": [...],
  "translations": [...],
  "inpaint_image": "base64_encoded_result",
  "total_processing_time_ms": 8500
}
```

---

## Part 3: Testing with Python Client

### 3.1 Using httpx Directly

```python
import httpx
import base64

client = httpx.Client(timeout=300)

# Test health
response = client.get("http://localhost:8000/health")
print("Health:", response.json())

# Load test image
with open("test_image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# Get available models
models = client.get("http://localhost:8000/models").json()
print("Available models:", models)

# Run detect
detect_response = client.post(
    "http://localhost:8000/detect",
    json={"image": img_base64, "detector": "craft"}
)
print("Detection result:", detect_response.json())

client.close()
```

### 3.2 Using Desktop App API Client

The `BallonsAPIClient` class (in `launch_desktop.py`) already handles all of this:

```python
from launch_desktop import BallonsAPIClient

client = BallonsAPIClient(api_url="http://localhost:8000")

# Test connection
if client.health_check():
    print("✓ API is healthy")

# Get models
models = client.get_models()
print("Available models:", models)

# Load models
success = client.load_models(
    detector="craft",
    ocr="easyocr",
    translator="google",
    inpainter="lama"
)
print("Models loaded:", success)
```

---

## Part 4: Testing Desktop Application

### 4.1 Configuration

**Edit `launch_desktop.py`:**
```python
# Line 1: Set to local API
API_URL = "http://localhost:8000"
```

### 4.2 Run Desktop App

**Ensure API is running (Terminal 1), then in Terminal 2:**
```bash
python launch_desktop.py
```

### 4.3 Test Workflow

1. **Launch the app**
   - Should show "✓ API Connected" in status
   - Models dropdown should be populated

2. **Upload image**
   - Click "Browse File"
   - Select `test_image.jpg`
   - Image preview should appear

3. **Configure translation**
   - Source language: Japanese
   - Target language: English
   - Detector: craft
   - OCR: easyocr
   - Translator: google
   - Inpainter: lama

4. **Run pipeline**
   - Click "Start Translation"
   - Progress bar should update: Detecting... → OCR... → Translating... → Inpainting...
   - Status shows actual processing time

5. **View results**
   - "Result Image" tab: Shows inpainted image
   - "Extracted Text" tab: Shows detected + recognized text
   - "Translated Text" tab: Shows translations
   - "Detection Info" tab: Shows bounding boxes

6. **Save results**
   - Right-click result image → Save
   - Results saved to current directory

### 4.4 Test Error Handling

**Test 1: Wrong image format**
- Upload invalid file (e.g., text file)
- Should show error: "Invalid image file"

**Test 2: Server offline**
- Stop API server
- Try to run pipeline
- Should show: "Failed to connect to API"

**Test 3: Out of memory**
- Update `TIMEOUT = 60` for faster failure
- Try translating very large image
- Should show timeout error with helpful message

---

## Part 5: Automated Testing

### 5.1 pytest Setup

Create `tests/test_api.py`:

```python
import pytest
import httpx
import base64
from api.server import app
from api.pipeline import get_pipeline

@pytest.fixture
def client():
    return httpx.Client(app=app, base_url="http://test")

def test_health(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_list_models(client):
    """Test models listing"""
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "detectors" in data
    assert "ocr_engines" in data

def test_detect_endpoint(client):
    """Test detection endpoint"""
    # Create dummy image base64
    img_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    img_base64 = base64.b64encode(img_data).decode()
    
    response = client.post(
        "/detect",
        json={"image": img_base64, "detector": "craft"}
    )
    # Should succeed or fail gracefully
    assert response.status_code in [200, 400]
```

**Run tests:**
```bash
pytest tests/test_api.py -v
```

---

## Part 6: Load Testing

### 6.1 Using Apache Bench

```bash
# Single request
ab -n 1 -c 1 http://localhost:8000/health

# 10 concurrent requests
ab -n 10 -c 5 http://localhost:8000/health
```

### 6.2 Using wrk

```bash
# 4 threads, 100 connections, 30 second test
wrk -t4 -c100 -d30s http://localhost:8000/health
```

### 6.3 Image Processing Load

```python
import concurrent.futures
import time
import base64
import httpx

def process_image(image_base64, request_id):
    client = httpx.Client(timeout=300)
    start = time.time()
    
    response = client.post(
        "http://localhost:8000/pipeline/full",
        json={
            "image": image_base64,
            "detector": "craft",
            "ocr": "easyocr",
            "translator": "google",
            "inpainter": "lama"
        }
    )
    
    elapsed = time.time() - start
    return {
        "request_id": request_id,
        "status": response.status_code,
        "time": elapsed
    }

# Load test image
with open("test_image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# Send 5 sequential requests (not parallel - Render free tier)
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    futures = [
        executor.submit(process_image, img_base64, i)
        for i in range(5)
    ]
    
    results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
for r in results:
    print(f"Request {r['request_id']}: {r['status']} ({r['time']:.1f}s)")
```

---

## Part 7: Debugging Tips

### 7.1 Enable Debug Logging

**Edit `api/server.py`:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 7.2 Check Request/Response

**Using httpx:**
```python
response = client.post(
    "http://localhost:8000/detect",
    json={"image": img_base64, "detector": "craft"}
)

print("Status:", response.status_code)
print("Headers:", response.headers)
print("Body:", response.json())
```

### 7.3 GPU Memory Check

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU memory: {torch.cuda.get_device_properties(0)}")
```

### 7.4 Profile Inference Time

```python
import time

start = time.perf_counter()
# ... do inference ...
elapsed = (time.perf_counter() - start) * 1000
print(f"Inference took {elapsed:.1f}ms")
```

---

## Part 8: Checklist

- [ ] API server starts without errors
- [ ] Health endpoint responds
- [ ] All models list correctly
- [ ] Models load successfully
- [ ] Detection works on sample image
- [ ] OCR works on sample image
- [ ] Translation works on sample text
- [ ] Full pipeline completes successfully
- [ ] Desktop app connects to API
- [ ] Desktop app displays results
- [ ] Error handling works (wrong files, offline API)
- [ ] Results can be saved to disk
- [ ] Response times are acceptable (<15s for full pipeline)

---

## Expected Performance

### Render Free Tier (CPU-only)

| Operation | Time |
|-----------|------|
| Detection | 5-15s |
| OCR | 5-10s |
| Translation | 1-3s |
| Inpainting | 10-30s |
| **Full Pipeline** | **20-60s** |

*Much slower than local, but functional. Expected due to CPU inference on shared infrastructure.*

### Local Development (varies by hardware)

| Operation | Time (CPU) | Time (GPU) |
|-----------|-----------|-----------|
| Detection | 2-4s | 0.5-1s |
| OCR | 2-5s | 1-2s |
| Translation | 0.5-2s | 0.5-1s |
| Inpainting | 3-8s | 1-2s |
| **Full Pipeline** | **8-20s** | **3-6s** |

*Times vary based on image size, model choice, and hardware*

<!-- Note: GPU support requires paid Render plan or local GPU hardware -->

---

## Next Steps

After successful testing:
1. ✅ All local tests passing
2. Push to GitHub
3. Deploy to Render
4. Test with public API URL
5. Update desktop app to use production API

---

**Version:** 1.0.0  
**Last Updated:** March 2026
