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
from typing import Tuple, Union, List, Dict, Optional, Any
from load import GradeLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取当前文件所在目录
CURRENT_DIR = Path(__file__).parent
CONFIG_PATH = CURRENT_DIR / "loadgrade" / "config.json"
DATA_DIR = CURRENT_DIR / "data"

class Config:
    """配置管理类"""
    def __init__(self):
        self.config_data = self._load_config()
        self.openai_config = self.config_data.get('openai', {})
        self.system_config = self.config_data.get('system', {})
        self.models_config = self.config_data.get('models', {})
        self.data_config = self.config_data.get('data', {})

    def _load_config(self) -> dict:
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    @property
    def available_models(self) -> List[str]:
        return self.models_config.get('available', [])

    @property
    def default_model(self) -> str:
        return self.models_config.get('default', '')

    @property
    def thinking_models(self) -> List[str]:
        return self.models_config.get('thinking_models', [])

    @property
    def search_models(self) -> List[str]:
        return self.models_config.get('search_models', [])

    @property
    def system_content(self) -> str:
        return self.system_config.get('content', '')

class ConversationManager:
    """对话管理类"""
    def __init__(self, data_dir: str, conversations_file: str):
        self.data_dir = data_dir
        self.conversations_file = conversations_file
        self.conversations = self._load_conversations()
        os.makedirs(data_dir, exist_ok=True)

    def _load_conversations(self) -> dict:
        """加载已保存的对话"""
        if os.path.exists(self.conversations_file):
            try:
                with open(self.conversations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error("对话文件格式错误")
                return {}
        return {}

    def save_conversations(self):
        """保存对话到文件"""
        try:
            with open(self.conversations_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存对话失败: {e}")

    def create_conversation(self) -> dict:
        """创建新对话"""
        conversation_id = str(uuid.uuid4())
        conversation = {
            'id': conversation_id,
            'title': f'新对话 {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            'messages': []
        }
        self.conversations[conversation_id] = conversation
        self.save_conversations()
        return conversation

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            self.save_conversations()
            return True
        return False

    def get_conversation_history(self, conversation_id: str) -> List[dict]:
        """获取对话历史"""
        if conversation_id not in self.conversations:
            return []
        
        history = []
        messages = self.conversations[conversation_id]['messages']
        
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                history.append({
                    'user': messages[i]['content'],
                    'ai': messages[i + 1]['content'],
                    'reasoning': messages[i + 1].get('reasoning', ''),
                    'timestamp': messages[i]['timestamp']
                })
        
        return history

    def add_message(self, conversation_id: str, message: dict):
        """添加消息到对话"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]['messages'].append(message)
            self.save_conversations()

    def update_title(self, conversation_id: str, new_title: str):
        """更新对话标题"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id]['title'] = new_title
            self.save_conversations()

class AIClient:
    """AI客户端类"""
    def __init__(self, config: Config):
        self.client = OpenAI(
            api_key=config.openai_config['api_key'],
            base_url=config.openai_config['api_base']
        )
        self.config = config

    def is_thinking_model(self, model_name: str) -> bool:
        return model_name in self.config.thinking_models

    def is_search_model(self, model_name: str) -> bool:
        return model_name in self.config.search_models

    def is_tool_model(self, model_name: str) -> bool:
        return model_name in self.config.tool_models

    def is_qwq_model(self, model_name: str) -> bool:
        return model_name == "qwq-32b"

    def generate_title(self, messages: List[dict]) -> Optional[str]:
        """生成对话标题"""
        try:
            prompt = "请根据以下对话内容，生成一个简短的标题（不超过15个字）：\n\n"
            for msg in messages:
                role = "用户" if msg.get('isUser', True) else "AI"
                prompt += f"{role}: {msg['content']}\n"
            
            completion = self.client.chat.completions.create(
                model=self.config.default_model,
                messages=[
                    {'role': 'system', 'content': '你是一个标题生成助手，请根据对话内容生成简短的标题，由两个或三个词语组成，能够显而易见对话的主题'},
                    {'role': 'user', 'content': prompt}
                ],
                stream=False
            )
            
            title = completion.choices[0].message.content.strip()
            title = title.strip('"\'')
            if len(title) > 15:
                title = title[:15] + '...'
                
            return title
        except Exception as e:
            logger.error(f"生成标题失败: {e}")
            return None

class GradeAnalyzer:
    """成绩分析工具类"""
    def __init__(self, config_path: str, data_dir: str):
        self.loader = GradeLoader(config_path, data_dir)

    def analyze_gpa(self, use_cache: bool = True) -> Tuple[bool, Union[List[Dict], str]]:
        """分析绩点数据"""
        if use_cache:
            success, result = self.loader.read_analyzed_grades()
            if success:
                logger.info("使用缓存的成绩数据")
                return True, result
        
        success, result = self.loader.login()
        if not success:
            return False, f"登录失败：{result}"
        
        return self.loader.analyze_grades()

    def analyze_plan(self, use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
        """分析培养计划"""
        if use_cache:
            success, result = self.loader.read_analyzed_plan()
            if success:
                logger.info("使用缓存的培养计划数据")
                return True, result
        
        success, result = self.loader.login()
        if not success:
            return False, f"登录失败：{result}"
        
        return self.loader.analyze_plan()

    def analyze_plan_completion(self, use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
        """分析培养计划完成情况"""
        if use_cache:
            success, result = self.loader.read_analyzed_completion()
            if success:
                logger.info("使用缓存的培养计划完成情况数据")
                return True, result
        
        success, result = self.loader.login()
        if not success:
            return False, f"登录失败：{result}"
        
        return self.loader.analyze_plan_completion()

class ChatHandler:
    """聊天处理类"""
    def __init__(self, ai_client: AIClient, conversation_manager: ConversationManager, grade_analyzer: GradeAnalyzer):
        self.ai_client = ai_client
        self.conversation_manager = conversation_manager
        self.grade_analyzer = grade_analyzer
        self.tools_list = self._init_tools()

    def _init_tools(self) -> List[dict]:
        """初始化工具列表"""
        return [
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
                    "description": "分析学生培养计划的完成情况（学业预警），了解已修课程和未修课程。",
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

    def _handle_tool_call(self, tool_call: dict, tool_result: Any) -> Tuple[List[dict], str]:
        """处理工具调用结果"""
        messages = []
        content = ""

        # 添加工具调用消息
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": tool_call["id"],
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": tool_call["arguments"]
                }
            }]
        })

        # 添加工具调用结果
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": str(tool_result)
        })

        # 添加分析提示
        messages.append({
            "role": "system",
            "content": "请分析上述工具调用返回的数据，并给出详细的分析结果。如果是培养计划数据，请总结课程安排和要求；如果是成绩数据，请分析成绩表现；如果是完成情况，请分析完成进度。"
        })

        return messages, content

    def _execute_tool(self, tool_name: str, arguments: dict) -> Tuple[bool, Any]:
        """执行工具调用"""
        try:
            if tool_name == "analyze_gpa":
                return self.grade_analyzer.analyze_gpa(arguments.get("use_cache", True))
            elif tool_name == "analyze_plan":
                return self.grade_analyzer.analyze_plan(arguments.get("use_cache", True))
            elif tool_name == "analyze_plan_completion":
                return self.grade_analyzer.analyze_plan_completion(arguments.get("use_cache", True))
            else:
                return False, f"未知的工具：{tool_name}"
        except Exception as e:
            logger.error(f"工具调用执行失败: {e}")
            return False, str(e)

    def generate_stream_response(self, conversation_id: str, messages_for_ai: List[dict], 
                               model_name: str, deep_thinking: bool = True, 
                               web_search: bool = False) -> Any:
        """生成流式响应"""
        try:
            # 添加用户消息
            user_message = {
                'content': messages_for_ai[-1]['content'],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.conversation_manager.add_message(conversation_id, user_message)
            logger.info(f"添加用户消息: {user_message['content']}")

            # 准备AI响应
            full_content = ""
            reasoning_content = ""
            is_answering = False
            current_tool_call = None
            tool_call_arguments = ""
            new_title = None

            # 准备消息历史
            current_messages = [
                {'role': 'system', 'content': self.ai_client.config.system_content}
            ]
            current_messages.extend(messages_for_ai)
            logger.info(f"准备消息历史，包含{len(messages_for_ai)}轮对话")

            # 准备extra_body
            extra_body_text = {
                "enable_thinking": (self.ai_client.is_thinking_model(model_name) and deep_thinking),
                "enable_search": (self.ai_client.is_search_model(model_name) and web_search)
            }
            logger.info(f"模型配置: {model_name}, 深度思考: {deep_thinking}, 网络搜索: {web_search}")

            # 根据模型类型决定是否使用工具调用
            use_tools = self.ai_client.is_tool_model(model_name)
            logger.info(f"是否使用工具调用: {use_tools}")

            # 第一次调用AI
            completion = self.ai_client.client.chat.completions.create(
                model=model_name,
                messages=current_messages,
                stream=True,
                tools=self.tools_list if use_tools else None,
                extra_body=extra_body_text
            )

            # 处理AI响应
            for chunk in completion:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                
                # 处理思考内容
                if self.ai_client.is_thinking_model(model_name) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    if not is_answering:
                        reasoning_content += delta.reasoning_content
                        logger.info(f"收到思考内容: {delta.reasoning_content}")
                        yield f"data: {json.dumps({
                            'type': 'reasoning',
                            'content': delta.reasoning_content
                        })}\n\n"

                # 处理工具调用（仅当不使用qwq模型时）
                if use_tools and hasattr(delta, "tool_calls") and delta.tool_calls:
                    tool_call = delta.tool_calls[0]
                    logger.info(f"收到工具调用: {tool_call}")
                    
                    if hasattr(tool_call, "function") and tool_call.function:
                        if hasattr(tool_call, "id") and tool_call.id:
                            current_tool_call = {
                                "id": tool_call.id,
                                "name": None,
                                "arguments": ""
                            }
                            logger.info(f"开始新的工具调用: {tool_call.id}")
                        
                        if hasattr(tool_call.function, "name") and tool_call.function.name:
                            current_tool_call["name"] = tool_call.function.name
                            logger.info(f"工具名称: {tool_call.function.name}")
                        
                        if hasattr(tool_call.function, "arguments") and tool_call.function.arguments:
                            tool_call_arguments += tool_call.function.arguments
                            logger.info(f"工具参数: {tool_call_arguments}")

                # 处理回答内容
                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        is_answering = True
                        logger.info("开始接收AI回答")
                        yield f"data: {json.dumps({
                            'type': 'answer_start',
                            'content': ''
                        })}\n\n"
                    
                    full_content += delta.content
                    logger.info(f"收到回答内容: {delta.content}")
                    yield f"data: {json.dumps({
                        'type': 'answer',
                        'content': delta.content
                    })}\n\n"

            # 处理工具调用（仅当不使用qwq模型时）
            if use_tools and current_tool_call and current_tool_call["name"]:
                try:
                    logger.info("执行工具调用")
                    arguments = json.loads(tool_call_arguments)
                    logger.info(f"解析后的参数: {arguments}")
                    
                    success, result = self._execute_tool(current_tool_call["name"], arguments)
                    tool_result = result if success else f"分析失败：{result}"
                    logger.info(f"工具调用结果: {tool_result}")

                    # 处理工具调用结果
                    tool_messages, _ = self._handle_tool_call(current_tool_call, tool_result)
                    current_messages.extend(tool_messages)

                    # 发送工具调用结果
                    yield f"data: {json.dumps({
                        'type': 'tool_result',
                        'content': str(tool_result)
                    })}\n\n"

                    # 获取AI对工具调用结果的回复
                    logger.info("获取AI对工具调用结果的回复")
                    completion = self.ai_client.client.chat.completions.create(
                        model=model_name,
                        messages=current_messages,
                        stream=True,
                        tools=self.tools_list if use_tools else None,
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
                        
                        if self.ai_client.is_thinking_model(model_name) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            if not is_answering:
                                reasoning_content += delta.reasoning_content
                                logger.info(f"收到思考内容: {delta.reasoning_content}")
                                yield f"data: {json.dumps({
                                    'type': 'reasoning',
                                    'content': delta.reasoning_content
                                })}\n\n"

                        if hasattr(delta, "content") and delta.content:
                            if not is_answering:
                                is_answering = True
                                logger.info("开始接收AI回答")
                                yield f"data: {json.dumps({
                                    'type': 'answer_start',
                                    'content': ''
                                })}\n\n"
                            
                            full_content += delta.content
                            logger.info(f"收到回答内容: {delta.content}")
                            yield f"data: {json.dumps({
                                'type': 'answer',
                                'content': delta.content
                            })}\n\n"

                except json.JSONDecodeError as e:
                    logger.error(f"解析工具调用参数失败: {e}, 参数内容: {tool_call_arguments}")
                except Exception as e:
                    logger.error(f"工具调用执行失败: {e}")

            # 保存AI响应
            if full_content:
                ai_message = {
                    'content': full_content,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'isUser': False
                }
                if self.ai_client.is_thinking_model(model_name):
                    ai_message['reasoning'] = reasoning_content
                self.conversation_manager.add_message(conversation_id, ai_message)
                logger.info(f"保存AI响应: {ai_message}")

                # 更新对话标题
                if len(self.conversation_manager.conversations[conversation_id]['messages']) >= 4:
                    new_title = self.ai_client.generate_title(
                        self.conversation_manager.conversations[conversation_id]['messages']
                    )
                    if new_title:
                        self.conversation_manager.update_title(conversation_id, new_title)
                        logger.info(f"更新对话标题: {new_title}")

            # 发送完成信号
            completion_message = {
                'type': 'done',
                'messages': self.conversation_manager.conversations[conversation_id]['messages'],
                'title': new_title if new_title else self.conversation_manager.conversations[conversation_id]['title']
            }
            logger.info(f"发送完成信号: {completion_message}")
            yield f"data: {json.dumps(completion_message)}\n\n"

        except Exception as e:
            error_message = f"AI服务错误: {str(e)}"
            logger.error(error_message)
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
            self.conversation_manager.add_message(conversation_id, ai_message)

# 初始化应用
load_dotenv()
config = Config()
app = Flask(__name__)
CORS(app)

# 初始化各个组件
conversation_manager = ConversationManager(
    config.data_config['dir'],
    os.path.join(config.data_config['dir'], config.data_config['conversations_file'])
)
ai_client = AIClient(config)
grade_analyzer = GradeAnalyzer(str(CONFIG_PATH), str(DATA_DIR))
chat_handler = ChatHandler(ai_client, conversation_manager, grade_analyzer)

# API路由
@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    return jsonify(list(conversation_manager.conversations.values()))

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    conversation = conversation_manager.create_conversation()
    return jsonify(conversation), 201

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    if conversation_manager.delete_conversation(conversation_id):
        return '', 204
    return jsonify({'error': '对话不存在'}), 404

@app.route('/api/conversations/<conversation_id>/history', methods=['GET'])
def get_conversation_history(conversation_id):
    history = conversation_manager.get_conversation_history(conversation_id)
    if history is None:
        return jsonify({'error': '对话不存在'}), 404
    return jsonify(history)

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(config.available_models)

@app.route('/api/thinking_models', methods=['GET'])
def get_thinking_models():
    return jsonify(config.thinking_models)

@app.route('/api/search_models', methods=['GET'])
def get_search_models():
    return jsonify(config.search_models)

@app.route('/api/default_model', methods=['GET'])
def get_default_model():
    return jsonify(config.default_model)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        message = data.get('message')
        conversation_id = data.get('conversation_id')
        model_name = data.get('model_name', config.default_model)
        deep_thinking = data.get('deep_thinking', True)
        web_search = data.get('web_search', False)
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        if not conversation_id:
            return jsonify({'error': '对话ID不能为空'}), 400

        if conversation_id not in conversation_manager.conversations:
            return jsonify({'error': '对话不存在'}), 404
        
        # 准备完整的对话历史
        messages_for_ai = [
            {'role': 'system', 'content': config.system_content}
        ]
        for msg in conversation_manager.conversations[conversation_id]['messages']:
            if not msg.get('isError', False):
                messages_for_ai.append({
                    'role': 'user' if msg.get('isUser', True) else 'assistant',
                    'content': msg['content']
                })
        messages_for_ai.append({'role': 'user', 'content': message})

        def generate():
            for chunk in chat_handler.generate_stream_response(
                conversation_id, messages_for_ai, model_name, deep_thinking, web_search
            ):
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
        logger.error(f"聊天处理错误: {e}")
        return jsonify({'error': f'系统错误: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True) 