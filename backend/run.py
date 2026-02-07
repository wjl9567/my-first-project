"""
启动脚本：在 backend 目录下执行 poetry run start 即可。
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
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
