"""
BallonsTranslator API Server
REST API for manga/comic translation pipeline
Root URL: https://ballons-translator-api.onrender.com/
"""
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
import numpy as np

from pipeline import (
    get_pipeline, 
    get_available_models, 
    TranslationPipeline
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BallonsTranslator API",
    description="ML-powered manga/comic translation API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Pydantic Models
# ============================================

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    models_available: bool

class LoadModelRequest(BaseModel):
    detector: Optional[str] = None
    ocr: Optional[str] = None
    translator: Optional[str] = None
    inpainter: Optional[str] = None

class DetectRequest(BaseModel):
    image_base64: str

class DetectResponse(BaseModel):
    status: str
    regions: List = []
    count: int = 0
    message: Optional[str] = None

class OCRRequest(BaseModel):
    image_base64: str
    regions: Optional[List] = None

class OCRResponse(BaseModel):
    status: str
    texts: List[str] = []
    count: int = 0
    message: Optional[str] = None

class TranslateRequest(BaseModel):
    texts: List[str]
    source_lang: Optional[str] = "auto"
    target_lang: str = "English"

class TranslateResponse(BaseModel):
    status: str
    translations: List[str] = []
    count: int = 0
    message: Optional[str] = None

class InpaintRequest(BaseModel):
    image_base64: str
    mask_base64: str

class InpaintResponse(BaseModel):
    status: str
    image_base64: Optional[str] = None
    message: Optional[str] = None

class FullPipelineRequest(BaseModel):
    image_base64: str
    source_lang: Optional[str] = "auto"
    target_lang: str = "English"
    detector: Optional[str] = None
    ocr: Optional[str] = None
    translator: Optional[str] = None
    inpainter: Optional[str] = None
    enable_detection: bool = True
    enable_ocr: bool = True
    enable_translation: bool = True
    enable_inpainting: bool = False

class FullPipelineResponse(BaseModel):
    status: str
    detected_regions: List = []
    extracted_texts: List[str] = []
    translated_texts: List[str] = []
    inpainted_image_base64: Optional[str] = None
    message: Optional[str] = None

# ============================================
# Root & Health Check Endpoints
# ============================================

@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "service": "BallonsTranslator API",
        "version": "1.0.0",
        "description": "ML-powered manga/comic translation pipeline",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "models": {
                "list": "/models",
                "load": "/models/load"
            },
            "pipeline": {
                "detect": "/detect",
                "ocr": "/ocr",
                "translate": "/translate",
                "inpaint": "/inpaint",
                "full": "/pipeline/full"
            }
        }
    }

@app.get("/health", response_model=HealthResponse)
def health():
    """Health check endpoint"""
    pipeline = get_pipeline()
    return HealthResponse(
        status="healthy",
        service="BallonsTranslator API",
        version="1.0.0",
        models_available=pipeline.initialized
    )

# ============================================
# Model Management Endpoints
# ============================================

@app.get("/models")
def list_models():
    """List available ML models"""
    models = get_available_models()
    return {
        "status": "success",
        "models": models,
        "total": sum(len(v) for v in models.values() if isinstance(v, list))
    }

@app.post("/models/load")
def load_models(request: LoadModelRequest):
    """Load specific ML models"""
    pipeline = get_pipeline()
    results = {}
    
    if request.detector:
        results['detector'] = pipeline.load_detector(request.detector)
    
    if request.ocr:
        results['ocr'] = pipeline.load_ocr(request.ocr)
    
    if request.translator:
        results['translator'] = pipeline.load_translator(request.translator)
    
    if request.inpainter:
        results['inpainter'] = pipeline.load_inpainter(request.inpainter)
    
    return {
        "status": "success",
        "results": results
    }

# ============================================
# Text Detection Endpoint
# ============================================

@app.post("/detect", response_model=DetectResponse)
async def detect_text(request: DetectRequest):
    """
    Detect text regions in image
    
    Expected input: image_base64 (base64 encoded image)
    Returns: detected regions
    """
    try:
        pipeline = get_pipeline()
        
        # Convert base64 to image
        image_array = TranslationPipeline.base64_to_image(request.image_base64)
        if image_array is None:
            raise ValueError("Invalid image data")
        
        # Run detection
        result = pipeline.detect_text(image_array)
        
        return DetectResponse(
            status=result.get("status"),
            regions=result.get("regions", []),
            count=result.get("count", 0),
            message=result.get("message")
        )
    
    except Exception as e:
        logger.error(f"Detection error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# OCR Endpoint
# ============================================

@app.post("/ocr", response_model=OCRResponse)
async def recognize_text(request: OCRRequest):
    """
    Recognize text from image (OCR)
    
    Expected input: 
      - image_base64: base64 encoded image
      - regions: (optional) list of text regions
    
    Returns: extracted text
    """
    try:
        pipeline = get_pipeline()
        
        # Convert base64 to image
        image_array = TranslationPipeline.base64_to_image(request.image_base64)
        if image_array is None:
            raise ValueError("Invalid image data")
        
        # Run OCR
        result = pipeline.recognize_text(image_array, request.regions)
        
        return OCRResponse(
            status=result.get("status"),
            texts=result.get("texts", []),
            count=result.get("count", 0),
            message=result.get("message")
        )
    
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Translation Endpoint
# ============================================

@app.post("/translate", response_model=TranslateResponse)
async def translate_texts(request: TranslateRequest):
    """
    Translate text
    
    Expected input:
      - texts: list of text strings to translate
      - source_lang: source language (default: "auto")
      - target_lang: target language
    
    Returns: translated text
    """
    try:
        pipeline = get_pipeline()
        
        # Run translation
        result = pipeline.translate_text(
            request.texts,
            request.source_lang,
            request.target_lang
        )
        
        return TranslateResponse(
            status=result.get("status"),
            translations=result.get("translations", []),
            count=result.get("count", 0),
            message=result.get("message")
        )
    
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Inpainting Endpoint
# ============================================

@app.post("/inpaint", response_model=InpaintResponse)
async def inpaint_image(request: InpaintRequest):
    """
    Remove text from image using inpainting
    
    Expected input:
      - image_base64: base64 encoded image
      - mask_base64: base64 encoded mask (white = inpaint, black = keep)
    
    Returns: inpainted image (base64)
    """
    try:
        pipeline = get_pipeline()
        
        # Convert base64 to images
        image_array = TranslationPipeline.base64_to_image(request.image_base64)
        mask_array = TranslationPipeline.base64_to_image(request.mask_base64)
        
        if image_array is None or mask_array is None:
            raise ValueError("Invalid image or mask data")
        
        # Run inpainting
        result = pipeline.inpaint_image(image_array, mask_array)
        
        if result.get("status") == "success" and result.get("image") is not None:
            inpainted_base64 = TranslationPipeline.image_to_base64(result["image"])
        else:
            inpainted_base64 = None
        
        return InpaintResponse(
            status=result.get("status"),
            image_base64=inpainted_base64,
            message=result.get("message")
        )
    
    except Exception as e:
        logger.error(f"Inpainting error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Full Pipeline Endpoints
# ============================================

@app.post("/pipeline/full", response_model=FullPipelineResponse)
async def full_translation_pipeline(request: FullPipelineRequest):
    """
    Complete translation pipeline: detect → OCR → translate → inpaint
    
    Expected input:
      - image_base64: base64 encoded image
      - source_lang: source language
      - target_lang: target language
      - enable_detection: run text detection
      - enable_ocr: run OCR
      - enable_translation: run translation
      - enable_inpainting: run inpainting
    
    Returns: all pipeline results
    """
    try:
        pipeline = get_pipeline()
        
        # Load models if specified
        if request.detector:
            pipeline.load_detector(request.detector)
        if request.ocr:
            pipeline.load_ocr(request.ocr)
        if request.translator:
            pipeline.load_translator(request.translator)
        if request.inpainter:
            pipeline.load_inpainter(request.inpainter)
        
        # Convert base64 to image
        image_array = TranslationPipeline.base64_to_image(request.image_base64)
        if image_array is None:
            raise ValueError("Invalid image data")
        
        detected_regions = []
        extracted_texts = []
        translated_texts = []
        inpainted_base64 = None
        
        # Step 1: Detection
        if request.enable_detection:
            detect_result = pipeline.detect_text(image_array)
            detected_regions = detect_result.get("regions", [])
            logger.info(f"Detection: {len(detected_regions)} regions found")
        
        # Step 2: OCR
        if request.enable_ocr:
            ocr_result = pipeline.recognize_text(
                image_array,
                detected_regions if request.enable_detection else None
            )
            extracted_texts = ocr_result.get("texts", [])
            logger.info(f"OCR: {len(extracted_texts)} texts extracted")
        
        # Step 3: Translation
        if request.enable_translation and extracted_texts:
            trans_result = pipeline.translate_text(
                extracted_texts,
                request.source_lang,
                request.target_lang
            )
            translated_texts = trans_result.get("translations", [])
            logger.info(f"Translation: {len(translated_texts)} texts translated")
        
        # Step 4: Inpainting
        if request.enable_inpainting:
            # Create a simple mask from detected regions
            if detected_regions:
                mask_array = np.zeros_like(image_array[:, :, 0], dtype=np.uint8)
                # Mark detected regions as white in mask
                for region in detected_regions:
                    # Assuming region is [x, y, w, h] or similar
                    try:
                        if isinstance(region, (list, tuple)) and len(region) >= 4:
                            x, y, w, h = region[:4]
                            mask_array[int(y):int(y+h), int(x):int(x+w)] = 255
                    except:
                        pass
                
                inpaint_result = pipeline.inpaint_image(image_array, mask_array)
                if inpaint_result.get("status") == "success":
                    inpainted_base64 = TranslationPipeline.image_to_base64(
                        inpaint_result["image"]
                    )
                    logger.info("Inpainting completed")
        
        return FullPipelineResponse(
            status="success",
            detected_regions=detected_regions,
            extracted_texts=extracted_texts,
            translated_texts=translated_texts,
            inpainted_image_base64=inpainted_base64,
            message="Pipeline completed successfully"
        )
    
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ============================================
# Legacy File Upload Endpoint (for backward compatibility)
# ============================================

@app.post("/translate")
async def translate_file(image: UploadFile = File(...), target_lang: str = "English"):
    """
    Legacy endpoint for image file upload and translation
    Kept for backward compatibility with existing clients
    """
    try:
        image_data = await image.read()
        
        # Convert file bytes to base64
        import base64
        image_base64 = base64.b64encode(image_data).decode()
        
        # Create request for full pipeline
        request = FullPipelineRequest(
            image_base64=image_base64,
            target_lang=target_lang,
            enable_detection=True,
            enable_ocr=True,
            enable_translation=True,
            enable_inpainting=False
        )
        
        # Run full pipeline
        result = await full_translation_pipeline(request)
        
        # Return in legacy format
        return JSONResponse({
            "status": result.status,
            "result_image": result.inpainted_image_base64 or "",
            "extracted_text": "\n".join(result.extracted_texts),
            "translated_text": "\n".join(result.translated_texts)
        })
    
    except Exception as e:
        logger.error(f"Legacy endpoint error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )
