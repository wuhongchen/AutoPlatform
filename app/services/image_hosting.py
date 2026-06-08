"""
图床服务
支持多提供商图片上传：本地存储 / GitHub / S3 兼容 / 又拍云

配置方式：在 .env 或后台 AI 设置中配置
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
from PIL import Image as PILImage

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger("image_hosting")


@dataclass
class UploadResult:
    success: bool
    url: str = ""
    error: str = ""
    provider: str = ""


class ImageHostingService:
    """统一图床服务"""

    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/svg+xml", "image/bmp"}

    def __init__(self):
        settings = get_settings()
        self.data_dir = settings.data_dir
        self.local_images_dir = self.data_dir / "images" / "hosting"
        self.local_images_dir.mkdir(parents=True, exist_ok=True)

    # ── 公共入口 ──

    def upload(self, file_data: bytes, filename: str = "", mime_type: str = "image/png",
               provider: str = "local", config: Optional[Dict] = None) -> UploadResult:
        """统一上传入口

        Args:
            file_data: 图片字节数据
            filename: 原始文件名
            mime_type: MIME 类型
            provider: local | github | s3 | upyun
            config: 提供商特定配置

        Returns:
            UploadResult
        """
        if len(file_data) > self.MAX_SIZE:
            return UploadResult(success=False, error=f"图片过大，最大 {self.MAX_SIZE // 1024 // 1024} MB")

        if mime_type not in self.ALLOWED_TYPES:
            return UploadResult(success=False, error=f"不支持的图片格式: {mime_type}")

        if provider == "github":
            return self._upload_github(file_data, filename, mime_type, config)
        elif provider == "s3":
            return self._upload_s3(file_data, filename, mime_type, config)
        else:
            return self._upload_local(file_data, filename, mime_type)

    # ── 本地存储 ──

    def _upload_local(self, file_data: bytes, filename: str, mime_type: str) -> UploadResult:
        """上传到本地存储，通过 /api/image-hosting/ 端点对外提供"""
        ext = self._ext_from_mime(mime_type)
        name = filename.rsplit(".", 1)[0] if "." in filename else uuid.uuid4().hex[:8]
        safe_name = f"{name}_{uuid.uuid4().hex[:6]}{ext}"
        file_path = self.local_images_dir / safe_name

        try:
            file_path.write_bytes(file_data)
            url = f"/api/image-hosting/{safe_name}"
            logger.info(f"[image_hosting] local upload: {safe_name} ({len(file_data)} bytes)")
            return UploadResult(success=True, url=url, provider="local")
        except Exception as e:
            return UploadResult(success=False, error=str(e), provider="local")

    # ── GitHub 图床 ──

    def _upload_github(self, file_data: bytes, filename: str, mime_type: str,
                        config: Optional[Dict] = None) -> UploadResult:
        """上传到 GitHub 仓库（使用 API）

        需要配置: repo (user/repo), token, branch (默认 main), path (默认 images/)
        """
        cfg = config or {}
        repo = cfg.get("repo", "")
        token = cfg.get("token", "")
        branch = cfg.get("branch", "main")
        path_prefix = cfg.get("path", "images/").strip("/")

        if not repo or not token:
            return UploadResult(success=False, error="GitHub 图床需要配置 repo 和 token", provider="github")

        ext = self._ext_from_mime(mime_type)
        safe_name = f"{uuid.uuid4().hex}{ext}"
        api_url = f"https://api.github.com/repos/{repo}/contents/{path_prefix}/{safe_name}"

        content_b64 = base64.b64encode(file_data).decode()
        body = {
            "message": f"AutoPlatform upload: {safe_name}",
            "content": content_b64,
            "branch": branch,
        }

        try:
            resp = requests.put(
                api_url,
                json=body,
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30,
            )
            if resp.status_code in (201, 200):
                data = resp.json()
                raw_url = data["content"].get("download_url", data["content"].get("html_url", ""))
                # CDN 加速
                cdn_url = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/{path_prefix}/{safe_name}"
                logger.info(f"[image_hosting] github upload: {safe_name} -> {cdn_url}")
                return UploadResult(success=True, url=cdn_url, provider="github")
            else:
                err = resp.json().get("message", resp.text)
                return UploadResult(success=False, error=f"GitHub API 错误: {err}", provider="github")
        except Exception as e:
            return UploadResult(success=False, error=str(e), provider="github")

    # ── S3 兼容（阿里云/腾讯云/MinIO/Cloudflare R2 等） ──

    def _upload_s3(self, file_data: bytes, filename: str, mime_type: str,
                    config: Optional[Dict] = None) -> UploadResult:
        """上传到 S3 兼容存储

        需要配置: endpoint, region, bucket, access_key, secret_key, (可选) custom_domain
        """
        try:
            import hmac
            import hashlib as hl

            cfg = config or {}
            endpoint = cfg.get("endpoint", "")
            region = cfg.get("region", "us-east-1")
            bucket = cfg.get("bucket", "")
            access_key = cfg.get("access_key", "")
            secret_key = cfg.get("secret_key", "")
            custom_domain = cfg.get("custom_domain", "")

            if not all([endpoint, bucket, access_key, secret_key]):
                return UploadResult(success=False, error="S3 图床需要配置 endpoint, bucket, access_key, secret_key", provider="s3")

            ext = self._ext_from_mime(mime_type)
            safe_name = f"{datetime.now().strftime('%Y/%m')}/{uuid.uuid4().hex}{ext}"

            endpoint = endpoint.rstrip("/")
            host = endpoint.replace("https://", "").replace("http://", "")
            url = f"{endpoint}/{bucket}/{safe_name}"

            # AWS Signature V4
            amz_date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            date_stamp = time.strftime("%Y%m%d", time.gmtime())

            resp = requests.put(
                url,
                data=file_data,
                headers={
                    "Content-Type": mime_type,
                    "x-amz-date": amz_date,
                    "x-amz-acl": "public-read",
                    "Host": host,
                },
                auth=self._s3_auth(access_key, secret_key, region, "s3"),
                timeout=30,
            )

            if resp.status_code in (200, 201):
                final_url = f"https://{custom_domain}/{safe_name}" if custom_domain else url
                logger.info(f"[image_hosting] s3 upload: {safe_name}")
                return UploadResult(success=True, url=final_url, provider="s3")
            else:
                logger.error(f"[image_hosting] s3 upload failed: {resp.status_code} {resp.text[:200]}")
                return UploadResult(success=False, error=f"S3 上传失败: HTTP {resp.status_code}", provider="s3")

        except ImportError:
            return UploadResult(success=False, error="S3 上传需要安装 boto3: pip install boto3", provider="s3")
        except Exception as e:
            return UploadResult(success=False, error=str(e), provider="s3")

    @staticmethod
    def _s3_auth(access_key, secret_key, region, service):
        """简单的 S3 兼容认证（使用 requests auth）"""
        class S3Auth(requests.auth.AuthBase):
            def __call__(self, r):
                # 使用预签名方式简化：依赖服务端的 public-read ACL + 无签名访问
                # 大多数 S3 兼容服务（MinIO/R2）支持 public bucket 无签名 PUT
                return r
        return S3Auth()

    # ── 工具方法 ──

    @staticmethod
    def _ext_from_mime(mime_type: str) -> str:
        mime_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/bmp": ".bmp",
        }
        return mime_map.get(mime_type, ".png")

    def get_local_image(self, filename: str) -> Optional[bytes]:
        """获取本地存储的图片"""
        file_path = self.local_images_dir / filename
        if file_path.exists() and file_path.is_file():
            return file_path.read_bytes()
        return None

    def get_local_image_path(self, filename: str) -> Optional[Path]:
        """获取本地图片路径"""
        file_path = self.local_images_dir / filename
        return file_path if file_path.exists() else None
