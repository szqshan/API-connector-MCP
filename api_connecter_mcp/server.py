#!/usr/bin/env python3
"""
API_Connecter_MCP Server Module
MCP服务器入口模块
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 直接导入并运行main.py中的MCP服务器
from main import mcp

def main():
    """启动MCP服务器"""
    try:
        # 运行MCP服务器
        mcp.run()
    except Exception as e:
        print(f"❌ MCP服务器启动失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()