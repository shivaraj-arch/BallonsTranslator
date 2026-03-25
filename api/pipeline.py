"""
BallonsTranslator ML/AI Pipeline Backend
Handles text detection, OCR, inpainting, and translation
"""
import os
import sys
import base64
import io
import re
import importlib
from functools import lru_cache
import numpy as np
from typing import Any, List, Dict, Optional
from PIL import Image
import logging

logger = logging.getLogger(__name__)

PIPELINE_EXCEPTIONS = (
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
    ImportError,
    OSError,
)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modules import GET_VALID_TEXTDETECTORS, GET_VALID_INPAINTERS, GET_VALID_TRANSLATORS, GET_VALID_OCR
    # from modules.base import BaseModule
    # from utils.config import ProgramConfig, pcfg
    # from utils.textblock import TextBlock
    # from utils.logger import logger as app_logger
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.warning("Could not import BallonsTranslator modules: %s. Running in stub mode.", e)
    IMPORTS_AVAILABLE = False


@lru_cache(maxsize=1)
def collect_module_import_diagnostics() -> Dict[str, Any]:
    """Import module scripts individually and capture failures for diagnostics."""
    diagnostics = {
        "imports_available": IMPORTS_AVAILABLE,
        "initialized": False,
        "registered": {
            "detectors": [],
            "ocr": [],
            "translators": [],
            "inpainters": [],
        },
        "failures": {
            "detectors": [],
            "ocr": [],
            "translators": [],
            "inpainters": [],
        },
    }

    if not IMPORTS_AVAILABLE:
        return diagnostics

    try:
        from modules.base import MODULE_SCRIPTS

        kind_map = {
            "textdetector": "detectors",
            "ocr": "ocr",
            "translator": "translators",
            "inpainter": "inpainters",
        }

        for module_kind, script_info in MODULE_SCRIPTS.items():
            output_key = kind_map[module_kind]
            module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), script_info["module_dir"])
            pattern = re.compile(script_info["module_pattern"])
            module_prefix = script_info["module_dir"].replace("/", ".") + "."

            for file_name in sorted(os.listdir(module_dir)):
                if pattern.match(file_name) is None:
                    continue
                module_name = module_prefix + file_name.replace(".py", "")
                try:
                    importlib.import_module(module_name)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    diagnostics["failures"][output_key].append(
                        {"module": module_name, "error": str(exc)}
                    )

        diagnostics["registered"] = {
            "detectors": list(GET_VALID_TEXTDETECTORS()),
            "ocr": list(GET_VALID_OCR()),
            "translators": list(GET_VALID_TRANSLATORS()),
            "inpainters": list(GET_VALID_INPAINTERS()),
        }
        diagnostics["initialized"] = True
    except PIPELINE_EXCEPTIONS as e:
        logger.error("Failed to collect module diagnostics: %s", e)

    return diagnostics


@lru_cache(maxsize=1)
def initialize_runtime_modules() -> bool:
    """Initialize module registries the same way the desktop launcher does."""
    if not IMPORTS_AVAILABLE:
        return False

    try:
        from modules.prepare_local_files import prepare_local_files_forall

        diagnostics = collect_module_import_diagnostics()
        prepare_local_files_forall()
        logger.info("Module registries initialized successfully")
        return diagnostics.get("initialized", False)
    except PIPELINE_EXCEPTIONS as e:
        logger.error("Failed to initialize module registries: %s", e)
        return False


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
                initialize_runtime_modules()
                if config_path and os.path.exists(config_path):
                    from utils import config as program_config
                    program_config.load_config(config_path)
                    self.config = program_config.pcfg
                self.initialized = True
                logger.info("Pipeline initialized successfully")
            except PIPELINE_EXCEPTIONS as e:
                logger.error("Failed to initialize pipeline: %s", e)
    
    def load_detector(self, detector_name: str = "craft"):
        """Load text detection model"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import TEXTDETECTORS
            if detector_name in TEXTDETECTORS.module_dict:
                self.detector = TEXTDETECTORS.module_dict[detector_name]()
                self.detector.load_model()
                logger.info("Loaded detector: %s", detector_name)
                return {"status": "success", "detector": detector_name}
            else:
                return {"status": "error", "message": f"Detector {detector_name} not found"}
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to load detector: %s", e)
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
                logger.info("Loaded OCR: %s", ocr_name)
                return {"status": "success", "ocr": ocr_name}
            else:
                return {"status": "error", "message": f"OCR {ocr_name} not found"}
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to load OCR: %s", e)
            return {"status": "error", "message": str(e)}
    
    def load_translator(
        self,
        translator_name: str = "google",
        source_lang: str = "Auto",
        target_lang: str = "English",
    ):
        """Load translation model/API"""
        if not IMPORTS_AVAILABLE:
            return {"status": "stub", "message": "Running in stub mode"}
        
        try:
            from modules import TRANSLATORS
            if translator_name in TRANSLATORS.module_dict:
                translator_module = TRANSLATORS.module_dict[translator_name]
                self.translator = translator_module(
                    source_lang,
                    target_lang,
                    raise_unsupported_lang=False,
                )
                logger.info("Loaded translator: %s", translator_name)
                return {"status": "success", "translator": translator_name}
            else:
                return {"status": "error", "message": f"Translator {translator_name} not found"}
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to load translator: %s", e)
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
                logger.info("Loaded inpainter: %s", inpainter_name)
                return {"status": "success", "inpainter": inpainter_name}
            else:
                return {"status": "error", "message": f"Inpainter {inpainter_name} not found"}
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to load inpainter: %s", e)
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
            logger.info("Detected %d text regions", len(results) if results else 0)
            return {
                "status": "success",
                "regions": results if results else [],
                "count": len(results) if results else 0
            }
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Detection failed: %s", e)
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
            
            logger.info("Recognized %d text blocks", len(texts))
            return {
                "status": "success",
                "texts": texts,
                "count": len(texts)
            }
        except PIPELINE_EXCEPTIONS as e:
            logger.error("OCR failed: %s", e)
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
            
            logger.info("Translated %d texts", len(translations))
            return {
                "status": "success",
                "translations": translations,
                "count": len(translations)
            }
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Translation failed: %s", e)
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
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Inpainting failed: %s", e)
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def image_to_base64(image_array: np.ndarray) -> str:
        """Convert numpy array to base64 string"""
        try:
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                image_rgb = image_array[:, :, ::-1]
            else:
                image_rgb = image_array

            img = Image.fromarray(image_rgb.astype("uint8"))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            return img_base64
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to convert image to base64: %s", e)
            return ""
    
    @staticmethod
    def base64_to_image(image_base64: str) -> Optional[np.ndarray]:
        """Convert base64 string to numpy array"""
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            return np.array(image)[:, :, ::-1]
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to convert base64 to image: %s", e)
            return None
    
    @staticmethod
    def bytes_to_image(image_bytes: bytes) -> Optional[np.ndarray]:
        """Convert bytes to numpy array"""
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            return np.array(image)[:, :, ::-1]
        except PIPELINE_EXCEPTIONS as e:
            logger.error("Failed to convert bytes to image: %s", e)
            return None


@lru_cache(maxsize=1)
def get_pipeline() -> TranslationPipeline:
    """Get or create global pipeline instance"""
    return TranslationPipeline()


def get_available_models() -> Dict:
    """Get list of available ML models"""
    if not IMPORTS_AVAILABLE:
        return {
            "detectors": [],
            "ocr": [],
            "translators": [],
            "inpainters": []
        }

    initialize_runtime_modules()
    
    return {
        "detectors": list(GET_VALID_TEXTDETECTORS()),
        "ocr": list(GET_VALID_OCR()),
        "translators": list(GET_VALID_TRANSLATORS()),
        "inpainters": list(GET_VALID_INPAINTERS())
    }


def get_module_diagnostics() -> Dict[str, Any]:
    """Return import diagnostics for module discovery on the backend."""
    return collect_module_import_diagnostics()


def get_translator_languages(translator_name: str) -> Dict[str, Any]:
    """Get supported source and target languages for a translator."""
    if not IMPORTS_AVAILABLE:
        return {
            "status": "stub",
            "translator": translator_name,
            "source_languages": [],
            "target_languages": [],
            "default_source": "Auto",
            "default_target": "English",
        }

    initialize_runtime_modules()

    try:
        from modules import TRANSLATORS

        if translator_name not in TRANSLATORS.module_dict:
            return {
                "status": "error",
                "message": f"Translator {translator_name} not found",
            }

        translator_module = TRANSLATORS.module_dict[translator_name]
        translator = translator_module("Auto", "English", raise_unsupported_lang=False)

        return {
            "status": "success",
            "translator": translator.name,
            "source_languages": list(translator.supported_src_list),
            "target_languages": list(translator.supported_tgt_list),
            "default_source": translator.lang_source,
            "default_target": translator.lang_target,
        }
    except PIPELINE_EXCEPTIONS as e:
        logger.error("Failed to get translator languages for %s: %s", translator_name, e)
        return {
            "status": "error",
            "message": str(e),
            "translator": translator_name,
            "source_languages": [],
            "target_languages": [],
            "default_source": "Auto",
            "default_target": "English",
        }
