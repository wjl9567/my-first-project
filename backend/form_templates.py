# -*- coding: utf-8 -*-
"""
设备登记差异化表单模板模块。

- 按操作类型（usage_type）映射到模板键，返回对应表单项配置，供 H5 联动加载。
- 预留科室专属模板：get_form_schema(usage_type, dept) 支持 dept 参数，后续可从
  dept_form_template 表或配置读取科室覆盖，实现科室专属模板配置。
- 字典扩展：新增 usage_type 时在 DEFAULT_USAGE_TYPE_TEMPLATE_MAP 中增加映射，
  或通过扩展配置/DB 维护，无需改业务逻辑。
"""
from typing import Any, Dict, List, Optional

# 操作类型编码 -> 模板键（与字典 usage_type 1=常规使用 2=借用 3=维修 4=校准 5=其他 一致）
DEFAULT_USAGE_TYPE_TEMPLATE_MAP: Dict[str, str] = {
    "1": "normal",   # 常规使用
    "2": "borrow",   # 借用
    "3": "repair",   # 维修/故障
    "4": "calibration",  # 校准/质控
    "5": "other",
}

# 各模板表单项配置：id 与 API/UsageRecord 字段对应，便于回填与提交
# type: date | text | textarea | time | radio | select | datetime_local
# widget: 可选，前端特殊渲染方式（如 hour_minute 表示时/分下拉组合）
# group: 可选，相邻同 group 的 hour_minute 字段在前端合并为一行展示
# default / default_hour / default_minute: 默认值
# rows: textarea 行数（默认 2）
TEMPLATE_FIELDS: Dict[str, List[Dict[str, Any]]] = {
    "normal": [
        {"id": "registration_date", "label": "登记日期", "type": "date", "required": True},
        {"id": "bed_number", "label": "床号", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 32},
        {"id": "id_number", "label": "ID 号", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 64},
        {"id": "patient_name", "label": "姓名", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 64},
        {"id": "start_time", "label": "开机时间", "type": "time", "widget": "hour_minute",
         "required": True, "default_hour": "08", "default_minute": "00", "group": "power_time"},
        {"id": "end_time", "label": "关机时间", "type": "time", "widget": "hour_minute",
         "required": True, "default_hour": "18", "default_minute": "00", "group": "power_time"},
        {"id": "equipment_condition", "label": "设备状况", "type": "radio", "required": True,
         "options": [{"value": "normal", "label": "正常"}, {"value": "abnormal", "label": "异常"}],
         "default": "normal"},
        {"id": "daily_maintenance", "label": "日常保养", "type": "radio", "required": True,
         "options": [{"value": "clean", "label": "清洁"}, {"value": "disinfect", "label": "消毒"}],
         "default": "clean"},
        {"id": "terminal_disinfection", "label": "终末消毒", "type": "textarea", "required": False,
         "placeholder": "选填，可填写终末消毒备注", "maxlength": 500},
    ],
    "borrow": [
        {"id": "registration_date", "label": "借用日期", "type": "date", "required": True},
        {"id": "end_time", "label": "预计归还日期", "type": "date", "required": True},
        {"id": "patient_name", "label": "借用人", "type": "text", "required": True,
         "placeholder": "请输入借用人", "maxlength": 64},
        {"id": "dept_at_use", "label": "借用科室", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 128},
        {"id": "note", "label": "备注", "type": "textarea", "required": False,
         "placeholder": "选填", "maxlength": 500},
    ],
    "repair": [
        {"id": "registration_date", "label": "报修日期", "type": "date", "required": True},
        {"id": "patient_name", "label": "报修人", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 64},
        {"id": "note", "label": "故障描述", "type": "textarea", "required": True,
         "placeholder": "请描述故障现象", "maxlength": 500, "rows": 3},
    ],
    "calibration": [
        {"id": "registration_date", "label": "登记日期", "type": "date", "required": True},
        {"id": "start_time", "label": "校准/质控时间", "type": "time", "required": True},
        {"id": "patient_name", "label": "操作人", "type": "text", "required": False,
         "placeholder": "选填", "maxlength": 64},
        {"id": "note", "label": "备注", "type": "textarea", "required": False,
         "placeholder": "选填", "maxlength": 500},
    ],
    "other": [
        {"id": "registration_date", "label": "登记日期", "type": "date", "required": True},
        {"id": "note", "label": "备注", "type": "textarea", "required": False,
         "placeholder": "选填", "maxlength": 500},
    ],
}

# 模板键 -> 显示名称（用于前端标题或提示）
TEMPLATE_LABELS: Dict[str, str] = {
    "normal": "常规使用",
    "borrow": "设备借用",
    "repair": "设备维修",
    "calibration": "校准/质控",
    "other": "其他",
}


def get_dept_template_override(
    db: Optional[Any],
    dept: Optional[str],
    usage_type: str,
) -> Optional[str]:
    """
    预留：科室专属模板覆盖。
    若存在 dept_form_template 表或配置，可在此查询 (dept, usage_type) -> template_key。
    当前返回 None，表示使用默认按 usage_type 的模板。
    """
    # TODO: 从表 dept_form_templates(dept, usage_type, template_key) 或配置读取
    return None


def get_form_schema(
    usage_type: str,
    dept: Optional[str] = None,
    db: Optional[Any] = None,
    usage_type_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    根据操作类型（及可选科室）返回表单模板配置，供 H5 联动加载差异化表单。

    :param usage_type: 操作类型编码（字符串，如 "1"、"2"）
    :param dept: 科室（预留，用于科室专属模板）
    :param db: 数据库会话（预留，用于科室覆盖查询）
    :param usage_type_label: 操作类型显示名（可选，由调用方从字典传入）
    :return: { "template_key", "fields", "usage_type", "usage_type_label" }
    """
    usage_type_str = str(usage_type).strip() if usage_type is not None else "1"
    template_key = get_dept_template_override(db, dept, usage_type_str)
    if template_key is None:
        template_key = DEFAULT_USAGE_TYPE_TEMPLATE_MAP.get(usage_type_str, "normal")
    fields = list(TEMPLATE_FIELDS.get(template_key, TEMPLATE_FIELDS["normal"]))
    return {
        "template_key": template_key,
        "template_label": TEMPLATE_LABELS.get(template_key, "常规使用"),
        "fields": fields,
        "usage_type": usage_type_str,
        "usage_type_label": usage_type_label or TEMPLATE_LABELS.get(template_key, "常规使用"),
    }
