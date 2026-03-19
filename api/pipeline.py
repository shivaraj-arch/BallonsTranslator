"""
BallonsTranslator ML/AI Pipeline Backend
Handles text detection, OCR, inpainting, and translation
"""
import os
import sys
import base64
import io
import numpy as np
import cv2
from typing import List, Dict, Optional, Tuple
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modules import GET_VALID_TEXTDETECTORS, GET_VALID_INPAINTERS, GET_VALID_TRANSLATORS, GET_VALID_OCR
    from modules.base import BaseModule
    from utils.config import ProgramConfig, pcfg
    from utils.textblock import TextBlock
    from utils.logger import logger as app_logger
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import BallonsTranslator modules: {e}. Running in stub mode.")
    IMPORTS_AVAILABLE = False


class TranslationPipeline:
    """Main translation pipeline for processing images"""
    
    def __init__(self, config_path: str = None):
        """Initialize pipeline with configuration"""
        self.initialized = False
        self.detector = None
        self.ocr = None
        self.translator = None
        self.inpainter = None
        self.config = None
        
        if IMPORTS_AVAILABLE:
            try:
                if config_path and os.path.exists(config_path):
                    from utils import config as program_config
                    program_config.load_config(config_path)
                    self.config = program_config.pcfg
                self.initialized = True
                logger.info("Pipeline initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize pipeline: {e}")
    
    def load_detector(self, detector_name: str = "craft"):
        """Load text detection model"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import TEXTDETECTORS
            if detector_name in TEXTDETECTORS.module_dict:
                self.detector = TEXTDETECTORS.module_dict[detector_name]()
                self.detector.load_model()
                logger.info(f"Loaded detector: {detector_name}")
                return {"status": "success", "detector": detector_name}
            else:
                return {"status": "error", "message": f"Detector {detector_name} not found"}
        except Exception as e:
            logger.error(f"Failed to load detector: {e}")
            return {"status": "error", "message": str(e)}
    
    def load_ocr(self, ocr_name: str = "paddleocr"):
        """Load OCR model"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import OCR
            if ocr_name in OCR.module_dict:
                self.ocr = OCR.module_dict[ocr_name]()
                self.ocr.load_model()
                logger.info(f"Loaded OCR: {ocr_name}")
                return {"status": "success", "ocr": ocr_name}
            else:
                return {"status": "error", "message": f"OCR {ocr_name} not found"}
        except Exception as e:
            logger.error(f"Failed to load OCR: {e}")
            return {"status": "error", "message": str(e)}
    
    def load_translator(self, translator_name: str = "google"):
        """Load translation model/API"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import TRANSLATORS
            if translator_name in TRANSLATORS.module_dict:
                self.translator = TRANSLATORS.module_dict[translator_name]()
                logger.info(f"Loaded translator: {translator_name}")
                return {"status": "success", "translator": translator_name}
            else:
                return {"status": "error", "message": f"Translator {translator_name} not found"}
        except Exception as e:
            logger.error(f"Failed to load translator: {e}")
            return {"status": "error", "message": str(e)}
    
    def load_inpainter(self, inpainter_name: str = "lama"):
        """Load inpainting model"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import INPAINTERS
            if inpainter_name in INPAINTERS.module_dict:
                self.inpainter = INPAINTERS.module_dict[inpainter_name]()
                self.inpainter.load_model()
                logger.info(f"Loaded inpainter: {inpainter_name}")
                return {"status": "success", "inpainter": inpainter_name}
            else:
                return {"status": "error", "message": f"Inpainter {inpainter_name} not found"}
        except Exception as e:
            logger.error(f"Failed to load inpainter: {e}")
            return {"status": "error", "message": str(e)}
    
    def detect_text(self, image_array: np.ndarray) -> Dict:
        """Detect text regions in image"""
        if not IMPORTS_AVAILABLE or self.detector is None:
            return {
                "status": "stub",
                "message": "Text detection not available",
                "regions": []
            }
        
        try:
            # Run detection
            results = self.detector(image_array)
            logger.info(f"Detected {len(results) if results else 0} text regions")
            return {
                "status": "success",
                "regions": results if results else [],
                "count": len(results) if results else 0
            }
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def recognize_text(self, image_array: np.ndarray, regions: List = None) -> Dict:
        """Recognize text from image regions (OCR)"""
        if not IMPORTS_AVAILABLE or self.ocr is None:
            return {
                "status": "stub",
                "message": "OCR not available",
                "texts": []
            }
        
        try:
            texts = []
            if regions:
                for region in regions:
                    text = self.ocr(image_array, region)
                    texts.append(text)
            else:
                text = self.ocr(image_array)
                texts.append(text)
            
            logger.info(f"Recognized {len(texts)} text blocks")
            return {
                "status": "success",
                "texts": texts,
                "count": len(texts)
            }
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def translate_text(self, texts: List[str], source_lang: str = "auto", target_lang: str = "English") -> Dict:
        """Translate text"""
        if not IMPORTS_AVAILABLE or self.translator is None:
            # Return mock translations for stub mode
            return {
                "status": "stub",
                "message": "Translation not available",
                "translations": [f"[Translated: {t}]" for t in texts]
            }
        
        try:
            self.translator.set_source(source_lang)
            self.translator.set_target(target_lang)
            
            translations = []
            for text in texts:
                if text.strip():
                    translated = self.translator(text)
                    translations.append(translated)
                else:
                    translations.append("")
            
            logger.info(f"Translated {len(translations)} texts")
            return {
                "status": "success",
                "translations": translations,
                "count": len(translations)
            }
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def inpaint_image(self, image_array: np.ndarray, mask_array: np.ndarray) -> Dict:
        """Remove text from image using inpainting"""
        if not IMPORTS_AVAILABLE or self.inpainter is None:
            return {
                "status": "stub",
                "message": "Inpainting not available",
                "image": None
            }
        
        try:
            inpainted = self.inpainter.inpaint(image_array, mask_array)
            logger.info("Image inpainting completed")
            return {
                "status": "success",
                "image": inpainted
            }
        except Exception as e:
            logger.error(f"Inpainting failed: {e}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def image_to_base64(image_array: np.ndarray) -> str:
        """Convert numpy array to base64 string"""
        try:
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                # Convert BGR to RGB if needed
                image_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image_array
            
            img = Image.fromarray(image_rgb.astype('uint8'))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return img_base64
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            return ""
    
    @staticmethod
    def base64_to_image(image_base64: str) -> Optional[np.ndarray]:
        """Convert base64 string to numpy array"""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            return image_array
        except Exception as e:
            logger.error(f"Failed to convert base64 to image: {e}")
            return None
    
    @staticmethod
    def bytes_to_image(image_bytes: bytes) -> Optional[np.ndarray]:
        """Convert bytes to numpy array"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            logger.error(f"Failed to convert bytes to image: {e}")
            return None


# Global pipeline instance
_pipeline = None


def get_pipeline() -> TranslationPipeline:
    """Get or create global pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = TranslationPipeline()
    return _pipeline


def get_available_models() -> Dict:
    """Get list of available ML models"""
    if not IMPORTS_AVAILABLE:
        return {
            "detectors": [],
            "ocr": [],
            "translators": [],
            "inpainters": []
        }
    
    return {
        "detectors": list(GET_VALID_TEXTDETECTORS()),
        "ocr": list(GET_VALID_OCR()),
        "translators": list(GET_VALID_TRANSLATORS()),
        "inpainters": list(GET_VALID_INPAINTERS())
    }
