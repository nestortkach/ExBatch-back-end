from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from app.models import Template
from datetime import datetime

class InputMappingBase(BaseModel):
    id: str
    name: str = Field(alias="column")
    source: str
    cell: str
    forced_value: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

class OutputMappingBase(BaseModel):
    id: str
    field: str = Field(alias="name")
    cell: str

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"
    
class IdentityMappingBase(BaseModel):
    id: str
    name: str
    templateId: str
    
    class Config:
        allow_population_by_field_name = True
        extra = "ignore"



class TemplateCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase] = Field(alias="inputMappings")
    output_mappings: List[OutputMappingBase] = Field(alias="outputMappings")
    identity_mappings: List[IdentityMappingBase] = Field(alias="identityMappings")


    class Config:
        allow_population_by_field_name = True
        extra = "ignore"

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase]
    output_mappings: List[OutputMappingBase]
    identity_mappings: List[IdentityMappingBase]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")

class TemplateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase] = Field(alias="inputMappings")
    output_mappings: List[OutputMappingBase] = Field(alias="outputMappings")
    identity_mappings: List[IdentityMappingBase] = Field(alias="identityMappings")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

class TemplatePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    input_mappings: Optional[List[InputMappingBase]] = Field(
        default=None, alias="inputMappings"
    )
    output_mappings: Optional[List[OutputMappingBase]] = Field(
        default=None, alias="outputMappings"
    )
    identity_mappings: Optional[List[IdentityMappingBase]] = Field(
        default=None, alias="identityMappings"
    )


    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    
class ResultLogsResponse(BaseModel):
    id: int
    datetime_started: datetime
    datetime_ended: datetime
    duration_seconds: int
    template_id: int
    excel_filename: str
    csv_filename: Optional[str]
    num_of_records: int
    processed_records: int
    download_link_json: Optional[str]
    download_link_csv: Optional[str]
    
    
def template_to_pydantic(db_template: Template) -> TemplateCreate:
    return TemplateCreate(
        name=db_template.name,
        description=db_template.description,
        input_mappings=[
            InputMappingBase(
                name=im.name,
                source=im.source,
                cell=im.cell,
                forced_value=im.forced_value
            ) for im in db_template.input_mappings
        ],
        output_mappings=[
            OutputMappingBase(
                field=om.field,
                cell=om.cell
            ) for om in db_template.output_mappings
        ],
        identity_mappings=[
            IdentityMappingBase(
                name=idm.name
            ) for idm in db_template.identity_mappings
        ]
    )


