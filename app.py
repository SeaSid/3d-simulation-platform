from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import numpy as np
import time
import threading
import ollama
import logging
from mcp import mcp_service

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/mcp/initialize', methods=['POST'])
def initialize_mcp():
    """初始化MCP服务"""
    try:
        params = request.json
        result = mcp_service.initialize_simulation(params)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/mcp/simulate', methods=['POST'])
def run_mcp_simulation():
    """运行MCP仿真"""
    try:
        data = request.json
        simulation_type = data.get('type')
        params = data.get('parameters', {})
        result = mcp_service.run_simulation(simulation_type, params)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/mcp/status', methods=['GET'])
def get_mcp_status():
    """获取MCP服务状态"""
    try:
        result = mcp_service.get_simulation_status()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/mcp/reset', methods=['POST'])
def reset_mcp():
    """重置MCP服务"""
    try:
        result = mcp_service.reset_simulation()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天消息"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', '')
        
        if not message:
            return jsonify({"success": False, "error": "消息不能为空"})
        
        # 发送开始信号
        socketio.emit('chat_start', {'session_id': session_id})
        
        def process_response():
            try:
                # 处理AI命令
                result = mcp_service.process_ai_command(message)
                
                if result["success"]:
                    if result.get("is_command", True):
                        # 如果是命令，发送命令执行结果
                        socketio.emit('simulation_response', {
                            'session_id': session_id,
                            'data': result
                        })
                    else:
                        # 如果不是命令，发送AI响应
                        socketio.emit('chat_response', {
                            'session_id': session_id,
                            'response': result["response"]
                        })
                else:
                    # 发送错误消息
                    socketio.emit('simulation_error', {
                        'session_id': session_id,
                        'error': result["error"]
                    })
                
                # 发送完成信号
                socketio.emit('chat_complete', {'session_id': session_id})
                
            except Exception as e:
                logger.error(f"处理响应时出错: {e}")
                socketio.emit('simulation_error', {
                    'session_id': session_id,
                    'error': str(e)
                })
                socketio.emit('chat_complete', {'session_id': session_id})
        
        # 在后台线程中处理响应
        thread = threading.Thread(target=process_response)
        thread.start()
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"处理聊天请求时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/shape/create', methods=['POST'])
def create_shape():
    """创建3D形状"""
    try:
        data = request.get_json()
        shape_type = data.get('type')
        params = data.get('parameters', {})
        
        result = mcp_service.create_shape(shape_type, params)
        return jsonify(result)
    except Exception as e:
        logger.error(f"创建形状时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/view/reset', methods=['POST'])
def reset_view():
    """重置视图"""
    try:
        result = mcp_service.reset_view()
        return jsonify(result)
    except Exception as e:
        logger.error(f"重置视图时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/view/mode', methods=['POST'])
def set_view_mode():
    """设置视图模式"""
    try:
        data = request.get_json()
        mode = data.get('mode')
        
        result = mcp_service.set_view_mode(mode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"设置视图模式时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/simulation/run', methods=['POST'])
def run_simulation():
    """运行仿真"""
    try:
        data = request.get_json()
        simulation_type = data.get('type')
        params = data.get('parameters', {})
        
        result = mcp_service.run_simulation(simulation_type, params)
        return jsonify(result)
    except Exception as e:
        logger.error(f"运行仿真时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/scene/clear', methods=['POST'])
def clear_scene():
    """清空场景"""
    try:
        result = mcp_service.clear_scene()
        return jsonify(result)
    except Exception as e:
        logger.error(f"清空场景时出错: {e}")
        return jsonify({"success": False, "error": str(e)})

def call_ollama_model_stream(message, session_id, sid=None):
    """流式调用Ollama本地大模型"""
    if not ollama_client:
        raise Exception("Ollama客户端未初始化")
    
    # 构建系统提示词
    system_prompt = """你是一个专业的仿真平台AI助手。你的主要功能包括：
1. 帮助用户创建3D几何体（立方体、球体、圆柱体等）
2. 进行物理仿真（重力、碰撞、流体等）
3. 分析模型属性和仿真结果
4. 提供技术支持和指导

请用中文回答，回答要简洁专业。如果用户要求创建模型，请确认并说明你将帮助他们创建相应的3D模型。"""

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
                
                # 发送流式内容
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

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    try:
        logger.info("Client connected")
        status = mcp_service.get_simulation_status()
        emit('simulation_status', status)
    except Exception as e:
        logger.error(f"处理连接时出错: {e}")
        emit('error', {'error': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('create_shape')
def handle_create_shape(data):
    """处理创建3D形状的请求"""
    shape_type = data.get('type')
    params = data.get('params', {})
    
    # 生成形状数据
    shape_data = generate_shape_data(shape_type, params)
    
    # 发送形状数据到前端
    emit('shape_created', {
        'type': shape_type,
        'data': shape_data,
        'id': f"{shape_type}_{int(time.time())}"
    })

@socketio.on('simulate')
def handle_simulation(data):
    """处理仿真请求"""
    simulation_type = data.get('type')
    params = data.get('params', {})
    
    # 在后台线程中运行仿真
    def run_simulation():
        result = perform_simulation(simulation_type, params)
        socketio.emit('simulation_result', result)
    
    thread = threading.Thread(target=run_simulation)
    thread.start()
    
    emit('simulation_started', {'message': f'开始{simulation_type}仿真...'})

def generate_shape_data(shape_type, params):
    """生成3D形状的几何数据"""
    if shape_type == 'cube':
        size = params.get('size', 1.0)
        return {
            'vertices': generate_cube_vertices(size),
            'faces': generate_cube_faces(),
            'type': 'cube',
            'size': size
        }
    elif shape_type == 'sphere':
        radius = params.get('radius', 1.0)
        segments = params.get('segments', 16)
        return {
            'vertices': generate_sphere_vertices(radius, segments),
            'faces': generate_sphere_faces(segments),
            'type': 'sphere',
            'radius': radius
        }
    elif shape_type == 'cylinder':
        radius = params.get('radius', 1.0)
        height = params.get('height', 2.0)
        segments = params.get('segments', 16)
        return {
            'vertices': generate_cylinder_vertices(radius, height, segments),
            'faces': generate_cylinder_faces(segments),
            'type': 'cylinder',
            'radius': radius,
            'height': height
        }
    
    return None

def generate_cube_vertices(size):
    """生成立方体顶点"""
    s = size / 2
    return [
        [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
        [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s]
    ]

def generate_cube_faces():
    """生成立方体面"""
    return [
        [0, 1, 2, 3],  # 底面
        [4, 7, 6, 5],  # 顶面
        [0, 4, 5, 1],  # 前面
        [2, 6, 7, 3],  # 后面
        [0, 3, 7, 4],  # 左面
        [1, 5, 6, 2]   # 右面
    ]

def generate_sphere_vertices(radius, segments):
    """生成球体顶点"""
    vertices = []
    for i in range(segments + 1):
        phi = np.pi * i / segments
        for j in range(segments):
            theta = 2 * np.pi * j / segments
            x = radius * np.sin(phi) * np.cos(theta)
            y = radius * np.sin(phi) * np.sin(theta)
            z = radius * np.cos(phi)
            vertices.append([x, y, z])
    return vertices

def generate_sphere_faces(segments):
    """生成球体面"""
    faces = []
    for i in range(segments):
        for j in range(segments):
            v1 = i * segments + j
            v2 = i * segments + (j + 1) % segments
            v3 = (i + 1) * segments + (j + 1) % segments
            v4 = (i + 1) * segments + j
            faces.append([v1, v2, v3, v4])
    return faces

def generate_cylinder_vertices(radius, height, segments):
    """生成圆柱体顶点"""
    vertices = []
    h = height / 2
    
    # 底面顶点
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        vertices.append([x, y, -h])
    
    # 顶面顶点
    for i in range(segments):
        angle = 2 * np.pi * i / segments
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        vertices.append([x, y, h])
    
    return vertices

def generate_cylinder_faces(segments):
    """生成圆柱体面"""
    faces = []
    
    # 侧面
    for i in range(segments):
        v1 = i
        v2 = (i + 1) % segments
        v3 = segments + (i + 1) % segments
        v4 = segments + i
        faces.append([v1, v2, v3, v4])
    
    # 底面和顶面（三角形面）
    for i in range(segments - 2):
        faces.append([0, i + 1, i + 2])
        faces.append([segments, segments + i + 2, segments + i + 1])
    
    return faces

def perform_simulation(simulation_type, params):
    """执行仿真"""
    if simulation_type == 'gravity':
        return simulate_gravity(params)
    elif simulation_type == 'collision':
        return simulate_collision(params)
    else:
        return {'error': '未知的仿真类型'}

def simulate_gravity(params):
    """重力仿真"""
    time_steps = params.get('time_steps', 100)
    initial_velocity = params.get('initial_velocity', [0, 0, 0])
    initial_position = params.get('initial_position', [0, 10, 0])
    
    positions = []
    velocities = []
    g = 9.81
    
    pos = list(initial_position)
    vel = list(initial_velocity)
    
    for t in range(time_steps):
        positions.append(pos.copy())
        velocities.append(vel.copy())
        
        # 更新速度和位置
        vel[1] -= g * 0.1  # 重力加速度
        pos[0] += vel[0] * 0.1
        pos[1] += vel[1] * 0.1
        pos[2] += vel[2] * 0.1
        
        # 地面碰撞
        if pos[1] < 0:
            pos[1] = 0
            vel[1] = -vel[1] * 0.8  # 弹性碰撞
    
    return {
        'type': 'gravity',
        'positions': positions,
        'velocities': velocities,
        'time_steps': time_steps
    }

def simulate_collision(params):
    """碰撞仿真"""
    time_steps = params.get('time_steps', 200)
    num_objects = params.get('num_objects', 3)
    object_size = params.get('object_size', 0.5)
    
    # 创建多个物体的初始状态
    objects = []
    for i in range(num_objects):
        obj = {
            'id': i,
            'position': [
                (i - num_objects/2) * 2,  # 减小水平间距
                8 + i * 1,                # 减小高度差
                0
            ],
            'velocity': [
                (i - num_objects/2) * 1.5,  # 减小初始水平速度
                -1,                         # 减小初始向下速度
                0
            ],
            'radius': object_size,
            'mass': 1.0
        }
        objects.append(obj)
    
    # 仿真数据
    simulation_data = {
        'time_steps': time_steps,
        'objects': [],
        'collisions': []
    }
    
    # 时间步长
    dt = 0.05
    g = 9.81  # 重力加速度
    
    # 运行仿真
    for step in range(time_steps):
        # 记录当前状态
        step_data = {
            'step': step,
            'objects': []
        }
        
        # 更新每个物体的位置和速度
        for obj in objects:
            # 应用重力
            obj['velocity'][1] -= g * dt
            
            # 更新位置
            obj['position'][0] += obj['velocity'][0] * dt
            obj['position'][1] += obj['velocity'][1] * dt
            obj['position'][2] += obj['velocity'][2] * dt
            
            # 记录物体状态
            step_data['objects'].append({
                'id': obj['id'],
                'position': obj['position'].copy(),
                'velocity': obj['velocity'].copy()
            })
            
            # 地面碰撞检测
            if obj['position'][1] < obj['radius']:
                obj['position'][1] = obj['radius']
                obj['velocity'][1] = -obj['velocity'][1] * 0.8  # 弹性碰撞
        
        # 物体间碰撞检测
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj1 = objects[i]
                obj2 = objects[j]
                
                # 计算距离
                dx = obj2['position'][0] - obj1['position'][0]
                dy = obj2['position'][1] - obj1['position'][1]
                dz = obj2['position'][2] - obj1['position'][2]
                distance = (dx**2 + dy**2 + dz**2)**0.5
                
                # 碰撞检测
                min_distance = obj1['radius'] + obj2['radius']
                if distance < min_distance and distance > 0:
                    # 记录碰撞
                    simulation_data['collisions'].append({
                        'step': step,
                        'object1': obj1['id'],
                        'object2': obj2['id'],
                        'position': [
                            (obj1['position'][0] + obj2['position'][0]) / 2,
                            (obj1['position'][1] + obj2['position'][1]) / 2,
                            (obj1['position'][2] + obj2['position'][2]) / 2
                        ]
                    })
                    
                    # 简单的弹性碰撞响应
                    # 计算碰撞法向量
                    nx = dx / distance
                    ny = dy / distance
                    nz = dz / distance
                    
                    # 计算相对速度
                    dvx = obj2['velocity'][0] - obj1['velocity'][0]
                    dvy = obj2['velocity'][1] - obj1['velocity'][1]
                    dvz = obj2['velocity'][2] - obj1['velocity'][2]
                    
                    # 计算相对速度在法向量上的投影
                    v_rel = dvx * nx + dvy * ny + dvz * nz
                    
                    # 如果物体正在分离，跳过碰撞响应
                    if v_rel > 0:
                        continue
                    
                    # 计算冲量
                    restitution = 0.8  # 弹性系数
                    j = -(1 + restitution) * v_rel / (1/obj1['mass'] + 1/obj2['mass'])
                    
                    # 更新速度
                    obj1['velocity'][0] -= j * nx / obj1['mass']
                    obj1['velocity'][1] -= j * ny / obj1['mass']
                    obj1['velocity'][2] -= j * nz / obj1['mass']
                    
                    obj2['velocity'][0] += j * nx / obj2['mass']
                    obj2['velocity'][1] += j * ny / obj2['mass']
                    obj2['velocity'][2] += j * nz / obj2['mass']
                    
                    # 分离重叠的物体
                    overlap = min_distance - distance
                    obj1['position'][0] -= overlap * nx * 0.5
                    obj1['position'][1] -= overlap * ny * 0.5
                    obj1['position'][2] -= overlap * nz * 0.5
                    
                    obj2['position'][0] += overlap * nx * 0.5
                    obj2['position'][1] += overlap * ny * 0.5
                    obj2['position'][2] += overlap * nz * 0.5
        
        simulation_data['objects'].append(step_data)
    
    return {
        'type': 'collision',
        'simulation_data': simulation_data,
        'num_objects': num_objects,
        'collision_count': len(simulation_data['collisions']),
        'message': f'碰撞仿真完成，检测到 {len(simulation_data["collisions"])} 次碰撞'
    }

def call_ollama_model(message):
    """非流式调用Ollama本地大模型（备用）"""
    if not ollama_client:
        raise Exception("Ollama客户端未初始化")
    
    # 构建系统提示词
    system_prompt = """你是一个专业的仿真平台AI助手。你的主要功能包括：
1. 帮助用户创建3D几何体（立方体、球体、圆柱体等）
2. 进行物理仿真（重力、碰撞、流体等）
3. 分析模型属性和仿真结果
4. 提供技术支持和指导

请用中文回答，回答要简洁专业。如果用户要求创建模型，请确认并说明你将帮助他们创建相应的3D模型。"""

    try:
        # 调用Ollama模型
        response = ollama_client.chat(
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
            }
        )
        
        return response['message']['content']
    
    except Exception as e:
        logger.error(f"Ollama API调用失败: {e}")
        raise e

@socketio.on('chat_message')
def handle_chat_message(data):
    """处理聊天消息的WebSocket事件"""
    user_message = data.get('message', '')
    session_id = data.get('session_id', f'session_{int(time.time())}')
    
    try:
        # 发送开始流式响应的信号
        socketio.emit('chat_start', {'session_id': session_id}, room=request.sid)
        
        # 在后台线程中处理流式响应
        def stream_response(sid):
            try:
                response = call_ollama_model_stream(user_message, session_id, sid)
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

if __name__ == '__main__':
    print("启动仿真平台服务器...")
    print("访问 http://localhost:6006 查看界面")
    socketio.run(app, debug=True, host='0.0.0.0', port=6006) 