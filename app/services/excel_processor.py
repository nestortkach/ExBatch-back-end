import openpyxl
import tempfile
import csv, re, uuid, io
from pathlib import Path
from io import BytesIO
from app.settings import STORAGE_DIR
from app.schemas import TemplateCreate
import xlwings as xw

_CELL_RGX = re.compile(r"([A-Z]+)(\d+)", re.I)
def _split(cell: str) -> tuple[str, int]:
    col, row = _CELL_RGX.fullmatch(cell).groups()
    return col.upper(), int(row)

def process_excel_file(
    file_bytes: bytes,
    template: TemplateCreate,
    csv_rows
) -> str:

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
        id_maps.append(idm.name)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    results = []
    app = xw.App(visible=False)
    try:
        wb = app.books.open(tmp_path)

        for csv_row in csv_rows:
            for sh, col, r, key, forced in in_maps:
                val = forced if forced is not None else csv_row.get(key, "")
                sheet = wb.sheets[sh]
                sheet.range(f"{col}{r}").value = val

            out_row = {}
            for sh, col, r, field in out_maps:
                sheet = wb.sheets[sh]
                result = sheet.range(f"{col}{r}").value
                print(f"Evaluating {sh}!{col}{r} -> {result}")
                out_row[field] = result or 0

            identity_data = {key: csv_row.get(key, "") for key in id_maps}
            combined_row = {**identity_data, **out_row}
            results.append(combined_row)
            
            print("Input mappings:", in_maps)
            print("Output mappings:", out_maps)
            print("ID mappings:", id_maps)

        wb.close()
    finally:
        app.quit()

    header = id_maps + [m.field for m in template.output_mappings]

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=header)
    writer.writeheader()
    writer.writerows(results)

    return sio.getvalue()