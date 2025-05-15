import openpyxl
import csv, re, uuid, io
from pathlib import Path
from io import BytesIO
from app.settings import STORAGE_DIR
from app.schemas import TemplateCreate
from xlcalculator import ModelCompiler, Evaluator

_CELL_RGX = re.compile(r"([A-Z]+)(\d+)", re.I)
def _split(cell: str) -> tuple[str, int]:
    col, row = _CELL_RGX.fullmatch(cell).groups()
    return col.upper(), int(row)

def process_excel_file(
    file_bytes: bytes,
    template: TemplateCreate,
    csv_rows
) -> str:  # returning CSV string, not Path

    in_maps, out_maps, id_maps = [], [], []

    for im in template.input_mappings:
        sh, cell = im.cell.split("!")
        col, row = _split(cell)
        in_maps.append((sh, col, row, im.name, im.forced_value))

    for om in template.output_mappings:
        sh, cell = om.cell.split("!")
        col, row = _split(cell)
        out_maps.append((sh, col, row, om.field))

    for idm in template.identity_mappings:
        # since your identity mapping has only "name" but no cell, 
        # you want to get it from CSV by that name (idm.name)
        # So just store the identity field names to extract from csv_row later
        id_maps.append(idm.name)

    mc = ModelCompiler()
    model = mc.read_and_parse_archive(BytesIO(file_bytes))
    ev = Evaluator(model)
    results = []

    for csv_row in csv_rows:
        # Set inputs in the Excel evaluator
        for sh, col, r, key, forced in in_maps:
            val = forced if forced is not None else csv_row.get(key, "")
            ev.set_cell_value(f"{sh}!{col}{r}", val)

        # Evaluate outputs
        out_row = {
            field: ev.evaluate(f"{sh}!{col}{r}") or 0
            for sh, col, r, field in out_maps
        }

        # Extract identity fields from the CSV row
        identity_data = {key: csv_row.get(key, "") for key in id_maps}

        # Combine identity data with output data, identity first
        combined_row = {**identity_data, **out_row}
        results.append(combined_row)

    # Prepare CSV header: identity fields first, then output fields
    header = id_maps + [m.field for m in template.output_mappings]

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=header)
    writer.writeheader()
    writer.writerows(results)

    return sio.getvalue()
