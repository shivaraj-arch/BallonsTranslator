from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

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

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BallonsTranslator API"
    }

@app.post("/translate")
async def translate(image: UploadFile = File(...), target_lang: str = "English"):
    """
    Placeholder translation endpoint
    """
    try:
        image_data = await image.read()
        
        # TODO: Add BallonsTranslator logic here
        # For now, return placeholder
        
        return JSONResponse({
            "status": "success",
            "result_image": "",  # base64 encoded image
            "extracted_text": "Placeholder text",
            "translated_text": "Placeholder translation"
        })
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/")
def root():
    """Root endpoint"""
    return {"service": "BallonsTranslator API", "version": "1.0.0"}
