from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models import Template, InputMapping, OutputMapping, IdentityMapping, get_db, Base, engine
from app.schemas import TemplateCreate, TemplateResponse, TemplateUpdate, TemplatePatch, template_to_pydantic
from app.services.excel_processor import process_excel_file
from typing import Optional 
from io import StringIO
import csv


app = FastAPI()

origins = [
    "https://ex-batch-front-end-seven.vercel.app",
    "https://localhost:3000",
    "http://localhost:3000",
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


@app.get("/templates_list")
def get_template(db: Session = Depends(get_db)):
    db_template = db.query(Template).all()
    if db_template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return db_template


@app.post("/process_excel/")
async def process_excel(
        template_id: int,
        excel_file: UploadFile = File(...),
        csv_file: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db)
):
    db_template = db.query(Template).filter(Template.id == template_id).first()

    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_pydantic = template_to_pydantic(db_template)

    excel_data = await excel_file.read()
    
    if csv_file:
        csv_bytes  = await csv_file.read()
        csv_data = list(csv.DictReader(csv_bytes.decode('utf-8').splitlines()))
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
    
    return JSONResponse(content={
        "json": json_result,
        "csv": csv_content
    })


