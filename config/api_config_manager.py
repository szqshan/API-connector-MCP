#!/usr/bin/env python3
"""
API配置管理器
负责加载和管理API配置信息
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class APIConfigManager:
    """API配置管理器类"""
    
    def __init__(self, config_file: str = "config/api_config.json"):
        self.config_file = config_file
        self.config_data = {}
        self._load_env_variables()
        self._load_config()
    
    def _load_env_variables(self):
        """加载环境变量"""
        try:
            # 尝试加载 .env 文件
            env_file = Path(".env")
            if env_file.exists():
                load_dotenv(env_file)
                logger.info("已加载 .env 文件")
            else:
                logger.info(".env 文件不存在，使用系统环境变量")
        except Exception as e:
            logger.warning(f"加载环境变量失败: {e}")
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                logger.error(f"API配置文件不存在: {self.config_file}")
                self.config_data = {"apis": {}, "default_settings": {}, "security": {}, "data_processing": {}}
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            # 处理环境变量替换
            self._resolve_environment_variables()
            
            logger.info(f"API配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"加载API配置文件失败: {e}")
            self.config_data = {"apis": {}, "default_settings": {}, "security": {}, "data_processing": {}}
    
    def _resolve_environment_variables(self):
        """解析配置中的环境变量引用"""
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str):
                # 查找 ${VAR_NAME} 格式的环境变量引用
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, obj)
                for var_name in matches:
                    env_value = os.getenv(var_name, '')
                    obj = obj.replace(f'${{{var_name}}}', env_value)
                return obj
            else:
                return obj
        
        self.config_data = replace_env_vars(self.config_data)
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """获取指定API的配置"""
        apis = self.config_data.get("apis", {})
        if api_name not in apis:
            logger.error(f"API配置不存在: {api_name}")
            return None
        
        config = apis[api_name].copy()
        
        # 检查是否启用
        if not config.get("enabled", True):
            logger.warning(f"API连接已禁用: {api_name}")
            return None
        
        return config
    
    def list_apis(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置的API"""
        apis = self.config_data.get("apis", {})
        result = {}
        
        for api_name, config in apis.items():
            # 只返回基本信息，不包含敏感数据
            result[api_name] = {
                "name": api_name,
                "base_url": config.get("base_url", ""),
                "description": config.get("description", ""),
                "enabled": config.get("enabled", True),
                "auth_type": config.get("auth_type", "none"),
                "endpoints_count": len(config.get("endpoints", {}))
            }
        
        return result
    
    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置"""
        return self.config_data.get("default_settings", {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1,
            "user_agent": "API_Connecter_MCP/1.0",
            "verify_ssl": True,
            "follow_redirects": True
        })
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return self.config_data.get("security", {
            "allowed_domains": [],
            "blocked_domains": [],
            "max_redirects": 5,
            "max_response_size": 10485760  # 10MB
        })
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """获取数据处理配置"""
        return self.config_data.get("data_processing", {
            "max_preview_size": 1000,
            "auto_detect_format": True,
            "default_encoding": "utf-8",
            "date_formats": ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]
        })
    
    def validate_api_config(self, api_name: str) -> tuple[bool, str, list]:
        """验证API配置"""
        try:
            config = self.get_api_config(api_name)
            if not config:
                return False, f"API配置不存在或已禁用: {api_name}", []
            
            errors = []
            suggestions = []
            
            # 检查必需字段
            required_fields = ["base_url"]
            for field in required_fields:
                if not config.get(field):
                    errors.append(f"缺少必需字段: {field}")
                    suggestions.append(f"请在配置中添加 {field} 字段")
            
            # 检查URL格式
            base_url = config.get("base_url", "")
            if base_url:
                try:
                    parsed = urlparse(base_url)
                    if not parsed.scheme or not parsed.netloc:
                        errors.append("base_url 格式无效")
                        suggestions.append("请确保 base_url 包含协议（http/https）和域名")
                except Exception:
                    errors.append("base_url 解析失败")
                    suggestions.append("请检查 base_url 格式是否正确")
            
            # 检查认证配置
            auth_type = config.get("auth_type", "none")
            if auth_type != "none":
                auth_config = config.get("auth", {})
                if not auth_config:
                    errors.append(f"认证类型为 {auth_type} 但缺少认证配置")
                    suggestions.append("请在配置中添加 auth 字段")
                else:
                    if auth_type == "api_key":
                        if not auth_config.get("key") and not auth_config.get("header_name"):
                            errors.append("API Key 认证缺少必要参数")
                            suggestions.append("请配置 key 和 header_name 参数")
                    elif auth_type == "bearer":
                        if not auth_config.get("token"):
                            errors.append("Bearer 认证缺少 token 参数")
                            suggestions.append("请配置 token 参数")
                    elif auth_type == "basic":
                        if not auth_config.get("username") or not auth_config.get("password"):
                            errors.append("Basic 认证缺少用户名或密码")
                            suggestions.append("请配置 username 和 password 参数")
            
            # 检查端点配置
            endpoints = config.get("endpoints", {})
            if not endpoints:
                errors.append("没有配置任何API端点")
                suggestions.append("请在 endpoints 字段中添加至少一个API端点")
            else:
                for endpoint_name, endpoint_config in endpoints.items():
                    if not isinstance(endpoint_config, dict):
                        errors.append(f"端点 {endpoint_name} 配置格式错误")
                        suggestions.append(f"请确保端点 {endpoint_name} 的配置是一个对象")
                        continue
                    
                    if not endpoint_config.get("path"):
                        errors.append(f"端点 {endpoint_name} 缺少 path 字段")
                        suggestions.append(f"请为端点 {endpoint_name} 添加 path 字段")
            
            if errors:
                return False, "; ".join(errors), suggestions
            else:
                return True, "API配置验证通过", []
        
        except Exception as e:
            logger.error(f"验证API配置失败: {e}")
            return False, f"配置验证失败: {str(e)}", ["请检查配置文件格式是否正确"]
    
    def add_api_config(self, api_name: str, config: Dict[str, Any]) -> bool:
        """添加API配置"""
        try:
            if "apis" not in self.config_data:
                self.config_data["apis"] = {}
            
            self.config_data["apis"][api_name] = config
            self._save_config()
            logger.info(f"API配置添加成功: {api_name}")
            return True
        except Exception as e:
            logger.error(f"添加API配置失败: {e}")
            return False
    
    def remove_api_config(self, api_name: str) -> bool:
        """删除API配置"""
        try:
            if "apis" in self.config_data and api_name in self.config_data["apis"]:
                del self.config_data["apis"][api_name]
                self._save_config()
                logger.info(f"API配置删除成功: {api_name}")
                return True
            else:
                logger.warning(f"API配置不存在: {api_name}")
                return False
        except Exception as e:
            logger.error(f"删除API配置失败: {e}")
            return False
    
    def update_api_config(self, api_name: str, config: Dict[str, Any]) -> bool:
        """更新API配置"""
        try:
            if "apis" not in self.config_data:
                self.config_data["apis"] = {}
            
            if api_name in self.config_data["apis"]:
                self.config_data["apis"][api_name].update(config)
            else:
                self.config_data["apis"][api_name] = config
            
            self._save_config()
            logger.info(f"API配置更新成功: {api_name}")
            return True
        except Exception as e:
            logger.error(f"更新API配置失败: {e}")
            return False
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建配置的副本，移除环境变量值（保留引用）
            config_to_save = self._restore_environment_references(self.config_data)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise
    
    def _restore_environment_references(self, obj):
        """恢复环境变量引用（用于保存配置时）"""
        # 这里可以实现将实际值转换回环境变量引用的逻辑
        # 目前简单返回原对象
        return obj
    
    def reload_config(self):
        """重新加载配置"""
        self._load_config()
        logger.info("API配置重新加载完成")
    
    def get_endpoint_config(self, api_name: str, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """获取指定端点的配置"""
        api_config = self.get_api_config(api_name)
        if not api_config:
            return None
        
        endpoints = api_config.get("endpoints", {})
        if endpoint_name not in endpoints:
            logger.error(f"端点不存在: {api_name}.{endpoint_name}")
            return None
        
        return endpoints[endpoint_name]
    
    def is_domain_allowed(self, url: str) -> bool:
        """检查域名是否被允许访问"""
        try:
            security_config = self.get_security_config()
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # 检查黑名单
            blocked_domains = security_config.get("blocked_domains", [])
            for blocked in blocked_domains:
                if domain == blocked.lower() or domain.endswith('.' + blocked.lower()):
                    return False
            
            # 检查白名单（如果配置了白名单）
            allowed_domains = security_config.get("allowed_domains", [])
            if allowed_domains:
                for allowed in allowed_domains:
                    if domain == allowed.lower() or domain.endswith('.' + allowed.lower()):
                        return True
                return False  # 配置了白名单但域名不在其中
            
            return True  # 没有配置白名单，且不在黑名单中
        
        except Exception as e:
            logger.error(f"检查域名权限失败: {e}")
            return False

# 创建全局实例
api_config_manager = APIConfigManager()