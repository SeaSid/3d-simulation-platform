#!/usr/bin/env python3
"""
启动脚本 - 同时启动FastMCP服务器和Flask应用
"""

import subprocess
import time
import signal
import sys
import os
from threading import Thread

class ServiceManager:
    def __init__(self):
        self.processes = []
        self.running = True
    
    def activate_conda_env(self):
        """激活conda环境"""
        print("激活conda环境...")
        try:
            # 激活conda环境
            activate_cmd = "bash -c 'source /root/miniconda3/bin/activate simulation-env'"
            result = subprocess.run(activate_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"激活conda环境失败: {result.stderr}")
                return False
            print("conda环境激活成功")
            return True
        except Exception as e:
            print(f"激活conda环境时出错: {e}")
            return False
    
    def install_dependencies(self):
        """安装缺失的依赖"""
        print("检查并安装依赖...")
        try:
            # 安装flask-socketio
            install_cmd = "bash -c 'source /root/miniconda3/bin/activate simulation-env && pip install flask-socketio'"
            result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"安装依赖失败: {result.stderr}")
                return False
            print("依赖安装完成")
            return True
        except Exception as e:
            print(f"安装依赖时出错: {e}")
            return False
    
    def start_fastmcp_server(self):
        """启动FastMCP服务器"""
        print("启动FastMCP服务器...")
        try:
            # 使用conda环境启动FastMCP服务器
            cmd = "bash -c 'source /root/miniconda3/bin/activate simulation-env && python fastmcp_server.py'"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(("FastMCP服务器", process))
            print(f"FastMCP服务器已启动 (PID: {process.pid})")
            
            # 等待一下检查是否启动成功
            time.sleep(5)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"FastMCP服务器启动失败:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
            return True
        except Exception as e:
            print(f"启动FastMCP服务器时出错: {e}")
            return False
    
    def start_flask_app(self):
        """启动Flask应用"""
        print("启动Flask应用...")
        try:
            # 使用conda环境启动Flask应用
            cmd = "bash -c 'source /root/miniconda3/bin/activate simulation-env && python app.py'"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(("Flask应用", process))
            print(f"Flask应用已启动 (PID: {process.pid})")
            
            # 等待一下检查是否启动成功
            time.sleep(5)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"Flask应用启动失败:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
            return True
        except Exception as e:
            print(f"启动Flask应用时出错: {e}")
            return False
    
    def start_services(self):
        """启动所有服务"""
        try:
            # 激活conda环境
            if not self.activate_conda_env():
                print("激活conda环境失败，停止启动流程")
                return False
            
            # 安装依赖
            if not self.install_dependencies():
                print("安装依赖失败，停止启动流程")
                return False
            
            # 启动FastMCP服务器
            if not self.start_fastmcp_server():
                print("FastMCP服务器启动失败，停止启动流程")
                return False
            
            time.sleep(3)  # 等待FastMCP服务器完全启动
            
            # 启动Flask应用
            if not self.start_flask_app():
                print("Flask应用启动失败，停止启动流程")
                return False
            
            print("\n" + "="*50)
            print("所有服务已启动:")
            print("- FastMCP服务器: http://localhost:8000")
            print("- Flask应用: http://localhost:6006")
            print("="*50)
            print("按 Ctrl+C 停止所有服务")
            
            # 等待进程
            while self.running:
                time.sleep(1)
                # 检查进程是否还在运行
                for name, process in self.processes:
                    if process.poll() is not None:
                        stdout, stderr = process.communicate()
                        print(f"{name}已停止 (退出码: {process.returncode})")
                        if stderr:
                            print(f"{name}错误输出: {stderr}")
                        self.running = False
                        break
                        
        except KeyboardInterrupt:
            print("\n正在停止所有服务...")
            self.stop_services()
    
    def stop_services(self):
        """停止所有服务"""
        for name, process in self.processes:
            try:
                print(f"正在停止{name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"{name}已停止")
            except subprocess.TimeoutExpired:
                print(f"强制停止{name}...")
                process.kill()
            except Exception as e:
                print(f"停止{name}时出错: {e}")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n收到信号 {signum}，正在停止服务...")
        self.running = False
        self.stop_services()
        sys.exit(0)

def main():
    # 注册信号处理器
    signal.signal(signal.SIGINT, lambda s, f: None)  # 忽略Ctrl+C，让ServiceManager处理
    
    manager = ServiceManager()
    manager.signal_handler = lambda s, f: manager.signal_handler(s, f)
    
    try:
        manager.start_services()
    except Exception as e:
        print(f"启动服务时出错: {e}")
        manager.stop_services()
        sys.exit(1)

if __name__ == "__main__":
    main() 