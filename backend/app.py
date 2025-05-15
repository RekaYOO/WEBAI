import os
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import uuid
from datetime import datetime
import json
import sys
from pathlib import Path
import logging
import pandas as pd
from typing import Tuple, Union, List, Dict
from load import GradeLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 获取当前文件所在目录
CURRENT_DIR = Path(__file__).parent
CONFIG_PATH = CURRENT_DIR / "loadgrade" / "config.json"
DATA_DIR = CURRENT_DIR / "data"

# 创建GradeLoader实例
loader = GradeLoader(str(CONFIG_PATH), str(DATA_DIR))

def analyze_gpa(use_cache: bool = True) -> Tuple[bool, Union[List[Dict], str]]:
    print("分析绩点数据")
    """
    分析绩点数据
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[List[Dict], str]]: (是否成功, 成绩数据列表或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的成绩数据
        success, result = loader.read_analyzed_grades()
        if success:
            logging.info("使用缓存的成绩数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析成绩
    return loader.analyze_grades()

def analyze_plan(use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
    print("分析培养计划")
    """
    分析培养计划
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的培养计划数据
        success, result = loader.read_analyzed_plan()
        if success:
            logging.info("使用缓存的培养计划数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析培养计划
    return loader.analyze_plan()

def analyze_plan_completion(use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
    print("分析培养计划完成情况")
    """
    分析培养计划完成情况
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的培养计划完成情况数据
        success, result = loader.read_analyzed_completion()
        if success:
            logging.info("使用缓存的培养计划完成情况数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析培养计划完成情况
    return loader.analyze_plan_completion()

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

# 定义工具列表
tools_list = [
    {
        "type": "function",
        "function": {
            "name": "analyze_gpa",
            "description": "分析学生的绩点数据，可以获取所有课程的成绩信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回，用户未提及时默认True",
                    }
                },
                "required": ["use_cache"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_plan",
            "description": "分析学生的培养计划，获取课程安排和要求。",
            "parameters": {
                "type": "object",
                "properties": {
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回，用户未提及时默认True",
                    }
                },
                "required": ["use_cache"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_plan_completion",
            "description": "分析学生培养计划的完成情况，了解已修课程和未修课程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "use_cache": {
                        "type": "boolean",
                        "description": "是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回，用户未提及时默认True",
                    }
                },
                "required": ["use_cache"],
            },
        },
    },
]

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

def is_search_model(model_name):
    return model_name in config['models']['search_models']

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

@app.route('/api/search_models', methods=['GET'])
def get_search_models():
    return jsonify(config['models']['search_models'])  # 返回搜索模型列表

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
        logging.info(f"添加用户消息: {user_message['content']}")

        # 准备AI响应
        full_content = ""
        reasoning_content = ""  # 完整思考过程
        is_answering = False  # 是否进入回复阶段
        current_tool_call = None  # 当前工具调用信息
        tool_call_arguments = ""  # 工具调用参数
        new_title = None  # 初始化new_title变量

        # 准备extra_body
        extra_body_text = {
            "enable_thinking": (is_thinking_model(model_name) and deep_thinking),
            "enable_search": (is_search_model(model_name) and web_search)
        }
        logging.info(f"模型配置: {model_name}, 深度思考: {deep_thinking}, 网络搜索: {web_search}")

        # 准备当前对话的消息历史
        current_messages = [
            {'role': 'system', 'content': config['system']['content']}
        ]
        # 添加完整的对话历史
        current_messages.extend(messages_for_ai)
        logging.info(f"准备消息历史，包含{len(messages_for_ai)}轮对话")

        # 调用AI接口
        try:
            logging.info("开始调用AI接口")
            completion = client.chat.completions.create(
                model=model_name,
                messages=current_messages,
                stream=True,
                tools=tools_list,
                extra_body=extra_body_text
            )

            # 重置工具调用状态
            current_tool_call = None
            tool_call_arguments = ""
            tool_result = None

            # 处理AI响应
            for chunk in completion:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                logging.debug(f"收到chunk: {chunk}")
                
                # 处理思考内容
                if is_thinking_model(model_name) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    if not is_answering:
                        reasoning_content += delta.reasoning_content
                        logging.info(f"收到思考内容: {delta.reasoning_content}")
                        yield f"data: {json.dumps({
                            'type': 'reasoning',
                            'content': delta.reasoning_content
                        })}\n\n"

                # 处理工具调用
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    logging.info(f"收到工具调用: {tool_call}")
                    
                    # 如果是新的工具调用开始
                    if hasattr(tool_call, "function") and tool_call.function:
                        # 获取工具调用ID
                        if hasattr(tool_call, "id") and tool_call.id:
                            current_tool_call = {
                                "id": tool_call.id,
                                "name": None,
                                "arguments": ""
                            }
                            logging.info(f"开始新的工具调用: {tool_call.id}")
                        
                        # 获取工具名称
                        if hasattr(tool_call.function, "name") and tool_call.function.name:
                            current_tool_call["name"] = tool_call.function.name
                            logging.info(f"工具名称: {tool_call.function.name}")
                        
                        # 获取工具参数
                        if hasattr(tool_call.function, "arguments") and tool_call.function.arguments:
                            tool_call_arguments += tool_call.function.arguments
                            logging.info(f"工具参数: {tool_call_arguments}")

                # 处理回答内容
                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        is_answering = True
                        logging.info("开始接收AI回答")
                        yield f"data: {json.dumps({
                            'type': 'answer_start',
                            'content': ''
                        })}\n\n"
                    
                    full_content += delta.content
                    logging.info(f"收到回答内容: {delta.content}")
                    yield f"data: {json.dumps({
                        'type': 'answer',
                        'content': delta.content
                    })}\n\n"

            # 如果收到了工具调用，执行工具并获取AI的回复
            if current_tool_call and current_tool_call["name"]:
                try:
                    logging.info("执行工具调用")
                    # 解析工具调用参数
                    arguments = json.loads(tool_call_arguments)
                    logging.info(f"解析后的参数: {arguments}")
                    
                    # 执行工具调用
                    if current_tool_call["name"] == "analyze_gpa":
                        logging.info("调用analyze_gpa函数")
                        success, result = analyze_gpa(arguments.get("use_cache", True))
                        tool_result = result if success else f"分析失败：{result}"
                    elif current_tool_call["name"] == "analyze_plan":
                        logging.info("调用analyze_plan函数")
                        success, result = analyze_plan(arguments.get("use_cache", True))
                        tool_result = result if success else f"分析失败：{result}"
                    elif current_tool_call["name"] == "analyze_plan_completion":
                        logging.info("调用analyze_plan_completion函数")
                        success, result = analyze_plan_completion(arguments.get("use_cache", True))
                        tool_result = result if success else f"分析失败：{result}"
                    
                    logging.info(f"工具调用结果: {tool_result}")
                    
                    # 添加模型的工具调用消息到历史
                    assistant_message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": current_tool_call["id"],
                            "type": "function",
                            "function": {
                                "name": current_tool_call["name"],
                                "arguments": tool_call_arguments
                            }
                        }]
                    }
                    current_messages.append(assistant_message)
                    logging.info(f"添加模型工具调用消息到历史: {assistant_message}")
                    
                    # 添加工具调用结果到消息历史
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": current_tool_call["id"],
                        "content": str(tool_result)
                    }
                    current_messages.append(tool_message)
                    logging.info(f"添加工具调用结果到消息历史: {tool_message}")

                    # 发送工具调用结果给前端
                    yield f"data: {json.dumps({
                        'type': 'tool_result',
                        'content': str(tool_result)
                    })}\n\n"

                    # 获取AI对工具调用结果的回复
                    logging.info("获取AI对工具调用结果的回复")
                    # 添加系统提示，要求AI分析工具调用结果
                    current_messages.append({
                        "role": "system",
                        "content": "请分析上述工具调用返回的数据，并给出详细的分析结果。如果是培养计划数据，请总结课程安排和要求；如果是成绩数据，请分析成绩表现；如果是完成情况，请分析完成进度。"
                    })
                    
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=current_messages,
                        stream=True,
                        tools=tools_list,
                        extra_body=extra_body_text
                    )

                    # 重置状态
                    full_content = ""
                    is_answering = False

                    # 处理AI的回复
                    for chunk in completion:
                        if not chunk.choices:
                            continue

                        delta = chunk.choices[0].delta
                        
                        # 处理思考内容
                        if is_thinking_model(model_name) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            if not is_answering:
                                reasoning_content += delta.reasoning_content
                                logging.info(f"收到思考内容: {delta.reasoning_content}")
                                yield f"data: {json.dumps({
                                    'type': 'reasoning',
                                    'content': delta.reasoning_content
                                })}\n\n"

                        # 处理回答内容
                        if hasattr(delta, "content") and delta.content:
                            if not is_answering:
                                is_answering = True
                                logging.info("开始接收AI回答")
                                yield f"data: {json.dumps({
                                    'type': 'answer_start',
                                    'content': ''
                                })}\n\n"
                            
                            full_content += delta.content
                            logging.info(f"收到回答内容: {delta.content}")
                            yield f"data: {json.dumps({
                                'type': 'answer',
                                'content': delta.content
                            })}\n\n"

                except json.JSONDecodeError as e:
                    logging.error(f"解析工具调用参数失败: {e}, 参数内容: {tool_call_arguments}")
                except Exception as e:
                    logging.error(f"工具调用执行失败: {e}")

            # 保存完整的AI响应到对话历史
            if full_content:  # 只有当有内容时才保存
                ai_message = {
                    'content': full_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'isUser': False
                }
                if is_thinking_model(model_name):
                    ai_message['reasoning'] = reasoning_content
                conversations[conversation_id]['messages'].append(ai_message)
                logging.info(f"保存AI响应: {ai_message}")

            # 更新对话标题
            if len(conversations[conversation_id]['messages']) >= 4:
                new_title = generate_conversation_title(conversations[conversation_id]['messages'])
                if new_title:
                    conversations[conversation_id]['title'] = new_title
                    logging.info(f"更新对话标题: {new_title}")

            # 保存到文件
            save_conversations()
            logging.info("保存对话历史到文件")

            # 发送完成信号
            completion_message = {
                'type': 'done',
                'messages': conversations[conversation_id]['messages'],
                'title': new_title if new_title else conversations[conversation_id]['title']
            }
            logging.info(f"发送完成信号: {completion_message}")
            yield f"data: {json.dumps(completion_message)}\n\n"

        except Exception as e:
            error_message = f"AI服务错误: {str(e)}"
            logging.error(f"AI服务错误: {str(e)}")
            yield f"data: {json.dumps({
                'type': 'error',
                'error': error_message
            })}\n\n"
            ai_message = {
                'content': error_message,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'isUser': False,
                'isError': True
            }
            conversations[conversation_id]['messages'].append(ai_message)
            save_conversations()

    except Exception as e:
        error_message = f'系统错误: {str(e)}'
        logging.error(error_message)
        yield f"data: {json.dumps({
            'type': 'error',
            'error': error_message
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