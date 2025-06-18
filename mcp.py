import json
import logging
from typing import Dict, List, Optional
import ollama
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ShapeType(Enum):
    CUBE = "cube"
    SPHERE = "sphere"
    CYLINDER = "cylinder"

class ViewMode(Enum):
    WIREFRAME = "wireframe"
    SOLID = "solid"

@dataclass
class Vector3:
    x: float
    y: float
    z: float

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "z": self.z}

@dataclass
class Shape:
    type: ShapeType
    vertices: List[Vector3]
    faces: List[List[int]]
    parameters: Dict

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "vertices": [v.to_dict() for v in self.vertices],
            "faces": self.faces,
            "parameters": self.parameters
        }

class MCPService:
    def __init__(self):
        self.shapes: List[Shape] = []
        self.view_mode: ViewMode = ViewMode.SOLID
        self.ollama_client = None
        self.initialize_ollama()
        self.simulation_status = {
            "status": "idle",
            "current_simulation": None,
            "shapes_count": 0,
            "view_mode": self.view_mode.value
        }

    def initialize_ollama(self):
        """初始化Ollama客户端"""
        try:
            self.ollama_client = ollama.Client(host="http://localhost:11434")
            models = self.ollama_client.list()
            logger.info(f"Ollama连接成功，可用模型: {[model['name'] for model in models['models']]}")
        except Exception as e:
            logger.warning(f"Ollama连接失败: {e}")
            self.ollama_client = None

    def create_shape(self, shape_type: str, params: Dict) -> Dict:
        """创建3D形状"""
        try:
            shape_type_enum = ShapeType(shape_type)
            
            if shape_type_enum == ShapeType.CUBE:
                vertices, faces = self._create_cube(params.get("size", 1.0))
            elif shape_type_enum == ShapeType.SPHERE:
                vertices, faces = self._create_sphere(
                    params.get("radius", 1.0),
                    params.get("segments", 32)
                )
            elif shape_type_enum == ShapeType.CYLINDER:
                vertices, faces = self._create_cylinder(
                    params.get("radius", 1.0),
                    params.get("height", 2.0),
                    params.get("segments", 32)
                )
            else:
                return {"success": False, "error": f"不支持的形状类型: {shape_type}"}

            shape = Shape(
                type=shape_type_enum,
                vertices=vertices,
                faces=faces,
                parameters=params
            )
            self.shapes.append(shape)
            self.update_simulation_status("active")

            return {
                "success": True,
                "data": shape.to_dict(),
                "message": f"成功创建{shape_type}形状"
            }
        except Exception as e:
            logger.error(f"创建形状失败: {e}")
            return {"success": False, "error": str(e)}

    def _create_cube(self, size: float) -> tuple[List[Vector3], List[List[int]]]:
        """创建立方体"""
        half_size = size / 2
        vertices = [
            Vector3(-half_size, -half_size, -half_size),  # 0
            Vector3(half_size, -half_size, -half_size),   # 1
            Vector3(half_size, half_size, -half_size),    # 2
            Vector3(-half_size, half_size, -half_size),   # 3
            Vector3(-half_size, -half_size, half_size),   # 4
            Vector3(half_size, -half_size, half_size),    # 5
            Vector3(half_size, half_size, half_size),     # 6
            Vector3(-half_size, half_size, half_size)     # 7
        ]
        faces = [
            [0, 1, 2, 3],  # 底面
            [4, 5, 6, 7],  # 顶面
            [0, 4, 7, 3],  # 左面
            [1, 5, 6, 2],  # 右面
            [0, 1, 5, 4],  # 前面
            [3, 2, 6, 7]   # 后面
        ]
        return vertices, faces

    def _create_sphere(self, radius: float, segments: int) -> tuple[List[Vector3], List[List[int]]]:
        """创建球体"""
        vertices = []
        faces = []
        
        # 生成顶点
        for i in range(segments + 1):
            lat = np.pi * (-0.5 + float(i) / segments)
            for j in range(segments + 1):
                lon = 2 * np.pi * float(j) / segments
                x = radius * np.cos(lat) * np.cos(lon)
                y = radius * np.cos(lat) * np.sin(lon)
                z = radius * np.sin(lat)
                vertices.append(Vector3(x, y, z))
        
        # 生成面
        for i in range(segments):
            for j in range(segments):
                first = i * (segments + 1) + j
                second = first + segments + 1
                faces.append([first, second, first + 1])
                faces.append([second, second + 1, first + 1])
        
        return vertices, faces

    def _create_cylinder(self, radius: float, height: float, segments: int) -> tuple[List[Vector3], List[List[int]]]:
        """创建圆柱体"""
        vertices = []
        faces = []
        half_height = height / 2
        
        # 生成底面顶点
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append(Vector3(x, y, -half_height))
        
        # 生成顶面顶点
        for i in range(segments):
            angle = 2 * np.pi * i / segments
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            vertices.append(Vector3(x, y, half_height))
        
        # 生成侧面
        for i in range(segments):
            next_i = (i + 1) % segments
            faces.append([i, i + segments, next_i + segments])
            faces.append([i, next_i + segments, next_i])
        
        # 生成底面
        for i in range(1, segments - 1):
            faces.append([0, i, i + 1])
        
        # 生成顶面
        for i in range(1, segments - 1):
            faces.append([segments, segments + i, segments + i + 1])
        
        return vertices, faces

    def reset_view(self) -> Dict:
        """重置视图"""
        try:
            # 重置所有形状的位置和旋转
            for shape in self.shapes:
                # 这里可以添加重置形状位置和旋转的逻辑
                pass
            
            self.update_simulation_status("idle")
            return {
                "success": True,
                "message": "视图已重置",
                "action": "reset_view"
            }
        except Exception as e:
            logger.error(f"重置视图失败: {e}")
            return {"success": False, "error": str(e)}

    def set_view_mode(self, mode: str) -> Dict:
        """设置视图模式"""
        try:
            view_mode = ViewMode(mode)
            self.view_mode = view_mode
            self.update_simulation_status("active")
            
            return {
                "success": True,
                "message": f"已切换到{mode}模式",
                "action": "set_view_mode",
                "mode": mode
            }
        except Exception as e:
            logger.error(f"设置视图模式失败: {e}")
            return {"success": False, "error": str(e)}

    def run_simulation(self, simulation_type: str, params: Dict) -> Dict:
        """运行仿真"""
        try:
            self.update_simulation_status("running", simulation_type)
            
            if simulation_type == "gravity":
                result = self._simulate_gravity(params)
            elif simulation_type == "collision":
                result = self._simulate_collision(params)
            else:
                return {"success": False, "error": f"不支持的仿真类型: {simulation_type}"}
            
            self.update_simulation_status("active")
            return result
        except Exception as e:
            logger.error(f"运行仿真失败: {e}")
            self.update_simulation_status("error")
            return {"success": False, "error": str(e)}

    def _simulate_gravity(self, params: Dict) -> Dict:
        """重力仿真"""
        try:
            gravity = params.get("gravity", 9.81)
            time_step = params.get("time_step", 0.1)
            duration = params.get("duration", 1.0)
            
            # 模拟重力效果
            trajectories = []
            for shape in self.shapes:
                trajectory = []
                for t in np.arange(0, duration, time_step):
                    # 计算每个顶点在重力作用下的位置
                    new_vertices = []
                    for vertex in shape.vertices:
                        new_vertex = Vector3(
                            vertex.x,
                            vertex.y,
                            vertex.z - 0.5 * gravity * t * t
                        )
                        new_vertices.append(new_vertex)
                    trajectory.append([v.to_dict() for v in new_vertices])
                trajectories.append(trajectory)
            
            return {
                "success": True,
                "data": {
                    "type": "gravity",
                    "parameters": params,
                    "results": {
                        "trajectories": trajectories,
                        "final_positions": [v.to_dict() for v in self.shapes[-1].vertices],
                        "time": duration
                    }
                }
            }
        except Exception as e:
            logger.error(f"重力仿真失败: {e}")
            return {"success": False, "error": str(e)}

    def _simulate_collision(self, params: Dict) -> Dict:
        """碰撞仿真"""
        try:
            restitution = params.get("restitution", 0.8)
            friction = params.get("friction", 0.1)
            time_step = params.get("time_step", 0.1)
            duration = params.get("duration", 1.0)
            
            # 模拟碰撞效果
            collision_points = []
            for i in range(len(self.shapes)):
                for j in range(i + 1, len(self.shapes)):
                    # 检测形状之间的碰撞
                    collision = self._check_collision(self.shapes[i], self.shapes[j])
                    if collision:
                        collision_points.append({
                            "shape1": i,
                            "shape2": j,
                            "point": collision["point"].to_dict(),
                            "normal": collision["normal"].to_dict()
                        })
            
            return {
                "success": True,
                "data": {
                    "type": "collision",
                    "parameters": params,
                    "results": {
                        "collision_points": collision_points,
                        "impact_forces": [1.0] * len(collision_points),  # 简化的力计算
                        "time": duration
                    }
                }
            }
        except Exception as e:
            logger.error(f"碰撞仿真失败: {e}")
            return {"success": False, "error": str(e)}

    def _check_collision(self, shape1: Shape, shape2: Shape) -> Optional[Dict]:
        """检测两个形状之间的碰撞"""
        # 简化的碰撞检测
        # 在实际应用中，这里应该实现更复杂的碰撞检测算法
        for v1 in shape1.vertices:
            for v2 in shape2.vertices:
                distance = np.sqrt(
                    (v1.x - v2.x) ** 2 +
                    (v1.y - v2.y) ** 2 +
                    (v1.z - v2.z) ** 2
                )
                if distance < 0.1:  # 碰撞阈值
                    return {
                        "point": Vector3(
                            (v1.x + v2.x) / 2,
                            (v1.y + v2.y) / 2,
                            (v1.z + v2.z) / 2
                        ),
                        "normal": Vector3(
                            v1.x - v2.x,
                            v1.y - v2.y,
                            v1.z - v2.z
                        )
                    }
        return None

    def clear_scene(self) -> Dict:
        """清空场景"""
        try:
            self.shapes.clear()
            self.update_simulation_status("idle")
            return {
                "success": True,
                "message": "场景已清空",
                "action": "clear_scene"
            }
        except Exception as e:
            logger.error(f"清空场景失败: {e}")
            return {"success": False, "error": str(e)}

    def get_ai_response(self, message: str) -> Dict:
        """获取AI响应"""
        if not self.ollama_client:
            return {"success": False, "error": "Ollama未连接"}
        
        try:
            # 构建系统提示词
            system_prompt = """你是一个专业的3D仿真平台AI助手。你可以帮助用户：

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

使用说明：
1. 创建形状时，可以指定参数，例如：
   - "创建一个边长为2的立方体"
   - "创建一个半径为1.5的球体"
   - "创建一个半径为1，高度为3的圆柱体"

2. 视图控制：
   - "重置视图" 或 "恢复默认视图"
   - "切换到线框模式" 或 "显示线框"
   - "切换到实体模式" 或 "显示实体"

3. 仿真操作：
   - "运行重力仿真" 或 "开始重力模拟"
   - "运行碰撞仿真" 或 "开始碰撞模拟"

4. 场景操作：
   - "清空场景" 或 "清除所有物体"

请用中文回答，回答要简洁专业。如果用户要求执行某个操作，请确认并说明你将执行的操作。如果用户没有指定具体参数，将使用默认值。"""

            # 调用Ollama模型
            response = self.ollama_client.chat(
                model="modelscope.cn/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF:Q4_K_M",
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
            
            return {
                "success": True,
                "response": response['message']['content']
            }
        except Exception as e:
            logger.error(f"获取AI响应失败: {e}")
            return {"success": False, "error": str(e)}

    def process_ai_command(self, ai_response: str) -> Dict:
        """处理AI命令"""
        try:
            # 根据AI回复内容执行相应操作
            if "创建立方体" in ai_response:
                # 从AI回复中提取参数
                size = 1.0  # 默认值
                if "边长为" in ai_response:
                    try:
                        size = float(ai_response.split("边长为")[1].split()[0])
                    except:
                        pass
                return self.create_shape("cube", {"size": size})
                
            elif "创建球体" in ai_response:
                radius = 1.0  # 默认值
                if "半径为" in ai_response:
                    try:
                        radius = float(ai_response.split("半径为")[1].split()[0])
                    except:
                        pass
                return self.create_shape("sphere", {"radius": radius})
                
            elif "创建圆柱体" in ai_response:
                radius = 1.0  # 默认值
                height = 2.0  # 默认值
                if "半径为" in ai_response:
                    try:
                        radius = float(ai_response.split("半径为")[1].split()[0])
                    except:
                        pass
                if "高度为" in ai_response:
                    try:
                        height = float(ai_response.split("高度为")[1].split()[0])
                    except:
                        pass
                return self.create_shape("cylinder", {"radius": radius, "height": height})
                
            elif "重置视图" in ai_response or "恢复默认视图" in ai_response:
                return self.reset_view()
                
            elif "线框模式" in ai_response or "显示线框" in ai_response:
                return self.set_view_mode("wireframe")
                
            elif "实体模式" in ai_response or "显示实体" in ai_response:
                return self.set_view_mode("solid")
                
            elif "重力仿真" in ai_response or "重力模拟" in ai_response:
                return self.run_simulation("gravity")
                
            elif "碰撞仿真" in ai_response or "碰撞模拟" in ai_response:
                return self.run_simulation("collision")
                
            elif "清空场景" in ai_response or "清除所有物体" in ai_response:
                return self.clear_scene()
            
            # 如果没有匹配到任何命令，返回AI的原始回复
            return {
                "success": True,
                "response": ai_response,
                "is_command": False
            }
            
        except Exception as e:
            logger.error(f"处理AI命令失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "is_command": False
            }

    def get_simulation_status(self) -> Dict:
        """获取当前仿真状态"""
        try:
            self.simulation_status.update({
                "shapes_count": len(self.shapes),
                "view_mode": self.view_mode.value,
                "shapes": [shape.to_dict() for shape in self.shapes]
            })
            return {
                "success": True,
                "data": self.simulation_status
            }
        except Exception as e:
            logger.error(f"获取仿真状态失败: {e}")
            return {"success": False, "error": str(e)}

    def update_simulation_status(self, status: str, simulation_type: Optional[str] = None) -> None:
        """更新仿真状态"""
        self.simulation_status["status"] = status
        if simulation_type:
            self.simulation_status["current_simulation"] = simulation_type
        else:
            self.simulation_status["current_simulation"] = None

# 创建全局MCP服务实例
mcp_service = MCPService() 