from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from app.models import Template

class InputMappingBase(BaseModel):
    name: str
    source: str
    cell: str
    forced_value: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

class OutputMappingBase(BaseModel):
    field: str
    cell: str

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase]
    output_mappings: List[OutputMappingBase]

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase]
    output_mappings: List[OutputMappingBase]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")


def template_to_pydantic(db_template: Template) -> TemplateCreate:
    return TemplateCreate(
        name=db_template.name,
        description=db_template.description,
        input_mappings=[{
            "name": input.name,
            "source": input.source,
            "cell": input.cell,
            "forced_value": input.forced_value
        } for input in db_template.input_mappings],
        output_mappings=[{
            "field": output.field,
            "cell": output.cell
        } for output in db_template.output_mappings]
    )


class TemplateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    input_mappings: List[InputMappingBase] = Field(alias="inputMappings")
    output_mappings: List[OutputMappingBase] = Field(alias="outputMappings")

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

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

