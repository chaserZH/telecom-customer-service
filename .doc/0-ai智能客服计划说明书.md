电信套餐AI智能客服系统-整体规划方案

# 1 项目概述

**项目名称**: 电信套餐AI智能客服系统
**业务场景**: 办理流量包的智能客服
**技术栈**: Python + 大模型(GPT/Claude) + MySQL + FastAPI + Vue.js
**开发周期**: 4个阶段，预计8-10周

**基本模块图**：如下

![himg](https://chaser-zh-bucket.oss-cn-shenzhen.aliyuncs.com//uPic/oPeZ9X.png)

# 2 系统目标

1. 理解用户自然语言查询套餐需求

2. 支持多轮对话，智能追问缺失信息
3. 精准推荐符合用户需求的套餐
4. 支持套餐办理、查询使用情况等业务
5. 预留RAG接口，未来可接入业务知识库

# 3 分阶段实施计划

## 3.1 第一阶段：NLU模块（2周）

**目标**: 实现自然语言理解，将用户输入转为结构化参数

**核心功能：**

	* 基于大模型Function Calling的意图识别
	* 实体抽取和参数提取
	* 槽位填充机制
	* 数据库查询执行器



**交服务：** 

	* NLU引擎核心代码
	* Function定义和路由系统
	* 数据库设计和初始化脚本
	* 单元测试

**技术方案：**

	* 使用OpenAI/Claude API的Function Calling
	* 不使用传统NLU模型(BERT/LSTM)
	* 直接用大模型端到端理解



## 3.2 第二阶段：DST模块（2周）

**目标**: 实现对话状态跟踪，管理多轮对话上下文

**核心功能**:

- 会话状态管理
- 对话历史追踪
- 槽位状态维护
- 上下文理解和继承



**交付物**:

- DialogStateTracker类
- 状态持久化机制(Redis)
- 多轮对话测试用例



**技术要点**:

- 状态机设计
- 槽位补全策略
- 会话超时管理



## 3.3 第三阶段：NLG + Policy模块（2周）

**目标**: 实现对话策略和自然语言生成

**核心功能**:

- 对话策略管理(Policy)
  - 何时反问
  - 何时推荐
  - 何时确认
- 自然语言生成(NLG)
  - 友好的回复话术
  - 动态模板生成
  - 大模型辅助生成

**交付物**:

- Policy决策引擎
- NLG生成模块
- 话术模板库

**技术要点**:

- 规则 + 大模型混合策略
- 响应模板管理
- A/B测试支持

## 3.4 第四阶段：Web 系统+AI Agent（2-4周）

**目标**: 完整的Web交互系统和Agent化部署

**核心功能**:

- Web前端界面(Vue.js)
- FastAPI后端服务
- Agent化封装
- MCP集成(最后实现)

**交付物**:

- 前端聊天界面
- RESTful API服务
- Docker部署方案
- 监控和日志系统



# 4 系统架构设计

## 4.1 整体架构

```
┌─────────────────────────────────────────────┐
│            用户层 (Web/API)                  │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         对话管理器 (Dialog Manager)          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   NLU    │→│   DST    │→│  Policy  │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│            执行层 (Executor)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ DB Query │  │   RAG    │  │ API Call │  │
│  │          │  │  (预留)   │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────┐
│         响应生成层 (NLG + Format)            │
└─────────────────────────────────────────────┘
```

## 4.2 数据流转

```
用户输入 
  → 文本预处理 
  → NLU理解(意图+实体) 
  → DST状态更新
  → Policy决策
  → 执行器调用
  → NLG生成回复
  → 返回用户
```

## 4.3 代码目录结构

```
telecom-ai-customer-service/
│
├── config/                    # 配置文件
│   ├── __init__.py
│   ├── settings.py           # 系统配置
│   └── prompts.py            # Prompt模板
│
├── core/                      # 核心模块
│   ├── __init__.py
│   │
│   ├── nlu/                  # 【第一阶段】NLU模块
│   │   ├── __init__.py
│   │   ├── nlu_engine.py     # NLU引擎主类
│   │   ├── intent_classifier.py  # 意图识别
│   │   ├── entity_extractor.py   # 实体抽取
│   │   ├── slot_filler.py        # 槽位填充
│   │   └── function_definitions.py  # Function定义
│   │
│   ├── dst/                  # 【第二阶段】DST模块
│   │   ├── __init__.py
│   │   ├── dialog_state.py   # 对话状态
│   │   ├── state_tracker.py  # 状态跟踪器
│   │   └── context_manager.py # 上下文管理
│   │
│   ├── policy/               # 【第三阶段】Policy模块
│   │   ├── __init__.py
│   │   ├── dialog_policy.py  # 对话策略
│   │   └── policy_rules.py   # 策略规则
│   │
│   └── nlg/                  # 【第三阶段】NLG模块
│       ├── __init__.py
│       ├── response_generator.py  # 响应生成
│       └── templates.py      # 模板库
│
├── executor/                  # 执行层
│   ├── __init__.py
│   ├── db_executor.py        # 数据库执行器
│   ├── rag_executor.py       # RAG执行器(预留)
│   └── api_executor.py       # API执行器
│
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── package.py            # 套餐模型
│   ├── user.py               # 用户模型
│   └── conversation.py       # 对话模型
│
├── database/                  # 数据库
│   ├── __init__.py
│   ├── db_manager.py         # 数据库管理
│   ├── schema.sql            # 表结构
│   └── init_data.sql         # 初始化数据
│
├── api/                       # 【第四阶段】API服务
│   ├── __init__.py
│   ├── main.py               # FastAPI主入口
│   ├── routers/
│   │   ├── chat.py           # 聊天接口
│   │   └── admin.py          # 管理接口
│   └── schemas/
│       └── request.py        # 请求模型
│
├── web/                       # 【第四阶段】前端
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   └── App.vue
│   └── package.json
│
├── agent/                     # 【第四阶段】Agent封装
│   ├── __init__.py
│   ├── chatbot_agent.py      # Chatbot Agent
│   └── mcp_integration.py    # MCP集成(最后)
│
├── tests/                     # 测试
│   ├── test_nlu.py
│   ├── test_dst.py
│   ├── test_policy.py
│   └── test_integration.py
│
├── utils/                     # 工具函数
│   ├── __init__.py
│   ├── logger.py             # 日志
│   └── validators.py         # 验证器
│
├── requirements.txt           # 依赖
├── README.md                  # 说明文档
├── Dockerfile                 # Docker配置
└── docker-compose.yml         # 容器编排
```



# 5 技术选型

### 后端

- **语言**: Python 3.10+
- **框架**: FastAPI (异步高性能)
- **大模型**: OpenAI GPT-4 / Anthropic Claude
- **数据库**: MySQL 8.0 (结构化数据)
- **缓存**: Redis (会话状态)
- **ORM**: SQLAlchemy



### 前端

- **框架**: Vue 3 + TypeScript

- **UI库**: Element Plus

- **状态管理**: Pinia

- **HTTP**: Axios

  

### DevOps

- **容器**: Docker + Docker Compose
- **日志**: Loguru
- **监控**: Prometheus + Grafana (可选)



# 6 开发里程碑

| 阶段     | 时间      | 里程碑         | 验收标准                       |
| -------- | --------- | -------------- | ------------------------------ |
| 第一阶段 | Week 1-2  | NLU模块完成    | 能正确理解用户意图并查询数据库 |
| 第二阶段 | Week 3-4  | DST模块完成    | 支持多轮对话，上下文正确追踪   |
| 第三阶段 | Week 5-6  | Policy+NLG完成 | 回复自然流畅，策略合理         |
| 第四阶段 | Week 7-10 | 完整系统上线   | Web界面可用，Agent可部署       |



# 7 风险与应付

| 风险             | 影响 | 应对措施                     |
| ---------------- | ---- | ---------------------------- |
| 大模型API不稳定  | 高   | 实现重试机制、多模型切换     |
| 意图识别准确率低 | 高   | 优化Prompt、增加Few-shot示例 |
| 多轮对话状态混乱 | 中   | 详细测试DST模块、状态回滚    |
| 响应延迟过高     | 中   | 缓存常见查询、异步处理       |