import sys
import os
import ctypes  # <--- 新增库：用于调用 Windows 系统 API
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGridLayout,
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# ==========================================
# 🔧 动态导入模块 (静态导入版)
# ==========================================
try:
    from BiliCommander import BiliCommander

    HAS_BILI = True
except ImportError:
    BiliCommander = None
    HAS_BILI = False

try:
    from youtube import YouTubeCommander

    HAS_YT = True
except ImportError:
    YouTubeCommander = None
    HAS_YT = False

try:
    from wangyiyun2 import UniversalCommander

    HAS_NCM_V2 = True
except ImportError:
    UniversalCommander = None
    HAS_NCM_V2 = False

try:
    from applemusicpack import AlbumPacker

    HAS_PACKER = True
except ImportError:
    AlbumPacker = None
    HAS_PACKER = False

try:
    from wangyiyun import NCMCommander

    HAS_NCM_OLD = True
except ImportError:
    NCMCommander = None
    HAS_NCM_OLD = False

# ==========================================
# ⚙️ 配置区
# ==========================================
TOOLS_CONFIG = {
    "bili": {
        "class_obj": BiliCommander,
        "available": HAS_BILI,
        "name": "BiliCommander v4.0",
        "desc": "B站高清下载 / 自动 Cookie / 4K",
        "color": "#fb7299",
        "icon": "📺"
    },
    "youtube": {
        "class_obj": YouTubeCommander,
        "available": HAS_YT,
        "name": "YouTube Commander",
        "desc": "油管下载 / Node.js 加速 / 封面嵌入",
        "color": "#ff0000",
        "icon": "🔴"
    },
    "ncm_v2": {
        "class_obj": UniversalCommander,
        "available": HAS_NCM_V2,
        "name": "Universal Music v3.1",
        "desc": "NCM 解密 / 智能格式转换 (修复版)",
        "color": "#27ae60",
        "icon": "🎧"
    },
    "packer": {
        "class_obj": AlbumPacker,
        "available": HAS_PACKER,
        "name": "Apple Album Packer",
        "desc": "元数据编辑 / 封面打包 / 导入准备",
        "color": "#9b59b6",
        "icon": "📦"
    },
    "ncm_old": {
        "class_obj": NCMCommander,
        "available": HAS_NCM_OLD,
        "name": "NCM Commander (旧版)",
        "desc": "仅 NCM 解密 (备用)",
        "color": "#7f8c8d",
        "icon": "💾"
    }
}


class ToolButton(QPushButton):
    def __init__(self, key, config, parent_launcher):
        super().__init__()
        self.key = key
        self.config = config
        self.launcher = parent_launcher

        self.is_available = config['available']

        if self.is_available:
            self.setText(f"{config['icon']} {config['name']}\n{config['desc']}")
        else:
            self.setText(f"❌ {config['name']} (文件缺失)")
            self.setEnabled(False)

        self.setMinimumHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.on_click)
        self.apply_style(config['color'])

    def apply_style(self, color):
        if not self.is_available:
            bg_color = "#444"
            text_color = "#888"
            border = "#555"
        else:
            bg_color = color
            text_color = "white"
            border = color

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 2px solid {border};
                border-radius: 10px;
                text-align: left;
                padding-left: 20px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {bg_color}DD;
                margin-top: -2px;
            }}
            QPushButton:pressed {{
                background-color: #333;
                margin-top: 2px;
            }}
        """)

    def on_click(self):
        self.launcher.launch_tool(self.key, self.config)


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        title_extra = " (管理员模式)" if ctypes.windll.shell32.IsUserAnAdmin() else ""
        self.setWindowTitle(f"Music Production Suite - Central Hub{title_extra}")
        self.setGeometry(100, 100, 800, 600)
        self.active_windows = []
        self.init_ui()
        self.apply_main_style()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 标题头
        header = QLabel("🎵 音频工程控制台")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #ecf0f1; margin-bottom: 20px; letter-spacing: 2px;")
        layout.addWidget(header)

        # 权限提示
        if ctypes.windll.shell32.IsUserAnAdmin():
            perm_lbl = QLabel("✅ 已获取管理员权限 (Cookie 读取功能正常)")
            perm_lbl.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 14px;")
            perm_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(perm_lbl)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #555;")
        layout.addWidget(line)

        # 按钮网格
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # 第一行
        grid_layout.addWidget(self.create_label("📡 资源获取"), 0, 0, 1, 2)
        self.btn_bili = ToolButton("bili", TOOLS_CONFIG["bili"], self)
        self.btn_yt = ToolButton("youtube", TOOLS_CONFIG["youtube"], self)
        grid_layout.addWidget(self.btn_bili, 1, 0)
        grid_layout.addWidget(self.btn_yt, 1, 1)

        # 第二行
        grid_layout.addWidget(self.create_label("🔧 转码与整理"), 2, 0, 1, 2)
        self.btn_ncm = ToolButton("ncm_v2", TOOLS_CONFIG["ncm_v2"], self)
        self.btn_pack = ToolButton("packer", TOOLS_CONFIG["packer"], self)
        grid_layout.addWidget(self.btn_ncm, 3, 0)
        grid_layout.addWidget(self.btn_pack, 3, 1)

        # 第三行
        self.btn_old = ToolButton("ncm_old", TOOLS_CONFIG["ncm_old"], self)
        self.btn_old.setMinimumHeight(60)
        self.btn_old.setStyleSheet(self.btn_old.styleSheet() + "font-size: 14px;")
        grid_layout.addWidget(self.btn_old, 4, 0, 1, 2)

        layout.addLayout(grid_layout)
        layout.addStretch()

        # 底部状态
        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setStyleSheet("color: #777; font-size: 12px;")
        layout.addWidget(self.status_lbl)

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #bdc3c7; font-weight: bold; font-size: 14px; margin-top: 15px;")
        return lbl

    def launch_tool(self, key, config):
        self.status_lbl.setText(f"正在启动: {config['name']} ...")
        QApplication.processEvents()

        try:
            target_class = config['class_obj']
            if target_class:
                window = target_class()
                window.show()
                self.active_windows.append(window)
                self.status_lbl.setText(f"运行中: {config['name']}")
            else:
                QMessageBox.critical(self, "错误", f"无法初始化模块: {config['name']}")
                self.status_lbl.setText("启动失败")

        except Exception as e:
            QMessageBox.critical(self, "崩溃", f"启动时发生异常:\n{str(e)}")
            self.status_lbl.setText("发生错误")

    def apply_main_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QMessageBox { background-color: #2b2b2b; color: white; }
        """)


# ==========================================
# 🛡️ 强制管理员启动逻辑
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == "__main__":
    # 如果不是管理员，尝试重新以管理员身份启动自己
    if not is_admin():
        # 获取当前运行的可执行文件或脚本路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 EXE
            executable = sys.executable
            params = ""
        else:
            # 如果是 .py 脚本
            executable = sys.executable
            params = " ".join([f'"{arg}"' for arg in sys.argv])

        try:
            # 这里的 "runas" 是 Windows 申请管理员权限的关键词
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        except Exception as e:
            print(f"提权失败: {e}")

        # 退出当前的非管理员进程
        sys.exit()

    # 如果是管理员，正常启动
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec())