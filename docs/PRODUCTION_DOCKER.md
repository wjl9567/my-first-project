# 生产级一站式部署方案（Docker Compose）

本文档面向生产环境：**上传代码 → 修改配置 → 执行 1～2 条命令**即可完成部署。覆盖 Docker、Nginx、HTTPS、JWT_SECRET、PostgreSQL 数据持久化、开机自启与日志轮转。

---

## 零、交给运维：文件在哪里、怎么给

**给运维时**需要保证他们拿到「完整项目 + 部署文档」。下面是要发过去的**部署相关文件位置**和**两种交付方式**。

### 部署相关文件位置（均在项目内）

| 文件 | 在项目中的路径 | 说明 |
|------|----------------|------|
| 部署主文档 | `docs/PRODUCTION_DOCKER.md` | 运维按此文档操作 |
| 应用镜像定义 | `Dockerfile` | 项目根目录 |
| 编排与数据卷 | `docker-compose.yml` | 项目根目录 |
| 一键部署脚本 | `deploy.sh` | 项目根目录 |
| 环境变量模板 | `.env.template` | 项目根目录（运维复制为 `.env` 再填写） |
| Nginx 主配置（HTTPS） | `nginx/nginx.conf` | 需把其中的 `your-domain.com` 改成实际域名 |
| Nginx 仅 HTTP 配置 | `nginx/nginx-http-only.conf` | 无证书时先用此配置 |
| 证书目录占位 | `nginx/ssl/.gitkeep` | 证书申请后放入 `nginx/ssl/`（fullchain.pem、privkey.pem） |
| 应用代码与依赖定义 | `backend/` 整个目录 | 含 `pyproject.toml`、`poetry.lock`、所有 .py、templates、static 等 |

**不需要**发给运维或不要打包进去：`.env`（含密码）、`backend/.env`、`backend/.venv/`、`backend/__pycache__/`、`nginx/ssl/*.pem`（证书在服务器上单独申请）。

### 方式一：通过 Git（推荐）

**你这边（开发/项目负责人）：**

1. 把当前代码（含上述所有部署文件）推送到公司 Git 仓库（GitLab/Gitee/自建等）。
2. 把**仓库地址 + 分支名**发给运维，并说明：「按仓库里的 `docs/PRODUCTION_DOCKER.md` 部署」。

**运维那边：**

在服务器上执行（把 `<仓库地址>`、`<分支名>` 换成实际值）：

```bash
git clone -b <分支名> <仓库地址> /opt/device-scan
cd /opt/device-scan
# 然后按本文档「三、部署步骤」操作
```

例如：

```bash
git clone -b main https://your-git.company.com/team/device-scan.git /opt/device-scan
cd /opt/device-scan
```

**没有 Git 仓库时**：可在你本机打一个「无远程」的 bundle 发给运维，他们在服务器上用 `git clone device-scan.bundle /opt/device-scan` 得到完整项目（见下方「方式二」里的 bundle 命令）。

### 方式二：打包整个项目

**你这边：** 在**项目根目录的上一级**执行打包，这样压缩包里会带一层「项目根目录」，运维解压后直接得到完整项目文件夹。

**Windows（PowerShell）：**

```powershell
# 进入项目所在目录（例如桌面上的 device_scan_code）
cd c:\Users\16539\Desktop\device_scan_code

# 打成 zip，排除缓存和敏感文件（把 my-first-project 换成你的项目文件夹名）
# 若需排除 __pycache__、.venv，可先复制一份再打 zip，或使用 7-Zip 的排除列表
Compress-Archive -Path my-first-project\backend, my-first-project\docs, my-first-project\nginx, my-first-project\Dockerfile, my-first-project\docker-compose.yml, my-first-project\deploy.sh, my-first-project\.env.template, my-first-project\.gitignore, my-first-project\readme.md, my-first-project\SRS.md -DestinationPath $env:USERPROFILE\Desktop\device-scan-deploy.zip
```

更稳妥：直接打包**整个项目文件夹**（手动删除其中的 `backend\.venv`、`backend\__pycache__`、`.env` 后再打包），这样不会漏文件：

```powershell
cd c:\Users\16539\Desktop\device_scan_code
# 打包整份 my-first-project（确保内含 backend、docs、nginx、Dockerfile、deploy.sh、.env.template）
Compress-Archive -Path my-first-project -DestinationPath $env:USERPROFILE\Desktop\device-scan-deploy.zip
```

**Linux / Git Bash / WSL：**

```bash
# 在项目根目录的上一级执行，得到 device-scan-deploy.tar.gz
cd /path/to/parent
tar --exclude='my-first-project/backend/__pycache__' --exclude='my-first-project/backend/.venv' --exclude='my-first-project/backend/.env' --exclude='my-first-project/.env' --exclude='my-first-project/nginx/ssl/*.pem' -czvf device-scan-deploy.tar.gz my-first-project
```

**运维那边：** 上传 zip 或 tar.gz 到服务器后解压，进入**含 Dockerfile 的那一层**再部署：

```bash
# 解压（得到 my-first-project/ 或 device-scan/ 等一个目录）
unzip device-scan-deploy.zip -d /opt
# 或
tar -xzvf device-scan-deploy.tar.gz -C /opt

# 进入项目根（目录名以你打包为准）
cd /opt/my-first-project
# 然后按本文档「三、部署步骤」执行：cp .env.template .env、编辑 .env、./deploy.sh
```

**注意**：打包必须包含**整个 `backend/`**（含 `pyproject.toml`、`poetry.lock`、所有 .py、templates、static），否则镜像构建会失败。

---

## 一、服务器环境准备

### 1.1 安装 Docker 与 Docker Compose

以下命令在 **CentOS 7/8** 与 **Ubuntu 20.04/22.04** 上通用（按系统二选一执行）。

**Ubuntu 20.04 / 22.04：**

```bash
# 安装 Docker
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 当前用户加入 docker 组（避免每次 sudo）
sudo usermod -aG docker $USER
# 重新登录后生效，或执行：newgrp docker
```

**CentOS 7 / 8：**

```bash
# CentOS 7
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker && sudo systemctl enable docker

# CentOS 8 或 Rocky/Alma
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker && sudo systemctl enable docker
```

**验证：**

```bash
docker --version
docker compose version
```

若使用旧版 standalone docker-compose（无 compose 子命令），可将下文及 `deploy.sh` 中的 `docker compose` 改为 `docker-compose`。

---

## 二、域名与 HTTPS（Let's Encrypt）

企微 OAuth 要求 **BASE_URL 为 HTTPS** 且与企微「可信域名」一致。推荐使用 Let's Encrypt 免费证书。

### 2.1 申请证书（首次）

**方式 A：standalone（需短暂停用占用 80 端口的服务）**

```bash
# 安装 certbot（Ubuntu）
sudo apt install -y certbot

# 申请证书（将 your-domain.com 改为实际域名；申请时 80 端口需空闲）
sudo certbot certonly --standalone -d your-domain.com
# 证书在：/etc/letsencrypt/live/your-domain.com/fullchain.pem 与 privkey.pem
```

**方式 B：webroot（与 Nginx 同时运行）**

先使用项目内 **仅 HTTP** 的 Nginx 配置启动服务（见下文「首次无证书部署」），再执行：

```bash
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d your-domain.com
```

若 Nginx 在 Docker 内，需将宿主机目录挂载到 Nginx 的 `/var/www/certbot`，并在 `nginx.conf` 中保留 `location /.well-known/acme-challenge/`。

**将证书供 Nginx 使用：**

项目默认从 **项目内 nginx/ssl/** 读取证书，便于不暴露宿主机路径。申请完成后复制到项目目录：

```bash
# 在项目根目录执行（替换 your-domain.com）
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
sudo chown -R $(whoami) nginx/ssl
```

然后将 `nginx/nginx.conf` 中的 `server_name your-domain.com` 改为你的域名，确认 `ssl_certificate` / `ssl_certificate_key` 指向 `/etc/nginx/ssl/fullchain.pem` 与 `privkey.pem`（Compose 已挂载 `./nginx/ssl` 到容器内 `/etc/nginx/ssl`）。重启 Nginx：

```bash
docker compose up -d nginx --force-recreate
```

### 2.2 证书自动续期

Let's Encrypt 证书约 90 天有效，建议用 cron 自动续期并重载 Nginx：

```bash
# 编辑 crontab
sudo crontab -e
# 添加（每月 1 日 3 点续期，并复制到 nginx/ssl、重启 nginx 容器）
0 3 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/your-domain.com/*.pem /path/to/project/nginx/ssl/ && cd /path/to/project && docker compose exec nginx nginx -s reload
```

将 `/path/to/project` 替换为项目在服务器上的实际路径。

---

## 三、部署步骤（一键流程）

### 3.1 上传代码

将项目（含 `backend/`、`Dockerfile`、`docker-compose.yml`、`nginx/`、`.env.template`、`deploy.sh`）上传到服务器，例如：

```bash
git clone <你的仓库> /opt/device-scan && cd /opt/device-scan
```

### 3.2 配置环境变量

```bash
# 复制模板
cp .env.template .env

# 编辑 .env，必填项：
# - JWT_SECRET：随机强密钥，见下文「JWT_SECRET 生成」
# - POSTGRES_PASSWORD：数据库密码
# - BASE_URL：对外 HTTPS 地址，与企微可信域名一致（如 https://device.xxx.edu.cn）
vim .env   # 或 nano .env
```

**JWT_SECRET 生成（32 位以上随机）：**

```bash
openssl rand -hex 32
# 将输出填入 .env：JWT_SECRET=<输出内容>
```

### 3.3 首次无证书时（仅 HTTP）

若尚未申请 HTTPS 证书，先使用仅 HTTP 的 Nginx 配置，避免 Nginx 启动报错：

```bash
cp nginx/nginx-http-only.conf nginx/nginx.conf
```

之后申请证书并放入 `nginx/ssl/` 后，再换回完整 `nginx/nginx.conf`（含 SSL）并重启 nginx 容器。

### 3.4 一键启动

```bash
chmod +x deploy.sh
./deploy.sh
```

脚本会检查 `.env`、`JWT_SECRET`、`POSTGRES_PASSWORD`，若无证书会提示并可选替换为仅 HTTP 配置，然后执行 `docker compose build` 与 `docker compose up -d`。

**若希望分步执行：**

```bash
docker compose build --no-cache
docker compose up -d
```

---

## 四、验证

在服务器本机或同网机器执行：

```bash
# 健康检查（端口 80 由 Nginx 监听）
curl -s http://localhost/health
# 期望输出：{"status":"ok"}

# 若仅本机可访问，用服务器 IP 或域名从外网测：
curl -s https://your-domain.com/health
```

- **页面访问**：浏览器打开 `https://your-domain.com` 或 `http://<服务器IP>`（仅 HTTP 时）。
- **数据库连接**：  
  `docker compose exec postgres psql -U device_scan -d device_scan -c 'SELECT 1'`  
  应返回一行结果。

---

## 五、安全与运维

### 5.1 开机自启

Docker 服务与 Compose 容器均设为 `restart: unless-stopped`，宿主机重启后容器会自动起来。若需在未登录时也自动启动 Compose 栈，可用 systemd：

```bash
# 创建服务文件（路径按实际修改）
sudo tee /etc/systemd/system/device-scan.service << 'EOF'
[Unit]
Description=Device Scan Docker Compose
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/device-scan
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable device-scan
sudo systemctl start device-scan
```

### 5.2 日志

- **查看应用日志**：`docker compose logs -f app`
- **查看 Nginx 日志**：`docker compose logs -f nginx`
- **查看数据库日志**：`docker compose logs -f postgres`
- **导出最近 1000 行**：`docker compose logs --tail=1000 app > app.log`

**容器日志轮转**：在 `/etc/docker/daemon.json` 中配置（如无该文件则新建）：

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

然后执行 `sudo systemctl restart docker`。仅对**新创建的容器**生效，已有容器需重建：`docker compose up -d --force-recreate`。

### 5.3 代码更新后重新部署

```bash
cd /opt/device-scan   # 或你的项目路径
git pull
docker compose build app
docker compose up -d
```

数据库在 volume `postgres_data` 中，不会因重新构建或替换 app 镜像而丢失。

---

## 六、配置文件说明速查

| 文件 | 说明 |
|------|------|
| `Dockerfile` | 应用镜像：Python 3.10 + Poetry 安装依赖，PYTHONPATH=/app，Uvicorn 单进程 |
| `docker-compose.yml` | 三服务：app、postgres、nginx；PostgreSQL 数据卷 `postgres_data`；敏感项通过 environment 注入 |
| `nginx/nginx.conf` | 反向代理、HTTPS、静态缓存、超时；部署前替换 `your-domain.com` 与确认证书路径 |
| `nginx/nginx-http-only.conf` | 仅 HTTP，用于首次部署或无证书时 |
| `.env.template` | 环境变量模板，必填：JWT_SECRET、POSTGRES_PASSWORD、BASE_URL |
| `deploy.sh` | 检查 .env/JWT_SECRET/证书，执行 build 与 up |

---

## 七、常见问题

- **应用启动报错「生产环境必须设置 JWT_SECRET」**  
  在 `.env` 中设置 `JWT_SECRET` 为随机值（非 `change-me-in-production`），并确保 Compose 能读到（不要改 docker-compose 里 ENVIRONMENT=production）。

- **Nginx 启动失败**  
  若使用带 SSL 的 `nginx.conf` 但未放置证书，会报错。先用 `cp nginx/nginx-http-only.conf nginx/nginx.conf` 或把证书放入 `nginx/ssl/` 后再启动。

- **企微登录或 H5 异常**  
  确认 `BASE_URL` 为 HTTPS 且与企微后台「可信域名」完全一致（含协议、无尾斜杠）。

- **宿主机 80/443 已被占用**  
  在 `docker-compose.yml` 的 nginx 的 `ports` 中修改映射，如 `"8080:80" "8443:443"`，访问时使用对应端口。

以上步骤完成后，服务器上仅需**上传代码、修改 .env、执行 `./deploy.sh`（或两条命令 build + up）**即可完成生产级一站式部署。
