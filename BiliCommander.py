import sys
import os
import subprocess
import time
import shutil
import yt_dlp
from datetime import datetime

try:
    import rookiepy
    HAS_ROOKIE = True
except ImportError:
    HAS_ROOKIE = False

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QRadioButton, QButtonGroup, QFileDialog, QTextEdit,
                             QGroupBox, QMessageBox, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal

def auto_renew_bili_cookies(target_file='bili.txt', logger=None):
    if not HAS_ROOKIE: return False, "缺少 rookiepy"

    # B站的核心域名
    domains = ["bilibili.com"]
    cookies = []
    source_used = "Unknown"

    try:
        if logger: logger.emit("尝试从 Chrome 提取...")
        cookies = rookiepy.chrome(domains)
        source_used = "Chrome"
    except Exception as e:
        if logger: logger.emit(f"Chrome 失败: {e}")
        try:
            if logger: logger.emit("尝试从 Edge 提取...")
            cookies = rookiepy.edge(domains)
            source_used = "Edge"
        except Exception as e2:
            if logger: logger.emit(f"Edge 失败: {e2}")
            try:
                if logger: logger.emit("尝试从 Firefox 提取...")
                cookies = rookiepy.firefox(domains)
                source_used = "Firefox"
            except Exception as e3:
                return False, f"所有浏览器均失败，请确保已在浏览器登录 Bilibili。"

    try:
        if not cookies: return False, "未找到 B站 Cookie"
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(f"# Generated at {datetime.now()} from {source_used}\n\n")
            for c in cookies:
                if isinstance(c, dict):
                    domain = c.get('domain', '')
                    path = c.get('path', '/')
                    secure = "TRUE" if c.get('secure', False) else "FALSE"
                    expires = c.get('expires', 0)
                    name = c.get('name', '')
                    value = c.get('value', '')
                else:
                    domain = getattr(c, 'domain', '')
                    path = getattr(c, 'path', '/')
                    secure = "TRUE" if getattr(c, 'secure', False) else "FALSE"
                    expires = getattr(c, 'expires', 0)
                    name = getattr(c, 'name', '')
                    value = getattr(c, 'value', '')

                if expires is None: expires = 0
                expiration = str(int(expires))
                flag = "TRUE" if domain.startswith('.') else "FALSE"
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")

        return True, f"成功从 {source_used} 刷新 ({len(cookies)} 条)"
    except Exception as e:
        return False, f"写入错误: {e}"

class BiliWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.cookie_filename = 'bili.txt'
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    class MyLogger:
        def __init__(self, signal): self.signal = signal

        def debug(self, msg): pass

        def info(self, msg): self.signal.emit(msg)

        def warning(self, msg): self.signal.emit(f"⚠️ {msg}")

        def error(self, msg): self.signal.emit(f"❌ {msg}")

    def run(self):
        self.log_signal.emit(f" [Bilibili] v4.0 全能版启动！")

        # 1. 初始 Cookie 检查
        if self.params['auto_cookie']:
            if HAS_ROOKIE:
                self.log_signal.emit(" 初始化 B站 Cookie...")
                success, msg = auto_renew_bili_cookies(self.cookie_filename, self.log_signal)
                if success:
                    self.log_signal.emit(f" {msg}")
                else:
                    self.log_signal.emit(f"⚠️ 初始化失败: {msg}")
            else:
                self.log_signal.emit("❌ 缺少 rookiepy，无法自动提取 Cookie")
        # 2. 侦察阶段
        video_queue = []
        try:
            self.log_signal.emit("🕵️‍♂️ 正在分析链接...")
            recon_opts = {
                'extract_flat': True,
                'ignoreerrors': True,
                'cookiefile': self.cookie_filename if os.path.exists(self.cookie_filename) else None,
                'user_agent': self.user_agent,
                'logger': self.MyLogger(self.log_signal),
                'nocheckcertificate': True
            }
            with yt_dlp.YoutubeDL(recon_opts) as ydl:
                info = ydl.extract_info(self.params['url'], download=False)
                if 'entries' in info:
                    entries = list(info['entries'])
                    self.log_signal.emit(f" 原始列表: {len(entries)} 条")
                    # 过滤无效视频
                    valid_entries = [e for e in entries if e is not None]
                    self.log_signal.emit(f" 有效任务: {len(valid_entries)} 条")
                    for e in valid_entries: video_queue.append(e)
                else:
                    video_queue.append(info)
        except Exception as e:
            self.log_signal.emit(f"💥 侦察失败: {e}")
            self.finished_signal.emit()
            return

        # 3. 下载阶段 
        total = len(video_queue)
        for idx, item in enumerate(video_queue):
            if item is None: continue

            try:
                target_url = item.get('url') or item.get('webpage_url')
                title = item.get('title', f'Unknown_{idx}')
                self.log_signal.emit(f"\n🎬 [{idx + 1}/{total}] 处理: {title}")

                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.process_single_video(target_url)
                        break
                    except yt_dlp.utils.DownloadError as e:
                        err_msg = str(e).lower()
                        # B站常见错误：403 Forbidden, 412 Precondition Failed, -404 
                        if "403" in err_msg or "412" in err_msg or "sign in" in err_msg:
                            self.log_signal.emit(f"🚨 权限/验证错误 (尝试 {attempt + 1}/{max_retries})")
                            if self.params['auto_cookie']:
                                self.log_signal.emit("💉 刷新 Cookie...")
                                success, msg = auto_renew_bili_cookies(self.cookie_filename, self.log_signal)
                                if success:
                                    self.log_signal.emit(f"✅ {msg}")
                                    time.sleep(3)
                                    continue
                            break
                        else:
                            self.log_signal.emit(f"❌ 下载错误: {e}")
                            break
                    except Exception as e:
                        self.log_signal.emit(f"💥 未知错误: {e}")
                        break
            except Exception as e_outer:
                self.log_signal.emit(f"⛔ 任务跳过: {e_outer}")
                continue
        self.finished_signal.emit()
    def process_single_video(self, url):
        ydl_opts = {
            'logger': self.MyLogger(self.log_signal),
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(self.params['save_dir'], '%(title)s.%(ext)s'),
            'writethumbnail': True,
            # B站封面通常无需转换
            'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}],
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'noplaylist': True,
            'cookiefile': self.cookie_filename if os.path.exists(self.cookie_filename) else None,
            'user_agent': self.user_agent,
            # 请求 HTML5 格式
            'extractor_args': {'bilibili': {'videoprofile': ['html5']}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 极速跳过逻辑
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)
            base = os.path.splitext(filename)[0]
            # 判断文件是否存在
            if self.params['mode'] == 'audio' and os.path.exists(base + ".m4a"):
                self.log_signal.emit("音频已存在")
                return
            if self.params['mode'] != 'audio' and os.path.exists(base + ".mp4"):
                self.log_signal.emit("视频已存在")
                if self.params['mode'] == 'both' and not os.path.exists(base + ".m4a"):
                    # 视频在但音频不在，只做后期处理
                    self.post_process(base + ".mp4", info)
                return
            self.log_signal.emit("开始下载...")
            ydl.download([url])
            if os.path.exists(base + ".mp4"):
                self.post_process(base + ".mp4", info)
    def post_process(self, video_path, info):
        # 提取上传者作为 artist
        artist = info.get('uploader', 'Bilibili Creator')
        self.process_media(video_path, info.get('title'), artist)
    def get_audio_sample_rate(self, filepath):
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate', '-of',
                   'default=noprint_wrappers=1:nokey=1', filepath]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return int(res.stdout.strip())
        except:
            return 48000
    def process_media(self, video_path, title, artist):
        base_path = os.path.splitext(video_path)[0]
        audio_path = base_path + ".m4a"
        cover = None
        for ext in ['.jpg', '.png', '.webp']:
            if os.path.exists(base_path + ext): cover = base_path + ext; break

        mode = self.params['mode']
        if mode in ['audio', 'both'] and not os.path.exists(audio_path):
            sr = self.get_audio_sample_rate(video_path)
            self.log_signal.emit(f"采样率: {sr} Hz")
            try:
                cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', video_path]
                if cover: cmd.extend(['-i', cover])
                cmd.extend(['-map', '0:a'])
                if cover: cmd.extend(['-map', '1', '-c:v:0', 'mjpeg', '-disposition:v:0', 'attached_pic'])

                # >48kHz 使用 ALAC s32p
                if sr > 48000:
                    self.log_signal.emit("💎 Hi-Res -> ALAC (32-bit)")
                    cmd.extend(['-c:a', 'alac', '-sample_fmt', 's32p'])
                else:
                    self.log_signal.emit("💿 标准 -> AAC 320k")
                    cmd.extend(['-c:a', 'aac', '-b:a', '320k', '-ac', '2'])

                cmd.extend(['-metadata', f'title={title}', '-metadata', f'artist={artist}'])
                cmd.extend(
                    ['-metadata', f'album={self.params["album_name"]}', '-metadata', 'album_artist=Bilibili Favorites'])
                cmd.extend(['-f', 'ipod', audio_path])
                subprocess.run(cmd, check=True)
                self.log_signal.emit(f"✅ 音频完成")
            except Exception as e:
                self.log_signal.emit(f"❌ 转换失败: {e}")

        if mode == 'audio':
            try:
                os.remove(video_path)
            except:
                pass
        if cover:
            try:
                os.remove(cover)
            except:
                pass

class BiliCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BiliCommander v4.0 (Ultimate)")
        self.setGeometry(100, 100, 720, 650)
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout()
        main.setLayout(layout)

        url_g = QGroupBox("Bilibili 链接")
        url_l = QVBoxLayout()
        self.url_in = QLineEdit()
        self.url_in.setPlaceholderText("粘贴视频/合集/收藏夹 URL...")
        url_l.addWidget(self.url_in)
        url_g.setLayout(url_l)
        layout.addWidget(url_g)

        # Cookie
        cookie_g = QGroupBox("身份验证 (会员/高清)")
        cookie_l = QVBoxLayout()
        self.chk_auto_cookie = QCheckBox("🔥 启用自动续命 (Chrome/Edge/Firefox)")
        self.chk_auto_cookie.setChecked(True)
        self.chk_auto_cookie.setToolTip("自动从浏览器读取登录状态，无需手动导出 cookie。")

        status_label = QLabel()
        if HAS_ROOKIE:
            status_label.setText("✅ rookiepy 就绪 (无需管理员即可读取 Edge/Firefox)")
            status_label.setStyleSheet("color: #00ff00;")
        else:
            status_label.setText("❌ 未检测到 rookiepy")
            status_label.setStyleSheet("color: #ff0000;")
            self.chk_auto_cookie.setEnabled(False)

        cookie_l.addWidget(self.chk_auto_cookie)
        cookie_l.addWidget(status_label)
        cookie_g.setLayout(cookie_l)
        layout.addWidget(cookie_g)

        save_g = QGroupBox("💾 仓库")
        save_l = QHBoxLayout()
        self.save_in = QLineEdit(r'G:\paqv')
        btn_b = QPushButton("浏览...")
        btn_b.clicked.connect(self.browse)
        save_l.addWidget(self.save_in)
        save_l.addWidget(btn_b)
        save_g.setLayout(save_l)
        layout.addWidget(save_g)

        set_l = QHBoxLayout()
        meta_g = QGroupBox("🏷️ 专辑")
        meta_vl = QVBoxLayout()
        self.album_in = QLineEdit("B站精选收藏")
        meta_vl.addWidget(self.album_in)
        meta_g.setLayout(meta_vl)

        mode_g = QGroupBox("⚙️ 模式")
        mode_hl = QHBoxLayout()
        self.rb_audio = QRadioButton("仅音频")
        self.rb_video = QRadioButton("仅视频")
        self.rb_both = QRadioButton("全都要")
        self.rb_both.setChecked(True)
        self.bg = QButtonGroup()
        self.bg.addButton(self.rb_audio)
        self.bg.addButton(self.rb_video)
        self.bg.addButton(self.rb_both)
        mode_hl.addWidget(self.rb_audio)
        mode_hl.addWidget(self.rb_video)
        mode_hl.addWidget(self.rb_both)
        mode_g.setLayout(mode_hl)

        set_l.addWidget(meta_g)
        set_l.addWidget(mode_g)
        layout.addLayout(set_l)

        self.log_txt = QTextEdit()
        self.log_txt.setReadOnly(True)
        layout.addWidget(self.log_txt)

        self.btn_run = QPushButton("🚀 执行任务")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.start)
        layout.addWidget(self.btn_run)
    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "选目录", self.save_in.text())
        if d: self.save_in.setText(d)
    def log(self, msg):
        self.log_txt.append(msg)
        self.log_txt.verticalScrollBar().setValue(self.log_txt.verticalScrollBar().maximum())
    def start(self):
        url = self.url_in.text().strip()
        if not url: return QMessageBox.warning(self, "!", "URL 为空")
        mode = 'both'
        if self.rb_audio.isChecked():
            mode = 'audio'
        elif self.rb_video.isChecked():
            mode = 'video'
        p = {
            'url': url, 'save_dir': self.save_in.text(),
            'mode': mode, 'album_name': self.album_in.text(),
            'auto_cookie': self.chk_auto_cookie.isChecked()
        }
        self.btn_run.setEnabled(False)
        self.log("--- BiliCommander v4.0 Ultimate ---")
        self.worker = BiliWorker(p)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(
            lambda: [self.btn_run.setEnabled(True), QMessageBox.information(self, "完成", "搞定!")])
        self.worker.start()
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QGroupBox { color: #00ddff; font-weight: bold; border: 1px solid #555; margin-top: 10px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit { background: #3d3d3d; color: #ffffff; border: 1px solid #555; padding: 5px; }
            QTextEdit { background: #1e1e1e; color: #00ff00; font-family: Consolas; border: 1px solid #555; }
            QPushButton { background: #e74c3c; color: white; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background: #c0392b; }
            QPushButton:disabled { background: #7f8c8d; }
            QLabel, QRadioButton, QCheckBox { color: white; }
        """)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = BiliCommander()
    w.show()

    sys.exit(app.exec())
