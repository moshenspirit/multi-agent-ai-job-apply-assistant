# BOSS 岗位匹配助手 v1.0

基于 Vue 3 + Flask + SQLite 的半自动化岗位筛选工具。

## 功能

- **简历管理**：上传 PDF/图片简历，自动解析结构化信息
- **条件配置**：自定义搜索关键词、筛选条件（城市、薪资、学历等）
- **岗位采集**：Playwright 自动化采集 BOSS 直聘岗位信息
- **AI 匹配**：GPT-4o 智能分析岗位与简历的匹配度
- **结果展示**：卡片式岗位列表，按匹配度排序，标记状态
- **投递记录**：手动标记已投递，跟踪进度

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ |

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

编辑 `backend/.env`，填入你的 OpenAI API Key：

```
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动

```bash
# 方式一：一键启动（Windows）
双击 start.bat

# 方式二：分别启动
# 终端1 - 后端
cd backend
python -m app.app

# 终端2 - 前端
cd frontend
npm run dev
```

访问 http://localhost:5173

## 使用流程

1. 在「简历管理」上传你的简历（前端开发 / AI开发）
2. 在「配置中心」设置搜索关键词和筛选条件
3. 在「仪表盘」点击「开始采集」
4. 等待采集和 AI 匹配完成
5. 在「岗位列表」查看匹配结果
6. 打开原始链接，手动在 BOSS 直聘投递
7. 回到系统标记「已投递」

## 项目结构

```
web/
├── backend/            # Python Flask 后端
│   ├── app/
│   │   ├── models/     # 数据模型
│   │   ├── routes/     # API 路由
│   │   ├── services/   # 业务逻辑
│   │   └── utils/      # 工具函数
│   └── requirements.txt
├── frontend/           # Vue 3 前端
│   └── src/
│       ├── views/      # 页面组件
│       ├── api/        # API 封装
│       ├── stores/     # Pinia 状态管理
│       └── types/      # TypeScript 类型
└── start.bat           # Windows 一键启动
```
