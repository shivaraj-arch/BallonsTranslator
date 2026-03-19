# BallonsTranslator API System

## 📋 Quick Start

### What Changed?

The BallonsTranslator application has been refactored into a **client-server architecture**:

- **Backend:** FastAPI REST server (`api/server.py`) running ML/AI models
- **Frontend:** PyQt6 desktop app (`launch_desktop.py`) as lightweight client
- **Original:** Monolithic app (`launch.py`) remains **completely untouched**

### Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│        Desktop Application (launch_desktop.py)  │
│      Image Upload → Pipeline Configuration      │
└────────────────────┬────────────────────────────┘
                     │ HTTP(S)
                     ↓
┌─────────────────────────────────────────────────┐
│    FastAPI Server (api/server.py)               │
│    /detect, /ocr, /translate, /inpaint          │
└────────────┬──────────────────────┬──────────────┘
             │                      │
             ↓                      ↓
    ┌─────────────────┐   ┌─────────────────────┐
    │ ML Pipeline     │   │ Inference Engine    │
    │ (api/pipeline.py)   │ (PyTorch/CV models) │
    └─────────────────┘   └─────────────────────┘
```

---

## 🚀 Getting Started

### Option 1: Local Development (Recommended for Testing)

```bash
# Terminal 1: Start API server
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Run desktop app
python launch_desktop.py
```

**Features:**
- Fast iteration and debugging
- Images never leave your machine
- Full model control
- Best for development

### Option 2: Cloud Deployment (Render.com)

```bash
# Push to GitHub
git push origin main

# Render auto-deploys and provides public URL:
# https://ballons-translator-api.onrender.com
```

**Features:**
- Access from anywhere
- Shared infrastructure
- Persistent logs
- Production-ready

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [**DEPLOYMENT.md**](DEPLOYMENT.md) | Setup guide for local & cloud |
| [**TESTING.md**](TESTING.md) | Testing all endpoints locally |
| [**CONFIGURATION.md**](CONFIGURATION.md) | Configure API, models, keys |
| [**API_USAGE.md**](API_USAGE.md) | API endpoint reference |
| [**ARCHITECTURE_ANALYSIS.md**](ARCHITECTURE_ANALYSIS.md) | Design rationale & separation analysis |

---

## 🔧 Configuration

### API URL (in `launch_desktop.py`)

```python
# Local development
API_URL = "http://localhost:8000"

# Cloud deployment
API_URL = "https://ballons-translator-api.onrender.com"
```

### Environment Variables

```bash
# API server
export DEBUG=1
export API_TIMEOUT=300
export MODEL_CACHE_DIR="/path/to/cache"

# Desktop app
export API_URL="http://localhost:8000"
export PYTHONUNBUFFERED=1
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete settings.

---

## 📦 Files Overview

### New/Modified Files

```
api/
├── __init__.py              [NEW] Package initialization
├── server.py                [ENHANCED] FastAPI server with 8 endpoints
├── pipeline.py              [NEW] ML inference wrapper
└── requirements.txt         [NEW] API dependencies

launch_desktop.py            [ENHANCED] PyQt6 client application

DEPLOYMENT.md                [NEW] Deployment & setup guide
TESTING.md                   [NEW] Testing procedures & examples
CONFIGURATION.md             [NEW] Configuration reference
API_USAGE.md                 [NEW] API endpoint documentation
ARCHITECTURE_ANALYSIS.md     [NEW] Design analysis

Procfile                     [NEW] Render deployment config
render.yaml                  [NEW] Comprehensive Render setup
```

### Untouched Files

```
launch.py                    [UNCHANGED] Original monolithic app
requirements.txt             [UNCHANGED] Main dependencies
modules/                     [UNCHANGED] All ML/AI models
utils/                       [UNCHANGED] Utility functions
ui/                          [UNCHANGED] Qt UI components (except launch_desktop.py)
```

---

## 🌐 API Endpoints

All endpoints return JSON and accept image data as base64-encoded strings.

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status |
| `/models` | GET | List available models |
| `/detect` | POST | Text detection |
| `/ocr` | POST | Optical character recognition |
| `/translate` | POST | Machine translation |
| `/inpaint` | POST | Image inpainting |
| `/pipeline/full` | POST | Complete translation pipeline |

**Example:**
```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"BallonsTranslator API","version":"1.0.0"}
```

See [API_USAGE.md](API_USAGE.md) for complete endpoint reference.

---

## 🎯 Use Cases

### Use Case 1: Development & Testing
- Run local API server
- Test models on sample images
- Debug and iterate quickly
- **Best for:** Developers, ML engineers

### Use Case 2: Desktop Application
- Single-user manga translation
- Local processing (privacy)
- Full model control
- **Best for:** Individual users

### Use Case 3: Custom Tools
- Build client applications in any language
- Call REST API endpoints
- Integrate with other services
- **Best for:** Integrators, developers

### Use Case 4: Cloud Service
- Deploy on Render/AWS/GCP
- Multi-user access
- Scalable infrastructure
- **Best for:** Services, teams, public deployments

---

## 📊 Performance

### Processing Times (Approximate)

| Component | CPU | GPU |
|-----------|-----|-----|
| Text Detection | 2-4s | 0.5-1s |
| OCR | 2-5s | 1-2s |
| Translation | 0.5-2s | 0.5-1s |
| Inpainting | 3-8s | 1-2s |
| **Full Pipeline** | **8-20s** | **3-6s** |

*Render free tier uses CPU. Upgrade for GPU acceleration.*

---

## 🔐 Security

### API Keys

For services requiring authentication:

```bash
export GOOGLE_TRANSLATE_KEY="..."
export DEEPL_AUTH_KEY="..."
export CHATGPT_API_KEY="..."
```

Store in `.env` (not committed to git):
```bash
# .gitignore
.env
config/secrets.py
```

See [CONFIGURATION.md](CONFIGURATION.md#security-configuration) for details.

### CORS

**Development:** Allows all origins
**Production:** Restrict to known domains (see CONFIGURATION.md)

---

## 🛠️ Troubleshooting

### API Won't Start
```bash
# Check imports
python -c "from api.server import app"

# Check port is available
lsof -i :8000
```

### Desktop App Can't Connect
```bash
# Verify API is running
curl http://localhost:8000/health

# Check API_URL in launch_desktop.py
grep "API_URL" launch_desktop.py

# Check network connectivity
ping the-api-server.com
```

### Models Not Loading
- CPU-only inference is slow (5-20 seconds per operation)
- Free Render tier may spin down, causing delays
- Upgrade to paid plan for faster loading
- Check logs: `api/logs/api.log`

### Out of Memory
- Render free tier: 512MB total
- Load one model at a time
- Upgrade for larger instance size
- See [CONFIGURATION.md](CONFIGURATION.md#memory-configuration)

See [TESTING.md](TESTING.md#part-7-debugging-tips) for advanced debugging.

---

## 📋 Deployment Steps

### 1. Prepare Repository
```bash
git add .
git commit -m "API and desktop app integration"
git branch -M main
git push -u origin main
```

### 2. Deploy to Render
- Go to https://dashboard.render.com
- Connect GitHub repository
- Select BallonsTranslator
- Render auto-detects `Procfile` and deploys

### 3. Test Public API
```bash
curl https://ballons-translator-api.onrender.com/health
```

### 4. Update Desktop App
Edit `launch_desktop.py`:
```python
API_URL = "https://ballons-translator-api.onrender.com"
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed steps.

---

## 🔄 Workflow Examples

### Example 1: Local Testing
```bash
# Terminal 1
uvicorn api.server:app --reload

# Terminal 2
python launch_desktop.py

# Upload image → Run pipeline → View results
```

### Example 2: Building Custom Client
```python
import httpx
import base64

client = httpx.Client()

# Load image
with open("manga.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

# Translate
response = client.post(
    "http://localhost:8000/pipeline/full",
    json={
        "image": img_b64,
        "detector": "craft",
        "translator": "google",
        "source_lang": "ja",
        "target_lang": "en"
    },
    timeout=300
)

result = response.json()
print(f"Done in {result['total_processing_time_ms']}ms")
```

### Example 3: Batch Processing
```bash
# Process multiple images
for img in *.jpg; do
  curl -X POST http://localhost:8000/pipeline/full \
    -F "image=@$img" \
    -F "translator=google"
done
```

---

## 📚 Learning Resources

### For Backend Development
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [uvicorn Server](https://www.uvicorn.org/)

### For Frontend Development  
- [PyQt6 Documentation](https://doc.qt.io/qt-6/)
- [httpx Client](https://www.python-httpx.org/)
- [Qt Signals & Slots](https://doc.qt.io/qt-6/signalsandslots.html)

### For Deployment
- [Render Documentation](https://render.com/docs)
- [Docker Best Practices](https://docs.docker.com/)
- [GitHub Actions CI/CD](https://github.com/features/actions)

---

## 🤝 Contributing

### Adding a New Translator
1. Add to `api/pipeline.py` `load_translator()` method
2. Update `/models` endpoint to list it
3. Test via API
4. Update [CONFIGURATION.md](CONFIGURATION.md#available-models)

### Adding a New Detector
1. Add to `api/pipeline.py` `load_detector()` method
2. Test detection endpoint
3. Update documentation

### Bug Reports
- Check [TESTING.md](TESTING.md) for local reproduction steps
- Review [TROUBLESHOOTING.md](DEPLOYMENT.md#troubleshooting--maintenance) section
- Include logs and error messages

---

## 📝 Version History

### v1.0.0 (Current)
- ✅ API server with 8 endpoints
- ✅ PyQt6 desktop client
- ✅ ML pipeline abstraction
- ✅ Render deployment ready
- ✅ Full documentation

### Planned (Future)
- [ ] GPU support on Render
- [ ] Result caching & database
- [ ] Batch processing API
- [ ] Authentication & rate limiting
- [ ] Mobile app client

---

## 📞 Support

### Quick Links
- **API Docs:** http://localhost:8000/docs (local) or deployed URL
- **Deployment Help:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Testing Guide:** [TESTING.md](TESTING.md)
- **Configuration:** [CONFIGURATION.md](CONFIGURATION.md)
- **API Reference:** [API_USAGE.md](API_USAGE.md)

### Common Issues
1. **API won't start** → Check imports, see TESTING.md
2. **Can't connect** → Verify API_URL, check network
3. **Too slow** → Expected on CPU, upgrade for GPU
4. **Models missing** → First download takes time, be patient

---

## 📄 License

Same as BallonsTranslator: [See LICENSE file](LICENSE)

---

## 🎉 What's Next?

✅ System is ready to use!

**Next steps:**
1. Follow [DEPLOYMENT.md](DEPLOYMENT.md) to set up locally
2. Run [TESTING.md](TESTING.md) test cases
3. Deploy to Render when ready
4. Update desktop app API_URL to production
5. Start translating manga!

---

**Last Updated:** March 2026  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
