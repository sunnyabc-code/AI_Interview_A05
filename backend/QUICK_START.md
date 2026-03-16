# 快速启动指南

## 环境准备

### 1. 激活虚拟环境
```bash
.venv\Scripts\activate
```

### 2. 安装依赖（如需要）
```bash
pip install djangorestframework django-cors-headers drf-yasg djangorestframework-simplejwt pymysql cryptography
```

### 3. 创建超级用户
```bash
python manage.py createsuperuser
```

### 4. 启动开发服务器
```bash
python manage.py runserver
```

### 5. 访问Admin后台
```
http://127.0.0.1:8000/admin/
```

## 数据库操作

### 创建迁移
```bash
python manage.py makemigrations
```

### 执行迁移
```bash
python manage.py migrate
```

### 查看迁移状态
```bash
python manage.py showmigrations
```

## 开发规范

### 创建新的API端点

1. 在对应app的 `serializers.py` 中创建序列化器
2. 在对应app的 `views.py` 中创建视图
3. 在对应app的 `urls.py` 中配置路由
4. 在主路由 `AI_Interview/urls.py` 中引入

### 使用统一响应格式
```python
from core.response import APIResponse

# 成功响应
return APIResponse.success(data=result)

# 错误响应
return APIResponse.error(message="错误信息", code=400)
```

### 使用分页
```python
from core.pagination import StandardPagination

class MyViewSet(BaseViewSet):
    pagination_class = StandardPagination
```

### 抛出自定义异常
```python
from core.exceptions import ValidationError, NotFoundError

raise ValidationError(message="验证失败")
raise NotFoundError(message="资源不存在")
```

## 模块开发检查清单

### 数据层（同学A）
- [ ] 数据模型定义
- [ ] 序列化器实现
- [ ] Admin配置
- [ ] API视图实现
- [ ] 路由配置
- [ ] 数据验证

### 面试引擎（同学B）
- [ ] 大模型API集成
- [ ] RAG检索实现
- [ ] 对话流程控制
- [ ] Prompt模板设计
- [ ] 消息管理

### 评估分析（同学C）
- [ ] 评估算法实现
- [ ] 评分规则定义
- [ ] 语音识别集成
- [ ] 报告生成逻辑
- [ ] 情感分析

### 推荐系统（同学D）
- [ ] 推荐算法实现
- [ ] 学习路径生成
- [ ] 前端页面开发
- [ ] API接口实现
- [ ] 前后端联调

## 常用命令

### Django Shell
```bash
python manage.py shell
```

### 收集静态文件
```bash
python manage.py collectstatic
```

### 运行测试
```bash
python manage.py test
```

### 查看SQL
```bash
python manage.py sqlmigrate app_name migration_name
```

## 问题排查

### MySQL连接失败
```bash
# 检查MySQL服务状态并确认账号密码
# 再执行迁移验证连接
python manage.py migrate
```

### 端口被占用
```bash
# 使用其他端口
python manage.py runserver 8001
```

### 迁移冲突
```bash
# 合并迁移
python manage.py makemigrations --merge
```

## 联系方式

如有问题，请联系项目负责人或在团队群中讨论。
