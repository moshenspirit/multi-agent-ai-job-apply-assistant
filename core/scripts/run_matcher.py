"""
Matcher 实测脚本 — 对 DB 里已有的未匹配岗位跑方向标记

不需要采集环境（纯本地）：读 DB status/match_direction 为空的岗位 → 匹配 → 打印分布 → 可选落库

用法（在 <repo>/core 目录下执行）：
    python scripts/run_matcher.py            # 只匹配不落库
    python scripts/run_matcher.py --persist  # 匹配并落库

日志：自动写入 2.0/logs/collect-*.log（包含 10 个文件轮转）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import AgentState, SequentialOrchestrator
from agents.matcher import MatcherAgent, MatcherPersistAgent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true", help="匹配后落库")
    args = ap.parse_args()

    state = AgentState()

    # 走编排器（自动建立文件 logger + 写摘要）
    agents = [MatcherAgent()]
    if args.persist:
        agents.append(MatcherPersistAgent())
    orch = SequentialOrchestrator(agents=agents)
    state = orch.run(state)

    ns = state.matcher
    print("\n=== 匹配结果 ===")
    print(f"方向分布: {ns.direction_counts}")
    print(f"总条数: {len(ns.matched_jobs)}")

    # 打印 each direction 前 2 条
    for direction in ("frontend", "ai", "both", "none"):
        items = [j for j in ns.matched_jobs if j.get("match_direction") == direction]
        print(f"\n[{direction}] {len(items)} 条")
        for j in items[:2]:
            print(f"  {j.get('job_name') or j.get('title')} | {j.get('company_name')} | 命中原因: {j.get('match_reason')}")


if __name__ == "__main__":
    main()
