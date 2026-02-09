# 数据库选型评估：MySQL vs PostgreSQL

> 针对「医院设备扫码登记系统」的现状与需求评估。

---

## 一、当前状态

| 项目 | 现状 |
|------|------|
| **默认配置** | `config.py`、`.env.example`、`database.py` 默认均为 **PostgreSQL**（`postgresql+psycopg2://...`） |
| **依赖** | `pyproject.toml` 仅声明 **psycopg2-binary**，项目描述为「FastAPI + PostgreSQL」 |
| **业务 SQL** | 设备/使用记录查询使用 SQLAlchemy ORM + `ilike` 模糊查询，无原生 SQL 依赖 |
| **迁移脚本** | 部分脚本仅支持 PostgreSQL（见下表） |

### 迁移脚本与数据库兼容性

| 脚本 | PostgreSQL | MySQL | 说明 |
|------|------------|--------|------|
| `run_migrate_usage_soft_delete.py` | ✅ | ❌ | 使用 `information_schema` 与 `BOOLEAN DEFAULT false`，文内写明「仅支持 PostgreSQL」 |
| `run_migrate_device_soft_delete.py` | ✅ | ⚠️ | 先试 `DEFAULT 0` 再试 `DEFAULT FALSE`，未针对 MySQL 单独写 |
| `run_migrate_device_code.py` | ✅ | ❌ | 含 PG/SQLite 分支，无 MySQL 分支 |
| `run_migrate_dict_code_to_int.py` | ✅ | ✅ | 标准 UPDATE/SELECT/DROP，SQLAlchemy create_all，与具体数据库无关 |

---

## 二、技术对比（与本系统相关的部分）

| 维度 | PostgreSQL | MySQL |
|------|------------|--------|
| **模糊搜索** | `ilike` 原生大小写不敏感 | SQLAlchemy 将 `ilike` 转为 `LIKE`，配合排序规则可达到类似效果 |
| **布尔类型** | 原生 BOOLEAN（TRUE/FALSE） | 常用 TINYINT(1)，SQLAlchemy 可统一抽象 |
| **information_schema** | 支持 | 支持（表/列名略有差异） |
| **事务与 ACID** | 支持完善 | InnoDB 支持完善 |
| **部署与运维** | 常见于企业/云环境 | 更常见，文档与运维经验更多 |
| **适用规模** | 本系统设备/记录量级下两者均足够 | 同左 |

本系统没有用到：窗口函数、JSON 查询、全文检索、数组类型、PG 专有扩展等，因此**从功能上两种数据库都能满足**。

---

## 三、建议结论

### 推荐：**继续使用 PostgreSQL**

理由简述：

1. **与当前实现一致**  
   默认配置、依赖和迁移脚本都是按 PostgreSQL 写的，部分迁移**仅支持 PostgreSQL**（如 usage 软删除）。继续用 PostgreSQL 无需改代码和迁移，运维与文档也统一。

2. **符合项目定位**  
   院内设备登记属于**小到中型业务、数据一致性和可追溯性要求高**的场景。PostgreSQL 在事务、约束、审计友好度上表现稳定，和「医院/机构内系统」的常见选型一致。

3. **迁移成本**  
   若改为 MySQL，需要：  
   - 增加 MySQL 驱动（如 `pymysql` 或 `mysqlclient`）；  
   - 修改或重写「仅支持 PostgreSQL」的迁移脚本；  
   - 在 MySQL 上完整跑一遍迁移与回归测试。  
   在无明确 MySQL 需求（如公司标准、已有 MySQL 运维体系）时，收益有限。

4. **可选：后续双库支持**  
   若将来确需支持 MySQL，可再：  
   - 用 SQLAlchemy 的 `dialect` 或环境变量区分库类型；  
   - 为 MySQL 补写等价迁移（含 `information_schema`、布尔默认值等）；  
   - 在 CI 中增加 MySQL 测试。  

当前阶段**不推荐**为「可能用 MySQL」提前做双库兼容，以免增加维护成本。

---

## 四、若必须使用 MySQL 时需做的改动

在「推荐继续用 PostgreSQL」的前提下，若因政策或环境**必须**迁到 MySQL，建议至少做：

1. **依赖与配置**  
   - 在 `pyproject.toml` 中增加 MySQL 驱动（如 `pymysql`）。  
   - 默认或示例 `DATABASE_URL` 改为 `mysql+pymysql://user:password@localhost:3306/device_scan`（或你方约定格式）。  

2. **迁移脚本**  
   - **run_migrate_usage_soft_delete.py**：  
     - 检测到 MySQL 时，用 MySQL 的 `information_schema`（如 `TABLE_SCHEMA = DATABASE()`）判断列是否存在；  
     - `ALTER TABLE ... ADD COLUMN is_deleted ...` 使用 MySQL 支持的默认值写法（如 `TINYINT(1) DEFAULT 0` 或等效布尔表示）。  
   - **run_migrate_device_soft_delete.py**：  
     - 显式增加 MySQL 分支（列类型与默认值按 MySQL 规范写）。  
   - **run_migrate_device_code.py**：  
     - 如需支持 MySQL，增加 MySQL 分支（列存在性检查、ALTER 语法等）。  

3. **验证**  
   - 在 MySQL 上从空库执行全部迁移脚本，再跑核心业务流程（登记、查询、导出、撤销等），确认无报错且结果与在 PostgreSQL 上一致。  

4. **文档**  
   - 在 README 或部署文档中说明：当前默认/推荐为 PostgreSQL；若使用 MySQL，需使用上述改造后的迁移与配置。

---

## 五、总结表

| 选项 | 建议 | 说明 |
|------|------|------|
| **新项目 / 未定库** | PostgreSQL | 与现有代码、迁移、文档一致，无需改库。 |
| **已有 PostgreSQL** | 继续用 PostgreSQL | 无迁移成本，运维一致。 |
| **公司强制 MySQL** | 按第四节改造后使用 MySQL | 需改迁移脚本与依赖，并做完整测试。 |

**结论：在未出现强制使用 MySQL 或已有 MySQL 资产的前提下，建议本系统继续使用 PostgreSQL。**
