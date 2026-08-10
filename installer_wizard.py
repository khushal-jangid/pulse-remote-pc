# PulseRemote PC - Official Setup Wizard Installer Engine
import sys
import os
import shutil
import zipfile
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QLineEdit, QFileDialog, QCheckBox,
    QProgressBar, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

class ExtractionWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, zip_path, dest_dir, desktop_sc, start_sc):
        super().__init__()
        self.zip_path = zip_path
        self.dest_dir = dest_dir
        self.desktop_sc = desktop_sc
        self.start_sc = start_sc

    def run(self):
        try:
            os.makedirs(self.dest_dir, exist_ok=True)
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                members = zip_ref.infolist()
                total = len(members)
                for idx, member in enumerate(members):
                    zip_ref.extract(member, self.dest_dir)
                    percent = int(((idx + 1) / total) * 90)
                    self.progress_signal.emit(percent, f"Extracting {member.filename}...")

            # Target EXE path
            exe_path = os.path.join(self.dest_dir, "PulseRemote.exe")

            # Create Desktop Shortcut
            if self.desktop_sc:
                self.progress_signal.emit(93, "Creating Desktop Shortcut...")
                desktop_folder = os.path.join(os.path.expanduser("~"), "Desktop")
                onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
                
                target_desktops = []
                if os.path.exists(desktop_folder): target_desktops.append(desktop_folder)
                if os.path.exists(onedrive_desktop): target_desktops.append(onedrive_desktop)

                for d_path in target_desktops:
                    sc_file = os.path.join(d_path, "PulseRemote PC.lnk")
                    ps_cmd = f"$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut('{sc_file}'); $s.TargetPath = '{exe_path}'; $s.WorkingDirectory = '{self.dest_dir}'; $s.Save()"
                    subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)

            # Create Start Menu Shortcut
            if self.start_sc:
                self.progress_signal.emit(97, "Creating Start Menu Program Shortcut...")
                start_menu = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "PulseRemote PC")
                os.makedirs(start_menu, exist_ok=True)
                sc_file = os.path.join(start_menu, "PulseRemote PC.lnk")
                ps_cmd = f"$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut('{sc_file}'); $s.TargetPath = '{exe_path}'; $s.WorkingDirectory = '{self.dest_dir}'; $s.Save()"
                subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)

            self.progress_signal.emit(100, "Installation Complete!")
            self.finished_signal.emit(True, "Installation Successful!")
        except Exception as e:
            self.finished_signal.emit(False, str(e))

class InstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bundle_dir = get_bundle_dir()
        self.payload_zip = os.path.join(self.bundle_dir, "app_payload.zip")
        
        default_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs", "PulseRemote")
        self.install_path = default_dir
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("PulseRemote PC Setup Wizard")
        self.setFixedSize(620, 420)

        self.setStyleSheet("""
            QMainWindow { background-color: #090d16; }
            QWidget { color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
            QFrame.card {
                background-color: rgba(15, 23, 42, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QLabel { font-size: 13px; }
            QLineEdit {
                background-color: #050811;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #4f46e5; }
            QPushButton#btn-cancel { background-color: rgba(255, 255, 255, 0.08); color: #cbd5e1; }
            QPushButton#btn-cancel:hover { background-color: rgba(255, 255, 255, 0.15); }
            QCheckBox { font-size: 12px; color: #cbd5e1; spacing: 8px; }
            QProgressBar {
                background-color: #050811;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: linear-gradient(90deg, #6366f1, #10b981);
                border-radius: 8px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        h_title = QLabel("⚡ PulseRemote PC Setup Wizard")
        h_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        h_sub = QLabel("Official Installer - Control your PC from your Phone")
        h_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(h_title)
        title_box.addWidget(h_sub)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Stacked Pages
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # PAGE 1: CONFIGURATION PAGE
        page1 = QFrame()
        page1.setProperty("class", "card")
        p1_layout = QVBoxLayout(page1)
        p1_layout.setContentsMargins(20, 20, 20, 20)
        p1_layout.setSpacing(14)

        desc = QLabel("Select the installation folder and shortcut options for PulseRemote PC:")
        desc.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        p1_layout.addWidget(desc)

        # Path Selection
        path_box = QVBoxLayout()
        p_lbl = QLabel("Destination Folder:")
        p_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        path_box.addWidget(p_lbl)

        path_row = QHBoxLayout()
        self.path_input = QLineEdit(self.install_path)
        path_row.addWidget(self.path_input)

        btn_browse = QPushButton("Browse...")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self.browse_folder)
        path_row.addWidget(btn_browse)
        path_box.addLayout(path_row)
        p1_layout.addLayout(path_box)

        # Checkboxes
        self.cb_desktop = QCheckBox("Create Desktop Shortcut")
        self.cb_desktop.setChecked(True)
        self.cb_start = QCheckBox("Create Start Menu Shortcut")
        self.cb_start.setChecked(True)

        p1_layout.addWidget(self.cb_desktop)
        p1_layout.addWidget(self.cb_start)
        p1_layout.addStretch()

        self.stack.addWidget(page1)

        # PAGE 2: PROGRESS PAGE
        page2 = QFrame()
        page2.setProperty("class", "card")
        p2_layout = QVBoxLayout(page2)
        p2_layout.setContentsMargins(20, 20, 20, 20)
        p2_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.setSpacing(16)

        self.lbl_status = QLabel("Preparing installation...")
        self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #6366f1;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setValue(0)
        p2_layout.addWidget(self.progress_bar)

        self.lbl_detail = QLabel("Please wait while files are extracted to your PC...")
        self.lbl_detail.setStyleSheet("font-size: 11px; color: #94a3b8;")
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p2_layout.addWidget(self.lbl_detail)

        self.stack.addWidget(page2)

        # PAGE 3: FINISH PAGE
        page3 = QFrame()
        page3.setProperty("class", "card")
        p3_layout = QVBoxLayout(page3)
        p3_layout.setContentsMargins(20, 20, 20, 20)
        p3_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.setSpacing(14)

        success_icon = QLabel("🎉")
        success_icon.setStyleSheet("font-size: 48px;")
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(success_icon)

        fin_title = QLabel("PulseRemote PC Installed Successfully!")
        fin_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
        fin_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(fin_title)

        fin_desc = QLabel("PulseRemote PC is now ready to use on your computer.")
        fin_desc.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        fin_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p3_layout.addWidget(fin_desc)

        self.cb_launch = QCheckBox("Launch PulseRemote PC now")
        self.cb_launch.setChecked(True)
        p3_layout.addWidget(self.cb_launch, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(page3)

        # BOTTOM BUTTON BAR
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn-cancel")
        self.btn_cancel.clicked.connect(self.close)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_next = QPushButton("Install Now ➔")
        self.btn_next.clicked.connect(self.start_install)
        btn_bar.addWidget(self.btn_next)

        layout.addLayout(btn_bar)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Installation Folder", self.path_input.text())
        if folder:
            self.path_input.setText(folder)

    def start_install(self):
        if self.stack.currentIndex() == 0:
            self.install_path = self.path_input.text()
            self.stack.setCurrentIndex(1)
            self.btn_cancel.setEnabled(False)
            self.btn_next.setEnabled(False)

            self.worker = ExtractionWorker(
                self.payload_zip,
                self.install_path,
                self.cb_desktop.isChecked(),
                self.cb_start.isChecked()
            )
            self.worker.progress_signal.connect(self.update_progress)
            self.worker.finished_signal.connect(self.on_finished)
            self.worker.start()
        elif self.stack.currentIndex() == 2:
            if self.cb_launch.isChecked():
                exe_path = os.path.join(self.install_path, "PulseRemote.exe")
                if os.path.exists(exe_path):
                    subprocess.Popen([exe_path], cwd=self.install_path)
            self.close()

    def update_progress(self, val, detail):
        self.progress_bar.setValue(val)
        self.lbl_detail.setText(detail)

    def on_finished(self, success, msg):
        if success:
            self.stack.setCurrentIndex(2)
            self.btn_cancel.hide()
            self.btn_next.setEnabled(True)
            self.btn_next.setText("Finish & Close")
        else:
            self.lbl_status.setText("❌ Installation Failed")
            self.lbl_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.lbl_detail.setText(f"Error: {msg}")
            self.btn_cancel.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec())
