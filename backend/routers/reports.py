"""Reports router with SSE heartbeat for long-running LLM analysis."""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, Report, UploadedFile
from services.analyzer import analyze_all
from services.report_generator import generate_html_report

router = APIRouter()

# Progress messages shown to user during analysis
PROGRESS_MESSAGES = [
    (0, "正在准备数据并发送给 AI..."),
    (10, "AI 正在阅读花名册数据..."),
    (25, "正在分析人员结构与部门分布..."),
    (45, "正在分析离职率与竞对数据..."),
    (70, "正在生成成本洞察与预警..."),
    (100, "正在整合各模块分析结果..."),
    (140, "正在生成执行摘要..."),
    (180, "分析接近完成，正在组装报告..."),
    (240, "大数据量分析耗时较长，请继续等待..."),
    (360, "仍在处理中，AI 正在深度推理..."),
]


def _get_progress_message(elapsed: int) -> str:
    """Get appropriate progress message based on elapsed seconds."""
    msg = PROGRESS_MESSAGES[0][1]
    for threshold, message in PROGRESS_MESSAGES:
        if elapsed >= threshold:
            msg = message
    return msg


class GenerateReportRequest(BaseModel):
    title: str
    period: str  # e.g. "2026年3月"
    year: int
    month: int
    roster_file_id: Optional[int] = None
    cost_file_id: Optional[int] = None
    salary_file_id: Optional[int] = None
    provider: Optional[str] = "google"
    model: Optional[str] = "gemini-3.1-pro-preview"


class SaveReportRequest(BaseModel):
    html_content: str


@router.post("/generate")
async def generate_report(req: GenerateReportRequest, db: Session = Depends(get_db)):
    """Generate a new report with SSE heartbeat to keep connection alive."""
    # Find latest files of each type if not specified
    roster_file = None
    cost_file = None
    salary_file = None

    if req.roster_file_id:
        roster_file = db.query(UploadedFile).filter_by(id=req.roster_file_id).first()
    else:
        roster_file = (
            db.query(UploadedFile).filter_by(file_type="roster").order_by(UploadedFile.upload_time.desc()).first()
        )

    if req.cost_file_id:
        cost_file = db.query(UploadedFile).filter_by(id=req.cost_file_id).first()
    else:
        cost_file = (
            db.query(UploadedFile).filter_by(file_type="cost").order_by(UploadedFile.upload_time.desc()).first()
        )

    if req.salary_file_id:
        salary_file = db.query(UploadedFile).filter_by(id=req.salary_file_id).first()
    else:
        salary_file = (
            db.query(UploadedFile).filter_by(file_type="salary").order_by(UploadedFile.upload_time.desc()).first()
        )

    if not roster_file:
        raise HTTPException(status_code=400, detail="请先上传花名册文件")

    async def event_stream():
        """SSE generator: sends heartbeats while LLM processes, then sends result."""
        import time as _time
        import traceback as _tb
        
        def _log(msg):
            ts = _time.strftime("%H:%M:%S")
            print(f"[SSE {ts}] {msg}", flush=True)
        
        try:
            _log(f"Starting SSE stream: provider={req.provider}, model={req.model}")
            
            # Start analysis as a background task
            task = asyncio.create_task(
                analyze_all(
                    roster_file_id=roster_file.id,
                    cost_file_id=cost_file.id if cost_file else None,
                    salary_file_id=salary_file.id if salary_file else None,
                    year=req.year,
                    month=req.month,
                    db=db,
                    provider=req.provider,
                    model=req.model,
                )
            )

            elapsed = 0
            heartbeat_interval = 3  # seconds

            # Send heartbeats every 3 seconds while analysis is running
            while not task.done():
                msg = _get_progress_message(elapsed)
                heartbeat = {
                    "type": "heartbeat",
                    "elapsed": elapsed,
                    "message": msg,
                }
                yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"

                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_interval)
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    _log(f"Task exception during wait: {e}")
                    pass  # Will be caught below via task.result()

                elapsed += heartbeat_interval

            # Task is done - check for errors
            _log(f"Task completed after {elapsed}s. Checking result...")
            try:
                analysis = task.result()
                _log(f"Analysis returned successfully")
            except Exception as e:
                _log(f"❌ Analysis failed: {_tb.format_exc()}")
                error_event = {
                    "type": "error",
                    "message": f"分析失败: {str(e)}",
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return

            # Generate HTML report
            try:
                _log("Generating HTML report...")
                html = generate_html_report(analysis, req.title, req.period)
                _log(f"HTML report generated: {len(html)} chars")
            except Exception as e:
                _log(f"❌ Report generation failed: {_tb.format_exc()}")
                error_event = {
                    "type": "error",
                    "message": f"报告生成失败: {str(e)}",
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return

            # Save report to database
            try:
                report = Report(
                    title=req.title,
                    period=req.period,
                    html_content=html,
                    analysis_data=analysis,
                    status="draft",
                )
                db.add(report)
                db.commit()
                db.refresh(report)
                _log(f"✅ Report saved: id={report.id}")
            except Exception as e:
                _log(f"❌ DB save failed: {_tb.format_exc()}")
                error_event = {
                    "type": "error",
                    "message": f"保存报告失败: {str(e)}",
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return

            # Send completion event
            done_event = {
                "type": "done",
                "id": report.id,
                "title": report.title,
                "period": report.period,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
            }
            yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            _log("SSE stream completed successfully")
            
        except Exception as e:
            # Top-level catch-all for any unexpected error in the generator
            _log(f"❌ UNEXPECTED SSE ERROR: {_tb.format_exc()}")
            try:
                error_event = {
                    "type": "error",
                    "message": f"未预期错误: {str(e)}",
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
            except Exception:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering if behind proxy
        },
    )


@router.get("/list")
async def list_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "period": r.period,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in reports
    ]


@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {
        "id": report.id,
        "title": report.title,
        "period": report.period,
        "html_content": report.html_content,
        "analysis_data": report.analysis_data,
        "status": report.status,
        "created_at": report.created_at.isoformat(),
    }


@router.put("/{report_id}")
async def update_report(report_id: int, req: SaveReportRequest, db: Session = Depends(get_db)):
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    report.html_content = req.html_content
    report.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "saved"}


@router.delete("/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    db.delete(report)
    db.commit()
    return {"status": "deleted"}
