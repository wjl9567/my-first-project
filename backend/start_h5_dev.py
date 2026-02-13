"""
H5 前端调试：启动后端并自动打开「设备使用维护登记」页面，便于直接做 H5 功能测试与验证。
在 backend 目录执行: poetry run python start_h5_dev.py
"""
import sys
import time
import webbrowser
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
H5_SCAN_URL = f"http://{HOST}:{PORT}/h5/scan"
ADMIN_URL = f"http://{HOST}:{PORT}/admin"


def main():
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open(H5_SCAN_URL)
        except Exception:
            pass

    import threading
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    print("=" * 60)
    print("  H5 前端调试：服务启动后会自动打开登记页")
    print("=" * 60)
    print(f"  登记页（自动打开）: {H5_SCAN_URL}")
    print(f"  后台登录（需先登录才能登记）: {ADMIN_URL}")
    print(f"  我的记录: http://{HOST}:{PORT}/h5/my-records")
    print("=" * 60)
    print("  若未自动打开，请复制上面「登记页」地址到浏览器。")
    print("  调试：按 F12 打开开发者工具 → Console 看报错，Network 看接口。")
    print("=" * 60)

    try:
        uvicorn.run(
            "backend.main:app",
            host=HOST,
            port=PORT,
            reload=True,
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
