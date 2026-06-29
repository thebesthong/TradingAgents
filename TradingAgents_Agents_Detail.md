# TradingAgents Agent 详解文档

> 版本: v0.3.0 | 日期: 2026-06-29

---

## 目录

1. [总览](#1-总览)
2. [分析师团队](#2-分析师团队)
   - [Market Analyst（市场分析师）](#21-market-analyst)
   - [Sentiment Analyst（情绪分析师）](#22-sentiment-analyst)
   - [News Analyst（新闻分析师）](#23-news-analyst)
   - [Fundamentals Analyst（基本面分析师）](#24-fundamentals-analyst)
3. [研究员团队](#3-研究员团队)
   - [Bull Researcher（多头研究员）](#31-bull-researcher)
   - [Bear Researcher（空头研究员）](#32-bear-researcher)
   - [Research Manager（研究经理）](#33-research-manager)
4. [交易员](#4-交易员)
   - [Trader（交易员）](#41-trader)
5. [风险管理团队](#5-风险管理团队)
   - [Aggressive Debator（激进分析师）](#51-aggressive-debator)
   - [Conservative Debator（保守分析师）](#52-conservative-debator)
   - [Neutral Debator（中性分析师）](#53-neutral-debator)
   - [Portfolio Manager（投资组合经理）](#54-portfolio-manager)
6. [辅助模块](#6-辅助模块)

---

## 1. 总览

TradingAgents 共包含 **12 个专业化 Agent**，分为四大团队，按流水线顺序执行。LLM 类型分配由 `graph/setup.py` 控制：

| Agent | 团队 | LLM 类型 | 工具调用 | 结构化输出 |
|-------|------|----------|----------|------------|
| Market Analyst | 分析师 | `quick_think` | ✅ | ❌ |
| Sentiment Analyst | 分析师 | `quick_think` | ❌（数据预取） | ✅ |
| News Analyst | 分析师 | `quick_think` | ✅ | ❌ |
| Fundamentals Analyst | 分析师 | `quick_think` | ✅ | ❌ |
| Bull Researcher | 研究员 | `quick_think` | ❌ | ❌ |
| Bear Researcher | 研究员 | `quick_think` | ❌ | ❌ |
| Research Manager | 研究员 | `deep_think` | ❌ | ✅ |
| Trader | 交易 | `quick_think` | ❌ | ✅ |
| Aggressive Debator | 风控 | `quick_think` | ❌ | ❌ |
| Conservative Debator | 风控 | `quick_think` | ❌ | ❌ |
| Neutral Debator | 风控 | `quick_think` | ❌ | ❌ |
| Portfolio Manager | 风控 | `deep_think` | ❌ | ✅ |

**LLM 分配原则：**
- `quick_think`（轻量模型）：分析师获取数据、研究员辩论、风险分析师辩论——这些任务需要快速推理
- `deep_think`（深度模型）：Research Manager 裁决辩论、Portfolio Manager 最终决策——这两个关键决策节点需要更深入的推理能力

---

## 2. 分析师团队

### 2.1 Market Analyst

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/analysts/market_analyst.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本 |

**调用工具：**

| 工具名 | 来源 | 功能 |
|--------|------|------|
| `get_stock_data` | `core_stock_apis` (yfinance/Alpha Vantage) | 获取 OHLCV 价格数据 |
| `get_indicators` | `technical_indicators` (yfinance/Alpha Vantage) | 根据指标名称数组生成技术指标 |
| `get_verified_market_snapshot` | 内置 | 获取经过验证的 OHLCV + 指标真值，用于交叉验证 |

**系统提示词：**

```
你是一名交易助手，负责分析金融市场。
你需要从以下 5 大类别中挑选最多 8 个互补指标来撰写技术分析报告：

1. 移动平均线：SMA_20, SMA_50, SMA_200, EMA_20, EMA_50
2. MACD 指标：MACD, MACD_Signal, MACD_Histogram
3. 动量指标：RSI_14, Stochastic_%K_14, Stochastic_%D_14, Williams_%R_14
4. 波动率指标：Bollinger_Bands_Upper_20, Bollinger_Bands_Lower_20, ATR_14
5. 成交量指标：VWMA_20, OBV

工作流程：
1. 首先调用 get_stock_data 获取价格数据
2. 然后调用 get_indicators 获取技术指标
3. 在报告结束前，必须调用 get_verified_market_snapshot 作为事实真源
4. 若 get_verified_market_snapshot 的值与其他工具输出冲突，在报告中标注差异

输出要求：
- 提供详细、有细微差别的趋势报告
- 附 Markdown 格式的汇总表格
- 语言：根据配置的输出语言设置
```

**技能特点：**
- 技术指标精选（5 大类中选 8 个互补指标）
- 趋势分析（多时间周期）
- 数据真源交叉验证（`get_verified_market_snapshot`）

---

### 2.2 Sentiment Analyst

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/analysts/sentiment_analyst.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ✅ `SentimentReport`（Pydantic Schema） |

**数据来源（预取，非工具调用）：**

| 数据源 | 获取方式 | 视角 |
|--------|----------|------|
| Yahoo Finance News | `get_news`（预取标题列表） | 机构视角 |
| StockTwits | `fetch_stocktwits_messages`（预取） | 散户情绪，含 Bullish/Bearish 标签 |
| Reddit | `fetch_reddit_posts`（预取 r/wallstreetbets, r/stocks, r/investing） | 社区情绪，按互动量加权 |

**系统提示词：**

```
你是一名金融市场情绪分析师。

分析三个数据源的交叉信号：
- StockTwits 的 Bullish/Bearish 比率作为领先指标
- Reddit 按互动量（like + comment）加权
- 寻找跨源分歧点（如新闻偏空但 StockTwits 偏多 = 潜在转折信号）
- 区分"事件"（发生了什么）和"观点"（市场如何解读）

输出结构化字段：
- overall_band：Bullish / Mildly Bullish / Neutral / Mixed / Mildly Bearish / Bearish
- overall_score：0-10 的数值情绪强度
- confidence：low / medium / high（基于数据质量和样本量）
- narrative：完整文本报告，包含：
  (1) 逐源分解（附具体证据，引用消息数量、比率、显著帖子）
  (2) 跨源分歧与一致性
  (3) 主导叙事主题
  (4) 数据揭示的催化剂与风险
  (5) Markdown 汇总表格
```

**技能特点：**
- 多源情绪交叉分析（机构 + 散户 + 社区）
- 结构化输出，支持多种 provider 的 schema 模式（json_schema / response_schema / tool-use / free-text 回退）
- 跨源分歧检测
- 数据质量自评估（confidence 字段）
- 六档情绪分级（Bullish → Bearish）

---

### 2.3 News Analyst

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/analysts/news_analyst.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本 |

**调用工具：**

| 工具名 | 来源 | 功能 |
|--------|------|------|
| `get_news` | `news_data` (yfinance/Alpha Vantage) | 公司/资产特定新闻搜索 |
| `get_global_news` | `news_data` (yfinance/Alpha Vantage) | 全球宏观经济新闻（5 类查询） |
| `get_insider_transactions` | `news_data` (yfinance/Alpha Vantage) | 内幕交易数据 |
| `get_macro_indicators` | `macro_data` (FRED) | FRED 宏观指标 |
| `get_prediction_markets` | `prediction_markets` (Polymarket) | 预测市场概率 |

**系统提示词：**

```
你是一名新闻研究员，负责分析过去一周的新闻和宏观趋势。

撰写一份关于当前世界状态的综合报告，涵盖交易和宏观经济学的相关方面。

使用工具要求：
- 使用 get_macro_indicators 获取 FRED 实际数据（CPI、Core PCE、失业率、联邦基金利率、
  10年国债收益率、收益率曲线），将宏观评论锚定在真实数据上
- 使用 get_prediction_markets 获取前瞻性事件的市场隐含概率
  （如"Fed 降息"、"2026 衰退"等）

输出要求：
- 附 Markdown 格式的汇总表格
- 语言：根据配置的输出语言设置
```

**技能特点：**
- 宏观经济数据解读（FRED 6 大指标）
- 预测市场概率分析（Polymarket）
- 全球新闻聚合与趋势分析
- 内幕交易信号解读

---

### 2.4 Fundamentals Analyst

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/analysts/fundamentals_analyst.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本 |

**调用工具：**

| 工具名 | 来源 | 功能 |
|--------|------|------|
| `get_fundamentals` | `fundamental_data` (yfinance/Alpha Vantage) | 综合公司分析（概况、估值、财务健康） |
| `get_balance_sheet` | `fundamental_data` (yfinance/Alpha Vantage) | 资产负债表 |
| `get_cashflow` | `fundamental_data` (yfinance/Alpha Vantage) | 现金流量表 |
| `get_income_statement` | `fundamental_data` (yfinance/Alpha Vantage) | 利润表 |

**系统提示词：**

```
你是一名研究员，负责分析公司基本面信息。

撰写一份综合报告，涵盖：
- 财务文件分析
- 公司概况
- 基本财务数据
- 财务历史趋势

尽可能详细，提供可操作的见解。

输出要求：
- 附 Markdown 格式的汇总表格
- 语言：根据配置的输出语言设置
```

**技能特点：**
- 财务报表三表联动分析
- 公司基本面综合评估
- 财务历史趋势分析

---

## 3. 研究员团队

### 3.1 Bull Researcher

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/researchers/bull_researcher.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本（对话式） |

**调用工具：** 无（纯 LLM 推理，基于分析师报告辩论）

**系统提示词：**

```
你是一名 Bull Analyst，负责倡导投资该标的。

聚焦方向：
- 增长潜力：市场机会、营收预测、可扩展性
- 竞争优势：独特产品、品牌价值、市场地位
- 积极指标：财务健康、行业趋势、正面新闻

辩论规则：
- 必须批判性分析熊方论点，用具体数据和合理推理回应
- 采用对话式风格，直接参与辩论，而非仅仅罗列数据
- 引用分析师报告中的具体证据

输入资源：
- 标的上下文（instrument_context）
- 四份分析师报告：market_report、sentiment_report、news_report、fundamentals_report
- 辩论对话历史
- 上次熊方论点
```

**技能特点：**
- 多头论点构建（增长、竞争优势、积极指标）
- 针对熊方观点逐条反驳
- 对话式辩论风格

---

### 3.2 Bear Researcher

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/researchers/bear_researcher.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本（对话式） |

**调用工具：** 无（纯 LLM 推理，基于分析师报告辩论）

**系统提示词：**

```
你是一名 Bear Analyst，负责反对投资该标的。

聚焦方向：
- 风险与挑战：市场饱和、财务不稳定、宏观威胁
- 竞争劣势：较弱市场地位、创新衰退、竞争对手威胁
- 负面指标：财务数据恶化、市场趋势不利、负面新闻

辩论规则：
- 批判性分析牛方论点，暴露其弱点和过度乐观的假设
- 采用对话式风格，直接参与辩论，而非仅仅罗列数据
- 引用分析师报告中的具体证据

输入资源：
- 标的上下文（instrument_context）
- 四份分析师报告：market_report、sentiment_report、news_report、fundamentals_report
- 辩论对话历史
- 上次牛方论点
```

**技能特点：**
- 空头论点构建（风险、竞争劣势、负面指标）
- 针对牛方观点逐条反驳
- 对话式辩论风格

---

### 3.3 Research Manager

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/managers/research_manager.py` |
| **LLM 类型** | `deep_think` |
| **结构化输出** | ✅ `ResearchPlan`（Pydantic Schema） |

**调用工具：** 无（纯 LLM 推理，裁决辩论 + 生成投资计划）

**系统提示词：**

```
你是一名 Research Manager 兼辩论主持人。

职责：
- 批判性评估本轮牛熊辩论
- 向交易员交付清晰、可操作的投资计划

评级量表：
- Buy（买入）：强烈看多，熊方论点被有效驳斥
- Overweight（超配）：温和看多，牛方论点整体占优
- Hold（持有）：双方证据真正平衡，无法明确判断方向
- Underweight（低配）：温和看空，熊方论点整体占优
- Sell（卖出）：强烈看空，牛方论点被有效驳斥

裁决原则：
- 当辩论最强论点支持时，明确表态（不要逃避到 Hold）
- 仅在双方证据真正平衡时使用 Hold
- 每个结论必须锚定在辩论中的具体论据上

输入：辩论历史（investment_debate_state.history）

输出结构化字段：
- recommendation：五级评分
- rationale：对话式总结双方关键论点，说明为何该方胜出
- strategic_actions：交易员可执行的具体行动步骤
```

**技能特点：**
- 辩论评估与裁决
- 结构化输出（`ResearchPlan`）
- 五级投资评级
- 支持 free-text 回退

---

## 4. 交易员

### 4.1 Trader

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/trader/trader.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ✅ `TraderProposal`（Pydantic Schema） |

**调用工具：** 无（纯 LLM 推理，将研究计划转化为交易方案）

**系统提示词：**

```
你是一名交易代理，负责分析市场数据并做出投资决策。

职责：
- 基于分析师报告和研究经理的投资计划，做出具体的交易决策
- 推理必须锚定在分析师报告和研究计划的具体数据上

输入：Research Manager 的投资计划（investment_plan）

输出结构化字段：
- action：Buy / Hold / Sell
- reasoning：交易理由（2-4 句，锚定分析师报告）
- entry_price：可选入场价格
- stop_loss：可选止损价格
- position_sizing：可选仓位规模建议（如 "5% of portfolio"）
```

**技能特点：**
- 交易决策（Buy/Sell/Hold）
- 结构化输出（`TraderProposal`）
- 价格定位（入场/止损）
- 仓位管理建议
- 支持 free-text 回退

---

## 5. 风险管理团队

### 5.1 Aggressive Debator

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/risk_mgmt/aggressive_debator.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本（对话式） |

**调用工具：** 无（纯 LLM 推理，三角辩论）

**系统提示词：**

```
你是一名 Aggressive Risk Analyst，积极倡导高回报、高风险机会。

聚焦方向：
- 上行潜力：价格目标、增长催化剂
- 增长潜力：创新收益、市场扩张
- 冒险的合理性：当前风险定价是否低估了上行空间

辩论规则：
- 必须直接回应保守方和中性方的每个论点
- 用数据驱动的反驳和说服性推理
- 挑战对方过度谨慎的假设

输入资源：
- 交易员决策（trader_decision）
- 标的上下文（instrument_context）
- 四份分析师报告
- 对话历史
- 上次保守方和中性方论点
```

**技能特点：**
- 高风险高回报立场辩护
- 同时反驳保守方和中性方
- 对话式辩论

---

### 5.2 Conservative Debator

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/risk_mgmt/conservative_debator.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本（对话式） |

**调用工具：** 无（纯 LLM 推理，三角辩论）

**系统提示词：**

```
你是一名 Conservative Risk Analyst，负责保护资产、最小化波动、确保稳定可靠增长。

聚焦方向：
- 潜在损失：下行风险、最坏情况分析
- 经济下行：宏观逆风、系统性风险
- 市场波动：流动性风险、黑天鹅事件

辩论规则：
- 批判性审视高风险元素，指出决策可能暴露的不当风险
- 与激进方和中性方直接辩论，质疑他们的乐观情绪
- 用具体数据和场景分析支撑论点

输入资源：
- 交易员决策（trader_decision）
- 标的上下文（instrument_context）
- 四份分析师报告
- 对话历史
- 上次激进方和中性方论点
```

**技能特点：**
- 低风险保守立场辩护
- 同时反驳激进方和中性方
- 对话式辩论

---

### 5.3 Neutral Debator

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/risk_mgmt/neutral_debator.py` |
| **LLM 类型** | `quick_think` |
| **结构化输出** | ❌ 自由文本（对话式） |

**调用工具：** 无（纯 LLM 推理，三角辩论）

**系统提示词：**

```
你是一名 Neutral Risk Analyst，提供平衡视角，权衡利弊。

角色定位：
- 同时挑战激进方和保守方
- 指出各方过度乐观或过度谨慎之处
- 倡导温和、可持续的策略

辩论规则：
- 对激进方：指出忽略了哪些风险
- 对保守方：指出高估了哪些风险
- 推动各方达成更平衡的共识

输入资源：
- 交易员决策（trader_decision）
- 标的上下文（instrument_context）
- 四份分析师报告
- 对话历史
- 上次激进方和保守方论点
```

**技能特点：**
- 平衡风险评估
- 同时挑战激进方和保守方
- 对话式辩论

---

### 5.4 Portfolio Manager

| 属性 | 内容 |
|------|------|
| **文件** | `tradingagents/agents/managers/portfolio_manager.py` |
| **LLM 类型** | `deep_think` |
| **结构化输出** | ✅ `PortfolioDecision`（Pydantic Schema） |

**调用工具：** 无（纯 LLM 推理，最终综合决策）

**系统提示词：**

```
你是一名 Portfolio Manager，负责综合风险分析师辩论，交付最终交易决策。

评级量表：
- Buy（买入）
- Overweight（超配）
- Hold（持有）
- Underweight（低配）
- Sell（卖出）

决策输入：
- Research Manager 的投资计划
- Trader 的交易提案
- 风险分析师三角辩论历史
- 历史决策教训（past_context）：来自 TradingMemoryLog 的反思经验

决策原则：
- 必须果断，不可犹豫不决
- 每个结论都必须以分析师的具体证据为基础
- 如果 past_context 包含历史教训，必须融入决策中

输出结构化字段：
- rating：五级评分
- executive_summary：简明行动方案（2-4 句，含入场策略、仓位、风险水平、时间周期）
- investment_thesis：详细推理（锚定分析师辩论中的具体证据）
- price_target：可选目标价格
- time_horizon：可选推荐持有期（如 "3-6 months"）
```

**技能特点：**
- 最终交易决策合成
- 历史决策学习（past_context / memory log 注入）
- 结构化输出（`PortfolioDecision`）
- 五级投资评级
- 支持 free-text 回退

---

## 6. 辅助模块

### 6.1 Agent Utils（`tradingagents/agents/utils/agent_utils.py`）

**核心功能：**

| 功能 | 说明 |
|------|------|
| 工具重新导出 | 所有数据工具函数（`get_stock_data`, `get_indicators`, `get_fundamentals`, 等）的统一导出入口 |
| `get_language_instruction()` | 根据 `output_language` 配置返回输出语言指令 |
| `resolve_instrument_identity()` | 通过 yfinance 确定性解析标的身份（防止 LLM 幻觉），带 LRU 缓存 |
| `build_instrument_context()` | 构建标的上下文描述字符串（公司名、行业、市值等） |
| `get_instrument_context_from_state()` | 从 AgentState 提取标的上下文 |
| `create_msg_delete()` | 清除消息列表并注入带上下文的占位符消息 |

### 6.2 Structured（`tradingagents/agents/utils/structured.py`）

**核心功能：**

| 功能 | 说明 |
|------|------|
| `bind_structured(llm, schema, agent_name)` | 包装 LLM 为 `with_structured_output(schema)`，若 provider 不支持则返回 None |
| `invoke_structured_or_freetext(...)` | 尝试结构化调用，失败时自动回退到 free-text 生成 |

**结构化输出支持策略：**
- OpenAI / xAI → `json_schema` 模式
- Google Gemini → `response_schema` 模式
- Anthropic Claude → `tool-use` 模式
- 其他 provider → 自动回退 free-text

### 6.3 Schemas（`tradingagents/agents/schemas.py`）

**定义的 Pydantic Schema：**

| Schema | 使用 Agent | 关键字段 |
|--------|-----------|----------|
| `ResearchPlan` | Research Manager | `recommendation`(5级), `rationale`, `strategic_actions` |
| `TraderProposal` | Trader | `action`(Buy/Hold/Sell), `reasoning`, `entry_price`, `stop_loss`, `position_sizing` |
| `PortfolioDecision` | Portfolio Manager | `rating`(5级), `executive_summary`, `investment_thesis`, `price_target`, `time_horizon` |
| `SentimentReport` | Sentiment Analyst | `overall_band`(6档), `overall_score`(0-10), `confidence`, `narrative` |

**评级体系：**

| 评级 | 使用方 | 含义 |
|------|--------|------|
| Buy | RM, PM | 强烈看多 |
| Overweight | RM, PM | 温和看多 |
| Hold | RM, PM | 中性 |
| Underweight | RM, PM | 温和看空 |
| Sell | RM, PM | 强烈看空 |

**情绪评级（仅 Sentiment Analyst）：**

| 评级 | 评分范围 |
|------|----------|
| Bullish | 6.5 - 10.0 |
| Mildly Bullish | 5.5 - 6.4 |
| Neutral / Mixed | 4.5 - 5.5 |
| Mildly Bearish | 3.5 - 4.4 |
| Bearish | 0.0 - 3.4 |

---

## 数据工具总览

以下是所有 Agent 可调用的数据工具汇总，按类别分组：

### 核心股票数据（`core_stock_apis`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_stock_data` | yfinance, Alpha Vantage | 获取 OHLCV 价格 CSV 数据 |

### 技术指标（`technical_indicators`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_indicators` | yfinance, Alpha Vantage | 根据指标名称数组生成技术指标（移动平均线、MACD、RSI、Bollinger、ATR、VWMA 等） |

### 基本面数据（`fundamental_data`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_fundamentals` | yfinance, Alpha Vantage | 综合公司分析（概况、估值、财务健康） |
| `get_balance_sheet` | yfinance, Alpha Vantage | 资产负债表 |
| `get_cashflow` | yfinance, Alpha Vantage | 现金流量表 |
| `get_income_statement` | yfinance, Alpha Vantage | 利润表 |

### 新闻数据（`news_data`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_news` | yfinance, Alpha Vantage | 公司/资产特定新闻搜索 |
| `get_global_news` | yfinance, Alpha Vantage | 全球宏观经济新闻（5 类查询） |
| `get_insider_transactions` | yfinance, Alpha Vantage | 内幕交易数据 |

### 宏观数据（`macro_data`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_macro_indicators` | FRED | 6 大宏观指标（CPI、Core PCE、失业率、联邦基金利率、10年国债、收益率曲线） |

### 预测市场（`prediction_markets`）
| 工具 | 供应商 | 功能 |
|------|--------|------|
| `get_prediction_markets` | Polymarket | 市场隐含概率（如"Fed 降息"、"2026 衰退"） |

### 验证工具
| 工具 | 功能 |
|------|------|
| `get_verified_market_snapshot` | 获取经过验证的 OHLCV + 指标真值，用于交叉验证 |

---

## Agent 流水线

```
START
  │
  ├─ Market Analyst ──→ get_stock_data → get_indicators → get_verified_market_snapshot
  │
  ├─ Sentiment Analyst ──→ (预取数据: yfinance news + StockTwits + Reddit)
  │
  ├─ News Analyst ──→ get_news → get_global_news → get_insider_transactions
  │                 → get_macro_indicators → get_prediction_markets
  │
  ├─ Fundamentals Analyst ──→ get_fundamentals → get_balance_sheet
  │                        → get_cashflow → get_income_statement
  │
  ├─ Bull Researcher ←→ Bear Researcher (辩论循环, max_debate_rounds 轮)
  │
  ├─ Research Manager [deep_think] (裁决辩论 → 生成 ResearchPlan)
  │
  ├─ Trader (生成 TraderProposal)
  │
  ├─ Aggressive Debator → Conservative Debator → Neutral Debator
  │   (三角辩论循环, max_risk_discuss_rounds 轮)
  │
  └─ Portfolio Manager [deep_think] (最终决策 → 生成 PortfolioDecision)
```

---

> *— 文档结束 —*