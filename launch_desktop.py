#!/usr/bin/env python3
from pathlib import Path
import sys
import argparse
import os
import importlib
import subprocess
import base64
import io
import json
from functools import lru_cache


BRANCH = "desktop-api"
VERSION = "1.4.0"

python = sys.executable
git = os.environ.get("GIT", "git")
skip_install = False
index_url = os.environ.get("INDEX_URL", "")

PATH_ROOT = Path(__file__).parent
PATH_FONTS = PATH_ROOT / "fonts"
PATH_TRANSLATE = PATH_ROOT / "translate"
FONT_EXTS = {".ttf", ".otf", ".ttc", ".pfb"}

DEFAULT_API_URL = os.environ.get(
    "BALLOONSTRANSLATOR_API_URL",
    "https://ballons-translator-api.onrender.com",
)


parser = argparse.ArgumentParser()
parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Remote API base URL")
parser.add_argument("--debug", action="store_true")
parser.add_argument("--frozen", action="store_true", help="Run without checking requirements")
parser.add_argument("--update", action="store_true", help="Update the repository before launching")
parser.add_argument("--requirements", default="requirements_desktop.txt")
parser.add_argument("--image", default="", help="Open an image file on startup")
parser.add_argument("--ldpi", default=None, type=float, help="Logical dots per inch override")
parser.add_argument("--timeout", default=300.0, type=float, help="HTTP timeout for API calls")
parser.add_argument(
    "--keepalive-interval",
    default=240,
    type=int,
    help="Seconds between background health pings after the first successful API contact",
)
args, _ = parser.parse_known_args()


def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False
    return spec is not None


def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    if desc is not None:
        print(desc)

    if live:
        result = subprocess.run(
            command,
            check=False,
            shell=True,
            env=os.environ if custom_env is None else custom_env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}"""
            )
        return ""

    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        env=os.environ if custom_env is None else custom_env,
    )

    if result.returncode != 0:
        message = f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}
stdout: {result.stdout.decode(encoding='utf8', errors='ignore') if len(result.stdout) > 0 else '<empty>'}
stderr: {result.stderr.decode(encoding='utf8', errors='ignore') if len(result.stderr) > 0 else '<empty>'}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")


def run_pip(pip_args, desc=None):
    if skip_install:
        return

    index_url_line = f" --index-url {index_url}" if index_url else ""
    command = (
        f'"{python}" -m pip {pip_args} --prefer-binary{index_url_line} '
        "--disable-pip-version-check --no-warn-script-location"
    )
    return run(
        command,
        desc=f"Installing {desc}" if desc else None,
        errdesc=f"Couldn't install {desc}" if desc else None,
        live=True,
    )


@lru_cache(maxsize=1)
def commit_hash():
    try:
        return run(f"{git} rev-parse HEAD").strip()
    except RuntimeError:
        return "<none>"


def restart():
    print("restarting...\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)


def find_all_files_recursive(root_dir: Path, suffixes):
    for current_root, _, filenames in os.walk(root_dir):
        for filename in filenames:
            file_path = Path(current_root) / filename
            if file_path.suffix.lower() in suffixes:
                yield file_path


def prepare_environment():
    if getattr(sys, "frozen", False) or args.frozen:
        return


def build_desktop_classes():
    import httpx
    from PIL import Image
    from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
    from PyQt6.QtGui import QPixmap, QImage
    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QComboBox,
        QFileDialog,
        QMessageBox,
        QProgressBar,
        QTextEdit,
        QCheckBox,
        QGroupBox,
        QTabWidget,
        QFormLayout,
        QLineEdit,
        QScrollArea,
    )

    class BallonsAPIClient:
        def __init__(self, base_url: str, timeout: float):
            self.base_url = base_url.rstrip("/")
            self.timeout = timeout
            self.client = None

        def get_client(self):
            if self.client is None:
                self.client = httpx.Client(timeout=self.timeout)
            return self.client

        def close(self):
            if self.client is not None:
                self.client.close()
                self.client = None

        def health_check(self) -> bool:
            try:
                response = self.get_client().get(
                    f"{self.base_url}/health",
                    timeout=min(self.timeout, 15.0),
                )
                return response.status_code == 200
            except httpx.HTTPError:
                return False
            except OSError:
                return False

        def list_models(self):
            try:
                response = self.get_client().get(f"{self.base_url}/models")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                return {"status": "error", "message": str(exc), "models": {}}
            except (OSError, ValueError) as exc:
                return {"status": "error", "message": str(exc), "models": {}}

        def get_translator_languages(self, translator_name: str):
            try:
                response = self.get_client().get(
                    f"{self.base_url}/translators/{translator_name}/languages"
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                return {
                    "status": "error",
                    "translator": translator_name,
                    "message": str(exc),
                    "source_languages": [],
                    "target_languages": [],
                    "default_source": "Auto",
                    "default_target": "English",
                }
            except (OSError, ValueError) as exc:
                return {
                    "status": "error",
                    "translator": translator_name,
                    "message": str(exc),
                    "source_languages": [],
                    "target_languages": [],
                    "default_source": "Auto",
                    "default_target": "English",
                }

        def full_pipeline(
            self,
            image_base64: str,
            source_lang: str,
            target_lang: str,
            detector: str,
            ocr: str,
            translator: str,
            inpainter: str,
            enable_detect: bool,
            enable_ocr: bool,
            enable_translate: bool,
            enable_inpaint: bool,
        ):
            payload = {
                "image_base64": image_base64,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "detector": detector or None,
                "ocr": ocr or None,
                "translator": translator or None,
                "inpainter": inpainter or None,
                "enable_detection": enable_detect,
                "enable_ocr": enable_ocr,
                "enable_translation": enable_translate,
                "enable_inpainting": enable_inpaint,
            }
            try:
                response = self.get_client().post(f"{self.base_url}/pipeline/full", json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                return {"status": "error", "message": str(exc)}

    class PipelineWorker(QThread):
        progress = pyqtSignal(str)
        finished = pyqtSignal(dict)
        failed = pyqtSignal(str)

        def __init__(
            self,
            api_client: BallonsAPIClient,
            image_base64: str,
            source_lang: str,
            target_lang: str,
            detector: str,
            ocr: str,
            translator: str,
            inpainter: str,
            enable_detect: bool,
            enable_ocr: bool,
            enable_translate: bool,
            enable_inpaint: bool,
        ):
            super().__init__()
            self.api_client = api_client
            self.image_base64 = image_base64
            self.source_lang = source_lang
            self.target_lang = target_lang
            self.detector = detector
            self.ocr = ocr
            self.translator = translator
            self.inpainter = inpainter
            self.enable_detect = enable_detect
            self.enable_ocr = enable_ocr
            self.enable_translate = enable_translate
            self.enable_inpaint = enable_inpaint

        def run(self):
            self.progress.emit("Calling remote pipeline...")
            result = self.api_client.full_pipeline(
                self.image_base64,
                self.source_lang,
                self.target_lang,
                self.detector,
                self.ocr,
                self.translator,
                self.inpainter,
                self.enable_detect,
                self.enable_ocr,
                self.enable_translate,
                self.enable_inpaint,
            )
            if result.get("status") == "success":
                self.finished.emit(result)
            else:
                self.failed.emit(result.get("message", "Unknown API error"))

    class BallonsTranslatorDesktop(QMainWindow):
        def __init__(self, api_url: str, timeout: float, startup_image: str = ""):
            super().__init__()
            self.api_client = BallonsAPIClient(api_url, timeout)
            self.image_path = None
            self.image_base64 = None
            self.result_image = None
            self.pipeline_worker = None
            self.models_loaded = False
            self.translator_languages = {}
            self.keepalive_interval_ms = max(args.keepalive_interval, 30) * 1000
            self.keepalive_timer = QTimer(self)
            self.keepalive_timer.setInterval(self.keepalive_interval_ms)
            self.keepalive_timer.timeout.connect(self.on_keepalive_tick)

            self.init_ui(api_url)
            self.start_keepalive(immediate=True)

            if startup_image:
                self.load_image_file(startup_image)

        def init_ui(self, api_url: str):
            self.setWindowTitle("BallonsTranslator Desktop")
            self.resize(1180, 760)
            self.setMinimumSize(960, 680)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(16, 16, 16, 16)
            main_layout.setSpacing(16)

            left_panel = QWidget()
            left_panel.setObjectName("leftPanel")
            left_panel.setMaximumWidth(420)
            left_layout = QVBoxLayout(left_panel)
            left_layout.setContentsMargins(0, 0, 0, 0)
            left_layout.setSpacing(12)
            right_layout = QVBoxLayout()
            right_layout.setSpacing(12)

            title = QLabel("BallonsTranslator API Client")
            title.setObjectName("titleLabel")
            left_layout.addWidget(title)

            self.api_url_input = QLineEdit(api_url)
            self.api_url_input.setReadOnly(True)
            left_layout.addWidget(QLabel("Remote API"))
            left_layout.addWidget(self.api_url_input)

            self.api_status_label = QLabel("API status: idle")
            left_layout.addWidget(self.api_status_label)

            self.upload_btn = QPushButton("Open Image")
            self.upload_btn.clicked.connect(self.upload_image)
            self.upload_btn.setMinimumHeight(40)
            left_layout.addWidget(self.upload_btn)

            self.image_label = QLabel("No image selected")
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setMinimumHeight(150)
            self.image_label.setStyleSheet(
                "border: 2px solid #3498db; border-radius: 5px; background: #ecf0f1;"
            )
            left_layout.addWidget(self.image_label)

            config_group = QGroupBox("Pipeline Configuration")
            config_layout = QFormLayout()
            config_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            config_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
            config_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
            config_layout.setHorizontalSpacing(12)
            config_layout.setVerticalSpacing(10)

            self.source_lang = QComboBox()
            self.source_lang.addItem("Auto")
            config_layout.addRow("Source", self.source_lang)

            self.target_lang = QComboBox()
            self.target_lang.addItem("English")
            config_layout.addRow("Target", self.target_lang)

            self.detector_combo = QComboBox()
            config_layout.addRow("Detector", self.detector_combo)

            self.ocr_combo = QComboBox()
            config_layout.addRow("OCR", self.ocr_combo)

            self.translator_combo = QComboBox()
            self.translator_combo.currentTextChanged.connect(self.on_translator_changed)
            config_layout.addRow("Translator", self.translator_combo)

            self.inpainter_combo = QComboBox()
            config_layout.addRow("Inpainter", self.inpainter_combo)

            config_group.setLayout(config_layout)
            left_layout.addWidget(config_group)

            options_group = QGroupBox("Pipeline Steps")
            options_layout = QVBoxLayout()
            self.enable_detect = QCheckBox("Detect text regions")
            self.enable_detect.setChecked(True)
            self.enable_ocr = QCheckBox("Run OCR")
            self.enable_ocr.setChecked(True)
            self.enable_translate = QCheckBox("Translate text")
            self.enable_translate.setChecked(True)
            self.enable_inpaint = QCheckBox("Inpaint image")
            self.enable_inpaint.setChecked(False)
            options_layout.addWidget(self.enable_detect)
            options_layout.addWidget(self.enable_ocr)
            options_layout.addWidget(self.enable_translate)
            options_layout.addWidget(self.enable_inpaint)
            options_group.setLayout(options_layout)
            left_layout.addWidget(options_group)

            self.translate_btn = QPushButton("Start Translation Pipeline")
            self.translate_btn.clicked.connect(self.start_pipeline)
            self.translate_btn.setEnabled(False)
            self.translate_btn.setMinimumHeight(45)
            self.translate_btn.setObjectName("primaryButton")
            left_layout.addWidget(self.translate_btn)

            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            left_layout.addWidget(self.progress_bar)

            self.status_label = QLabel("Ready")
            self.status_label.setWordWrap(True)
            left_layout.addWidget(self.status_label)
            left_layout.addStretch()

            left_scroll = QScrollArea()
            left_scroll.setWidgetResizable(True)
            left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            left_scroll.setWidget(left_panel)

            self.tabs = QTabWidget()

            image_widget = QWidget()
            image_layout = QVBoxLayout()
            self.result_label = QLabel("Result image will appear here")
            self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.result_label.setMinimumHeight(300)
            self.result_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
            image_layout.addWidget(self.result_label)
            image_widget.setLayout(image_layout)
            self.tabs.addTab(image_widget, "Result Image")

            extracted_widget = QWidget()
            extracted_layout = QVBoxLayout()
            self.extracted_text = QTextEdit()
            self.extracted_text.setReadOnly(True)
            extracted_layout.addWidget(self.extracted_text)
            extracted_widget.setLayout(extracted_layout)
            self.tabs.addTab(extracted_widget, "Extracted Text")

            translated_widget = QWidget()
            translated_layout = QVBoxLayout()
            self.translated_text = QTextEdit()
            self.translated_text.setReadOnly(True)
            translated_layout.addWidget(self.translated_text)
            translated_widget.setLayout(translated_layout)
            self.tabs.addTab(translated_widget, "Translated Text")

            detection_widget = QWidget()
            detection_layout = QVBoxLayout()
            self.detection_info = QTextEdit()
            self.detection_info.setReadOnly(True)
            detection_layout.addWidget(self.detection_info)
            detection_widget.setLayout(detection_layout)
            self.tabs.addTab(detection_widget, "Detection Info")

            right_layout.addWidget(self.tabs)

            self.save_btn = QPushButton("Save Result Image")
            self.save_btn.clicked.connect(self.save_result)
            self.save_btn.setEnabled(False)
            self.save_btn.setMinimumHeight(40)
            right_layout.addWidget(self.save_btn)

            main_layout.addWidget(left_scroll, 0)
            main_layout.addLayout(right_layout, 2)
            central_widget.setLayout(main_layout)
            self.setStyleSheet(self.get_stylesheet())

        def load_available_models(self):
            models_response = self.api_client.list_models()
            models = models_response.get("models", {})

            for combo, items in (
                (self.detector_combo, models.get("detectors", [])),
                (self.ocr_combo, models.get("ocr", [])),
                (self.inpainter_combo, models.get("inpainters", [])),
            ):
                combo.clear()
                combo.addItem("")
                combo.addItems(items)

            translators = models.get("translators", [])
            self.translator_combo.blockSignals(True)
            self.translator_combo.clear()
            self.translator_combo.addItems(translators)
            self.translator_combo.blockSignals(False)

            default_translator = "google" if "google" in translators else (translators[0] if translators else "")
            if default_translator:
                self.translator_combo.setCurrentText(default_translator)
                self.ensure_translator_languages(default_translator)

            self.models_loaded = any(bool(items) for items in models.values())
            return models_response

        def start_keepalive(self, immediate: bool = False):
            if not self.keepalive_timer.isActive():
                self.keepalive_timer.start()
            if immediate:
                self.api_status_label.setText("API status: warming remote service")
                self.on_keepalive_tick()

        def stop_keepalive(self):
            if self.keepalive_timer.isActive():
                self.keepalive_timer.stop()

        def on_keepalive_tick(self):
            if self.api_client.health_check():
                self.api_status_label.setText("API status: connected (keep-alive active)")
            else:
                self.api_status_label.setText("API status: unavailable")
                self.stop_keepalive()

        def ensure_translator_languages(self, translator_name: str):
            if not translator_name:
                return

            cached = self.translator_languages.get(translator_name)
            if cached is None:
                cached = self.api_client.get_translator_languages(translator_name)
                self.translator_languages[translator_name] = cached

            if cached.get("status") != "success":
                self.status_label.setText(
                    f"Could not load languages for {translator_name}: {cached.get('message', 'Unknown error')}"
                )
                return

            self.start_keepalive()

            source_languages = cached.get("source_languages", []) or [cached.get("default_source", "Auto")]
            target_languages = cached.get("target_languages", []) or [cached.get("default_target", "English")]
            current_source = self.source_lang.currentText()
            current_target = self.target_lang.currentText()

            self.source_lang.blockSignals(True)
            self.target_lang.blockSignals(True)
            self.source_lang.clear()
            self.target_lang.clear()
            self.source_lang.addItems(source_languages)
            self.target_lang.addItems(target_languages)
            self.source_lang.setCurrentText(
                current_source if current_source in source_languages else cached.get("default_source", source_languages[0])
            )
            self.target_lang.setCurrentText(
                current_target if current_target in target_languages else cached.get("default_target", target_languages[0])
            )
            self.source_lang.blockSignals(False)
            self.target_lang.blockSignals(False)

        def on_translator_changed(self, translator_name: str):
            if self.models_loaded and translator_name:
                self.ensure_translator_languages(translator_name)

        def upload_image(self):
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Image",
                "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
            )
            if file_path:
                self.load_image_file(file_path)

        def load_image_file(self, file_path: str):
            try:
                with open(file_path, "rb") as file_handle:
                    image_data = file_handle.read()
                self.image_path = file_path
                self.image_base64 = base64.b64encode(image_data).decode()
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
                    self.image_label.setPixmap(scaled_pixmap)
                else:
                    self.image_label.setText(Path(file_path).name)
                self.status_label.setText(f"Loaded: {Path(file_path).name}")
                self.translate_btn.setEnabled(True)
            except (OSError, ValueError) as exc:
                QMessageBox.critical(self, "Error", f"Failed to load image: {exc}")

        def start_pipeline(self):
            if not self.image_base64:
                QMessageBox.warning(self, "Warning", "Please open an image first")
                return

            self.api_status_label.setText("API status: contacting remote service")

            if not self.models_loaded:
                models_response = self.load_available_models()
                if models_response.get("status") == "error":
                    self.api_status_label.setText("API status: unavailable")
                    QMessageBox.critical(
                        self,
                        "API Error",
                        f"Failed to load models from API: {models_response.get('message', 'Unknown error')}",
                    )
                    return

            if not self.api_client.health_check():
                self.api_status_label.setText("API status: unavailable")
                QMessageBox.critical(self, "API Error", "Could not reach the Render API.")
                return

            self.start_keepalive()

            self.translate_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.status_label.setText("Submitting work to remote API...")
            self.api_status_label.setText("API status: connected (keep-alive active)")

            self.pipeline_worker = PipelineWorker(
                self.api_client,
                self.image_base64,
                self.source_lang.currentText(),
                self.target_lang.currentText(),
                self.detector_combo.currentText(),
                self.ocr_combo.currentText(),
                self.translator_combo.currentText(),
                self.inpainter_combo.currentText(),
                self.enable_detect.isChecked(),
                self.enable_ocr.isChecked(),
                self.enable_translate.isChecked(),
                self.enable_inpaint.isChecked(),
            )
            self.pipeline_worker.progress.connect(self.update_progress)
            self.pipeline_worker.finished.connect(self.on_pipeline_complete)
            self.pipeline_worker.failed.connect(self.on_pipeline_error)
            self.pipeline_worker.start()

        def update_progress(self, message: str):
            self.status_label.setText(message)
            self.progress_bar.setValue(min(self.progress_bar.value() + 25, 90))

        def on_pipeline_complete(self, result: dict):
            try:
                self.extracted_text.setText("\n".join(result.get("extracted_texts", [])))
                self.translated_text.setText("\n".join(result.get("translated_texts", [])))

                regions = result.get("detected_regions", [])
                self.detection_info.setText(json.dumps(regions, indent=2) if regions else "No regions returned")

                inpainted_b64 = result.get("inpainted_image_base64")
                if inpainted_b64:
                    image_data = base64.b64decode(inpainted_b64)
                    image = Image.open(io.BytesIO(image_data)).convert("RGBA")
                    data = image.tobytes("raw", "RGBA")
                    q_image = QImage(
                        data,
                        image.width,
                        image.height,
                        QImage.Format.Format_RGBA8888,
                    )
                    pixmap = QPixmap.fromImage(q_image)
                    scaled_pixmap = pixmap.scaledToHeight(300, Qt.TransformationMode.SmoothTransformation)
                    self.result_label.setPixmap(scaled_pixmap)
                    self.result_image = image
                    self.save_btn.setEnabled(True)

                self.progress_bar.setValue(100)
                self.status_label.setText("Pipeline completed successfully")
            except (OSError, ValueError) as exc:
                QMessageBox.critical(self, "Error", f"Failed to display results: {exc}")
            finally:
                self.translate_btn.setEnabled(True)

        def on_pipeline_error(self, error_message: str):
            QMessageBox.critical(self, "Translation Error", error_message)
            self.status_label.setText(f"Error: {error_message}")
            self.progress_bar.setVisible(False)
            self.translate_btn.setEnabled(True)

        def save_result(self):
            if self.result_image is None:
                QMessageBox.warning(self, "Warning", "No result image to save")
                return

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Image",
                "",
                "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)",
            )
            if not file_path:
                return

            try:
                self.result_image.save(file_path)
            except OSError as exc:
                QMessageBox.critical(self, "Error", f"Failed to save image: {exc}")

        def closeEvent(self, event):
            self.stop_keepalive()
            self.api_client.close()
            super().closeEvent(event)

        @staticmethod
        def get_stylesheet() -> str:
            return """
            QMainWindow {
                background-color: #eef2f6;
            }
            QWidget {
                color: #1f2933;
                background-color: transparent;
            }
            QWidget#leftPanel {
                background-color: transparent;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: 700;
                color: #1b2a41;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c5394;
            }
            QPushButton:disabled {
                background-color: #b8c5d1;
                color: #f7fafc;
            }
            QPushButton#primaryButton {
                background-color: #1f9d55;
                color: #ffffff;
                font-size: 14px;
            }
            QPushButton#primaryButton:hover {
                background-color: #19804a;
            }
            QGroupBox {
                color: #1f2933;
                background-color: #f8fafc;
                border: 1px solid #c7d2de;
                border-radius: 8px;
                margin-top: 12px;
                padding: 14px 12px 12px 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QComboBox, QLineEdit {
                min-height: 18px;
                padding: 7px 9px;
                color: #111827;
                background-color: #ffffff;
                border: 1px solid #b9c5d3;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView {
                color: #111827;
                background-color: #ffffff;
                selection-color: #111827;
                selection-background-color: #dbeafe;
            }
            QTextEdit, QLabel {
                color: #1f2933;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #b9c5d3;
                border-radius: 6px;
                padding: 6px;
                selection-color: #111827;
                selection-background-color: #dbeafe;
            }
            QCheckBox {
                color: #1f2933;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QTabWidget::pane {
                border: 1px solid #c7d2de;
                background: #ffffff;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #dde5ee;
                color: #243b53;
                padding: 8px 12px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #111827;
            }
            QProgressBar {
                color: #111827;
                background-color: #ffffff;
                border: 1px solid #b9c5d3;
                border-radius: 6px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 5px;
            }
            QScrollArea {
                border: none;
            }
            """

    return QApplication, BallonsTranslatorDesktop


def main():
    if args.debug:
        os.environ["BALLOONTRANS_DEBUG"] = "1"

    commit = commit_hash()
    print("Python version:", sys.version)
    print("Python executable:", sys.executable)
    print(f"Version: {VERSION}")
    print(f"Branch: {BRANCH}")
    print(f"Commit hash: {commit}")

    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    prepare_environment()

    if args.update and not getattr(sys, "frozen", False):
        print("Checking for updates...")
        try:
            current_commit = commit_hash()
            run(f"{git} fetch origin", desc="Fetching updates from git...", errdesc="Failed to fetch updates.")
            latest_commit = run(f"{git} rev-parse origin/dev").strip()
            if current_commit != latest_commit:
                run(f"{git} pull origin dev", desc="Updating repository...", errdesc="Failed to update repository.")
                restart()
                return
            print("No updates found.")
        except RuntimeError as exc:
            print(f"Update check failed: {exc}")

    QApplication, BallonsTranslatorDesktop = build_desktop_classes()

    from PyQt6.QtCore import QLocale, QTranslator
    from PyQt6.QtGui import QFont, QFontDatabase, QGuiApplication

    app = QApplication(sys.argv)
    app.setApplicationName("BalloonsTranslator")
    app.setApplicationVersion(VERSION)

    lang = QLocale.system().name().replace("en_CN", "zh_CN")
    lang_path = PATH_TRANSLATE / f"{lang}.qm"
    if lang_path.exists():
        translator = QTranslator()
        translator.load(lang, str(PATH_TRANSLATE))
        app.installTranslator(translator)

    if args.ldpi:
        os.environ["QT_SCALE_FACTOR"] = str(args.ldpi / 96.0)

    if PATH_FONTS.exists():
        for font_path in find_all_files_recursive(PATH_FONTS, FONT_EXTS):
            QFontDatabase.addApplicationFont(str(font_path))

    app_font = QFont("Microsoft YaHei UI")
    if not app_font.exactMatch() or sys.platform == "darwin":
        app_font = app.font()
    app_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app_font.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.NoSubpixelAntialias
    )
    QGuiApplication.setFont(app_font)

    window = BallonsTranslatorDesktop(args.api_url, args.timeout, args.image)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

