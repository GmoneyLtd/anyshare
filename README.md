# anyShare

anyShare 是一个简洁高效的临时文件分享系统, 允许用户上传文件并生成安全链接进行分享。系统支持文件过期时间设置, 管理员后台管理, 以及文件加密保护功能。

## 功能特点

- **文件上传与分享**：支持拖拽上传文件, 自动生成公开和受密码保护的分享链接
- **过期时间设置**：支持设置文件的过期时间(1小时、1天、1周、1个月或永久)
- **文件大小限制**：默认限制上传文件大小为10MB, 可通过环境变量配置
- **管理员后台**：提供文件管理界面, 包括查看所有文件、统计信息和删除文件功能
- **安全性**：自动为每个文件生成唯一哈希值和密码, 支持加密访问
- **匿名访问控制**：可配置是否允许匿名用户上传文件

## 技术栈

- **后端**：Python 3.13+ 与 Bottle 框架
- **服务器**：Waitress WSGI服务器
- **前端**：原生JavaScript、HTML5、CSS3
- **容器化**：Docker 与 Docker Compose 支持
- **数据存储**：SQLite 数据库

## 项目结构

```
anyShare/
├── .dockerignore           # Docker 忽略文件
├── .gitignore              # Git 忽略文件
├── .venv/                  # Python 虚拟环境 (建议不提交)
├── Dockerfile              # Docker 配置文件
├── README.md               # 项目说明文件
├── pycache /            # Python 编译缓存 (建议不提交)
├── app.py                  # Bottle 应用主文件
├── compose.yaml            # Docker Compose 配置文件
├── database.py             # 数据库操作模块
├── log/                    # 日志文件夹 (运行时生成)
├── pyproject.toml          # Python 项目配置文件 (PEP 518)
├── static/                 # 静态资源 (CSS, JS, images, fonts)
│   ├── css/
│   ├── font/
│   ├── image/
│   └── js/
├── upload/                 # 上传文件存储目录 (运行时生成)
├── uv.lock                 # uv 锁文件, 用于确定性构建
└── views/                  # Bottle 模板视图文件 (.html)
├── admin.html
├── error.html
├── index.html
├── login.html
├── password.html
└── upload.html
```

## 安装与启动

### 先决条件

- Docker
- Docker Compose (或 Docker CLI v2+ 中的 `docker compose`)
- Python 3.13+ (如果希望在本地非 Docker 环境运行)
- uv (Python 包安装器, 如果希望在本地非 Docker 环境运行)

### 使用 Docker (推荐)

1.  **克隆仓库**:
    ```bash
    git clone <your-repository-url>
    cd anyshare
    ```
2.  **设置相关目录权限**:
    ```bash
    # 创建目录(如果不存在)
    mkdir -p ./log ./upload

    # 设置权限 - 使用1000:1000(容器内appuser的UID和GID)
    chown -R 1000:1000 ./log ./upload
    chmod 750 ./log ./upload
    ```
3.  **启动服务**:
    使用 Docker Compose:
    ```bash
    docker compose up -d
    ```
    或者 (旧版 Docker Compose):
    ```bash
    docker-compose up -d
    ```
    这将根据 `compose.yaml` 构建并启动服务。

4.  **访问应用**:
    应用将在 `http://localhost:80` (或 `compose.yaml` 中配置的其他端口) 可用。

### 本地开发 (不使用 Docker)

1.  **克隆仓库**:
    ```bash
    git clone https://gitea.apuer.tech/nice/anyShare.git
    cd anyshare
    ```

2.  **创建并激活虚拟环境**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    # .venv\Scripts\activate  # Windows
    ```

3.  **安装依赖**:
    确保已安装 `uv`。如果未安装, 请先安装 `uv` (例如 `pip install uv`)。
    ```bash
    uv sync
    ```

4.  **配置环境变量** (参见下一节 "配置")。

5.  **运行应用**:
    ```bash
    python app.py
    ```
    应用默认将在 `http://localhost:80` 启动 (由 `app.py` 中的 `serve(app, host="0.0.0.0", port=80)` 定义)。

## 配置

应用通过环境变量进行配置。以下是可用的环境变量：

| 环境变量          | 描述                                     | `app.py` 默认值 | `Dockerfile` / `compose.yaml` 示例 |
| ----------------- | ---------------------------------------- | --------------- | ------------------------------------ |
| `ADMIN_USERNAME`  | 管理员用户名                             | `admin`         | `admin`                              |
| `ADMIN_PASSWORD`  | 管理员密码                               | `admin`         | `123456`                             |
| `ANONYMOUS`       | 是否允许匿名上传 (`"true"` 或 `"false"`) | `"true"`        | `"true"`                             |
| `FILE_LIMIT_SIZE` | 最大文件上传大小 (单位 MiB)              | `"10.00"`       | `"10.00"`                            |

**注意**:
- 当使用 Docker (通过 `Dockerfile` 或 `compose.yaml`) 启动时, `Dockerfile` 或 `compose.yaml` 中设置的环境变量会覆盖 `app.py` 中的默认值。
- 对于本地开发, 可以在运行 `python app.py` 前在终端中设置这些环境变量, 或者修改 `app.py` 中的默认值 (不推荐用于生产)。

`compose.yaml` 文件中还定义了卷映射, 用于持久化日志和上传的文件：
-   `./log:/app/log`
-   `./upload:/app/upload`

## 使用说明

### 文件上传

1.  打开浏览器访问应用首页 (例如 `http://localhost:80`)。
2.  可以通过拖拽文件到指定区域或点击选择文件。
3.  选择文件的过期时间(例如：1小时、1天、1周、1个月、永久)。
4.  点击 "上传" 按钮。
5.  上传成功后, 页面会显示文件的访问链接和密码。请务必保存好密码, 因为它是访问文件的凭证。

### 文件访问

1.  在浏览器中打开文件的访问链接。
2.  如果文件设有密码, 系统会提示输入密码。
3.  输入正确的密码后即可下载或查看文件。

### 管理员后台

1.  访问 `/admin` 路径 (例如 `http://localhost:80/admin`)。
2.  使用配置的管理员用户名和密码登录。
3.  管理员后台可以查看当前所有文件的列表、文件大小、上传时间、过期时间、上传者 IP 等信息。
4.  管理员可以查看存储统计信息, 如活跃文件数和已用存储空间。
5.  管理员可以删除不再需要的文件。

## 主要 API 端点

-   `GET /`: 应用首页, 用于文件上传。
-   `POST /upload`: 处理文件上传的接口。
-   `GET /upload?file_info={...}`: 文件上传成功后展示信息的页面。
-   `GET /file?hash=<file_hash>`: 访问文件页面, 如果需要密码会提示输入。
-   `POST /verify`: 验证文件访问密码。
-   `GET /admin`: 管理员登录页面或已登录后的管理仪表盘。
-   `POST /login`: 处理管理员登录请求。
-   `GET /logout`: 管理员登出。
-   `POST /delete/<file_hash>`: (管理员权限) 删除指定文件。
-   `GET /admin/stats`: (管理员权限) 获取管理员统计信息。
-   `GET /api/healthz`: 应用健康检查端点。
-   `GET /static/<filepath:path>`: 提供静态资源服务。

## 贡献

欢迎提交 Pull Request 或 Issue 来改进本项目。

## 许可证

本项目未指定明确的开源许可证。请根据您的需求或组织策略添加合适的许可证。