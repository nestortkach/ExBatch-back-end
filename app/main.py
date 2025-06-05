from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session, selectinload
from app.models import Template, InputMapping, OutputMapping, IdentityMapping, ResultLogs, get_db, Base, engine
from app.schemas import TemplateCreate, TemplateResponse, TemplateUpdate, TemplatePatch, ResultLogsResponse, template_to_pydantic
from app.services.excel_processor import process_excel_file
from app.settings import STORAGE_DIR, JSON_STORAGE_DIR, CSV_STORAGE_DIR
import os
from json import dump as json_dump
from typing import Optional, List
from io import StringIO
import csv
from datetime import datetime

from fastapi.staticfiles import StaticFiles

app = FastAPI()

# # Mount the entire frontend directory as static files
# app.mount("/assets", StaticFiles(directory="frontend/assets"), name="assets")
# app.mount("/static", StaticFiles(directory="frontend"), name="frontend")

# @app.get("/")
# async def serve_frontend():
#     return FileResponse("frontend/index.html")

# Your existing CORS configuration
origins = [
    "https://ex-batch-front-end-seven.vercel.app",
    "https://localhost:3000",
    "http://localhost:3000",
    "http://localhost:8000",  # Add your FastAPI server
    "http://127.0.0.1:8000",
]

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/templates", response_model=TemplateResponse)
def save_template(template: TemplateCreate, db: Session = Depends(get_db)):
    db_template = Template(
        name=template.name,
        description=template.description
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    for input_mapping in template.input_mappings:
        db_input_mapping = InputMapping(
            name=input_mapping.name,
            source=input_mapping.source,
            cell=input_mapping.cell,
            forced_value=input_mapping.forced_value,
            template_id=db_template.id
        )
        db.add(db_input_mapping)

    for output_mapping in template.output_mappings:
        db_output_mapping = OutputMapping(
            field=output_mapping.field,
            cell=output_mapping.cell,
            template_id=db_template.id
        )
        db.add(db_output_mapping)

    for identity_mapping in template.identity_mappings:
        db_identity_mapping= IdentityMapping(
            name=identity_mapping.name,
            template_id=db_template.id
        )
        db.add(db_identity_mapping)
        
    db.commit()
    return db_template


@app.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(Template).filter(Template.id == template_id).first()
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template


@app.get("/templates_list", response_model=List[TemplateResponse])
def get_template(db: Session = Depends(get_db)):
    db_template = db.query(Template).options(
        selectinload(Template.input_mappings),
        selectinload(Template.output_mappings),
        selectinload(Template.identity_mappings)
        ).all()
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template


@app.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
        template_id: int,
        payload: TemplateUpdate,
        db: Session = Depends(get_db)):
    db_tpl: Template = db.get(Template, template_id)
    if not db_tpl:
        raise HTTPException(404, "Template not found")

    db_tpl.name = payload.name
    db_tpl.description = payload.description

    db.query(InputMapping).filter(InputMapping.template_id == template_id).delete()
    db.query(OutputMapping).filter(OutputMapping.template_id == template_id).delete()
    db.query(IdentityMapping).filter(IdentityMapping.template_id == template_id).delete()

    for im in payload.input_mappings:
        db.add(InputMapping(**im.dict(by_alias=False), template_id=template_id))
    for om in payload.output_mappings:
        db.add(OutputMapping(**om.dict(by_alias=False), template_id=template_id))
    for idm in payload.identity_mappings:
        db.add(IdentityMapping(**idm.dict(by_alias=False), template_id=template_id))

    db.commit()
    db.refresh(db_tpl)
    return db_tpl


@app.patch("/templates/{template_id}", response_model=TemplateResponse)
def patch_template(
        template_id: int,
        payload: TemplatePatch,
        db: Session = Depends(get_db)):

    db_tpl: Template = db.get(Template, template_id)
    if not db_tpl:
        raise HTTPException(404, "Template not found")

    if payload.name is not None:
        db_tpl.name = payload.name
    if payload.description is not None:
        db_tpl.description = payload.description

    if payload.input_mappings is not None:
        db.query(InputMapping).filter(InputMapping.template_id == template_id).delete()
        for im in payload.input_mappings:
            db.add(InputMapping(**im.dict(by_alias=False), template_id=template_id))

    if payload.output_mappings is not None:
        db.query(OutputMapping).filter(OutputMapping.template_id == template_id).delete()
        for om in payload.output_mappings:
            db.add(OutputMapping(**om.dict(by_alias=False), template_id=template_id))

    if payload.identity_mappings is not None:
        db.query(IdentityMapping).filter(IdentityMapping.template_id == template_id).delete()
        for idm in payload.identity_mappings:
            db.add(IdentityMapping(**idm.dict(by_alias=False), template_id=template_id))

    db.commit()
    db.refresh(db_tpl)
    return db_tpl


@app.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    db_tpl: Template = db.get(Template, template_id)
    if not db_tpl:
        raise HTTPException(404, "Template not found")

    db.delete(db_tpl)
    db.commit()
    return JSONResponse({"message": "Template successfully deleted!"})


@app.get("/download/json/{filename}")
async def download_json(filename: str):
    file_path = os.path.join(JSON_STORAGE_DIR, f"{filename}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="JSON file not found")
    return FileResponse(
        path=file_path,
        media_type="application/json",
        filename=f"{filename}.json"
    )


@app.get("/download/csv/{filename}")
async def download_csv(filename: str):
    file_path = os.path.join(CSV_STORAGE_DIR, f"{filename}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="CSV file not found")
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=f"{filename}.csv"
    )


@app.get("/logs_list", response_model=List[ResultLogsResponse])
def get_logs_list(db: Session = Depends(get_db)):
    db_logs = db.query(ResultLogs).all()
    if not db_logs:
        raise HTTPException(status_code=404, detail="Logs not found")
    return db_logs


@app.get("/logs/{log_id}", response_model=ResultLogsResponse)
def get_log(log_id: int,db: Session = Depends(get_db)):
    db_log = db.query(ResultLogs).filter(ResultLogs.id == log_id).first()
    if db_log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return db_log


@app.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(log_id: int, db: Session = Depends(get_db)):
    db_log: ResultLogs = db.get(ResultLogs, log_id)
    if not db_log:
        raise HTTPException(404, "Log not found")

    db.delete(db_log)
    db.commit()
    return JSONResponse({"message": "Log successfully deleted!"})


@app.post("/process_excel/")
async def process_excel(
        template_id: int,
        excel_file: UploadFile = File(...),
        csv_file: UploadFile = File(None),
        skip_rows: bool = True,
        db: Session = Depends(get_db)
):  
    
    execution_log = ResultLogs(
        template_id=template_id,
        excel_filename=excel_file.filename,
        csv_filename=csv_file.filename if csv_file else None,
        datetime_started=datetime.now(),
        datetime_ended=None,
        duration_seconds=None
    )
    
    try:
        
        db_template = db.query(Template).filter(Template.id == template_id).first()

        if not db_template:
            raise HTTPException(status_code=404, detail="Template not found")

        template_pydantic = template_to_pydantic(db_template)

        excel_data = await excel_file.read() 
        csv_data = await _process_csv_input(csv_file, template_pydantic)
        total_rows = len(csv_data)
        
        result_filename = _generate_result_filename(excel_file, csv_file, template_id)
        csv_content, processed_rows = process_excel_file(excel_data, template_pydantic, csv_data, skip_rows)
        json_result = list(csv.DictReader(StringIO(csv_content)))
        
        file_links = _save_results(result_filename, csv_content, json_result)
        
        _finalize_execution_log(execution_log, total_rows, processed_rows, file_links, db)
        
        return JSONResponse(content={
            "json": json_result,
            "csv": csv_content,
            "dowload_links":{
                "json": f"/download/json/{result_filename}",
                "csv": f"/download/csv/{result_filename}"
            }
        })
    
    except Exception as e:
        _finalize_execution_log(execution_log, 0, 0, None, db)
        error_name = type(e).__name__
        raise HTTPException(
            status_code=400,
            detail=f"Error during file processing: {str(e)}"
        )


async def _process_csv_input(csv_file: UploadFile, template_pydantic) -> list:
    
    if csv_file:
        csv_bytes = await csv_file.read()
        return list(csv.DictReader(csv_bytes.decode('utf-8-sig').splitlines()))

    if all(im.forced_value is not None for im in template_pydantic.input_mappings):
        return [{}]
    
    raise HTTPException(
        status_code=400,
        detail="CSV file is required unless all inputs are forced in the template."
    )


def _generate_result_filename(excel_file: UploadFile, csv_file: UploadFile, template_id: int):
    
    excel_filename = excel_file.filename.split('.')[0]
    result_filename = f"result_{excel_filename}_"
    if csv_file:
        result_filename += csv_file.filename.split('.')[0]
    result_filename += f"_template_{template_id}"
    return result_filename


def _save_results(result_filename: str, csv_content: str, json_result: list) -> dict:
    

    csv_path = os.path.join(CSV_STORAGE_DIR, f"{result_filename}.csv")
    json_path = os.path.join(JSON_STORAGE_DIR, f"{result_filename}.json")
    
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        f.write(csv_content)
    
    with open(json_path, "w", encoding="utf-8") as f:
        json_dump(json_result, f, ensure_ascii=False)
        
    
    return {"csv": f"/download/csv/{result_filename}", "json": f"/download/json/{result_filename}"}


def _finalize_execution_log(
    execution_log: ResultLogs, 
    total_rows: int, 
    processed_rows: int,
    file_links: dict,
    db: Session
):
    
    execution_log.datetime_ended = datetime.now()
    time_diff = execution_log.datetime_ended - execution_log.datetime_started
    execution_log.duration_seconds = int(time_diff.total_seconds()) 
    execution_log.num_of_records = total_rows
    execution_log.processed_records = processed_rows
    if file_links:
        execution_log.download_link_csv = file_links["csv"]
        execution_log.download_link_json = file_links["json"]
    db.add(execution_log)
    db.commit()
    db.refresh(execution_log)


