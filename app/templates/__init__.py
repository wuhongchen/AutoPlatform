"""
发布模板系统
提供多种排版风格供用户选择
"""

from .base import BaseTemplate, TemplateRegistry
from .default import DefaultTemplate
from .minimal import MinimalTemplate
from .tech import TechTemplate
from .business import BusinessTemplate

# 注册所有模板
TemplateRegistry.register("default", DefaultTemplate)
TemplateRegistry.register("minimal", MinimalTemplate)
TemplateRegistry.register("tech", TechTemplate)
TemplateRegistry.register("business", BusinessTemplate)

__all__ = [
    "BaseTemplate",
    "TemplateRegistry",
    "DefaultTemplate",
    "MinimalTemplate", 
    "TechTemplate",
    "BusinessTemplate",
]
