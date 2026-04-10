# HR 月度报告生成器

自动化人力资源分析报告生成系统。

## 功能
- 上传花名册（Excel）自动解析在职/离职数据
- 上传成本数据、薪酬数据（可选）
- LLM 驱动生成 Key Findings 和高管洞察
- 在线预览 HTML 报告，支持所见即所得编辑
- Admin 后台配置 LLM 提示词

## 技术栈
- **后端**: Python 3.10+ / FastAPI / SQLite / pandas / OpenRouter LLM
- **前端**: React 18 / Vite / TypeScript / Tailwind CSS

## 部署
阿里云 + 宝塔面板，详见 DEPLOY.md

## 目录结构
```
hr-report/
├── backend/         # FastAPI 后端
│   ├── main.py      # 入口
│   ├── routers/     # API 路由
│   └── services/    # 业务逻辑
├── frontend/        # React 前端
│   └── src/
├── Data/            # 数据库 + 上传文件
└── README.md
```
