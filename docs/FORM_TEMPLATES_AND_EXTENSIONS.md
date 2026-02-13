# 登记表单模板与扩展能力说明

## 业务流程概览

设备登记 H5 完整流程：**设备二维码扫描 → 解析设备信息回填 → 操作类型选择 → 联动加载差异化表单模板 → 表单校验 → 数据提交 → 页面跳转（成功后可查看我的记录）**。

- **操作类型**：来源于字典 `GET /api/dict?dict_type=usage_type`（常规使用、借用、维修/故障、校准/质控、其他）。
- **差异化表单**：根据所选操作类型请求 `GET /api/usage/form-schema?usage_type=<code>&dept=<科室>`，按返回的 `template_key` 展示对应表单项（常规使用 / 借用 / 维修 / 校准 / 其他）。

## 字典扩展

- 新增操作类型：在 **字典表** `dict_items` 中增加 `dict_type=usage_type` 的项（或通过后台字典管理维护），前端下拉即可出现新选项。
- 新增类型对应的表单模板：在 **后端** `backend/form_templates.py` 中：
  - 在 `DEFAULT_USAGE_TYPE_TEMPLATE_MAP` 中增加 `"<code>": "template_key"`；
  - 在 `TEMPLATE_FIELDS` 中增加该 `template_key` 的字段列表；
  - 在 `TEMPLATE_LABELS` 中增加显示名。
- 未配置的类型会回退到 `normal` 模板，保证兼容。

## 科室专属模板配置（预留）

- 接口 `GET /api/usage/form-schema` 已支持查询参数 `dept`；H5 在设备信息回填后可传入设备所属科室，用于后续科室级模板覆盖。
- 实现扩展方式：在 `form_templates.get_dept_template_override(db, dept, usage_type)` 中：
  - 从表（如 `dept_form_templates`：科室、操作类型、模板键）或配置中查询；
  - 若存在覆盖则返回该 `template_key`，否则返回 `None` 使用默认按操作类型的模板。
- 当前为占位实现，返回 `None`，即全部使用默认模板。

## 模块与可适配性

- **后端**：`form_templates.py` 独立模块，与路由解耦；`routes_usage.py` 仅调用 `get_form_schema()`。
- **前端**：按 `template_key` 切换 `.form-block[data-template="..."]`，提交时按当前模板组装 payload，便于后续增加新模板块或改为由 schema 动态渲染。
