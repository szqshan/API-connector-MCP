"""
API Connecter MCP - 基于MCP协议的通用API连接器

这是一个极简化的API连接器MCP服务，让AI能够通过API连接万物。
支持API配置管理、数据获取、数据存储和转换等功能。
"""

__version__ = "1.0.0"
__author__ = "szqshan"
__email__ = "szqshan@example.com"
__description__ = "Universal API Connector MCP for AI applications"
__license__ = "MIT"

# 导出主要功能
from .main import *

# 版本信息
VERSION = __version__