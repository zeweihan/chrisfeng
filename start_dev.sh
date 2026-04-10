#!/bin/bash
source ~/.zshrc 2>/dev/null
echo "🚀 正在启动研发环境 HR Report 系统..."

# ================================
# 1. 后端自检与启动
# ================================
echo "--> 启动 FastAPI 后端 (Port: 9169)"
cd backend

# 检查虚拟环境并自动配置
if [ ! -d "venv" ]; then
    echo "📦 检测到尚未配置 Python 虚拟环境，正在全自动配置..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 确保数据库存在
python3 -c "import database; database.init_db()"

python3 -m uvicorn main:app --host 0.0.0.0 --port 9169 --reload &
BACKEND_PID=$!

# ================================
# 2. 前端自检与启动
# ================================
echo "--> 启动 React 前端 (Port: 3169)"
cd ../frontend

# 检查 Node 依赖是否已经安装
if [ ! -d "node_modules" ]; then
    echo "📦 检测到尚未安装 Node 模块，正在自动构建..."
    npm install
fi

npm run dev -- --force &
FRONTEND_PID=$!

echo "✨ 系统已完美启动并实现环境隔离！"
echo "👉 后端接口: http://127.0.0.1:9169/docs (Swagger)"
echo "👉 前端面板: http://127.0.0.1:3169/"
echo "按 Ctrl+C 安全停止所有服务。"

# 等待按键停止
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
