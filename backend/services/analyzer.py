"""Analyzer service using LLM to extract insights from raw data."""
import json
import asyncio
import os
import pandas as pd
from typing import Optional
from sqlalchemy.orm import Session
import re
import time
import traceback

from database import UploadedFile
from services.parser import load_roster_data, df_to_markdown, df_to_smart_summary
from services.llm_client import get_configured_prompt, analyze_with_llm
from config import settings


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[Analyzer {ts}] {msg}", flush=True)


def _extract_json(text: str) -> dict:
    """Safely extract JSON from LLM output block."""
    # Try looking for a json block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    # Try directly parsing
    try:
        return json.loads(text.strip())
    except Exception as e:
        # Fallback to key-value string
        return {"error": "解析失败: " + str(e), "raw": text}


async def analyze_all(
    roster_file_id: int,
    cost_file_id: Optional[int],
    salary_file_id: Optional[int],
    year: int,
    month: int,
    db: Session,
    provider: str = "google",
    model: str = "gemini-3.1-pro-preview",
) -> dict:
    """Main entry point to analyze all data files."""
    _log(f"=== Starting analysis: provider={provider}, model={model} ===")
    
    # 1. Load data
    try:
        roster_file = db.query(UploadedFile).filter_by(id=roster_file_id).first()
        roster_path = os.path.join(settings.UPLOAD_DIR, roster_file.filename)
        _log(f"Loading roster: {roster_path}")
        df_active, df_left = load_roster_data(roster_path)
        _log(f"Loaded: active={len(df_active)} rows, left={len(df_left)} rows")
    except Exception as e:
        _log(f"❌ Error loading roster: {traceback.format_exc()}")
        raise
    
    # For Kimi (256K context limit), use smart statistical summary to stay under limit.
    # Other providers (Gemini 1M, OpenRouter) get full raw data.
    use_compact = (provider == "kimi")
    
    if use_compact:
        print(f"[Kimi mode] Using smart summary to fit within 256K context limit...")
        active_str = df_to_smart_summary(df_active, label="在职员工")
        left_str = df_to_smart_summary(df_left, label="离职员工")
    else:
        active_str = df_to_markdown(df_active)
        left_str = df_to_markdown(df_left)
    
    cost_str = "未提供成本数据。"
    df_cost = None
    if cost_file_id:
        from services.parser import _decrypt_if_needed, _clean_excel_df
        cost_f = db.query(UploadedFile).filter_by(id=cost_file_id).first()
        cf_path = _decrypt_if_needed(os.path.join(settings.UPLOAD_DIR, cost_f.filename))
        df_cost = _clean_excel_df(pd.read_excel(cf_path))
        if use_compact:
            cost_str = df_to_smart_summary(df_cost, label="成本数据")
        else:
            cost_str = df_to_markdown(df_cost)

    # 2. Get prompts
    system_prompt = await get_configured_prompt(db, "system_prompt")
    
    keys = ["cost", "turnover", "onboard_dept", "competitor", "onboard_detail", "offboard_dept", "offboard_detail"]
    prompts = {}
    for key in keys:
        prompts[key] = await get_configured_prompt(db, f"section_prompt_{key}")
    exec_prompt = await get_configured_prompt(db, "executive_summary_prompt")
    
    # 3. Construct unified context and instruction
    unified_context = f"【在职名单数据】\n{active_str}\n\n【离职名单数据】\n{left_str}\n\n【成本数据】\n{cost_str}"
    
    char_count = len(unified_context)
    est_tokens = int(char_count * 1.2)
    _log(f"Context: chars={char_count}, est_tokens≈{est_tokens}")
    
    unified_instruction = (
        "请作为一个拥有 15 年经验的 HRBP，全面一次性分析以下所有 8 个模块，严格按照各模块的专属提示进行洞察分析：\n"
    )
    for key, p in prompts.items():
        unified_instruction += f"\n--- 模块：{key} ---\n{p}\n"
    unified_instruction += f"\n--- 模块：executive_summary ---\n{exec_prompt}\n"
        
    unified_instruction += (
        "\n\n请必须以 **单个严格合法的大型 JSON 对象** 的形式返回数据！格式要求如下（除 JSON 外请勿返回任何前缀或后缀文字）：\n"
        "{\n"
        '  "cost": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "turnover": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "onboard_dept": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "competitor": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "onboard_detail": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "offboard_dept": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "offboard_detail": {"kpis": [], "insights": [], "warning_texts": []},\n'
        '  "executive_summary": {"cards": [{"title":"...","value":"...","desc":"...","color":"..."}]}\n'
        "}\n\n"
        "每个子模块中的 `kpis` 必须包含 label, value, change, type(positive/negative/neutral/warning)。"
        "`warning_texts` 必须包含 title, desc, level(danger/warning)。"
    )
    
    _log(f"Sending unified LLM request: provider={provider}, model={model}")
    try:
        result_text = await analyze_with_llm(system_prompt, unified_context, unified_instruction, provider=provider, model=model)
        _log(f"LLM returned {len(result_text)} chars")
    except Exception as e:
        _log(f"❌ LLM call failed: {traceback.format_exc()}")
        raise
    
    results = _extract_json(result_text)
    
    if "error" in results:
        _log(f"⚠️ LLM returned malformed JSON: {results['error']}")
        results = {k: {"kpis": [], "insights": ["分析解析出错..."], "warning_texts": []} for k in keys}
        results["executive_summary"] = {"cards": []}
    else:
        _log(f"✅ JSON parsed OK. Keys: {list(results.keys())}")

    # 4. Extract tables for template injection
    results["raw_tables"] = {
        "cost_preview": df_cost.head(5).to_dict(orient="records") if df_cost is not None else [],
    }

    _log(f"=== Analysis complete ===")
    return results
