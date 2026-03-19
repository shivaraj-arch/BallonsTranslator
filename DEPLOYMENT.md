# BallonsTranslator API - Deployment & Setup Guide

## Overview

The BallonsTranslator API is now split into:
- **Backend API** (`api/server.py`) - REST API for ML/AI operations
- **Frontend Desktop App** (`launch_desktop.py`) - PyQt6 client that calls the API
- **Pipeline Engine** (`api/pipeline.py`) - Core inference logic

---

## Architecture

```
GitHub Repository
    ↓
Render.com Deployment
    ↓
REST API Server (https://ballons-translator-api.onrender.com)
    ↓
Desktop Client (launch_desktop.py) ← Makes HTTP calls
```

---

## Step 1: Local Setup (Development)

### Prerequisites
- Python 3.10+
- Git
- 8GB+ RAM (for ML models)

### Installation

1. **Clone and setup:**
```bash
git clone https://github.com/YOUR_USERNAME/BallonsTranslator.git
cd BallonsTranslator
```

2. **Install main dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install API dependencies:**
```bash
pip install -r api/requirements.txt
```

4. **Install desktop dependencies (if not already included):**
```bash
pip install PyQt6 httpx
```

### Run Locally

**Terminal 1 - Start API Server:**
```bash
cd /path/to/BallonsTranslator
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Run Desktop Client:**
```bash
cd /path/to/BallonsTranslator

# Edit launch_desktop.py to use local API:
# API_URL = "http://localhost:8000"

python launch_desktop.py
```

**Test the API:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

---

## Step 2: Prepare for Render Deployment

### GitHub Setup

1. **Initialize Git (if not already done):**
```bash
cd BallonsTranslator
git init
git add .
git commit -m "Initial commit: API and desktop app integration"
```

2. **Add to GitHub:**
```bash
# Create new repository at github.com
git remote add origin https://github.com/YOUR_USERNAME/BallonsTranslator.git
git branch -M main
git push -u origin main
```

### Project Structure

Ensure your repository has:
```
BallonsTranslator/
├── api/
│   ├── __init__.py          ✓ Created
│   ├── server.py            ✓ Enhanced
│   ├── pipeline.py          ✓ Created
│   └── requirements.txt      ✓ Created
├── modules/                 ✓ Existing (ML models)
├── utils/                   ✓ Existing (helpers)
├── launch.py                ✓ Main entry (UNCHANGED)
├── launch_desktop.py        ✓ Desktop client (ENHANCED)
├── requirements.txt         ⚠️ Main deps
├── Procfile                 ✓ Created
├── render.yaml              ✓ Created
├── API_USAGE.md            ✓ Created
└── DEPLOYMENT.md           (this file)
```

---

## Step 3: Deploy to Render

### Option A: Using GitHub Integration (Recommended)

1. **Go to Render Dashboard:**
   - Visit https://dashboard.render.com
   - Sign up/login with GitHub account

2. **Connect Repository:**
   - Click "New +" → "Web Service"
   - Select "Build and deploy from Git repository"
   - Connect your GitHub account
   - Select your BallonsTranslator repository

3. **Configure Service:**
   - **Name:** `ballons-translator-api`
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** (leave empty - Render auto-detects from Procfile)
   - **Start Command:** (Procfile will be used)
   - **Plan:** Free tier (or upgrade for GPU)

4. **Environment Variables:**
   Add these if needed:
   ```
   PYTHONUNBUFFERED=1
   PYTHONDONTWRITEBYTECODE=1
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment
   - Render shows status and logs

### Option B: Manual Render Deployment

1. **Install Render CLI:**
```bash
npm install -g render-cli
```

2. **Login:**
```bash
render login
```

3. **Deploy:**
```bash
render deploy --name ballons-translator-api
```

---

## Step 4: Verify Deployment

### Check API Status

```bash
# Health check endpoint
curl https://ballons-translator-api.onrender.com/health

# Should return:
# {"status":"healthy","service":"BallonsTranslator API","version":"1.0.0","models_available":true}
```

### View Admin Dashboard

- Visit Render Dashboard
- Find `ballons-translator-api` service
- View logs, metrics, and settings

### View Deployed API Docs

- Swagger UI: https://ballons-translator-api.onrender.com/docs
- ReDoc: https://ballons-translator-api.onrender.com/redoc

---

## Step 5: Use Desktop App with Deployed API

### Update Configuration

Edit `launch_desktop.py`:
```python
# Change from local to deployed API
API_URL = "https://ballons-translator-api.onrender.com"
```

### Run Desktop Client

```bash
python launch_desktop.py
```

The app will:
1. Connect to your Render API
2. Load available models
3. Send images for processing
4. Display results

---

## Monitoring & Maintenance

### View Logs

```bash
# On Render Dashboard
→ Service: ballons-translator-api
→ Logs tab
```

### Monitor Performance

- **CPU Usage:** View in Render dashboard
- **Response Times:** Check Swagger UI (timing headers)
- **Errors:** Check application logs

### Update Deployment

1. **Make changes locally**
2. **Commit to GitHub:**
```bash
git add .
git commit -m "Update: improved detection threshold"
git push origin main
```
3. **Render auto-deploys** (if auto-deploy enabled)

### Restart Service

```bash
# Via Render Dashboard
→ Service settings
→ Manual Deploy (or trigger from GitHub)
```

---

## Troubleshooting

### 1. API Deployment Failed
- Check Render logs: https://dashboard.render.com
- Verify `Procfile` exists and syntax is correct
- Ensure all imports work: `python -c "from api.server import app"`

### 2. Desktop App Can't Connect
- Verify API URL in `launch_desktop.py`
- Check network connectivity
- Try: `curl https://ballons-translator-api.onrender.com/health`

### 3. Models Not Loading
- Render free tier has 512MB RAM
- Models may take time to download on first use
- Upgrade to paid plan for faster loading

### 4. Timeout Errors
- Set longer timeout in client: `TIMEOUT = 600` (10 min)
- Render may be initializing models
- Wait for "spun down" service to restart

### 5. Port Issues
- Render automatically assigns port via `$PORT` environment variable
- Don't hardcode port in Procfile

---

## Performance Optimization

### For Free Tier (512MB RAM)
- GPU unavailable, use CPU models
- Load one model at a time
- Queue requests if concurrent users

### For Paid Plans
- Enable GPU (NVIDIA) - requires paid tier upgrade
- Pre-load all models on startup
- Increase instance size if needed
- GPU significantly speeds up all operations (3-6x faster)

<!-- GPU-specific configuration (requires paid plan):
  export CUDA_VISIBLE_DEVICES="0"
  export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
-->

### Model Caching
The API caches loaded models between requests. Models are unloaded after:
- Application restart
- Manual unload via API
- Service idle timeout (Render free tier = 15 min)

---

## Cost Estimation

### Render Free Tier
- **Cost:** $0/month
- **Limitations:** 
  - 0.5 CPU
  - 512MB RAM
  - Spins down after 15 min inactivity (cold starts)
  - No GPU

### Render Paid Tier (USD/month)
- **Standard:** $7/month (1 CPU, 512MB)
- **Pro:** $12/month (1 CPU, 1GB)
- **GPU:** +$0.50-5.00 depending on type

---

## API Endpoints (Quick Reference)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status |
| `/models` | GET | List available models |
| `/models/load` | POST | Load specific models |
| `/detect` | POST | Text detection |
| `/ocr` | POST | Text recognition |
| `/translate` | POST | Translation |
| `/inpaint` | POST | Image inpainting |
| `/pipeline/full` | POST | Complete pipeline |

---

## Security Notes

### CORS
- Currently allows all origins (demo)
- In production, restrict to your domains:
```python
allow_origins=["https://yourdomain.com"]
```

### API Rate Limiting
- Not implemented (add if needed)
- Consider for production: `slowapi` library

### Model Security
- Models downloaded from public sources
- Verify checksums if security-critical

---

## Next Steps

1. ✅ Local testing complete
2. ✅ Push to GitHub
3. ✅ Deploy to Render
4. ✅ Verify API running
5. ✅ Update desktop app with API URL
6. ✅ Test end-to-end translation

For issues: Check logs, verify connectivity, restart service.

---

## Support & Documentation

- **API Docs:** https://ballons-translator-api.onrender.com/docs
- **Usage Guide:** See `API_USAGE.md`
- **Architecture Analysis:** See `ARCHITECTURE_ANALYSIS.md`
- **Render Docs:** https://render.com/docs

---

**Version:** 1.0.0  
**Last Updated:** March 2026
