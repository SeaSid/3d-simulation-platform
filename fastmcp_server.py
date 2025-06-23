#!/usr/bin/env python3
"""
FastMCP服务器 - 提供3D建模和仿真相关的MCP工具
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP
import numpy as np
from simulation_service import MCPService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastMCP应用
app = FastMCP("3D-Simulation-Platform")

# 初始化MCP服务
mcp_service = MCPService()

# 定义MCP工具
@app.tool()
async def create_shape(shape_type: str, size: Optional[float] = 1.0, radius: Optional[float] = 1.0, height: Optional[float] = 2.0, segments: Optional[int] = 32) -> Dict[str, Any]:
    """
    创建3D形状（立方体、球体、圆柱体）
    
    根据用户需求创建相应的3D几何体。
    - cube: 创建立方体，需要指定size参数
    - sphere: 创建球体，需要指定radius参数
    - cylinder: 创建圆柱体，需要指定radius和height参数
    """
    try:
        # 根据形状类型构建参数
        if shape_type == "cube":
            params = {"size": size}
        elif shape_type == "sphere":
            params = {"radius": radius}
        elif shape_type == "cylinder":
            params = {"radius": radius, "height": height, "segments": segments}
        else:
            params = {}
        
        result = mcp_service.create_shape(shape_type, params)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"成功创建{shape_type}形状",
                "data": result["data"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    except Exception as e:
        logger.error(f"创建形状失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.tool()
async def run_simulation(simulation_type: str, time_steps: Optional[int] = 100, num_objects: Optional[int] = 3, object_size: Optional[float] = 0.5) -> Dict[str, Any]:
    """
    运行物理仿真（重力仿真、碰撞仿真）
    
    执行物理仿真计算，包括：
    - gravity: 重力仿真，模拟物体在重力作用下的运动
    - collision: 碰撞仿真，模拟多个物体之间的碰撞
    """
    try:
        params = {
            "time_steps": time_steps,
            "num_objects": num_objects,
            "object_size": object_size
        }
        
        result = mcp_service.run_simulation(simulation_type, params)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"成功运行{simulation_type}仿真",
                "data": result.get("data", {})
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
    except Exception as e:
        logger.error(f"运行仿真失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.tool()
async def reset_view() -> Dict[str, Any]:
    """
    重置3D视图到默认状态
    """
    try:
        result = mcp_service.reset_view()
        return {
            "success": result["success"],
            "message": "视图已重置"
        }
    except Exception as e:
        logger.error(f"重置视图失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.tool()
async def clear_scene() -> Dict[str, Any]:
    """
    清空3D场景中的所有对象
    """
    try:
        result = mcp_service.clear_scene()
        return {
            "success": result["success"],
            "message": "场景已清空"
        }
    except Exception as e:
        logger.error(f"清空场景失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.tool()
async def get_status() -> Dict[str, Any]:
    """
    获取仿真平台当前状态
    """
    try:
        status = mcp_service.get_simulation_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"获取状态失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.tool()
async def process_ai_command(command: str) -> Dict[str, Any]:
    """
    处理AI命令，自动解析用户输入并依次执行多条操作
    支持的命令类型：
    - 创建形状: "创建立方体", "创建球体", "创建圆柱体"
    - 运行仿真: "运行重力仿真", "运行碰撞仿真"
    - 场景操作: "重置视图", "清空场景"
    """
    import re
    try:
        # 用"，""然后""再"分割多步命令
        # 支持中文逗号、顿号、分号、换行、然后、再
        split_pattern = r'[，,、；;\n]|然后|再|接着|并且'
        sub_commands = [s.strip() for s in re.split(split_pattern, command) if s.strip()]
        results = []
        for sub_cmd in sub_commands:
            cmd_lower = sub_cmd.lower()
            # 解析创建形状命令
            if "立方体" in cmd_lower or "cube" in cmd_lower:
                size = 1.0
                if "尺寸" in sub_cmd or "大小" in sub_cmd:
                    size_match = re.search(r'(\d+(?:\.\d+)?)', sub_cmd)
                    if size_match:
                        size = float(size_match.group(1))
                res = await create_shape(shape_type="cube", size=size)
                results.append({"command": sub_cmd, **res})
            elif "球体" in cmd_lower or "sphere" in cmd_lower:
                radius = 1.0
                radius_match = re.search(r'(\d+(?:\.\d+)?)', sub_cmd)
                if radius_match:
                    radius = float(radius_match.group(1))
                res = await create_shape(shape_type="sphere", radius=radius)
                results.append({"command": sub_cmd, **res})
            elif "圆柱" in cmd_lower or "cylinder" in cmd_lower:
                radius = 1.0
                height = 2.0
                radius_match = re.search(r'半径[：:]\s*(\d+(?:\.\d+)?)', sub_cmd)
                height_match = re.search(r'高度[：:]\s*(\d+(?:\.\d+)?)', sub_cmd)
                if radius_match:
                    radius = float(radius_match.group(1))
                if height_match:
                    height = float(height_match.group(1))
                res = await create_shape(shape_type="cylinder", radius=radius, height=height)
                results.append({"command": sub_cmd, **res})
            elif "重力仿真" in cmd_lower or "gravity" in cmd_lower:
                res = await run_simulation(simulation_type="gravity")
                results.append({"command": sub_cmd, **res})
            elif "碰撞仿真" in cmd_lower or "collision" in cmd_lower:
                res = await run_simulation(simulation_type="collision")
                results.append({"command": sub_cmd, **res})
            elif "重置" in cmd_lower or "reset" in cmd_lower:
                res = await reset_view()
                results.append({"command": sub_cmd, **res})
            elif "清空" in cmd_lower or "clear" in cmd_lower:
                res = await clear_scene()
                results.append({"command": sub_cmd, **res})
            else:
                results.append({
                    "command": sub_cmd,
                    "success": False,
                    "error": f"无法识别的命令: {sub_cmd}",
                    "available_commands": [
                        "创建立方体", "创建球体", "创建圆柱体",
                        "运行重力仿真", "运行碰撞仿真",
                        "重置视图", "清空场景"
                    ]
                })
        return {"success": all(r.get("success", False) for r in results), "results": results}
    except Exception as e:
        logger.error(f"处理AI命令失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    import asyncio
    # 打印工具列表
    tools = asyncio.run(app.get_tools())
    print(f"可用工具数量: {len(tools)}")
    for tool in tools:
        if hasattr(tool, 'name') and hasattr(tool, 'description'):
            print(f"  - {tool.name}: {tool.description}")
        else:
            print(f"  - {tool}")
    # 启动FastMCP服务
    uvicorn.run(app.http_app(), host="0.0.0.0", port=8000) 