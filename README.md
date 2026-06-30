# AI_Interview_A05

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2.12-092E20?logo=django&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vuedotjs&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-REST%20API-009688)
![License](https://img.shields.io/badge/License-TODO-lightgrey)

面向大学生职业能力提升的 AI 模拟面试平台，提供岗位化题库、智能面试、多轮评估、语音分析与学习推荐的一体化能力，帮助用户在真实面试前完成高频训练与针对性提升。

## 项目简介

AI_Interview_A05 是一个基于 Django + DRF + Vue 3 的前后端分离项目，核心目标是把“练面试、做评估、看改进、继续学习”串成闭环。

核心特性：

- 支持岗位导向的面试流程设计
- 支持 JWT 登录认证与后台管理
- 支持面试记录、轮次分析和总评估
- 支持语音识别、音频分析与大模型能力接入
- 支持个性化学习路径与推荐内容
- 支持 Swagger / ReDoc 接口文档

## 核心功能

- 🎯 岗位化面试：围绕不同岗位组织题库、轮次和评估逻辑。
- 🤖 智能对话：通过大模型接口驱动面试问答与追问。
- 🧠 多维评估：输出综合分、能力项分析、亮点、不足与建议。
- 🎙️ 语音能力：支持音频上传、转写和语音相关分析流程。
- 📚 学习推荐：根据面试结果生成学习资源与学习路径。
- 📈 可视化前端：使用 Vue 3、Pinia、ECharts、D3、WaveSurfer 构建交互页面。

## 技术栈

| 层级          | 技术                                                             |
| ------------- | ---------------------------------------------------------------- |
| 后端          | Django 5.2.12、Django REST Framework、Simple JWT、CORS、drf-yasg |
| 异步任务      | Celery、Redis                                                    |
| 数据库        | MySQL                                                            |
| 音频与 ASR    | faster-whisper、openai-whisper、librosa、SciPy、webrtcvad        |
| 大模型接入    | DashScope、OpenAI 兼容接口                                       |
| 前端          | Vue 3、Vite、TypeScript、Pinia、Vue Router                       |
| 图表与音频 UI | ECharts、D3、WaveSurfer                                          |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20.19+ 或 22.12+
- MySQL 8.x
- Redis 7.x
- 可选：FFmpeg

### 1. 克隆项目

```bash
git clone <repository-url>
cd AI_Interview_A05
```

### 2. 启动后端

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

如果你计划使用 Docker，请先准备 `backend/.env.docker`，因为当前 `docker-compose.yml` 会读取该文件，但仓库中没有提供示例。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 最简运行路径

```bash
cd backend
python manage.py runserver
```

访问地址：

- 后端管理后台：`http://127.0.0.1:8000/admin/`
- Swagger：`http://127.0.0.1:8000/swagger/`
- ReDoc：`http://127.0.0.1:8000/redoc/`

## 使用示例

### 本地开发

```bash
# 后端
cd backend
python manage.py runserver

# 前端
cd frontend
npm run dev
```

### Docker 启动

```bash
docker compose up --build
```

如需启动 Celery Beat：

```bash
docker compose --profile beat up --build
```

![1782807175411](image/README/1782807175411.png)

## 配置说明

后端会自动读取仓库根目录或 backend 目录下的 `.env` 文件。当前仓库可确认的关键配置如下：

| 变量                       | 说明                            |
| -------------------------- | ------------------------------- |
| `DASHSCOPE_API_KEY`      | 阿里云百炼 / DashScope 调用密钥 |
| `DASHSCOPE_APP_IDS_JSON` | 按岗位映射的应用 ID 配置        |
| `LLM_BASE_URL`           | 大模型兼容接口地址              |
| `LLM_API_KEY`            | 大模型接口密钥                  |
| `LLM_MODEL`              | 默认模型名                      |
| `CELERY_BROKER_URL`      | Celery Broker 地址，默认 Redis  |
| `ASR_PROVIDER`           | 语音识别提供方                  |
| `FFMPEG_BINARY`          | FFmpeg 路径，用于音频格式转换   |

前端环境变量：

| 文件                          | 说明                                          |
| ----------------------------- | --------------------------------------------- |
| `frontend/.env.development` | 本地开发配置，默认 `VITE_API_BASE_URL=/api` |
| `frontend/.env.production`  | 生产环境配置，默认需要替换为真实后端地址      |

## API 与文档

后端已接入接口文档：

- Swagger UI：`/swagger/`
- ReDoc：`/redoc/`

项目接口采用 REST 风格与统一响应结构，主要模块包括：

- 用户与认证
- 岗位管理
- 题库管理
- 面试流程
- 轮次分析
- 评估报告
- 学习推荐
- 用户作品与路径扩展模块

## 目录结构

```text
AI_Interview_A05/
├── backend/            # Django 后端
├── frontend/           # Vue 3 前端
├── docker-compose.yml  # Docker 编排
├── requirements.txt    # Python 依赖
└── README.md
```
