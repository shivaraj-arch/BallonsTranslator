from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import base64
import io
import logging
from PIL import Image

# Import BallonsTranslator modules
from modules.ocr.ocr_base import OCRBase
from modules.textdetector.detector_base import TextDetectorBase
from modules.translators.trans_google import TransGoogle
from modules.inpaint.base import InpainterBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BallonsTranslator API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
text_detector = None
ocr = None
translator = None
inpainter = None

@app.on_event("startup")
async def startup():
    """Initialize models on startup"""
    global text_detector, ocr, translator, inpainter
    try:
        logger.info("Loading BallonsTranslator models...")
        
        # Initialize text detector
        text_detector = TextDetectorBase()
        logger.info("✓ Text detector loaded")
        
        # Initialize OCR
        ocr = OCRBase()
        logger.info("✓ OCR loaded")
        
        # Initialize translator (Google by default)
        translator = TransGoogle()
        logger.info("✓ Translator loaded")
        
        # Initialize inpainter
        inpainter = InpainterBase()
        logger.info("✓ Inpainter loaded")
        
        logger.info("✓ All models loaded successfully")
    except Exception as e:
        logger.error(f"Error loading models: {e}")

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BallonsTranslator API",
        "models_loaded": text_detector is not None
    }

@app.post("/translate")
async def translate(image: UploadFile = File(...), target_lang: str = "English"):
    """
    Translate manga/comic image
    
    Args:
        image: Image file (JPG, PNG, etc.)
        target_lang: Target language (default: English)
    
    Returns:
        JSON with result image (base64) and extracted text
    """
    try:
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            raise HTTPException(status_code=400, detail="Only image files allowed")
        
        # Read image
        logger.info(f"Processing image: {image.filename}")
        image_data = await image.read()
        
        # Convert to OpenCV format
        image_array = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        logger.info(f"Image shape: {img.shape}")
        
        # Detect text regions
        logger.info("Detecting text...")
        text_blocks = text_detector.detect(img)
        logger.info(f"Found {len(text_blocks)} text blocks")
        
        # Extract text with OCR
        logger.info("Running OCR...")
        for block in text_blocks:
            block.text = ocr.ocr(block.crop_image())
        
        extracted_text = "\n".join([block.text for block in text_blocks if block.text])
        logger.info(f"Extracted text: {extracted_text[:100]}...")
        
        # Translate
        logger.info(f"Translating to {target_lang}...")
        text_list = [block.text for block in text_blocks if block.text]
        translated_list = translator.translate(text_list, target_lang)
        
        # Update blocks with translation
        idx = 0
        for block in text_blocks:
            if block.text and idx < len(translated_list):
                block.text = translated_list[idx]
                idx += 1
        
        # Inpaint (remove original text)
        logger.info("Inpainting...")
        result_img = inpainter.inpaint(img, text_blocks)
        
        # Draw translated text
        logger.info("Drawing text...")
        for block in text_blocks:
            cv2.putText(result_img, block.text, block.xyxy[:2], 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Encode result image
        _, buffer = cv2.imencode('.png', result_img)
        result_base64 = base64.b64encode(buffer).decode('utf-8')
        
        logger.info("✓ Translation complete")
        
        return JSONResponse({
            "status": "success",
            "result_image": result_base64,
            "extracted_text": extracted_text,
            "translated_text": "\n".join(translated_list),
            "text_blocks_count": len(text_blocks)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during translation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "BallonsTranslator API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "translate": "/translate (POST)",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
