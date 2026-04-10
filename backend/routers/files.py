"""File upload router."""
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from fastapi.params import Depends

from config import settings
from database import get_db, UploadedFile
from services.parser import parse_roster, parse_cost_data, parse_salary_data

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),  # roster / cost / salary
    password: str = Form(None),
    db: Session = Depends(get_db),
):
    if file_type not in ("roster", "cost", "salary"):
        raise HTTPException(status_code=400, detail="file_type 必须是 roster/cost/salary")

    # Save file
    ext = os.path.splitext(file.filename)[1]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_name = f"{file_type}_{timestamp}{ext}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_name)

    with open(saved_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Parse based on type
    try:
        if file_type == "roster":
            summary = parse_roster(saved_path, password=password)
        elif file_type == "cost":
            summary = parse_cost_data(saved_path, password=password)
        elif file_type == "salary":
            summary = parse_salary_data(saved_path, password=password)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败: {str(e)}")

    # Save record
    record = UploadedFile(
        filename=saved_name,
        original_name=file.filename,
        file_type=file_type,
        file_size=len(content),
        upload_time=datetime.utcnow(),
        summary=summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "filename": file.filename,
        "file_type": file_type,
        "summary": summary,
    }


@router.get("/list")
async def list_files(db: Session = Depends(get_db)):
    files = db.query(UploadedFile).order_by(UploadedFile.upload_time.desc()).all()
    return [
        {
            "id": f.id,
            "filename": f.original_name,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "upload_time": f.upload_time.isoformat(),
            "summary": f.summary,
        }
        for f in files
    ]


@router.delete("/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db)):
    record = db.query(UploadedFile).filter_by(id=file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    # Delete physical file
    filepath = os.path.join(settings.UPLOAD_DIR, record.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.delete(record)
    db.commit()
    return {"status": "deleted"}
