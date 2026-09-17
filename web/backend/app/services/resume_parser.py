"""
简历解析服务
- PDF：PyMuPDF 提取文本
- 图片：PaddleOCR 识别
- 结构化：LLM 提取技能/经验/项目/教育
"""
import os
import json
from datetime import datetime

import pymupdf as fitz  # PyMuPDF（新版主入口，fitz 别名已废弃）

from app.config import Config


def extract_text_from_pdf(file_path: str) -> str:
    """从 PDF 提取纯文本"""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(text_parts).strip()


def extract_text_from_image(file_path: str) -> str:
    """从图片提取文本（PaddleOCR）"""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError("请安装 paddleocr: pip install paddleocr")

    ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    result = ocr.ocr(file_path, cls=True)
    if not result or not result[0]:
        return ""

    lines = []
    for line_info in result[0]:
        if line_info and len(line_info) >= 2:
            text = line_info[1][0] if isinstance(line_info[1], (list, tuple)) else str(line_info[1])
            lines.append(text)
    return "\n".join(lines)


def extract_text_from_file(file_path: str) -> str:
    """根据文件类型自动选择提取方式"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        return extract_text_from_image(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def parse_resume_to_structured(raw_text: str) -> dict:
    """用 LLM 从简历文本中提取结构化信息"""
    from openai import OpenAI

    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == "sk-your-api-key-here":
        # 没有配置 API Key 时返回基础结构
        return {
            "name": "",
            "skills": [],
            "years": 0,
            "education": "",
            "school": "",
            "projects": [],
            "raw_summary": raw_text[:500],
        }

    client = OpenAI(
        api_key=Config.OPENAI_API_KEY,
        base_url=Config.OPENAI_BASE_URL,
    )

    prompt = f"""你是一个专业的简历解析器。请从以下简历文本中提取结构化信息。

【简历文本】
{raw_text[:4000]}

请以 JSON 格式返回（不要包含 markdown 代码块标记）：
{{
    "name": "姓名",
    "skills": ["技能1", "技能2", ...],
    "years": 工作年限(数字),
    "education": "最高学历（如：本科、硕士）",
    "school": "毕业院校",
    "projects": [
        {{"name": "项目名称", "role": "担任角色", "tech": ["使用的技术"], "desc": "简要描述"}}
    ],
    "summary": "200字以内的简历摘要"
}}
"""

    try:
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        # 清理可能的 markdown 代码块标记
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)
    except Exception as e:
        # LLM 调用失败，返回降级结果
        return {
            "name": "",
            "skills": [],
            "years": 0,
            "education": "",
            "school": "",
            "projects": [],
            "raw_summary": raw_text[:500],
            "parse_error": str(e),
        }
