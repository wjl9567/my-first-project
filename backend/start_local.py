"""
本地启动脚本：只监听 127.0.0.1，避免防火墙/多网卡干扰；启动后自动用默认浏览器打开后台。
在 backend 目录执行: poetry run python start_local.py
"""
import sys
import time
import webbrowser
from pathlib import Path

# 项目根目录 = backend 的上一级
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn

# 只绑定本机，避免 VPN/防火墙 拦截
HOST = "127.0.0.1"
PORT = 8010
ADMIN_URL = f"http://{HOST}:{PORT}/admin"


def main():
    # 延迟 2 秒后打开浏览器，给服务启动留时间
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open(ADMIN_URL)
        except Exception:
            pass

    import threading
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    print(f"正在启动服务，仅本机访问: http://{HOST}:{PORT}")
    print(f"启动成功后将自动打开: {ADMIN_URL}")
    print("若未自动打开，请手动在浏览器输入上述地址。")

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
