from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from app.schemas import TemplateCreate, TemplateResponse, TemplateUpdate, TemplatePatch, template_to_pydantic
from app.services.excel_processor import process_excel_file
from app.settings import STORAGE_DIR, JSON_STORAGE_DIR, CSV_STORAGE_DIR, TEMPLATES_STORAGE_DIR
import os
from json import load, dump
from fastapi.encoders import jsonable_encoder
from typing import Optional 
from io import StringIO
import csv

app = FastAPI()

origins = [
    "https://ex-batch-front-end-seven.vercel.app",
    "https://localhost:3000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/templates", response_model=TemplateResponse)
def save_template_2(template: TemplateCreate):
    
    existing_ids = []
    for file in TEMPLATES_STORAGE_DIR.glob("template_*.json"):
        try:
            id_str = int(file.stem.split("_")[1])
            existing_ids.append(id_str)
        except (IndexError, ValueError):
            continue
    next_id = max(existing_ids, default=0) + 1
    
    template_name = f"template_{next_id}"
    template_path = os.path.join(TEMPLATES_STORAGE_DIR, f"{template_name}.json")
    
    template_data = jsonable_encoder(template)
    template_data['id'] = next_id
    
    with open(template_path, "w", encoding="utf-8") as f:
        dump(template_data, f, ensure_ascii=False, indent=4)
    
    return template_data


@app.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int):
    try:
        with open(TEMPLATES_STORAGE_DIR / f"template_{template_id}.json", "r", encoding="utf-8") as f:
            template = load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
        template_id: int,
        payload: TemplateUpdate):
    
    template_path = TEMPLATES_STORAGE_DIR / f"template_{template_id}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            existing_template = load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read existing template: {e}")
    
    updated_template = payload.model_dump(by_alias=False)
    existing_template.update(updated_template)
    existing_template["id"] = template_id
    
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            dump(existing_template, f, ensure_ascii=False, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update template: {e}")
    
    return TemplateResponse(**existing_template)


@app.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int):
    template = TEMPLATES_STORAGE_DIR / f"template_{template_id}.json"
    if os.path.exists(template):
        os.remove(template)
    else:
        raise HTTPException(404, "Template not found")


@app.get("/templates_list")
def get_template():
    if not TEMPLATES_STORAGE_DIR.exists():
        raise HTTPException(status_code=500, detail="Templates storage directory not found")
    templates = []
    for file in TEMPLATES_STORAGE_DIR.glob("template_*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = load(f)
                template = TemplateResponse(**data)
                templates.append(template)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading template {file.name}: {e}")
    if not templates:
        raise HTTPException(status_code=404, detail="No template found")
    return templates


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


@app.post("/process_excel/")
async def process_excel(
        template_id: int,
        excel_file: UploadFile = File(...),
        csv_file: UploadFile = File(None)
):
    try:
        with open(TEMPLATES_STORAGE_DIR / f"template_{template_id}.json", "r", encoding="utf-8") as f:
            db_template = load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")

    template_pydantic = template_to_pydantic(db_template)

    excel_data = await excel_file.read()
    
    if csv_file:
        csv_bytes  = await csv_file.read()
        csv_data = list(csv.DictReader(csv_bytes.decode('utf-8-sig').splitlines()))
    else:
        if all(im.forced_value is not None for im in template_pydantic.input_mappings):
            csv_data = [{}]
        else:
            raise HTTPException(
                status_code=400,
                detail="CSV file is required unless all input are forced in the template."
            )
    
    csv_content = process_excel_file(excel_data, template_pydantic, csv_data)

    reader = csv.DictReader(StringIO(csv_content))
    json_result = list(reader)
    
    base_filename = f"result_{template_id}"
    
    csv_path = os.path.join(CSV_STORAGE_DIR, f"{base_filename}.csv")
    json_path = os.path.join(JSON_STORAGE_DIR, f"{base_filename}.json")
    
    
    with open(csv_path, "w", newline='', encoding="utf-8") as f:
        f.write(csv_content)

    with open(json_path, "w", encoding="utf-8") as f:
        dump(json_result, f, ensure_ascii=False)
    
    return JSONResponse(content={
        "json": json_result,
        "csv": csv_content,
        "dowload_links":{
            "json": f"/download/json/{base_filename}",
            "csv": f"/download/csv/{base_filename}"
        }
    })


