// 全局变量
let scene, camera, renderer, controls;
let socket;
let objects = [];
let selectedObject = null;
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();
let shapes = [];
let simulationObjects = [];
let isSimulating = false;
let simulationAnimationId = null;
let initialized = false;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM加载完成');
    
    try {
        // 检查Three.js是否加载成功
        if (typeof THREE === 'undefined') {
            console.error('Three.js库未加载');
            alert('Three.js库加载失败，请刷新页面重试');
            return;
        }
        console.log('Three.js库加载成功，版本:', THREE.REVISION);
        
        if (!initialized) {
            initThreeJS();
            initSocket();
            initEventListeners();
            initGUI();
            initModelStatus();
            initMCP();
            initialized = true;
        }
    } catch (error) {
        console.error('初始化过程中发生错误:', error);
        alert('页面初始化失败: ' + error.message);
    }
});

// 初始化Three.js
function initThreeJS() {
    console.log('开始初始化Three.js...');
    
    // 检查WebGL支持
    if (!window.WebGLRenderingContext) {
        console.error('浏览器不支持WebGL');
        alert('您的浏览器不支持WebGL，请使用支持WebGL的浏览器');
        return;
    }
    
    // 创建场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);
    console.log('场景创建完成');

    // 创建相机
    const container = document.getElementById('threejs-container');
    console.log('容器元素:', container);
    
    if (!container) {
        console.error('找不到threejs-container元素');
        return;
    }
    
    // 确保容器有正确的尺寸
    if (container.clientWidth === 0 || container.clientHeight === 0) {
        console.log('容器尺寸为0，等待下一帧...');
        setTimeout(initThreeJS, 100);
        return;
    }
    
    console.log('容器尺寸:', container.clientWidth, 'x', container.clientHeight);
    
    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
    camera.position.set(5, 5, 5);
    console.log('相机创建完成');

    // 创建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    console.log('渲染器创建完成');

    // 添加轨道控制器
    if (typeof THREE.SimpleOrbitControls !== 'undefined') {
        controls = new THREE.SimpleOrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        console.log('简单轨道控制器创建完成');
    } else {
        console.warn('SimpleOrbitControls未加载，将使用基本相机控制');
        // 如果没有OrbitControls，使用基本的鼠标控制
        controls = null;
    }

    // 添加光源
    addLights();
    console.log('光源添加完成');

    // 添加网格
    addGrid();
    console.log('网格添加完成');

    // 添加坐标轴
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);
    console.log('坐标轴添加完成');

    // 添加鼠标点击事件监听器（在renderer创建后）
    renderer.domElement.addEventListener('click', onMouseClick);
    console.log('鼠标事件监听器添加完成');

    // 开始渲染循环
    animate();
    console.log('渲染循环开始');

    // 窗口大小调整
    window.addEventListener('resize', onWindowResize);
    console.log('Three.js初始化完成');
}

// 添加光源
function addLights() {
    // 环境光
    const ambientLight = new THREE.AmbientLight(0x404040, 0.4);
    scene.add(ambientLight);

    // 方向光
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);

    // 点光源
    const pointLight = new THREE.PointLight(0xffffff, 0.5);
    pointLight.position.set(-10, 10, -10);
    scene.add(pointLight);
}

// 添加网格
function addGrid() {
    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    scene.add(gridHelper);
}

// 初始化WebSocket连接
function initSocket() {
    console.log('开始初始化WebSocket连接...');
    
    // 检查Socket.IO是否加载成功
    if (typeof io === 'undefined') {
        console.error('Socket.IO库未加载');
        alert('Socket.IO库加载失败，请刷新页面重试');
        return;
    }
    
    socket = io();
    console.log('Socket.IO客户端创建完成');
    
    socket.on('connect', function() {
        console.log('Connected to server');
        addChatMessage('系统', '已连接到仿真服务器', 'bot');
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        addChatMessage('系统', '与服务器断开连接', 'bot');
    });

    socket.on('shape_created', function(data) {
        console.log('=== SHAPE_CREATED EVENT RECEIVED ===');
        console.log('Raw data:', data);
        console.log('Data type:', typeof data);
        console.log('Data structure:', JSON.stringify(data, null, 2));
        
        // 检查数据格式
        if (data && typeof data === 'object') {
            console.log('Data is valid object');
            if (data.type) {
                console.log('Shape type found:', data.type);
            } else {
                console.log('No shape type found in data');
            }
        } else {
            console.error('Invalid data format:', data);
            return;
        }
        
        createShapeFromData(data);
    });

    socket.on('simulation_result', function(data) {
        console.log('Simulation result:', data);
        displaySimulationResult(data);
    });

    socket.on('simulation_started', function(data) {
        console.log('=== SIMULATION_STARTED EVENT RECEIVED ===');
        console.log('Raw data:', data);
        console.log('Data type:', typeof data);
        console.log('Data structure:', JSON.stringify(data, null, 2));
        
        addChatMessage('系统', data.message || '仿真已开始', 'bot');
        
        // 如果有仿真数据，显示仿真结果
        if (data.data) {
            console.log('显示仿真结果:', data.data);
            console.log('仿真数据类型:', typeof data.data);
            console.log('仿真数据键:', Object.keys(data.data));
            displaySimulationResult(data.data);
        } else {
            console.log('没有仿真数据');
        }
    });

    // 流式对话事件监听器
    socket.on('chat_start', function(data) {
        console.log('Chat started:', data);
        // 可以在这里添加开始聊天的UI指示
    });

    socket.on('chat_message', function(data) {
        console.log('Chat message received:', data);
        const messageId = `ai_${data.session_id}`;
        
        if (data.is_complete) {
            // 完整消息，隐藏打字指示器
            hideTypingIndicator(messageId);
            
            // 处理消息内容，格式化工具调用标记
            let formattedContent = formatMessageContent(data.content);
            updateChatMessage(messageId, formattedContent);
            
            // 显示模型信息
            if (data.model && data.model !== 'fallback') {
                addChatMessage('系统', `使用模型: ${data.model}`, 'bot');
            }
        } else {
            // 流式内容，追加到现有消息
            hideTypingIndicator(messageId);
            let formattedContent = formatMessageContent(data.content);
            updateChatMessage(messageId, formattedContent, true);
        }
    });

    socket.on('chat_complete', function(data) {
        console.log('Chat completed:', data);
        const messageId = `ai_${data.session_id}`;
        hideTypingIndicator(messageId);
    });

    socket.on('chat_error', function(data) {
        console.error('Chat error:', data);
        const messageId = `ai_${data.session_id}`;
        hideTypingIndicator(messageId);
        addChatMessage('系统', `错误: ${data.error}`, 'bot');
    });

    // MCP相关事件监听器
    socket.on('chat_response', function(data) {
        console.log('Chat response:', data);
        const messageId = `ai_${data.session_id}`;
        updateChatMessage(messageId, data.response);
    });

    socket.on('simulation_response', function(data) {
        console.log('Simulation response:', data);
        // 处理仿真响应
        if (data.data && data.data.type) {
            displaySimulationResult(data.data);
        }
    });

    socket.on('simulation_error', function(data) {
        console.error('Simulation error:', data);
        addChatMessage('系统', `仿真错误: ${data.error}`, 'bot');
    });

    socket.on('error', function(data) {
        console.error('WebSocket error:', data);
        hideLoading(); // 隐藏加载状态
        addChatMessage('系统', `WebSocket错误: ${data.message || '未知错误'}`, 'bot');
    });

    // 工具调用事件监听器
    socket.on('tool_call_start', function(data) {
        console.log('工具调用开始:', data);
        addToolCallMessage(data.tool, data.params, null, 'start');
    });

    socket.on('tool_call_complete', function(data) {
        console.log('工具调用完成:', data);
        updateToolCallMessage(data.tool, data.params, data.success, data.result || data.error);
    });
}

// 初始化事件监听器
function initEventListeners() {
    console.log('开始初始化事件监听器...');
    
    // 聊天功能
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-message');

    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
        console.log('发送按钮事件监听器添加完成');
    } else {
        console.error('找不到发送按钮');
    }
    
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        console.log('聊天输入框事件监听器添加完成');
    } else {
        console.error('找不到聊天输入框');
    }

    // 快速操作按钮
    const actionButtons = document.querySelectorAll('.action-btn');
    console.log('找到快速操作按钮数量:', actionButtons.length);
    actionButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const shapeType = this.dataset.shape;
            createShape(shapeType);
        });
    });

    // 仿真控制按钮
    const gravitySimBtn = document.getElementById('gravity-sim');
    const collisionSimBtn = document.getElementById('collision-sim');
    const clearSceneBtn = document.getElementById('clear-scene');
    
    if (gravitySimBtn) {
        gravitySimBtn.addEventListener('click', function() {
            startSimulation('gravity');
        });
        console.log('重力仿真按钮事件监听器添加完成');
    }
    
    if (collisionSimBtn) {
        collisionSimBtn.addEventListener('click', function() {
            startSimulation('collision');
        });
        console.log('碰撞仿真按钮事件监听器添加完成');
    }
    
    if (clearSceneBtn) {
        clearSceneBtn.addEventListener('click', clearScene);
        console.log('清空场景按钮事件监听器添加完成');
    }

    // 视图控制按钮
    const resetViewBtn = document.getElementById('resetView');
    const wireframeBtn = document.getElementById('wireframe');
    const solidBtn = document.getElementById('solid');
    
    if (resetViewBtn) {
        resetViewBtn.addEventListener('click', resetView);
        console.log('重置视图按钮事件监听器添加完成');
    }
    
    if (wireframeBtn) {
        wireframeBtn.addEventListener('click', toggleWireframe);
        console.log('线框模式按钮事件监听器添加完成');
    }
    
    if (solidBtn) {
        solidBtn.addEventListener('click', toggleSolid);
        console.log('实体模式按钮事件监听器添加完成');
    }

    // 参数控制
    const sizeInput = document.getElementById('size-input');
    const radiusInput = document.getElementById('radius-input');
    const heightInput = document.getElementById('height-input');
    
    if (sizeInput) {
        sizeInput.addEventListener('input', function() {
            document.getElementById('size-value').textContent = this.value;
        });
        console.log('尺寸输入框事件监听器添加完成');
    }
    
    if (radiusInput) {
        radiusInput.addEventListener('input', function() {
            document.getElementById('radius-value').textContent = this.value;
        });
        console.log('半径输入框事件监听器添加完成');
    }
    
    if (heightInput) {
        heightInput.addEventListener('input', function() {
            document.getElementById('height-value').textContent = this.value;
        });
        console.log('高度输入框事件监听器添加完成');
    }
    
    console.log('事件监听器初始化完成');
}

// 初始化GUI
function initGUI() {
    // 这里可以添加更复杂的GUI控制
    console.log('GUI initialized');
}

// 初始化MCP
function initMCP() {
    console.log('MCP initialized');
}

// 发送消息
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (message) {
        addChatMessage('用户', message, 'user');
        input.value = '';
        
        // 生成会话ID
        const sessionId = `session_${Date.now()}`;
        
        // 创建AI消息容器（用于流式更新）
        const aiMessageId = `ai_${sessionId}`;
        addChatMessage('AI助手', '', 'bot', aiMessageId);
        
        // 显示打字指示器
        showTypingIndicator(aiMessageId);
        
        // 使用WebSocket发送消息（推荐方式）
        if (socket && socket.connected) {
            socket.emit('chat_message', {
                message: message,
                session_id: sessionId
            });
        } else {
            // 备用HTTP方式
            sendMessageHTTP(message, sessionId, aiMessageId);
        }
    }
}

// HTTP方式发送消息（备用）
function sendMessageHTTP(message, sessionId, aiMessageId) {
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            message: message,
            session_id: sessionId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'streaming') {
            // 流式响应已通过WebSocket处理
            console.log('开始流式响应');
        } else {
            hideTypingIndicator(aiMessageId);
            updateChatMessage(aiMessageId, data.error || '发送消息失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        hideTypingIndicator(aiMessageId);
        updateChatMessage(aiMessageId, '发送消息时出错');
    });
}

// 添加聊天消息（支持流式更新）
function addChatMessage(sender, content, type, messageId = null) {
    // 如果是系统消息，显示为提示框
    if (sender === '系统') {
        showToast(content, 'success');
        return null;
    }
    
    const chatMessages = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    let html = content;
    // 保留思考过程和工具调用的收缩逻辑
    html = html.replace(/<think>([\s\S]*?)<\/think>/g, '<details><summary>思考过程</summary><div class="think-block">$1</div></details>');
    html = html.replace(/\[TOOL_CALL:([^:]+):([\s\S]+?)\]/g, function(match, tool, params) {
        return `<details><summary>工具调用: ${tool}</summary><div class="tool-block">${params}</div></details>`;
    });
    if (type === 'user') {
        bubble.className = 'chat-bubble user';
        bubble.innerHTML = '<i class="fas fa-user"></i> ' + html;
    } else {
        bubble.className = 'chat-bubble ai';
        bubble.innerHTML = '<i class="fas fa-robot"></i> ' + html;
    }
    if (messageId) {
        bubble.id = messageId;
    }
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
}

// 显示提示框
function showToast(message, type = 'info') {
    // 创建提示框元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-message">${message}</span>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 2秒后开始淡出
    setTimeout(() => {
        toast.classList.add('fade-out');
    }, 2000);
    
    // 2.5秒后移除元素
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 2500);
}

// 更新聊天消息内容（用于流式更新）
function updateChatMessage(messageId, content, append = false) {
    const bubble = document.getElementById(messageId);
    if (bubble) {
        let icon = bubble.classList.contains('user') ? '<i class="fas fa-user"></i> ' : '<i class="fas fa-robot"></i> ';
        let html = content;
        html = html.replace(/<think>([\s\S]*?)<\/think>/g, '<details><summary>思考过程</summary><div class="think-block">$1</div></details>');
        html = html.replace(/\[TOOL_CALL:([^:]+):([\s\S]+?)\]/g, function(match, tool, params) {
            return `<details><summary>工具调用: ${tool}</summary><div class="tool-block">${params}</div></details>`;
        });
        if (append) {
            bubble.innerHTML += html;
        } else {
            bubble.innerHTML = icon + html;
        }
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 显示打字指示器
function showTypingIndicator(messageId) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            contentDiv.innerHTML = '<span class="typing-indicator">AI正在思考</span><span class="typing-dots">...</span>';
        }
    }
}

// 隐藏打字指示器
function hideTypingIndicator(messageId) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            const typingIndicator = contentDiv.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            const typingDots = contentDiv.querySelector('.typing-dots');
            if (typingDots) {
                typingDots.remove();
            }
        }
    }
}

// 创建形状
function createShape(shapeType) {
    console.log('Creating shape:', shapeType);
    
    // 检查WebSocket连接
    if (!socket) {
        console.error('Socket对象不存在');
        addChatMessage('系统', 'WebSocket未初始化，请刷新页面重试', 'bot');
        return;
    }
    
    if (!socket.connected) {
        console.error('WebSocket未连接，连接状态:', socket.connected);
        addChatMessage('系统', 'WebSocket连接失败，请刷新页面重试', 'bot');
        return;
    }
    
    console.log('WebSocket连接正常，发送创建形状请求');
    
    const params = getCurrentParameters(shapeType);
    console.log('Shape parameters:', params);
    
    socket.emit('create_shape', {
        type: shapeType,
        params: params
    });
    
    console.log('创建形状请求已发送');
}

// 获取当前参数
function getCurrentParameters(shapeType) {
    const params = {};
    
    if (shapeType === 'cube') {
        params.size = parseFloat(document.getElementById('size-input').value);
    } else if (shapeType === 'sphere' || shapeType === 'cylinder') {
        params.radius = parseFloat(document.getElementById('radius-input').value);
        if (shapeType === 'cylinder') {
            params.height = parseFloat(document.getElementById('height-input').value);
        }
    }
    
    return params;
}

// 从数据创建形状
function createShapeFromData(data) {
    console.log('=== CREATE_SHAPE_FROM_DATA CALLED ===');
    console.log('Input data:', data);
    console.log('Input data type:', typeof data);
    console.log('Input data structure:', JSON.stringify(data, null, 2));
    
    // 数据可能来自不同的来源，需要处理不同的格式
    let shapeData, shapeType;
    
    if (data.shape_data) {
        // 来自MCP工具的数据格式
        console.log('Using shape_data from MCP tool');
        shapeData = data.shape_data;
        shapeType = shapeData.type;
    } else if (data.type) {
        // 直接的数据格式
        console.log('Using direct data format');
        shapeData = data;
        shapeType = data.type;
    } else {
        console.error('无法识别的数据格式:', data);
        console.error('Data keys:', Object.keys(data || {}));
        return;
    }
    
    console.log('处理后的形状数据:', shapeData);
    console.log('形状类型:', shapeType);
    console.log('形状数据键:', Object.keys(shapeData));
    
    let geometry, material, mesh;
    
    if (shapeType === 'cube') {
        const size = shapeData.size || shapeData.parameters?.size || 1.0;
        geometry = new THREE.BoxGeometry(size, size, size);
        console.log('创建立方体，尺寸:', size);
    } else if (shapeType === 'sphere') {
        const radius = shapeData.radius || shapeData.parameters?.radius || 1.0;
        geometry = new THREE.SphereGeometry(radius, 32, 32);
        console.log('创建球体，半径:', radius);
    } else if (shapeType === 'cylinder') {
        const radius = shapeData.radius || shapeData.parameters?.radius || 1.0;
        const height = shapeData.height || shapeData.parameters?.height || 2.0;
        geometry = new THREE.CylinderGeometry(radius, radius, height, 32);
        console.log('创建圆柱体，半径:', radius, '高度:', height);
    } else {
        console.error('未知的形状类型:', shapeType);
        return;
    }
    
    material = new THREE.MeshPhongMaterial({ 
        color: getRandomColor(),
        transparent: true,
        opacity: 0.8
    });
    
    mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = { type: shapeType, id: shapeData.id || Date.now() };
    
    // 随机位置
    mesh.position.set(
        (Math.random() - 0.5) * 10,
        Math.random() * 5 + 1,
        (Math.random() - 0.5) * 10
    );
    
    scene.add(mesh);
    objects.push(mesh);
    
    console.log('=== 形状创建完成 ===');
    console.log('形状已添加到场景，位置:', mesh.position);
    console.log('当前场景中的对象数量:', scene.children.length);
    console.log('当前objects数组长度:', objects.length);
    console.log('新创建的mesh对象:', mesh);
    console.log('mesh的geometry:', mesh.geometry);
    console.log('mesh的material:', mesh.material);
    console.log('mesh的userData:', mesh.userData);
    
    // 验证形状是否真的在场景中
    const meshInScene = scene.children.includes(mesh);
    console.log('mesh是否在场景中:', meshInScene);
    
    // 验证形状是否真的在objects数组中
    const meshInObjects = objects.includes(mesh);
    console.log('mesh是否在objects数组中:', meshInObjects);
    
    addChatMessage('系统', `已创建${getShapeName(shapeType)}`, 'bot');
}

// 获取形状名称
function getShapeName(type) {
    const names = {
        'cube': '立方体',
        'sphere': '球体',
        'cylinder': '圆柱体'
    };
    return names[type] || type;
}

// 获取随机颜色
function getRandomColor() {
    const colors = [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0x96ceb4, 0xfeca57, 0xff9ff3];
    return colors[Math.floor(Math.random() * colors.length)];
}

// 开始仿真
function startSimulation(type) {
    console.log('Starting simulation:', type);
    
    // 检查WebSocket连接
    if (!socket || !socket.connected) {
        console.error('WebSocket not connected');
        addChatMessage('系统', 'WebSocket连接失败，请刷新页面重试', 'bot');
        return;
    }
    
    let params = {};
    
    if (type === 'gravity') {
        params = {
            time_steps: 100,
            initial_position: [0, 10, 0],
            initial_velocity: [0, 0, 0]
        };
    } else if (type === 'collision') {
        params = {
            time_steps: 200,
            num_objects: 5,
            object_size: 0.5
        };
    }
    
    console.log('Simulation parameters:', params);
    
    socket.emit('simulate', {
        type: type,
        params: params
    });
}

// 显示仿真结果
function displaySimulationResult(data) {
    console.log('=== DISPLAY_SIMULATION_RESULT CALLED ===');
    console.log('Input data:', data);
    console.log('Data type:', typeof data);
    console.log('Data structure:', JSON.stringify(data, null, 2));
    
    const resultsContent = document.getElementById('results-content');
    if (!resultsContent) {
        console.error('找不到results-content元素');
        return;
    }
    
    console.log('仿真类型:', data.type);
    
    if (data.type === 'gravity') {
        console.log('处理重力仿真数据');
        let html = '<h4>重力仿真结果</h4>';
        html += `<p>仿真步数: ${data.time_steps}</p>`;
        
        if (data.positions && data.positions.length > 0) {
            const finalPos = data.positions[data.positions.length - 1];
            html += `<p>最终位置: [${finalPos[0].toFixed(2)}, ${finalPos[1].toFixed(2)}, ${finalPos[2].toFixed(2)}]</p>`;
        }
        
        if (data.velocities && data.velocities.length > 0) {
            const finalVel = data.velocities[data.velocities.length - 1];
            html += `<p>最终速度: [${finalVel[0].toFixed(2)}, ${finalVel[1].toFixed(2)}, ${finalVel[2].toFixed(2)}]</p>`;
        }
        
        console.log('生成的HTML:', html);
        resultsContent.innerHTML = html;
        
        // 创建动画球体
        console.log('创建动画球体');
        createAnimatedSphere(data);
    } else if (data.type === 'collision') {
        console.log('处理碰撞仿真数据');
        let html = '<h4>碰撞仿真结果</h4>';
        html += `<p>仿真步数: ${data.simulation_data.time_steps}</p>`;
        html += `<p>物体数量: ${data.num_objects}</p>`;
        html += `<p>碰撞次数: ${data.collision_count}</p>`;
        html += `<p>${data.message}</p>`;
        
        resultsContent.innerHTML = html;
        
        // 创建碰撞动画物体
        createCollisionObjects(data);
    } else {
        console.log('未知的仿真类型或没有类型信息');
        resultsContent.innerHTML = `<p>${data.message || '仿真完成'}</p>`;
    }
}

// 创建动画球体
function createAnimatedSphere(data) {
    console.log('=== CREATE_ANIMATED_SPHERE CALLED ===');
    console.log('Input data:', data);
    console.log('Positions array length:', data.positions ? data.positions.length : 'undefined');
    
    if (!data.positions || data.positions.length === 0) {
        console.error('没有位置数据，无法创建动画球体');
        return;
    }
    
    const geometry = new THREE.SphereGeometry(0.5, 32, 32);
    const material = new THREE.MeshPhongMaterial({ 
        color: 0xff6b6b,
        transparent: true,
        opacity: 0.8
    });
    
    const sphere = new THREE.Mesh(geometry, material);
    sphere.castShadow = true;
    sphere.userData = { 
        type: 'animated',
        positions: data.positions,
        currentStep: 0
    };
    
    // 设置初始位置
    if (data.positions[0]) {
        sphere.position.set(data.positions[0][0], data.positions[0][1], data.positions[0][2]);
        console.log('设置初始位置:', data.positions[0]);
    }
    
    scene.add(sphere);
    objects.push(sphere);
    
    console.log('动画球体已创建并添加到场景');
    console.log('当前场景对象数量:', scene.children.length);
    console.log('当前objects数组长度:', objects.length);
}

// 创建碰撞动画物体
function createCollisionObjects(data) {
    const simData = data.simulation_data;
    const colors = [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0x96ceb4, 0xfeca57, 0xff9ff3];
    
    // 为每个物体创建动画对象
    for (let objId = 0; objId < data.num_objects; objId++) {
        const geometry = new THREE.SphereGeometry(0.5, 32, 32);
        const material = new THREE.MeshPhongMaterial({ 
            color: colors[objId % colors.length],
            transparent: true,
            opacity: 0.8
        });
        
        const sphere = new THREE.Mesh(geometry, material);
        sphere.castShadow = true;
        sphere.userData = { 
            type: 'collision_animated',
            objectId: objId,
            positions: [],
            currentStep: 0
        };
        
        // 提取该物体的所有位置数据
        simData.objects.forEach(step => {
            const objData = step.objects.find(obj => obj.id === objId);
            if (objData) {
                sphere.userData.positions.push(objData.position);
            }
        });
        
        scene.add(sphere);
        objects.push(sphere);
    }
    
    // 显示碰撞提示
    addChatMessage('系统', `开始播放碰撞仿真动画，共${data.num_objects}个物体`, 'bot');
}

// 清空场景
function clearScene() {
    objects.forEach(obj => {
        scene.remove(obj);
    });
    objects = [];
    selectedObject = null;
    addChatMessage('系统', '场景已清空', 'bot');
}

// 重置视图
function resetView() {
    camera.position.set(5, 5, 5);
    if (controls && controls.reset) {
        controls.reset();
    }
    showToast('视图已重置', 'info');
}

// 切换线框模式
function toggleWireframe() {
    objects.forEach(obj => {
        if (obj.material) {
            obj.material.wireframe = true;
        }
    });
}

// 切换实体模式
function toggleSolid() {
    objects.forEach(obj => {
        if (obj.material) {
            obj.material.wireframe = false;
        }
    });
}

// 鼠标点击事件
function onMouseClick(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(objects);
    
    if (intersects.length > 0) {
        selectedObject = intersects[0].object;
        updateObjectInfo();
    } else {
        selectedObject = null;
        updateObjectInfo();
    }
}

// 更新对象信息
function updateObjectInfo() {
    const selectedElement = document.getElementById('selected-object');
    const positionElement = document.getElementById('object-position');
    const rotationElement = document.getElementById('object-rotation');
    
    if (selectedObject) {
        selectedElement.textContent = selectedObject.userData.type || '未知';
        positionElement.textContent = `X: ${selectedObject.position.x.toFixed(2)}, Y: ${selectedObject.position.y.toFixed(2)}, Z: ${selectedObject.position.z.toFixed(2)}`;
        rotationElement.textContent = `X: ${(selectedObject.rotation.x * 180 / Math.PI).toFixed(1)}°, Y: ${(selectedObject.rotation.y * 180 / Math.PI).toFixed(1)}°, Z: ${(selectedObject.rotation.z * 180 / Math.PI).toFixed(1)}°`;
    } else {
        selectedElement.textContent = '无';
        positionElement.textContent = 'X: 0, Y: 0, Z: 0';
        rotationElement.textContent = 'X: 0°, Y: 0°, Z: 0°';
    }
}

// 窗口大小调整
function onWindowResize() {
    const container = document.getElementById('threejs-container');
    const aspect = container.clientWidth / container.clientHeight;
    
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
}

// 动画循环
function animate() {
    requestAnimationFrame(animate);
    
    // 仿真动画推进
    objects.forEach(obj => {
        // 重力仿真动画
        if (obj.userData.type === 'animated' && obj.userData.positions) {
            let step = obj.userData.currentStep;
            if (step < obj.userData.positions.length) {
                let pos = obj.userData.positions[step];
                obj.position.set(pos[0], pos[1], pos[2]);
                obj.userData.currentStep++;
            }
        }
        // 碰撞仿真动画
        if (obj.userData.type === 'collision_animated' && obj.userData.positions) {
            let step = obj.userData.currentStep;
            if (step < obj.userData.positions.length) {
                let pos = obj.userData.positions[step];
                obj.position.set(pos[0], pos[1], pos[2]);
                obj.userData.currentStep++;
            }
        }
    });

    if (controls) {
        controls.update();
    }
    
    if (renderer && scene && camera) {
        renderer.render(scene, camera);
        
        // 每100帧输出一次调试信息
        if (Math.random() < 0.01) { // 大约1%的概率输出
            console.log('=== 渲染循环调试信息 ===');
            console.log('场景对象数量:', scene.children.length);
            console.log('objects数组长度:', objects.length);
            console.log('相机位置:', camera.position);
            console.log('渲染器状态:', renderer ? '正常' : '异常');
        }
    } else {
        console.error('渲染器、场景或相机未初始化');
        console.error('renderer:', renderer);
        console.error('scene:', scene);
        console.error('camera:', camera);
    }
}

// 初始化模型状态
function initModelStatus() {
    checkModelStatus();
    
    // 模型选择器事件
    document.getElementById('model-selector').addEventListener('change', function() {
        const selectedModel = this.value;
        if (selectedModel) {
            setModel(selectedModel);
        }
    });
}

// 检查模型状态
function checkModelStatus() {
    console.log('开始检查模型状态...');
    const statusElement = document.getElementById('model-status');
    const selectorElement = document.getElementById('model-selector');
    
    if (!statusElement) {
        console.error('找不到model-status元素');
        return;
    }
    
    statusElement.textContent = '模型状态: 检查中...';
    console.log('发送API请求到 /api/models');
    
    fetch('/api/models')
        .then(response => {
            console.log('API响应状态:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('API响应数据:', data);
            if (data.success) {
                statusElement.textContent = `当前模型: ${data.current_model}`;
                
                // 填充模型选择器
                selectorElement.innerHTML = '<option value="">选择模型</option>';
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    if (model === data.current_model) {
                        option.selected = true;
                    }
                    selectorElement.appendChild(option);
                });
                
                selectorElement.style.display = 'block';
                console.log('模型状态更新完成');
            } else {
                statusElement.textContent = `模型状态: ${data.error}`;
                selectorElement.style.display = 'none';
                console.error('模型状态检查失败:', data.error);
            }
        })
        .catch(error => {
            console.error('检查模型状态失败:', error);
            statusElement.textContent = '模型状态: 连接失败';
            selectorElement.style.display = 'none';
        });
}

// 设置模型
function setModel(modelName) {
    fetch('/api/set-model', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model: modelName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('model-status').textContent = `当前模型: ${data.current_model}`;
            addChatMessage('系统', data.message, 'bot');
        } else {
            addChatMessage('系统', `模型切换失败: ${data.error}`, 'bot');
        }
    })
    .catch(error => {
        console.error('设置模型失败:', error);
        addChatMessage('系统', '模型切换失败', 'bot');
    });
}

// 添加工具调用消息
function addToolCallMessage(toolName, params, result, status) {
    const chatMessages = document.getElementById('chat-messages');
    const toolCallId = `tool_call_${Date.now()}`;
    
    let summaryText = `🔧 调用工具: ${getToolDisplayName(toolName)}`;
    if (status === 'complete') {
        summaryText += ' ✓';
    }
    
    const toolCallHtml = `
        <div class="chat-message">
            <div class="tool-call" id="${toolCallId}">
                <summary>${summaryText}</summary>
                <div class="tool-content">
                    <div class="tool-name">工具: ${toolName}</div>
                    <div class="tool-params">参数: ${JSON.stringify(params, null, 2)}</div>
                    ${result ? `<div class="tool-result">结果: ${JSON.stringify(result, null, 2)}</div>` : ''}
                </div>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', toolCallHtml);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // 存储工具调用ID用于后续更新
    window.currentToolCallId = toolCallId;
}

// 更新工具调用消息
function updateToolCallMessage(toolName, params, success, result) {
    const toolCallElement = document.getElementById(window.currentToolCallId);
    if (!toolCallElement) return;
    
    const summaryElement = toolCallElement.querySelector('summary');
    const contentElement = toolCallElement.querySelector('.tool-content');
    
    // 更新摘要
    let summaryText = `🔧 调用工具: ${getToolDisplayName(toolName)}`;
    if (success) {
        summaryText += ' ✓';
        summaryElement.style.color = '#28a745';
    } else {
        summaryText += ' ✗';
        summaryElement.style.color = '#dc3545';
    }
    summaryElement.textContent = summaryText;
    
    // 更新内容
    let resultHtml = '';
    if (success) {
        if (typeof result === 'object') {
            resultHtml = `<div class="tool-result">结果: ${JSON.stringify(result, null, 2)}</div>`;
        } else {
            resultHtml = `<div class="tool-result">结果: ${result}</div>`;
        }
    } else {
        resultHtml = `<div class="tool-error">错误: ${result}</div>`;
    }
    
    contentElement.innerHTML = `
        <div class="tool-name">工具: ${toolName}</div>
        <div class="tool-params">参数: ${JSON.stringify(params, null, 2)}</div>
        ${resultHtml}
    `;
}

// 获取工具显示名称
function getToolDisplayName(toolName) {
    const displayNames = {
        'create_shape': '创建形状',
        'run_simulation': '运行仿真',
        'reset_view': '重置视图',
        'clear_scene': '清空场景',
        'get_status': '获取状态',
        'process_ai_command': '处理AI命令'
    };
    return displayNames[toolName] || toolName;
}

// 处理消息内容，格式化工具调用标记
function formatMessageContent(content) {
    if (!content) return content;
    
    // 将工具调用标记格式化为可读的HTML
    let formattedContent = content;
    
    // 匹配工具调用标记 [TOOL_CALL:tool_name:params]
    const toolCallRegex = /\[TOOL_CALL:([^:]+):(.+?)\]/g;
    
    formattedContent = formattedContent.replace(toolCallRegex, function(match, toolName, params) {
        try {
            // 尝试解析参数
            let parsedParams = {};
            try {
                parsedParams = JSON.parse(params);
            } catch (e) {
                // 如果JSON解析失败，尝试手动解析
                params = params.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
                if (!params.startsWith('{')) params = '{' + params;
                if (!params.endsWith('}')) params = params + '}';
                try {
                    parsedParams = JSON.parse(params);
                } catch (e2) {
                    parsedParams = { raw: params };
                }
            }
            
            // 创建格式化的工具调用显示
            const toolDisplayName = getToolDisplayName(toolName);
            const paramsStr = JSON.stringify(parsedParams, null, 2);
            
            return `<div class="tool-call-inline">
                <span class="tool-call-marker">🔧 ${toolDisplayName}</span>
                <div class="tool-call-details">
                    <strong>工具:</strong> ${toolName}<br>
                    <strong>参数:</strong> <code>${paramsStr}</code>
                </div>
            </div>`;
        } catch (e) {
            // 如果解析失败，显示原始标记
            return `<span class="tool-call-raw">${match}</span>`;
        }
    });
    
    return formattedContent;
} 