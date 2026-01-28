(https://github.com/user-attachments/files/24898592/readme.txt)
这是一个全流程的音频/视频工程套件，它整合了从 资源获取 (B站/YouTube)，使用yt-dlp（https://github.com/yt-dlp/yt-dlp）到格式解密/转换（ncmd）(NCM/Smart Convert)，再到元数据整理 (Apple Music Packer) 的一站式工作流。
主要功能
BiliCommander 
极速下载：支持 4K 视频及 Hi-Res 无损音质提取。
集成 rookiepy，自动从 Chrome/Edge/Firefox 读取 Cookie，无缝解决“会员/高清”权限问题。
智能合并：下载后自动调用 FFmpeg 将音视频合并，并支持提取纯净音频 (ALAC/AAC)。
YouTube Commander （暂时不可用）
强力内核：基于 yt-dlp 开发版，支持最新的 YouTube 签名算法 (n-sig)。
反爬虫对抗：内置 Cookie 自动刷新机制和 Node.js 环境检测，有效防止 403 错误和限速。
格式修复：自动修复下载列表中的空指针错误，支持断点续传。
Universal Music Converter (网易云/通用转码)
NCM 解密：调用 ncmdump 对网易云音乐加密格式 (.ncm) 进行硬解密。
智能转码：
Hi-Res 保留：若源文件采样率 > 48kHz，自动保留高位深 (24-bit/32-bit)。
空间优化：若源文件为 CD 音质 (≤ 48kHz)，自动转换为 16-bit 以节省空间。
多格式支持：输出支持 ALAC (.m4a), FLAC, MP3, WAV 等，并智能处理封面嵌入问题。
Apple Album Packer (专辑打包器)
元数据编辑：批量修改专辑名、艺术家、封面图片。
自动音轨号：支持拖拽排序，根据列表顺序自动写入 Track Number (如 1/12, 2/12)，完美适配 Apple Music / iTunes 导入。
环境准备 (必读)！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
运行之前，请确保你的系统满足以下条件，并已下载必要的外部工具：
pip install PyQt6 yt-dlp mutagen rookiepy pyinstaller
(或者直接运行 build_zip.bat 自动安装)
外部工具 (必须放在项目根目录)
本套件依赖以下外部 .exe 工具，请自行下载并放入脚本同级目录：
ffmpeg.exe & ffprobe.exe: 用于音视频合并与转码(https://github.com/FFmpeg/FFmpeg)
ncmdump.exe: 用于 NCM 文件解密(https://github.com/taurusxin/ncmdump)
Node.js: (必须安装) 请前往 nodejs.org 下载安装 LTS 版本并重启电脑。YouTube依赖它来解密签名(https://github.com/nodejs/node)
快速启动
直接运行 
运行中控台脚本，它会自动检测并加载所有可用模块：python Launcher.py
Launcher.py 会尝试申请管理员权限，这是为了让 Cookie 提取功能正常工作。
其实也可以每个分别运行
双击运行 build_zip.bat。 该脚本会执行以下操作：
自动从 GitHub 拉取 yt-dlp 的最新 Master 分支（修复 YouTube 下载报错的关键）。
将所有 Python 脚本和依赖打包成独立的 MusicSuite_v3.0.exe。
自动将 EXE 和必要的 ffmpeg/ncmdump 工具打包成 ZIP 文件。
YouTube 下载提示 "Signature solving failed" 或 "n challenge failed"
这是因为 YouTube 更新了反爬算法。（所以依靠更新，可以自己关掉续命，自己从网站获取cookie（油管每隔一段时间换一次））
解决方法 1：运行 build_zip.bat，它包含强制更新命令：pip install ... force-reinstall ... master.zip。
解决方法 2：在 CMD 中运行 yt-dlp --rm-cache-dir 清除旧缓存。
解决方法 3：确保你已经安装了 Node.js！！！！！！！！
提示 "Chrome/Edge 提取失败" 或无法获取 Cookie？
请确保浏览器已关闭，或者没有被其他程序占用文件锁。
尝试以 管理员身份 运行 Launcher.py。
如果还是失败，请手动删除目录下的 youtube_cookies.txt 或 bili.txt 让程序重试。
为什么转码后的文件封面没了？
如果是转换成 OGG 或 WAV 格式，这些格式对内嵌封面的支持较差，程序会自动跳过封面写入以防报错。
建议使用 ALAC (.m4a)（aac也行） 或 FLAC 格式，但是不建议mp3。
