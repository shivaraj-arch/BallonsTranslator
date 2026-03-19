#!/usr/bin/env python3
"""BallonsTranslator Desktop App - Hybrid Mode
Calls Render API for translation, displays results in PyQt6 GUI"""
import sys, os, json, base64
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QFileDialog, QMessageBox, QProgressBar, QTextEdit, QScrollArea
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import requests
from PIL import Image
import io

API_URL = "https://ballons-translator-api.onrender.com"

class TranslateWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_path, target_lang):
        super().__init__()
        self.image_path = image_path
        self.target_lang = target_lang

    def run(self):
        try:
            self.progress.emit("📤 Uploading image...")
            with open(self.image_path, 'rb') as f:
                files = {'image': f}
                data = {'target_lang': self.target_lang}
                response = requests.post(f"{API_URL}/translate", files=files, data=data, timeout=300)
                if response.status_code == 200:
                    result = response.json()
                    self.progress.emit("✅ Translation complete!")
                    self.finished.emit(result)
                else:
                    self.error.emit(f"API Error: {response.status_code}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

class BallonsTranslatorDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.result_image = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("🎨 BallonsTranslator Desktop - Hybrid Mode")
        self.setGeometry(100, 100, 1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        left_panel = QVBoxLayout()
        title = QLabel("BallonsTranslator")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        left_panel.addWidget(title)
        self.upload_btn = QPushButton("📤 Upload Image")
        self.upload_btn.clicked.connect(self.upload_image)
        left_panel.addWidget(self.upload_btn)
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        left_panel.addWidget(self.image_label)
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Target Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Spanish", "French", "German", "Chinese", "Japanese", "Korean"])
        lang_layout.addWidget(self.lang_combo)
        left_panel.addLayout(lang_layout)
        self.translate_btn = QPushButton("🌍 Translate (Call API)")
        self.translate_btn.clicked.connect(self.translate_image)
        self.translate_btn.setEnabled(False)
        self.translate_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 10px;")
        left_panel.addWidget(self.translate_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_panel.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        left_panel.addWidget(self.status_label)
        left_panel.addStretch()

        right_panel = QVBoxLayout()
        results_title = QLabel("📊 Results")
        results_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        right_panel.addWidget(results_title)
        self.result_label = QLabel("Result image will appear here")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setMinimumHeight(250)
        self.result_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        right_panel.addWidget(self.result_label)
        extracted_title = QLabel("📝 Extracted Text:")
        extracted_title.setStyleSheet("font-weight: bold;")
        right_panel.addWidget(extracted_title)
        self.extracted_text = QTextEdit()
        self.extracted_text.setReadOnly(True)
        self.extracted_text.setMaximumHeight(100)
        right_panel.addWidget(self.extracted_text)
        translated_title = QLabel("🌍 Translated Text:")
        translated_title.setStyleSheet("font-weight: bold;")
        right_panel.addWidget(translated_title)
        self.translated_text = QTextEdit()
        self.translated_text.setReadOnly(True)
        self.translated_text.setMaximumHeight(100)
        right_panel.addWidget(self.translated_text)
        self.save_btn = QPushButton("💾 Save Result")
        self.save_btn.clicked.connect(self.save_result)
        self.save_btn.setEnabled(False)
        right_panel.addWidget(self.save_btn)

        left_container = QWidget()
        left_container.setLayout(left_panel)
        left_container.setMaximumWidth(400)
        right_container = QWidget()
        right_container.setLayout(right_panel)
        main_layout.addWidget(left_container)
        main_layout.addWidget(right_container)
        central_widget.setLayout(main_layout)

    def upload_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp);;All Files (*)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.status_label.setText(f"✓ Loaded: {Path(file_path).name}")
            self.translate_btn.setEnabled(True)

    def translate_image(self):
        if not self.image_path:
            QMessageBox.warning(self, "Warning", "Please upload an image first")
            return
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Processing...")
        target_lang = self.lang_combo.currentText()
        self.worker = TranslateWorker(self.image_path, target_lang)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_translation_done)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()

    def update_progress(self, message):
        self.status_label.setText(message)

    def on_translation_done(self, result):
        try:
            if 'result_image' in result:
                image_data = base64.b64decode(result['result_image'])
                image = Image.open(io.BytesIO(image_data))
                image_array = image.tobytes('raw', 'RGB')
                q_image = QImage(image_array, image.width, image.height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                scaled_pixmap = pixmap.scaledToHeight(250, Qt.TransformationMode.SmoothTransformation)
                self.result_label.setPixmap(scaled_pixmap)
                self.result_image = image
                self.save_btn.setEnabled(True)
                self.extracted_text.setText(result.get('extracted_text', 'No text extracted'))
                self.translated_text.setText(result.get('translated_text', 'No translation'))
                self.status_label.setText("✅ Translation complete!")
                self.translate_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display results: {str(e)}")
            self.translate_btn.setEnabled(True)

    def on_translation_error(self, error_msg):
        QMessageBox.critical(self, "Translation Error", error_msg)
        self.status_label.setText("❌ Error")
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def save_result(self):
        if not self.result_image:
            QMessageBox.warning(self, "Warning", "No result to save")
            return
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save Image", "", "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)")
        if file_path:
            self.result_image.save(file_path)
            QMessageBox.information(self, "Success", f"Saved to {file_path}")


def main():
    app = QApplication(sys.argv)
    window = BallonsTranslatorDesktop()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()