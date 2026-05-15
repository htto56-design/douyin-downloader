# 抖音视频下载器

粘贴抖音分享的整段文字，自动识别链接并下载视频。

## 使用方法

1. 在抖音 App 中复制分享链接（整段文字）
2. 打开 `抖音视频下载器.exe`
3. 粘贴到输入框，点击「开始下载」
4. 视频自动保存到 `banana` 文件夹

## 引擎

- **主引擎**: Playwright（模拟真实浏览器访问，成功率最高）
- **备用引擎**: yt-dlp（自动切换）

## 安装依赖（开发者）

```bash
pip install customtkinter playwright requests
python -m playwright install chromium
```

## 打包为 exe

```bash
pyinstaller --onefile --windowed --name "抖音视频下载器" \
    --hidden-import customtkinter --hidden-import darkdetect \
    --hidden-import playwright --hidden-import playwright.sync_api \
    --hidden-import requests \
    --add-data "path/to/playwright:playwright" \
    --clean 源码.py
```

## 免责声明

本工具仅供学习研究使用，请勿用于侵犯他人版权。下载的视频请在 24 小时内删除。

## License

MIT
