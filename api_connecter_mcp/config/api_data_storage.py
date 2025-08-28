#!/usr/bin/env python3
"""
API数据存储管理器
负责将API获取的数据存储到临时数据库文件中
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import uuid
import hashlib

logger = logging.getLogger(__name__)

class APIDataStorage:
    """API数据存储管理器"""
    
    def __init__(self, storage_dir: str = "api_data_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.metadata_db = self.storage_dir / "metadata.db"
        self._init_metadata_db()
    
    def _init_metadata_db(self):
        """初始化元数据数据库"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                # 存储会话表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS storage_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT NOT NULL,
                        description TEXT,
                        api_name TEXT NOT NULL,
                        endpoint_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_records INTEGER DEFAULT 0,
                        last_operation_at TIMESTAMP
                    )
                """)
                
                # 操作日志表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS data_operations (
                        operation_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        records_affected INTEGER DEFAULT 0,
                        operation_details TEXT,
                        FOREIGN KEY (session_id) REFERENCES storage_sessions (session_id)
                    )
                """)
                
                conn.commit()
                logger.info("API数据存储元数据库初始化完成")
        
        except Exception as e:
            logger.error(f"初始化元数据数据库失败: {e}")
            raise
    
    def create_storage_session(self, 
                             session_name: str,
                             api_name: str,
                             endpoint_name: str,
                             description: str = None) -> tuple[bool, str, str]:
        """创建存储会话"""
        try:
            session_id = str(uuid.uuid4())
            file_name = f"{api_name}_{endpoint_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            file_path = self.storage_dir / file_name
            
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    INSERT INTO storage_sessions 
                    (session_id, session_name, description, api_name, endpoint_name, file_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, session_name, description, api_name, endpoint_name, str(file_path)))
                conn.commit()
            
            # 创建数据存储文件
            with sqlite3.connect(file_path) as data_conn:
                data_conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_hash TEXT UNIQUE,
                        raw_data TEXT,
                        processed_data TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source_params TEXT
                    )
                """)
                data_conn.commit()
            
            logger.info(f"存储会话创建成功: {session_name} (ID: {session_id})")
            return True, session_id, f"存储会话创建成功: {session_name}"
        
        except Exception as e:
            logger.error(f"创建存储会话失败: {e}")
            return False, "", f"创建存储会话失败: {str(e)}"
    
    def store_api_data(self, 
                      session_id: str,
                      raw_data: Any,
                      processed_data: Any = None,
                      source_params: Dict[str, Any] = None) -> tuple[bool, int, str]:
        """存储API数据"""
        try:
            # 获取会话信息
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, 0, f"存储会话不存在: {session_id}"
            
            file_path = session_info['file_path']
            
            # 生成数据哈希（用于去重）
            data_str = json.dumps(raw_data, sort_keys=True, default=str)
            data_hash = hashlib.md5(data_str.encode()).hexdigest()
            
            with sqlite3.connect(file_path) as conn:
                # 检查是否已存在相同数据
                cursor = conn.execute("SELECT id FROM api_data WHERE data_hash = ?", (data_hash,))
                if cursor.fetchone():
                    return True, 0, "数据已存在，跳过重复存储"
                
                # 存储数据
                conn.execute("""
                    INSERT INTO api_data (data_hash, raw_data, processed_data, source_params)
                    VALUES (?, ?, ?, ?)
                """, (
                    data_hash,
                    json.dumps(raw_data, default=str),
                    json.dumps(processed_data, default=str) if processed_data else None,
                    json.dumps(source_params, default=str) if source_params else None
                ))
                
                records_added = conn.total_changes
                conn.commit()
            
            # 更新会话统计
            self._update_session_stats(session_id)
            
            # 记录操作
            self._log_operation(session_id, "store_data", records_added, 
                              f"存储API数据，哈希: {data_hash[:8]}...")
            
            return True, records_added, f"数据存储成功，新增 {records_added} 条记录"
            
        except Exception as e:
            logger.error(f"存储API数据失败: {e}")
            return False, 0, f"存储API数据失败: {str(e)}"
    
    def get_stored_data(self, 
                       session_id: str,
                       limit: int = None,
                       offset: int = 0,
                       format_type: str = "json") -> tuple[bool, Any, str]:
        """获取存储的数据"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, None, f"存储会话不存在: {session_id}"
            
            file_path = session_info['file_path']
            
            with sqlite3.connect(file_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 构建查询
                query = "SELECT * FROM api_data ORDER BY timestamp DESC"
                params = []
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                    
                if offset > 0:
                    query += " OFFSET ?"
                    params.append(offset)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
            
            if not rows:
                return True, [], "没有找到存储的数据"
            
            # 转换数据格式
            if format_type == "json":
                data = []
                for row in rows:
                    item = {
                        'id': row['id'],
                        'data_hash': row['data_hash'],
                        'raw_data': json.loads(row['raw_data']) if row['raw_data'] else None,
                        'processed_data': json.loads(row['processed_data']) if row['processed_data'] else None,
                        'timestamp': row['timestamp'],
                        'source_params': json.loads(row['source_params']) if row['source_params'] else None
                    }
                    data.append(item)
                return True, data, f"获取到 {len(data)} 条记录"
            
            elif format_type == "dataframe":
                # 转换为表格格式（兼容DataFrame接口的列表字典）
                data_list = []
                for row in rows:
                    raw_data = json.loads(row['raw_data']) if row['raw_data'] else {}
                    if isinstance(raw_data, dict):
                        item = raw_data.copy()
                        item['_id'] = row['id']
                        item['_timestamp'] = row['timestamp']
                        data_list.append(item)
                    elif isinstance(raw_data, list):
                        for i, sub_item in enumerate(raw_data):
                            if isinstance(sub_item, dict):
                                item = sub_item.copy()
                                item['_id'] = f"{row['id']}_{i}"
                                item['_timestamp'] = row['timestamp']
                                data_list.append(item)
                
                return True, data_list, f"转换为表格格式，包含 {len(data_list)} 行数据"
            
            else:
                return False, None, f"不支持的格式类型: {format_type}"
        
        except Exception as e:
            logger.error(f"获取存储数据失败: {e}")
            return False, None, f"获取存储数据失败: {str(e)}"
    
    def list_storage_sessions(self) -> tuple[bool, List[Dict[str, Any]], str]:
        """列出所有存储会话"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM storage_sessions 
                    ORDER BY created_at DESC
                """)
                rows = cursor.fetchall()
            
            sessions = []
            for row in rows:
                session = {
                    'session_id': row['session_id'],
                    'session_name': row['session_name'],
                    'description': row['description'],
                    'api_name': row['api_name'],
                    'endpoint_name': row['endpoint_name'],
                    'file_path': row['file_path'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'total_records': row['total_records'],
                    'last_operation_at': row['last_operation_at']
                }
                sessions.append(session)
            
            return True, sessions, f"找到 {len(sessions)} 个存储会话"
        
        except Exception as e:
            logger.error(f"列出存储会话失败: {e}")
            return False, [], f"列出存储会话失败: {str(e)}"
    
    def _get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM storage_sessions WHERE session_id = ?", 
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        'session_id': row['session_id'],
                        'session_name': row['session_name'],
                        'description': row['description'],
                        'api_name': row['api_name'],
                        'endpoint_name': row['endpoint_name'],
                        'file_path': row['file_path'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'total_records': row['total_records'],
                        'last_operation_at': row['last_operation_at']
                    }
                return None
        
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return None
    
    def _update_session_stats(self, session_id: str):
        """更新会话统计信息"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return
            
            file_path = session_info['file_path']
            
            # 获取记录总数
            with sqlite3.connect(file_path) as data_conn:
                cursor = data_conn.execute("SELECT COUNT(*) FROM api_data")
                total_records = cursor.fetchone()[0]
            
            # 更新元数据
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    UPDATE storage_sessions 
                    SET total_records = ?, updated_at = CURRENT_TIMESTAMP, last_operation_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (total_records, session_id))
                conn.commit()
        
        except Exception as e:
            logger.error(f"更新会话统计失败: {e}")
    
    def _log_operation(self, session_id: str, operation_type: str, 
                      records_affected: int, details: str):
        """记录操作日志"""
        try:
            operation_id = str(uuid.uuid4())
            with sqlite3.connect(self.metadata_db) as conn:
                conn.execute("""
                    INSERT INTO data_operations 
                    (operation_id, session_id, operation_type, records_affected, operation_details)
                    VALUES (?, ?, ?, ?, ?)
                """, (operation_id, session_id, operation_type, records_affected, details))
                conn.commit()
        
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    def delete_storage_session(self, session_id: str) -> tuple[bool, str]:
        """删除存储会话"""
        try:
            session_info = self._get_session_info(session_id)
            if not session_info:
                return False, f"存储会话不存在: {session_id}"
            
            file_path = Path(session_info['file_path'])
            
            # 删除数据文件
            if file_path.exists():
                file_path.unlink()
            
            # 删除元数据记录
            with sqlite3.connect(self.metadata_db) as conn:
                # 删除操作日志
                conn.execute("DELETE FROM data_operations WHERE session_id = ?", (session_id,))
                # 删除会话记录
                conn.execute("DELETE FROM storage_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
            
            logger.info(f"存储会话删除成功: {session_id}")
            return True, f"存储会话删除成功: {session_info['session_name']}"
        
        except Exception as e:
            logger.error(f"删除存储会话失败: {e}")
            return False, f"删除存储会话失败: {str(e)}"
    
    def get_session_operations(self, session_id: str) -> tuple[bool, List[Dict[str, Any]], str]:
        """获取会话操作历史"""
        try:
            with sqlite3.connect(self.metadata_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM data_operations 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC
                """, (session_id,))
                rows = cursor.fetchall()
            
            operations = []
            for row in rows:
                operation = {
                    'operation_id': row['operation_id'],
                    'operation_type': row['operation_type'],
                    'timestamp': row['timestamp'],
                    'records_affected': row['records_affected'],
                    'operation_details': row['operation_details']
                }
                operations.append(operation)
            
            return True, operations, f"找到 {len(operations)} 个操作记录"
            
        except Exception as e:
            logger.error(f"获取会话操作历史失败: {e}")
            return False, [], f"获取会话操作历史失败: {str(e)}"

# 创建全局实例
api_data_storage = APIDataStorage()