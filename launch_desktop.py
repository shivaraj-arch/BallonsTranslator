#!/usr/bin/env python3
"""
BallonsTranslator Desktop App - API Client Mode
Connects to Render API for ML/AI tasks
API Root: https://ballons-translator-api.onrender.com/
"""
import sys
import os
import json
import base64
import httpx
from pathlib import Path
from typing import Optional, Dict, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox,
    QProgressBar, QTextEdit, QSpinBox, QCheckBox, QGroupBox,
    QTabWidget, QFormLayout, QLineEdit
)
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PIL import Image
import io

# ============================================
# Configuration
# ============================================
API_URL = "https://ballons-translator-api.onrender.com"
# Uncomment for local testing:
# API_URL = "http://localhost:8000"

TIMEOUT = 300  # 5 minute timeout for API calls

# ============================================
# API Client
# ============================================

class BallonsAPIClient:
    """Client for BallonsTranslator API"""
    
    def __init__(self, base_url: str = API_URL, timeout: float = TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = None
    
    def get_client(self):
        """Get or create HTTP client"""
        if self.client is None:
            self.client = httpx.Client(timeout=self.timeout)
        return self.client
    
    def close(self):
        """Close HTTP client"""
        if self.client:
            self.client.close()
            self.client = None
    
    def health_check(self) -> bool:
        """Check API health"""
        try:
            response = self.get_client().get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> Dict:
        """Get list of available models"""
        try:
            response = self.get_client().get(f"{self.base_url}/models")
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            print(f"Error listing models: {e}")
            return {}
    
    def detect_text(self, image_base64: str) -> Dict:
        """Detect text regions in image"""
        try:
            response = self.get_client().post(
                f"{self.base_url}/detect",
                json={"image_base64": image_base64}
            )
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def ocr(self, image_base64: str, regions: Optional[List] = None) -> Dict:
        """Recognize text from image"""
        try:
            response = self.get_client().post(
                f"{self.base_url}/ocr",
                json={"image_base64": image_base64, "regions": regions}
            )
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def translate(self, texts: List[str], source_lang: str = "auto", target_lang: str = "English") -> Dict:
        """Translate text"""
        try:
            response = self.get_client().post(
                f"{self.base_url}/translate",
                json={
                    "texts": texts,
                    "source_lang": source_lang,
                    "target_lang": target_lang
                }
            )
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def inpaint(self, image_base64: str, mask_base64: str) -> Dict:
        """Inpaint image"""
        try:
            response = self.get_client().post(
                f"{self.base_url}/inpaint",
                json={"image_base64": image_base64, "mask_base64": mask_base64}
            )
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def full_pipeline(self, image_base64: str, source_lang: str = "auto", target_lang: str = "English",
                     enable_detect: bool = True, enable_ocr: bool = True,
                     enable_translate: bool = True, enable_inpaint: bool = False) -> Dict:
        """Run full translation pipeline"""
        try:
            response = self.get_client().post(
                f"{self.base_url}/pipeline/full",
                json={
                    "image_base64": image_base64,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "enable_detection": enable_detect,
                    "enable_ocr": enable_ocr,
                    "enable_translation": enable_translate,
                    "enable_inpainting": enable_inpaint
                }
            )
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ============================================
# Worker Threads
# ============================================

class PipelineWorker(QThread):
    """Worker thread for translation pipeline"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, api_client: BallonsAPIClient, image_base64: str,
                 source_lang: str, target_lang: str,
                 enable_detect: bool, enable_ocr: bool,
                 enable_translate: bool, enable_inpaint: bool):
        super().__init__()
        self.api_client = api_client
        self.image_base64 = image_base64
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.enable_detect = enable_detect
        self.enable_ocr = enable_ocr
        self.enable_translate = enable_translate
        self.enable_inpaint = enable_inpaint
    
    def run(self):
        try:
            self.progress.emit("📤 Uploading image...")
            self.progress.emit("🔍 Running detection...")
            
            result = self.api_client.full_pipeline(
                self.image_base64,
                self.source_lang,
                self.target_lang,
                self.enable_detect,
                self.enable_ocr,
                self.enable_translate,
                self.enable_inpaint
            )
            
            if result.get("status") == "success":
                self.progress.emit("✅ Pipeline completed!")
                self.finished.emit(result)
            else:
                self.error.emit(f"Pipeline failed: {result.get('message', 'Unknown error')}")
        
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")


# ============================================
# Main Application Window
# ============================================

class BallonsTranslatorDesktop(QMainWindow):
    """Main desktop application window"""
    
    def __init__(self):
        super().__init__()
        self.api_client = BallonsAPIClient()
        self.image_path = None
        self.image_base64 = None
        self.result_image = None
        self.pipeline_worker = None
        
        # Check API connection
        self.check_api_connection()
        
        self.initUI()
        self.load_available_models()
    
    def check_api_connection(self):
        """Check if API is available"""
        try:
            if self.api_client.health_check():
                print("✓ API is available")
            else:
                print("✗ API health check failed")
        except Exception as e:
            print(f"✗ Cannot connect to API: {e}")
    
    def initUI(self):
        """Initialize UI"""
        self.setWindowTitle("🎨 BallonsTranslator Desktop - API Client Mode")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        left_panel = self.create_left_panel()
        left_panel.setMaximumWidth(420)
        
        # Right panel - Results
        right_panel = self.create_right_panel()
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        central_widget.setLayout(main_layout)
        self.setStyleSheet(self.get_stylesheet())
    
    def create_left_panel(self) -> QVBoxLayout:
        """Create left control panel"""
        left_panel = QVBoxLayout()
        
        # Title
        title = QLabel("BallonsTranslator")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        left_panel.addWidget(title)
        
        # File selection
        self.upload_btn = QPushButton("📤 Upload Image")
        self.upload_btn.clicked.connect(self.upload_image)
        self.upload_btn.setMinimumHeight(40)
        left_panel.addWidget(self.upload_btn)
        
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(150)
        self.image_label.setStyleSheet("border: 2px solid #3498db; border-radius: 5px; background: #ecf0f1;")
        left_panel.addWidget(self.image_label)
        
        # API Configuration
        config_group = QGroupBox("Pipeline Configuration")
        config_layout = QFormLayout()
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Source:"))
        self.source_lang = QComboBox()
        self.source_lang.addItems(["Auto", "English", "Japanese", "Chinese", "Korean"])
        lang_layout.addWidget(self.source_lang)
        config_layout.addRow("Language:", lang_layout)
        
        tgt_layout = QHBoxLayout()
        tgt_layout.addWidget(QLabel("Target:"))
        self.target_lang = QComboBox()
        self.target_lang.addItems(["English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean"])
        tgt_layout.addWidget(self.target_lang)
        config_layout.addRow("", tgt_layout)
        
        # Module selection
        self.detector_combo = QComboBox()
        config_layout.addRow("Detector:", self.detector_combo)
        
        self.ocr_combo = QComboBox()
        config_layout.addRow("OCR:", self.ocr_combo)
        
        self.translator_combo = QComboBox()
        config_layout.addRow("Translator:", self.translator_combo)
        
        self.inpainter_combo = QComboBox()
        config_layout.addRow("Inpainter:", self.inpainter_combo)
        
        config_group.setLayout(config_layout)
        left_panel.addWidget(config_group)
        
        # Pipeline options
        options_group = QGroupBox("Pipeline Steps")
        options_layout = QVBoxLayout()
        
        self.enable_detect = QCheckBox("Detect Text Regions")
        self.enable_detect.setChecked(True)
        options_layout.addWidget(self.enable_detect)
        
        self.enable_ocr = QCheckBox("Run OCR")
        self.enable_ocr.setChecked(True)
        options_layout.addWidget(self.enable_ocr)
        
        self.enable_translate = QCheckBox("Translate Text")
        self.enable_translate.setChecked(True)
        options_layout.addWidget(self.enable_translate)
        
        self.enable_inpaint = QCheckBox("Inpaint Image")
        self.enable_inpaint.setChecked(False)
        options_layout.addWidget(self.enable_inpaint)
        
        options_group.setLayout(options_layout)
        left_panel.addWidget(options_group)
        
        # Translate button
        self.translate_btn = QPushButton("🚀 Start Translation Pipeline")
        self.translate_btn.clicked.connect(self.start_pipeline)
        self.translate_btn.setEnabled(False)
        self.translate_btn.setMinimumHeight(45)
        self.translate_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 14px;")
        left_panel.addWidget(self.translate_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_panel.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        left_panel.addWidget(self.status_label)
        
        left_panel.addStretch()
        
        return left_panel
    
    def create_right_panel(self) -> QVBoxLayout:
        """Create right results panel"""
        right_panel = QVBoxLayout()
        
        # Tabs for different results
        self.tabs = QTabWidget()
        
        # Image tab
        image_layout = QVBoxLayout()
        self.result_label = QLabel("Result image will appear here")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setMinimumHeight(300)
        self.result_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        image_layout.addWidget(self.result_label)
        image_widget = QWidget()
        image_widget.setLayout(image_layout)
        self.tabs.addTab(image_widget, "📷 Result Image")
        
        # Extracted text tab
        extracted_layout = QVBoxLayout()
        extracted_title = QLabel("📝 Extracted Text")
        extracted_title.setStyleSheet("font-weight: bold;")
        extracted_layout.addWidget(extracted_title)
        self.extracted_text = QTextEdit()
        self.extracted_text.setReadOnly(True)
        extracted_layout.addWidget(self.extracted_text)
        extracted_widget = QWidget()
        extracted_widget.setLayout(extracted_layout)
        self.tabs.addTab(extracted_widget, "📝 Extracted Text")
        
        # Translated text tab
        translated_layout = QVBoxLayout()
        translated_title = QLabel("🌍 Translated Text")
        translated_title.setStyleSheet("font-weight: bold;")
        translated_layout.addWidget(translated_title)
        self.translated_text = QTextEdit()
        self.translated_text.setReadOnly(True)
        translated_layout.addWidget(self.translated_text)
        translated_widget = QWidget()
        translated_widget.setLayout(translated_layout)
        self.tabs.addTab(translated_widget, "🌍 Translated Text")
        
        # Detection info tab
        detection_layout = QVBoxLayout()
        detection_title = QLabel("🔍 Detection Info")
        detection_title.setStyleSheet("font-weight: bold;")
        detection_layout.addWidget(detection_title)
        self.detection_info = QTextEdit()
        self.detection_info.setReadOnly(True)
        detection_layout.addWidget(self.detection_info)
        detection_widget = QWidget()
        detection_widget.setLayout(detection_layout)
        self.tabs.addTab(detection_widget, "🔍 Detection Info")
        
        right_panel.addWidget(self.tabs)
        
        # Save button
        self.save_btn = QPushButton("💾 Save Result Image")
        self.save_btn.clicked.connect(self.save_result)
        self.save_btn.setEnabled(False)
        self.save_btn.setMinimumHeight(40)
        right_panel.addWidget(self.save_btn)
        
        return right_panel
    
    def load_available_models(self):
        """Load available models from API"""
        models = self.api_client.list_models()
        
        if "models" in models:
            self.detector_combo.addItems(models["models"].get("detectors", []))
            self.ocr_combo.addItems(models["models"].get("ocr", []))
            self.translator_combo.addItems(models["models"].get("translators", []))
            self.inpainter_combo.addItems(models["models"].get("inpainters", []))
    
    def upload_image(self):
        """Handle image upload"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"
        )
        
        if file_path:
            try:
                self.image_path = file_path
                
                # Load and encode image
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                self.image_base64 = base64.b64encode(image_data).decode()
                
                # Display thumbnail
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                
                self.status_label.setText(f"✓ Loaded: {Path(file_path).name}")
                self.translate_btn.setEnabled(True)
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
    
    def start_pipeline(self):
        """Start the translation pipeline"""
        if not self.image_base64:
            QMessageBox.warning(self, "Warning", "Please upload an image first")
            return
        
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Processing...")
        
        source_lang = self.source_lang.currentText()
        target_lang = self.target_lang.currentText()
        
        self.pipeline_worker = PipelineWorker(
            self.api_client,
            self.image_base64,
            source_lang,
            target_lang,
            self.enable_detect.isChecked(),
            self.enable_ocr.isChecked(),
            self.enable_translate.isChecked(),
            self.enable_inpaint.isChecked()
        )
        
        self.pipeline_worker.progress.connect(self.update_progress)
        self.pipeline_worker.finished.connect(self.on_pipeline_complete)
        self.pipeline_worker.error.connect(self.on_pipeline_error)
        self.pipeline_worker.start()
    
    def update_progress(self, message: str):
        """Update progress message"""
        self.status_label.setText(message)
        self.progress_bar.setValue(min(self.progress_bar.value() + 10, 90))
    
    def on_pipeline_complete(self, result: dict):
        """Handle pipeline completion"""
        try:
            # Display extracted text
            extracted_texts = result.get("extracted_texts", [])
            self.extracted_text.setText("\n".join(extracted_texts))
            
            # Display translated text
            translated_texts = result.get("translated_texts", [])
            self.translated_text.setText("\n".join(translated_texts))
            
            # Display detection info
            regions = result.get("detected_regions", [])
            detection_info = f"Regions detected: {len(regions)}\n"
            if regions:
                detection_info += "Regions:\n" + json.dumps(regions[:5], indent=2)
                if len(regions) > 5:
                    detection_info += f"\n... and {len(regions) - 5} more"
            self.detection_info.setText(detection_info)
            
            # Display result image if available
            inpainted_b64 = result.get("inpainted_image_base64")
            if inpainted_b64:
                image_data = base64.b64decode(inpainted_b64)
                image = Image.open(io.BytesIO(image_data))
                
                # Convert to QPixmap
                image_rgb = image.convert('RGB')
                data = image_rgb.tobytes('raw', 'RGB')
                q_image = QImage(data, image_rgb.width, image_rgb.height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaledToHeight(300, Qt.TransformationMode.SmoothTransformation)
                self.result_label.setPixmap(scaled_pixmap)
                
                self.result_image = image
                self.save_btn.setEnabled(True)
            
            self.status_label.setText("✅ Pipeline completed successfully!")
            self.progress_bar.setValue(100)
            self.translate_btn.setEnabled(True)
            
            # Switch to results tab
            self.tabs.setCurrentIndex(0)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display results: {str(e)}")
            self.translate_btn.setEnabled(True)
    
    def on_pipeline_error(self, error_msg: str):
        """Handle pipeline error"""
        QMessageBox.critical(self, "Translation Error", error_msg)
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def save_result(self):
        """Save result image"""
        if not self.result_image:
            QMessageBox.warning(self, "Warning", "No result image to save")
            return
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, "Save Image", "",
            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)"
        )
        
        if file_path:
            try:
                self.result_image.save(file_path)
                QMessageBox.information(self, "Success", f"Saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    @staticmethod
    def get_stylesheet() -> str:
        """Get application stylesheet"""
        return """
        QMainWindow {
            background-color: #ecf0f1;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1c5394;
        }
        QGroupBox {
            color: #2c3e50;
            border: 2px solid #3498db;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QComboBox, QLineEdit {
            padding: 5px;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
        }
        QTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            padding: 5px;
        }
        """


# ============================================
# Main Entry Point
# ============================================

def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = BallonsTranslatorDesktop()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

