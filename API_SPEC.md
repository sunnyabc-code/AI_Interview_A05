# AI模拟面试平台 - API规范文档（最新版）

> 更新时间：2026-03-14  
> 说明：本版本已同步当前数据库结构与近期模型调整（多目标岗位、删除面试消息表、删除维度评分表、新增轮次分析表）。

---

## 一、API设计原则

### 1.1 RESTful规范
- 使用 HTTP 动词表示操作（GET/POST/PUT/PATCH/DELETE）
- 资源名使用复数
- 统一版本前缀：`/api/v1/`

### 1.2 统一响应格式

#### 成功响应
```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

#### 错误响应
```json
{
  "code": 400,
  "message": "错误信息",
  "errors": {}
}
```

#### 列表响应（分页）
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [],
    "pagination": {
      "total": 100,
      "page": 1,
      "page_size": 20,
      "total_pages": 5
    }
  }
}
```

### 1.3 HTTP状态码规范
- `200`：成功
- `201`：创建成功
- `204`：删除成功
- `400`：请求参数错误
- `401`：未认证
- `403`：无权限
- `404`：资源不存在
- `422`：业务校验失败
- `500`：服务端错误

---

## 二、与当前模型一致的资源说明

### 2.1 用户（`users`）
- 已支持用户多目标岗位：`target_positions`（ManyToMany）

### 2.2 岗位（`job_positions`）
- 已移除岗位评估维度表，不再提供“岗位维度”相关资源

### 2.3 题库（`questions`）
- 问题主表：`questions`
- 题目分类：`question_categories`
- 知识点：`knowledge_points`

### 2.4 面试（`interviews` / `interview_rounds`）
- `interviews` 新增：`total_rounds`
- `interview_rounds` 已支持：
  - `question`（问题ID关联）
  - `question_content`（问题快照）
  - `user_answer`（用户回答）

### 2.5 轮次分析（`interview_round_analyses`）
- 每个轮次一条分析记录（`OneToOne`）
- 字段参考总评估表：综合分、各维度分、亮点/不足/建议

### 2.6 评估与语音
- 总评估表：`evaluations`
- 语音分析表：`voice_analyses`（已关联 `interview_rounds`）
- 维度评分表已删除（`dimension_scores`）

### 2.7 已删除资源（禁止继续设计/实现）
- `interview_messages`
- `dimension_scores`
- `position_dimensions`

---

## 三、API端点规划（最新）

> 说明：当前仓库中多数 API 视图仍是占位，以下为“最新规划”，与现有表结构一致。

### 3.1 用户模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/v1/users/register/` | 用户注册 | 公开 |
| POST | `/api/v1/users/login/` | 用户登录 | 公开 |
| GET | `/api/v1/users/profile/` | 获取个人信息 | 认证 |
| PUT | `/api/v1/users/profile/` | 更新个人信息（含 `target_positions`） | 认证 |
| GET | `/api/v1/users/progress/` | 获取用户进度 | 认证 |

### 3.2 岗位模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/positions/` | 岗位列表 | 公开 |
| GET | `/api/v1/positions/{id}/` | 岗位详情 | 公开 |

### 3.3 题库模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/questions/categories/` | 题目分类列表 | 公开 |
| GET | `/api/v1/questions/knowledge-points/` | 知识点列表 | 公开 |
| GET | `/api/v1/questions/` | 题目列表 | 公开 |
| GET | `/api/v1/questions/{id}/` | 题目详情 | 公开 |

### 3.4 面试模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/v1/interviews/` | 创建面试 | 认证 |
| GET | `/api/v1/interviews/` | 面试列表 | 认证 |
| GET | `/api/v1/interviews/{id}/` | 面试详情 | 认证 |
| PATCH | `/api/v1/interviews/{id}/` | 更新面试状态/总轮数等 | 认证 |
| POST | `/api/v1/interviews/{id}/start/` | 开始面试 | 认证 |
| POST | `/api/v1/interviews/{id}/end/` | 结束面试 | 认证 |

### 3.5 面试轮次模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/v1/interviews/{interview_id}/rounds/` | 创建轮次（含问题ID/快照） | 认证 |
| GET | `/api/v1/interviews/{interview_id}/rounds/` | 轮次列表 | 认证 |
| GET | `/api/v1/rounds/{id}/` | 轮次详情 | 认证 |
| PATCH | `/api/v1/rounds/{id}/` | 更新用户回答、结束时间等 | 认证 |

### 3.6 轮次分析模块（新增）

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| POST | `/api/v1/rounds/{round_id}/analysis/` | 创建轮次分析结果 | 认证 |
| GET | `/api/v1/rounds/{round_id}/analysis/` | 获取轮次分析结果 | 认证 |
| PUT | `/api/v1/rounds/{round_id}/analysis/` | 覆盖更新轮次分析结果 | 认证 |

### 3.7 评估模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/evaluations/{interview_id}/` | 获取总评估结果 | 认证 |
| POST | `/api/v1/evaluations/{interview_id}/generate/` | 生成总评估 | 认证 |

### 3.8 报告模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/reports/{interview_id}/` | 获取报告 | 认证 |
| GET | `/api/v1/reports/{interview_id}/download/` | 下载PDF报告 | 认证 |

### 3.9 推荐模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/recommendations/` | 推荐列表 | 认证 |
| PUT | `/api/v1/recommendations/{id}/complete/` | 标记完成 | 认证 |

### 3.10 学习模块

| 方法 | 路径 | 描述 | 权限 |
|---|---|---|---|
| GET | `/api/v1/learning/resources/` | 学习资源列表 | 认证 |
| GET | `/api/v1/learning/paths/` | 学习路径列表 | 认证 |
| PUT | `/api/v1/learning/paths/{id}/progress/` | 更新学习进度 | 认证 |

---

## 四、关键请求体字段（最新）

### 4.1 创建/更新面试
```json
{
  "position": 1,
  "mode": "text",
  "total_rounds": 5,
  "notes": "本次重点考察项目经历"
}
```

### 4.2 创建轮次
```json
{
  "round_number": 1,
  "category": 1,
  "question": 12,
  "question_content": "请描述你在项目中如何优化查询性能？",
  "user_answer": "我主要通过索引优化和SQL重写..."
}
```

### 4.3 创建轮次分析
```json
{
  "overall_score": 82.5,
  "overall_comment": "回答结构清晰，但细节深度可提升",
  "technical_score": 80,
  "communication_score": 85,
  "logic_score": 83,
  "adaptability_score": 82,
  "highlights": ["思路清晰", "有性能优化经验"],
  "weaknesses": ["缺少压测数据支撑"],
  "suggestions": ["补充量化指标", "增加方案对比"]
}
```

---

## 五、实现约束（与现代码保持一致）

1. 使用统一响应封装：`core.response.APIResponse`
2. 列表分页统一使用：`core.pagination.StandardPagination`
3. 异常统一使用：`core.exceptions.custom_exception_handler`
4. 所有新 API 路由统一挂载到 `/api/v1/`
5. 不得再新增或依赖以下已删除资源：
   - `interview_messages`
   - `dimension_scores`
   - `position_dimensions`

---

## 六、认证与权限

### 6.1 推荐认证方式
- JWT（业务 API）
- Session（后台管理）

### 6.2 默认权限建议
- 默认 `IsAuthenticated`
- 公共资源（岗位、题库）可 `AllowAny`

---

## 七、Swagger 文档入口

- Swagger UI：`/swagger/`
- ReDoc：`/redoc/`

---

## 八、版本说明

- 本文档已与当前模型结构同步。
- 若后续再修改模型，请先更新 `DATABASE_SCHEMA.md`，再同步本文件的端点与字段说明。
