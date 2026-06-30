# AI模拟面试平台 — 测试用例文档

> 版本: v1.0
> 日期: 2026-06-29
> 对应课程: 软件工程管理、软件工程流程、软件工程经济学

---

## 目录

1. [测试策略概述](#1-测试策略概述)
2. [测试环境配置](#2-测试环境配置)
3. [单元测试用例](#3-单元测试用例)
4. [集成测试用例](#4-集成测试用例)
5. [API 端点测试用例](#5-api-端点测试用例)
6. [前端测试用例](#6-前端测试用例)
7. [AI 智能体测试用例](#7-ai-智能体测试用例)
8. [测试覆盖率目标](#8-测试覆盖率目标)
9. [测试执行与报告](#9-测试执行与报告)

---

## 1. 测试策略概述

### 1.1 测试金字塔

```
          ┌─────────┐
          │  E2E    │  5%   — 端到端：完整面试流程
          │  端到端  │
         ┌┴─────────┴┐
         │ Integration│ 15%  — 集成：API + 数据库 + LLM Mock
         │   集成测试  │
        ┌┴───────────┴┐
        │    Unit     │ 50%  — 单元：函数/类/模块
        │   单元测试   │
       ┌┴─────────────┴┐
       │   AI Agent   │ 30%  — 智能体：LLM 输出质量与稳定性
       │   智能体测试  │
       └───────────────┘
```

### 1.2 测试分层说明

| 层级 | 目标 | 框架 | 执行频率 |
|------|------|------|---------|
| **单元测试** | 验证函数/方法的正确性 | pytest + pytest-django | 每次提交 |
| **集成测试** | 验证模块间协作和数据库交互 | pytest + Django Test Client | 每次 PR |
| **AI智能体测试** | 验证 LLM 输出的格式正确性、评分合理性、追问适当性 | pytest + --run-llm | 每日/每周 |
| **前端测试** | 验证 Store、API、组件逻辑 | Vitest + jsdom | 每次提交 |
| **端到端测试** | 验证完整用户流程 | 手动 / Playwright | 里程碑节点 |

### 1.3 测试分类

| 分类 | 说明 | 示例 |
|------|------|------|
| **功能测试** | 验证功能是否正确 | 注册/登录/创建面试 |
| **边界测试** | 验证边界条件处理 | 空输入/超长输入/特殊字符 |
| **异常测试** | 验证异常处理 | 网络错误/数据库错误/认证失败 |
| **性能测试** | 验证响应时间和并发 | LLM 调用超时/大数量查询 |
| **安全测试** | 验证安全机制 | SQL注入/Token伪造/权限绕过 |
| **回归测试** | 防止新代码破坏旧功能 | 全套测试用例 |

---

## 2. 测试环境配置

### 2.1 后端测试环境

```bash
# 安装测试依赖
cd backend
pip install -r requirements.txt

# 运行单元测试（不调用真实 LLM API）
pytest -m "not llm" -v

# 运行全部测试（需要配置 .env 中的 DeepSeek API Key）
pytest --run-llm -v

# 运行指定模块测试
pytest interview_md/services/test_llm.py -v
pytest interview_md/test_views.py -v

# 生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term -m "not llm"
```

### 2.2 前端测试环境

```bash
# 安装前端测试依赖
cd frontend
npm install -D vitest @vitest/coverage-v8 jsdom @testing-library/jest-dom

# 运行测试
npx vitest run

# 监听模式
npx vitest

# 生成覆盖率
npx vitest run --coverage
```

### 2.3 DeepSeek API 配置

```bash
# 1. 复制配置模板
cd backend
cp .env.example .env

# 2. 编辑 .env 文件，填入你的 DeepSeek API Key
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_API_KEY=sk-your-actual-api-key
# LLM_MODEL=deepseek-chat

# 3. 测试配置是否正确
pytest interview_md/services/test_llm.py::TestDeepSeekApiCompatibility -v --run-llm
```

---

## 3. 单元测试用例

### 3.1 LLM 服务层 (`test_llm.py`)

| 编号 | 用例名称 | 输入 | 预期输出 | 优先级 |
|------|---------|------|---------|--------|
| LLM-01 | 纯JSON字符串提取 | `'{"score":85}'` | `{"score":85}` | P0 |
| LLM-02 | 带Markdown代码块提取 | ` ```json\n{...}\n``` ` | 正常解析JSON | P0 |
| LLM-03 | JSON前后有文字 | `'评估：{"s":80}\n以上'` | `{"s":80}` | P1 |
| LLM-04 | 嵌套JSON提取 | `'{"e":{"s":90}}'` | 完整嵌套结构 | P1 |
| LLM-05 | 含数组JSON | `'{"arr":[1,2]}'` | 数组正确解析 | P1 |
| LLM-06 | 空字符串处理 | `""` | `{}`（空字典） | P0 |
| LLM-07 | 无JSON文本处理 | `'这不是JSON'` | `{}` | P0 |
| LLM-08 | JSON语法错误 | `'{"key": invalid}'` | `{}` | P1 |
| LLM-09 | 未配置API抛异常 | `LLM_API_KEY=""` | `RuntimeError` | P0 |
| LLM-10 | 正常请求体构造 | 标准system_prompt | 正确构造messages/headers/body | P0 |
| LLM-11 | JSON模式自动启用 | prompt含"json" | `response_format: json_object` | P0 |
| LLM-12 | 历史消息正确追加 | history_messages传3条 | messages共4条(system+3) | P1 |
| LLM-13 | HTTP 500抛异常 | Mock返回500 | `RuntimeError` | P1 |
| LLM-14 | 空choices返回空串 | `choices:[]` | `""` | P1 |

### 3.2 JWT 认证 (`test_authentication.py`)

| 编号 | 用例名称 | 输入 | 预期输出 | 优先级 |
|------|---------|------|---------|--------|
| AUTH-01 | 签发token包含user_id | `issue_jwt(42)` | payload含`user_id:42` | P0 |
| AUTH-02 | 不同用户token不同 | `issue_jwt(1)` vs `issue_jwt(2)` | 两token不同 | P0 |
| AUTH-03 | 无Authorization返回None | 空请求头 | `None` | P0 |
| AUTH-04 | 正确token认证成功 | 有效Bearer token | 返回(user,None) | P0 |
| AUTH-05 | 用户不存在抛异常 | 有效token+不存在的user_id | `AuthenticationFailed` | P0 |
| AUTH-06 | 用户禁用抛异常 | user.status=0 | `AuthenticationFailed` | P0 |
| AUTH-07 | 伪造token抛异常 | "this.is.fake" | `AuthenticationFailed` | P1 |
| AUTH-08 | 过期token抛异常 | 1h前过期 | `AuthenticationFailed` | P1 |

### 3.3 会话服务 (`test_session_service.py`)

| 编号 | 用例名称 | 输入 | 预期输出 | 优先级 |
|------|---------|------|---------|--------|
| SESS-01 | 基本会话创建 | user+role+difficulty | session.status='running' | P0 |
| SESS-02 | 岗位不存在抛异常 | role_id=999 | `ValueError` | P0 |
| SESS-03 | 难度不存在抛异常 | difficulty='unknown' | `ValueError` | P0 |
| SESS-04 | 事务原子性验证 | 正常创建 | Session+Aspect+Chain+Round全创建 | P0 |
| SESS-05 | 难度影响链数 | hard(3+2+2) | total_chain_count=7 | P1 |
| SESS-06 | 首链状态为running | 创建后 | chain[0].status='running' | P0 |
| SESS-07 | 其余链状态为created | 创建后 | chain[1:].status='created' | P0 |
| SESS-08 | 权重从策略读取 | strategy.w_t=0.5 | aspect[0].weight=0.5 | P1 |
| SESS-09 | 无策略时默认权重 | 不创建strategy | aspect[1].weight=0.33 | P1 |
| SESS-10 | 选题循环逻辑 | 2题→取2次 | 两次不同题 | P1 |
| SESS-11 | 无题目返回None | 空题库 | `_pick_question→None` | P1 |
| SESS-12 | 语音模式创建 | mode='voice' | session.mode='voice' | P1 |

### 3.4 面试编排器 (`test_orchestrator.py`)

| 编号 | 用例名称 | 输入 | 预期输出 | 优先级 |
|------|---------|------|---------|--------|
| ORCH-01 | 空轮次转录 | `_build_transcript([])` | `""` | P0 |
| ORCH-02 | 单轮转录 | 1问1答 | 含"面试官"/"候选人"标签 | P0 |
| ORCH-03 | 仅问题无回答 | Q有A空 | 不含"候选人："行 | P1 |
| ORCH-04 | 平均分计算 | [80,75,85,70,90] | 80.00 | P0 |
| ORCH-05 | 部分None取均值 | [80,None,85] | 82.50 | P1 |
| ORCH-06 | 全部None默认60 | [None×5] | 60 | P1 |
| ORCH-07 | 会话不存在抛异常 | session_id=99999 | ValueError | P0 |
| ORCH-08 | 答案持久化 | 提交回答 | round.answer正确保存 | P0 |
| ORCH-09 | 无评估生成默认报告 | aggregate_report | overall_score=60 | P1 |
| ORCH-10 | 有评估正确聚合 | 3条ChainEval | 加权综合分 | P0 |
| ORCH-11 | GrowthSnapshot更新 | aggregate_report后 | gs.total_sessions>=1 | P1 |
| ORCH-12 | 权重影响总分 | w_t=0.8 | 技术分数占比最高 | P1 |

---

## 4. 集成测试用例

### 4.1 完整面试流程

| 编号 | 测试场景 | 步骤 | 验证点 | 优先级 |
|------|---------|------|--------|--------|
| INT-01 | **注册→登录→面试→报告** | 1.注册新用户 2.登录获取token 3.选择岗位创建面试 4.回答3轮问题 5.获取评估报告 | 全流程状态正确，数据一致 | P0 |
| INT-02 | **密码重置流程** | 1.用户存在 2.发送验证码 3.用验证码重置密码 4.新密码登录 | 密码成功更新，旧密码失效 | P0 |
| INT-03 | **多岗位面试** | 1.创建Java面试 2.完成后创建前端面试 | 两次面试互不影响 | P1 |
| INT-04 | **并发回答保护** | 同一轮次同时提交两个回答 | 行级锁生效，只有一个写入 | P1 |

### 4.2 数据库集成

| 编号 | 测试场景 | 验证点 | 优先级 |
|------|---------|--------|--------|
| DB-01 | 级联关系完整性 | 删除session→chain→round→eval的关联 | P0 |
| DB-02 | JSON字段读写 | strengths/weaknesses/suggestions 正确序列化 | P1 |
| DB-03 | Decimal精度 | 分数`80.00`存储和读取精度一致 | P1 |

---

## 5. API 端点测试用例

### 5.1 认证端点

| 编号 | 方法 | 路径 | 用例 | 预期状态码 |
|------|------|------|------|-----------|
| API-01 | POST | `/api/chain/auth/register/` | 正常注册 | 200, code=1 |
| API-02 | POST | `/api/chain/auth/register/` | 用户名已存在 | 200, code=400 |
| API-03 | POST | `/api/chain/auth/register/` | 密码<6位 | 200, code=400 |
| API-04 | POST | `/api/chain/auth/register/` | 用户名为空 | 200, code=400 |
| API-05 | POST | `/api/chain/auth/login/` | 正确密码 | 200, code=1, 含token |
| API-06 | POST | `/api/chain/auth/login/` | 错误密码 | 200, code=401 |
| API-07 | POST | `/api/chain/auth/login/` | 不存在用户 | 200, code=401 |
| API-08 | POST | `/api/chain/auth/send-code/` | 邮箱发送验证码 | 200, code=1, 6位码 |
| API-09 | POST | `/api/chain/auth/send-code/` | 未注册邮箱重置 | 200, code=400 |
| API-10 | POST | `/api/chain/auth/send-code/` | 邮箱格式错误 | 200, code=400 |
| API-11 | POST | `/api/chain/auth/send-code/` | 全角@自动转换 | 200, code=1 |
| API-12 | POST | `/api/chain/auth/reset-password/` | 完整重置流程 | 200, code=1 |
| API-13 | POST | `/api/chain/auth/reset-password/` | 错误验证码 | 200, code=400 |
| API-14 | POST | `/api/chain/auth/reset-password/` | 两次密码不一致 | 200, code=400 |

### 5.2 业务端点

| 编号 | 方法 | 路径 | 用例 | 预期 |
|------|------|------|------|------|
| API-15 | GET | `/api/scenario/list/` | 获取岗位列表 | 200, code=1, 数组 |
| API-16 | GET | `/api/scenario/list/` | 仅返回is_active=1 | 不包含禁用岗位 |
| API-17 | POST | `/api/session/create/` | 创建面试会话 | 200, code=1, sessionId |
| API-18 | POST | `/api/session/create/` | 无认证创建 | 401 |
| API-19 | POST | `/api/dialogue/next/` | 提交回答 | 200, code=1 |
| API-20 | POST | `/api/evaluation/submit/` | 提交评估 | 200, code=1 |
| API-21 | GET | `/api/report/detail/` | 获取报告 | 200, code=1 |
| API-22 | GET | `/api/report/detail/` | 不存在的报告 | 200, code=404 |
| API-23 | GET | `/api/profile/trend/` | 趋势数据 | 200, code=1 |
| API-24 | GET | `/api/profile/history/` | 历史记录 | 200, code=1 |

---

## 6. 前端测试用例

### 6.1 Pinia Store

| 编号 | Store | 用例 | 预期 |
|------|-------|------|------|
| FE-01 | user | setUser 正确设置 state | userId/nickname/token 全部更新 |
| FE-02 | user | nickname为空设空串 | nickname='' |
| FE-03 | user | 持久化到 localStorage | token和userId正确存储 |
| FE-04 | user | loadFromStorage 恢复状态 | 从localStorage正确读取 |
| FE-05 | user | localStorage无数据保持默认 | userId=0, token='' |
| FE-06 | user | userId解析失败设为0 | userId='not-number' → 0 |

### 6.2 axios 请求拦截器

| 编号 | 用例 | 预期 |
|------|------|------|
| FE-07 | 公开端点不注入token | 4个公开URL均不附加Authorization |
| FE-08 | 保护端点注入token | 非公开URL自动附加值Bearer |
| FE-09 | 无token时都不注入 | token=null时保护端点也不添加 |

### 6.3 axios 响应拦截器

| 编号 | 用例 | 预期 |
|------|------|------|
| FE-10 | code=1解包data | 返回`res.data.data` |
| FE-11 | code≠1 reject | Promise.reject |

---

## 7. AI 智能体测试用例

> 此类测试需要配置真实 LLM API Key，使用 `pytest --run-llm` 执行。

### 7.1 DeepSeek API 连通性

| 编号 | 用例 | Prompt | 验证点 | 容错标准 |
|------|------|--------|--------|---------|
| AI-01 | 基础连通 | `请回复"正常"` | 返回非空文本 | 100%成功率 |
| AI-02 | JSON输出 | 要求输出JSON | 可解析为合法JSON | ≥95% |
| AI-03 | 追问决策 | 模拟1轮面试对话 | 返回need_followup+followup_question | need_followup判断合理 |
| AI-04 | 面试评估 | 模拟完整问答 | 返回包含overall_score的JSON | 分数在0-100范围 |

### 7.2 LLM 输出质量评测

| 编号 | 测试维度 | 评测方法 | 量化指标 | 最低通过标准 |
|------|---------|---------|---------|------------|
| AI-05 | **格式正确性** | 100次调用中JSON可解析率 | JSON解析成功率 | ≥95% |
| AI-06 | **评分一致性** | 相同输入10次评分的方差 | `σ² < 25`（满分100） | 标准差<5 |
| AI-07 | **追问适当性** | 人工评审20条追问的合理性 | 合理追问占比 | ≥80% |
| AI-08 | **评分合理性** | 对比人工评分与LLM评分偏差 | `|LLM-人工| < 15` | ≥80%样本通过 |
| AI-09 | **响应时间** | P95延迟 | ≤30秒 | 单次<120秒 |

### 7.3 DeepSeek vs 百炼对比测试

| 编号 | 对比维度 | DeepSeek | 百炼(qwen-turbo) | 测试方法 |
|------|---------|---------|-----------------|---------|
| AI-10 | JSON格式遵循 | - | - | 100次prompt中JSON可解析次数 |
| AI-11 | 中文追问质量 | - | - | 人工盲评打分(1-5) |
| AI-12 | 评估分数方差 | - | - | 相同输入×10的标准差 |
| AI-13 | 平均响应延迟 | - | - | 调用100次取P50/P95 |

---

## 8. 测试覆盖率目标

| 模块 | 目标行覆盖率 | 目标分支覆盖率 | 当前状态 |
|------|------------|--------------|---------|
| `interview_md/services/llm.py` | 95% | 90% | ✅ 已编写 |
| `interview_md/services/orchestrator.py` | 85% | 80% | ✅ 已编写 |
| `interview_md/services/session_service.py` | 90% | 85% | ✅ 已编写 |
| `interview_md/authentication.py` | 95% | 90% | ✅ 已编写 |
| `interview_md/views.py` | 85% | 75% | ✅ 已编写 |
| `interview_md/models.py` | 70% | - | 待补充 |
| 其他 app (users/positions等) | 60% | - | 待补充 |
| **前端 Store** | 90% | 80% | ✅ 已编写 |
| **前端 API 层** | 80% | - | ✅ 已编写 |
| **前端 组件** | 60% | - | 待补充 |

---

## 9. 测试执行与报告

### 9.1 CI/CD 集成建议

```yaml
# GitHub Actions 示例
name: Test Suite
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && pytest -m "not llm" --cov=. --cov-report=xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - run: cd frontend && npm ci && npx vitest run --coverage
```

### 9.2 执行命令速查

| 场景 | 命令 |
|------|------|
| 快速冒烟 | `pytest -m "not llm" -x --tb=short` |
| 完整回归 | `pytest -m "not llm" --cov=. --cov-report=html` |
| 含AI测试 | `pytest --run-llm -v --tb=long` |
| 单文件调试 | `pytest interview_md/services/test_llm.py -vvs` |
| 前端测试 | `npx vitest run` |
| 前端覆盖率 | `npx vitest run --coverage` |

---

### 📊 统计摘要

| 指标 | 数值 |
|------|------|
| **后端测试文件** | 5个 |
| **后端测试函数** | 85+ |
| **前端测试文件** | 2个 |
| **前端测试函数** | 20+ |
| **API端点覆盖** | 14个端点 / 24个用例 |
| **AI智能体测试** | 13个评测用例 |
| **LLM容错测试** | 4类边界场景 |

---

*本文档随项目迭代持续更新。最后一次更新：2026-06-29*
