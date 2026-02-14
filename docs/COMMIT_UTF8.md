# 提交与文档编码说明（避免 GitHub 乱码）

本仓库要求**所有文档与提交信息使用 UTF-8 编码**，以便在 GitHub 上正确显示中文。

## 文档文件

- 编辑 `.md`、`.txt` 等文档时请**以 UTF-8 保存**（Cursor / VS Code 默认即为 UTF-8）。
- 仓库已通过 `.gitattributes` 将文本类文件统一为 LF 换行，保持跨平台一致。

## 提交信息（commit message）

在 **Windows 命令行 / PowerShell** 下直接写中文提交信息时，可能因编码问题在 GitHub 上显示为乱码。建议任选其一：

1. **用 UTF-8 文件写备注再提交**  
   将提交说明写进一个 UTF-8 文本文件（如 `msg.txt`），然后执行：  
   `git commit -F msg.txt`  
   或修改最近一次提交：  
   `git commit --amend -F msg.txt`

2. **用 Cursor / VS Code 的「源代码管理」提交**  
   在 IDE 的提交框里输入中文，由 IDE 按 UTF-8 提交，一般不会乱码。

提交后可在 GitHub 网页上确认说明是否显示正常。
