import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QListWidget, QGroupBox, QMessageBox, QFileDialog,
                             QCheckBox, QProgressBar, QAbstractItemView, QTextEdit)  # <--- 补上了 QTextEdit
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

# 引入 mutagen 用于处理标签 (支持 m4a/mp4/mp3/flac)
try:
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.id3 import ID3, APIC, TALB, TPE2, TIT2, TRCK
    from mutagen.flac import FLAC, Picture
except ImportError:
    print("请先安装库: pip install mutagen")
    sys.exit()
class PackWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    def __init__(self, files, album_name, album_artist, cover_path, auto_track):
        super().__init__()
        self.files = files
        self.album_name = album_name
        self.album_artist = album_artist
        self.cover_path = cover_path
        self.auto_track = auto_track
    def run(self):
        total = len(self.files)
        self.log.emit(f"🚀 开始打包 {total} 首歌曲...")
        cover_data = None
        if self.cover_path and os.path.exists(self.cover_path):
            with open(self.cover_path, 'rb') as f:
                cover_data = f.read()
        for idx, file_path in enumerate(self.files):
            try:
                filename = os.path.basename(file_path)
                ext = os.path.splitext(filename)[1].lower()
                self.log.emit(f"正在处理 [{idx + 1}/{total}]: {filename}")
                track_num = idx + 1 if self.auto_track else None
                if ext == '.m4a' or ext == '.mp4':
                    self.tag_m4a(file_path, cover_data, track_num)
                elif ext == '.mp3':
                    self.tag_mp3(file_path, cover_data, track_num)
                elif ext == '.flac':
                    self.tag_flac(file_path, cover_data, track_num)
                self.progress.emit(int((idx + 1) / total * 100))
            except Exception as e:
                self.log.emit(f"❌ 错误: {filename} - {e}")
        self.finished.emit()
    def tag_m4a(self, path, cover_data, track_num):
        audio = MP4(path)
        # 写入专辑名
        if self.album_name:
            audio['\xa9alb'] = self.album_name
        # 写入专辑艺术家
        if self.album_artist:
            audio['aART'] = self.album_artist
        # 写入音轨号
        if track_num:
            # trkn 格式是 tuple: (track_num, total_tracks)
            audio['trkn'] = [(track_num, len(self.files))]
        # 写入封面
        if cover_data:
            # 自动检测格式
            fmt = MP4Cover.FORMAT_PNG if self.cover_path.lower().endswith('.png') else MP4Cover.FORMAT_JPEG
            audio['covr'] = [MP4Cover(cover_data, imageformat=fmt)]
        audio.save()
    def tag_mp3(self, path, cover_data, track_num):
        try:
            audio = ID3(path)
        except:
            audio = ID3()  
        if self.album_name:
            audio.add(TALB(encoding=3, text=self.album_name))
        if self.album_artist:
            audio.add(TPE2(encoding=3, text=self.album_artist))
        if track_num:
            audio.add(TRCK(encoding=3, text=f"{track_num}/{len(self.files)}"))
        if cover_data:
            mime = 'image/png' if self.cover_path.lower().endswith('.png') else 'image/jpeg'
            audio.add(APIC(
                encoding=3,
                mime=mime,
                type=3,  # 3 is for the cover image
                desc='Cover',
                data=cover_data
            ))
        audio.save(path)
    def tag_flac(self, path, cover_data, track_num):
        audio = FLAC(path)
        if self.album_name: audio['album'] = self.album_name
        if self.album_artist: audio['albumartist'] = self.album_artist
        if track_num:
            audio['tracknumber'] = str(track_num)
            audio['totaltracks'] = str(len(self.files))
        if cover_data:
            p = Picture()
            p.type = 3
            if self.cover_path.lower().endswith('.png'):
                p.mime = 'image/png'
            else:
                p.mime = 'image/jpeg'
            p.data = cover_data
            audio.clear_pictures()
            audio.add_picture(p)
        audio.save()
class AlbumPacker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apple Music Album Packer v1.1")
        self.setGeometry(300, 300, 600, 700)
        self.init_ui()
        self.apply_styles()
    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout()
        main.setLayout(layout)

        # 1. 列表区
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)  # 允许拖拽排序
        layout.addWidget(QLabel("🎶 歌曲列表 (可拖拽调整顺序，顺序将决定音轨号)"))
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加歌曲...")
        btn_add.clicked.connect(self.add_files)
        btn_clear = QPushButton("清空列表")
        btn_clear.clicked.connect(self.list_widget.clear)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)

        # 2. 专辑信息区
        meta_group = QGroupBox("💿 专辑信息")
        meta_layout = QVBoxLayout()

        # 专辑名
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("专辑名称:"))
        self.in_album = QLineEdit()
        self.in_album.setPlaceholderText("例如: B站精选收藏 2026")
        h1.addWidget(self.in_album)
        meta_layout.addLayout(h1)

        # 专辑艺术家
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("专辑艺人:"))
        self.in_artist = QLineEdit()
        self.in_artist.setPlaceholderText("例如: Various Artists (这能防止列表被打散)")
        h2.addWidget(self.in_artist)
        meta_layout.addLayout(h2)

        # 封面
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("封面图片:"))
        self.in_cover = QLineEdit()
        self.in_cover.setPlaceholderText("选择 jpg/png 图片...")
        btn_cover = QPushButton("浏览...")
        btn_cover.clicked.connect(self.sel_cover)
        h3.addWidget(self.in_cover)
        h3.addWidget(btn_cover)
        meta_layout.addLayout(h3)

        # 选项
        self.chk_track = QCheckBox("根据列表顺序自动写入音轨号 (1, 2, 3...)")
        self.chk_track.setChecked(True)
        meta_layout.addWidget(self.chk_track)

        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)

        # 3. 进度与日志
        self.pbar = QProgressBar()
        layout.addWidget(self.pbar)

        self.log_txt = QTextEdit()
        self.log_txt.setMaximumHeight(100)
        self.log_txt.setReadOnly(True)  
        layout.addWidget(self.log_txt)

        # 4. 执行按钮
        self.btn_run = QPushButton("📦 一键打包")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.start_packing)
        layout.addWidget(self.btn_run)
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频", "", "Audio (*.m4a *.mp3 *.flac *.mp4)")
        if files:
            for f in files:
                # 简单去重
                items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
                if f not in items:
                    self.list_widget.addItem(f)
    def sel_cover(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择封面", "", "Images (*.jpg *.png *.jpeg)")
        if f: self.in_cover.setText(f)

    def log(self, msg):
        self.log_txt.append(msg)
        self.log_txt.verticalScrollBar().setValue(self.log_txt.verticalScrollBar().maximum())

    def start_packing(self):
        count = self.list_widget.count()
        if count == 0:
            return QMessageBox.warning(self, "!", "列表是空的！")

        files = [self.list_widget.item(i).text() for i in range(count)]
        album = self.in_album.text().strip()
        artist = self.in_artist.text().strip()
        cover = self.in_cover.text().strip()

        if not album:
            return QMessageBox.warning(self, "!", "必须要填专辑名！")
        if not artist:
            res = QMessageBox.question(self, "?",
                                       "未填写专辑艺人，这可能导致专辑分散。\n建议填 'Various Artists'。\n是否继续？")
            if res == QMessageBox.StandardButton.No: return

        self.btn_run.setEnabled(False)
        self.worker = PackWorker(files, album, artist, cover, self.chk_track.isChecked())
        self.worker.log.connect(self.log)
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.finished.connect(lambda: [self.btn_run.setEnabled(True), QMessageBox.information(self, "完成",
                                                                                                     "打包完成！\n请将这些文件重新拖入 Apple Music。")])
        self.worker.start()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QWidget { color: #ffffff; font-size: 14px; }
            QListWidget { background-color: #333; border: 1px solid #555; padding: 5px; }
            QListWidget::item:selected { background-color: #e74c3c; }
            QLineEdit { background-color: #444; padding: 5px; border: 1px solid #555; }
            QPushButton { background-color: #555; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #666; }
            QGroupBox { border: 1px solid #555; margin-top: 10px; padding-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QProgressBar { border: 1px solid #555; text-align: center; }
            QProgressBar::chunk { background-color: #e74c3c; }
            QTextEdit { background-color: #333; border: 1px solid #555; }
        """)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AlbumPacker()
    w.show()

    sys.exit(app.exec())
