import sys
import os
import subprocess
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QTextEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal
class Worker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, files, save_dir, ncmdump_path):
        super().__init__()
        self.files = files
        self.save_dir = save_dir
        self.ncmdump_exe = ncmdump_path
    def run(self):
        self.log.emit(f"启动外部支援: {os.path.basename(self.ncmdump_exe)}")
        for idx, file_path in enumerate(self.files):
            try:
                filename = os.path.basename(file_path)
                self.log.emit(f"\n[{idx + 1}/{len(self.files)}] 处理: {filename}")
                temp_ncm = os.path.join(self.save_dir, filename)
                shutil.copy2(file_path, temp_ncm)
                self.log.emit("硬解密中...")
                cmd = [self.ncmdump_exe, temp_ncm]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                try:
                    os.remove(temp_ncm)
                except:
                    pass
                base_name = os.path.splitext(filename)[0]
                decrypted_file = None
                possible_exts = [".flac", ".mp3", ".m4a", ".wav", ".ogg"]
                for ext in possible_exts:
                    candidate = os.path.join(self.save_dir, base_name + ext)
                    if os.path.exists(candidate):
                        decrypted_file = candidate
                        break
                if not decrypted_file:
                    for f in os.listdir(self.save_dir):
                        if base_name in f and f.endswith(tuple(possible_exts)):
                            decrypted_file = os.path.join(self.save_dir, f)
                            break
                if not decrypted_file:
                    self.log.emit(f"ncmdump 未生成预期文件。报错信息: {proc.stderr}")
                    continue
                self.log.emit(f"解密成功: {os.path.basename(decrypted_file)}")
                ext = os.path.splitext(decrypted_file)[1].lower()
                final_path = ""
                if ext == '.mp3':
                    final_path = decrypted_file  # MP3 一般不用动，除非你想剥离封面视频
                    self.log.emit("MP3 格式。")
                else:
                    final_path = os.path.splitext(decrypted_file)[0] + ".m4a"
                    self.log.emit("正在提取纯净音频并转为 ALAC (Apple Lossless)...")
                    try:
                        self.convert_ffmpeg(decrypted_file, final_path)
                        try:
                            os.remove(decrypted_file)
                        except:
                            pass
                    except Exception as e:
                        self.log.emit(f"❌ 转换失败: {e}")
                        continue
                self.log.emit(f"🎉 搞定: {os.path.basename(final_path)}")
            except Exception as e:
                self.log.emit(f"💥 流程异常: {e}")
        self.finished.emit()
    def convert_ffmpeg(self, inp, out):
        cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', inp]
        cmd.extend(['-map', '0:a', '-vn'])
        cmd.extend(['-c:a', 'alac', '-f', 'ipod'])
        cmd.append(out)
        subprocess.run(cmd, check=True)
class NCMCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NCM Commander v2.1 (Audio Pure)")
        self.setGeometry(100, 100, 600, 550)
        w = QWidget()
        self.setCentralWidget(w)
        layout = QVBoxLayout()
        w.setLayout(layout)
        self.ncmdump_path = os.path.join(os.getcwd(), "ncmdump.exe")
        lbl_status = QLabel()
        if os.path.exists(self.ncmdump_path):
            lbl_status.setText("已检测到 ncmdump.exe")
            lbl_status.setStyleSheet("color: #00ff00; font-weight: bold;")
        else:
            lbl_status.setText("未检测到 ncmdump.exe (请将其放入脚本同目录)")
            lbl_status.setStyleSheet("color: #ff0000; font-weight: bold;")
        layout.addWidget(lbl_status)
        g1 = QGroupBox("选择文件")
        l1 = QVBoxLayout()
        self.btn_files = QPushButton("选择 .ncm 文件")
        self.btn_files.clicked.connect(self.sel_files)
        self.lbl_count = QLabel("未选择")
        l1.addWidget(self.btn_files)
        l1.addWidget(self.lbl_count)
        g1.setLayout(l1)
        layout.addWidget(g1)
        g2 = QGroupBox("💾 保存位置")
        l2 = QHBoxLayout()
        self.path_in = QLineEdit(os.path.join(os.getcwd(), 'NCM_Decrypted'))
        btn_path = QPushButton("浏览...")
        btn_path.clicked.connect(self.sel_path)
        l2.addWidget(self.path_in)
        l2.addWidget(btn_path)
        g2.setLayout(l2)
        layout.addWidget(g2)
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        layout.addWidget(self.log_txt)
        self.btn_run = QPushButton("启动")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.start)
        self.btn_run.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        if not os.path.exists(self.ncmdump_path):
            self.btn_run.setEnabled(False)
        layout.addWidget(self.btn_run)
        self.files = []
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QGroupBox { color: #00ddff; font-weight: bold; border: 1px solid #555; margin-top: 10px; padding-top: 15px; }
            QLabel { color: #ccc; }
            QLineEdit, QTextEdit { background: #333; color: #fff; border: 1px solid #555; }
            QPushButton { background: #444; color: #fff; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background: #555; }
        """)
    def sel_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 NCM", "", "NCM Files (*.ncm)")
        if files:
            self.files = files
            self.lbl_count.setText(f"已选中 {len(files)} 个文件")
            self.log_txt.append(f"准备就绪: {len(files)} 个文件")
    def sel_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d: self.path_in.setText(d)
    def start(self):
        if not self.files: return QMessageBox.warning(self, "!", "请先选择文件")
        out_dir = self.path_in.text()
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        self.btn_run.setEnabled(False)
        self.worker = Worker(self.files, out_dir, self.ncmdump_path)
        self.worker.log.connect(self.log_txt.append)
        self.worker.finished.connect(
            lambda: [self.btn_run.setEnabled(True), QMessageBox.information(self, "完成", "任务结束")])
        self.worker.start()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = NCMCommander()
    w.show()
    sys.exit(app.exec())
