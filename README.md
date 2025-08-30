# 🌐 API Connecter MCP - 让AI连接万物的桥梁

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/MCP-Protocol-green.svg" alt="MCP Protocol">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Stable-brightgreen.svg" alt="Status">
</p>

## 🎯 项目简介

### 💡 开发灵感
还记得第一次让Claude帮我查天气，结果它无奈地告诉我"我无法直接访问互联网"时的那种挫败感吗？作为一个开发者，我每天都在和各种API打交道，突然意识到：为什么不能让我们的AI助手也能像开发者一样自由地调用各种API呢？

于是，API Connecter MCP诞生了！这是一个专门为MCP（Model Context Protocol）设计的通用API连接器，它的使命很简单：**让AI能够像人类一样自由地连接和使用各种API服务**。

### 🚀 核心愿景
- **打破数据孤岛**：让AI不再局限于训练数据，而是能够实时获取最新信息
- **降低使用门槛**：不需要编程背景，通过简单的配置就能让AI使用各种API
- **统一接口标准**：无论API多么复杂，都提供统一的调用方式
- **安全可靠**：内置安全检查，防止恶意API调用

### ✨ 功能亮点
- **零代码集成**：通过配置文件即可连接任何REST API
- **智能数据转换**：自动将API数据转换为AI友好的格式
- **会话管理**：为不同任务创建独立的数据存储会话
- **实时预览**：调用前预览数据结构，避免意外结果
- **全平台支持**：支持Windows、macOS、Linux

## 📦 部署指南

### 🏃‍♂️ 一键安装（推荐）

#### 方法1：PyPI安装（最简单）
```bash
# 安装包
pip install api-connecter-mcp

# 验证安装
python -c "import api_connecter_mcp.server; print('安装成功！')"
```

#### 方法2：源码安装（开发者模式）
```bash
# 克隆项目
git clone https://github.com/your-repo/api-connecter-mcp.git
cd api-connecter-mcp

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### ⚙️ 客户端配置

#### Claude Desktop配置
1. **找到配置文件**：
   - Windows: `%APPDATA%/Claude/claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **添加MCP服务器**：
   ```json
   {
     "mcpServers": {
       "api-connecter": {
         "command": "uvx",
         "args": ["api-connecter-mcp"]
       }
     }
   }
   ```

3. **重启Claude Desktop**即可生效！

#### 其他MCP客户端
- **Cursor**: 在设置中添加MCP服务器配置
- **Windsurf**: 支持MCP协议的IDE扩展
- **自定义客户端**: 任何支持MCP协议的客户端都可以使用

### 🔧 环境依赖

#### 系统要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **内存**: 至少512MB可用内存
- **存储**: 100MB可用磁盘空间

#### Python依赖包
```txt
requests>=2.28.0
pandas>=1.5.0
mcp>=1.0.0
python-dotenv>=1.0.0
```

### 🗂️ 配置文件设置 （可选，不是必须）

#### 1. 环境变量配置
复制示例文件：
```bash
cp .env.example .env
```

编辑`.env`文件：（可选，不是必须）
```bash
# API密钥配置
OPENAI_API_KEY=sk-your-openai-key
WEATHER_API_KEY=your-weather-api-key
GITHUB_TOKEN=ghp-your-github-token

# 安全配置
MAX_RESPONSE_SIZE=10485760
LOG_LEVEL=INFO
```

#### 2. API配置文件（可选，不是必须）
编辑`config/api_config.json`：
```json
{
  "apis": {
    "weather": {
      "name": "天气API",
      "description": "获取全球天气信息",
      "enabled": true,
      "base_url": "https://api.openweathermap.org/data/2.5",
      "auth_type": "api_key",
      "auth": {
        "key": "${WEATHER_API_KEY}",
        "param_name": "appid"
      },
      "endpoints": {
        "current_weather": {
          "path": "/weather",
          "method": "GET",
          "description": "获取当前天气",
          "params": {
            "q": {"type": "string", "description": "城市名称"},
            "units": {"type": "string", "default": "metric"}
          }
        }
      }
    }
  }
}
```

## 🎮 使用示例

### 📸 实际效果展示

#### 场景1：让Claude帮你查天气
**用户输入**：
```
帮我查一下北京现在的天气
```

**Claude使用MCP工具**：
```python
fetch_api_data(
    api_name="weather",
    endpoint_name="current_weather",
    params={"q": "Beijing", "units": "metric"}
)
```

**返回结果**：
```json
{
  "coord": {"lon": 116.4074, "lat": 39.9042},
  "weather": [{
    "main": "Clear",
    "description": "晴朗",
    "icon": "01d"
  }],
  "main": {
    "temp": 22.5,
    "feels_like": 21.8,
    "humidity": 45,
    "pressure": 1013
  },
  "wind": {
    "speed": 3.5,
    "deg": 180
  }
}
```

**Claude回复**：
```
北京当前天气：晴朗，气温22.5°C，湿度45%，东南风3.5m/s。体感温度21.8°C，非常舒适！
```

#### 场景2：批量获取GitHub用户信息
**用户输入**：
```
帮我获取facebook、google、microsoft的GitHub组织信息
```

**Claude批量调用**：
```python
companies = ["facebook", "google", "microsoft"]
results = []

for company in companies:
    data = fetch_api_data(
        api_name="github",
        endpoint_name="get_org",
        params={"org": company}
    )
    results.append(data)
```

**返回结果预览**：
```json
[
  {
    "login": "facebook",
    "name": "Meta Platforms, Inc.",
    "public_repos": 398,
    "followers": 20234,
    "description": "We are working to build community through open source technology."
  },
  {
    "login": "google",
    "name": "Google Inc.",
    "public_repos": 2876,
    "followers": 89421,
    "description": "Google ❤️ Open Source"
  }
]
```

#### 场景3：数据转换和筛选
**用户输入**：
```
获取豆瓣电影Top250，只要评分9.0以上的，按评分排序
```

**Claude使用数据转换**：
```python
transform_config = {
    "filter_conditions": [
        {"field": "rating", "operator": "gte", "value": 9.0}
    ],
    "sort_by": "rating",
    "order": "desc",
    "select_fields": ["title", "rating", "year", "director"],
    "limit": 50
}

fetch_api_data(
    api_name="douban",
    endpoint_name="top250",
    transform_config=transform_config
)
```

**返回结果**：
```json
[
  {"title": "肖申克的救赎", "rating": 9.7, "year": 1994, "director": "弗兰克·德拉邦特"},
  {"title": "霸王别姬", "rating": 9.6, "year": 1993, "director": "陈凯歌"},
  {"title": "阿甘正传", "rating": 9.5, "year": 1994, "director": "罗伯特·泽米吉斯"}
]
```

### 🛠️ 高级用法示例

#### 创建数据存储会话
```python
# 为长期项目创建专用会话
session = create_api_storage_session(
    session_name="stock_analysis_2024",
    api_name="alphavantage",
    endpoint_name="daily_prices",
    description="2024年股票分析数据收集"
)

# 后续调用直接使用会话ID
fetch_api_data(
    api_name="alphavantage",
    endpoint_name="daily_prices",
    storage_session_id="stock_analysis_2024",
    params={"symbol": "AAPL"}
)
```

#### 批量API测试
```python
# 测试所有配置的API
manage_api_config(action="test_all")

# 结果示例
{
  "weather": {"status": "success", "response_time": 245},
  "github": {"status": "success", "response_time": 123},
  "douban": {"status": "failed", "error": "Rate limit exceeded"}
}
```

### 🎨 可视化效果

#### 1. 配置管理界面（Claude Desktop）
```
Claude: 我已连接到你的API Connecter MCP服务器！
可用API列表：
- 🌤️ 天气API (openweathermap.org)
- 🐙 GitHub API (api.github.com)
- 🎬 豆瓣电影 (api.douban.com)
- 📈 股票数据 (alphavantage.co)

要开始使用，请告诉我你想查询什么信息！
```

#### 2. 实时数据展示
```
用户: 帮我分析一下苹果公司最近7天的股价
Claude: 我来为你获取AAPL最近7天的数据...

[正在调用股票API...]
[获取数据成功，共7条记录]

📊 分析结果：
- 平均价格: $185.32
- 最高价格: $189.45 (2024-01-15)
- 最低价格: $182.11 (2024-01-12)
- 涨跌幅: +2.34%
- 趋势: 整体呈上升趋势
```

## 🚀 快速上手

### 5分钟快速体验

1. **安装**：`pip install api-connecter-mcp`
2. **配置**：复制`claude_desktop_config_simple.json`到Claude配置
3. **启动**：重启Claude Desktop
4. **测试**：说"帮我查一下天气"试试看！

### 故障排除

#### 常见问题
1. **连接失败**：检查网络连接和API密钥
2. **编码错误**：确保配置文件使用UTF-8编码
3. **权限问题**：检查文件和目录权限
4. **端口冲突**：修改配置中的端口号

#### 调试模式
```bash
# 开启详细日志
export LOG_LEVEL=DEBUG
python -m api_connecter_mcp.server
```

## 🤝 社区支持

- **问题反馈**：[GitHub Issues](https://github.com/your-repo/issues)
- **功能建议**：[GitHub Discussions](https://github.com/your-repo/discussions)
- **实时交流**：[Discord社区](https://discord.gg/your-server)

---

**让AI不再受限于训练数据，让实时世界触手可及！** 🌐✨

<p align="center">
  <i>Made with ❤️ by developers, for developers and AI enthusiasts</i>
</p>
