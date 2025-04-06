# 医疗知识图谱系统 - 后端

本项目是医疗知识图谱问答系统的后端服务，基于Django框架开发，提供用户认证、知识图谱查询和医疗问答功能。

## 安装指南

### 1. 环境需求

- Python 3.8+
- MySQL 5.7+
- Neo4j 4.4+

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建`.env`文件在项目根目录，添加以下配置：

```
DJANGO_SECRET_KEY=your_secret_key
MEDKG_DEBUG=False
DB_NAME=medkg_qa
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 4. 数据库迁移

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### 5. 创建超级用户

```bash
python manage.py createsuperuser
```

### 6. 启动服务

```bash
python manage.py runserver 0.0.0.0:8000
```

## API文档

### 用户认证API

#### 用户注册
- URL: `/api/register/`
- 方法: POST
- 参数: 
  - username: 用户名（3字符以上）
  - password: 密码（6字符以上）
  - email: 邮箱地址

#### 用户登录
- URL: `/api/login/`
- 方法: POST
- 参数:
  - username: 用户名
  - password: 密码

#### 获取用户信息
- URL: `/api/user-info/`
- 方法: GET
- 认证: 需要Bearer Token

### 知识图谱问答API

#### 医疗问答
- URL: `/api/qa/`
- 方法: GET/POST
- 参数:
  - question: 医疗问题

## 前端集成

前端项目需要配置以下内容：

1. 确保API请求地址正确配置
2. 登录成功后保存JWT令牌
3. 后续请求带上Authorization头：`Bearer {token}`

## 项目结构

```
medkg_backend/
├── accounts/         # 用户认证模块
├── kg_module/        # 知识图谱模块
├── nlp_module/       # 自然语言处理模块
├── qa_api/           # 问答接口模块
├── utils/            # 工具函数
└── medkg_backend/    # 项目配置
``` 