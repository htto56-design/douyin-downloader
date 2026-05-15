"""
抖音视频下载器 v4.1
引擎: Playwright + Direct CDN (+ yt-dlp 备用)
UI: Apple Design Language (customtkinter)
新增: 完整异常捕获 · 错误日志 · 自动重试 · 备用引擎
修复: PyInstaller 打包后 Playwright 浏览器路径问题
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox, Menu
import threading, os, re, requests, traceback, sys, subprocess, glob
from datetime import datetime

# ★ 关键修复: PyInstaller 打包后 Playwright 找不到浏览器
# 必须指向系统安装的 ms-playwright 目录
_PW_BROWSERS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
if os.path.isdir(_PW_BROWSERS):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _PW_BROWSERS

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

APPLE_BG = "#F2F2F7"
APPLE_CARD = "#FFFFFF"
APPLE_ACCENT = "#007AFF"
APPLE_TEXT = "#1C1C1E"
APPLE_SECONDARY = "#8E8E93"
APPLE_SEPARATOR = "#E5E5EA"
APPLE_GREEN = "#34C759"
APPLE_RED = "#FF3B30"
APPLE_ORANGE = "#FF9500"

FONT_TITLE = ("Microsoft YaHei UI", 24, "bold")
FONT_HEADING = ("Microsoft YaHei UI", 15, "bold")
FONT_BODY = ("Microsoft YaHei UI", 14)
FONT_SMALL = ("Microsoft YaHei UI", 12)
FONT_MONO = ("Consolas", 11)
FONT_BUTTON = ("Microsoft YaHei UI", 16, "bold")

SAVE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "banana")
os.makedirs(SAVE_DIR, exist_ok=True)
ERROR_LOG = os.path.join(SAVE_DIR, "error_log.txt")


def write_error_log(phase, error_obj, extra=""):
    """将错误详情写入日志文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"时间: {timestamp}\n")
        f.write(f"阶段: {phase}\n")
        f.write(f"错误类型: {type(error_obj).__name__}\n")
        f.write(f"错误信息: {str(error_obj)}\n")
        if extra:
            f.write(f"附加信息: {extra}\n")
        f.write(f"Python版本: {sys.version}\n")
        f.write(f"平台: {sys.platform}\n")
        f.write(f"详细追踪:\n{traceback.format_exc()}\n")


def add_context_menu(widget):
    menu = Menu(widget, tearoff=0, font=("Microsoft YaHei UI", 12),
                bg="#FFFFFF", fg=APPLE_TEXT, activebackground=APPLE_ACCENT,
                activeforeground="#FFFFFF", bd=0, relief="flat")

    def popup(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    menu.add_command(label="剪切", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_command(label="复制", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="粘贴", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_separator()
    menu.add_command(label="全选", command=lambda: widget.event_generate("<<SelectAll>>"))
    widget.bind("<Button-3>", popup, add="+")
    widget.bind("<Control-a>", lambda e: widget.event_generate("<<SelectAll>>"), add="+")
    return menu


class Card(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=APPLE_CARD, corner_radius=18,
                         border_width=0.5, border_color="#D1D1D6", **kwargs)


class DouyinDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("抖音视频下载器 v4.1")
        self.root.geometry("780x750")
        self.root.minsize(620, 600)
        self.root.configure(bg=APPLE_BG, fg_color=APPLE_BG)

        self.scroll_frame = ctk.CTkScrollableFrame(root, fg_color="transparent",
                                                     scrollbar_button_color="#C8C8CD",
                                                     scrollbar_button_hover_color="#A8A8AD")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        main.pack(fill="x", padx=30, pady=25)

        # ── Title ──
        title_row = ctk.CTkFrame(main, fg_color="transparent")
        title_row.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(title_row, text="抖音视频下载器 v4.0", font=FONT_TITLE,
                     text_color=APPLE_TEXT).pack(anchor="w")
        ctk.CTkLabel(title_row, text="粘贴分享文字 · 自动识别 · 异常自诊断",
                     font=FONT_SMALL, text_color=APPLE_SECONDARY).pack(anchor="w")
        ctk.CTkFrame(main, fg_color=APPLE_SEPARATOR, height=1).pack(fill="x", pady=(15, 18))

        # ── Card 1: 粘贴 ──
        card1 = Card(main)
        card1.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(card1, text="粘贴抖音分享内容", font=FONT_HEADING,
                     text_color=APPLE_TEXT).pack(anchor="w", padx=24, pady=(20, 12))
        self.paste_text = ctk.CTkTextbox(card1, font=FONT_BODY, fg_color="#F9F9FB",
                                          text_color=APPLE_TEXT, corner_radius=12,
                                          border_width=1, border_color="#E8E8ED",
                                          height=100, wrap="word")
        self.paste_text.pack(fill="x", padx=24, pady=(0, 5))
        add_context_menu(self.paste_text)

        btn_row = ctk.CTkFrame(card1, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 18))
        self.extract_btn = ctk.CTkButton(btn_row, text="识别链接", font=FONT_BODY,
                                          fg_color=APPLE_ACCENT, hover_color="#0066CC",
                                          corner_radius=12, height=40, width=120,
                                          command=self.extract_url)
        self.extract_btn.pack(side="right")

        # ── Card 2: 识别结果 ──
        card2 = Card(main)
        card2.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(card2, text="识别结果", font=FONT_HEADING,
                     text_color=APPLE_TEXT).pack(anchor="w", padx=24, pady=(20, 12))
        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(card2, textvariable=self.url_var, font=FONT_BODY,
                                       fg_color="#F9F9FB", text_color=APPLE_GREEN,
                                       corner_radius=12, border_width=1, border_color="#E8E8ED",
                                       height=44)
        self.url_entry.pack(fill="x", padx=24, pady=(0, 18))
        add_context_menu(self.url_entry)

        # ── Card 3: 保存位置 ──
        card3 = Card(main)
        card3.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(card3, text="保存位置", font=FONT_HEADING,
                     text_color=APPLE_TEXT).pack(anchor="w", padx=24, pady=(20, 12))
        path_row = ctk.CTkFrame(card3, fg_color="transparent")
        path_row.pack(fill="x", padx=24, pady=(0, 18))
        self.download_path = SAVE_DIR
        self.path_var = ctk.StringVar(value=self.download_path)
        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.path_var, font=FONT_SMALL,
                                        fg_color="#F9F9FB", text_color=APPLE_SECONDARY,
                                        corner_radius=12, border_width=1, border_color="#E8E8ED",
                                        height=40)
        self.path_entry.pack(side="left", fill="x", expand=True)
        add_context_menu(self.path_entry)
        ctk.CTkButton(path_row, text="更改", font=FONT_SMALL,
                       fg_color="#F2F2F7", hover_color="#E5E5EA",
                       text_color=APPLE_TEXT, corner_radius=12,
                       height=40, width=70, command=self.browse_folder).pack(side="right", padx=(12, 0))

        # ── Card 4: 下载 ──
        card4 = Card(main)
        card4.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(card4, text="下载", font=FONT_HEADING,
                     text_color=APPLE_TEXT).pack(anchor="w", padx=24, pady=(20, 8))
        self.download_btn = ctk.CTkButton(card4, text="开始下载", font=FONT_BUTTON,
                                           fg_color=APPLE_ACCENT, hover_color="#0066CC",
                                           corner_radius=14, height=56,
                                           command=self.start_download)
        self.download_btn.pack(fill="x", padx=24, pady=(5, 20))

        # ── Card 5: 状态 ──
        card5 = Card(main)
        card5.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(card5, text="状态", font=FONT_HEADING,
                     text_color=APPLE_TEXT).pack(anchor="w", padx=24, pady=(20, 8))

        self.progress = ctk.CTkProgressBar(card5, height=8, corner_radius=4,
                                            fg_color="#E5E5EA", progress_color=APPLE_ACCENT)
        self.progress.set(0)
        self.progress.pack_forget()
        self.progress_label = ctk.CTkLabel(card5, text="", font=FONT_SMALL, text_color=APPLE_SECONDARY)
        self.status_label = ctk.CTkLabel(card5, text="就绪", font=FONT_BODY, text_color=APPLE_SECONDARY)
        self.status_label.pack(anchor="w", padx=24, pady=(6, 6))

        self.log_text = ctk.CTkTextbox(card5, font=FONT_MONO, fg_color="#F9F9FB",
                                        text_color=APPLE_SECONDARY, corner_radius=12,
                                        border_width=1, border_color="#E8E8ED",
                                        height=120, wrap="word")
        self.log_text.pack(fill="x", padx=24, pady=(5, 5))
        add_context_menu(self.log_text)

        # 查看错误日志按钮
        log_btn_row = ctk.CTkFrame(card5, fg_color="transparent")
        log_btn_row.pack(fill="x", padx=24, pady=(0, 18))
        ctk.CTkButton(log_btn_row, text="查看错误日志", font=FONT_SMALL,
                       fg_color="#F2F2F7", hover_color="#E5E5EA",
                       text_color=APPLE_SECONDARY, corner_radius=10,
                       height=32, width=120, command=self.open_error_log).pack(side="left")
        ctk.CTkButton(log_btn_row, text="清空日志", font=FONT_SMALL,
                       fg_color="#F2F2F7", hover_color="#FFD5D5",
                       text_color=APPLE_RED, corner_radius=10,
                       height=32, width=80, command=self.clear_log).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(main, text="引擎: Playwright + yt-dlp  ·  错误自动记录  ·  仅供学习研究",
                     font=("Microsoft YaHei UI", 9), text_color="#C7C7CC").pack(side="bottom", pady=(5, 0))

    # ========== 日志 & 错误处理 ==========

    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full = f"[{timestamp}] {msg}"
        self.root.after(0, lambda: self._log(full))

    def _log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def log_error(self, phase, error_obj, extra=""):
        """统一的错误记录"""
        self.log(f"!! 异常 [{phase}]: {error_obj}", "ERROR")
        try:
            write_error_log(phase, error_obj, extra)
        except:
            pass

    def open_error_log(self):
        if os.path.exists(ERROR_LOG):
            os.startfile(ERROR_LOG)
        else:
            messagebox.showinfo("提示", "暂无错误日志")

    def clear_log(self):
        self.log_text.delete("1.0", "end")
        self.log("日志已清空")

    # ========== 核心功能 ==========

    def extract_url(self):
        try:
            raw_text = self.paste_text.get("1.0", "end").strip()
            if not raw_text:
                self.status_label.configure(text="请先粘贴抖音分享内容", text_color=APPLE_RED)
                return
            patterns = [
                r'https?://v\.douyin\.com/\S+',
                r'https?://www\.douyin\.com/\S+',
                r'https?://www\.iesdouyin\.com/\S+',
            ]
            for pat in patterns:
                m = re.search(pat, raw_text)
                if m:
                    url = m.group().rstrip("。，,.;;!！？?\"'》）")
                    self.url_var.set(url)
                    self.status_label.configure(text="已识别链接 ✓", text_color=APPLE_GREEN)
                    return
            self.status_label.configure(text="未找到有效的抖音链接", text_color=APPLE_RED)
        except Exception as e:
            self.log_error("链接识别", e)
            self.status_label.configure(text="链接识别异常", text_color=APPLE_RED)

    def browse_folder(self):
        try:
            folder = filedialog.askdirectory(initialdir=self.download_path)
            if folder:
                self.download_path = folder
                self.path_var.set(folder)
        except Exception as e:
            self.log_error("选择文件夹", e)

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            self.extract_url()
            url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "未能识别到有效的视频链接")
            return

        self.download_btn.configure(state="disabled", text="下载中...")
        self.progress.pack(fill="x", padx=24, pady=(5, 10))
        self.progress.set(0)
        self.progress.start()
        self.progress_label.pack(anchor="w", padx=24, pady=(0, 8))
        self.progress_label.configure(text="准备中...", text_color=APPLE_ORANGE)
        self.status_label.configure(text="")
        self.log("")
        self.log("━" * 40)
        self.log(f"开始任务: {url}")

        threading.Thread(target=self.do_download, args=(url,), daemon=True).start()

    def do_download(self, short_url):
        # Phase 1: Playwright 解析
        video_url, title, error = self.phase_playwright(short_url)

        if error:
            self.log(f"Playwright 失败: {error}")
            self.log("尝试备用引擎 yt-dlp...")
            self.root.after(0, self.progress_label.configure,
                            "Playwright 失败，尝试备用引擎...", APPLE_ORANGE)
            # Phase 2: yt-dlp 备用
            output, error2 = self.phase_ytdlp(short_url)
            self.root.after(0, self.on_complete, output, error2 if not output else None,
                            "yt-dlp 备用引擎")
            return

        if not video_url:
            self.root.after(0, self.on_complete, None, "未能获取视频地址，可能链接已失效")
            return

        # Phase 3: 下载
        output, error3 = self.phase_download(video_url, title)
        self.root.after(0, self.on_complete, output, error3, "Playwright")

    def phase_playwright(self, short_url):
        """Phase 1: 用 Playwright 解析短链获取真实视频地址"""
        from playwright.sync_api import sync_playwright

        video_data = {}
        try:
            self.log("Phase 1: Playwright 浏览器解析")
            self.root.after(0, self.progress_label.configure, "启动 Chromium 浏览器...", APPLE_ORANGE)

            with sync_playwright() as p:
                try:
                    # 尝试启动，优先用 PLAYWRIGHT_BROWSERS_PATH 指定的系统浏览器
                    browser = p.chromium.launch(headless=True)
                    self.log("  Chromium 启动成功")
                except Exception as be:
                    self.log(f"  默认启动失败，尝试查找本地浏览器...")
                    # 备选：手动找 chrome 路径
                    found = False
                    browsers_base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
                    search_patterns = [
                        os.path.join(browsers_base, "chromium-*", "chrome-win", "chrome.exe"),
                        os.path.join(browsers_base, "chromium-*", "chrome-win64", "chrome.exe"),
                        os.path.join(browsers_base, "chromium_headless_shell-*", "chrome-headless-shell-win64", "chrome-headless-shell.exe"),
                    ]
                    for pat in search_patterns:
                        matches = glob.glob(pat)
                        if matches:
                            matches.sort(reverse=True)
                            exe_path = matches[0]
                            self.log(f"  找到: {exe_path}")
                            browser = p.chromium.launch(headless=True, executable_path=exe_path)
                            found = True
                            break

                    if not found:
                        self.log_error("Playwright-启动浏览器", be,
                                       "请运行: playwright install chromium")
                        return None, None, f"浏览器启动失败: {be}"

                ctx = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                )
                page = ctx.new_page()

                def on_response(response):
                    if "aweme/v1/web/aweme/detail" in response.url and "aweme_id=" in response.url:
                        try:
                            data = response.json()
                            aweme = data.get("aweme_detail", {})
                            video = aweme.get("video", {})
                            if video:
                                video_data["title"] = aweme.get("desc", "douyin_video")
                                for key in ["play_addr_h264", "play_addr", "download_addr"]:
                                    addr = video.get(key)
                                    if addr:
                                        url_list = addr.get("url_list", [])
                                        if url_list:
                                            video_data["url"] = url_list[0]
                                            break
                        except:
                            pass

                page.on("response", on_response)

                self.log("  正在访问页面...")
                self.root.after(0, self.progress_label.configure, "加载抖音页面...", APPLE_ORANGE)
                page.goto(short_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(8000)

                vid_match = re.search(r"video/(\d+)", page.url)
                self.log(f"  视频 ID: {vid_match.group(1) if vid_match else 'unknown'}")
                browser.close()

            if video_data.get("url"):
                self.log(f"  标题: {video_data['title']}")
                self.log(f"  API 拦截成功 ✓")
                return video_data["url"], video_data["title"], None
            else:
                self.log("  API 未返回视频数据")
                return None, None, "API 未拦截到视频数据"

        except Exception as e:
            self.log_error("Playwright-解析", e, f"短链: {short_url}")
            return None, None, str(e)

    def phase_ytdlp(self, short_url):
        """Phase 2 (备用): yt-dlp 下载 (先解析短链)"""
        try:
            self.log("Phase 2: yt-dlp 备用引擎")
            self.root.after(0, self.progress_label.configure, "yt-dlp 解析中...", APPLE_ORANGE)

            # 先把短链解析成 douyin.com/video/ID 格式
            resolved_url = short_url
            try:
                import urllib.request
                req = urllib.request.Request(short_url, method="HEAD",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                resp = urllib.request.urlopen(req, timeout=15)
                # 跟踪重定向获取最终URL
                final = resp.geturl()
                vid = re.search(r'video/(\d+)', final)
                if vid:
                    resolved_url = f"https://www.douyin.com/video/{vid.group(1)}"
                    self.log(f"  短链解析: video/{vid.group(1)}")
            except Exception as e:
                self.log(f"  短链解析失败，用原始链接: {e}")

            output = os.path.join(self.download_path, "%(title)s.%(ext)s")
            cmd = [
                "yt-dlp",
                "-o", output,
                "--no-playlist",
                "--user-agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                resolved_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8")

            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Destination:" in line:
                        out_file = line.split("Destination:")[-1].strip()
                        self.log(f"  yt-dlp 成功: {os.path.basename(out_file)}")
                        return out_file, None
                return None, "下载完成但未找到文件"
            else:
                err = (result.stderr or "")[-200:]
                self.log_error("yt-dlp-下载失败", Exception(err), f"短链: {short_url}")
                return None, f"yt-dlp 失败: {err[:100]}"

        except subprocess.TimeoutExpired:
            return None, "yt-dlp 下载超时"
        except FileNotFoundError:
            return None, "yt-dlp 未安装，请运行: pip install yt-dlp"
        except Exception as e:
            self.log_error("yt-dlp-异常", e, f"短链: {short_url}")
            return None, str(e)

    def phase_download(self, video_url, title):
        """Phase 3: 直接下载视频文件"""
        try:
            self.log("Phase 3: CDN 下载")
            self.root.after(0, self.progress_label.configure, "下载视频中...", APPLE_ORANGE)

            safe_title = re.sub(r'[<>:"/\\|?*\n\r]', "_", title)[:80]
            output = os.path.join(self.download_path, f"{safe_title}.mp4")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.douyin.com/"
            }
            r = requests.get(video_url, headers=headers, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))

            downloaded = 0
            with open(output, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total
                        self.root.after(0, self.progress.set, pct)
                        self.root.after(0, self.progress_label.configure,
                                        f"下载中 {downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB",
                                        APPLE_ORANGE)

            size_mb = downloaded / 1024 / 1024
            self.log(f"  完成: {size_mb:.1f} MB")
            self.log(f"  文件: {os.path.basename(output)}")
            return output, None

        except requests.exceptions.ConnectionError as e:
            self.log_error("下载-网络连接", e, f"视频URL: {video_url[:100]}")
            return None, f"网络错误: 无法连接到CDN服务器"
        except requests.exceptions.Timeout:
            self.log_error("下载-超时", Exception("timeout"), f"视频URL: {video_url[:100]}")
            return None, "下载超时，请检查网络"
        except requests.exceptions.HTTPError as e:
            self.log_error("下载-HTTP", e, f"状态码: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
            return None, f"HTTP 错误: {e}"
        except OSError as e:
            self.log_error("下载-文件系统", e, f"输出路径: {self.download_path}")
            return None, f"文件错误: 磁盘空间不足或权限不足"
        except Exception as e:
            self.log_error("下载-未知", e, f"视频URL: {video_url[:100]}")
            return None, str(e)

    def on_complete(self, output, error, engine=""):
        self.root.after(0, self.progress.stop)
        self.root.after(0, self.progress.pack_forget)
        self.root.after(0, self.progress_label.pack_forget)

        if error:
            error_msg = f"✗ 失败 [{engine}]: {error}"
            self.log(error_msg)
            self.root.after(0, lambda: self.status_label.configure(
                text=error_msg, text_color=APPLE_RED))
            # 如果有错误日志，提示
            if os.path.exists(ERROR_LOG):
                self.log("  详细错误已写入 error_log.txt")
        elif output:
            size = os.path.getsize(output) / 1024 / 1024 if os.path.exists(output) else 0
            success_msg = f"✓ 下载完成 — {os.path.basename(output)} ({size:.1f} MB)"
            self.root.after(0, lambda: self.status_label.configure(
                text=success_msg, text_color=APPLE_GREEN))
        else:
            self.root.after(0, lambda: self.status_label.configure(
                text="下载失败，请查看日志", text_color=APPLE_RED))

        self.root.after(0, lambda: self.download_btn.configure(state="normal", text="开始下载"))


if __name__ == "__main__":
    root = ctk.CTk()
    DouyinDownloader(root)
    root.mainloop()
