"""
实测脚本 — 验证 CollectorAgent 真实采集链路

前置条件（《2.0-采集运行模式深度调研》结论）：
1. 电脑连手机**数据流量热点**（宽带 IP 已被 BOSS 标记）
2. 关闭 Clash/代理（code 37 与代理出口 IP 相关）
3. 专用 Chrome 已启动且已登录（第三方 scraper 放在仓库根 tools/ 下）：
   cd <repo>/tools/boss-zhipin-scraper
   python scripts/boss_cdp_raw.py --setup-chrome
   （首次需扫码登录，登录态持久保存于 ~/.boss-zhipin-scraper/chrome-profile）

用法（base 环境，有 pydantic + sqlalchemy）：
    python scripts/run_collector.py --keyword "AI开发" --city 广州 --pages 1
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import AgentState, build_default_pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="AI开发")
    ap.add_argument("--city", default="广州")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--no-persist", action="store_true",
                    help="只测采集不落库（跳过 CollectorPersistAgent）")
    args = ap.parse_args()

    # bat 里空输入会传空串 ""，回退到默认值
    keyword = args.keyword or "AI开发"
    city = args.city or "广州"
    pages = args.pages or 1

    state = AgentState()
    state.collector.keyword = keyword
    state.collector.city = city
    state.collector.pages = pages

    if args.no_persist:
        # 只跑采集 Agent（默认流水线第一个）
        from agents import CollectorAgent, SequentialOrchestrator
        from agents.logging_setup import setup_run_log, write_summary
        from agents.base import BaseAgent

        logger, log_path = setup_run_log(run_id=state.run_id)
        BaseAgent.set_file_logger(logger)
        print(f"[run_collector] 📄 日志: {log_path}")
        try:
            state = CollectorAgent().run(state)
            write_summary(logger, state)
        finally:
            BaseAgent.clear_file_logger()
        print("\n=== 采集结果（未落库）===")
        print(f"总条数: {state.collector.stats.get('total')}")
        print(f"关键词: {state.collector.keyword} | 城市: {state.collector.city}")
    else:
        orch = build_default_pipeline()
        state = orch.run(state)

        print("\n=== 流水线结果 ===")
        print(f"采集: {state.collector.stats.get('total')} 条")
        print(f"落库: {state.collector.stats.get('persisted')}")
        print(f"错误: {state.extra.get('errors', []) or '无'}")

    # 打印前 3 条样本
    jobs = state.collector.raw_jobs
    print(f"\n=== 样本（前 {min(3, len(jobs))} 条）===")
    for j in jobs[:3]:
        print(f"  {j.get('title')} | {j.get('salary')} | {j.get('location')} | {j.get('boss_name')}")


if __name__ == "__main__":
    main()
