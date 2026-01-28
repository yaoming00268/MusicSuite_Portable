import sys
import os
import subprocess
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QTextEdit, QGroupBox, QMessageBox,
                             QCheckBox, QComboBox)
from PyQt6.QtCore import QThread, pyqtSignal

class Worker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, files, save_dir, ncmdump_path, keep_cover, target_fmt):
        super().__init__()
        self.files = files
        self.save_dir = save_dir
        self.ncmdump_exe = ncmdump_path
        self.keep_cover = keep_cover
        self.target_fmt = target_fmt  # (alac, flac, mp3...)
        # 格式对应的后缀名映射
        self.ext_map = {
            'alac': '.m4a',
            'flac': '.flac',
            'mp3': '.mp3',
            'wav': '.wav',
            'ogg': '.ogg'
        }
        self.target_ext = self.ext_map.get(target_fmt, '.m4a')
    def run(self):
        self.log.emit(f"启动任务: 目标格式 [{self.target_fmt.upper()}]")
        total = len(self.files)
        for idx, file_path in enumerate(self.files):
            try:
                filename = os.path.basename(file_path)
                file_ext = os.path.splitext(filename)[1].lower()
                self.log.emit(f"\n[{idx + 1}/{total}] 处理: {filename}")
                if file_ext == '.ncm':
                    source_to_convert = self.process_ncm_decrypt(file_path, filename)
                    is_temp = True  # 标记为临时文件，转码后需删除
                else:
                    source_to_convert = file_path
                    is_temp = False
                if not source_to_convert: continue
                self.process_conversion(source_to_convert, filename, is_temp)
            except Exception as e:
                self.log.emit(f"异常跳过: {e}")
        self.finished.emit()
    def process_ncm_decrypt(self, file_path, filename):
        """解密并返回解密后的临时文件路径"""
        temp_ncm = os.path.join(self.save_dir, filename)
        shutil.copy2(file_path, temp_ncm)
        self.log.emit("[NCM] 正在解密...")
        cmd = [self.ncmdump_exe, temp_ncm]
        subprocess.run(cmd, capture_output=True, text=True)
        # 删除 NCM 副本
        try:
            os.remove(temp_ncm)
        except:
            pass
        #(ncmdump 通常输出 mp3 或 flac)
        base_name = os.path.splitext(filename)[0]
        decrypted_file = None
        for ext in [".flac", ".mp3", ".m4a", ".wav"]:
            candidate = os.path.join(self.save_dir, base_name + ext)
            if os.path.exists(candidate):
                decrypted_file = candidate
                break
        if not decrypted_file:
            self.log.emit("NCM 解密失败，未找到产物。")
            return None
        return decrypted_file
    def get_sample_rate(self, filepath):
        """获取音频采样率"""
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                   '-show_entries', 'stream=sample_rate', '-of',
                   'default=noprint_wrappers=1:nokey=1', filepath]
            # 隐藏窗口运行
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, startupinfo=startupinfo)
            return int(res.stdout.strip())
        except:
            return 44100 
    def process_conversion(self, source_path, original_filename, is_temp_file):
        # 构建输出路径
        base_name = os.path.splitext(original_filename)[0]
        final_path = os.path.join(self.save_dir, base_name + self.target_ext)
        # 检测采样率
        sample_rate = self.get_sample_rate(source_path)
        self.log.emit(f"🔍 采样率检测: {sample_rate} Hz")
        try:
            # 调用 FFmpeg
            self.convert_ffmpeg(source_path, final_path, sample_rate)
            self.log.emit(f"转换完成: {os.path.basename(final_path)}")
            # 清理临时文件
            if is_temp_file:
                try:
                    os.remove(source_path)
                except:
                    pass
        except Exception as e:
            self.log.emit(f"转码失败: {e}")
    def convert_ffmpeg(self, inp, out, sample_rate):
        cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', inp]
        # 音频流映射
        cmd.extend(['-map', '0:a'])
        # OGG 和 WAV 都不支持流式封面嵌入
        if self.keep_cover and self.target_fmt not in ['wav', 'ogg']:
            cmd.extend(['-map', '0:v?', '-c:v', 'mjpeg', '-disposition:v:0', 'attached_pic'])
        else:
            if self.target_fmt == 'ogg' and self.keep_cover:
                self.log.emit("⚠️ OGG 格式暂不支持保留封面，已自动移除以避免错误。")
            cmd.extend(['-vn'])  # 明确丢弃视频
        #MP3
        if self.target_fmt == 'mp3':
            # 使用 V0
            cmd.extend(['-c:a', 'libmp3lame', '-q:a', '0'])
        #OGG 
        elif self.target_fmt == 'ogg':
            cmd.extend(['-c:a', 'libvorbis', '-q:a', '6'])
        #FLAC
        elif self.target_fmt == 'flac':
            cmd.extend(['-c:a', 'flac'])
            # >48k 保持原样(或24bit)
            if sample_rate > 48000:
                self.log.emit("💎 检测到 Hi-Res，保留高位深")
            else:
                self.log.emit("💿 标准采样率，自动设为 16-bit (CD质量)")
                cmd.extend(['-sample_fmt', 's16'])
        #ALAC
        elif self.target_fmt == 'alac':
            cmd.extend(['-c:a', 'alac', '-f', 'ipod'])  # ipod 容器即 m4a
            if sample_rate <= 48000:
                self.log.emit("💿 标准采样率，自动优化为 16-bit ALAC")
                cmd.extend(['-sample_fmt', 's16p'])
            else:
                self.log.emit("💎 Hi-Res ALAC 模式")
        #WAV
        elif self.target_fmt == 'wav':
            cmd.extend(['-c:a', 'pcm_s16le', '-f', 'wav'])
        cmd.append(out)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(cmd, check=True, startupinfo=startupinfo)
class UniversalCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Music Commander v3.1 (Fix OGG)")
        self.setGeometry(100, 100, 650, 650)

        w = QWidget()
        self.setCentralWidget(w)
        layout = QVBoxLayout()
        w.setLayout(layout)
        self.ncmdump_path = os.path.join(os.getcwd(), "ncmdump.exe")
        lbl_status = QLabel()
        if os.path.exists(self.ncmdump_path):
            lbl_status.setText("ncmdump.exe 就绪")
            lbl_status.setStyleSheet("color: #00ff00; font-weight: bold;")
        else:
            lbl_status.setText("未检测到 ncmdump.exe (NCM 解密将跳过)")
            lbl_status.setStyleSheet("color: #ffcc00; font-weight: bold;")
        layout.addWidget(lbl_status)
        g1 = QGroupBox("1. 选择资源")
        l1 = QVBoxLayout()
        self.btn_files = QPushButton("添加文件 (NCM / FLAC / MP3 / WAV...)")
        self.btn_files.clicked.connect(self.sel_files)
        self.lbl_count = QLabel("等待添加...")
        l1.addWidget(self.btn_files)
        l1.addWidget(self.lbl_count)
        g1.setLayout(l1)
        layout.addWidget(g1)
        g2 = QGroupBox("2. 转换设置")
        l2 = QVBoxLayout()
        h_fmt = QHBoxLayout()
        h_fmt.addWidget(QLabel("目标格式:"))
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems([
            "ALAC - Apple Lossless (.m4a)",
            "FLAC - Free Lossless (.flac)",
            "MP3 - High Quality (.mp3)",
            "WAV - PCM (.wav)",
            "OGG - Vorbis (.ogg)"
        ])
        # 默认选 ALAC
        self.combo_fmt.setCurrentIndex(0)
        h_fmt.addWidget(self.combo_fmt)
        l2.addLayout(h_fmt)
        # 路径选择行
        h_path = QHBoxLayout()
        self.path_in = QLineEdit(os.path.join(os.getcwd(), 'Music_Converted'))
        btn_path = QPushButton("更改目录...")
        btn_path.clicked.connect(self.sel_path)
        h_path.addWidget(self.path_in)
        h_path.addWidget(btn_path)
        l2.addLayout(h_path)
        self.chk_cover = QCheckBox("尝试保留封面图片 (WAV/OGG 除外)")
        self.chk_cover.setChecked(True)
        l2.addWidget(self.chk_cover)
        l2.addWidget(QLabel("💡 智能逻辑: 若源文件采样率 ≤ 48kHz，无损格式将自动使用 16-bit 以节省空间。"))
        g2.setLayout(l2)
        layout.addWidget(g2)
        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        layout.addWidget(self.log_txt)
        self.btn_run = QPushButton("🚀 开始处理")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.start)
        self.btn_run.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.btn_run)
        self.files = []
        self.apply_styles()
    def sel_files(self):
        filters = "Audio Files (*.ncm *.flac *.mp3 *.wav *.ogg *.m4a);;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频文件", "", filters)
        if files:
            self.files = files
            self.lbl_count.setText(f"已装填 {len(files)} 个文件")
            self.log_txt.append(f"准备就绪: {len(files)} 个文件")
    def sel_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d: self.path_in.setText(d)

    def start(self):
        if not self.files: return QMessageBox.warning(self, "!", "请先选择文件")
        out_dir = self.path_in.text()
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        fmt_text = self.combo_fmt.currentText()
        target_fmt = fmt_text.split(' ')[0].lower()  # 取第一个单词并转小写

        self.btn_run.setEnabled(False)
        self.worker = Worker(self.files, out_dir, self.ncmdump_path,
                             self.chk_cover.isChecked(), target_fmt)
        self.worker.log.connect(self.log_txt.append)
        self.worker.finished.connect(
            lambda: [self.btn_run.setEnabled(True), QMessageBox.information(self, "完成", "所有任务已处理完毕!")])
        self.worker.start()
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QGroupBox { color: #00ddff; font-weight: bold; border: 1px solid #555; margin-top: 10px; padding-top: 15px; }
            QLabel, QCheckBox { color: #ccc; }
            QLineEdit, QTextEdit { background: #333; color: #fff; border: 1px solid #555; }
            QPushButton { background: #444; color: #fff; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background: #555; }
            QComboBox { background: #333; color: #fff; border: 1px solid #555; padding: 5px; }
            QComboBox::drop-down { border: 0px; }
        """)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = UniversalCommander()
    w.show()
    sys.exit(app.exec())
