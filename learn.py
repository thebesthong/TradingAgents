"""
learn.py — 单独运行 TradingAgents 中任意一个 Agent 的示例脚本。

可以直接运行一个 Agent 并查看其输出，无需启动完整的 LangGraph 流水线。

用法：
    python learn.py

运行前需设置环境变量（如 OPENAI_API_KEY），或修改下方 AGENT_CONFIG。
"""

import os
from langchain_core.messages import HumanMessage

# ============================================================
# 1. 选择要运行的 Agent 和配置
# ============================================================

# 可选 Agent 类型:
#   "market"        — Market Analyst (技术分析，需要工具调用)
#   "sentiment"     — Sentiment Analyst (情绪分析，数据预取，不需要工具调用)
#   "news"          — News Analyst (新闻分析，需要工具调用)
#   "fundamentals"  — Fundamentals Analyst (基本面分析，需要工具调用)
#   "trader"        — Trader (交易决策，需要 Research Plan 输入)
#   "bull"          — Bull Researcher (多头辩论，需要分析师报告)
#   "bear"          — Bear Researcher (空头辩论，需要分析师报告)

AGENT_TO_RUN = "market"       # <-- 修改这里切换 Agent

# 分析参数
TICKER = "AAPL"               # 股票代码
TRADE_DATE = "2026-06-20"     # 分析日期

# LLM 配置
LLM_PROVIDER = "openai"       # openai / google / anthropic / deepseek 等
LLM_MODEL = "gpt-4.1-mini"    # 模型名称

# ============================================================
# 2. 初始化 LLM
# ============================================================

from tradingagents.llm_clients import create_llm_client
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG

# 应用默认配置（数据缓存路径、供应商配置等）
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = LLM_PROVIDER
config["deep_think_llm"] = LLM_MODEL
config["quick_think_llm"] = LLM_MODEL
set_config(config)

# 确保缓存目录存在
os.makedirs(config["data_cache_dir"], exist_ok=True)

# 创建 LLM 客户端
client = create_llm_client(
    provider=LLM_PROVIDER,
    model=LLM_MODEL,
)
llm = client.get_llm()
print(f"[OK] LLM 已初始化: {LLM_PROVIDER} / {LLM_MODEL}")

# ============================================================
# 3. 解析标的身份（防止 LLM 幻觉）
# ============================================================

from tradingagents.agents.utils.agent_utils import (
    resolve_instrument_identity,
    build_instrument_context,
)

identity = resolve_instrument_identity(TICKER)
instrument_context = build_instrument_context(TICKER, "stock", identity)
print(f"[OK] 标的身份已解析: {TICKER} → {identity.get('name', TICKER)}")

# ============================================================
# 4. 构建最小 State 并运行 Agent
# ============================================================

# 所有 Agent 节点的通用最小 State
state = {
    "messages": [HumanMessage(content=f"Analyze {TICKER}")],
    "company_of_interest": TICKER,
    "trade_date": TRADE_DATE,
    "asset_type": "stock",
    "instrument_context": instrument_context,
}


def run_market_analyst():
    """运行 Market Analyst — 技术分析，需要多轮工具调用"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst
    from tradingagents.agents.utils.agent_utils import (
        get_stock_data,
        get_indicators,
        get_verified_market_snapshot,
    )

    agent = create_market_analyst(llm)

    # 第一轮：LLM 决定调用工具
    print("\n[Round 1] Market Analyst 正在分析...")
    result = agent(state)

    # 如果 LLM 返回了 tool_calls，手动执行工具并继续
    last_msg = result["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []

    round_num = 1
    while tool_calls:
        round_num += 1
        print(f"\n[Round {round_num}] 执行 {len(tool_calls)} 个工具调用...")

        tool_results = []
        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            print(f"  → 调用 {tool_name}({tool_args})")

            # 执行工具
            if tool_name == "get_stock_data":
                output = get_stock_data.func(**tool_args)
            elif tool_name == "get_indicators":
                output = get_indicators.func(**tool_args)
            elif tool_name == "get_verified_market_snapshot":
                output = get_verified_market_snapshot.func(**tool_args)
            else:
                output = f"Unknown tool: {tool_name}"

            from langchain_core.messages import ToolMessage
            tool_results.append(
                ToolMessage(content=str(output), tool_call_id=tc["id"])
            )

        # 将工具结果追加到消息列表，再次调用 Agent
        state["messages"] = state["messages"] + [result["messages"][-1]] + tool_results
        result = agent(state)

        last_msg = result["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", []) or []

    print("\n" + "=" * 60)
    print("Market Analyst 报告:")
    print("=" * 60)
    print(result.get("market_report", last_msg.content))
    return result


def run_sentiment_analyst():
    """运行 Sentiment Analyst — 情绪分析，数据预取，无需工具调用"""
    from tradingagents.agents.analysts.sentiment_analyst import create_sentiment_analyst

    agent = create_sentiment_analyst(llm)

    print("\nSentiment Analyst 正在分析（预取 yfinance news + StockTwits + Reddit）...")
    result = agent(state)

    print("\n" + "=" * 60)
    print("Sentiment Analyst 报告:")
    print("=" * 60)
    print(result.get("sentiment_report", ""))
    return result


def run_news_analyst():
    """运行 News Analyst — 新闻/宏观分析，需要多轮工具调用"""
    from tradingagents.agents.analysts.news_analyst import create_news_analyst
    from tradingagents.agents.utils.agent_utils import (
        get_news,
        get_global_news,
        get_macro_indicators,
        get_prediction_markets,
    )

    agent = create_news_analyst(llm)

    print("\n[Round 1] News Analyst 正在分析...")
    result = agent(state)

    last_msg = result["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []

    round_num = 1
    while tool_calls:
        round_num += 1
        print(f"\n[Round {round_num}] 执行 {len(tool_calls)} 个工具调用...")

        tool_results = []
        tool_map = {
            "get_news": get_news.func,
            "get_global_news": get_global_news.func,
            "get_macro_indicators": get_macro_indicators.func,
            "get_prediction_markets": get_prediction_markets.func,
        }

        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            print(f"  → 调用 {tool_name}(...)")

            func = tool_map.get(tool_name)
            if func:
                output = func(**tool_args)
            else:
                output = f"Unknown tool: {tool_name}"

            from langchain_core.messages import ToolMessage
            tool_results.append(
                ToolMessage(content=str(output), tool_call_id=tc["id"])
            )

        state["messages"] = state["messages"] + [result["messages"][-1]] + tool_results
        result = agent(state)

        last_msg = result["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", []) or []

    print("\n" + "=" * 60)
    print("News Analyst 报告:")
    print("=" * 60)
    print(result.get("news_report", last_msg.content))
    return result


def run_fundamentals_analyst():
    """运行 Fundamentals Analyst — 基本面分析，需要多轮工具调用"""
    from tradingagents.agents.analysts.fundamentals_analyst import create_fundamentals_analyst
    from tradingagents.agents.utils.agent_utils import (
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    )

    agent = create_fundamentals_analyst(llm)

    print("\n[Round 1] Fundamentals Analyst 正在分析...")
    result = agent(state)

    last_msg = result["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", []) or []

    round_num = 1
    while tool_calls:
        round_num += 1
        print(f"\n[Round {round_num}] 执行 {len(tool_calls)} 个工具调用...")

        tool_results = []
        tool_map = {
            "get_fundamentals": get_fundamentals.func,
            "get_balance_sheet": get_balance_sheet.func,
            "get_cashflow": get_cashflow.func,
            "get_income_statement": get_income_statement.func,
        }

        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            print(f"  → 调用 {tool_name}(...)")

            func = tool_map.get(tool_name)
            if func:
                output = func(**tool_args)
            else:
                output = f"Unknown tool: {tool_name}"

            from langchain_core.messages import ToolMessage
            tool_results.append(
                ToolMessage(content=str(output), tool_call_id=tc["id"])
            )

        state["messages"] = state["messages"] + [result["messages"][-1]] + tool_results
        result = agent(state)

        last_msg = result["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", []) or []

    print("\n" + "=" * 60)
    print("Fundamentals Analyst 报告:")
    print("=" * 60)
    print(result.get("fundamentals_report", last_msg.content))
    return result


def run_trader():
    """运行 Trader — 需要模拟 Research Manager 的输出作为输入"""
    from tradingagents.agents.trader.trader import create_trader

    # Trader 需要 Research Manager 的投资计划作为输入
    # 这里模拟一个 Research Plan
    fake_investment_plan = (
        "**Recommendation**: Buy\n\n"
        "**Rationale**: The bull case is strong based on technical indicators "
        "showing an uptrend, positive sentiment across social media, and solid "
        "fundamentals with revenue growth. The bear case raises valid concerns "
        "about valuation, but the growth trajectory justifies the premium.\n\n"
        "**Strategic Actions**: Enter a long position at current market price, "
        "set stop-loss at 5% below entry, target 10% upside in 3 months."
    )

    state["investment_plan"] = fake_investment_plan

    agent = create_trader(llm)
    print("\nTrader 正在生成交易方案...")
    result = agent(state)

    print("\n" + "=" * 60)
    print("Trader 交易方案:")
    print("=" * 60)
    print(result.get("trader_investment_plan", ""))
    return result


def run_bull_researcher():
    """运行 Bull Researcher — 需要模拟分析师报告作为输入"""
    from tradingagents.agents.researchers.bull_researcher import create_bull_researcher

    # Bull Researcher 需要分析师报告，这里做简单模拟
    state["market_report"] = "Market report: AAPL shows bullish trend with SMA crossover."
    state["sentiment_report"] = "Sentiment: Bullish, score 7.5/10."
    state["news_report"] = "News: Positive macro outlook, no major risks."
    state["fundamentals_report"] = "Fundamentals: Strong revenue growth, healthy balance sheet."
    state["investment_debate_state"] = {
        "bull_history": "",
        "bear_history": "",
        "history": "",
        "current_response": "Bull",
        "judge_decision": "",
        "count": 0,
    }

    agent = create_bull_researcher(llm)
    print("\nBull Researcher 正在构建多头论点...")
    result = agent(state)

    print("\n" + "=" * 60)
    print("Bull Researcher 论点:")
    print("=" * 60)
    print(result["messages"][-1].content)
    return result


def run_bear_researcher():
    """运行 Bear Researcher — 需要模拟分析师报告作为输入"""
    from tradingagents.agents.researchers.bear_researcher import create_bear_researcher

    state["market_report"] = "Market report: AAPL shows bullish trend with SMA crossover."
    state["sentiment_report"] = "Sentiment: Bullish, score 7.5/10."
    state["news_report"] = "News: Positive macro outlook, no major risks."
    state["fundamentals_report"] = "Fundamentals: Strong revenue growth, healthy balance sheet."
    state["investment_debate_state"] = {
        "bull_history": "Bull: AAPL has strong growth potential...",
        "bear_history": "",
        "history": "",
        "current_response": "Bear",
        "judge_decision": "",
        "count": 1,
    }

    agent = create_bear_researcher(llm)
    print("\nBear Researcher 正在构建空头论点...")
    result = agent(state)

    print("\n" + "=" * 60)
    print("Bear Researcher 论点:")
    print("=" * 60)
    print(result["messages"][-1].content)
    return result


# ============================================================
# 5. 主入口
# ============================================================

AGENT_RUNNERS = {
    "market":       ("Market Analyst (技术分析)", run_market_analyst),
    "sentiment":    ("Sentiment Analyst (情绪分析)", run_sentiment_analyst),
    "news":         ("News Analyst (新闻分析)", run_news_analyst),
    "fundamentals": ("Fundamentals Analyst (基本面分析)", run_fundamentals_analyst),
    "trader":       ("Trader (交易决策)", run_trader),
    "bull":         ("Bull Researcher (多头研究员)", run_bull_researcher),
    "bear":         ("Bear Researcher (空头研究员)", run_bear_researcher),
}

if __name__ == "__main__":
    print("=" * 60)
    print("  TradingAgents — 单 Agent 运行示例")
    print("=" * 60)

    if AGENT_TO_RUN not in AGENT_RUNNERS:
        print(f"未知 Agent: {AGENT_TO_RUN}")
        print(f"可选: {', '.join(AGENT_RUNNERS.keys())}")
        exit(1)

    name, runner = AGENT_RUNNERS[AGENT_TO_RUN]
    print(f"\nAgent: {name}")
    print(f"标的: {TICKER}")
    print(f"日期: {TRADE_DATE}")
    print(f"模型: {LLM_PROVIDER} / {LLM_MODEL}")

    runner()