import sys
import os
import socket
import qrcode
import subprocess
from io import BytesIO
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTextEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QIcon

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

class NodeServerThread(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(bool)

    def __init__(self, cwd):
        super().__init__()
        this_dir = cwd
        self.cwd = this_dir
        self.process = None
        self.running = False

    def run(self):
        try:
            self.running = True
            self.status_signal.emit(True)
            
            node_bin = os.path.join(self.cwd, 'bin', 'node.exe')
            if not os.path.exists(node_bin):
                node_bin = 'node'
                
            self.process = subprocess.Popen(
                [node_bin, 'server.js'],
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1
            )
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    self.log_signal.emit(line.strip())
            self.process.wait()
        except Exception as e:
            self.log_signal.emit(f"Server Error: {e}")
        finally:
            self.running = False
            self.status_signal.emit(False)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cwd = os.path.dirname(os.path.abspath(__file__))
        self.local_ip = get_local_ip()
        self.port = 3000
        self.server_url = f"http://{self.local_ip}:{self.port}"
        
        self.init_ui()
        self.start_server()

    def init_ui(self):
        self.setWindowTitle("PulseRemote PC - Phone Control Desktop App")
        self.resize(850, 580)
        self.setMinimumSize(780, 520)

        # Global Dark StyleSheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #090d16;
            }
            QWidget {
                color: #f8fafc;
                font-family: 'Segoe UI', sans-serif;
            }
            QFrame.card {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
            QPushButton#btn-toggle-server {
                background-color: #10b981;
            }
            QPushButton#btn-toggle-server[running="false"] {
                background-color: #ef4444;
            }
            QTextEdit {
                background-color: #050811;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #94a3b8;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # TOP BAR
        top_bar = QHBoxLayout()
        
        brand_layout = QVBoxLayout()
        title_label = QLabel("📱 PulseRemote PC")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        sub_label = QLabel("Control your PC from your Smartphone Browser")
        sub_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        brand_layout.addWidget(title_label)
        brand_layout.addWidget(sub_label)
        top_bar.addLayout(brand_layout)

        top_bar.addStretch()

        self.status_pill = QLabel("🔴 Server Stopped")
        self.status_pill.setStyleSheet("""
            background-color: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 16px;
            padding: 6px 14px;
            font-weight: bold;
            font-size: 12px;
        """)
        top_bar.addWidget(self.status_pill)

        self.btn_toggle = QPushButton("Stop Server")
        self.btn_toggle.setObjectName("btn-toggle-server")
        self.btn_toggle.setProperty("running", "true")
        self.btn_toggle.clicked.connect(self.toggle_server)
        top_bar.addWidget(self.btn_toggle)

        main_layout.addLayout(top_bar)

        # MAIN CONTENT GRID (LEFT: QR CODE CARD, RIGHT: DETAILS & LOGS)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # LEFT CARD: QR CODE
        qr_card = QFrame()
        qr_card.setProperty("class", "card")
        qr_layout = QVBoxLayout(qr_card)
        qr_layout.setContentsMargins(20, 20, 20, 20)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_title = QLabel("Scan to Connect Phone")
        qr_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        qr_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(qr_title)

        qr_sub = QLabel("Scan QR code from phone camera on same Wi-Fi")
        qr_sub.setStyleSheet("font-size: 11px; color: #94a3b8; margin-bottom: 10px;")
        qr_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(qr_sub)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(240, 240)
        self.qr_label.setStyleSheet("background-color: #ffffff; border-radius: 12px; padding: 10px;")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self.qr_label)

        url_box = QHBoxLayout()
        self.url_label = QLabel(self.server_url)
        self.url_label.setStyleSheet("font-family: Consolas; font-weight: bold; color: #8b5cf6; font-size: 13px;")
        url_box.addWidget(self.url_label)

        btn_copy = QPushButton("Copy URL")
        btn_copy.setFixedWidth(90)
        btn_copy.clicked.connect(self.copy_url)
        url_box.addWidget(btn_copy)
        qr_layout.addLayout(url_box)

        content_layout.addWidget(qr_card, stretch=4)

        # RIGHT CARD: SYSTEM INFO & ACTIVITY LOGS
        right_card = QFrame()
        right_card.setProperty("class", "card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(20, 20, 20, 20)

        info_title = QLabel("Server & Connection Info")
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        right_layout.addWidget(info_title)

        info_grid = QHBoxLayout()
        
        ip_box = QVBoxLayout()
        ip_title = QLabel("Wi-Fi IP Address")
        ip_title.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.ip_val = QLabel(self.local_ip)
        self.ip_val.setStyleSheet("font-size: 15px; font-weight: bold; color: #10b981;")
        ip_box.addWidget(ip_title)
        ip_box.addWidget(self.ip_val)
        info_grid.addLayout(ip_box)

        port_box = QVBoxLayout()
        port_title = QLabel("Port Number")
        port_title.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.port_val = QLabel(str(self.port))
        self.port_val.setStyleSheet("font-size: 15px; font-weight: bold; color: #6366f1;")
        port_box.addWidget(port_title)
        port_box.addWidget(self.port_val)
        info_grid.addLayout(port_box)

        right_layout.addLayout(info_grid)

        log_title = QLabel("Live Activity Log")
        log_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #cbd5e1; margin-top: 10px;")
        right_layout.addWidget(log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)

        content_layout.addWidget(right_card, stretch=5)

        main_layout.addLayout(content_layout)

        # Render QR Code Image
        self.generate_qr_pixmap()

    def generate_qr_pixmap(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2
        )
        qr.add_data(self.server_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qimg = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qimg)
        self.qr_label.setPixmap(pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def copy_url(self):
        cb = QApplication.clipboard()
        cb.setText(self.server_url)
        self.append_log(f"Copied connection URL to clipboard: {self.server_url}")

    def append_log(self, text):
        self.log_text.append(text)

    def start_server(self):
        self.server_thread = NodeServerThread(self.cwd)
        self.server_thread.log_signal.connect(self.append_log)
        self.server_thread.status_signal.connect(self.update_status)
        self.server_thread.start()

    def update_status(self, is_running):
        if is_running:
            self.status_pill.setText("🟢 Server Active")
            self.status_pill.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.15);
                color: #10b981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 16px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            """)
            self.btn_toggle.setText("Stop Server")
            self.btn_toggle.setProperty("running", "true")
        else:
            self.status_pill.setText("🔴 Server Stopped")
            self.status_pill.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.15);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 16px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 12px;
            """)
            self.btn_toggle.setText("Start Server")
            self.btn_toggle.setProperty("running", "false")
        
        self.btn_toggle.style().unpolish(self.btn_toggle)
        self.btn_toggle.style().polish(self.btn_toggle)

    def toggle_server(self):
        if hasattr(self, 'server_thread') and self.server_thread.isRunning():
            self.server_thread.stop()
            self.append_log("Server stopped by user.")
        else:
            self.start_server()
            self.append_log("Starting server...")

    def closeEvent(self, event):
        if hasattr(self, 'server_thread') and self.server_thread.isRunning():
            self.server_thread.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
