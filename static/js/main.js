// 全局变量
let scene, camera, renderer, controls;
let socket;
let objects = [];
let selectedObject = null;
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initThreeJS();
    initSocket();
    initEventListeners();
    initGUI();
    initModelStatus();
    initMCP();
});

// 初始化Three.js
function initThreeJS() {
    // 创建场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);

    // 创建相机
    const container = document.getElementById('threejs-container');
    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 1000);
    camera.position.set(5, 5, 5);

    // 创建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 添加光源
    addLights();

    // 添加网格
    addGrid();

    // 添加控制器
    addControls();

    // 开始渲染循环
    animate();

    // 窗口大小调整
    window.addEventListener('resize', onWindowResize);
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

// 添加控制器
function addControls() {
    // 简单的轨道控制器
    let isMouseDown = false;
    let mouseX = 0;
    let mouseY = 0;
    let targetRotationX = 0;
    let targetRotationY = 0;

    const container = renderer.domElement;

    container.addEventListener('mousedown', function(event) {
        isMouseDown = true;
        mouseX = event.clientX;
        mouseY = event.clientY;
    });

    container.addEventListener('mousemove', function(event) {
        if (isMouseDown) {
            const deltaX = event.clientX - mouseX;
            const deltaY = event.clientY - mouseY;
            
            targetRotationY += deltaX * 0.01;
            targetRotationX += deltaY * 0.01;
            
            mouseX = event.clientX;
            mouseY = event.clientY;
        }
    });

    container.addEventListener('mouseup', function() {
        isMouseDown = false;
    });

    container.addEventListener('wheel', function(event) {
        const distance = camera.position.distanceTo(new THREE.Vector3(0, 0, 0));
        const newDistance = distance + event.deltaY * 0.01;
        if (newDistance > 1 && newDistance < 50) {
            camera.position.normalize().multiplyScalar(newDistance);
        }
    });

    // 更新相机位置
    function updateCamera() {
        const radius = camera.position.distanceTo(new THREE.Vector3(0, 0, 0));
        const x = radius * Math.sin(targetRotationY) * Math.cos(targetRotationX);
        const z = radius * Math.cos(targetRotationY) * Math.cos(targetRotationX);
        const y = radius * Math.sin(targetRotationX);
        
        camera.position.set(x, y, z);
        camera.lookAt(0, 0, 0);
    }

    // 将updateCamera添加到渲染循环
    window.updateCamera = updateCamera;
}

// 初始化WebSocket连接
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        addChatMessage('系统', '已连接到仿真服务器', 'bot');
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        addChatMessage('系统', '与服务器断开连接', 'bot');
    });

    socket.on('shape_created', function(data) {
        console.log('Shape created:', data);
        createShapeFromData(data);
    });

    socket.on('simulation_result', function(data) {
        console.log('Simulation result:', data);
        displaySimulationResult(data);
    });

    socket.on('simulation_started', function(data) {
        addChatMessage('系统', data.message, 'bot');
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
            updateChatMessage(messageId, data.content);
            
            // 显示模型信息
            if (data.model && data.model !== 'fallback') {
                addChatMessage('系统', `使用模型: ${data.model}`, 'bot');
            }
        } else {
            // 流式内容，追加到现有消息
            hideTypingIndicator(messageId);
            updateChatMessage(messageId, data.content, true);
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
        updateChatMessage(messageId, `错误: ${data.error}`);
    });
}

// 初始化事件监听器
function initEventListeners() {
    // 聊天功能
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-message');

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // 快速操作按钮
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const shapeType = this.dataset.shape;
            createShape(shapeType);
        });
    });

    // 仿真控制按钮
    document.getElementById('gravity-sim').addEventListener('click', function() {
        startSimulation('gravity');
    });

    document.getElementById('collision-sim').addEventListener('click', function() {
        startSimulation('collision');
    });

    document.getElementById('clear-scene').addEventListener('click', clearScene);

    // 视图控制按钮
    document.getElementById('resetView').addEventListener('click', resetView);
    document.getElementById('wireframe').addEventListener('click', toggleWireframe);
    document.getElementById('solid').addEventListener('click', toggleSolid);

    // 参数控制
    document.getElementById('size-input').addEventListener('input', function() {
        document.getElementById('size-value').textContent = this.value;
    });

    document.getElementById('radius-input').addEventListener('input', function() {
        document.getElementById('radius-value').textContent = this.value;
    });

    // 鼠标点击选择对象
    renderer.domElement.addEventListener('click', onMouseClick);
}

// 初始化GUI
function initGUI() {
    // 这里可以添加更复杂的GUI控制
    console.log('GUI initialized');
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
        
        // 检查是否需要创建形状（在后台进行，不阻塞界面）
        setTimeout(() => {
            if (message.toLowerCase().includes('立方体') || message.toLowerCase().includes('cube')) {
                createShape('cube');
            } else if (message.toLowerCase().includes('球体') || message.toLowerCase().includes('sphere')) {
                createShape('sphere');
            } else if (message.toLowerCase().includes('圆柱') || message.toLowerCase().includes('cylinder')) {
                createShape('cylinder');
            }
        }, 100);
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
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    if (messageId) {
        messageDiv.id = messageId;
    }
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    // 处理<think>标签为下拉框
    let html = content;
    html = html.replace(/<think>([\s\S]*?)<\/think>/g, '<details><summary>思考过程</summary><div class="think-block">$1</div></details>');
    // 处理模型名称显示长度
    html = html.replace(/使用模型: ([^<\s]+)/g, function(match, modelName) {
        let shortName = modelName;
        if (modelName.includes(':')) shortName = modelName.split(':')[0];
        if (shortName.length > 20) shortName = shortName.slice(0, 20) + '...';
        return '使用模型: ' + shortName;
    });
    contentDiv.innerHTML = html;
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageDiv;
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
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            // 处理<think>标签为下拉框
            let html = content;
            html = html.replace(/<think>([\s\S]*?)<\/think>/g, '<details><summary>思考过程</summary><div class="think-block">$1</div></details>');
            // 处理模型名称显示长度
            html = html.replace(/使用模型: ([^<\s]+)/g, function(match, modelName) {
                let shortName = modelName;
                if (modelName.includes(':')) shortName = modelName.split(':')[0];
                if (shortName.length > 20) shortName = shortName.slice(0, 20) + '...';
                return '使用模型: ' + shortName;
            });
            if (append) {
                contentDiv.innerHTML += html;
            } else {
                contentDiv.innerHTML = html;
            }
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
    // 检查AI回复内容是否包含仿真指令
    if (content.includes('重力仿真')) {
        startSimulation('gravity');
    } else if (content.includes('碰撞仿真')) {
        startSimulation('collision');
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
    const params = getCurrentParameters(shapeType);
    
    socket.emit('create_shape', {
        type: shapeType,
        params: params
    });
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
    const shapeData = data.data;
    let geometry, material, mesh;
    
    if (data.type === 'cube') {
        geometry = new THREE.BoxGeometry(shapeData.size, shapeData.size, shapeData.size);
    } else if (data.type === 'sphere') {
        geometry = new THREE.SphereGeometry(shapeData.radius, 32, 32);
    } else if (data.type === 'cylinder') {
        geometry = new THREE.CylinderGeometry(shapeData.radius, shapeData.radius, shapeData.height, 32);
    }
    
    material = new THREE.MeshPhongMaterial({ 
        color: getRandomColor(),
        transparent: true,
        opacity: 0.8
    });
    
    mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = { type: data.type, id: data.id };
    
    // 随机位置
    mesh.position.set(
        (Math.random() - 0.5) * 10,
        Math.random() * 5 + 1,
        (Math.random() - 0.5) * 10
    );
    
    scene.add(mesh);
    objects.push(mesh);
    
    addChatMessage('系统', `已创建${getShapeName(data.type)}`, 'bot');
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
    
    socket.emit('simulate', {
        type: type,
        params: params
    });
}

// 显示仿真结果
function displaySimulationResult(data) {
    const resultsContent = document.getElementById('results-content');
    
    if (data.type === 'gravity') {
        let html = '<h4>重力仿真结果</h4>';
        html += `<p>仿真步数: ${data.time_steps}</p>`;
        html += `<p>最终位置: [${data.positions[data.positions.length-1][0].toFixed(2)}, ${data.positions[data.positions.length-1][1].toFixed(2)}, ${data.positions[data.positions.length-1][2].toFixed(2)}]</p>`;
        html += `<p>最终速度: [${data.velocities[data.velocities.length-1][0].toFixed(2)}, ${data.velocities[data.velocities.length-1][1].toFixed(2)}, ${data.velocities[data.velocities.length-1][2].toFixed(2)}]</p>`;
        
        resultsContent.innerHTML = html;
        
        // 创建动画球体
        createAnimatedSphere(data);
    } else if (data.type === 'collision') {
        let html = '<h4>碰撞仿真结果</h4>';
        html += `<p>仿真步数: ${data.simulation_data.time_steps}</p>`;
        html += `<p>物体数量: ${data.num_objects}</p>`;
        html += `<p>碰撞次数: ${data.collision_count}</p>`;
        html += `<p>${data.message}</p>`;
        
        resultsContent.innerHTML = html;
        
        // 创建碰撞动画物体
        createCollisionObjects(data);
    } else {
        resultsContent.innerHTML = `<p>${data.message || '仿真完成'}</p>`;
    }
}

// 创建动画球体
function createAnimatedSphere(data) {
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
    
    scene.add(sphere);
    objects.push(sphere);
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
    camera.lookAt(0, 0, 0);
    window.targetRotationX = 0;
    window.targetRotationY = 0;
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

// 显示加载状态
function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

// 隐藏加载状态
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
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
    
    // 更新相机
    if (window.updateCamera) {
        window.updateCamera();
    }
    
    // 更新动画对象
    objects.forEach(obj => {
        if (obj.userData.type === 'animated') {
            const data = obj.userData;
            if (data.currentStep < data.positions.length) {
                const pos = data.positions[data.currentStep];
                obj.position.set(pos[0], pos[1], pos[2]);
                data.currentStep++;
            }
        } else if (obj.userData.type === 'collision_animated') {
            const data = obj.userData;
            if (data.currentStep < data.positions.length) {
                const pos = data.positions[data.currentStep];
                obj.position.set(pos[0], pos[1], pos[2]);
                data.currentStep++;
            }
        }
        
        // 旋转动画（只对非动画物体应用）
        if (obj.userData.type !== 'animated' && obj.userData.type !== 'collision_animated') {
            obj.rotation.y += 0.01;
        }
    });
    
    renderer.render(scene, camera);
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
    const statusElement = document.getElementById('model-status');
    const selectorElement = document.getElementById('model-selector');
    
    statusElement.textContent = '模型状态: 检查中...';
    
    fetch('/api/models')
        .then(response => response.json())
        .then(data => {
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
            } else {
                statusElement.textContent = `模型状态: ${data.error}`;
                selectorElement.style.display = 'none';
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

// 仿真状态更新
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const simulationStatusValue = document.getElementById('simulation-status-value');
    const simulationTypeValue = document.getElementById('simulation-type-value');

    // 处理仿真状态更新
    socket.on('simulation_status', function(data) {
        if (data.success) {
            updateSimulationStatus(data.data);
        }
    });

    // 处理仿真响应
    socket.on('simulation_response', function(data) {
        if (data.success) {
            updateSimulationStatus(data.data);
            showNotification('仿真操作成功', 'success');
        } else {
            showNotification('仿真操作失败: ' + data.error, 'error');
        }
    });

    // 处理仿真错误
    socket.on('simulation_error', function(data) {
        showNotification('仿真错误: ' + data.error, 'error');
    });

    // 更新仿真状态显示
    function updateSimulationStatus(data) {
        if (data.status) {
            simulationStatusValue.textContent = data.status;
        }
        if (data.current_simulation) {
            simulationTypeValue.textContent = data.current_simulation;
        }
    }

    // 显示通知
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // 处理消息发送
    const sendMessageBtn = document.getElementById('send-message');
    const chatInput = document.getElementById('chat-input');

    sendMessageBtn.addEventListener('click', function() {
        const message = chatInput.value.trim();
        if (message) {
            socket.emit('chat_message', {
                message: message,
                session_id: Date.now().toString()
            });
            chatInput.value = '';
        }
    });

    // 处理回车键发送消息
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessageBtn.click();
        }
    });
}); 