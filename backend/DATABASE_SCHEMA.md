# AI模拟面试平台 - 数据库表结构文档

**第一次数据库表创建时间**：2026/3/14 12:00

## 1. 用户相关表

### 1.1 users 表 - 用户表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 用户ID |
| `username` | Username | CharField(150) | 唯一 | 用户名 |
| `password` | Password | CharField(128) | - | 密码 |
| `email` | Email | CharField(254) | - | 邮箱 |
| `phone` | Phone | CharField(20) | 可空 | 手机号 |
| `avatar` | Avatar URL | CharField(500) | 可空 | 头像URL |
| `target_positions` | Target Positions | ManyToManyField | 可空 | 目标岗位（多选） |
| `interview_count` | Interview Count | IntegerField | 默认0 | 面试次数 |
| `is_active` | Is Active | BooleanField | 默认True | 是否激活 |
| `is_staff` | Is Staff | BooleanField | 默认False | 是否员工 |
| `is_superuser` | Is Superuser | BooleanField | 默认False | 是否超级用户 |
| `last_login` | Last Login | DateTimeField | 可空 | 最后登录时间 |
| `date_joined` | Date Joined | DateTimeField | - | 加入时间 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 1.2 user_progress 表 - 用户进度表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 进度ID |
| `user` | User | OneToOneField | 外键 | 关联用户 |
| `total_interviews` | Total Interviews | IntegerField | 默认0 | 总面试次数 |
| `total_questions_answered` | Total Questions Answered | IntegerField | 默认0 | 总答题数 |
| `avg_overall_score` | Average Overall Score | FloatField | 默认0 | 平均综合得分 |
| `avg_technical_score` | Average Technical Score | FloatField | 默认0 | 平均技术得分 |
| `avg_communication_score` | Average Communication Score | FloatField | 默认0 | 平均沟通得分 |
| `avg_logic_score` | Average Logic Score | FloatField | 默认0 | 平均逻辑得分 |
| `completed_recommendations` | Completed Recommendations | IntegerField | 默认0 | 已完成推荐数 |
| `skill_gaps` | Skill Gaps | JSONField | 默认[] | 技能缺口 |
| `improvement_areas` | Improvement Areas | JSONField | 默认[] | 改进领域 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 2. 岗位相关表

### 2.1 job_positions 表 - 岗位表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 岗位ID |
| `code` | Code | CharField(50) | 唯一 | 岗位代码 |
| `name` | Name | CharField(100) | - | 岗位名称 |
| `description` | Description | TextField | 可空 | 岗位描述 |
| `tech_stack` | Tech Stack | JSONField | 默认[] | 技术栈 |
| `required_skills` | Required Skills | JSONField | 默认[] | 必备技能 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |


## 3. 题库相关表

### 3.1 question_categories 表 - 题目分类表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 分类ID |
| `code` | Code | CharField(50) | 唯一 | 分类代码 |
| `name` | Name | CharField(100) | - | 分类名称 |
| `description` | Description | TextField | 可空 | 分类描述 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |

### 3.2 knowledge_points 表 - 知识点表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 知识点ID |
| `name` | Name | CharField(200) | - | 知识点名称 |
| `description` | Description | TextField | 可空 | 知识点描述 |
| `position` | Position | ForeignKey | 外键 | 所属岗位 |
| `difficulty` | Difficulty | IntegerField | 默认1 | 难度等级 |
| `vector_id` | Vector ID | CharField(200) | 可空 | 向量ID |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 3.3 questions 表 - 面试题表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 题目ID |
| `position` | Position | ForeignKey | 外键 | 岗位 |
| `category` | Category | ForeignKey | 外键 | 分类 |
| `title` | Title | CharField(300) | - | 题目标题 |
| `content` | Content | TextField | - | 题目内容 |
| `reference_answer` | Reference Answer | TextField | 可空 | 参考答案 |
| `difficulty` | Difficulty | IntegerField | 默认1 | 难度 |
| `tags` | Tags | JSONField | 默认[] | 标签 |
| `follow_up_questions` | Follow Up Questions | JSONField | 默认[] | 追问模板 |
| `usage_count` | Usage Count | IntegerField | 默认0 | 使用次数 |
| `is_active` | Is Active | BooleanField | 默认True | 是否启用 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 4. 面试相关表

### 4.1 interviews 表 - 面试记录表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 面试ID |
| `user` | User | ForeignKey | 外键 | 用户 |
| `position` | Position | ForeignKey | 外键 | 岗位 |
| `status` | Status | CharField(20) | 默认'pending' | 状态 |
| `mode` | Mode | CharField(20) | 默认'text' | 交互模式 |
| `start_time` | Start Time | DateTimeField | 可空 | 开始时间 |
| `end_time` | End Time | DateTimeField | 可空 | 结束时间 |
| `duration_seconds` | Duration Seconds | IntegerField | 默认0 | 时长(秒) |
| `total_rounds` | Total Rounds | IntegerField | 默认0 | 总轮次 |
| `difficulty_config` | Difficulty Config | ForeignKey | 可空 | 关联难度配置 |
| `enable_technical_questions` | Enable Technical Questions | BooleanField | 默认True | 是否选择技术知识题 |
| `enable_project_questions` | Enable Project Questions | BooleanField | 默认True | 是否选择项目经历题 |
| `enable_scenario_questions` | Enable Scenario Questions | BooleanField | 默认True | 是否选择场景题 |
| `notes` | Notes | TextField | 可空 | 备注 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 4.2 interview_rounds 表 - 面试轮次表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 轮次ID |
| `interview` | Interview | ForeignKey | 外键 | 关联面试 |
| `round_number` | Round Number | IntegerField | - | 轮次 |
| `category` | Category | ForeignKey | 可空 | 题目分类 |
| `question` | Question | ForeignKey | 可空 | 关联题目（问题ID） |
| `question_content` | Question Content Snapshot | TextField | 可空 | 问题内容快照 |
| `user_answer` | User Answer | TextField | 可空 | 用户回答 |
| `start_time` | Start Time | DateTimeField | - | 开始时间 |
| `end_time` | End Time | DateTimeField | 可空 | 结束时间 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |

### 4.3 interview_round_analyses 表 - 轮次分析结果表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 轮次分析ID |
| `round` | Round | OneToOneField | 外键 | 关联面试轮次 |
| `overall_score` | Overall Score | FloatField | - | 综合得分 |
| `overall_comment` | Overall Comment | TextField | - | 综合评价 |
| `technical_score` | Technical Score | FloatField | - | 技术得分 |
| `communication_score` | Communication Score | FloatField | - | 沟通得分 |
| `logic_score` | Logic Score | FloatField | - | 逻辑得分 |
| `adaptability_score` | Adaptability Score | FloatField | - | 应变得分 |
| `highlights` | Highlights | JSONField | 默认[] | 亮点 |
| `weaknesses` | Weaknesses | JSONField | 默认[] | 不足 |
| `suggestions` | Suggestions | JSONField | 默认[] | 建议 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 5. 评估相关表

### 5.1 evaluations 表 - 评估记录表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 评估ID |
| `interview` | Interview | OneToOneField | 外键 | 关联面试 |
| `overall_score` | Overall Score | FloatField | - | 综合得分 |
| `overall_comment` | Overall Comment | TextField | - | 综合评价 |
| `technical_score` | Technical Score | FloatField | - | 技术得分 |
| `communication_score` | Communication Score | FloatField | - | 沟通得分 |
| `logic_score` | Logic Score | FloatField | - | 逻辑得分 |
| `adaptability_score` | Adaptability Score | FloatField | - | 应变得分 |
| `highlights` | Highlights | JSONField | 默认[] | 亮点 |
| `weaknesses` | Weaknesses | JSONField | 默认[] | 不足 |
| `suggestions` | Suggestions | JSONField | 默认[] | 建议 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 5.2 voice_analyses 表 - 语音分析表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 分析ID |
| `round` | Round | ForeignKey | 可空 | 关联面试轮次 |
| `duration_seconds` | Duration Seconds | FloatField | - | 时长(秒) |
| `speech_rate` | Speech Rate | FloatField | - | 语速(字/分钟) |
| `clarity_score` | Clarity Score | FloatField | - | 清晰度得分 |
| `confidence_score` | Confidence Score | FloatField | - | 自信度得分 |
| `emotion` | Emotion | CharField(50) | 可空 | 情感 |
| `transcript` | Transcript | TextField | 可空 | 转录文本 |
| `analysis_details` | Analysis Details | JSONField | 默认{} | 分析详情 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |

### 5.2.2 difficulty_config 表 - 难度配置表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 配置ID |
| `difficulty_code` | Difficulty Code | CharField(16) | 唯一 | 难度编码（easy / medium / hard） |
| `difficulty_name` | Difficulty Name | CharField(32) | - | 难度名称 |
| `answer_time_seconds` | Answer Time Seconds | IntegerField | - | 单轮默认答题时长 |
| `technical_chain_count` | Technical Chain Count | IntegerField | - | 技术知识链数量 |
| `project_chain_count` | Project Chain Count | IntegerField | - | 项目深挖链数量 |
| `scenario_chain_count` | Scenario Chain Count | IntegerField | - | 场景题链数量 |
| `technical_max_followup_depth` | Technical Max Followup Depth | IntegerField | - | 技术链最大追问深度 |
| `project_max_followup_depth` | Project Max Followup Depth | IntegerField | - | 项目链最大追问深度 |
| `scenario_max_followup_depth` | Scenario Max Followup Depth | IntegerField | - | 场景链最大追问深度 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 6. 报告相关表

### 6.1 reports 表 - 评估报告表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 报告ID |
| `interview` | Interview | OneToOneField | 外键 | 关联面试 |
| `evaluation` | Evaluation | OneToOneField | 外键 | 关联评估 |
| `title` | Title | CharField(200) | - | 报告标题 |
| `content` | Content | TextField | - | 报告内容 |
| `pdf_file` | PDF File URL | CharField(500) | 可空 | PDF文件URL |
| `summary` | Summary | TextField | - | 摘要 |
| `key_findings` | Key Findings | JSONField | 默认[] | 关键发现 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 7. 学习相关表

### 7.1 learning_resources 表 - 学习资源表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 资源ID |
| `title` | Title | CharField(300) | - | 资源标题 |
| `resource_type` | Resource Type | CharField(20) | - | 资源类型 |
| `url` | URL | URLField | 可空 | 链接 |
| `content` | Content | TextField | 可空 | 内容 |
| `position` | Position | ForeignKey | 外键 | 岗位 |
| `difficulty` | Difficulty | IntegerField | 默认1 | 难度 |
| `estimated_time` | Estimated Time | IntegerField | 可空 | 预计学习时长(分钟) |
| `tags` | Tags | JSONField | 默认[] | 标签 |
| `is_active` | Is Active | BooleanField | 默认True | 是否启用 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 7.2 learning_paths 表 - 学习路径表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 路径ID |
| `user` | User | ForeignKey | 外键 | 用户 |
| `position` | Position | ForeignKey | 外键 | 岗位 |
| `title` | Title | CharField(200) | - | 路径标题 |
| `description` | Description | TextField | - | 描述 |
| `progress` | Progress | FloatField | 默认0 | 进度 |
| `is_completed` | Is Completed | BooleanField | 默认False | 是否完成 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

### 7.3 learning_path_items 表 - 学习路径项表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 路径项ID |
| `learning_path` | Learning Path | ForeignKey | 外键 | 关联学习路径 |
| `resource` | Resource | ForeignKey | 外键 | 关联资源 |
| `order` | Order | IntegerField | - | 顺序 |
| `is_completed` | Is Completed | BooleanField | 默认False | 是否完成 |
| `completed_at` | Completed At | DateTimeField | 可空 | 完成时间 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |

## 8. 推荐相关表

### 8.1 recommendations 表 - 推荐表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 推荐ID |
| `user` | User | ForeignKey | 外键 | 用户 |
| `interview` | Interview | ForeignKey | 可空 | 关联面试 |
| `recommendation_type` | Recommendation Type | CharField(20) | - | 推荐类型 |
| `title` | Title | CharField(300) | - | 标题 |
| `description` | Description | TextField | - | 描述 |
| `priority` | Priority | IntegerField | 默认1 | 优先级 |
| `is_completed` | Is Completed | BooleanField | 默认False | 是否完成 |
| `related_dimension` | Related Dimension | CharField(100) | 可空 | 关联维度（文本） |
| `related_knowledge_point` | Related Knowledge Point | ForeignKey | 可空 | 关联知识点 |
| `created_at` | Created At | DateTimeField | - | 创建时间 |
| `updated_at` | Updated At | DateTimeField | - | 更新时间 |

## 9. 多对多关联表

### 9.1 questions_knowledge_points 表 - 题目与知识点关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `question_id` | Question ID | BigIntegerField | 外键 | 题目ID |
| `knowledgepoint_id` | Knowledge Point ID | BigIntegerField | 外键 | 知识点ID |

### 9.2 learning_resources_knowledge_points 表 - 学习资源与知识点关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `learningresource_id` | Learning Resource ID | BigIntegerField | 外键 | 学习资源ID |
| `knowledgepoint_id` | Knowledge Point ID | BigIntegerField | 外键 | 知识点ID |

### 9.3 users_target_positions 表 - 用户与目标岗位关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `user_id` | User ID | BigIntegerField | 外键 | 用户ID |
| `jobposition_id` | Job Position ID | BigIntegerField | 外键 | 岗位ID |

## 10. 系统表

### 10.1 django_content_type 表 - 内容类型表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | AutoField | 主键 | 内容类型ID |
| `app_label` | App Label | CharField(100) | - | 应用标签 |
| `model` | Model | CharField(100) | - | 模型名称 |

### 10.2 auth_permission 表 - 权限表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | AutoField | 主键 | 权限ID |
| `name` | Name | CharField(255) | - | 权限名称 |
| `content_type_id` | Content Type ID | ForeignKey | 外键 | 内容类型ID |
| `codename` | Codename | CharField(100) | - | 权限代码 |

### 10.3 auth_group 表 - 用户组表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | AutoField | 主键 | 组ID |
| `name` | Name | CharField(150) | 唯一 | 组名称 |

### 10.4 auth_group_permissions 表 - 用户组权限关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `group_id` | Group ID | ForeignKey | 外键 | 组ID |
| `permission_id` | Permission ID | ForeignKey | 外键 | 权限ID |

### 10.5 users_groups 表 - 用户与组关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `user_id` | User ID | ForeignKey | 外键 | 用户ID |
| `group_id` | Group ID | ForeignKey | 外键 | 组ID |

### 10.6 users_user_permissions 表 - 用户与权限关联表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | BigAutoField | 主键 | 关联ID |
| `user_id` | User ID | ForeignKey | 外键 | 用户ID |
| `permission_id` | Permission ID | ForeignKey | 外键 | 权限ID |

### 10.7 django_admin_log 表 - 管理员操作日志表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `id` | ID | AutoField | 主键 | 日志ID |
| `action_time` | Action Time | DateTimeField | - | 操作时间 |
| `user_id` | User ID | ForeignKey | 外键 | 用户ID |
| `content_type_id` | Content Type ID | ForeignKey | 可空 | 内容类型ID |
| `object_id` | Object ID | TextField | 可空 | 对象ID |
| `object_repr` | Object Repr | CharField(200) | - | 对象表示 |
| `action_flag` | Action Flag | SmallIntegerField | - | 操作标志 |
| `change_message` | Change Message | TextField | - | 变更消息 |

### 10.8 django_session 表 - 会话表

| 字段名 | 英文名称 | 数据类型 | 约束 | 描述 |
|--------|---------|---------|------|------|
| `session_key` | Session Key | CharField(40) | 主键 | 会话键 |
| `session_data` | Session Data | TextField | - | 会话数据 |
| `expire_date` | Expire Date | DateTimeField | - | 过期时间 |

## 11. 数据库版本信息

- **数据库类型**: SQLite
- **数据库文件**: `db.sqlite3`
- **第一次创建时间**: 2026/3/14 12:00
- **模型数量**: 16个自定义模型
- **总表数量**: 28个表（含 `django_migrations`）

---

## 12. 表关联关系与级联影响

### 12.1 关联关系类型说明

| 关联类型 | 英文名称 | 说明 | 级联行为 |
|---------|---------|------|---------|
| `OneToOneField` | 一对一关联 | 删除主表时，关联表记录会被删除（CASCADE） |
| `ForeignKey` | 外键关联 | 默认删除主表时，关联表记录会被删除（CASCADE） |
| `ManyToManyField` | 多对多关联 | 通过中间表管理，删除主表时自动清理中间表记录 |

### 12.2 核心表关联关系图

```
users (用户)
├── OneToOne → user_progress (用户进度)
├── ManyToMany → job_positions (目标岗位)
├── OneToMany → interviews (面试记录)
└── OneToMany → learning_paths (学习路径)

job_positions (岗位)
├── OneToMany → knowledge_points (知识点)
├── OneToMany → questions (面试题)
├── OneToMany → learning_resources (学习资源)
└── OneToMany → interviews (面试记录)

question_categories (题目分类)
└── OneToMany → questions (面试题)

knowledge_points (知识点)
├── ForeignKey → job_positions (所属岗位)
├── ManyToMany → questions (关联题目)
└── ManyToMany → learning_resources (关联资源)

questions (面试题)
├── ForeignKey → job_positions (岗位)
├── ForeignKey → question_categories (分类)
└── ManyToMany → knowledge_points (知识点)

interviews (面试记录)
├── ForeignKey → users (用户)
├── ForeignKey → job_positions (岗位)
├── ForeignKey → difficulty_config (难度配置)
├── OneToOne → evaluations (评估结果)
├── OneToOne → reports (评估报告)
├── OneToMany → interview_rounds (面试轮次)
└── OneToMany → recommendations (推荐记录)

interview_rounds (面试轮次)
├── ForeignKey → interviews (面试记录)
├── ForeignKey → question_categories (题目分类)
├── ForeignKey → questions (关联题目)
├── OneToOne → interview_round_analyses (轮次分析结果)
└── OneToMany → voice_analyses (语音分析)

interview_round_analyses (轮次分析结果)
└── OneToOne → interview_rounds (面试轮次)

evaluations (评估记录)
├── OneToOne → interviews (面试记录)
└── OneToOne → reports (评估报告)

voice_analyses (语音分析)
└── ForeignKey → interview_rounds (面试轮次)

reports (评估报告)
├── OneToOne → interviews (面试记录)
└── OneToOne → evaluations (评估记录)

learning_resources (学习资源)
├── ForeignKey → job_positions (岗位)
└── ManyToMany → knowledge_points (知识点)

learning_paths (学习路径)
├── ForeignKey → users (用户)
├── ForeignKey → job_positions (岗位)
└── ManyToMany → learning_resources (通过learning_path_items)

learning_path_items (学习路径项)
├── ForeignKey → learning_paths (学习路径)
└── ForeignKey → learning_resources (学习资源)

recommendations (推荐记录)
├── ForeignKey → users (用户)
├── ForeignKey → interviews (面试记录)
├── CharField → related_dimension (关联维度)
└── ForeignKey → knowledge_points (关联知识点)
```

### 12.3 修改和删除注意事项

#### 12.3.1 高风险表（删除会影响多个表）

| 表名 | 英文名称 | 删除影响 | 风险等级 |
|-----|---------|---------|---------|
| `users` | Users | 删除用户会级联删除：user_progress、所有interviews、所有learning_paths、所有recommendations | ⚠️ **高风险** |
| `job_positions` | Job Positions | 删除岗位会级联删除：knowledge_points、questions、learning_resources、interviews | ⚠️ **高风险** |
| `interviews` | Interviews | 删除面试会级联删除：interview_rounds、interview_round_analyses、voice_analyses、evaluations、reports、recommendations | ⚠️ **高风险** |
| `evaluations` | Evaluations | 删除评估会影响reports | ⚠️ **中风险** |
| `question_categories` | Question Categories | 删除分类会影响interview_rounds和questions | ⚠️ **中风险** |
| `knowledge_points` | Knowledge Points | 删除知识点会清理questions和learning_resources的关联 | ⚠️ **中风险** |

#### 12.3.2 中风险表（删除会影响部分表）

| 表名 | 英文名称 | 删除影响 | 风险等级 |
|-----|---------|---------|---------|
| `questions` | Questions | 删除题目会影响interview_rounds和knowledge_points关联（关联字段会置空） | ⚠️ **中风险** |
| `interview_rounds` | Interview Rounds | 删除轮次会影响voice_analyses和interview_round_analyses | ⚠️ **中风险** |
| `learning_paths` | Learning Paths | 删除路径会清理learning_path_items | ⚠️ **中风险** |
| `learning_resources` | Learning Resources | 删除资源会影响learning_path_items和knowledge_points关联 | ⚠️ **中风险** |

#### 12.3.3 低风险表（删除影响有限）

| 表名 | 英文名称 | 删除影响 | 风险等级 |
|-----|---------|---------|---------|
| `voice_analyses` | Voice Analyses | 无级联影响 | ✅ **低风险** |
| `interview_round_analyses` | Interview Round Analyses | 无级联影响 | ✅ **低风险** |
| `reports` | Reports | 无级联影响 | ✅ **低风险** |
| `learning_path_items` | Learning Path Items | 无级联影响 | ✅ **低风险** |
| `recommendations` | Recommendations | 无级联影响 | ✅ **低风险** |

### 12.4 操作建议

#### 12.4.1 删除操作建议

1. **高风险表删除前检查**：
   ```python
   # 删除用户前检查
   user = User.objects.get(id=user_id)
   if user.interviews.count() > 0:
       raise Exception("用户有面试记录，不能删除")
   if user.learning_paths.count() > 0:
       raise Exception("用户有学习路径，不能删除")
   ```

2. **使用软删除**：
   ```python
   # 添加is_deleted字段，不真正删除数据
   is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
   ```

3. **事务处理**：
   ```python
   from django.db import transaction
   
   @transaction.atomic
   def delete_user(user_id):
       user = User.objects.get(id=user_id)
       # 执行删除操作
       user.delete()
   ```

#### 12.4.2 修改操作建议

1. **修改岗位前检查**：
   ```python
   # 检查是否有面试记录
   position = JobPosition.objects.get(id=position_id)
   if position.interviews.count() > 0:
       raise Exception("岗位已有面试记录，不能修改")
   ```

2. **修改分类前检查**：
   ```python
   # 检查是否有题目使用
   category = QuestionCategory.objects.get(id=category_id)
   if category.questions.count() > 0:
       raise Exception("分类下有题目，不能修改")
   ```

3. **级联更新**：
   ```python
   # 修改岗位时更新关联数据
   @transaction.atomic
   def update_position(position_id, new_data):
       position = JobPosition.objects.get(id=position_id)
       position.name = new_data['name']
       position.save()
       # 更新相关数据
       position.knowledge_points.update(position_name=new_data['name'])
   ```

### 12.5 数据完整性约束

| 约束类型 | 英文名称 | 说明 | 示例 |
|---------|---------|------|------|
| `ForeignKey` | 外键约束 | 确保关联数据存在 |
| `OneToOneField` | 一对一约束 | 确保唯一关联 |
| `ManyToManyField` | 多对多约束 | 通过中间表管理关联 |
| `unique_together` | 联合唯一 | 确保组合字段唯一 |
| `on_delete` | 删除行为 | CASCADE（级联删除）、SET_NULL（设为空）、PROTECT（保护） |

### 12.6 级联删除行为配置

| 删除行为 | 英文名称 | 说明 | 使用场景 |
|---------|---------|------|---------|
| `CASCADE` | 级联删除 | 删除主表时自动删除关联记录 |
| `SET_NULL` | 设为空 | 删除主表时关联字段设为NULL（需要字段可为空） |
| `PROTECT` | 保护删除 | 删除主表时抛出异常，阻止删除 |
| `DO_NOTHING` | 不做操作 | 删除主表时不处理关联记录（可能导致数据不一致） |

**当前项目默认使用**：`CASCADE` 级联删除，删除主表时会自动删除所有关联记录。

---

**文档生成时间**: 2026/3/14
**文档版本**: 1.0
