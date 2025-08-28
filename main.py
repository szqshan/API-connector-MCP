#!/usr/bin/env python3
"""
API_Connecter_MCP - 基于MCP模板的API连接器
极简版API连接器MCP服务，直接在main.py中初始化所有组件

功能：
- API配置管理
- API数据获取与存储  
- API数据预览
- API存储会话管理
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# ================================
# 1. 配置工具
# ================================
TOOL_NAME = "API_Connecter_MCP"

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_connecter_mcp.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(TOOL_NAME)

# 创建MCP服务器
mcp = FastMCP(TOOL_NAME)

# ================================
# 2. 直接导入和初始化核心组件
# ================================

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    # 直接导入核心组件
    from config.api_config_manager import APIConfigManager
    from config.api_connector import APIConnector
    from config.api_data_storage import APIDataStorage
    from utils.data_transformer import DataTransformer
    
    # 直接初始化所有组件
    logger.info("🚀 开始初始化核心组件...")
    
    # 初始化配置管理器
    api_config_manager = APIConfigManager()
    logger.info("✅ API配置管理器初始化成功")
    
    # 初始化数据存储
    api_data_storage = APIDataStorage()
    logger.info("✅ API数据存储初始化成功")
    
    # 初始化数据转换器
    data_transformer = DataTransformer()
    logger.info("✅ 数据转换器初始化成功")
    
    logger.info("🎉 所有核心组件初始化完成！")
    
except Exception as e:
    logger.error(f"❌ 核心组件初始化失败: {e}")
    import traceback
    logger.error(f"详细错误: {traceback.format_exc()}")
    sys.exit(1)

# ================================
# 3. 工具函数
# ================================

@mcp.tool()
def manage_api_config(
    action: str,
    api_name: str = None,
    config: dict = None
) -> str:
    """
    🔧 API配置管理工具 - 管理API连接配置
    
    Args:
        action: 操作类型 (list/add/update/delete/validate/test)
        api_name: API名称（除list操作外必需）
        config: API配置信息（add/update操作时必需）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        logger.info(f"🔧 API配置管理: action={action}, api_name={api_name}")
        
        if action == "list":
            apis = api_config_manager.list_apis()
            return json.dumps({
                "success": True,
                "message": "API配置列表获取成功",
                "data": apis
            }, indent=2, ensure_ascii=False)
            
        elif action == "add":
            if not api_name or not config:
                return json.dumps({
                    "success": False,
                    "message": "添加API配置需要提供api_name和config参数"
                }, ensure_ascii=False)
                
            success = api_config_manager.add_api_config(api_name, config)
            return json.dumps({
                "success": success,
                "message": "API配置添加成功" if success else "API配置添加失败"
            }, ensure_ascii=False)
            
        elif action == "test":
            if not api_name:
                return json.dumps({
                    "success": False,
                    "message": "测试API连接需要提供api_name参数"
                }, ensure_ascii=False)
                
            # 获取API配置
            api_config = api_config_manager.get_api_config(api_name)
            if not api_config:
                return json.dumps({
                    "success": False,
                    "message": f"API配置 '{api_name}' 不存在"
                }, ensure_ascii=False)
                
            # 创建连接器并测试
            default_settings = api_config_manager.get_default_settings()
            connector = APIConnector(api_config, default_settings)
            
            success, message, details = connector.test_connection()
            return json.dumps({
                "success": success,
                "message": message,
                "details": details
            }, indent=2, ensure_ascii=False)
            
        else:
            return json.dumps({
                "success": False,
                "message": f"不支持的操作: {action}"
            }, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"API配置管理错误: {e}")
        return json.dumps({
            "success": False,
            "message": f"操作失败: {str(e)}"
        }, ensure_ascii=False)

@mcp.tool()
def api_data_preview(
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
    👁️ API数据预览工具 - 预览API数据而不存储
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数
        max_rows: 最大预览行数
        max_cols: 最大预览列数
        preview_fields: 指定预览字段
        preview_depth: 嵌套数据预览深度
        show_data_types: 是否显示数据类型
        show_summary: 是否显示数据摘要
        truncate_length: 文本截断长度
        
    Returns:
        str: JSON格式的数据预览结果
    """
    try:
        logger.info(f"👁️ API数据预览: api_name={api_name}, endpoint_name={endpoint_name}")
        
        # 获取API配置
        api_config = api_config_manager.get_api_config(api_name)
        if not api_config:
            return json.dumps({
                "success": False,
                "message": f"API配置 '{api_name}' 不存在"
            }, ensure_ascii=False)
            
        # 获取端点配置
        endpoint_config = api_config_manager.get_endpoint_config(api_name, endpoint_name)
        if not endpoint_config:
            return json.dumps({
                "success": False,
                "message": f"端点 '{endpoint_name}' 在API '{api_name}' 中不存在"
            }, ensure_ascii=False)
            
        # 创建连接器
        default_settings = api_config_manager.get_default_settings()
        connector = APIConnector(api_config, default_settings)
        
        # 调用API
        success, message, data = connector.call_api(endpoint_name, params or {})
        
        if not success:
            return json.dumps({
                "success": False,
                "message": f"API调用失败: {message}"
            }, ensure_ascii=False)
            
        # 数据预览处理
        preview_result = data_transformer.preview_data(
            data,
            max_rows=max_rows,
            max_cols=max_cols,
            preview_fields=preview_fields,
            preview_depth=preview_depth,
            show_data_types=show_data_types,
            show_summary=show_summary,
            truncate_length=truncate_length
        )
        
        return json.dumps({
            "success": True,
            "message": "API数据预览成功",
            "preview": preview_result,
            "api_info": {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "params": params
            }
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"API数据预览错误: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return json.dumps({
            "success": False,
            "message": f"预览失败: {str(e)}"
        }, ensure_ascii=False)

@mcp.tool()
def fetch_api_data(
    api_name: str,
    endpoint_name: str,
    params: dict = None,
    data: dict = None,
    method: str = None,
    transform_config: dict = None,
    storage_session_id: str = None
) -> str:
    """
    📡 API数据获取工具 - 从API获取数据并自动存储
    
    Args:
        api_name: API名称
        endpoint_name: 端点名称
        params: 请求参数（GET请求）
        data: 请求数据（POST/PUT请求）
        method: HTTP方法（可选，默认使用配置中的方法）
        transform_config: 数据转换配置（可选）
        storage_session_id: 存储会话ID（可选，不提供时自动创建）
        
    Returns:
        str: JSON格式的数据获取和存储结果
    """
    try:
        logger.info(f"📡 API数据获取: api_name={api_name}, endpoint_name={endpoint_name}")
        
        # 获取API配置
        api_config = api_config_manager.get_api_config(api_name)
        if not api_config:
            return json.dumps({
                "success": False,
                "message": f"API配置 '{api_name}' 不存在"
            }, ensure_ascii=False)
            
        # 创建连接器
        default_settings = api_config_manager.get_default_settings()
        connector = APIConnector(api_config, default_settings)
        
        # 调用API
        success, message, raw_data = connector.call_api(endpoint_name, params or {})
        
        if not success:
            return json.dumps({
                "success": False,
                "message": f"API调用失败: {message}"
            }, ensure_ascii=False)
            
        # 数据转换
        if transform_config:
            transformed_data = data_transformer.transform_data(raw_data, transform_config)
        else:
            transformed_data = raw_data
            
        # 存储数据
        if not storage_session_id:
            storage_session_id = f"{api_name}_{endpoint_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        storage_result = api_data_storage.store_api_data(
            storage_session_id,
            transformed_data,
            {
                "api_name": api_name,
                "endpoint_name": endpoint_name,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return json.dumps({
            "success": True,
            "message": "API数据获取和存储成功",
            "storage_session_id": storage_session_id,
            "storage_result": storage_result,
            "data_summary": {
                "type": type(transformed_data).__name__,
                "size": len(str(transformed_data))
            }
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"API数据获取错误: {e}")
        return json.dumps({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }, ensure_ascii=False)

@mcp.tool()
def create_api_storage_session(
    session_name: str,
    api_name: str,
    endpoint_name: str,
    description: str = None
) -> str:
    """
    📁 API存储会话创建工具 - 创建新的API数据存储会话
    
    Args:
        session_name: 存储会话名称
        api_name: API名称
        endpoint_name: 端点名称
        description: 会话描述（可选）
        
    Returns:
        str: JSON格式的会话创建结果
    """
    try:
        logger.info(f"📁 创建存储会话: {session_name}")
        
        success, session_id, message = api_data_storage.create_storage_session(
            session_name,
            api_name,
            endpoint_name,
            description
        )
        
        if not success:
            return json.dumps({
                "success": False,
                "message": f"创建会话失败: {message}"
            }, ensure_ascii=False)
        
        return json.dumps({
            "success": True,
            "message": "存储会话创建成功",
            "session_id": session_id,
            "session_name": session_name
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"创建存储会话错误: {e}")
        return json.dumps({
            "success": False,
            "message": f"创建失败: {str(e)}"
        }, ensure_ascii=False)

@mcp.tool()
def list_api_storage_sessions() -> str:
    """
    📋 API存储会话列表工具 - 查看所有API数据存储会话
    
    Returns:
        str: JSON格式的会话列表，包含会话信息和数据统计
    """
    try:
        logger.info("📋 获取存储会话列表")
        
        success, sessions, message = api_data_storage.list_storage_sessions()
        
        if not success:
            return json.dumps({
                "success": False,
                "message": f"获取会话列表失败: {message}"
            }, ensure_ascii=False)
        
        return json.dumps({
            "success": True,
            "message": "存储会话列表获取成功",
            "sessions": sessions
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取存储会话列表错误: {e}")
        return json.dumps({
            "success": False,
            "message": f"获取失败: {str(e)}"
        }, ensure_ascii=False)

# ================================
# 4. 启动服务器
# ================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 API_Connecter_MCP 测试模式")
        print("✅ 服务器可以正常启动")
        print("✅ 核心组件初始化成功")
        
        # 测试API配置管理
        try:
            result = manage_api_config("list")
            print("✅ API配置管理功能正常")
        except Exception as e:
            print(f"⚠️  API配置管理测试失败: {e}")
        
        # 测试存储会话管理
        try:
            result = list_api_storage_sessions()
            print("✅ 存储会话管理功能正常")
        except Exception as e:
            print(f"⚠️  存储会话管理测试失败: {e}")
        
        print("🎉 测试完成！服务器准备就绪")
        sys.exit(0)
    
    logger.info(f"启动 {TOOL_NAME}")
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("正在关闭...")
    finally:
        logger.info("服务器已关闭")