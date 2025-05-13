# WEBAI

基于 Flask + Vue3 的 AI 对话应用。


## 部署方法

### 后端部署

1. 安装 Python 依赖
```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

2. 配置
- 复制 `config.example.json` 为 `config.json`
- 填写必要的 API Key

### 前端部署

1. 安装 Node.js 依赖
```bash
cd frontend
npm install
```

## 启动方法

### 开发环境

1. 启动后端服务
```bash
cd backend
python app.py
```

2. 启动前端服务
```bash
cd frontend
npm run dev
```

### 生产环境

1. 构建前端
```bash
cd frontend
npm run build
```

2. 启动后端服务
```bash
cd backend
flask run
```

## 目录结构

```
WEBAI/
├── backend/          # Flask 后端
│   ├── app.py       # 主应用
│   ├── config.json  # 配置文件
│   └── requirements.txt
└── frontend/        # Vue3 前端
    ├── src/         # 源代码
    ├── public/      # 静态资源
    └── package.json
``` 