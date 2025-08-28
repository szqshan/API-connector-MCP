#!/usr/bin/env python3
"""
API连接器
负责HTTP请求和响应处理
"""

import requests
import json
import time
import logging
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

class APIConnector:
    """API连接器类"""
    
    def __init__(self, config: Dict[str, Any], default_settings: Dict[str, Any] = None):
        self.config = config
        self.default_settings = default_settings or {}
        self.session = None
        self._setup_session()
    
    def _setup_session(self):
        """设置HTTP会话"""
        self.session = requests.Session()
        
        # 设置重试策略
        max_retries = self.default_settings.get("max_retries", 3)
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认headers
        user_agent = self.default_settings.get("user_agent", "API_Connecter_MCP/1.0")
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json, application/xml, text/plain, */*",
            "Accept-Encoding": "gzip, deflate"
        })
        
        # 设置SSL验证
        verify_ssl = self.default_settings.get("verify_ssl", True)
        self.session.verify = verify_ssl
        
        # 设置重定向
        follow_redirects = self.default_settings.get("follow_redirects", True)
        if not follow_redirects:
            self.session.max_redirects = 0
    
    def test_connection(self) -> tuple[bool, str, Dict[str, Any]]:
        """测试API连接"""
        try:
            base_url = self.config.get("base_url")
            if not base_url:
                return False, "缺少base_url配置", {}
            
            # 尝试连接到base_url
            timeout = self.default_settings.get("timeout", 30)
            
            start_time = time.time()
            response = self.session.get(base_url, timeout=timeout)
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)  # 毫秒
            
            connection_info = {
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "headers": dict(response.headers),
                "url": response.url,
                "encoding": response.encoding
            }
            
            if response.status_code < 400:
                return True, f"连接成功 (状态码: {response.status_code}, 响应时间: {response_time}ms)", connection_info
            else:
                return False, f"连接失败 (状态码: {response.status_code})", connection_info
        
        except requests.exceptions.Timeout:
            return False, "连接超时", {"error": "timeout"}
        except requests.exceptions.ConnectionError as e:
            return False, f"连接错误: {str(e)}", {"error": "connection_error"}
        except Exception as e:
            return False, f"测试连接失败: {str(e)}", {"error": "unknown_error"}
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证头"""
        headers = {}
        auth_type = self.config.get("auth_type", "none")
        auth_config = self.config.get("auth", {})
        
        if auth_type == "api_key":
            key = auth_config.get("key")
            header_name = auth_config.get("header_name", "X-API-Key")
            if key:
                headers[header_name] = key
        
        elif auth_type == "bearer":
            token = auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "basic":
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        elif auth_type == "custom":
            custom_headers = auth_config.get("headers", {})
            headers.update(custom_headers)
        
        return headers
    
    def _build_request_params(self, endpoint_config: Dict[str, Any], 
                            params: Dict[str, Any] = None) -> Dict[str, Any]:
        """构建请求参数"""
        request_params = {
            "method": endpoint_config.get("method", "GET").upper(),
            "url": urljoin(self.config["base_url"], endpoint_config["path"]),
            "timeout": self.default_settings.get("timeout", 30)
        }
        
        # 添加认证头
        headers = self._build_auth_headers()
        
        # 添加端点特定的头
        endpoint_headers = endpoint_config.get("headers", {})
        headers.update(endpoint_headers)
        
        if headers:
            request_params["headers"] = headers
        
        # 处理参数
        if params:
            method = request_params["method"]
            if method in ["GET", "DELETE"]:
                request_params["params"] = params
            else:
                # POST, PUT, PATCH等方法
                content_type = headers.get("Content-Type", "application/json")
                if "application/json" in content_type:
                    request_params["json"] = params
                elif "application/x-www-form-urlencoded" in content_type:
                    request_params["data"] = params
                else:
                    request_params["data"] = params
        
        return request_params
    
    def call_api(self, endpoint_name: str, params: Dict[str, Any] = None) -> tuple[bool, str, Any]:
        """调用API端点"""
        try:
            # 获取端点配置
            endpoints = self.config.get("endpoints", {})
            if endpoint_name not in endpoints:
                return False, f"端点不存在: {endpoint_name}", None
            
            endpoint_config = endpoints[endpoint_name]
            
            # 构建请求参数
            request_params = self._build_request_params(endpoint_config, params)
            
            # 发送请求
            success, message, response_data = self._send_request_with_retry(**request_params)
            
            if success:
                logger.info(f"API调用成功: {endpoint_name}")
                return True, "API调用成功", response_data
            else:
                logger.error(f"API调用失败: {endpoint_name} - {message}")
                return False, message, response_data
        
        except Exception as e:
            error_msg = f"API调用异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def _send_request_with_retry(self, **kwargs) -> tuple[bool, str, Any]:
        """发送带重试的请求"""
        max_retries = self.default_settings.get("max_retries", 3)
        retry_delay = self.default_settings.get("retry_delay", 1)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(**kwargs)
                
                # 解析响应
                success, message, data = self._parse_response(response)
                
                if success or response.status_code < 500:
                    # 成功或客户端错误（不重试）
                    return success, message, data
                else:
                    # 服务器错误，可能需要重试
                    last_error = message
                    if attempt < max_retries:
                        logger.warning(f"请求失败，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries + 1}): {message}")
                        time.sleep(retry_delay)
                        continue
            
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                if attempt < max_retries:
                    logger.warning(f"请求超时，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries + 1})")
                    time.sleep(retry_delay)
                    continue
            
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误: {str(e)}"
                if attempt < max_retries:
                    logger.warning(f"连接错误，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}")
                    time.sleep(retry_delay)
                    continue
            
            except Exception as e:
                last_error = f"请求异常: {str(e)}"
                break  # 其他异常不重试
        
        return False, last_error or "请求失败", None
    
    def _parse_response(self, response: requests.Response) -> tuple[bool, str, Any]:
        """解析响应"""
        try:
            # 检查状态码
            if response.status_code >= 400:
                error_msg = f"HTTP错误 {response.status_code}"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg += f": {error_data.get('message', error_data.get('error', ''))}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                return False, error_msg, {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text[:1000]  # 限制错误内容长度
                }
            
            # 解析响应内容
            content_type = response.headers.get("Content-Type", "").lower()
            
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": response.url,
                "encoding": response.encoding,
                "content_type": content_type
            }
            
            if "application/json" in content_type:
                try:
                    response_data["data"] = response.json()
                    response_data["format"] = "json"
                except json.JSONDecodeError:
                    response_data["data"] = response.text
                    response_data["format"] = "text"
                    response_data["parse_error"] = "JSON解析失败"
            
            elif "application/xml" in content_type or "text/xml" in content_type:
                try:
                    response_data["data"] = self._xml_to_dict(response.text)
                    response_data["format"] = "xml"
                except Exception as e:
                    response_data["data"] = response.text
                    response_data["format"] = "text"
                    response_data["parse_error"] = f"XML解析失败: {str(e)}"
            
            else:
                response_data["data"] = response.text
                response_data["format"] = "text"
            
            return True, "请求成功", response_data
        
        except Exception as e:
            return False, f"响应解析失败: {str(e)}", None
    
    def _xml_to_dict(self, xml_string: str) -> Dict[str, Any]:
        """将XML转换为字典"""
        def element_to_dict(element):
            result = {}
            
            # 添加属性
            if element.attrib:
                result["@attributes"] = element.attrib
            
            # 处理子元素
            children = list(element)
            if children:
                child_dict = {}
                for child in children:
                    child_data = element_to_dict(child)
                    if child.tag in child_dict:
                        # 如果标签已存在，转换为列表
                        if not isinstance(child_dict[child.tag], list):
                            child_dict[child.tag] = [child_dict[child.tag]]
                        child_dict[child.tag].append(child_data)
                    else:
                        child_dict[child.tag] = child_data
                result.update(child_dict)
            
            # 添加文本内容
            if element.text and element.text.strip():
                if result:  # 如果已有其他内容，将文本作为特殊键
                    result["#text"] = element.text.strip()
                else:  # 如果只有文本，直接返回文本
                    return element.text.strip()
            
            return result if result else None
        
        root = ET.fromstring(xml_string)
        return {root.tag: element_to_dict(root)}
    
    def get_api_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """获取所有API端点信息"""
        endpoints = self.config.get("endpoints", {})
        result = {}
        
        for name, config in endpoints.items():
            result[name] = {
                "name": name,
                "method": config.get("method", "GET"),
                "path": config.get("path", ""),
                "description": config.get("description", ""),
                "parameters": config.get("parameters", {}),
                "response_format": config.get("response_format", "json")
            }
        
        return result
    
    def close(self):
        """关闭连接"""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()