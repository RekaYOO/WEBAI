import os
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import uuid
from datetime import datetime
import json

# 加载环境变量（仅用于开发环境）
load_dotenv()

# 加载配置文件
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

config = load_config()

app = Flask(__name__)
CORS(app)

# OpenAI客户端配置
client = OpenAI(
    api_key=config['openai']['api_key'],
    base_url=config['openai']['api_base']
)

# 数据存储配置
DATA_DIR = config['data']['dir']
CONVERSATIONS_FILE = os.path.join(DATA_DIR, config['data']['conversations_file'])

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 初始化数据
def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_conversations():
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

# 加载已保存的对话
conversations = load_conversations()

# 模型配置
available_models = config['models']['available']
default_model = config['models']['default']

# 判断模型类型
def is_thinking_model(model_name):
    return model_name in config['models']['thinking_models']

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    return jsonify(list(conversations.values()))

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    conversation_id = str(uuid.uuid4())
    conversation = {
        'id': conversation_id,
        'title': f'新对话 {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        'messages': []
    }
    conversations[conversation_id] = conversation
    save_conversations()  # 保存到文件
    return jsonify(conversation), 201

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if conversation_id in conversations:
        del conversations[conversation_id]
        save_conversations()  # 保存到文件
        return '', 204
    return jsonify({'error': '对话不存在'}), 404

@app.route('/api/conversations/<conversation_id>/history', methods=['GET'])
def get_conversation_history(conversation_id):
    if conversation_id not in conversations:
        return jsonify({'error': '对话不存在'}), 404
    
    history = []
    messages = conversations[conversation_id]['messages']
    
    for i in range(0, len(messages), 2):
        if i + 1 < len(messages):
            history.append({
                'user': messages[i]['content'],
                'ai': messages[i + 1]['content'],
                'reasoning': messages[i + 1].get('reasoning', ''),
                'timestamp': messages[i]['timestamp']
            })
    
    return jsonify(history)

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(available_models)  # 直接返回模型列表

@app.route('/api/thinking_models', methods=['GET'])
def get_thinking_models():
    return jsonify(config['models']['thinking_models'])  # 返回思考模型列表

@app.route('/api/default_model', methods=['GET'])
def get_default_model():
    return jsonify(default_model)

def generate_conversation_title(messages):
    """使用默认模型生成对话标题"""
    try:
        # 准备提示词
        prompt = "请根据以下对话内容，生成一个简短的标题（不超过15个字）：\n\n"
        for msg in messages:
            role = "用户" if msg.get('isUser', True) else "AI"
            prompt += f"{role}: {msg['content']}\n"
        
        # 调用默认模型生成标题
        completion = client.chat.completions.create(
            model=default_model,
            messages=[
                {'role': 'system', 'content': '你是一个标题生成助手，请根据对话内容生成简短的标题，由两个或三个词语组成，能够显而易见对话的主题'},
                {'role': 'user', 'content': prompt}
            ],
            stream=False
        )
        
        # 获取生成的标题
        title = completion.choices[0].message.content.strip()
        # 移除可能的引号
        title = title.strip('"\'')
        # 限制长度
        if len(title) > 15:
            title = title[:15] + '...'
            
        return title
    except Exception as e:
        print(f"生成标题失败: {e}")
        return None

def generate_stream_response(conversation_id, messages_for_ai, model_name, deep_thinking=True, web_search=False):
    try:
        # 添加用户消息
        user_message = {
            'content': messages_for_ai[-1]['content'],
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        conversations[conversation_id]['messages'].append(user_message)

        # 准备AI响应
        full_content = ""
        reasoning_content = ""  # 完整思考过程
        is_answering = False  # 是否进入回复阶段

        # 准备extra_body
        extra_body_text = {
            "enable_thinking": (is_thinking_model(model_name) and deep_thinking),
            "enable_search": web_search  # 根据前端传来的参数设置
        }
        print(f"Debug - Model: {model_name}, Deep Thinking: {deep_thinking}, Web Search: {web_search}, Extra Body: {extra_body_text}")

        # 调用AI接口
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages_for_ai,
                stream=True,
                extra_body=extra_body_text
            )

            for chunk in completion:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                
                # 处理思考内容
                if is_thinking_model(model_name) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    if not is_answering:
                        reasoning_content += delta.reasoning_content
                        yield f"data: {json.dumps({
                            'type': 'reasoning',
                            'content': delta.reasoning_content
                        })}\n\n"

                # 处理回答内容
                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        is_answering = True
                        yield f"data: {json.dumps({
                            'type': 'answer_start',
                            'content': ''
                        })}\n\n"
                    
                    full_content += delta.content
                    yield f"data: {json.dumps({
                        'type': 'answer',
                        'content': delta.content
                    })}\n\n"

            # 保存完整的AI响应
            ai_message = {
                'content': full_content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'isUser': False
            }
            if is_thinking_model(model_name):
                ai_message['reasoning'] = reasoning_content  # 保存完整的思考内容
            conversations[conversation_id]['messages'].append(ai_message)

            # 更新对话标题
            # 当对话消息数量达到4条（2轮对话）时，生成新标题
            new_title = None
            if len(conversations[conversation_id]['messages']) >= 4:
                new_title = generate_conversation_title(conversations[conversation_id]['messages'])
                if new_title:
                    conversations[conversation_id]['title'] = new_title
                    print(f"Debug - 更新对话标题: {new_title}")

            # 保存到文件
            save_conversations()

            # 发送完成信号
            yield f"data: {json.dumps({
                'type': 'done',
                'messages': conversations[conversation_id]['messages'],
                'title': new_title  # 包含新生成的标题
            })}\n\n"

        except Exception as e:
            error_message = f"AI服务错误: {str(e)}"
            yield f"data: {json.dumps({
                'type': 'error',
                'error': error_message
            })}\n\n"
            # 记录错误消息
            ai_message = {
                'content': error_message,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'isUser': False,
                'isError': True
            }
            conversations[conversation_id]['messages'].append(ai_message)
            save_conversations()

    except Exception as e:
        yield f"data: {json.dumps({
            'type': 'error',
            'error': f'系统错误: {str(e)}'
        })}\n\n"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        message = data.get('message')
        conversation_id = data.get('conversation_id')
        model_name = data.get('model_name', default_model)
        deep_thinking = data.get('deep_thinking', True)  # 默认开启深度思考
        web_search = data.get('web_search', False)  # 获取联网搜索参数
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        if not conversation_id:
            return jsonify({'error': '对话ID不能为空'}), 400

        if conversation_id not in conversations:
            return jsonify({'error': '对话不存在'}), 404
        
        # 准备完整的对话历史
        messages_for_ai = [
            {'role': 'system', 'content': config['system']['content']}
        ]
        for msg in conversations[conversation_id]['messages']:
            if not msg.get('isError', False):  # 跳过错误消息
                messages_for_ai.append({
                    'role': 'user' if msg.get('isUser', True) else 'assistant',
                    'content': msg['content']
                })
        messages_for_ai.append({'role': 'user', 'content': message})

        def generate():
            for chunk in generate_stream_response(conversation_id, messages_for_ai, model_name, deep_thinking, web_search):
                yield chunk

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    except Exception as e:
        return jsonify({'error': f'系统错误: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True) 