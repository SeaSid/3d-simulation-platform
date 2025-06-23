# 3D仿真平台

一个基于 Flask 和 FastMCP 的 3D 建模与物理仿真平台，支持 AI 对话驱动的 3D 建模和仿真操作。

---

## 项目亮点
- **AI 智能对话驱动**：通过自然语言即可创建、操作 3D 模型和运行物理仿真。
- **双服务架构**：Flask 提供 Web 界面和 API，FastMCP 提供高效的仿真与建模工具。
- **实时 3D 渲染**：基于 Three.js，支持多种模型与交互。
- **自定义物理引擎**：支持重力、碰撞、多物体交互等仿真。
- **易扩展**：支持自定义 MCP 工具和 AI 命令解析。

## 适用场景
- 教育与科研中的 3D 建模与仿真教学
- AI 驱动的智能 CAD/CAE 应用原型
- 物理仿真算法快速验证

## 技术栈
- **后端**：Flask、FastMCP、Python 3.11
- **前端**：Three.js、Socket.IO、HTML5/CSS3
- **AI**：Ollama（本地大模型）
- **物理引擎**：自定义算法

## 目录结构
```
web/
├── app.py                 # Flask 主应用
├── fastmcp_server.py      # FastMCP 服务器
├── simulation_service.py  # 物理仿真服务
├── start_services.py      # 一键启动脚本
├── requirements.txt       # 依赖列表
├── static/                # 静态资源（js/css/3D编辑器）
├── templates/             # HTML 模板
```

## 安装与运行

1. 安装依赖
    ```bash
    conda activate simulation-env
    pip install -r requirements.txt
    ```
2. 启动服务
    ```bash
    # 推荐一键启动
    python start_services.py
    # 或分别启动
    python fastmcp_server.py
    python app.py
    ```
3. 访问
    - Web 界面: http://localhost:6006
    - FastMCP 服务: http://localhost:8000

## 功能示例

- **AI 对话建模**
    - 用户："创建一个尺寸为2的立方体"
    - AI："成功创建立方体形状"
- **物理仿真**
    - 用户："运行重力仿真"
    - AI："成功运行 gravity 仿真"
- **场景管理**
    - 用户："清空场景"
    - AI："场景已清空"

## 常见问题 FAQ

**Q: 启动时报端口占用？**  
A: 检查 6006/8000 端口是否被其他进程占用，或修改端口配置。

**Q: 浏览器无法显示 3D 场景？**  
A: 请使用支持 WebGL 的现代浏览器（如 Chrome、Edge、Firefox）。

**Q: AI 无法识别命令？**  
A: 请使用简明中文描述，如"创建立方体"、"运行重力仿真"。

## 贡献指南
1. Fork 本仓库并新建分支
2. 提交代码前请确保通过基本测试
3. 提交 Pull Request，描述变更内容和用途
4. 欢迎 Issue 反馈 bug 或建议

## 许可证
MIT License 