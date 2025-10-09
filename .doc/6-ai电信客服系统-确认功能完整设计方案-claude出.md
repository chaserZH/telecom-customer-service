# 客服系统确认功能完整设计方案

**版本**: v2.0  
**设计方案**: 状态机 + 规则增强  
**最后更新**: 2025-01-XX

---

## 目录

- [一、问题分析](#一问题分析)
- [二、方案对比](#二方案对比)
- [三、方案选择](#三方案选择)
- [四、详细设计](#四详细设计)
- [五、核心实现](#五核心实现)
- [六、集成方案](#六集成方案)
- [七、测试方案](#七测试方案)
- [八、上线计划](#八上线计划)

---

## 一、问题分析

### 1.1 核心挑战

在对话式客服系统中，需要处理**确认流程中的复杂对话**，特别是以下场景：

#### 场景一：简单确认流程 ✅
```
用户: 有哪些套餐
系统: [返回套餐列表]
用户: 办理经济套餐，手机号13800000000
系统: 请确认为138...办理【经济套餐】吗？
用户: 确认办理
系统: 已成功办理【经济套餐】，次月生效
```
**状态**: 当前系统已基本支持

#### 场景二：确认中插入咨询 🔥（核心挑战）
```
用户: 办理无限套餐，手机号13800000000
系统: 此为高价套餐，请确认为138...办理【无限套餐】吗？
用户: 那先介绍下无限套餐信息  ← 🔥 插入咨询
系统: 【无限套餐】价格150元/月，流量150G
      💡 提醒：待确认为138...办理【无限套餐】，确认请回复"确认"
用户: 确认办理
系统: 已成功办理【无限套餐】，次月生效
```
**状态**: ❌ 当前系统存在问题

#### 场景三：确认中换话题
```
用户: 办理无限套餐，手机号13800000000
系统: 请确认为138...办理【无限套餐】吗？
用户: 查询我的流量使用情况  ← 🔥 完全新话题
系统: [清除确认态，处理新请求]
      📱 138...的使用情况：本月已用流量5GB...
```
**状态**: ❌ 当前系统可能误判

### 1.2 技术问题

#### 问题1：意图识别不准确
- **现象**: "办理流程" 被误判为 "确认"
- **原因**: 规则过于宽松（`len(text) <= 5` 且包含"办理"）
- **影响**: 用户咨询流程却触发了业务执行

#### 问题2：状态管理混乱
- **现象**: 咨询后确认态被错误清除
- **原因**: 无法区分"相关咨询"和"新话题"
- **影响**: 用户咨询后需要重新发起办理

#### 问题3：用户体验不佳
- **现象**: 咨询后没有提醒用户仍需确认
- **原因**: 缺少确认提醒机制
- **影响**: 用户以为咨询就是取消了操作

### 1.3 设计目标

| 目标 | 指标 | 说明 |
|------|------|------|
| **准确率** | ≥ 90% | 正确识别确认/取消/咨询/新话题 |
| **用户体验** | 自然流畅 | 支持插入式咨询，不打断流程 |
| **响应速度** | < 50ms | 状态判断和转移的耗时 |
| **可维护性** | 高 | 代码结构清晰，易于扩展 |
| **误判率** | < 3% | "办理流程"等case不误判 |

---

## 二、方案对比

### 方案A：纯规则增强

#### 核心思路
在当前规则基础上，增加"话题相关性检测"和"意图细分"，通过 if-else 处理各种情况。

#### 架构
```
用户输入 → 确认态检查 → 话题相关性 → 意图判断 → if-else分支处理
```

#### 优点
- ✅ 开发快速：2周完成
- ✅ 简单直观：逻辑清晰
- ✅ 无需数据：不需要标注
- ✅ 可独立工作：不依赖其他架构

#### 缺点
- ❌ 结构性差：if-else嵌套深，难以维护
- ❌ 扩展困难：添加新状态需改多处
- ❌ 状态隐式：pending 标志分散在代码中
- ❌ 测试困难：状态转移逻辑耦合

#### 适用场景
- 快速验证 MVP
- 团队人数 < 2 人
- 场景简单（< 5 种状态）

---

### 方案B：状态机 + 规则增强 ⭐⭐⭐⭐⭐（推荐）

#### 核心思路
**分层设计**：用状态机管理架构，用规则实现算法。

```
架构层（状态机）：定义有哪些状态、如何转移
    ↓
算法层（规则）：判断应该转移到哪个状态
    ↓
业务层：执行具体操作
```

#### 架构
```
用户输入 → 状态机检查当前状态 → 规则检测事件类型 
         → 状态机执行转移 → 业务处理
```

#### 优点
- ✅ **结构清晰**：状态和转移显式定义
- ✅ **易于扩展**：添加新状态独立修改
- ✅ **便于测试**：状态转移可单独测试
- ✅ **可维护性高**：职责分离，代码组织好
- ✅ **规则灵活**：算法层可独立优化

#### 缺点
- ❌ 开发周期稍长：2.5-3周
- ❌ 学习成本：需要理解状态机概念
- ❌ 代码量稍多：~600行（vs 400行）

#### 适用场景
- ✅ 长期维护的产品（推荐）
- ✅ 状态较多（> 3 种）
- ✅ 需要高可维护性
- ✅ 团队 ≥ 2 人

---

### 方案C：小模型分类

#### 核心思路
训练 BERT-tiny 模型，在确认态下分类用户意图。

#### 架构
```
用户输入 → 确认态检查 → 规则快速路径(70%) 
         → BERT模型分类(25%) → 状态处理
```

#### 优点
- ✅ 准确率高：92-95%
- ✅ 泛化能力强：理解口语化表达

#### 缺点
- ❌ 需要数据：2000-5000 条标注
- ❌ 开发周期长：1-2 个月
- ❌ 维护成本高：需要 ML 工程师
- ❌ 部署复杂：模型服务

#### 适用场景
- 成熟期产品
- 有 ML 团队
- 对准确率要求极高

---

### 方案D：LLM 直接判断

#### 核心思路
每次确认态输入，调用 LLM（DeepSeek/GPT-4o-mini）分类。

#### 架构
```
用户输入 → 确认态检查 → 构建 prompt → LLM 分类 → JSON 输出
```

#### 优点
- ✅ 准确率最高：96-98%
- ✅ 开发最快：1-2 天
- ✅ 理解能力强：处理复杂对话

#### 缺点
- ❌ 成本高：0.001-0.01 元/次
- ❌ 响应慢：200-500ms
- ❌ 不稳定：输出可能变化

#### 适用场景
- 预算充足
- 追求极致体验
- 低并发场景

---

### 方案E：混合架构（终极方案）

#### 核心思路
规则(70%) + 模型(25%) + LLM(5%) 分层决策。

#### 优点
- ✅ 准确率最优：94-97%
- ✅ 性能均衡：平均 10-50ms
- ✅ 成本可控：只有 5% 走 LLM

#### 缺点
- ❌ 架构复杂
- ❌ 开发周期长：2-3 个月

#### 适用场景
- 成熟产品
- 有完整技术团队
- 长期运营 1 年+

---

### 方案对比总结

| 方案 | 开发周期 | 准确率 | 响应时间 | 维护成本 | 推荐指数 | 适用阶段 |
|------|---------|--------|---------|---------|---------|---------|
| A. 纯规则 | 2周 | 85-90% | <5ms | 低 | ⭐⭐⭐ | 快速验证 |
| **B. 状态机+规则** | 2.5-3周 | 88-92% | <10ms | 中 | ⭐⭐⭐⭐⭐ | **推荐** |
| C. 小模型 | 1-2月 | 92-95% | 5-10ms | 高 | ⭐⭐⭐ | 成熟期 |
| D. LLM | 1-2天 | 96-98% | 200-500ms | 中 | ⭐⭐ | 特殊场景 |
| E. 混合 | 2-3月 | 94-97% | 10-50ms | 高 | ⭐⭐⭐⭐⭐ | 终极方案 |

---

## 三、方案选择

### 3.1 推荐方案：方案B（状态机 + 规则增强）

#### 选择理由

**1. 符合当前阶段**
- 你的系统处于开发期，需要清晰的架构
- 团队规模 1-2 人，需要高可维护性
- 需要支持长期迭代优化

**2. 技术优势明显**
- **状态机提供架构**：状态清晰，转移规范
- **规则提供算法**：快速实现，易于调试
- **职责分离**：状态管理和事件检测独立

**3. 投入产出比优**
- 开发成本：2.5-3周（可接受）
- 准确率预期：88-92%（覆盖绝大多数场景）
- 维护成本：中等（分层清晰，易于修改）

**4. 可持续演进**
```
当前：隐式状态管理
  ↓
方案B：状态机 + 规则
  ↓ (用户量增长)
方案E：状态机 + 混合算法（规则+模型+LLM）
```

### 3.2 状态机和规则的关系

#### 核心认知 🎯

**状态机和规则不是对立的，而是互补的！**

```
完整方案 = 状态机（架构层） + 规则（算法层）
```

| 层面 | 状态机 | 规则 |
|------|--------|------|
| **职责** | 管理状态和转移 | 检测事件类型 |
| **问题** | "有哪些状态？如何转移？" | "当前是什么事件？" |
| **类比** | 地图（有哪些地点） | 导航（如何从A到B） |
| **代码** | `state_machine.transition(event)` | `event = detect_event(input)` |

#### 为什么必须结合？

**单独用状态机**：
```python
# 只能这样调用
state_machine.transition("user_confirm", context)

# 🤔 问题：如何知道用户输入是"user_confirm"事件？
# 答：需要规则/模型来判断！
```

**单独用规则**：
```python
# 只能这样判断
if is_confirmation_word(user_input):
    state.pending_confirmation = False  # 手动管理
    execute_action()

# 🤔 问题：状态分散管理，如何保证转移合法？
# 答：需要状态机统一管理！
```

**结合使用**：
```python
# 1. 规则检测事件
event = event_detector.detect(user_input)  # "user_confirm"

# 2. 状态机执行转移
state_machine.transition(event)  # PENDING → EXECUTING

# 3. 根据新状态处理
handle_by_state(state_machine.current_state)
```

### 3.3 实施路线图

```
Week 1: 状态机框架 + 基础规则
  - 定义状态枚举
  - 实现状态机类
  - 移植现有规则为事件检测器

Week 2: 完善规则 + 集成
  - 优化事件检测逻辑（话题相关性等）
  - 集成到 chatbot_policy.py
  - 完善各状态的处理逻辑

Week 2.5: 测试
  - 单元测试（状态转移）
  - 集成测试（完整对话流程）
  - 手动测试（边界case）

Week 3: 上线
  - 灰度发布
  - 监控指标
  - Badcase 收集
```

---

## 四、详细设计

### 4.1 整体架构

```
┌──────────────────────────────────────────────────────┐
│                    用户输入                           │
└────────────────────┬─────────────────────────────────┘
                     ↓
         ┌───────────────────────┐
         │ Layer 1: 状态机层     │  ← What（架构）
         │ 检查当前状态          │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Layer 2: 算法层       │  ← How（实现）
         │ 规则检测事件类型      │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Layer 1: 状态机层     │  ← What（架构）
         │ 执行状态转移          │
         └───────────┬───────────┘
                     ↓
         ┌───────────────────────┐
         │ Layer 3: 业务层       │  ← Do（执行）
         │ 根据状态执行处理      │
         └───────────────────────┘
```

### 4.2 状态机设计

#### 4.2.1 状态定义

```python
class ConfirmationState(Enum):
    """确认状态枚举"""
    IDLE = "idle"                           # 空闲（无确认）
    PENDING = "pending_confirmation"        # 待确认
    INQUIRING = "confirming_with_inquiry"   # 确认中咨询
    EXECUTING = "executing"                 # 执行中
    COMPLETED = "completed"                 # 已完成
    CANCELLED = "cancelled"                 # 已取消
    TIMEOUT = "timeout"                     # 已超时
```

#### 4.2.2 状态转移图

```
                    trigger_confirmation
        IDLE ─────────────────────────────→ PENDING
         ↑                                      │
         │                                      │ user_confirm
         │                                      ↓
         │                                  EXECUTING
         │                                      │
         │                                      │ success
         │                                      ↓
         │                                  COMPLETED
         │
         │ user_new_topic                      
         ├──────────────────────────── PENDING
         │                                  │  │
         │                     user_inquiry │  │ user_deny
         │                                  ↓  ↓
         │                              INQUIRING  CANCELLED
         │                                  │
         │                  inquiry_answered│
         │                                  ↓
         └──────────────────────────────PENDING
                                             │
                                     timeout │
                                             ↓
                                          TIMEOUT
```

#### 4.2.3 状态转移表

```python
STATE_TRANSITIONS = {
    "IDLE": {
        "trigger_confirmation": "PENDING",  # 触发确认流程
    },
    
    "PENDING": {
        "user_confirm": "EXECUTING",        # 用户确认 → 执行
        "user_deny": "CANCELLED",           # 用户取消 → 取消
        "user_inquiry": "INQUIRING",        # 用户咨询 → 咨询态
        "user_new_topic": "IDLE",           # 新话题 → 空闲
        "timeout": "TIMEOUT",               # 超时 → 超时态
    },
    
    "INQUIRING": {
        "inquiry_answered": "PENDING",      # 咨询完成 → 回到待确认
        "user_confirm": "EXECUTING",        # 咨询中确认 → 执行
        "user_deny": "CANCELLED",           # 咨询中取消 → 取消
        "user_new_topic": "IDLE",           # 咨询中新话题 → 空闲
    },
    
    "EXECUTING": {
        "success": "COMPLETED",             # 执行成功 → 完成
        "failure": "IDLE",                  # 执行失败 → 空闲
    },
    
    "COMPLETED": {
        # 终态，自动返回 IDLE
    },
    
    "CANCELLED": {
        # 终态，自动返回 IDLE
    },
    
    "TIMEOUT": {
        # 终态，自动返回 IDLE
    }
}
```

### 4.3 事件检测（规则层）

#### 4.3.1 事件类型

```python
class ConfirmationEvent(Enum):
    """确认事件类型"""
    USER_CONFIRM = "user_confirm"          # 用户确认
    USER_DENY = "user_deny"                # 用户取消
    USER_INQUIRY = "user_inquiry"          # 用户咨询（相关话题）
    USER_NEW_TOPIC = "user_new_topic"      # 用户新话题（无关）
    TIMEOUT = "timeout"                    # 超时
    INQUIRY_ANSWERED = "inquiry_answered"  # 咨询已回答
    SUCCESS = "success"                    # 执行成功
    FAILURE = "failure"                    # 执行失败
```

#### 4.3.2 事件检测流程

```
用户输入
  ↓
【优先级1】纯确认/取消词检测（快速路径）
  ↓ (未匹配)
【优先级2】话题相关性分析
  ↓
  ├─→ 相关 → 【优先级3】意图细分（确认/取消/咨询组合词）
  │              ↓
  │            确定事件类型
  │
  └─→ 不相关 → USER_NEW_TOPIC
```

#### 4.3.3 话题相关性算法

**目标**：判断用户输入是否与待确认操作相关

**评分规则**：

| 规则 | 权重 | 示例 |
|------|------|------|
| 包含待确认实体（套餐名等） | +0.4 | "无限套餐" |
| 包含咨询关键词 | +0.3 | "介绍"、"价格"、"详情" |
| 包含套餐相关词 | +0.2 | "套餐"、"资费"、"流量" |
| 疑问句 | +0.1 | "？"、"吗"、"呢" |
| 包含新话题关键词 | -0.3 | "查询余额"、"流量使用" |

**阈值**：`score >= 0.5` 视为相关

**示例**：

| 输入 | 待确认操作 | 实体 | 咨询 | 套餐 | 疑问 | 新话题 | 总分 | 相关? |
|------|-----------|------|------|------|------|--------|------|-------|
| "介绍下无限套餐" | 办理无限套餐 | 0.4 | 0.3 | 0.2 | 0 | 0 | **0.9** | ✅ |
| "套餐价格多少" | 办理无限套餐 | 0 | 0.3 | 0.2 | 0.1 | 0 | **0.6** | ✅ |
| "查询我的流量" | 办理无限套餐 | 0 | 0 | 0 | 0 | -0.3 | **-0.3** | ❌ |

### 4.4 模块划分

```
core/policy/confirmation/
├── __init__.py
│
├── state_machine.py              # 状态机（Layer 1）
│   ├── ConfirmationState         # 状态枚举
│   ├── ConfirmationStateMachine  # 状态机类
│   └── STATE_TRANSITIONS         # 转移表
│
├── event_detector.py             # 事件检测器（Layer 2）
│   ├── ConfirmationEvent         # 事件枚举
│   ├── EventDetector             # 检测器主类
│   ├── IntentClassifier          # 意图分类
│   └── TopicAnalyzer             # 话题相关性
│
├── handler.py                    # 确认处理器（Layer 3）
│   └── ConfirmationHandler       # 统一处理入口
│
└── context.py                    # 数据结构
    ├── ConfirmationContext       # 确认上下文
    └── ConfirmationResult        # 处理结果
```

---

## 五、核心实现

### 5.1 状态机实现

```python
# core/policy/confirmation/state_machine.py

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from utils.logger import logger


class ConfirmationState(Enum):
    """确认状态"""
    IDLE = "idle"
    PENDING = "pending_confirmation"
    INQUIRING = "confirming_with_inquiry"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# 状态转移表
STATE_TRANSITIONS = {
    "IDLE": {
        "trigger_confirmation": "PENDING"
    },
    "PENDING": {
        "user_confirm": "EXECUTING",
        "user_deny": "CANCELLED",
        "user_inquiry": "INQUIRING",
        "user_new_topic": "IDLE",
        "timeout": "TIMEOUT"
    },
    "INQUIRING": {
        "inquiry_answered": "PENDING",
        "user_confirm": "EXECUTING",
        "user_deny": "CANCELLED",
        "user_new_topic": "IDLE"
    },
    "EXECUTING": {
        "success": "COMPLETED",
        "failure": "IDLE"
    },
    "COMPLETED": {},  # 终态
    "CANCELLED": {},  # 终态
    "TIMEOUT": {}     # 终态
}


class InvalidTransitionError(Exception):
    """非法状态转移异常"""
    pass


class ConfirmationStateMachine:
    """确认状态机"""
    
    def __init__(self):
        """初始化"""
        self.current_state = ConfirmationState.IDLE
        self.previous_state: Optional[ConfirmationState] = None
        self.transition_history = []  # 转移历史
        
        logger.info("状态机初始化完成")
    
    def transition(self, event: str, context: Optional[Dict] = None):
        """
        执行状态转移
        
        Args:
            event: 事件名称
            context: 上下文信息
            
        Raises:
            InvalidTransitionError: 非法转移
        """
        context = context or {}
        
        # 检查转移是否合法
        transitions = STATE_TRANSITIONS.get(self.current_state.name, {})
        
        if event not in transitions:
            error_msg = (f"非法转移: {self.current_state.name} "
                        f"无法通过事件 '{event}' 转移")
            logger.error(error_msg)
            raise InvalidTransitionError(error_msg)
        
        # 获取目标状态
        target_state_name = transitions[event]
        target_state = ConfirmationState[target_state_name]
        
        # 执行转移前钩子
        self._before_transition(self.current_state, target_state, event, context)
        
        # 更新状态
        self.previous_state = self.current_state
        self.current_state = target_state
        
        # 记录历史
        self.transition_history.append({
            "from": self.previous_state.name,
            "to": self.current_state.name,
            "event": event,
            "timestamp": datetime.now()
        })
        
        # 执行转移后钩子
        self._after_transition(self.current_state, event, context)
        
        logger.info(f"状态转移: {self.previous_state.name} "
                   f"--[{event}]--> {self.current_state.name}")
    
    def _before_transition(self, from_state: ConfirmationState,
                          to_state: ConfirmationState,
                          event: str,
                          context: Dict):
        """转移前钩子"""
        # 可以在这里添加日志、验证等
        pass
    
    def _after_transition(self, new_state: ConfirmationState,
                         event: str,
                         context: Dict):
        """转移后钩子"""
        # 可以在这里添加状态进入后的处理
        # 例如：记录咨询次数
        if new_state == ConfirmationState.INQUIRING:
            context["inquiry_count"] = context.get("inquiry_count", 0) + 1
    
    def can_transition(self, event: str) -> bool:
        """
        检查是否可以执行转移
        
        Args:
            event: 事件名称
            
        Returns:
            bool: 是否可以转移
        """
        transitions = STATE_TRANSITIONS.get(self.current_state.name, {})
        return event in transitions
    
    def reset(self):
        """重置状态机"""
        self.current_state = ConfirmationState.IDLE
        self.previous_state = None
        self.transition_history = []
        logger.info("状态机已重置")
    
    def is_terminal_state(self) -> bool:
        """是否处于终态"""
        return self.current_state in [
            ConfirmationState.COMPLETED,
            ConfirmationState.CANCELLED,
            ConfirmationState.TIMEOUT
        ]
    
    def get_state_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "current_state": self.current_state.name,
            "previous_state": self.previous_state.name if self.previous_state else None,
            "is_terminal": self.is_terminal_state(),
            "history_count": len(self.transition_history)
        }
```

### 5.2 事件检测器实现

```python
# core/policy/confirmation/event_detector.py

from enum import Enum
from typing import Optional
from dataclasses import dataclass
import re
from utils.logger import logger


class ConfirmationEvent(Enum):
    """确认事件"""
    USER_CONFIRM = "user_confirm"
    USER_DENY = "user_deny"
    USER_INQUIRY = "user_inquiry"
    USER_NEW_TOPIC = "user_new_topic"
    TIMEOUT = "timeout"
    INQUIRY_ANSWERED = "inquiry_answered"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class TopicRelevance:
    """话题相关性"""
    is_related: bool
    score: float
    reason: str


class EventDetector:
    """事件检测器（规则实现）"""
    
    def __init__(self):
        """初始化"""
        logger.info("事件检测器初始化完成")
    
    def detect(self, user_input: str, confirmation_ctx: Dict) -> str:
        """
        检测事件类型
        
        Args:
            user_input: 用户输入
            confirmation_ctx: 确认上下文
            
        Returns:
            str: 事件名称
        """
        logger.info(f"[事件检测] 输入: {user_input}")
        
        # 优先级1: 纯确认/取消词（快速路径）
        if self._is_pure_confirmation(user_input):
            logger.info("检测到纯确认词")
            return ConfirmationEvent.USER_CONFIRM.value
        
        if self._is_pure_cancellation(user_input):
            logger.info("检测到纯取消词")
            return ConfirmationEvent.USER_DENY.value
        
        # 优先级2: 话题相关性分析
        relevance = self._analyze_topic_relevance(user_input, confirmation_ctx)
        logger.info(f"话题相关性: {relevance.is_related}, "
                   f"分数: {relevance.score:.2f}")
        
        if not relevance.is_related:
            # 不相关 → 新话题
            logger.info("检测到新话题")
            return ConfirmationEvent.USER_NEW_TOPIC.value
        
        # 优先级3: 相关话题下的意图细分
        return self._classify_related_intent(user_input)
    
    def _is_pure_confirmation(self, text: str) -> bool:
        """纯确认词检测"""
        clean = re.sub(r'[,。!?、\s]+', '', text.lower())
        pure_words = [
            "确认", "确定", "是的", "是", "对", "好的",
            "可以", "ok", "yes", "嗯", "行", "同意", "没问题"
        ]
        return clean in pure_words
    
    def _is_pure_cancellation(self, text: str) -> bool:
        """纯取消词检测"""
        clean = re.sub(r'[,。!?、\s]+', '', text.lower())
        pure_words = [
            "取消", "不", "不要", "算了", "不办",
            "no", "cancel", "不行", "不用"
        ]
        return clean in pure_words
    
    def _analyze_topic_relevance(self, text: str, 
                                 confirmation_ctx: Dict) -> TopicRelevance:
        """
        话题相关性分析（核心算法）
        """
        score = 0.0
        reasons = []
        
        # 规则1: 包含待确认实体（套餐名）
        pending_package = confirmation_ctx.get("parameters", {}).get("new_package_name")
        if pending_package and pending_package in text:
            score += 0.4
            reasons.append(f"包含套餐名'{pending_package}'")
        
        # 规则2: 包含咨询关键词
        inquiry_keywords = [
            "介绍", "详情", "说明", "了解", "查询",
            "价格", "多少钱", "包含", "什么", "有什么"
        ]
        matched_inquiry = [kw for kw in inquiry_keywords if kw in text]
        if matched_inquiry:
            score += 0.3
            reasons.append(f"包含咨询词: {matched_inquiry}")
        
        # 规则3: 包含套餐相关词
        package_keywords = ["套餐", "资费", "办理", "月费", "流量"]
        matched_package = [kw for kw in package_keywords if kw in text]
        if matched_package:
            score += 0.2
            reasons.append(f"包含套餐词: {matched_package}")
        
        # 规则4: 疑问句
        if any(w in text for w in ["？", "?", "吗", "呢"]):
            score += 0.1
            reasons.append("疑问句")
        
        # 规则5: 新话题关键词（负分）
        new_topic_keywords = [
            "我要", "帮我", "查询余额", "流量使用",
            "当前套餐", "我的套餐"
        ]
        matched_new = [kw for kw in new_topic_keywords if kw in text]
        if matched_new:
            score -= 0.3
            reasons.append(f"包含新话题词: {matched_new}")
        
        # 规则6: 咨询词排除（优先级最高）
        consultation_keywords = [
            "怎么", "如何", "怎样",
            "流程", "步骤", "手续",
            "条件", "要求"
        ]
        matched_consult = [kw for kw in consultation_keywords if kw in text]
        if matched_consult:
            # 咨询流程类问题，虽然可能相关，但不是确认/取消
            # 单独标记为咨询
            reasons.append(f"包含咨询流程词: {matched_consult}")
        
        is_related = score >= 0.5
        reason_text = "; ".join(reasons) if reasons else "无匹配"
        
        return TopicRelevance(
            is_related=is_related,
            score=score,
            reason=reason_text
        )
    
    def _classify_related_intent(self, text: str) -> str:
        """
        相关话题的意图细分
        
        Returns:
            str: 事件名称
        """
        # 1. 确认组合词
        confirm_patterns = [
            "确认办理", "好的办理", "可以办理",
            "就这个", "就办这个", "办吧", "办理吧"
        ]
        if any(p in text for p in confirm_patterns):
            logger.info("检测到确认组合词")
            return ConfirmationEvent.USER_CONFIRM.value
        
        # 2. 取消组合词
        deny_patterns = [
            "不办了", "算了不办", "取消办理",
            "不想办", "再想想", "考虑一下"
        ]
        if any(p in text for p in deny_patterns):
            logger.info("检测到取消组合词")
            return ConfirmationEvent.USER_DENY.value
        
        # 3. 咨询模式
        inquiry_patterns = [
            "介绍", "说明", "详情", "了解",
            "价格", "多少钱", "包含什么", "有什么"
        ]
        if any(p in text for p in inquiry_patterns):
            logger.info("检测到咨询模式")
            return ConfirmationEvent.USER_INQUIRY.value
        
        # 4. 短句"办理"（严格限制）
        if "办理" in text and len(text) <= 3:
            logger.info("检测到短句办理")
            return ConfirmationEvent.USER_CONFIRM.value
        
        # 5. 默认：倾向确认（低置信度）
        logger.warning(f"未明确匹配，默认确认: {text}")
        return ConfirmationEvent.USER_CONFIRM.value
```

### 5.3 确认处理器实现

```python
# core/policy/confirmation/handler.py

from typing import Dict, Any, Optional
from datetime import datetime

from .state_machine import (
    ConfirmationStateMachine, 
    ConfirmationState,
    InvalidTransitionError
)
from .event_detector import EventDetector, ConfirmationEvent
from .context import ConfirmationContext, ConfirmationResult
from utils.logger import logger


class ConfirmationHandler:
    """确认处理器（整合状态机 + 事件检测）"""
    
    def __init__(self, nlu_engine, executor):
        """
        初始化
        
        Args:
            nlu_engine: NLU引擎
            executor: 业务执行器
        """
        # Layer 1: 状态机
        self.state_machine = ConfirmationStateMachine()
        
        # Layer 2: 事件检测器
        self.event_detector = EventDetector()
        
        # 依赖
        self.nlu = nlu_engine
        self.executor = executor
        
        logger.info("确认处理器初始化完成")
    
    def handle(self, user_input: str, 
               dialog_state: 'DialogState') -> ConfirmationResult:
        """
        处理用户输入（主入口）
        
        Args:
            user_input: 用户输入
            dialog_state: 对话状态
            
        Returns:
            ConfirmationResult: 处理结果
        """
        logger.info(f"[确认处理] 开始处理: {user_input}")
        
        # 构建确认上下文
        confirmation_ctx = self._build_context(dialog_state)
        
        # Step 1: 检测事件类型（Layer 2: 算法）
        try:
            event = self.event_detector.detect(user_input, confirmation_ctx)
            logger.info(f"检测到事件: {event}")
        except Exception as e:
            logger.error(f"事件检测失败: {e}")
            return ConfirmationResult(
                action="clarify",
                message="没听明白，请回复"确认"或"取消""
            )
        
        # Step 2: 执行状态转移（Layer 1: 状态机）
        try:
            self.state_machine.transition(event, confirmation_ctx)
        except InvalidTransitionError as e:
            logger.error(f"状态转移失败: {e}")
            return ConfirmationResult(
                action="clarify",
                message="操作不合法，请重新操作"
            )
        
        # Step 3: 根据新状态执行处理（Layer 3: 业务）
        new_state = self.state_machine.current_state
        return self._handle_by_state(new_state, user_input, dialog_state)
    
    def _build_context(self, dialog_state: 'DialogState') -> Dict:
        """构建确认上下文"""
        return {
            "intent": dialog_state.confirmation_intent,
            "parameters": dialog_state.confirmation_slots,
            "created_at": dialog_state.confirmation_timestamp,
            "inquiry_count": 0
        }
    
    def _handle_by_state(self, state: ConfirmationState,
                        user_input: str,
                        dialog_state: 'DialogState') -> ConfirmationResult:
        """
        根据状态执行处理
        
        Args:
            state: 当前状态
            user_input: 用户输入
            dialog_state: 对话状态
            
        Returns:
            ConfirmationResult: 处理结果
        """
        handlers = {
            ConfirmationState.EXECUTING: self._handle_executing,
            ConfirmationState.INQUIRING: self._handle_inquiring,
            ConfirmationState.CANCELLED: self._handle_cancelled,
            ConfirmationState.TIMEOUT: self._handle_timeout,
            ConfirmationState.IDLE: self._handle_idle,
        }
        
        handler = handlers.get(state)
        if handler:
            return handler(user_input, dialog_state)
        
        # 默认
        return ConfirmationResult(
            action="inform",
            message="处理完成"
        )
    
    def _handle_executing(self, user_input: str,
                         dialog_state: 'DialogState') -> ConfirmationResult:
        """处理执行状态"""
        logger.info("[状态处理] EXECUTING")
        
        # 执行业务
        result = self.executor.execute_function(
            dialog_state.confirmation_intent,
            dialog_state.confirmation_slots
        )
        
        # 根据结果转移状态
        if result.get("success"):
            self.state_machine.transition("success")
            return ConfirmationResult(
                action="confirm_executed",
                result=result,
                clear_confirmation=True
            )
        else:
            self.state_machine.transition("failure")
            return ConfirmationResult(
                action="execute_failed",
                message=f"抱歉，{result.get('error', '执行失败')}",
                clear_confirmation=True
            )
    
    def _handle_inquiring(self, user_input: str,
                         dialog_state: 'DialogState') -> ConfirmationResult:
        """处理咨询状态（关键）"""
        logger.info("[状态处理] INQUIRING")
        
        # 1. 提取咨询意图
        inquiry_intent = self._extract_inquiry_intent(user_input)
        
        # 2. 提取咨询参数（利用确认上下文）
        inquiry_params = self._extract_inquiry_params(
            user_input,
            dialog_state
        )
        
        # 3. 执行咨询
        inquiry_result = self.executor.execute_function(
            inquiry_intent,
            inquiry_params
        )
        
        # 4. 生成提醒
        reminder = self._generate_reminder(dialog_state)
        
        # 5. 转移回待确认状态
        self.state_machine.transition("inquiry_answered")
        
        return ConfirmationResult(
            action="inquiry_answered",
            result=inquiry_result,
            reminder=reminder,
            clear_confirmation=False  # 🔥 不清除确认态
        )
    
    def _handle_cancelled(self, user_input: str,
                         dialog_state: 'DialogState') -> ConfirmationResult:
        """处理取消状态"""
        logger.info("[状态处理] CANCELLED")
        
        # 自动返回IDLE
        self.state_machine.reset()
        
        return ConfirmationResult(
            action="cancelled",
            message="已取消操作。还有什么可以帮您的吗？",
            clear_confirmation=True
        )
    
    def _handle_timeout(self, user_input: str,
                       dialog_state: 'DialogState') -> ConfirmationResult:
        """处理超时状态"""
        logger.info("[状态处理] TIMEOUT")
        
        # 自动返回IDLE
        self.state_machine.reset()
        
        return ConfirmationResult(
            action="timeout",
            message="确认已超时，请重新操作。还有什么可以帮您的吗？",
            clear_confirmation=True
        )
    
    def _handle_idle(self, user_input: str,
                    dialog_state: 'DialogState') -> ConfirmationResult:
        """处理空闲状态（新话题）"""
        logger.info("[状态处理] IDLE")
        
        return ConfirmationResult(
            action="new_topic",
            message="收到，为您处理新的请求",
            clear_confirmation=True
        )
    
    def _extract_inquiry_intent(self, user_input: str) -> str:
        """提取咨询意图"""
        # 套餐详情
        if any(kw in user_input for kw in ["介绍", "详情", "说明"]):
            return "query_package_detail"
        
        # 价格咨询
        if "价格" in user_input or "多少钱" in user_input:
            return "query_package_detail"
        
        # 流程咨询
        if "流程" in user_input or "怎么办" in user_input:
            return "business_consultation"
        
        # 默认
        return "query_package_detail"
    
    def _extract_inquiry_params(self, user_input: str,
                                dialog_state: 'DialogState') -> Dict:
        """提取咨询参数（从上下文补充）"""
        params = {}
        
        # 尝试从用户输入提取
        nlu_result = self.nlu.understand(user_input, "temp_inquiry")
        if nlu_result.parameters:
            params.update(nlu_result.parameters)
        
        # 🔥 从确认上下文补充（关键）
        if "package_name" not in params:
            pending_package = dialog_state.confirmation_slots.get("new_package_name")
            if pending_package:
                params["package_name"] = pending_package
                logger.info(f"从确认上下文补充: package_name={pending_package}")
        
        return params
    
    def _generate_reminder(self, dialog_state: 'DialogState') -> str:
        """生成确认提醒"""
        intent = dialog_state.confirmation_intent
        params = dialog_state.confirmation_slots
        
        if intent == "change_package":
            package = params.get("new_package_name")
            phone = params.get("phone", "您")
            return (f"💡 提醒：待确认为 {phone} 办理【{package}】，"
                   f"确认请回复\"确认\"，取消请回复\"取消\"")
        
        return "💡 提醒：仍有待确认的操作，确认请回复\"确认\""
```

### 5.4 数据结构

```python
# core/policy/confirmation/context.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class ConfirmationContext:
    """确认上下文"""
    intent: str                            # 待确认意图
    parameters: Dict[str, Any]             # 待确认参数
    created_at: datetime                   # 创建时间
    inquiry_count: int = 0                 # 咨询次数
    inquiry_history: List[Dict] = field(default_factory=list)  # 咨询历史


@dataclass
class ConfirmationResult:
    """确认处理结果"""
    action: str                            # 动作类型
    message: str = ""                      # 响应消息
    result: Optional[Dict] = None          # 执行结果
    reminder: str = ""                     # 提醒信息
    clear_confirmation: bool = False       # 是否清除确认态
```

---

## 六、集成方案

### 6.1 文件结构

```
telecom_chatbot/
├── core/
│   ├── policy/
│   │   ├── confirmation/              ← 🆕 新增目录
│   │   │   ├── __init__.py
│   │   │   ├── state_machine.py       ← 状态机
│   │   │   ├── event_detector.py      ← 事件检测
│   │   │   ├── handler.py             ← 处理器
│   │   │   └── context.py             ← 数据结构
│   │   ├── policy_engine.py
│   │   └── ...
│   ├── chatbot_policy.py              ← 📝 修改
│   └── ...
└── tests/
    ├── test_confirmation_state_machine.py  ← 🆕 新增
    ├── test_confirmation_flow.py           ← 🆕 新增
    └── ...
```

### 6.2 集成步骤

#### 步骤1：创建确认模块

**1.1 创建目录结构**

```bash
mkdir -p core/policy/confirmation
touch core/policy/confirmation/__init__.py
touch core/policy/confirmation/state_machine.py
touch core/policy/confirmation/event_detector.py
touch core/policy/confirmation/handler.py
touch core/policy/confirmation/context.py
```

**1.2 复制代码**

将第五章的代码分别复制到对应文件：
- `state_machine.py` - 状态机实现
- `event_detector.py` - 事件检测器实现
- `handler.py` - 确认处理器实现
- `context.py` - 数据结构

**1.3 完善 `__init__.py`**

```python
# core/policy/confirmation/__init__.py

from .state_machine import (
    ConfirmationState,
    ConfirmationStateMachine,
    InvalidTransitionError
)

from .event_detector import (
    ConfirmationEvent,
    EventDetector
)

from .handler import ConfirmationHandler

from .context import (
    ConfirmationContext,
    ConfirmationResult
)

__all__ = [
    # 状态机
    'ConfirmationState',
    'ConfirmationStateMachine',
    'InvalidTransitionError',
    
    # 事件检测
    'ConfirmationEvent',
    'EventDetector',
    
    # 处理器
    'ConfirmationHandler',
    
    # 数据结构
    'ConfirmationContext',
    'ConfirmationResult',
]
```

#### 步骤2：修改 chatbot_policy.py

**2.1 导入新模块**

```python
# 在文件顶部添加
from core.policy.confirmation import (
    ConfirmationHandler,
    ConfirmationState
)
```

**2.2 初始化处理器**

```python
class TelecomChatbotPolicy:
    def __init__(self):
        # 第一阶段：NLU
        self.nlu = NLUEngine()
        
        # 第二阶段：DST
        self.dst = DialogStateTracker()
        
        # 第三阶段：Policy + NLG
        self.policy = PolicyEngine()
        self.nlg = NLGGenerator()
        
        # 🆕 新增：确认处理器（状态机 + 规则）
        self.confirmation_handler = ConfirmationHandler(
            nlu_engine=self.nlu,
            executor=self.db_executor
        )
        
        # 高级特性
        self.recommendation = RecommendationEngine()
        
        # 执行器
        self.db_executor = DatabaseExecutor()
        
        # 缓存
        self.cache = ResponseCache(ttl=300, max_size=1000)
        
        logger.info("=" * 60)
        logger.info("第三阶段对话系统初始化完成（状态机 + 规则）")
        logger.info("=" * 60)
```

**2.3 修改 chat() 方法**

```python
def chat(self, user_input: str, session_id: Optional[str] = None,
         user_phone: Optional[str] = None) -> Dict[str, Any]:
    """处理用户输入"""
    
    start_time = datetime.now()
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    logger.info(f"\n{'=' * 60}")
    logger.info(f"[{session_id}] 收到用户输入: {user_input}")
    logger.info(f"{'=' * 60}")
    
    try:
        # 加载状态
        current_state = self.dst.get_state(session_id)
        
        # ========== 🔥 关键：确认态处理 ==========
        if current_state.pending_confirmation:
            logger.info("【检测到确认态】启用状态机处理器")
            
            # 超时检查
            if current_state.is_confirmation_expired():
                logger.warning("确认已超时")
                current_state.clear_pending_confirmation()
                self.dst.state_store.save(session_id, current_state)
                
                return {
                    "session_id": session_id,
                    "response": "确认已超时，请重新操作。还有什么可以帮您的吗？",
                    "action": "INFORM",
                    "requires_confirmation": False,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 🆕 使用状态机处理器
            confirmation_result = self.confirmation_handler.handle(
                user_input,
                current_state
            )
            
            # 构建响应
            return self._build_confirmation_response(
                confirmation_result,
                session_id,
                current_state,
                user_input
            )
        
        # ========== 正常流程（保持不变）==========
        logger.info("【阶段1】NLU理解...")
        nlu_result = self.nlu.understand(user_input, session_id, user_phone)
        nlu_result.raw_input = user_input
        logger.info(f"✓ NLU完成: intent={nlu_result.intent}")
        
        # ... 后续流程保持不变
        
    except Exception as e:
        logger.error(f"[{session_id}] 处理异常: {e}", exc_info=True)
        return {
            "session_id": session_id,
            "response": "抱歉，系统遇到了问题，请稍后再试",
            "action": "APOLOGIZE",
            "timestamp": datetime.now().isoformat()
        }
```

**2.4 添加响应构建方法**

```python
def _build_confirmation_response(
    self,
    result: ConfirmationResult,
    session_id: str,
    state: DialogState,
    user_input: str
) -> Dict[str, Any]:
    """
    构建确认响应
    
    Args:
        result: 确认处理结果
        session_id: 会话ID
        state: 对话状态
        user_input: 用户输入
        
    Returns:
        Dict: 响应字典
    """
    action = result.action
    
    # ========== 场景1: 咨询已回答 ==========
    if action == "inquiry_answered":
        logger.info("【场景】咨询已回答，保持确认态")
        
        # 格式化咨询结果
        inquiry_result = result.result
        if inquiry_result and inquiry_result.get("success"):
            response_text = self._format_inquiry_response(inquiry_result)
        else:
            response_text = f"抱歉，{inquiry_result.get('error', '查询失败') if inquiry_result else '查询失败'}"
        
        # 添加提醒
        response_text += "\n\n" + result.reminder
        
        # 更新状态（保持确认态）
        state.add_turn('assistant', response_text)
        self.dst.state_store.save(session_id, state)
        
        return {
            "session_id": session_id,
            "response": response_text,
            "action": "INFORM_WITH_REMINDER",
            "requires_confirmation": True,  # 🔥 仍需确认
            "data": inquiry_result,
            "state": {
                "turn_count": state.turn_count,
                "pending_confirmation": True
            },
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # ========== 场景2: 确认执行 ==========
    elif action == "confirm_executed":
        logger.info("【场景】确认执行")
        
        exec_result = result.result
        
        # 生成回复
        if exec_result and exec_result.get("success"):
            action_obj = Action(
                action_type=ActionType.INFORM,
                intent=state.confirmation_intent,
                parameters=exec_result
            )
            response_text = self.nlg.generate(action_obj, state)
        else:
            response_text = f"抱歉，{exec_result.get('error', '处理失败') if exec_result else '处理失败'}"
        
        # 清除确认态
        if result.clear_confirmation:
            state.clear_pending_confirmation()
        
        state.add_turn('assistant', response_text)
        self.dst.state_store.save(session_id, state)
        
        return {
            "session_id": session_id,
            "response": response_text,
            "action": "INFORM",
            "requires_confirmation": False,
            "data": exec_result,
            "state": {
                "turn_count": state.turn_count,
                "pending_confirmation": False
            },
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # ========== 场景3: 取消 ==========
    elif action == "cancelled":
        logger.info("【场景】用户取消")
        
        response_text = result.message
        
        # 清除确认态
        if result.clear_confirmation:
            state.clear_pending_confirmation()
        
        state.add_turn('assistant', response_text)
        self.dst.state_store.save(session_id, state)
        
        return {
            "session_id": session_id,
            "response": response_text,
            "action": "INFORM",
            "requires_confirmation": False,
            "state": {
                "turn_count": state.turn_count,
                "pending_confirmation": False
            },
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # ========== 场景4: 新话题 ==========
    elif action == "new_topic":
        logger.info("【场景】新话题，清除确认态")
        
        # 清除确认态
        state.clear_pending_confirmation()
        self.dst.state_store.save(session_id, state)
        
        # 重新处理
        return self.chat(user_input, session_id)
    
    # ========== 场景5: 澄清 ==========
    elif action == "clarify":
        logger.warning("【场景】需要澄清")
        
        return {
            "session_id": session_id,
            "response": result.message,
            "action": "CLARIFY",
            "requires_confirmation": True,
            "state": {
                "turn_count": state.turn_count,
                "pending_confirmation": True
            },
            "metadata": {
                "timestamp": datetime.now().isoformat()
            }
        }
    
    # ========== 默认 ==========
    else:
        logger.error(f"未知的确认动作: {action}")
        return {
            "session_id": session_id,
            "response": "抱歉，处理出现问题",
            "action": "ERROR",
            "requires_confirmation": False,
            "timestamp": datetime.now().isoformat()
        }

def _format_inquiry_response(self, result: Dict) -> str:
    """格式化咨询响应（复用现有逻辑）"""
    if not result.get("success"):
        return f"抱歉，{result.get('error', '查询失败')}"
    
    data = result.get("data", {})
    
    # 套餐详情
    if isinstance(data, dict) and "name" in data:
        return self._format_package_detail_response({"data": data})
    
    # 套餐列表
    if isinstance(data, list):
        return self._format_packages_response(result)
    
    return "查询完成"
```

### 6.3 移除旧代码（可选）

可以移除或注释 `chatbot_policy.py` 中的：
- `_is_confirmation_word()`
- `_is_cancellation_word()`
- `_handle_confirmation_response()`

**建议**：先注释，验证无问题后再删除。

---

## 七、测试方案

### 7.1 单元测试

#### 测试状态机

```python
# tests/test_confirmation_state_machine.py

import pytest
from core.policy.confirmation import (
    ConfirmationStateMachine,
    ConfirmationState,
    InvalidTransitionError
)


class TestStateMachine:
    """测试状态机"""
    
    def test_initial_state(self):
        """测试初始状态"""
        sm = ConfirmationStateMachine()
        assert sm.current_state == ConfirmationState.IDLE
    
    def test_trigger_confirmation(self):
        """测试触发确认"""
        sm = ConfirmationStateMachine()
        sm.transition("trigger_confirmation")
        assert sm.current_state == ConfirmationState.PENDING
    
    def test_user_confirm(self):
        """测试用户确认"""
        sm = ConfirmationStateMachine()
        sm.transition("trigger_confirmation")
        sm.transition("user_confirm")
        assert sm.current_state == ConfirmationState.EXECUTING
    
    def test_user_inquiry(self):
        """测试用户咨询"""
        sm = ConfirmationStateMachine()
        sm.transition("trigger_confirmation")
        sm.transition("user_inquiry")
        assert sm.current_state == ConfirmationState.INQUIRING
    
    def test_inquiry_back_to_pending(self):
        """测试咨询后返回待确认"""
        sm = ConfirmationStateMachine()
        sm.transition("trigger_confirmation")
        sm.transition("user_inquiry")
        sm.transition("inquiry_answered")
        assert sm.current_state == ConfirmationState.PENDING
    
    def test_invalid_transition(self):
        """测试非法转移"""
        sm = ConfirmationStateMachine()
        # IDLE 不能直接 user_confirm
        with pytest.raises(InvalidTransitionError):
            sm.transition("user_confirm")
    
    def test_can_transition(self):
        """测试转移检查"""
        sm = ConfirmationStateMachine()
        assert sm.can_transition("trigger_confirmation")
        assert not sm.can_transition("user_confirm")
```

#### 测试事件检测

```python
# tests/test_confirmation_event_detector.py

import pytest
from core.policy.confirmation import EventDetector


@pytest.fixture
def detector():
    return EventDetector()


@pytest.fixture
def confirmation_ctx():
    return {
        "intent": "change_package",
        "parameters": {
            "new_package_name": "无限套餐",
            "phone": "13800000000"
        }
    }


class TestEventDetector:
    """测试事件检测"""
    
    def test_pure_confirmation(self, detector, confirmation_ctx):
        """测试纯确认词"""
        cases = ["确认", "确定", "是的", "好的", "可以"]
        for text in cases:
            event = detector.detect(text, confirmation_ctx)
            assert event == "user_confirm"
    
    def test_pure_cancellation(self, detector, confirmation_ctx):
        """测试纯取消词"""
        cases = ["取消", "不要", "算了", "不办"]
        for text in cases:
            event = detector.detect(text, confirmation_ctx)
            assert event == "user_deny"
    
    def test_related_inquiry(self, detector, confirmation_ctx):
        """测试相关咨询"""
        cases = [
            "先介绍下无限套餐",
            "无限套餐价格多少",
            "套餐包含什么"
        ]
        for text in cases:
            event = detector.detect(text, confirmation_ctx)
            assert event == "user_inquiry"
    
    def test_new_topic(self, detector, confirmation_ctx):
        """测试新话题"""
        cases = [
            "查询我的余额",
            "我要查流量使用",
            "帮我看看当前套餐"
        ]
        for text in cases:
            event = detector.detect(text, confirmation_ctx)
            assert event == "user_new_topic"
    
    def test_consultation_not_confirmation(self, detector, confirmation_ctx):
        """测试咨询不被误判（重要）"""
        cases = [
            "办理流程",
            "怎么办理",
            "需要什么条件"
        ]
        for text in cases:
            event = detector.detect(text, confirmation_ctx)
            # 应该被识别为咨询或新话题，而不是确认
            assert event != "user_confirm"
```

### 7.2 集成测试

```python
# tests/test_confirmation_flow.py

import pytest
from core.chatbot_policy import TelecomChatbotPolicy


@pytest.fixture
def chatbot():
    return TelecomChatbotPolicy()


class TestConfirmationFlow:
    """测试完整确认流程"""
    
    def test_simple_confirmation(self, chatbot):
        """测试简单确认"""
        sid = "test_simple"
        
        # 轮1: 查询套餐
        r1 = chatbot.chat("有哪些套餐", sid)
        assert "套餐" in r1["response"]
        
        # 轮2: 办理套餐
        r2 = chatbot.chat("办理经济套餐，手机号13800000000", sid)
        assert r2.get("requires_confirmation") == True
        
        # 轮3: 确认
        r3 = chatbot.chat("确认办理", sid)
        assert r3.get("requires_confirmation") == False
        assert ("成功" in r3["response"] or "生效" in r3["response"])
    
    def test_confirmation_with_inquiry(self, chatbot):
        """测试确认中咨询（核心）"""
        sid = "test_inquiry"
        
        # 轮1: 办理套餐
        r1 = chatbot.chat("办理无限套餐，手机号13800000000", sid)
        assert r1.get("requires_confirmation") == True
        
        # 轮2: 咨询（关键）
        r2 = chatbot.chat("那先介绍下无限套餐信息", sid)
        assert r2.get("requires_confirmation") == True  # 🔥 仍需确认
        assert "无限套餐" in r2["response"]
        assert ("提醒" in r2["response"] or "💡" in r2["response"])
        
        # 轮3: 确认
        r3 = chatbot.chat("确认办理", sid)
        assert r3.get("requires_confirmation") == False
        assert ("成功" in r3["response"] or "生效" in r3["response"])
    
    def test_confirmation_cancelled(self, chatbot):
        """测试取消"""
        sid = "test_cancel"
        
        # 轮1: 办理
        r1 = chatbot.chat("办理无限套餐，手机号13800000000", sid)
        assert r1.get("requires_confirmation") == True
        
        # 轮2: 取消
        r2 = chatbot.chat("算了不办了", sid)
        assert r2.get("requires_confirmation") == False
        assert "取消" in r2["response"]
    
    def test_new_topic_clears_confirmation(self, chatbot):
        """测试新话题清除确认态"""
        sid = "test_new"
        
        # 轮1: 办理
        r1 = chatbot.chat("办理无限套餐，手机号13800000000", sid)
        assert r1.get("requires_confirmation") == True
        
        # 轮2: 新话题
        r2 = chatbot.chat("查询我的流量使用情况", sid)
        assert r2.get("requires_confirmation") == False
        assert ("流量" in r2["response"] or "查询" in r2["response"])
```

### 7.3 手动测试清单

| 场景 | 输入序列 | 期望输出 | 通过? |
|------|---------|---------|-------|
| 简单确认 | 1. 办理经济套餐<br>2. 确认 | 办理成功 | ☐ |
| 简单取消 | 1. 办理经济套餐<br>2. 取消 | 已取消 | ☐ |
| 确认中咨询 | 1. 办理无限套餐<br>2. 介绍下<br>3. 确认 | 回答+提醒→成功 | ☐ |
| 新话题 | 1. 办理经济套餐<br>2. 查询余额 | 清除确认态 | ☐ |
| 咨询不误判 | 1. 办理经济套餐<br>2. 办理流程 | 回答流程+保持确认 | ☐ |
| 超时 | 1. 办理经济套餐<br>2. (等6分钟)<br>3. 确认 | 提示超时 | ☐ |
| 多次咨询 | 1. 办理无限套餐<br>2. 价格多少<br>3. 包含什么<br>4. 确认 | 全部回答+成功 | ☐ |

---

## 八、上线计划

### 8.1 开发阶段（Week 1-2.5）

#### Week 1: 状态机框架

**Day 1-2**
- [ ] 创建目录结构
- [ ] 实现状态机核心代码
- [ ] 编写状态机单元测试

**Day 3-4**
- [ ] 实现事件检测器
- [ ] 编写事件检测单元测试

**Day 5**
- [ ] 实现确认处理器
- [ ] 整合状态机 + 事件检测

#### Week 2: 集成与完善

**Day 1-2**
- [ ] 修改 chatbot_policy.py
- [ ] 添加响应构建方法
- [ ] 集成测试

**Day 3-4**
- [ ] 完善边界case处理
- [ ] 优化日志和异常处理
- [ ] 手动测试

**Day 5**
- [ ] Bug修复
- [ ] 代码Review

#### Week 2.5: 测试优化

**Day 1-2**
- [ ] 完整测试套件
- [ ] 边界case测试
- [ ] 压力测试

**Day 3**
- [ ] 文档完善
- [ ] 部署准备

### 8.2 上线阶段（Week 3）

#### 灰度发布

**Day 1**
- [ ] 10%流量灰度
- [ ] 监控关键指标
- [ ] 收集Badcase

**Day 2**
- [ ] 分析灰度数据
- [ ] 30%流量

**Day 3**
- [ ] 50%流量

**Day 4**
- [ ] 100%全量发布

**Day 5**
- [ ] 监控稳定性
- [ ] 总结优化

### 8.3 监控指标

| 指标 | 目标值 | 说明 |
|------|-------|------|
| 确认成功率 | ≥ 85% | 用户确认 / 总确认请求 |
| 取消率 | < 10% | 用户取消 / 总确认请求 |
| 超时率 | < 5% | 超时 / 总确认请求 |
| 咨询识别准确率 | ≥ 85% | 正确识别咨询 / 总咨询 |
| 误判率 | < 3% | "办理流程"等误判 |
| 平均确认时长 | < 15s | 从确认请求到用户确认 |

### 8.4 回滚机制

```python
# config/settings.py
CONFIRMATION_STATE_MACHINE_ENABLED = True  # 状态机开关

# chatbot_policy.py
if settings.CONFIRMATION_STATE_MACHINE_ENABLED:
    # 新逻辑（状态机）
    result = self.confirmation_handler.handle(...)
else:
    # 旧逻辑（兜底）
    result = self._handle_confirmation_old(...)
```

---

## 九、常见问题

### Q1: 状态机和规则的关系是什么？

**A**: 互补关系，不是对立关系。
- **状态机**：架构层，定义有哪些状态、如何转移
- **规则**：算法层，判断应该转移到哪个状态

### Q2: 如何调整话题相关性阈值？

**A**: 修改 `event_detector.py` 中的评分规则：
```python
# 当前阈值
is_related = score >= 0.5

# 调整建议：
# - 提高到 0.6：减少误判
# - 降低到 0.4：提高召回
```

### Q3: 如何添加新状态？

**A**: 三步完成：
1. 在 `ConfirmationState` 添加枚举值
2. 在 `STATE_TRANSITIONS` 添加转移规则
3. 在 `ConfirmationHandler` 添加处理方法

### Q4: 如何处理多次咨询？

**A**: 已内置支持，状态机会记录咨询历史。
可以设置上限：
```python
if context["inquiry_count"] >= 3:
    return "您已咨询多次，请明确是否确认"
```

### Q5: 如何升级到混合算法？

**A**: 只需修改事件检测器：
```python
class EventDetector:
    def detect(self, user_input, context):
        # 优先级1: 规则快速路径
        if rule_result.confidence > 0.9:
            return rule_result
        
        # 优先级2: 模型分类（新增）
        if model_result.confidence > 0.8:
            return model_result
        
        # 优先级3: LLM兜底（新增）
        return llm_classify(...)
```

---

## 十、总结

### 10.1 方案优势

✅ **架构清晰**：状态机提供结构，规则提供实现  
✅ **职责分离**：状态管理和事件检测独立  
✅ **易于扩展**：添加新状态独立修改  
✅ **便于测试**：状态转移可单独测试  
✅ **可维护性高**：代码组织清晰  
✅ **可演进**：算法层可独立升级  

### 10.2 技术亮点

1. **状态机 + 规则结合**：发挥各自优势
2. **分层设计**：架构层、算法层、业务层分离
3. **话题相关性算法**：多维度评分判断
4. **插入式对话支持**：咨询不影响确认流程

### 10.3 预期效果

| 指标 | 当前 | 目标 | 说明 |
|------|------|------|------|
| 准确率 | ~80% | 88-92% | 提升 8-12% |
| 误判率 | ~5% | < 3% | 降低 2% |
| 可维护性 | 中 | 高 | 代码结构优化 |
| 扩展性 | 中 | 高 | 状态机架构 |

### 10.4 后续优化

**短期（1-3个月）**
- 收集Badcase，优化规则
- A/B测试阈值参数

**中期（3-6个月）**
- 引入小模型处理边界case
- 构建混合算法

**长期（6个月+）**
- LLM兜底
- 多轮嵌套确认
- 情感理解

---

**文档版本**: v2.0  
**最后更新**: 2025-01-XX  
**设计方案**: 状态机 + 规则增强  
**维护者**: [您的名字]
