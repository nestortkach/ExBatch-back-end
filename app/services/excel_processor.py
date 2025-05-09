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
) -> Path:

    in_maps, out_maps = [], []

    for im in template.input_mappings:
        sh, cell = im.cell.split("!")
        col, row = _split(cell)
        in_maps.append((sh, col, row, im.name, im.forced_value))

    for om in template.output_mappings:
        sh, cell = om.cell.split("!")
        col, row = _split(cell)
        out_maps.append((sh, col, row, om.field))

    mc = ModelCompiler()
    model = mc.read_and_parse_archive(BytesIO(file_bytes))
    ev = Evaluator(model)
    results = []

    for csv_row in csv_rows:
        for sh, col, r, key, forced in in_maps:
            val = forced if forced is not None else csv_row.get(key, "")
            ev.set_cell_value(f"{sh}!{col}{r}", val)

        out_row = {
            field: ev.evaluate(f"{sh}!{col}{r}") or 0
            for sh, col, r, field in out_maps
        }
        results.append(out_row)



    sio = io.StringIO()
    header = [m.field for m in template.output_mappings]
    writer = csv.DictWriter(sio, fieldnames=header)
    writer.writeheader()
    writer.writerows(results)

    return sio.getvalue()