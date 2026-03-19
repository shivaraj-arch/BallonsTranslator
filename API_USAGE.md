# BallonsTranslator API - Deployment & Usage Guide

## Quick Start

### Option 1: Use Public API (Simple)
The API is deployed on Render:
```
https://ballons-translator-api.onrender.com/
```

**Run the desktop client:**
```bash
python launch_desktop.py
```

### Option 2: Local API Server (Development)
1. Install dependencies:
```bash
pip install -r api/requirements.txt
```

2. Start the server:
```bash
# Using uvicorn
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Or using FastAPI CLI
fastapi run api/server.py
```

3. Access the API:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### Health Check
```
GET /health
```
Returns API status and version.

### Model Management

#### List Available Models
```
GET /models
```
Returns all available detectors, OCR engines, translators, and inpainters.

#### Load Models
```
POST /models/load
```
Load specific ML models into memory.

**Request:**
```json
{
  "detector": "craft",
  "ocr": "paddleocr",
  "translator": "google",
  "inpainter": "lama"
}
```

### Pipeline Endpoints

#### Text Detection
```
POST /detect
```
Detect text regions in an image.

**Request:**
```json
{
  "image_base64": "base64_encoded_image_data"
}
```

**Response:**
```json
{
  "status": "success",
  "regions": [...],
  "count": 5
}
```

#### OCR (Text Recognition)
```
POST /ocr
```
Extract text from image regions.

**Request:**
```json
{
  "image_base64": "base64_encoded_image_data",
  "regions": [optional_region_list]
}
```

**Response:**
```json
{
  "status": "success",
  "texts": ["text1", "text2"],
  "count": 2
}
```

#### Translation
```
POST /translate
```
Translate text strings.

**Request:**
```json
{
  "texts": ["text1", "text2"],
  "source_lang": "auto",
  "target_lang": "English"
}
```

**Response:**
```json
{
  "status": "success",
  "translations": ["translated1", "translated2"],
  "count": 2
}
```

#### Image Inpainting
```
POST /inpaint
```
Remove text from images.

**Request:**
```json
{
  "image_base64": "base64_encoded_image",
  "mask_base64": "base64_encoded_mask"
}
```

**Response:**
```json
{
  "status": "success",
  "image_base64": "base64_encoded_result"
}
```

### Full Pipeline
```
POST /pipeline/full
```
Run complete translation pipeline: detect → OCR → translate → inpaint.

**Request:**
```json
{
  "image_base64": "base64_encoded_image",
  "source_lang": "auto",
  "target_lang": "English",
  "enable_detection": true,
  "enable_ocr": true,
  "enable_translation": true,
  "enable_inpainting": false
}
```

**Response:**
```json
{
  "status": "success",
  "detected_regions": [...],
  "extracted_texts": ["text1", "text2"],
  "translated_texts": ["translated1", "translated2"],
  "inpainted_image_base64": "base64_encoded_result"
}
```

---

## Desktop Application

### Features
- ✅ Image upload and preview
- ✅ Configurable language pairs
- ✅ Module selection (detector, OCR, translator, inpainter)
- ✅ Pipeline step toggling
- ✅ Real-time progress tracking
- ✅ Results in tabbed interface (image, extracted text, translated text, detection info)
- ✅ Save translated images

### Configuration
Edit `launch_desktop.py` to change API URL:
```python
API_URL = "https://ballons-translator-api.onrender.com"  # Remote
# API_URL = "http://localhost:8000"  # Local
```

---

## Deployment to Render

1. Create `Procfile`:
```
web: uvicorn api.server:app --host 0.0.0.0 --port $PORT
```

2. Push to GitHub and connect to Render

3. Configure environment:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: See Procfile

---

## Python Requirements

### API Server
See `api/requirements.txt`

### Desktop Client (additional)
- PyQt6
- httpx (or requests)
- Pillow

Install both:
```bash
pip install -r requirements.txt
pip install -r api/requirements.txt
```

---

## Architecture

```
Desktop App (launch_desktop.py)
    ↓
HTTP Requests (httpx)
    ↓
API Server (api/server.py)
    ↓
Pipeline (api/pipeline.py)
    ↓
ML Modules (modules/ + utils/)
    ↓
Models (detector, OCR, translator, inpainter)
```

### Key Files
- `api/server.py` - FastAPI application with all endpoints
- `api/pipeline.py` - ML inference pipeline wrapper
- `launch_desktop.py` - PyQt6 desktop client
- `api/requirements.txt` - API dependencies

---

## Error Handling

If API is unavailable:
1. Desktop app gracefully shows error messages
2. Check API health: `GET /health`
3. View logs in server/desktop console
4. Ensure models are loaded: `POST /models/load`

---

## Performance Tips

1. **Pre-load models** on server startup to reduce first-request latency
2. **Use appropriate image sizes** (reduce resolution if needed)
3. **Cache results** on client side if processing same images
4. **Choose efficient models** - balance speed vs accuracy

---

## Support

For issues or questions:
1. Check API docs: `/docs` endpoint
2. Review error messages in desktop app
3. Check server logs for details
4. Verify network connectivity to API

---

## Version
API Version: 1.0.0
Desktop Version: 1.0.0
