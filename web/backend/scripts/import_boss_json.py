"""
BOSS 采集结果导入脚本 — 把 boss-zhipin-scraper 的 JSON 输出导入 1.0 jobs 表

用法：
    cd <repo>/web/backend
    python scripts/import_boss_json.py ^
        --list "<repo>/tools/boss-zhipin-scraper/test_output/ai_dev_gz.json" ^
        --detail "C:/Users/<you>/.boss-zhipin-scraper/job-result/boss_details.json" ^
        --keyword "AI开发" --city "广州"

说明：
- 列表 JSON 与详情 JSON 按 job_id 合并
- source_url 唯一约束去重（已存在的跳过）
- salary 支持 "8-12K" / "200-250元/天" / "面议"
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 允许直接运行 scripts/ 下的脚本
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.job import Job


def parse_salary(text: str) -> tuple:
    """解析 '8-12K' / '200-250元/天' / '15-25K·15薪' / '面议' → (min, max)"""
    if not text or "面议" in text:
        return None, None
    # 元/天、元/小时 类日薪：不入薪资范围（存 None）
    if "元/天" in text or "元/小时" in text or "日" in text:
        return None, None
    m = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*[Kk]", text)
    if m:
        return int(m.group(1)) * 1000, int(m.group(2)) * 1000
    m = re.search(r"(\d+)\s*[Kk]\s*以上", text)
    if m:
        return int(m.group(1)) * 1000, None
    m = re.search(r"(\d+)\s*[Kk]", text)
    if m:
        v = int(m.group(1)) * 1000
        return v, v
    return None, None


def parse_tags(tags_text: str) -> tuple:
    """解析 '经验不限 | 大专' → (experience, education)"""
    if not tags_text:
        return "", ""
    parts = [p.strip() for p in tags_text.split("|") if p.strip()]
    exp = next((p for p in parts if "经验" in p or "应届" in p or "年" in p), "")
    edu = next((p for p in parts if p in ("大专", "本科", "硕士", "博士", "中专", "高中", "不限学历")), "")
    return exp, edu


def parse_district(location: str) -> str:
    """解析 '广州·天河区' → '天河区'；'广州··' → ''"""
    if not location:
        return ""
    parts = location.split("·")
    return parts[1] if len(parts) > 1 and parts[1].strip() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="列表 JSON 路径")
    ap.add_argument("--detail", required=False, default="", help="详情 JSON 路径")
    ap.add_argument("--keyword", required=True, help="抓取关键词（写入 source_keyword）")
    ap.add_argument("--city", required=True, help="城市（写入 city）")
    args = ap.parse_args()

    # 读取列表
    with open(args.list, encoding="utf-8") as f:
        list_data = json.load(f)
    jobs = list_data.get("jobs", list_data) if isinstance(list_data, dict) else list_data
    print(f"📋 列表 {len(jobs)} 条")

    # 读取详情（可选）
    details = {}
    if args.detail and Path(args.detail).exists():
        with open(args.detail, encoding="utf-8") as f:
            detail_data = json.load(f)
        details = {d.get("job_id"): d for d in detail_data} if isinstance(detail_data, list) else detail_data
        print(f"📄 详情 {len(details)} 条")

    db = SessionLocal()
    batch = datetime.now().strftime("%Y%m%d%H%M%S")
    new_cnt = dup_cnt = skip_cnt = 0

    for j in jobs:
        job_id = j.get("job_id")
        det = details.get(job_id, {}) if job_id else {}

        source_url = (det.get("job_link") or j.get("job_link") or j.get("link") or "").strip()
        if not source_url:
            skip_cnt += 1
            continue

        # 去重：source_url 已存在则跳过
        if db.query(Job).filter_by(source_url=source_url).first():
            dup_cnt += 1
            continue

        title = det.get("title") or j.get("title") or ""
        company = det.get("company") or j.get("company") or j.get("boss_name") or "未知"
        salary_text = det.get("salary") or j.get("salary") or ""
        tags_text = det.get("tags_list") or j.get("tags") or j.get("job_labels") or ""
        location = det.get("location") or j.get("location") or ""
        exp, edu = parse_tags(tags_text)
        sal_min, sal_max = parse_salary(salary_text)

        job = Job(
            job_name=title,
            company_name=company,
            salary_min=sal_min,
            salary_max=sal_max,
            city=args.city,
            district=parse_district(location),
            experience=exp,
            education=edu,
            jd_text=(det.get("jd") or "").strip() or None,
            company_size=j.get("company_scale") or "",
            company_industry=j.get("company_industry") or "",
            company_finance=j.get("company_stage") or "",
            boss_active=(det.get("boss_active_status") or j.get("boss_active_status") or ""),
            source_url=source_url,
            source_keyword=args.keyword,
            status="new",
            collect_batch=batch,
        )
        db.add(job)
        new_cnt += 1

    db.commit()
    db.close()

    print(f"\n✅ 导入完成: 新增 {new_cnt} / 重复跳过 {dup_cnt} / 缺链接跳过 {skip_cnt} / 批次 {batch}")


if __name__ == "__main__":
    main()
