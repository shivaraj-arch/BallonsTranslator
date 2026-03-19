# BallonsTranslator API - Configuration Guide

## Overview

This guide explains how to configure the API backend and desktop frontend for different deployment scenarios.

---

## Part 1: API URL Configuration

The desktop app can connect to either a **local development API** or a **remote Render API**.

### Option 1: Local Development

**Edit `launch_desktop.py` (Line 1):**
```python
API_URL = "http://localhost:8000"
```

**Usage:**
- Start API server: `uvicorn api.server:app --host 0.0.0.0 --port 8000`
- Run desktop: `python launch_desktop.py`
- Development, fast iteration, debugging
- Images never leave your machine

### Option 2: Remote Render API

**Edit `launch_desktop.py` (Line 1):**
```python
API_URL = "https://ballons-translator-api.onrender.com"
```

**Usage:**
- API running on Render.com
- Connect from any device with internet
- Shared resource (may be slower than local)
- Models run on Render's infrastructure

### Option 3: Custom Server

For self-hosted or other cloud providers:

```python
API_URL = "https://your-custom-domain.com"
API_URL = "https://api.yourdomain.com:8443"  # With custom port
```

---

## Part 2: Environment Variables

### API Server Configuration

**Set environment variables before running uvicorn:**

```bash
# Development mode
export DEBUG=1
export LOG_LEVEL=DEBUG

# Production mode
export DEBUG=0
export LOG_LEVEL=INFO

# Custom port
export PORT=8000

# CORS settings
export CORS_ORIGINS="['https://yourdomain.com', 'http://localhost:3000']"

# Model paths
export MODEL_CACHE_DIR="/path/to/model/cache"
export MODEL_DOWNLOAD_DIR="/path/to/downloads"

# Resource limits
export MAX_IMAGE_SIZE=10485760  # 10MB in bytes
export API_TIMEOUT=300  # 5 minutes

# Render specific
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
```

**Usage example:**
```bash
# Set and run
export DEBUG=1
export PORT=8000
uvicorn api.server:app --host 0.0.0.0 --port $PORT
```

### Desktop Client Configuration

Currently in `launch_desktop.py`:

```python
# API connection
API_URL = "http://localhost:8000"
TIMEOUT = 300  # 5 minutes for processing

# UI settings
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
THEME_COLOR = "#3498db"  # Blue

# Debug settings
DEBUG_MODE = False
```

To make these configurable via environment:

```python
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = int(os.getenv("API_TIMEOUT", "300"))
DEBUG_MODE = os.getenv("DEBUG", "0") == "1"
```

**Set before running:**
```bash
export API_URL="https://ballons-translator-api.onrender.com"
export API_TIMEOUT="600"
export DEBUG="1"
python launch_desktop.py
```

---

## Part 3: Configuration Files

### Suggested Config Structure

Create `config/api_config.json`:

```json
{
  "development": {
    "api_url": "http://localhost:8000",
    "timeout": 300,
    "debug": true,
    "cors_origins": ["http://localhost:3000"]
  },
  "staging": {
    "api_url": "https://staging-api.ballons.com",
    "timeout": 300,
    "debug": true,
    "cors_origins": ["https://staging.ballons.com"]
  },
  "production": {
    "api_url": "https://ballons-translator-api.onrender.com",
    "timeout": 300,
    "debug": false,
    "cors_origins": ["https://ballons.com"]
  }
}
```

**Load config:**
```python
import json
import os

ENV = os.getenv("ENVIRONMENT", "development")

with open("config/api_config.json") as f:
    config = json.load(f)[ENV]

API_URL = config["api_url"]
TIMEOUT = config["timeout"]
DEBUG = config["debug"]
```

---

## Part 4: Model Configuration

### Available Models in `api/pipeline.py`

#### Text Detectors
```python
"craft"                    # Better quality
"craft_fast"              # Faster inference
"yolov3"                  # Alternative
"yolov5"                  # Alternative
"paddleocr-detection"     # Paddle alternative
```

#### OCR Engines
```python
"easyocr"                 # Recommended
"paddleocr"               # Good for CJK
"tesseract"               # Standard
"keras_ocr"               # Alternative
```

#### Translators (20+ backends)
```python
"chatgpt"                 # Requires API key
"google"                  # Free, quota-limited
"deepl"                   # High quality, paid
"baidu"                   # Requires API key
"trans_qq"                # Free
"trans_tencent"           # Requires config
"trans_alibaba"           # Requires config
"trans_volcengine"        # Requires config
"trans_microsoft"         # Requires API key
"trans_bing"              # Free with limits
"trans_yandex"            # Limited free tier
"trans_papago"            # Free, CJK optimized
"trans_iciba"             # Limited
"trans_itranslate"        # Some features require API
"trans_mymemory"          # Free but limited
"trans_reverso"           # Free
"nllb"                    # Offline, slower
"trans_baidu_field"       # Domain-specific
"trans_caiyun"            # Chinese focused
"trans_lingo24"           # Limited
"trans_modernmt"          # Requires API
"trans_lingvanex"         # Limited free
```

#### Image Inpainters
```python
"lama"                    # Recommended (fast)
"propainter"              # High quality but slow
"aot"                     # Alternative
"fcf"                     # Fast
```

### Configure Default Models

Edit `api/pipeline.py`:

```python
DEFAULT_MODELS = {
    "detector": "craft",        # Text detection
    "ocr": "easyocr",          # Character recognition
    "translator": "google",     # Translation backend
    "inpainter": "lama"        # Inpainting method
}
```

### Configure Translator API Keys

For translators requiring authentication:

```bash
# Environment variables
export GOOGLE_TRANSLATE_KEY="..."
export DEEPL_AUTH_KEY="..."
export CHATGPT_API_KEY="..."
export BAIDU_APPID="..."
export BAIDU_SECRET="..."
export MICROSOFT_API_KEY="..."
export TENCENT_SECRET_ID="..."
export TENCENT_SECRET_KEY="..."
```

Or in `config/secrets.py`:

```python
# config/secrets.py
GOOGLE_TRANSLATE_KEY = "..."
DEEPL_AUTH_KEY = "..."
CHATGPT_API_KEY = "..."
BAIDU_APPID = "..."
BAIDU_SECRET = "..."
MICROSOFT_API_KEY = "..."

# Usage in code
from config.secrets import DEEPL_AUTH_KEY
os.environ["DEEPL_AUTH_KEY"] = DEEPL_AUTH_KEY
```

---

## Part 5: Performance Tuning

### Memory Configuration

**In `api/server.py`:**

```python
# Limit cached models (free tier: max 2-3 models)
MAX_CACHED_MODELS = 2

# Pre-load models on startup
PRELOAD_MODELS = False  # Set to True if you want models ready

# Model unload timeout (15 min = 900s)
MODEL_IDLE_TIMEOUT = 900
```

### Batch Processing

**For processing multiple images:**

```python
# Edit api/server.py to add batch endpoint
@app.post("/pipeline/batch")
async def batch_pipeline(request: BatchPipelineRequest):
    """Process multiple images serially"""
    results = []
    for image in request.images:
        result = await full_translation_pipeline(
            image=image.image,
            detector=request.detector,
            ocr=request.ocr,
            translator=request.translator,
            inpainter=request.inpainter
        )
        results.append(result)
    return results
```

### Timeout Configuration

**In `launch_desktop.py`:**

```python
# Increase for large images / slow GPU
TIMEOUT = 600  # 10 minutes

# For local dev (fast)
TIMEOUT = 300  # 5 minutes

# For Render free tier
TIMEOUT = 900  # 15 minutes (may need restart)
```

---

## Part 6: Logging Configuration

### Server-side Logging

**In `api/server.py`:**

```python
import logging
from logging.handlers import RotatingFileHandler

# Setup file logging
handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=10485760,  # 10MB
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
```

### Client-side Logging

**In `launch_desktop.py`:**

```python
import logging

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/desktop.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Connecting to API: {API_URL}")
```

---

## Part 7: CORS Configuration

### For Development

Allow all origins (current default):

```python
# api/server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### For Production

Restrict to specific domains:

```python
import os

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    '["https://ballons.com", "https://app.ballons.com"]'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

**Or use environment:**

```bash
export CORS_ORIGINS='["https://ballons.com"]'
uvicorn api.server:app
```

---

## Part 8: Database Configuration

### Optional: Store Results

If you want to persist translation results:

```python
# config/database.py
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./translations.db"  # Local SQLite
)

engine = create_engine(DATABASE_URL)

# PostgreSQL example (Render)
# DATABASE_URL = "postgresql://user:pass@host/dbname"

# Usage in api/server.py
from config.database import engine
from sqlalchemy.orm import Session
```

---

## Part 9: Security Configuration

### API Keys & Secrets

**Never commit secrets:**

```bash
# .gitignore
config/secrets.py
.env
.env.local
logs/
```

**Use environment variables:**

```bash
# .env (gitignore'd)
GOOGLE_TRANSLATE_KEY=sk-...
DEEPL_AUTH_KEY=...
CHATGPT_API_KEY=sk-...
```

**Load in code:**

```python
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_TRANSLATE_KEY = os.getenv("GOOGLE_TRANSLATE_KEY")
```

### Rate Limiting

**Add to `api/server.py`:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/pipeline/full")
@limiter.limit("5/minute")  # 5 requests per minute
async def pipeline_full(request: Request):
    # ...
```

### Authentication

For protected APIs:

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/pipeline/full")
async def pipeline_full(
    request: PipelineRequest,
    credentials: HTTPAuthCredentials = Depends(security)
):
    token = credentials.credentials
    # Validate token
    # ...
```

---

## Part 10: Configuration Summary

### Quick Setup Checklist

**Development:**
```bash
export API_URL="http://localhost:8000"
export DEBUG="1"
export API_TIMEOUT="300"
uvicorn api.server:app --reload
```

**Staging:**
```bash
export API_URL="https://staging-api.ballons.com"
export DEBUG="1"
export API_TIMEOUT="300"
uvicorn api.server:app
```

**Production (Render):**
```yaml
# render.yaml handles this automatically
# Just ensure environment variables are set
environment:
  - key: PYTHONUNBUFFERED
    value: "1"
  - key: PYTHONDONTWRITEBYTECODE
    value: "1"
```

---

## File Reference

| File | Purpose | Editable |
|------|---------|----------|
| `launch_desktop.py` | Desktop app settings | ✓ API_URL, TIMEOUT |
| `api/server.py` | API configuration | ✓ CORS, models, logging |
| `api/pipeline.py` | Model selection | ✓ DEFAULT_MODELS |
| `config/secrets.py` | API keys (gitignore'd) | ✓ API credentials |
| `render.yaml` | Render deployment | ✓ Build/start commands |
| `.env` | Local environment | ✓ Local secrets (gitignore'd) |

---

**Version:** 1.0.0  
**Last Updated:** March 2026
