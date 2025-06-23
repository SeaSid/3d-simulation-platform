#!/usr/bin/env python3
"""
3D仿真平台 - Flask后端应用
集成FastMCP服务，支持AI驱动的3D建模和物理仿真
"""

import json
import logging
import asyncio
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import requests
from simulation_service import MCPService
import threading
import time
import ollama
import uuid
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储仿真数据
simulation_data = {}

# Ollama配置
OLLAMA_MODEL = "modelscope.cn/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M"  # 使用本地可用模型
OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama默认地址

# 初始化Ollama客户端
try:
    ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
    # 测试连接
    models = ollama_client.list()
    logger.info(f"Ollama连接成功，可用模型: {[model['name'] for model in models['models']]}")
except Exception as e:
    logger.warning(f"Ollama连接失败: {e}")
    ollama_client = None

# 初始化MCP服务
mcp_service = MCPService()


# FastMCP服务器配置
FASTMCP_URL = "http://localhost:8000"

# MCP客户端配置
MCP_CONFIG = {
    "mcpServers": {
        "simulation_service": {
            "url": f"{FASTMCP_URL}/mcp",
            "transport": "streamable-http"
        }
    }
}

class MCPClient:
    """MCP客户端，使用FastMCP官方SDK"""
    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self._session_id = None
        self.is_initialized = False

    async def initialize(self):
        """初始化MCP连接"""
        try:
            from fastmcp import Client
            self.client = Client(self.config)
            self.is_initialized = True
            # 初始化会在async context manager中自动完成
            return True
        except Exception as e:
            print(f"初始化异常: {e}")
            self.is_initialized = False
            return False

    async def call_tool(self, tool_name: str, **kwargs) -> dict:
        """调用MCP工具"""
        if not self.client:
            if not await self.initialize():
                return {"success": False, "error": "MCP连接未初始化"}
        
        try:
            async with self.client:
                # FastMCP工具期望直接传递参数值
                result = await self.client.call_tool(tool_name, kwargs)
                return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_tools(self) -> list:
        """获取工具列表"""
        if not self.client:
            if not await self.initialize():
                return []
        
        try:
            async with self.client:
                tools = await self.client.list_tools()
                return [{"name": tool.name, "description": tool.description} for tool in tools]
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

# 创建MCP客户端
mcp_client = MCPClient(MCP_CONFIG)

# 检查FastMCP服务器可用性并输出工具数量
try:
    tools = asyncio.run(mcp_client.get_tools())
    logger.info(f"FastMCP服务器连接成功，可用工具: {len(tools)}")
except Exception as e:
    logger.warning(f"FastMCP服务器连接失败: {e}")
    logger.warning("将使用本地MCP服务作为备选")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/test')
def test_page():
    """测试页面"""
    return render_template('test_page.html')

@app.route('/test-shape')
def test_shape():
    """形状创建测试页面"""
    return render_template('test_shape.html')

@app.route('/api/shapes', methods=['POST'])
def create_shape():
    """创建3D形状API"""
    try:
        data = request.get_json()
        shape_type = data.get('type')
        params = data.get('params', {})
        
        # 使用MCP服务创建形状
        result = mcp_service.create_shape(shape_type, params)
        
        if result['success']:
            # 通过WebSocket发送到前端
            socketio.emit('shape_created', result['data'])
            return jsonify({"success": True, "message": f"成功创建{shape_type}"})
        else:
            return jsonify({"success": False, "error": result['error']})
    
    except Exception as e:
        logger.error(f"创建形状失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/simulation', methods=['POST'])
def run_simulation():
    """运行仿真API"""
    try:
        data = request.get_json()
        sim_type = data.get('type')
        params = data.get('params', {})
        
        # 使用MCP服务运行仿真
        result = mcp_service.run_simulation(sim_type, params)
        
        if result['success']:
            # 通过WebSocket发送仿真结果
            socketio.emit('simulation_result', result.get('data', {}))
            return jsonify({"success": True, "message": f"仿真完成"})
        else:
            return jsonify({"success": False, "error": result['error']})
    
    except Exception as e:
        logger.error(f"运行仿真失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI聊天API - 集成MCP工具调用"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"success": False, "error": "消息不能为空"})
        
        # 首先尝试使用MCP工具处理命令
        mcp_result = asyncio.run(mcp_client.call_tool("process_ai_command", command=user_message))
        
        if mcp_result.get("success"):
            # MCP工具成功处理了命令
            response_message = mcp_result.get("result", {}).get("message", "命令执行成功")
            
            # 发送AI回复
            socketio.emit('ai_response', {
                'message': response_message,
                'timestamp': time.time()
            })
            
            # 如果有仿真数据，发送到前端
            if 'simulation_data' in mcp_result.get("result", {}):
                socketio.emit('simulation_result', mcp_result["result"]['simulation_data'])
            
            # 如果有形状数据，发送到前端
            if 'shape_data' in mcp_result.get("result", {}):
                socketio.emit('shape_created', mcp_result["result"]['shape_data'])
            
            return jsonify({
                "success": True,
                "message": response_message,
                "tool_used": True
            })
        
        else:
            # MCP工具无法处理，使用简单的AI回复
            ai_response = generate_simple_ai_response(user_message)
            
            # 发送AI回复
            socketio.emit('ai_response', {
                'message': ai_response,
                'timestamp': time.time()
            })
            
            return jsonify({
                "success": True,
                "message": ai_response,
                "tool_used": False
            })
    
    except Exception as e:
        logger.error(f"AI聊天处理失败: {e}")
        return jsonify({"success": False, "error": str(e)})

def generate_simple_ai_response(user_message: str) -> str:
    """生成简单的AI回复（当MCP工具无法处理时）"""
    message_lower = user_message.lower()
    
    if any(word in message_lower for word in ['你好', 'hello', 'hi']):
        return "你好！我是3D仿真平台的AI助手。我可以帮你创建3D形状、运行物理仿真等。请告诉我你需要什么帮助！"
    
    elif any(word in message_lower for word in ['帮助', 'help', '功能']):
        return """我可以帮你：
1. 创建3D形状：立方体、球体、圆柱体
2. 运行物理仿真：重力仿真、碰撞仿真
3. 场景操作：重置视图、清空场景

试试说"创建立方体"或"运行重力仿真"！"""
    
    elif any(word in message_lower for word in ['谢谢', 'thank']):
        return "不客气！如果还有其他问题，随时告诉我。"
    
    else:
        return f"我理解你说的是：{user_message}。如果你需要创建3D形状或运行仿真，请使用具体的命令，比如'创建立方体'或'运行重力仿真'。"

@app.route('/api/tools', methods=['GET'])
def get_available_tools():
    """获取可用工具列表"""
    try:
        tools = asyncio.run(mcp_client.get_tools())
        return jsonify({"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取平台状态"""
    try:
        status = mcp_service.get_simulation_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return jsonify({"success": False, "error": str(e)})

@socketio.on('connect')
def handle_connect():
    """客户端连接处理"""
    logger.info("客户端已连接")
    emit('connected', {'message': '已连接到3D仿真平台'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接处理"""
    logger.info("客户端已断开连接")

@socketio.on('create_shape')
def handle_create_shape(data):
    """处理创建形状的WebSocket消息"""
    try:
        shape_type = data.get('type')
        params = data.get('params', {})
        
        logger.info(f"收到创建形状请求: {shape_type}, 参数: {params}")
        
        result = mcp_service.create_shape(shape_type, params)
        
        if result['success']:
            emit('shape_created', result['data'])
        else:
            emit('error', {'message': result['error']})
    
    except Exception as e:
        logger.error(f"WebSocket创建形状失败: {e}")
        emit('error', {'message': str(e)})

@socketio.on('simulate')
def handle_simulate(data):
    """处理运行仿真的WebSocket消息（前端发送simulate事件）"""
    try:
        sim_type = data.get('type')
        params = data.get('params', {})
        
        logger.info(f"收到仿真请求: {sim_type}, 参数: {params}")
        
        result = mcp_service.run_simulation(sim_type, params)
        
        if result['success']:
            emit('simulation_result', result.get('data', {}))
        else:
            emit('error', {'message': result['error']})
    
    except Exception as e:
        logger.error(f"WebSocket运行仿真失败: {e}")
        emit('error', {'message': str(e)})

def call_ollama_model_stream(message, session_id, sid=None):
    """流式调用Ollama本地大模型"""
    if not ollama_client:
        raise Exception("Ollama客户端未初始化")
    
    # 使用默认系统提示词
    system_prompt = """你是一个专业的仿真平台AI助手。你的主要功能包括：
1. 帮助用户创建3D几何体（立方体、球体、圆柱体等）
2. 进行物理仿真（重力、碰撞、流体等）
3. 分析模型属性和仿真结果
4. 提供技术支持和指导

回答格式要求：
1. 首先用<think>标签包含你的思考过程，说明你如何理解用户需求并决定采取的行动
2. 如果需要调用工具，在思考过程后使用[TOOL_CALL:工具名:参数]格式
3. 最后给出简洁专业的回答

可用工具：
- create_shape: 创建3D形状（参数：shape_type, size, radius, height等）
- run_simulation: 运行仿真（参数：simulation_type, time_steps等）
- reset_view: 重置视图
- clear_scene: 清空场景
- get_status: 获取状态

示例格式：
<think>
用户要求创建一个立方体。我需要使用create_shape工具，指定shape_type为cube，并设置合适的尺寸。
</think>
[TOOL_CALL:create_shape:{"shape_type": "cube", "size": 1.0}]
好的，我已经为您创建了一个立方体。

请用中文回答，回答要简洁专业。"""

    try:
        # 使用流式调用
        stream = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': message
                }
            ],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 500
            },
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                full_response += content
                
                # 发送流式内容（包含思考过程，但工具调用指令会被格式化显示）
                if sid:
                    socketio.emit('chat_message', {
                        'session_id': session_id,
                        'content': content,
                        'is_complete': False
                    }, room=sid)
        
        # 发送完整响应
        if sid:
            socketio.emit('chat_message', {
                'session_id': session_id,
                'content': full_response,
                'is_complete': True
            }, room=sid)
        
        return full_response
    
    except Exception as e:
        logger.error(f"Ollama流式API调用失败: {e}")
        raise e

def simulate_llm_response(message):
    """备用的大模型响应（当Ollama不可用时使用）"""
    # 简单的关键词匹配来模拟响应
    message_lower = message.lower()
    
    if 'cube' in message_lower or '立方体' in message_lower:
        return "我理解您想要创建一个立方体。立方体是一个三维几何体，具有6个面、12条边和8个顶点。我可以帮您生成一个立方体的仿真模型。"
    elif 'sphere' in message_lower or '球体' in message_lower:
        return "球体是一个完美的三维圆形物体。我可以为您创建一个球体模型，并计算其体积和表面积。"
    elif 'cylinder' in message_lower or '圆柱' in message_lower:
        return "圆柱体是一个三维几何体，具有两个平行的圆形底面和一个侧面。我可以帮您创建圆柱体模型。"
    elif 'simulate' in message_lower or '仿真' in message_lower:
        return "我可以帮您进行物理仿真。请告诉我您想要仿真什么类型的物理现象，比如重力、碰撞、流体等。"
    elif 'help' in message_lower or '帮助' in message_lower:
        return "我是您的仿真助手！我可以帮您：\n1. 创建3D几何体（立方体、球体、圆柱体等）\n2. 进行物理仿真\n3. 分析模型属性\n4. 生成仿真报告\n请告诉我您需要什么帮助！"
    else:
        return "我理解您的需求。作为仿真助手，我可以帮您创建3D模型、进行物理仿真和分析。请具体描述您想要创建的模型或进行的仿真类型。"

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """获取可用的Ollama模型列表"""
    try:
        if ollama_client:
            models = ollama_client.list()
            return jsonify({
                'success': True,
                'models': [model['name'] for model in models['models']],
                'current_model': OLLAMA_MODEL
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ollama未连接',
                'models': []
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'models': []
        })

@app.route('/api/set-model', methods=['POST'])
def set_model():
    """设置当前使用的模型"""
    global OLLAMA_MODEL
    data = request.json
    new_model = data.get('model')
    
    if new_model:
        try:
            # 验证模型是否存在
            if ollama_client:
                models = ollama_client.list()
                available_models = [model['name'] for model in models['models']]
                if new_model in available_models:
                    OLLAMA_MODEL = new_model
                    return jsonify({
                        'success': True,
                        'message': f'模型已切换到 {new_model}',
                        'current_model': OLLAMA_MODEL
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'模型 {new_model} 不可用'
                    })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Ollama未连接'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            })
    else:
        return jsonify({
            'success': False,
            'error': '未提供模型名称'
        })

@socketio.on('chat_message')
def handle_chat_message(data):
    """处理聊天消息的WebSocket事件"""
    user_message = data.get('message', '')
    session_id = data.get('session_id', f'session_{int(time.time())}')
    
    try:
        # 获取可用工具列表
        tools = asyncio.run(mcp_client.get_tools())
        tools_info = "\n".join([f"- {tool['name']}: {tool['description']}" for tool in tools])
        
        # 发送开始流式响应的信号
        socketio.emit('chat_start', {'session_id': session_id}, room=request.sid)
        
        # 在后台线程中处理流式响应
        def stream_response(sid):
            try:
                # 构建包含工具信息的系统提示词
                system_prompt = f"""你是一个专业的3D仿真平台AI助手。你可以帮助用户：

1. 创建3D几何体：
   - 创建立方体（可指定大小）
   - 创建球体（可指定半径）
   - 创建圆柱体（可指定半径和高度）

2. 控制3D视图：
   - 重置视图（将视图恢复到初始状态）
   - 切换线框模式（显示模型的线框结构）
   - 切换实体模式（显示模型的实体表面）

3. 进行物理仿真：
   - 重力仿真（模拟物体在重力作用下的运动）
   - 碰撞仿真（模拟物体之间的碰撞效果）

4. 场景管理：
   - 清空场景（移除所有已创建的物体）

可用工具：
{tools_info}

重要：当用户要求执行具体操作时，你必须严格按照以下格式回复：

[TOOL_CALL:工具名称:参数JSON]

JSON格式要求：
- 使用双引号包围键名和字符串值
- 数字值不需要引号
- 布尔值使用true或false（小写）
- 确保JSON格式完全正确

具体示例：
- 用户说"创建立方体"，你回复："我来为您创建一个立方体。[TOOL_CALL:create_shape:{{\"shape_type\":\"cube\",\"size\":1.0}}]"
- 用户说"运行重力仿真"，你回复："开始运行重力仿真。[TOOL_CALL:run_simulation:{{\"simulation_type\":\"gravity\"}}]"
- 用户说"创建一个半径为1.5的球体"，你回复："我来为您创建一个半径为1.5的球体。[TOOL_CALL:create_shape:{{\"shape_type\":\"sphere\",\"radius\":1.5}}]"

注意：
1. 工具调用指令必须放在回复的最后
2. JSON中的双引号必须正确转义（在Python字符串中使用\\"）
3. 如果用户只是询问或聊天，正常回复即可，不需要工具调用
4. 工具调用后，系统会自动执行相应操作并返回结果

请用中文回答，回答要简洁专业。"""

                # 调用Ollama获取响应
                response = call_ollama_model_stream_with_tools(user_message, session_id, sid, system_prompt)
                
                # 发送完成信号
                socketio.emit('chat_complete', {
                    'session_id': session_id,
                    'model': OLLAMA_MODEL
                }, room=sid)
                
            except Exception as e:
                logger.error(f"流式调用大模型失败: {e}")
                # 发送错误信息
                socketio.emit('chat_error', {
                    'session_id': session_id,
                    'error': str(e)
                }, room=sid)
                # 使用备用响应
                fallback_response = simulate_llm_response(user_message)
                socketio.emit('chat_message', {
                    'session_id': session_id,
                    'content': fallback_response,
                    'is_complete': True,
                    'model': 'fallback'
                }, room=sid)
        
        thread = threading.Thread(target=stream_response, args=(request.sid,))
        thread.start()
        
    except Exception as e:
        logger.error(f"处理WebSocket聊天消息失败: {e}")
        socketio.emit('chat_error', {
            'session_id': session_id,
            'error': str(e)
        }, room=request.sid)

@socketio.on('mcp_command')
def handle_mcp_command(data):
    """处理MCP命令"""
    try:
        command = data.get('command')
        params = data.get('parameters', {})
        
        if command == 'initialize':
            result = mcp_service.initialize_simulation(params)
        elif command == 'simulate':
            simulation_type = params.get('type')
            sim_params = params.get('parameters', {})
            result = mcp_service.run_simulation(simulation_type, sim_params)
        elif command == 'reset':
            result = mcp_service.reset_simulation()
        else:
            result = {"success": False, "error": f"未知命令: {command}"}
        
        emit('mcp_response', result)
    except Exception as e:
        emit('mcp_error', {"error": str(e)})

def call_ollama_model_stream_with_tools(message, session_id, sid=None, system_prompt=None):
    """流式调用Ollama本地大模型，支持多工具调用"""
    if not ollama_client:
        raise Exception("Ollama客户端未初始化")
    if not system_prompt:
        system_prompt = """你是一个专业的仿真平台AI助手。你的主要功能包括：\n1. 帮助用户创建3D几何体（立方体、球体、圆柱体等）\n2. 进行物理仿真（重力、碰撞、流体等）\n3. 分析模型属性和仿真结果\n4. 提供技术支持和指导\n\n回答格式要求：\n1. 首先用<think>标签包含你的思考过程，说明你如何理解用户需求并决定采取的行动\n2. 如果需要调用工具，在思考过程后使用[TOOL_CALL:工具名:参数]格式\n3. 最后给出简洁专业的回答\n\n可用工具：\n- create_shape: 创建3D形状（参数：shape_type, size, radius, height等）\n- run_simulation: 运行仿真（参数：simulation_type, time_steps等）\n- reset_view: 重置视图\n- clear_scene: 清空场景\n- get_status: 获取状态\n\n示例格式：\n<think>\n用户要求创建一个立方体。我需要使用create_shape工具，指定shape_type为cube，并设置合适的尺寸。\n</think>\n[TOOL_CALL:create_shape:{\"shape_type\": \"cube\", \"size\": 1.0}]\n好的，我已经为您创建了一个立方体。\n\n请用中文回答，回答要简洁专业。"""
    try:
        stream = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': message}
            ],
            options={
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 500
            },
            stream=True
        )
        full_response = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                content = chunk['message']['content']
                full_response += content
                if sid:
                    socketio.emit('chat_message', {
                        'session_id': session_id,
                        'content': content,
                        'is_complete': False
                    }, room=sid)
        # 检查是否包含多条工具调用指令
        tool_call_pattern = r'\[TOOL_CALL:([^:]+):(.+?)\]'
        all_matches = list(re.finditer(tool_call_pattern, full_response, re.DOTALL))
        if all_matches:
            last_idx = len(all_matches) - 1
            start_idx = last_idx
            for i in range(last_idx - 1, -1, -1):
                if all_matches[i].end() + 2 < all_matches[i+1].start():
                    break
                start_idx = i
            tool_calls = [ (m.group(1), m.group(2)) for m in all_matches[start_idx:] ]
        else:
            tool_calls = []
        valid_tools = ['create_shape', 'run_simulation', 'reset_view', 'clear_scene', 'get_status', 'process_ai_command']
        if tool_calls:
            print(f"检测到多条工具调用指令: {tool_calls}")
            results = []
            for tool_name, tool_params_str in tool_calls:
                tool_name = tool_name.strip()
                tool_params_str = tool_params_str.strip()
                tool_params_str = tool_params_str.replace('\\"', '"').replace('\\\\', '\\')
                if not tool_params_str.startswith('{'):
                    tool_params_str = '{' + tool_params_str
                if not tool_params_str.endswith('}'):
                    tool_params_str = tool_params_str + '}'
                try:
                    import json
                    tool_params = json.loads(tool_params_str)
                except Exception:
                    tool_params = {}
                if tool_name not in valid_tools or not isinstance(tool_params, dict) or not tool_params:
                    print(f"跳过无效工具调用: 工具={tool_name}, 参数={tool_params}")
                    continue
                async def execute_tool_call(tool_name, tool_params):
                    try:
                        socketio.emit('tool_call_start', {'tool': tool_name, 'params': tool_params}, room=sid)
                        result = await mcp_client.call_tool(tool_name, **tool_params)
                        if result and isinstance(result, dict) and 'result' in result:
                            r = result['result']
                            try:
                                from mcp.types import TextContent
                            except ImportError:
                                TextContent = None
                            def textcontent_to_dict(obj):
                                if hasattr(obj, 'text'):
                                    try:
                                        import json
                                        return json.loads(obj.text)
                                    except Exception:
                                        return {'text': obj.text}
                                return str(obj)
                            if isinstance(r, list):
                                result['result'] = [textcontent_to_dict(x) for x in r]
                            elif TextContent and isinstance(r, TextContent):
                                result['result'] = textcontent_to_dict(r)
                            socketio.emit('tool_call_complete', {
                                'tool': tool_name,
                                'params': tool_params,
                                'success': result.get('success', False),
                                'result': result
                            }, room=sid)
                        if tool_name == "create_shape" and result.get("result"):
                            shape_result = result["result"]
                            if isinstance(shape_result, list) and len(shape_result) > 0:
                                shape_data = shape_result[0].get("data")
                                if shape_data:
                                    socketio.emit('shape_created', shape_data, room=sid)
                            elif isinstance(shape_result, dict) and "data" in shape_result:
                                socketio.emit('shape_created', shape_result["data"], room=sid)
                        return {'tool': tool_name, 'params': tool_params, 'result': result}
                    except Exception as e:
                        socketio.emit('tool_call_complete', {
                            'tool': tool_name,
                            'params': tool_params,
                            'success': False,
                            'error': str(e)
                        }, room=sid)
                        return {'tool': tool_name, 'params': tool_params, 'result': {'success': False, 'error': str(e)}}
                import asyncio
                result = asyncio.run(execute_tool_call(tool_name, tool_params))
                results.append(result)
            clean_response = re.sub(tool_call_pattern, '', full_response).strip()
            if clean_response:
                if sid:
                    socketio.emit('chat_message', {
                        'session_id': session_id,
                        'content': clean_response,
                        'is_complete': True
                    }, room=sid)
            return {'success': True, 'results': results}
        else:
            if sid:
                socketio.emit('chat_message', {
                    'session_id': session_id,
                    'content': full_response,
                    'is_complete': True
                }, room=sid)
            return {'success': True, 'results': []}
    except Exception as e:
        logger.error(f"Ollama流式API调用失败: {e}")
        raise e

@app.route('/jscad_editor')
def jscad_editor():
    return render_template('jscad_editor.html')

if __name__ == '__main__':
    logger.info("启动3D仿真平台...")
    logger.info(f"FastMCP服务器地址: {FASTMCP_URL}")
    
    socketio.run(app, host='0.0.0.0', port=6006, debug=True) 