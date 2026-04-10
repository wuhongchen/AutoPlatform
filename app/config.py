"""
统一配置管理
使用 Pydantic Settings 管理所有配置
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    url: str = Field(default="sqlite:///data/db/autoplatform.db", description="数据库URL")
    echo: bool = Field(default=False, description="是否打印SQL")


class WechatConfig(BaseSettings):
    """微信公众号配置"""
    model_config = SettingsConfigDict(env_prefix="WECHAT_")
    
    appid: str = Field(default="", description="公众号AppID")
    secret: str = Field(default="", description="公众号AppSecret")
    author: str = Field(default="W 小龙虾", description="默认作者")


class AIConfig(BaseSettings):
    """AI模型配置"""
    model_config = SettingsConfigDict(env_prefix="AI_")
    
    provider: str = Field(default="auto", description="模型提供者")
    api_key: str = Field(default="", description="API密钥")
    endpoint: str = Field(default="https://ark.cn-beijing.volces.com/api/v3", description="API端点")
    model: str = Field(default="doubao-seed-2-0-pro-260215", description="模型ID")
    timeout: int = Field(default=60, description="请求超时")


class ImageConfig(BaseSettings):
    """图片生成配置"""
    model_config = SettingsConfigDict(env_prefix="IMAGE_")
    
    provider: str = Field(default="auto", description="图片提供者")
    api_key: str = Field(default="", description="API密钥")
    endpoint: str = Field(default="https://ark.cn-beijing.volces.com/api/v3", description="API端点")
    model: str = Field(default="doubao-seedream-5-0-260128", description="模型ID")
    size: str = Field(default="1280x720", description="图片尺寸")


class PipelineConfig(BaseSettings):
    """流水线配置"""
    model_config = SettingsConfigDict(env_prefix="PIPELINE_")
    
    role: str = Field(default="tech_expert", description="默认改写角色")
    model: str = Field(default="auto", description="默认改写模型")
    batch_size: int = Field(default=3, description="批处理大小")
    content_direction: str = Field(default="", description="内容方向")
    prompt_direction: str = Field(default="", description="提示词方向")
    wechat_direction: str = Field(default="", description="公众号方向")


class AppConfig(BaseSettings):
    """应用主配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__"
    )
    
    # 基础配置
    env: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="调试模式")
    
    # 路径配置
    project_root: Path = Field(default=Path(__file__).parent.parent, description="项目根目录")
    data_dir: Path = Field(default=Path("data"), description="数据目录")
    output_dir: Path = Field(default=Path("data/output"), description="输出目录")
    
    # 子配置
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    wechat: WechatConfig = Field(default_factory=WechatConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    
    # 功能开关
    auto_install: bool = Field(default=True, description="自动安装依赖")
    non_interactive: bool = Field(default=False, description="非交互模式")
    schema_check_enabled: bool = Field(default=True, description="启用表结构检查")
    schema_check_interval: int = Field(default=21600, description="表结构检查间隔")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = AppConfig()


def get_settings() -> AppConfig:
    """获取配置实例"""
    return settings
