#!/usr/bin/env bash
# 医院设备扫码登记系统 - 一键部署脚本
# 作用：检查配置 -> 构建镜像 -> 启动容器；首次部署前请复制 .env.template 为 .env 并填写必填项
set -e

cd "$(dirname "$0")"

if [ ! -f docker-compose.yml ]; then
  echo "错误：请在项目根目录（含 docker-compose.yml）执行 ./deploy.sh"
  exit 1
fi

# 1. 检查 .env
if [ ! -f .env ]; then
  echo "未找到 .env，已从 .env.template 复制，请编辑 .env 填写 JWT_SECRET、POSTGRES_PASSWORD、BASE_URL 后重新执行本脚本"
  cp -f .env.template .env
  exit 1
fi

# 2. 检查 JWT_SECRET（必填且不能为默认值）
source .env 2>/dev/null || true
if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "change-me-in-production" ]; then
  echo "错误：生产环境必须设置 JWT_SECRET 且不可为默认值。"
  echo "生成随机密钥：openssl rand -hex 32"
  echo "将输出填入 .env 的 JWT_SECRET= 后重新执行 ./deploy.sh"
  exit 1
fi

# 3. 检查 POSTGRES_PASSWORD
if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "your-postgres-password" ]; then
  echo "错误：请在 .env 中设置安全的 POSTGRES_PASSWORD"
  exit 1
fi

# 4. HTTPS 证书（可选：无证书时使用仅 HTTP 配置）
if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
  echo "提示：未检测到 nginx/ssl 证书，将使用仅 HTTP 配置（端口 80）。"
  echo "若需 HTTPS，请先申请证书并放入 nginx/ssl/ 后，用 nginx/nginx.conf 替换当前 nginx 配置并重启 nginx 容器。"
  if [ -f nginx/nginx.conf ] && grep -q "ssl_certificate " nginx/nginx.conf 2>/dev/null; then
    echo "当前 nginx.conf 含 SSL 配置，可能导致 nginx 启动失败。建议临时使用：cp nginx/nginx-http-only.conf nginx/nginx.conf"
    read -p "是否自动替换为仅 HTTP 配置？[y/N] " -n 1 -r; echo
    if [[ $REPLY =~ ^[yY]$ ]]; then
      cp -f nginx/nginx-http-only.conf nginx/nginx.conf
    fi
  fi
fi

# 5. 构建并启动
echo "正在构建镜像并启动容器..."
docker compose build --no-cache
docker compose up -d

echo ""
echo "部署完成。验证步骤："
echo "  健康检查: curl -s http://localhost/health  或 curl -s http://localhost:80/health"
echo "  页面访问: 浏览器打开 http://<服务器IP> 或 https://<域名>（若已配置 SSL）"
echo "  数据库:   docker compose exec postgres psql -U \${POSTGRES_USER:-device_scan} -d \${POSTGRES_DB:-device_scan} -c 'SELECT 1'"
echo "  应用日志: docker compose logs -f app"
echo "  更新部署: git pull && docker compose build app && docker compose up -d"
