"""DraftForge DOCX 字体合规检查库。"""
from .inspector import inspect, validate
from .model import FontSegment, Violation

__all__ = ["inspect", "validate", "FontSegment", "Violation"]
