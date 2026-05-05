from __future__ import annotations

import html
import re
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "bilibili-downloader"
SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
SUGGEST_API = "https://s.search.bilibili.com/main/suggest"

# 更完整的请求头，模拟真实浏览器
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# 生成随机 buvid（B站设备指纹）
def generate_buvid() -> str:
    import random
    import string
    chars = string.hexdigits.lower()
    return f"XX{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}-{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}{random.choice(chars)}infoc"

# 会话级别的 Cookie 缓存
_search_session: requests.Session | None = None
_last_search_time: float = 0

def get_search_session() -> requests.Session:
    """获取或创建带 Cookie 的搜索会话"""
    global _search_session
    if _search_session is None:
        _search_session = requests.Session()
        _search_session.headers.update(SEARCH_HEADERS)
        # 设置必要的 Cookie
        buvid = generate_buvid()
        _search_session.cookies.set("buvid3", buvid, domain=".bilibili.com")
        _search_session.cookies.set("buvid4", f"{buvid.split('-')[0]}-{buvid.split('-')[1]}", domain=".bilibili.com")
        _search_session.cookies.set("_uuid", f"{buvid.split('-')[0]}-{buvid.split('-')[1]}", domain=".bilibili.com")
        # 添加 fingerprint
        _search_session.cookies.set("b_nut", str(int(time.time())), domain=".bilibili.com")
        _search_session.cookies.set("b_lsid", generate_buvid()[:20], domain=".bilibili.com")
    return _search_session
TITLE_TAG_RE = re.compile(r"<[^>]+>")
SAFE_NAME_RE = re.compile(r'[\\/:*?"<>|]+')


app = FastAPI(title="Bilibili Downloader")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@dataclass
class DownloadJob:
    id: str
    title: str
    url: str
    output_dir: str
    file_name: str | None
    browser: str | None
    audio_only: bool = False
    status: str = "queued"
    progress: str = "Waiting"
    percent: float = 0.0
    filename: str | None = None
    error: str | None = None
    downloaded_path: str | None = None
    created_order: int = field(default=0)


class SearchResult(BaseModel):
    bvid: str
    title: str
    author: str
    description: str
    duration: str
    play: int | None
    pubdate: int | None
    url: str
    pic: str | None


class DownloadRequest(BaseModel):
    url: str
    title: str = Field(min_length=1, max_length=300)
    output_dir: str = Field(min_length=1)
    file_name: str | None = Field(default=None, max_length=200)
    cookies_browser: str | None = Field(default=None, max_length=20)
    audio_only: bool = Field(default=False)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    page: int
    page_size: int
    total: int
    has_more: bool


class JobResponse(BaseModel):
    id: str
    title: str
    status: str
    progress: str
    percent: float
    output_dir: str
    filename: str | None
    downloaded_path: str | None
    error: str | None


jobs: dict[str, DownloadJob] = {}
jobs_lock = threading.Lock()
job_counter = 0


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    clean = TITLE_TAG_RE.sub("", text)
    return html.unescape(clean).strip()


def sanitize_filename(name: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", name).strip().rstrip(".")
    return cleaned[:180] or "video"


def bilibili_search(keyword: str, page: int = 1, page_size: int = 12, order: str = "totalrank") -> dict:
    global _last_search_time

    # 限制请求频率，避免触发风控
    elapsed = time.time() - _last_search_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_search_time = time.time()

    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "order": order,  # totalrank(综合), click(播放量), pubdate(发布日期)
    }

    session = get_search_session()

    try:
        response = session.get(SEARCH_API, params=params, timeout=20)

        # 如果遇到 412 风控，尝试重建会话
        if response.status_code == 412 or "412" in response.text:
            global _search_session
            _search_session = None
            session = get_search_session()
            time.sleep(2)  # 等待一段时间再重试
            response = session.get(SEARCH_API, params=params, timeout=20)

        response.raise_for_status()

        # 检查是否返回了 HTML 错误页面
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise HTTPException(
                status_code=503,
                detail="B站搜索服务暂时不可用，请稍后再试（触发风控限制）"
            )

        payload = response.json()

        if payload.get("code") != 0:
            error_msg = payload.get("message", "未知错误")
            # 常见错误码处理
            if payload.get("code") == -400:
                raise HTTPException(status_code=400, detail=f"请求参数错误: {error_msg}")
            elif payload.get("code") == -412:
                raise HTTPException(status_code=503, detail="请求过于频繁，请稍后再试")
            else:
                raise HTTPException(status_code=502, detail=f"B站搜索失败: {error_msg}")

        data = payload.get("data", {})
        results = []
        for item in data.get("result", []):
            bvid = item.get("bvid")
            if not bvid:
                continue
            results.append(
                SearchResult(
                    bvid=bvid,
                    title=strip_html(item.get("title")),
                    author=item.get("author") or "",
                    description=strip_html(item.get("description")),
                    duration=item.get("duration") or "",
                    play=item.get("play"),
                    pubdate=item.get("pubdate"),
                    url=f"https://www.bilibili.com/video/{bvid}",
                    pic=item.get("pic"),
                )
            )

        # B站 API 的 numResults 始终返回 1000，不可靠
        # 改用实际返回结果数判断是否有更多数据
        result_count = len(results)
        has_more = result_count >= page_size

        return {
            "results": results,
            "page": page,
            "page_size": page_size,
            "total": result_count,  # 显示当前页结果数，而非不可靠的总数
            "has_more": has_more,
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="搜索超时，请稍后再试")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="网络连接失败，请检查网络")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索出错: {str(e)}")


def get_job(job_id: str) -> DownloadJob:
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def set_job_fields(job_id: str, **fields: Any) -> None:
    with jobs_lock:
        job = jobs[job_id]
        for key, value in fields.items():
            setattr(job, key, value)


def make_job_response(job: DownloadJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        title=job.title,
        status=job.status,
        progress=job.progress,
        percent=job.percent,
        output_dir=job.output_dir,
        filename=job.filename,
        downloaded_path=job.downloaded_path,
        error=job.error,
    )


def build_ydl_options(job: DownloadJob) -> dict[str, Any]:
    target_dir = Path(job.output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = sanitize_filename(job.file_name or job.title)

    options: dict[str, Any] = {
        "outtmpl": str(target_dir / f"{base_name}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    # 根据是否只下载音频选择不同格式
    if job.audio_only:
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        options["format"] = "bestvideo*+bestaudio/best"
        options["merge_output_format"] = "mp4"

    if job.browser and job.browser != "none":
        options["cookiesfrombrowser"] = (job.browser,)

    def progress_hook(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status == "downloading":
            total = payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0
            downloaded = payload.get("downloaded_bytes") or 0
            percent = round((downloaded / total) * 100, 1) if total else 0.0
            progress_text = payload.get("_percent_str", "").strip() or f"{percent}%"
            set_job_fields(
                job.id,
                status="downloading",
                percent=percent,
                progress=progress_text,
                filename=payload.get("filename"),
            )
        elif status == "finished":
            filename = payload.get("filename")
            set_job_fields(
                job.id,
                status="processing",
                percent=100.0,
                progress="Download finished, finalizing file",
                filename=filename,
            )

    options["progress_hooks"] = [progress_hook]
    return options


def run_download(job_id: str) -> None:
    job = get_job(job_id)
    set_job_fields(job.id, status="starting", progress="Preparing download")
    try:
        options = build_ydl_options(job)
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(job.url, download=True)
            final_path = ydl.prepare_filename(info)

        actual_path = Path(final_path)
        if actual_path.suffix.lower() != ".mp4":
            mp4_candidate = actual_path.with_suffix(".mp4")
            if mp4_candidate.exists():
                actual_path = mp4_candidate

        set_job_fields(
            job.id,
            status="completed",
            progress="Completed",
            percent=100.0,
            downloaded_path=str(actual_path),
            filename=actual_path.name,
            error=None,
        )
    except Exception as exc:
        set_job_fields(
            job.id,
            status="failed",
            progress="Failed",
            error=str(exc),
        )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/search", response_model=SearchResponse)
def search_videos(q: str, page: int = 1, order: str = "totalrank") -> SearchResponse:
    query = q.strip()
    if len(query) < 1:
        raise HTTPException(status_code=400, detail="请输入搜索关键词")
    result = bilibili_search(query, page=page, order=order)
    return SearchResponse(
        results=result["results"],
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        has_more=result["has_more"],
    )


@app.post("/api/download", response_model=JobResponse)
def create_download(request: DownloadRequest) -> JobResponse:
    global job_counter

    output_dir = Path(request.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = (DEFAULT_DOWNLOAD_DIR / output_dir).resolve()

    job_id = str(uuid.uuid4())
    with jobs_lock:
        job_counter += 1
        job = DownloadJob(
            id=job_id,
            title=request.title,
            url=request.url,
            output_dir=str(output_dir),
            file_name=request.file_name.strip() if request.file_name else None,
            browser=request.cookies_browser,
            audio_only=request.audio_only,
            created_order=job_counter,
        )
        jobs[job_id] = job

    thread = threading.Thread(target=run_download, args=(job_id,), daemon=True)
    thread.start()
    return make_job_response(job)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_download_job(job_id: str) -> JobResponse:
    return make_job_response(get_job(job_id))


@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    with jobs_lock:
        ordered = sorted(jobs.values(), key=lambda item: item.created_order, reverse=True)
    return [make_job_response(job) for job in ordered]
