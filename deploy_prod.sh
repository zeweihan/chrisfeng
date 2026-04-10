#!/bin/bash
source ~/.zshrc 2>/dev/null
# 宝塔面板生产环境一键部署脚本 (配合 WebHook/Git Deploy 使用)

echo "🚀 开始部署 HR Report 生产环境..."

# 0. 拉取最新代码
echo "--> 0/3 拉取最新代码..."
git fetch --all
git reset --hard origin/main
git pull origin main || echo "⚠️ 代码拉取可能遇到警告，但将继续执行部署。"

# 1. 前端打包
echo "--> 1/3 构建前端资源..."
cd frontend
npm install
npm run build
cd ..

# 2. 安装后端环境
echo "--> 2/3 安装后端依赖..."
cd backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi
pip install -r requirements.txt
# 确保数据库文件存在
python3 -c "import database; database.init_db()"
cd ..

# 3. 使用 PM2 守护进程部署
echo "--> 3/3 配置 PM2 进程守护..."
# 检查是否安装了 pm2
if ! command -v pm2 &> /dev/null
then
    echo "❌ 尚未安装 pm2！请先执行: npm install -g pm2"
    exit 1
fi

# 停止旧进程
pm2 delete hr-backend 2>/dev/null
pm2 delete hr-frontend 2>/dev/null

# 启动后端 (指定虚拟环境中的 python 路径以避免找不到包)
cd backend

if [ -f "venv/bin/uvicorn" ]; then
    pm2 start ./venv/bin/uvicorn --name "hr-backend" -- main:app --host 127.0.0.1 --port 9169
elif [ -f ".venv/bin/uvicorn" ]; then
    pm2 start ./.venv/bin/uvicorn --name "hr-backend" -- main:app --host 127.0.0.1 --port 9169
else
    # 万一都没有，尝试用虚拟环境下的 python 运行模块
    if [ -f "venv/bin/python" ]; then
        pm2 start ./venv/bin/python --name "hr-backend" -- -m uvicorn main:app --host 127.0.0.1 --port 9169
    elif [ -f ".venv/bin/python" ]; then
        pm2 start ./.venv/bin/python --name "hr-backend" -- -m uvicorn main:app --host 127.0.0.1 --port 9169
    else
        pm2 start python3 --name "hr-backend" -- -m uvicorn main:app --host 127.0.0.1 --port 9169
    fi
fi
cd ..

# 启动前端静态资源代理 (SPA模式，防止 React Router 刷新 404)
pm2 serve ./frontend/dist 3169 --spa --name "hr-frontend"

# 保存并配置开机自启
pm2 save

echo "✅ 部署完成！"
echo "前端运行在: http://127.0.0.1:3169"
echo "后端运行在: http://127.0.0.1:9169"
echo "💡 提示：建议在宝塔面板配置 Nginx 反向代理，将域名指向前端端口 3169，并针对 /api 路径反向代理至 9169。"
