# Bilibili Downloader

一个简洁的 B站视频下载器，支持搜索和下载 Bilibili 视频。

## 功能特性

- 🔍 关键词搜索 B站视频
- 📥 一键下载视频到本地
- 📊 实时显示下载进度
- 🍪 支持从浏览器导入 Cookies（下载会员视频）
- 🖥️ Web 界面操作简单

## 环境要求

- Python 3.11+
- ffmpeg（用于合并音视频）

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/cyberyear/bilibilidownload.git
cd bilibilidownload
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
winget install ffmpeg
```

或从 [ffmpeg官网](https://ffmpeg.org/download.html) 下载。

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

## 启动方式

### 方式一：Windows 脚本启动（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File E:\auto360\run_app.ps1
```

### 方式二：命令行启动

```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 方式三：桌面启动器（自动打开浏览器）

```bash
python3 desktop_launcher.py
```

启动后，在浏览器中访问：**http://localhost:8000**

## 使用说明

1. 在搜索框输入关键词，点击「搜索」
2. 在搜索结果中找到想要的视频，点击「下载这个视频」
3. 设置保存目录（默认为 `downloads`）
4. 可选择从 Chrome/Edge/Firefox 导入 Cookies（用于下载需要登录的视频）
5. 在「下载任务」区域查看下载进度

## 注意事项

- 部分视频需要登录才能下载，请选择你登录过 B站的浏览器导入 Cookies
- 会员视频需要大会员账号的 Cookies
- 请遵守 B站用户协议，仅下载你有权保存的内容
- 下载的视频仅供个人学习使用，请勿用于商业用途

## 技术栈

- **后端**: FastAPI + yt-dlp
- **前端**: 原生 HTML/CSS/JavaScript

## License

MIT
