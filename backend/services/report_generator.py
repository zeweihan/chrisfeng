"""HTML Report Generator using Jinja2."""
import os
import datetime
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

def generate_html_report(analysis_data: dict, title: str, period: str) -> str:
    """Generate HTML string from analysis dict using Jinja template."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    
    # Custom filter to map standard colors to tailwind classes if needed, or format numbers
    
    template = env.get_template("report_template.html")
    
    context = {
        "title": title,
        "period": period,
        "generated_date": datetime.datetime.now().strftime("%Y年%m月%d日"),
        "analysis": analysis_data,
        "sections": [
            {"id": "cost", "title": "人力成本使用率与编制分析", "num": "01"},
            {"id": "turnover", "title": "入离职趋势概览", "num": "02"},
            {"id": "onboard_dept", "title": "入职分析 - 部门维度", "num": "03"},
            {"id": "competitor", "title": "竞对人才获取分析", "num": "04"},
            {"id": "onboard_detail", "title": "关键入职人员明细", "num": "05"},
            {"id": "offboard_dept", "title": "离职分析 - 部门维度", "num": "06"},
            {"id": "offboard_detail", "title": "关键离职人员明细", "num": "07"},
        ]
    }
    
    return template.render(**context)

