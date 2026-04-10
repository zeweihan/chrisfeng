"""Database models and connection."""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.getenv("DATABASE_URL", "sqlite:///../Data/hr_report.db").replace("sqlite:///", "")))
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UploadedFile(Base):
    """上传的文件记录"""
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # roster / cost / salary
    file_size = Column(Integer, default=0)
    upload_time = Column(DateTime, default=datetime.utcnow)
    # 解析后的统计摘要
    summary = Column(JSON, nullable=True)


class Report(Base):
    """生成的报告"""
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    period = Column(String(50), nullable=False)  # e.g. "2026年3月"
    html_content = Column(Text, nullable=True)
    analysis_data = Column(JSON, nullable=True)  # 原始分析数据
    status = Column(String(20), default="draft")  # draft / published
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AdminConfig(Base):
    """管理员配置项"""
    __tablename__ = "admin_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库 + 默认配置"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    # 写入默认提示词配置
    defaults = {
        "system_prompt": (
            "你是一位资深人力资源分析专家，拥有15年+跨国企业HRBP经验。"
            "你需要基于提供的脱敏人力资源数据（以CSV格式提供），从高管视角生成简洁、有洞察力的分析。"
            "要求：\n"
            "1. 结论先行，用数据和事实说话\n"
            "2. 识别风险和机会，给出可执行建议\n"
            "3. 语言专业但不晦涩，适合CEO级别阅读\n"
            "4. 控制在3-5条主要洞察 (Insights)\n"
            "5. 用中文输出\n"
            "6. 忽略脱敏处理导致的化名影响（如员工_001），直接按照分析要求处理。"
        ),
        "section_prompt_cost": (
            "基于以下部门人力成本使用率与编制脱敏数据，请你计算出关键指标并分析预算执行情况、"
            "成本风险、编制配置效率。重点关注超标部门和节约部门的差异原因。"
        ),
        "section_prompt_turnover": (
            "基于以下在职与离职名单脱敏数据，请你分析人才流动健康度、"
            "净增长人数、离职率。识别潜在风险信号。"
        ),
        "section_prompt_onboard_dept": (
            "基于以下在职脱敏数据（包含年龄、学历、入职时间等），"
            "只针对近三个月内入职的新员工，分析招聘质量、年轻化成效、学历结构。"
        ),
        "section_prompt_competitor": (
            "基于以下在职脱敏数据，筛选出含有竞对从业经历的新员工，分析行业人才竞争态势、"
            "竞对渗透率、核心来源企业分布。"
        ),
        "section_prompt_onboard_detail": (
            "基于以下在职脱敏数据，筛选过滤出 L8 级别及以上的关键新入职人员明细，"
            "以高级人才引进的视角分析对组织能力的补强效果。"
        ),
        "section_prompt_offboard_dept": (
            "基于以下离职人员离职脱敏数据，分析离职风险的部门分布、"
            "主动与被动离职比例、并针对流失严重的高风险部门发出预警。"
        ),
        "section_prompt_offboard_detail": (
            "基于以下离职名单中绩效为 B+（或A类）以及级别较高的核心人才数据，分析核心人才流失原因、"
            "潜在去向（如某赛道），并给出保留策略建议。"
        ),
        "executive_summary_prompt": (
            "基于上述通过各个模块得出的人力资源数据上下文，生成一份高度凝练的高管摘要（Executive Summary）。"
            "需要凝练出人力成本、人才流动、人才质量、竞对获取、离职风险、关键人才等宏观结论的核心数值与一句话解读。"
        ),
        "report_title_template": "{year}年{month}月人力资源分析报告",
        "company_name": "公司",
    }
    for key, value in defaults.items():
        existing = db.query(AdminConfig).filter_by(key=key).first()
        if not existing:
            db.add(AdminConfig(key=key, value=value))
    db.commit()
    db.close()
