# 上线部署详细步骤

本文档按顺序列出从零到生产可用的完整步骤，便于在服务器上**一次性完成上线**。按顺序执行且环境匹配（Linux + PostgreSQL + Python 3.10+）时，可一次安装部署成功；若某步报错，请对照第七章「常见问题」和日志排查。

---

## 一、前置准备

### 1.1 服务器与环境

- **系统**：Linux（推荐 Ubuntu 22.04 / Debian 12 / CentOS 7+）
- **权限**：能安装软件、写文件、开放端口（如 80/443）
- **网络**：服务器可访问外网（安装依赖、企业微信 API）；若仅内网使用，需能访问 PostgreSQL 和企业微信

### 1.2 需提前准备的信息

| 项 | 说明 | 示例 |
|----|------|------|
| 公网域名或内网地址 | 用户访问的地址，需 HTTPS（企业微信要求） | `https://device.xxx.edu.cn` |
| PostgreSQL 数据库 | 库名、用户名、密码、主机与端口 | 见下方 2.1 |
| JWT 密钥 | 生产用随机字符串，至少 32 位 | 见下方 3.2 |
| 企业微信（可选） | 企业 ID、应用 AgentId、Secret、可信域名 | 见 `docs/WECOM_SETUP.md` |
| 院内访问控制（可选） | 管理后台允许的 Origin 或 IP | 见下方 3.4 |

---

## 二、安装依赖

### 2.1 安装 PostgreSQL

**Ubuntu/Debian：**

```bash
sudo apt update
sudo apt install -y postgresql postgresql-client
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

创建数据库与用户（按需修改库名、用户名、密码）：

```bash
sudo -u postgres psql -c "CREATE USER device_scan WITH PASSWORD '你的数据库密码';"
sudo -u postgres psql -c "CREATE DATABASE device_scan OWNER device_scan;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE device_scan TO device_scan;"
```

**CentOS/RHEL：**

```bash
sudo yum install -y postgresql-server postgresql
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
# 再同上用 psql 创建用户和库
```

### 2.2 安装 Python 3.10+ 与 Poetry

**Ubuntu 22.04（通常自带 3.10）：**

```bash
sudo apt install -y python3 python3-pip python3-venv
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -
# 将 Poetry 加入 PATH（按安装完成时的提示执行，例如）：
export PATH="$HOME/.local/bin:$PATH"
```

**若系统 Python 版本不足 3.10：**

```bash
# Ubuntu: 使用 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
# 用 python3.10 安装 Poetry 后，Poetry 会使用 3.10 创建虚拟环境
```

验证：

```bash
python3 --version   # 应为 3.10+
poetry --version
```

### 2.3 安装系统依赖（PDF 导出可选）

若使用 PDF 导出，需中文字体。例如：

```bash
sudo apt install -y fonts-wqy-zenhei fonts-wqy-microhei
# 或把 TTF 字体放到 backend/static/fonts/ 并在代码中引用
```

---

## 三、部署应用代码

### 3.1 上传代码到服务器

- 用 **git**（推荐）：在服务器上 `git clone` 你的仓库，或 `git pull` 到已有目录。
- 或用 **rsync/scp** 上传整个项目目录（不要上传 `backend/.env`，在服务器上新建）。

示例（git）：

```bash
cd /opt
sudo git clone https://你的仓库地址.git device_scan
cd device_scan
# 如需要指定分支：git checkout main
# 若用 systemd 以 www-data 运行，需赋予该用户读权限：
# sudo chown -R www-data:www-data /opt/device_scan
```

目录结构应类似：

```
/opt/device_scan/          # 项目根目录（含 backend 的上一级）
├── .env                   # 在项目根创建（见 3.2），应用从工作目录读 .env
├── backend/
│   ├── main.py
│   ├── pyproject.toml
│   ├── poetry.lock
│   ├── templates/
│   └── static/
└── docs/
```

说明：应用以**项目根**为工作目录启动，**`.env` 必须放在项目根**（`/opt/device_scan/.env`），否则读不到配置。

### 3.2 配置环境变量（生产必读）

在**项目根目录**创建 `.env`（应用启动时工作目录是项目根，会从这里读取 `.env`）：

```bash
cd /opt/device_scan
cp backend/.env.example .env
nano .env   # 或用 vi/vim
```

**必须修改的项：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `ENVIRONMENT` | 生产必须设为 `production` | `production` |
| `JWT_SECRET` | 生产用随机长字符串，**不可**用默认值 | 用 `openssl rand -hex 32` 生成 |
| `DATABASE_URL` | 数据库连接串 | `postgresql+psycopg2://device_scan:你的密码@localhost:5432/device_scan` |
| `BASE_URL` | 用户访问的完整根地址，**必须 HTTPS**（企微要求） | `https://device.xxx.edu.cn` |

**生成 JWT_SECRET：**

```bash
openssl rand -hex 32
# 将输出复制到 .env 的 JWT_SECRET=
```

**推荐配置的项（生产）：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `ALLOWED_ADMIN_ORIGINS` | 允许访问 /admin、/docs 的 Origin，逗号分隔 | `https://device.xxx.edu.cn` |
| `ALLOWED_ADMIN_IPS` | 允许的 IP 或 CIDR，逗号分隔 | `192.168.0.0/16,10.0.0.0/8` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 首次管理员账号密码（可选，首次登录自动建 sys_admin） | 按需设置 |
| `WECOM_CORP_ID` / `WECOM_AGENT_ID` / `WECOM_SECRET` | 企业微信登录，见 `docs/WECOM_SETUP.md` | 按企微后台填写 |

**.env 示例（最小生产配置）：**

```env
ENVIRONMENT=production
JWT_SECRET=这里填上面 openssl 生成的 64 位十六进制
DATABASE_URL=postgresql+psycopg2://device_scan:你的密码@localhost:5432/device_scan
BASE_URL=https://device.xxx.edu.cn

# 院内访问（二选一或都配）
ALLOWED_ADMIN_ORIGINS=https://device.xxx.edu.cn
# ALLOWED_ADMIN_IPS=192.168.0.0/16
```

保存后确认 **不要** 把 `.env` 提交到 git。若你习惯把 `.env` 放在 `backend/`，需在 systemd 的 `ExecStart` 前通过 `EnvironmentFile` 加载，或改用项目根下的 `.env`（推荐）。

### 3.3 安装 Python 依赖并试运行

Poetry 项目在 **backend** 目录，在 **backend** 下安装依赖：

```bash
cd /opt/device_scan/backend
poetry config virtualenvs.in-project true
poetry install --no-dev
```

虚拟环境会创建在 `backend/.venv`。首次启动会**自动建表 + 写字典种子**（见 `main.py`），无需单独执行迁移（除非你有自定义迁移脚本）。

**前台试运行（确认能起来）：** 必须在**项目根目录**运行，并让 Python 找到 `backend` 包：

```bash
cd /opt/device_scan
export PYTHONPATH=/opt/device_scan
/opt/device_scan/backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

在服务器本机或同网机器访问：

- `http://服务器IP:8000/health` 应返回 `{"status":"ok"}`
- `http://服务器IP:8000/` 应返回 API 欢迎信息

确认无误后 `Ctrl+C` 停止，再进行下一步。

---

## 四、使用 systemd 常驻运行（推荐）

### 4.1 创建 systemd 服务文件

```bash
sudo nano /etc/systemd/system/device-scan.service
```

写入（路径按你实际部署修改）：

```ini
[Unit]
Description=设备扫码登记系统
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/device_scan
Environment=PYTHONPATH=/opt/device_scan
ExecStart=/opt/device_scan/backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

注意：

- `User/Group`：若没有 `www-data`，可改为 `root` 或你用于运行服务的用户。
- `WorkingDirectory` 必须是**项目根目录**（即 `/opt/device_scan`，含 `backend` 的目录）；**PYTHONPATH** 也指向该目录，这样 `backend.main:app` 才能被正确加载。
- 若虚拟环境不在 `/opt/device_scan/backend/.venv`，把 `ExecStart` 中的路径改成实际路径（在 backend 目录下执行 `poetry env info -p` 可查看）。

### 4.2 启动并开机自启

```bash
sudo systemctl daemon-reload
sudo systemctl enable device-scan
sudo systemctl start device-scan
sudo systemctl status device-scan
```

查看日志：

```bash
sudo journalctl -u device-scan -f
```

---

## 五、配置 Nginx 反向代理（HTTPS）

若用户通过域名访问且需 HTTPS（企业微信要求可信域名为 https），可用 Nginx 做反向代理并配 SSL。

### 5.1 安装 Nginx 与证书

```bash
sudo apt install -y nginx
# 证书：用校内/云厂商的证书，或 Let's Encrypt
# 例如 Let's Encrypt：
# sudo apt install certbot python3-certbot-nginx
# sudo certbot --nginx -d device.xxx.edu.cn
```

### 5.2 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/device-scan
```

示例（请替换域名和证书路径）：

```nginx
server {
    listen 80;
    server_name device.xxx.edu.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name device.xxx.edu.cn;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/device-scan /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 六、上线后检查清单

按顺序自检：

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 访问 `https://你的域名/health` | `{"status":"ok"}` |
| 2 | 访问 `https://你的域名/` | API 欢迎信息 |
| 3 | 访问 `https://你的域名/h5/scan` | H5 登记页 |
| 4 | 访问 `https://你的域名/h5/my-records` | 我的记录页（可能提示登录） |
| 5 | 访问 `https://你的域名/admin` | 管理后台登录页（若配了院内访问，需在允许的 Origin/IP 下访问） |
| 6 | 管理员登录（ADMIN_USERNAME/ADMIN_PASSWORD 或企微） | 能进后台、看设备/使用记录/审计 |
| 7 | H5 登记一条记录 | 我的记录中可见；管理端使用记录中可见 |

若 **ENVIRONMENT=production** 且 **JWT_SECRET** 仍为默认值，应用会**拒绝启动**并报错，需按 3.2 修改 `.env`。

---

## 七、常见问题

**Q：启动报 “生产环境必须设置 JWT_SECRET”**  
A：在**项目根**的 `.env`（如 `/opt/device_scan/.env`）中设置 `ENVIRONMENT=production` 且 `JWT_SECRET` 为随机字符串（不要用 `change-me-in-production`）。**.env 必须在项目根**，因应用以项目根为工作目录启动，只从当前目录读 `.env`。

**Q：配置都写了但应用仍用默认值**  
A：确认 `.env` 在**项目根**（与 `backend` 同级），而不是仅在 `backend/` 下；否则 `load_dotenv()` 读不到。

**Q：企业微信登录失败 / 回调 404**  
A：检查 `BASE_URL` 是否为 https、与企微应用「可信域名」一致；回调地址为 `{BASE_URL}/api/auth/wecom/callback`。详见 `docs/WECOM_SETUP.md`。

**Q：访问 /admin 或 /docs 被拒绝**  
A：若配置了 `ALLOWED_ADMIN_ORIGINS` 或 `ALLOWED_ADMIN_IPS`，需从允许的域名或 IP 访问；或暂时清空这两项再试（仅建议用于排查）。

**Q：如何更新代码后再上线？**  
A：在服务器上 `git pull`（或重新上传代码），在 **backend** 目录执行 `poetry install --no-dev`，再 `sudo systemctl restart device-scan`。`.env` 在项目根时无需改动。如有数据库结构变更，需按项目说明执行迁移脚本。

**Q：日志与排错**  
A：`sudo journalctl -u device-scan -f` 查看应用日志；Nginx 错误日志一般在 `/var/log/nginx/error.log`。

---

## 八、步骤速查（无 Nginx 时最小流程）

1. 安装 PostgreSQL，建库建用户。  
2. 安装 Python 3.10+、Poetry；`cd backend && poetry install --no-dev`。  
3. 在**项目根**的 `.env` 配置：`ENVIRONMENT=production`、`JWT_SECRET`（随机）、`DATABASE_URL`、`BASE_URL`（最终访问地址）。  
4. 试运行：在项目根执行 `PYTHONPATH=$(pwd) backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000`，访问 `http://服务器IP:8000/health` 确认。  
5. 配置 systemd 服务（WorkingDirectory=项目根、PYTHONPATH=项目根、ExecStart 用 backend/.venv 里的 uvicorn），`systemctl enable --now device-scan`。  
6. 若需 HTTPS，再配 Nginx 反向代理与证书。  
7. 按第六章做一次上线检查。

完成以上步骤即可上线使用。若有校内统一入口或防火墙策略，需在对应平台放行 80/443 或后端 8000 端口。
