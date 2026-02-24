"""
设备编码规范化：从「扫码/识别结果」中只取出用于查询的编码。
支持：自有生成码（纯编号或 URL）、现有资产码（多行或单行「编码+文字」）。
"""
import re
from typing import Optional


def normalize_device_code(raw: Optional[str]) -> str:
    """
    从可能包含多行或「编码+文字」的识别结果中，只取出设备编码（用于查库、写库）。
    - 多行：优先匹配「资产编号：xxx」或「编码：xxx」，否则取第一行再取首段编码。
    - 单行：取行首连续数字/字母（含 -_）直到空格或中文。
    """
    if not raw or not isinstance(raw, str):
        return (raw or "").strip()
    s = raw.strip()
    if not s:
        return s
    lines = [
        ln.strip()
        for ln in s.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if ln.strip()
    ]
    for line in lines:
        if "资产编号" in line and "：" in line:
            idx = line.find("：")
            if idx >= 0:
                after = line[idx + 1 :].strip()
                if after:
                    return _first_code_token(after)
        if "编码" in line and "：" in line:
            # 避免把「资产编号」里的「编码」当关键字
            before_colon = line.split("：", 1)[0]
            if "资产编号" in before_colon:
                continue
            idx = line.find("：")
            if idx >= 0:
                after = line[idx + 1 :].strip()
                if after:
                    return _first_code_token(after)
    first_line = lines[0] if lines else s
    return _first_code_token(first_line)


def _first_code_token(text: str) -> str:
    """取字符串开头连续的数字/字母（含 -_），直到空格或中文等。"""
    text = text.strip()
    if not text:
        return text
    m = re.match(r"^([0-9A-Za-z\-_]+)", text)
    if m:
        return m.group(1)
    return text
