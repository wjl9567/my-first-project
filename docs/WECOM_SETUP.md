# 企业微信配置说明（设备扫码登记系统）

本系统使用**企业微信自建应用**的网页授权登录。按下面步骤在企微后台和项目里配置即可在企微内扫码打开 H5 并完成登录。

---

## 一、在企业微信管理后台获取参数

登录 [企业微信管理后台](https://work.weixin.qq.com/)。

### 1. 获取企业 ID（CorpID）

- 路径：**我的企业** → **企业信息**
- 在页面中找到 **企业ID**，复制保存，即 `WECOM_CORP_ID`（注意是 **WECOM_CORP_ID**，不是 WECOM_CORPID）。

### 2. 创建/选择自建应用并获取 AgentId、Secret

- 路径：**应用管理** → **应用** → **自建**
- 若还没有应用：点击 **创建应用**，填写名称（如「设备扫码登记」）、上传 logo、选择可见范围后创建。
- 进入该应用详情页：
  - **AgentId**：在应用详情页可直接看到（有时写为「应用 ID」）。
  - **Secret**：同一页面中 **Secret** 或「应用凭证」一栏，点击「查看」后复制（仅首次或重置后可见，请妥善保存）。

### 3. 配置可信域名（必做，否则授权会报错）

- 仍在**该自建应用**内，找到 **网页授权及 JS-SDK** 或 **企业微信授权** 相关配置。
- 在 **可信域名** 中填写**你的后端访问域名**：
  - **仅填域名**，不要带 `http://`、`https://` 或路径。  
    例如：`your-server.com` 或 `device.xxx-hospital.com`。
  - **不能填** `127.0.0.1` 或 `localhost`（企微不认）。  
    本地调试可用内网穿透（如 ngrok、cpolar）获得一个 HTTPS 域名，把该域名填到可信域名。
  - 生产环境：填你部署后实际访问的域名（需 HTTPS）。

本系统回调地址为：`{你的域名}/api/auth/wecom/callback`，可信域名必须与「访问后端时使用的域名」一致。

---

## 二、在项目里配置 .env

在项目 **backend** 目录下编辑 `.env`（可先复制 `.env.example`），填写：

```env
# 数据库（保持你现有的即可）
DATABASE_URL=postgresql+psycopg2://postgres:kwabc123@localhost:5432/device_scan

# 企业微信（从上面步骤 1、2 复制过来）
WECOM_CORP_ID=你的企业ID
WECOM_AGENT_ID=你的AgentId
WECOM_SECRET=你的Secret

# 后端访问地址（用于拼登录回调 URL 和登录后跳转）
# 本地调试且用内网穿透时：填穿透后的地址，如 https://xxx.ngrok.io
# 生产：填实际域名，如 https://device.xxx-hospital.com
BASE_URL=https://你的域名

# JWT（生产环境务必改成随机字符串）
JWT_SECRET=change-me-in-production
```

注意：

- 变量名是 **WECOM_CORP_ID**（中间有下划线），不是 `WECOM_CORPID`。
- `BASE_URL` 的**域名部分**必须与企微后台里该应用的**可信域名**一致，且使用 HTTPS（生产/穿透时）。

---

## 三、与 routes_auth 的对应关系

| 项目配置 / 企微后台     | 本系统用途 |
|-------------------------|------------|
| 可信域名                | 必须与 `BASE_URL` 的域名一致，否则 `redirect_uri` 不合法。 |
| 回调 URL（实际）        | `{BASE_URL}/api/auth/wecom/callback`（代码里在 `routes_auth` 中写死路径）。 |
| 登录入口                | 浏览器或企微内打开：`{BASE_URL}/api/auth/wecom/login?next_path=/h5/scan`。 |

无需在企微后台再单独填「回调 URL」；只要可信域名正确，回调地址由代码中的 `BASE_URL + "/api/auth/wecom/callback"` 自动拼出。

---

## 四、本地调试（无公网域名时）

1. 使用内网穿透（如 [ngrok](https://ngrok.com/)、[cpolar](https://www.cpolar.com/)）把本机 `http://127.0.0.1:8000` 暴露为一个 **HTTPS** 公网地址，例如 `https://abc123.ngrok.io`。
2. 企微后台该应用的**可信域名**填：`abc123.ngrok.io`（无协议、无路径）。
3. `.env` 中：`BASE_URL=https://abc123.ngrok.io`。
4. 启动后端：`poetry run python run.py`。
5. 在手机企业微信中打开：`https://abc123.ngrok.io/api/auth/wecom/login?next_path=/h5/scan`，即可走通授权并跳转到登记页。

---

## 五、配置完成后

- **未配置企微**：访问 `/api/auth/wecom/login` 会返回 503；H5 仍可直接用浏览器打开（如 `/h5/scan`），用于功能测试。
- **已配置**：在企业微信内打开登录链接，授权后会跳转到 H5 并带上 token；需要管理员权限时，在数据库表 `users` 中把对应用户的 `role` 改为 `device_admin` 或 `sys_admin`。

如有报错「redirect_uri 需使用应用可信域名」，请检查：可信域名是否与 `BASE_URL` 的域名完全一致、是否未带 `http(s)://` 或路径。
