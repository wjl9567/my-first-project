"""
启动脚本：在 backend 目录下执行 poetry run python run.py 即可。
会把项目根目录加入 Python 路径，再启动 uvicorn。
"""
import sys
from pathlib import Path

# 项目根目录 = backend 的上一级
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn


def main():
    # 只绑定 127.0.0.1，避免 VPN/多网卡导致无法访问；需局域网访问时改为 0.0.0.0
    host = "127.0.0.1"
    port = 8010
    print(f"启动中: http://{host}:{port}  后台: http://{host}:{port}/admin")
    try:
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            reload=True,
        )
    except KeyboardInterrupt:
        print("\n服务已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
