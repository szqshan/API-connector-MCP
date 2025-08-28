#!/usr/bin/env python3
"""
数据转换器
负责API数据的格式转换和处理
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import xml.etree.ElementTree as ET
import csv
import io

logger = logging.getLogger(__name__)

class DataTransformer:
    """数据转换器类"""
    
    def __init__(self):
        self.supported_formats = ["json", "csv", "xml", "dataframe", "list"]
    
    def transform_data(self, 
                      data: Any, 
                      output_format: str = "json",
                      transform_config: Dict[str, Any] = None) -> tuple[bool, Any, str]:
        """转换数据格式"""
        try:
            if output_format not in self.supported_formats:
                return False, None, f"不支持的输出格式: {output_format}"
            
            # 应用转换配置
            if transform_config:
                success, processed_data, message = self._apply_transform_config(data, transform_config)
                if not success:
                    return False, None, message
                data = processed_data
            
            # 格式转换
            if output_format == "json":
                return self._to_json(data)
            elif output_format == "csv":
                return self._to_csv(data)
            elif output_format == "xml":
                return self._to_xml(data)
            elif output_format == "dataframe":
                return self._to_dataframe(data)
            elif output_format == "list":
                return self._to_list(data)
            else:
                return False, None, f"未实现的格式转换: {output_format}"
        
        except Exception as e:
            logger.error(f"数据转换失败: {e}")
            return False, None, f"数据转换失败: {str(e)}"
    
    def _apply_transform_config(self, data: Any, config: Dict[str, Any]) -> tuple[bool, Any, str]:
        """应用转换配置"""
        try:
            result_data = data
            
            # 字段选择
            if "select_fields" in config and isinstance(result_data, (list, dict)):
                fields = config["select_fields"]
                if isinstance(result_data, dict):
                    result_data = {k: v for k, v in result_data.items() if k in fields}
                elif isinstance(result_data, list) and result_data and isinstance(result_data[0], dict):
                    result_data = [{k: v for k, v in item.items() if k in fields} for item in result_data]
            
            # 字段重命名
            if "rename_fields" in config and isinstance(result_data, (list, dict)):
                rename_map = config["rename_fields"]
                if isinstance(result_data, dict):
                    result_data = {rename_map.get(k, k): v for k, v in result_data.items()}
                elif isinstance(result_data, list) and result_data and isinstance(result_data[0], dict):
                    result_data = [{rename_map.get(k, k): v for k, v in item.items()} for item in result_data]
            
            # 数据过滤
            if "filter_conditions" in config and isinstance(result_data, list):
                conditions = config["filter_conditions"]
                filtered_data = []
                for item in result_data:
                    if self._check_filter_conditions(item, conditions):
                        filtered_data.append(item)
                result_data = filtered_data
            
            # 数据排序
            if "sort_by" in config and isinstance(result_data, list):
                sort_field = config["sort_by"]
                reverse = config.get("sort_desc", False)
                try:
                    result_data = sorted(result_data, 
                                       key=lambda x: x.get(sort_field, 0) if isinstance(x, dict) else x,
                                       reverse=reverse)
                except Exception as e:
                    logger.warning(f"排序失败: {e}")
            
            # 数据限制
            if "limit" in config and isinstance(result_data, list):
                limit = config["limit"]
                result_data = result_data[:limit]
            
            # 数据类型转换
            if "type_conversions" in config:
                conversions = config["type_conversions"]
                result_data = self._apply_type_conversions(result_data, conversions)
            
            # 添加计算字段
            if "computed_fields" in config and isinstance(result_data, (list, dict)):
                computed = config["computed_fields"]
                result_data = self._add_computed_fields(result_data, computed)
            
            return True, result_data, "转换配置应用成功"
        
        except Exception as e:
            logger.error(f"应用转换配置失败: {e}")
            return False, data, f"应用转换配置失败: {str(e)}"
    
    def _check_filter_conditions(self, item: Dict[str, Any], conditions: List[Dict[str, Any]]) -> bool:
        """检查过滤条件"""
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "eq")
            value = condition.get("value")
            
            if field not in item:
                continue
            
            item_value = item[field]
            
            if operator == "eq" and item_value != value:
                return False
            elif operator == "ne" and item_value == value:
                return False
            elif operator == "gt" and not (item_value > value):
                return False
            elif operator == "gte" and not (item_value >= value):
                return False
            elif operator == "lt" and not (item_value < value):
                return False
            elif operator == "lte" and not (item_value <= value):
                return False
            elif operator == "contains" and value not in str(item_value):
                return False
            elif operator == "startswith" and not str(item_value).startswith(str(value)):
                return False
            elif operator == "endswith" and not str(item_value).endswith(str(value)):
                return False
        
        return True
    
    def _apply_type_conversions(self, data: Any, conversions: Dict[str, str]) -> Any:
        """应用数据类型转换"""
        try:
            if isinstance(data, dict):
                for field, target_type in conversions.items():
                    if field in data:
                        data[field] = self._convert_value_type(data[field], target_type)
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                for item in data:
                    for field, target_type in conversions.items():
                        if field in item:
                            item[field] = self._convert_value_type(item[field], target_type)
            
            return data
        except Exception as e:
            logger.warning(f"类型转换失败: {e}")
            return data
    
    def _convert_value_type(self, value: Any, target_type: str) -> Any:
        """转换单个值的类型"""
        try:
            if target_type == "int":
                return int(float(value)) if value is not None else None
            elif target_type == "float":
                return float(value) if value is not None else None
            elif target_type == "str":
                return str(value) if value is not None else None
            elif target_type == "bool":
                if isinstance(value, str):
                    return value.lower() in ["true", "1", "yes", "on"]
                return bool(value) if value is not None else None
            elif target_type == "datetime":
                if isinstance(value, str):
                    # 尝试多种日期格式
                    formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d/%m/%Y"]
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                return value
            else:
                return value
        except Exception:
            return value
    
    def _add_computed_fields(self, data: Any, computed: Dict[str, str]) -> Any:
        """添加计算字段"""
        try:
            if isinstance(data, dict):
                for field_name, expression in computed.items():
                    data[field_name] = self._evaluate_expression(data, expression)
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                for item in data:
                    for field_name, expression in computed.items():
                        item[field_name] = self._evaluate_expression(item, expression)
            
            return data
        except Exception as e:
            logger.warning(f"添加计算字段失败: {e}")
            return data
    
    def _evaluate_expression(self, item: Dict[str, Any], expression: str) -> Any:
        """评估表达式（简单实现）"""
        try:
            # 简单的字段引用
            if expression.startswith("${") and expression.endswith("}"): 
                field_name = expression[2:-1]
                return item.get(field_name)
            
            # 简单的数学运算
            if "+" in expression:
                parts = expression.split("+")
                result = 0
                for part in parts:
                    part = part.strip()
                    if part.startswith("${") and part.endswith("}"): 
                        field_name = part[2:-1]
                        result += float(item.get(field_name, 0))
                    else:
                        result += float(part)
                return result
            
            # 字符串连接
            if "||" in expression:
                parts = expression.split("||")
                result = ""
                for part in parts:
                    part = part.strip()
                    if part.startswith("${") and part.endswith("}"): 
                        field_name = part[2:-1]
                        result += str(item.get(field_name, ""))
                    else:
                        result += part.strip('"\'')
                return result
            
            return expression
        except Exception:
            return expression
    
    def _to_json(self, data: Any) -> tuple[bool, str, str]:
        """转换为JSON格式"""
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
            return True, json_str, "转换为JSON成功"
        except Exception as e:
            return False, None, f"转换为JSON失败: {str(e)}"
    
    def _to_csv(self, data: Any) -> tuple[bool, str, str]:
        """转换为CSV格式"""
        try:
            if isinstance(data, list) and data and isinstance(data[0], dict):
                # 列表字典转CSV
                output = io.StringIO()
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                return True, output.getvalue(), "转换为CSV成功"
            elif isinstance(data, dict):
                # 单个字典转CSV
                output = io.StringIO()
                fieldnames = data.keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(data)
                return True, output.getvalue(), "转换为CSV成功"
            else:
                return False, None, "数据格式不适合转换为CSV"
        except Exception as e:
            return False, None, f"转换为CSV失败: {str(e)}"
    
    def _to_xml(self, data: Any) -> tuple[bool, str, str]:
        """转换为XML格式"""
        try:
            def dict_to_xml(d, root_name="root"):
                root = ET.Element(root_name)
                
                def add_to_element(element, key, value):
                    if isinstance(value, dict):
                        sub_element = ET.SubElement(element, key)
                        for k, v in value.items():
                            add_to_element(sub_element, k, v)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                sub_element = ET.SubElement(element, key)
                                for k, v in item.items():
                                    add_to_element(sub_element, k, v)
                            else:
                                sub_element = ET.SubElement(element, key)
                                sub_element.text = str(item)
                    else:
                        sub_element = ET.SubElement(element, key)
                        sub_element.text = str(value)
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        add_to_element(root, key, value)
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        add_to_element(root, f"item_{i}", item)
                else:
                    root.text = str(data)
                
                return ET.tostring(root, encoding='unicode')
            
            xml_str = dict_to_xml(data)
            return True, xml_str, "转换为XML成功"
        except Exception as e:
            return False, None, f"转换为XML失败: {str(e)}"
    
    def _to_dataframe(self, data: Any) -> tuple[bool, List[Dict[str, Any]], str]:
        """转换为表格格式（兼容DataFrame接口的列表字典）"""
        try:
            if isinstance(data, list) and data and isinstance(data[0], dict):
                # 已经是列表字典格式
                return True, data, "转换为表格格式成功"
            elif isinstance(data, dict):
                # 单个字典转为列表
                return True, [data], "转换为表格格式成功"
            elif isinstance(data, list):
                # 纯列表转为字典列表
                table_data = [{"value": item, "index": i} for i, item in enumerate(data)]
                return True, table_data, "转换为表格格式成功"
            else:
                # 其他类型转为单个字典
                return True, [{"value": data}], "转换为表格格式成功"
        except Exception as e:
            return False, [], f"转换为表格格式失败: {str(e)}"
    
    def _to_list(self, data: Any) -> tuple[bool, List[Any], str]:
        """转换为列表格式"""
        try:
            if isinstance(data, list):
                return True, data, "数据已是列表格式"
            elif isinstance(data, dict):
                return True, [data], "转换为列表成功"
            else:
                return True, [data], "转换为列表成功"
        except Exception as e:
            return False, None, f"转换为列表失败: {str(e)}"
    
    def preview_data(self, 
                    data: Any,
                    max_rows: int = 10,
                    max_cols: int = 10,
                    preview_fields: list = None,
                    preview_depth: int = 3,
                    show_data_types: bool = True,
                    show_summary: bool = True,
                    truncate_length: int = 100) -> Dict[str, Any]:
        """预览数据"""
        try:
            preview_result = {
                "data_type": type(data).__name__,
                "preview": None,
                "summary": None,
                "data_types": None
            }
            
            # 处理不同类型的数据
            if isinstance(data, dict):
                preview_result["preview"] = self._preview_dict(data, max_rows, max_cols, preview_fields, preview_depth, truncate_length)
            elif isinstance(data, list):
                preview_result["preview"] = self._preview_list(data, max_rows, max_cols, preview_fields, preview_depth, truncate_length)
            else:
                preview_result["preview"] = str(data)[:truncate_length]
                
            # 添加摘要信息
            if show_summary:
                preview_result["summary"] = self.get_data_info(data)
                
            # 添加数据类型信息
            if show_data_types:
                preview_result["data_types"] = self._get_data_types(data, preview_depth)
                
            return preview_result
            
        except Exception as e:
            logger.error(f"数据预览错误: {e}")
            return {
                "error": str(e),
                "data_type": type(data).__name__
            }
    
    def _preview_dict(self, data: dict, max_rows: int, max_cols: int, preview_fields: list, preview_depth: int, truncate_length: int) -> dict:
        """预览字典数据"""
        result = {}
        count = 0
        
        for key, value in data.items():
            if count >= max_cols:
                result["..."] = f"还有 {len(data) - count} 个字段"
                break
                
            if preview_fields and key not in preview_fields:
                continue
                
            if isinstance(value, (dict, list)) and preview_depth > 0:
                if isinstance(value, dict):
                    result[key] = self._preview_dict(value, max_rows, max_cols, None, preview_depth - 1, truncate_length)
                else:
                    result[key] = self._preview_list(value, max_rows, max_cols, None, preview_depth - 1, truncate_length)
            else:
                str_value = str(value)
                result[key] = str_value[:truncate_length] + "..." if len(str_value) > truncate_length else str_value
                
            count += 1
            
        return result
    
    def _preview_list(self, data: list, max_rows: int, max_cols: int, preview_fields: list, preview_depth: int, truncate_length: int) -> list:
        """预览列表数据"""
        result = []
        
        for i, item in enumerate(data[:max_rows]):
            if isinstance(item, dict) and preview_depth > 0:
                result.append(self._preview_dict(item, max_rows, max_cols, preview_fields, preview_depth - 1, truncate_length))
            elif isinstance(item, list) and preview_depth > 0:
                result.append(self._preview_list(item, max_rows, max_cols, preview_fields, preview_depth - 1, truncate_length))
            else:
                str_item = str(item)
                result.append(str_item[:truncate_length] + "..." if len(str_item) > truncate_length else str_item)
                
        if len(data) > max_rows:
            result.append(f"... 还有 {len(data) - max_rows} 个项目")
            
        return result
    
    def _get_data_types(self, data: Any, depth: int = 3) -> Dict[str, Any]:
        """获取数据类型信息"""
        if depth <= 0:
            return {"type": type(data).__name__}
            
        if isinstance(data, dict):
            types_info = {"type": "dict", "fields": {}}
            for key, value in data.items():
                types_info["fields"][key] = self._get_data_types(value, depth - 1)
            return types_info
        elif isinstance(data, list) and data:
            return {
                "type": "list",
                "length": len(data),
                "item_type": self._get_data_types(data[0], depth - 1) if data else "unknown"
            }
        else:
            return {"type": type(data).__name__}
    
    def get_data_info(self, data: Any) -> Dict[str, Any]:
        """获取数据信息"""
        try:
            info = {
                "type": type(data).__name__,
                "size": 0,
                "structure": {},
                "sample": None
            }
            
            if isinstance(data, list):
                info["size"] = len(data)
                if data:
                    info["sample"] = data[0] if len(data) == 1 else data[:2]
                    if isinstance(data[0], dict):
                        info["structure"] = {
                            "fields": list(data[0].keys()),
                            "field_types": {k: type(v).__name__ for k, v in data[0].items()}
                        }
            elif isinstance(data, dict):
                info["size"] = len(data)
                info["sample"] = data
                info["structure"] = {
                    "fields": list(data.keys()),
                    "field_types": {k: type(v).__name__ for k, v in data.items()}
                }
            else:
                info["size"] = 1
                info["sample"] = data
            
            return info
        except Exception as e:
            logger.error(f"获取数据信息失败: {e}")
            return {"error": str(e)}

# 创建全局实例
data_transformer = DataTransformer()