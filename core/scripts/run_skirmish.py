"""
Skirmish 实测脚本 — 对 DB 里的岗位跑公司避坑（被动 + 可选主动形态）

用法（在 <repo>/core 目录下执行）：
    python scripts/run_skirmish.py            # 只跑被动形态（无 LLM 也能用）
    python scripts/run_skirmish.py --persist  # 落库
    python scripts/run_skirmish.py --no-active # 强制只用被动（不调 LLM）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import AgentState, SequentialOrchestrator
from agents.skirmish import SkirmishAgent, SkirmishPersistAgent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist", action="store_true", help="落库到 jobs 表")
    ap.add_argument("--no-active", action="store_true", help="只用被动形态（不调 LLM）")
    args = ap.parse_args()

    state = AgentState()

    agents = [SkirmishAgent(enable_active=not args.no_active)]
    if args.persist:
        agents.append(SkirmishPersistAgent())
    orch = SequentialOrchestrator(agents=agents)
    state = orch.run(state)

    ns = state.skirmish
    print(f"\n=== 避坑结果 ===")
    print(f"公司信息包: {len(ns.company_profiles)} 条")
    print(f"主动风险分析: {len(ns.risk_flags)} 条")

    # 打印前 2 条公司信息包
    print(f"\n[公司信息包样本（前 2 条）]")
    for p in ns.company_profiles[:2]:
        print(f"\n--- {p['job_name']} | {p['company_name']} ---")
        print(p['profile_text'])

    # 打印有风险的
    risky = [r for r in ns.risk_flags if r.get('flags') and r['flags'][0].get('flag') != 'llm_error']
    print(f"\n[主动风险分析] 实际有风险的: {len(risky)} 条")
    for r in risky[:3]:
        print(f"\n--- {r['job_name']} | {r['company_name']} ---")
        for f in r['flags']:
            print(f"  [{f['severity']}] {f['flag']}: {f['reason']}")


if __name__ == "__main__":
    main()
