# BallonsTranslator - Architecture Analysis for Frontend/Backend Separation

## Executive Summary
**YES, it is possible to separate frontend and backend.** The current architecture is already semi-modular with a `ModuleManager` that can be extracted into an API backend. The codebase has good separation of concerns between UI (PyQt6) and ML/AI inference logic.

---

## Current Architecture Flow

### Entry Point: `launch.py` (Lines 1-350)
**Role:** Environment setup and engine initialization
- Sets up Python dependencies (torch, models, translators)
- Loads PyQt API (`pyqt6`, `pyside6`, `pyqt5`)
- Initializes configuration and logging
- Spawns MainWindow or runs headless mode
- **Already supports headless mode** via `--headless` flag (Line 42)

### Frontend: `launch_desktop.py`
**Current State:** Basic template skeleton
- Already designed to call Render API (`API_URL = "https://ballons-translator-api.onrender.com"`)
- Has `TranslateWorker` thread for non-blocking API calls
- Only needs enhancement to integrate with full pipeline

### Backend: `api/server.py`
**Current State:** FastAPI stub with placeholder endpoints
- `/translate` endpoint (POST) - needs implementation
- `/health` endpoint (GET) - ready
- CORS enabled
- Ready for enhancement

---

## Key ML/AI Components to Extract

### 1. **Text Detection Pipeline**
**Lines:** `ui/module_manager.py` → `TextDetectThread`

```
MainWindow.setupConfig() [line 340]
├── ModuleManager() instantiation
├── module_manager.textdetect_thread
├── module_manager.setTextDetector()
└── modules/textdetector/*
    └── Detects text regions/speech bubbles
```

**What to Extract:**
- `TextDetectThread._set_module()` - loads detector model
- `modules/textdetector/` - all detectors
- Configuration parameters for each detector

---

### 2. **OCR Pipeline**
**Lines:** `ui/module_manager.py` → `OCRThread`

```
MainWindow.setupConfig() [line 342]
├── module_manager.ocr_thread
├── module_manager.setOCR()
└── modules/ocr/*
    └── Extracts text from detected regions
```

**What to Extract:**
- `OCRThread._set_module()` - loads OCR model
- `modules/ocr/` - all OCR engines
- Text extraction logic

---

### 3. **Inpainting Pipeline**
**Lines:** `ui/module_manager.py` → `InpaintThread`

```
MainWindow.setupConfig() [line 375]
├── module_manager.inpaint_thread
├── module_manager.setInpainter()
└── modules/inpaint/*
    └── Removes original text from images
```

**What to Extract:**
- `InpaintThread._inpaint()` - performs inpainting
- `modules/inpaint/` - all inpainting models
- Image processing logic

---

### 4. **Translation Pipeline**
**Lines:** `ui/module_manager.py` → `TranslateThread`

```
MainWindow.setupConfig() [line 344]
├── module_manager.translate_thread
├── module_manager.setTranslator()
└── modules/translators/*
    ├── ChatGPT
    ├── Google Translate
    ├── DeepL
    ├── Baidu
    └── Others (20+ translators)
```

**What to Extract:**
- `TranslateThread` class
- All translator implementations in `modules/translators/`
- Language pair configuration

---

## Heavy ML/AI Calls in MainWindow

### Entry Points for Translation/Detection:

**1. User clicks "Run" button**
- `on_transpagebtn_pressed()` [Line 1227]
- `run_imgtrans()` [Line 1788]
- `on_run_imgtrans()` [Line 1825]

**2. User runs single text block translation**
- `on_transpagebtn_pressed()` [Line 1227]
- `translateBlkitemList()` [Line 1240]
- `module_manager.runBlktransPipeline()` ← **API CALL NEEDED HERE**

**3. Page translation finished**
- `on_pagtrans_finished()` [Line 1698]
- `finishTranslatePage()` [Line 1267]

---

## Critical Methods to Migrate to API

### Pipeline Execution Methods

| Method | Current Location | Type | What It Does |
|--------|-----------------|------|-------------|
| `runBlktransPipeline()` | ModuleManager | Pipeline | Runs text detection, OCR, translation on text blocks |
| `_set_module()` | ModuleThread | Loader | Loads ML models (detector, OCR, translator, inpainter) |
| `_inpaint()` | InpaintThread | Inference | Runs image inpainting |
| `translate()` | Various Translators | Inference | Translates text using selected backend |
| `detect()` | TextDetector | Inference | Detects text regions |
| `recognize()` | OCR | Inference | Extracts text from image regions |

---

## Separation Strategy - Three-Layer Architecture

### Layer 1: Frontend (Qt Desktop App)
**File:** `launch_desktop.py` with PyQt6

**Responsibilities:**
- Image/project loading
- UI rendering
- User interactions (editing, formatting)
- Progress tracking
- Result display

**Qt Components (Keep Local):**
- Canvas rendering
- Text editing widgets
- Drawing/inpainting brush UI
- File dialogs
- Configuration panels

**API Calls to Backend:**
1. `/api/detect` - send image + config, get text regions
2. `/api/ocr` - send image + regions, get extracted text
3. `/api/inpaint` - send image + mask, get inpainted image
4. `/api/translate` - send text + lang pair, get translation

---

### Layer 2: Backend API (FastAPI)
**Files:** `api/server.py` + new `api/pipeline.py`

**Responsibilities:**
- Model management (loading/caching)
- ML inference execution
- Configuration management
- Result post-processing

**Endpoints to Create:**
```python
POST /api/detect           # Text detection
POST /api/ocr              # Optical character recognition
POST /api/inpaint          # Image inpainting
POST /api/translate        # Machine translation
POST /api/models/load      # Load specific model
POST /api/models/list      # List available models
GET  /api/health           # Health check
```

---

### Layer 3: Shared Logic
**Keep in `modules/`**:
- Model definitions (can be imported by both frontend & backend)
- Configuration loading
- Utility functions
- Text processing helpers

---

## Implementation Roadmap (Phase-by-Phase)

### Phase 1: Extract ML Components (Minimal Changes)
1. Create `api/backend.py` - copy `ModuleManager` and threaded modules
2. Create `api/routes/` - define endpoints for each module
3. Keep current PyQt app loading behavior
4. **Result:** Headless server works, desktop app unchanged

### Phase 2: Connect Desktop App to API
1. Modify `launch_desktop.py` to make HTTP calls instead of local ML
2. Create `api/client.py` - RequestsSession wrapper for API communication
3. Handle async request/response in Qt threads
4. **Result:** Desktop app sends all ML tasks to API

### Phase 3: Optimize Deployment
1. Run separate backend process
2. Desktop app configurable to use local `http://localhost:8000` or remote Render URL
3. Model caching in backend
4. **Result:** Scalable architecture

---

## Which Code Lines Need Refactoring

### Frontend Refactoring

| File | Lines | Action |
|------|-------|--------|
| `ui/mainwindow.py` | 340-376 | ModuleManager init → API client init |
| `ui/mainwindow.py` | 1227-1267 | Direct ML calls → API HTTP calls |
| `ui/mainwindow.py` | 1470-1550 | `on_run_imgtrans()` → Queue to API |
| `ui/mainwindow.py` | 1698-1750 | Post-processing stays local |
| `launch_desktop.py` | All | Enhance with HTTP client library (requests/httpx) |

### Backend Creation

| New File | Purpose | Source Code |
|----------|---------|-------------|
| `api/backend.py` | Core ML pipeline | Copy from `ui/module_manager.py` |
| `api/routes/detect.py` | Detection endpoint | Adapt `TextDetectThread` |
| `api/routes/ocr.py` | OCR endpoint | Adapt `OCRThread` |
| `api/routes/translate.py` | Translation endpoint | Adapt `TranslateThread` |
| `api/routes/inpaint.py` | Inpainting endpoint | Adapt `InpaintThread` |

---

## Feasibility Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| **UI/Logic Separation** | ✅ Excellent | ModuleManager already abstracts ML |
| **Model Compatibility** | ✅ Full | All models in `modules/` can run remotely |
| **Configuration** | ✅ Good | `utils/config.py` can be shared |
| **Threading** | ⚠️ Medium | Qt threads → Flask/FastAPI async |
| **File I/O** | ⚠️ Medium | Desktop reads files, API processes data |
| **State Management** | ⚠️ Medium | Project state management needs careful handling |

---

## Challenges & Solutions

### Challenge 1: Large Image Processing
**Problem:** Sending large manga images over HTTP can be slow
**Solution:** 
- Compress before sending
- Use base64 or binary protocols
- Stream processing for large batches
- Keep inpainted image generation client-side if possible

### Challenge 2: Model Loading Time
**Problem:** First API call loads models (5-30 seconds)
**Solution:**
- Pre-load models on API startup
- Implement model warming in `on_startup` event
- Cache loaded models per session

### Challenge 3: GPU Memory on Render.com
**Problem:** Limited GPU memory on free tier
**Solution:**
- Move inexpensive models to CPU
- Load/unload models on demand
- Implement queue system for concurrent requests

### Challenge 4: Desktop App Works Offline
**Problem:** Current app works without internet
**Solution:**
- Add fallback to local ML if API unavailable
- Configuration for local vs. remote mode
- Graceful degradation

---

## Proof of Concept Tasks

To verify this is possible, implement in this order:

1. **Task 1**: Create `/api/health` endpoint ✓ (Already done)
2. **Task 2**: Extract `ModuleManager` to `api/backend.py`
3. **Task 3**: Create `/api/translate` endpoint (text only, no images)
4. **Task 4**: Modify `launch_desktop.py` to call `/api/translate`
5. **Task 5**: Test end-to-end translation via API

---

## Conclusion

**It IS possible and recommended.** The codebase is well-structured with good separation. The main work is:
1. Extracting `ModuleManager` logic to FastAPI endpoints
2. Adding HTTP client to PyQt frontend
3. Handling async operations in Qt

The existing `--headless` mode and modular architecture provide excellent starting points for this refactoring.
