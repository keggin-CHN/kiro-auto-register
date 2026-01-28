# AWS Builder ID 自动注册工具

🤖 全自动批量注册 AWS Builder ID 账号，并获取 Kiro OAuth Token 和 AWS SSO OIDC Token

<h1 align="center">
  🚨 警告：Kiro 封号政策更新 🚨
  <br>
  本仓库方法已失效，仅作讨论用途
</h1>

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ⚠️ 免责声明 ##

本工具仅供学习和研究使用，使用者需自行承担使用本工具的一切后果。请遵守相关法律法规和服务条款。

## ✨ 功能特性

- ✅ **全自动注册** - 无需手动操作，自动完成整个注册流程
- 📧 **临时邮箱** - 自动创建和管理临时邮箱（无需自己部署）
- 🔐 **Token 获取** - 自动获取 Kiro Access Token 和 AWS SSO OIDC Refresh Token
- 🌍 **多地区支持** - 支持美国、德国、日本等地区的本地化环境
- 🎭 **代理支持** - 支持静态代理和动态代理 API
- 📱 **设备模拟** - 支持桌面和移动设备模拟
- 🔄 **批量注册** - 支持批量创建多个账号
- 💾 **自动保存** - 账号信息自动保存为 JSON 格式

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- Chrome 或 Edge 浏览器（推荐 Edge，Windows 自带）
- 稳定的网络连接（建议使用代理）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/keggin-CHN/kiro-auto-register.git
cd kiro-auto-register
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置文件**

编辑 [`config/config.yaml`](config/config.yaml) 文件：

```yaml
# 浏览器配置
browser:
  headless: false      # 是否无头模式
  type: "edge"         # 浏览器类型: chrome 或 edge
  driver_strategy: "auto"  # WebDriver 获取策略

# 地区配置
region:
  current: "usa"       # 当前地区: usa, germany, japan
  device_type: "desktop"  # 设备类型: desktop, mobile
  
  # 代理配置
  use_proxy: false     # 是否使用代理（强烈建议启用）
  proxy_mode: "static" # 代理模式: static 或 dynamic
  proxy_url: ""        # 静态代理地址（如: http://host:port）
```

### 运行程序

#### 方式一：批量注册（推荐）

```bash
# Windows
python src/runners/main.py

# Linux/Mac
python3 src/runners/main.py
```

程序会提示输入：
- 注册数量（默认 1 个）
- 每个账号之间的间隔时间（默认 30 秒）

#### 方式二：智能注册（自动检测代理地区）

```bash
python src/runners/smart_run.py
```

会根据代理 IP 的地理位置自动配置环境（语言、时区等）

#### 方式三：单次注册

```bash
from runners.main import run
run()
```

## 📋 配置说明

### 代理配置

#### 静态代理

```yaml
region:
  use_proxy: true
  proxy_mode: "static"
  proxy_url: "http://proxy.example.com:8080"
  # 或使用 SOCKS5
  # proxy_url: "socks5://proxy.example.com:1080"
```

#### 动态代理 API

```yaml
region:
  use_proxy: true
  proxy_mode: "dynamic"
  proxy_api:
    url: "http://api.proxy.com/get?key=YOUR_API_KEY"
    timeout: 10
    protocol: "http"  # http 或 socks5
    auth_required: false
    username: ""
    password: ""
```

### 地区配置

支持三个地区，每个地区都有对应的语言、时区和 User-Agent：

| 地区 | 语言 | 时区 | 说明 |
|------|------|------|------|
| `usa` | en-US | America/New_York | 美国（默认） |
| `germany` | de-DE | Europe/Berlin | 德国 |
| `japan` | ja-JP | Asia/Tokyo | 日本 |

### 浏览器配置

```yaml
browser:
  # 浏览器类型
  type: "edge"  # chrome 或 edge（推荐 edge）
  
  # WebDriver 获取策略
  # auto: 自动尝试所有方式
  # manager: 仅使用 webdriver-manager 自动下载
  # system: 仅使用系统 PATH 中的驱动
  # local: 仅使用本地目录的驱动文件
  driver_strategy: "auto"
  
  # 无头模式（建议调试时关闭）
  headless: false
  
  # 操作延迟（毫秒，模拟人类操作）
  slow_mo: 100
```

## 📁 项目结构

```
kiro-auto-register/
├── config/                    # 配置文件
│   ├── config.yaml           # 主配置文件
│   └── languages.yaml        # 多语言配置
├── src/
│   ├── config.py             # 配置加载
│   ├── helpers/              # 工具模块
│   │   ├── browser_factory.py    # 浏览器工厂
│   │   ├── ip_location.py        # IP 定位
│   │   ├── multilang.py          # 多语言支持
│   │   └── utils.py              # 工具函数
│   ├── managers/             # 管理器
│   │   └── proxy_manager.py      # 代理管理器
│   ├── services/             # 服务模块
│   │   ├── email_service.py      # 邮箱服务
│   │   ├── kiro_oauth.py         # Kiro OAuth
│   │   ├── aws_sso_oidc.py       # AWS SSO OIDC
│   │   └── outlook_service.py    # Outlook 服务（可选）
│   └── runners/              # 运行脚本
│       ├── main.py               # 主程序
│       ├── smart_run.py          # 智能运行
│       └── batch_run.py          # 批量运行
├── accounts.json             # 账号保存文件（自动生成）
├── requirements.txt          # Python 依赖
└── README.md                 # 本文件
```
### 调试模式

如果遇到问题，启用调试功能：

```bash
python src/runners/debug_aws_login.py
```

会在每个步骤保存截图，方便排查问题。

## 📊 输出格式

账号信息保存在 [`accounts.json`](accounts.json) 文件中：

```json
[
  {
    "email": "example@domain.com",
    "password": "Abc123!@#",
    "name": "John Doe",
    "created_at": "2026-01-16 12:51:58",
    "status": "aws_sso_authorized",
    
    // Kiro OAuth Token
    "kiro_access_token": "aoaAAAAA...",
    "kiro_csrf_token": "5DeDWVSt...",
    "kiro_refresh_token": "AAAADmtl...",
    "kiro_expires_in": 604800,
    
    // AWS SSO OIDC Token (用于 Kiro Account Manager)
    "aws_sso_refresh_token": "aorAAAAA...",  // aor 开头
    "aws_sso_client_id": "HZ6-Q9bO...",
    "aws_sso_client_secret": "eyJraWQi...",
    "aws_sso_access_token": "aoaAAAAA...",
    "aws_sso_region": "us-east-1",
    "aws_sso_provider": "BuilderId"
  }
]
```

### Token 说明

1. **Kiro Access Token** - 用于访问 AWS Kiro 服务
2. **AWS SSO Refresh Token** - 用于导入到 Kiro Account Manager（`aor` 开头）
3. **Client ID/Secret** - AWS SSO OIDC 客户端凭据



## 📝 注意事项

1. **代理建议** - 强烈建议使用代理，避免 IP 被限制
2. **间隔时间** - 批量注册时建议设置 30 秒以上的间隔
3. **成功率** - 受网络环境影响，建议使用稳定的代理服务
4. **合规使用** - 请遵守 AWS 服务条款，仅用于学习和测试

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)

## 🙏 致谢

- 临时邮箱服务：[mail.chatgpt.org.uk](https://mail.chatgpt.org.uk)

## 🔗 相关链接

- [AWS Builder ID 官网](https://builder.aws.com)
- [Kiro Account Manager](https://kiro.aws.dev)
- [AWS CodeWhisperer](https://aws.amazon.com/codewhisperer/)

---
