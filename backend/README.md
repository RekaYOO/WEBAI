# 后端服务

这是一个基于 Flask 的后端服务，提供 AI 对话功能。

## 功能特性

- AI 对话接口
- CORS 支持
- 环境变量配置

## 安装和运行

1. 创建虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
- 创建 `.env` 文件
- 填写必要的环境变量：
  - DASHSCOPE_API_KEY：阿里云通义千问 API Key

4. 运行服务：
```bash
flask run
```

## API 接口

### AI 对话

#### 发送消息
- 路径：`/api/v1/chat`
- 方法：POST
- 请求体：
```json
{
    "message": "string"
}
```
- 响应示例：
```json
{
    "response": "AI的回复内容",
    "message": "AI响应成功"
}
```

## 注意事项

1. 确保正确配置 CORS
2. 需要有效的阿里云通义千问 API Key 