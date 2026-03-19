"""
BallonsTranslator API Package
REST API for manga/comic translation pipeline
"""

__version__ = "1.0.0"
__author__ = "BallonsTranslator Contributors"

from .pipeline import TranslationPipeline, get_pipeline, get_available_models
from .server import app

__all__ = [
    "TranslationPipeline",
    "get_pipeline",
    "get_available_models",
    "app"
]
