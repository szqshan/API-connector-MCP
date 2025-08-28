#!/usr/bin/env python3
"""
API_Connecter_MCP - API管理核心模块

这个模块包含所有API管理相关的工具函数：
- manage_api_config: API配置管理
- fetch_api_data: API数据获取并自动存储
- api_data_preview: API数据预览
- create_api_storage_session: 创建API存储会话
- list_api_storage_sessions: 列出API存储会话
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# 设置日志
logger = logging.getLogger("API_Connecter_MCP.APIManager")

# 导入API相关模块
try:
    from config.api_config_manager import APIConfigManager
    from config.api_connector import APIConnector
    from config.api_data_storage import APIDataStorage
    from utils.data_transformer import DataTransformer
except ImportError as e:
    logger.warning(f"API模块导入失败: {e}")
    # 定义空的占位类
    class APIConfigManager:
        def list_apis(self): return {}
        def add_api_config(self, name, config): return False
        def remove_api_config(self, name): return False
        def reload_config(self): pass
        def test_api_connection(self, name): return False, "API配置管理器未初始化"
        def get_api_endpoints(self, name): return []
    
    class APIConnector:
        def test_api_connection(self, name): return False, "API连接器未初始化"
        def get_api_endpoints(self, name): return []
        def call_api(self, **kwargs): return False, None, "API连接器未初始化"
    
    class APIDataStorage:
        def create_storage_session(self, **kwargs): return False, None, "API存储未初始化"
        def store_api_data(self, **kwargs): return False, 0, "API存储未初始化"
        def list_storage_sessions(self): return False, [], "API存储未初始化"
        def get_stored_data(self, **kwargs): return False, None, "API存储未初始化"
    
    class DataTransformer:
        def transform_data(self, **kwargs): return False, None, "数据转换器未初始化"
        def get_data_summary(self, data): return False, None, "数据转换器未初始化"

# 初始化API管理器实例
try:
    api_config_manager = APIConfigManager()
    # APIConnector需要config参数，先用空配置初始化
    api_connector = None  # 延迟初始化
    api_data_storage = APIDataStorage()
    data_transformer = DataTransformer()
except Exception as e:
    logger.warning(f"API管理器初始化失败: {e}")
    api_config_manager = APIConfigManager()
    api_connector = None
    api_data_storage = APIDataStorage()
    data_transformer = DataTransformer()

# ================================
# API管理工具函数
# ================================

def manage_api_config_impl(
    action: str,
    api_name: str = None,
    config_data: dict = None
) -> str:
    """
    管理API配置
    
    Args:
        action: 操作类型 (list|test|add|remove|reload|get_endpoints)
        api_name: API名称
        config_data: API配置数据
    
    Returns:
        str: 操作结果
    """
    try:
        if action == "list":
            apis = api_config_manager.list_apis()
            if not apis:
                result = {
                    "status": "success",
                    "message": "当前没有配置任何API",
                    "data": {"apis": []}
                }
                return f"📋 API配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            api_list = list(apis.values())
            result = {
                "status": "success",
                "message": f"找到 {len(api_list)} 个API配置",
                "data": {"apis": api_list}
            }
            return f"📋 API配置列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "test":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "测试API连接需要提供api_name参数"
                }
                return f"❌ 测试失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success, message = api_connector.test_api_connection(api_name)
            result = {
                "status": "success" if success else "error",
                "message": message,
                "data": {"api_name": api_name, "connected": success}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API连接测试\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "add":
            if not api_name or not config_data:
                result = {
                    "status": "error",
                    "message": "添加API配置需要提供api_name和config_data参数"
                }
                return f"❌ 添加失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = api_config_manager.add_api_config(api_name, config_data)
            result = {
                "status": "success" if success else "error",
                "message": f"API配置 '{api_name}' {'添加成功' if success else '添加失败'}",
                "data": {"api_name": api_name}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API配置管理\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "remove":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "删除API配置需要提供api_name参数"
                }
                return f"❌ 删除失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            success = api_config_manager.remove_api_config(api_name)
            result = {
                "status": "success" if success else "error",
                "message": f"API配置 '{api_name}' {'删除成功' if success else '删除失败'}",
                "data": {"api_name": api_name}
            }
            status_icon = "✅" if success else "❌"
            return f"{status_icon} API配置管理\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "reload":
            api_config_manager.reload_config()
            result = {
                "status": "success",
                "message": "API配置重新加载完成"
            }
            return f"🔄 配置重载\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        elif action == "get_endpoints":
            if not api_name:
                result = {
                    "status": "error",
                    "message": "获取API端点需要提供api_name参数"
                }
                return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            endpoints = api_connector.get_api_endpoints(api_name)
            result = {
                "status": "success",
                "message": f"API '{api_name}' 有 {len(endpoints)} 个端点",
                "data": {"api_name": api_name, "endpoints": endpoints}
            }
            return f"📋 API端点列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        else:
            result = {
                "status": "error",
                "message": f"不支持的操作: {action}",
                "supported_actions": ["list", "test", "add", "remove", "reload", "get_endpoints"]
            }
            return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"管理API配置失败: {e}")
        result = {
            "status": "error",
            "message": f"管理API配置失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 操作失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def fetch_api_data_impl(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    data: dict = None,
    method: str = None,
    transform_config: dict = None,
    storage_session_id: str = None
) -> str:
    """
    从API获取数据并自动存储
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        data: 请求数据（POST/PUT）
        method: HTTP方法
        transform_config: 数据转换配置
        storage_session_id: 存储会话ID（可选，不提供时自动创建）
    
    Returns:
        str: 数据获取和存储结果
    """
    try:
        if not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "获取API数据需要提供api_name和endpoint_name参数"
            }
            return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取API连接器
        connector = _get_api_connector(api_name)
        if not connector:
            result = {
                "status": "error",
                "message": f"无法创建API连接器: {api_name}"
            }
            return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 调用API
        success, response_data, message = connector.call_api(
            endpoint_name,
            params or {},
            data=data,
            method=method
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"API调用失败: {message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ API调用失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 自动创建存储会话（如果未提供）
        if not storage_session_id:
            session_name = f"{api_name}_{endpoint_name}_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            create_success, auto_session_id, create_message = api_data_storage.create_storage_session(
                session_name=session_name,
                api_name=api_name,
                endpoint_name=endpoint_name,
                description=f"自动创建的存储会话 - {api_name}.{endpoint_name}"
            )
            
            if not create_success:
                result = {
                    "status": "error",
                    "message": f"自动创建存储会话失败: {create_message}"
                }
                return f"❌ 会话创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
            
            storage_session_id = auto_session_id
        
        # 存储数据
        store_success, stored_count, store_message = api_data_storage.store_api_data(
            session_id=storage_session_id,
            data=response_data,
            transform_config=transform_config
        )
        
        if not store_success:
            result = {
                "status": "error",
                "message": f"数据存储失败: {store_message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name,
                    "session_id": storage_session_id
                }
            }
            return f"❌ 存储失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        result = {
            "status": "success",
            "message": f"成功获取并存储了 {stored_count} 条数据",
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "session_id": storage_session_id,
                "stored_count": stored_count,
                "preview": response_data if isinstance(response_data, (dict, list)) and len(str(response_data)) < 1000 else "数据过大，请使用预览功能查看"
            }
        }
        return f"✅ 数据获取成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"获取API数据失败: {e}")
        result = {
            "status": "error",
            "message": f"获取API数据失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def _get_api_connector(api_name: str):
    """获取API连接器实例"""
    try:
        api_config = api_config_manager.get_api_config(api_name)
        if not api_config:
            logger.error(f"无法获取API配置: {api_name}")
            return None
        
        default_settings = api_config_manager.get_default_settings()
        connector = APIConnector(api_config, default_settings)
        return connector
    except Exception as e:
        logger.error(f"创建API连接器失败: {e}")
        return None

def api_data_preview_impl(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    max_rows: int = 10,
    max_cols: int = 10,
    preview_fields: list = None,
    preview_depth: int = 3,
    show_data_types: bool = True,
    show_summary: bool = True,
    truncate_length: int = 100
) -> str:
    """
    预览API数据（不存储）
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        max_rows: 最大显示行数
        max_cols: 最大显示列数
        preview_fields: 预览字段列表
        preview_depth: 预览深度
        show_data_types: 是否显示数据类型
        show_summary: 是否显示摘要
        truncate_length: 截断长度
    
    Returns:
        str: 预览结果
    """
    logger.info(f"🔍 开始API数据预览: api_name={api_name}, endpoint_name={endpoint_name}")
    try:
        if not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "预览API数据需要提供api_name和endpoint_name参数"
            }
            return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 获取API连接器
        connector = _get_api_connector(api_name)
        if not connector:
            result = {
                "status": "error",
                "message": f"无法创建API连接器: {api_name}"
            }
            return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 调用API
        success, response_data, message = connector.call_api(
            endpoint_name,
            params or {}
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"API调用失败: {message}",
                "data": {
                    "api_name": api_name,
                    "endpoint_name": endpoint_name
                }
            }
            return f"❌ API调用失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        # 生成预览
        preview_data = _generate_enhanced_preview(
            response_data,
            max_rows=max_rows,
            max_cols=max_cols,
            preview_fields=preview_fields,
            preview_depth=preview_depth,
            show_data_types=show_data_types,
            truncate_length=truncate_length
        )
        
        result = {
            "status": "success",
            "message": "API数据预览",
            "data": {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "preview": preview_data,
                "summary": {
                    "total_size": len(str(response_data)),
                    "data_type": type(response_data).__name__,
                    "preview_settings": {
                        "max_rows": max_rows,
                        "max_cols": max_cols,
                        "truncate_length": truncate_length
                    }
                } if show_summary else None
            }
        }
        return f"👁️ API数据预览\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"预览API数据失败: {e}")
        result = {
            "status": "error",
            "message": f"预览API数据失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 预览失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def create_api_storage_session_impl(
    session_name: str,
    api_name: str,
    endpoint_name: str,
    description: str = None
) -> str:
    """
    创建API存储会话
    
    Args:
        session_name: 会话名称
        api_name: API名称
        endpoint_name: 端点名称
        description: 会话描述
    
    Returns:
        str: 创建结果
    """
    try:
        if not session_name or not api_name or not endpoint_name:
            result = {
                "status": "error",
                "message": "创建存储会话需要提供session_name、api_name和endpoint_name参数"
            }
            return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        success, session_id, message = api_data_storage.create_storage_session(
            session_name=session_name,
            api_name=api_name,
            endpoint_name=endpoint_name,
            description=description
        )
        
        if not success:
            result = {
                "status": "error",
                "message": f"创建存储会话失败: {message}"
            }
            return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        result = {
            "status": "success",
            "message": f"存储会话 '{session_name}' 创建成功",
            "data": {
                "session_id": session_id,
                "session_name": session_name,
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "description": description
            }
        }
        return f"✅ 会话创建成功\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"创建存储会话失败: {e}")
        result = {
            "status": "error",
            "message": f"创建存储会话失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 创建失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

def list_api_storage_sessions_impl() -> str:
    """
    列出所有API存储会话
    
    Returns:
        str: 会话列表
    """
    try:
        success, sessions, message = api_data_storage.list_storage_sessions()
        
        if not success:
            result = {
                "status": "error",
                "message": f"获取存储会话列表失败: {message}"
            }
            return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        if not sessions:
            result = {
                "status": "success",
                "message": "当前没有任何存储会话",
                "data": {"sessions": []}
            }
            return f"📋 存储会话列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
        
        result = {
            "status": "success",
            "message": f"找到 {len(sessions)} 个存储会话",
            "data": {"sessions": sessions}
        }
        return f"📋 存储会话列表\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"
    
    except Exception as e:
        logger.error(f"获取存储会话列表失败: {e}")
        result = {
            "status": "error",
            "message": f"获取存储会话列表失败: {str(e)}",
            "error_type": type(e).__name__
        }
        return f"❌ 获取失败\n\n{json.dumps(result, indent=2, ensure_ascii=False)}"

# ================================
# 辅助函数
# ================================

def _generate_enhanced_preview(data, max_rows=10, max_cols=10, preview_fields=None, 
                             preview_depth=3, show_data_types=True, truncate_length=100) -> dict:
    """
    生成增强的数据预览
    """
    try:
        if data is None:
            return {"type": "null", "value": None}
        
        data_type = type(data).__name__
        
        if isinstance(data, dict):
            preview = {}
            keys = list(data.keys())[:max_cols] if preview_fields is None else preview_fields[:max_cols]
            
            for key in keys:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and len(value) > truncate_length:
                        preview[key] = value[:truncate_length] + "..."
                    elif isinstance(value, (dict, list)) and preview_depth > 0:
                        preview[key] = _generate_enhanced_preview(
                            value, max_rows, max_cols, None, preview_depth-1, show_data_types, truncate_length
                        )
                    else:
                        preview[key] = value
            
            return {
                "type": data_type,
                "value": preview,
                "total_keys": len(data),
                "shown_keys": len(preview)
            }
        
        elif isinstance(data, list):
            preview = []
            for i, item in enumerate(data[:max_rows]):
                if isinstance(item, str) and len(item) > truncate_length:
                    preview.append(item[:truncate_length] + "...")
                elif isinstance(item, (dict, list)) and preview_depth > 0:
                    preview.append(_generate_enhanced_preview(
                        item, max_rows, max_cols, preview_fields, preview_depth-1, show_data_types, truncate_length
                    ))
                else:
                    preview.append(item)
            
            return {
                "type": data_type,
                "value": preview,
                "total_items": len(data),
                "shown_items": len(preview)
            }
        
        else:
            # 基本数据类型
            value_str = str(data)
            if len(value_str) > truncate_length:
                value_str = value_str[:truncate_length] + "..."
            
            return {
                "type": data_type,
                "value": value_str if show_data_types else data
            }
    
    except Exception as e:
        logger.error(f"生成预览失败: {e}")
        return {
            "type": "error",
            "value": f"预览生成失败: {str(e)}"
        }

def init_api_manager_module():
    """
    初始化API管理模块
    """
    try:
        logger.info("API管理模块初始化完成")
    except Exception as e:
        logger.warning(f"API管理模块初始化失败: {e}")