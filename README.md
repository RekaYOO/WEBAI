# WEBAI - 结合 NEU 系统的 AI 应用

基于Flask + Vue3

## 启动说明

### 环境要求
- Python 3.8+
- Node.js 16+
- 有效的 AI API Key
- 东北大学统一身份认证账号（用于成绩分析功能）

### 完整启动步骤

1. 克隆项目
```bash
git clone <repository_url>
cd WEBAI
```

2. 后端配置
```bash
# 进入后端目录
cd backend

# 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
# 复制 config.example.json 为 config.json 并填写必要的 API Key
cp config.example.json config.json
# 编辑 config.json 文件，填入你的 API Key

# 配置成绩分析功能
# 复制 loadgrade/config.example.json 为 loadgrade/config.json 并填写账号信息
cp loadgrade/config.example.json loadgrade/config.json
# 编辑 loadgrade/config.json 文件，填入你的统一身份认证账号信息
```

3. 前端配置
```bash
# 进入前端目录
cd ../frontend

# 安装依赖
npm install
```

4. 启动服务

开发环境：
```bash
# 终端 1：启动后端服务
cd backend
venv\Scripts\activate     # Windows
python app.py

# 终端 2：启动前端服务
cd frontend
npm run dev
```

生产环境：
需要单独配置一下静态资源

### 访问应用

- 开发环境：
  - 前端：http://localhost:5173
  - 后端：http://localhost:5000

- 生产环境：
  - 应用：http://localhost:5000

### 配置文件说明

1. 后端主配置文件 (`backend/config.json`)
   - 包含 AI API Key 和系统配置
   - 从 `config.example.json` 复制并填写

2. 成绩分析配置文件 (`backend/loadgrade/config.json`)
   - 包含统一身份认证账号信息
   - 从 `loadgrade/config.example.json` 复制并填写
   - 格式示例：
     ```json
     {
         "user_info": {
             "username": "your_student_id",
             "password": "your_password"
         },
         "login_history": [],
         "last_login": null
     }
     ```

