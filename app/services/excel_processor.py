import tempfile
import openpyxl
import numpy_financial as npf
import csv, re, uuid, io
from pathlib import Path
from io import BytesIO
from app.settings import STORAGE_DIR
from app.schemas import TemplateCreate
from xlcalculator import ModelCompiler, Evaluator


def calculate_irr(values, guess=None):
    return npf.irr(values)

def parse_cell_reference(cell):
    pattern = r'^([A-Z]+)(\d+)$'
    match = re.match(pattern, cell)
    if match:
        column, row = match.groups()
        return [column, int(row)] 
    else:
        raise ValueError(f"Invalid format of the cell: {cell}")

_CELL_RGX = re.compile(r"([A-Z]+)(\d+)", re.I)
def _split(cell: str) -> tuple[str, int]:
    col, row = _CELL_RGX.fullmatch(cell).groups()
    return col.upper(), int(row)

def process_excel_file(
    file_bytes: bytes,
    template: TemplateCreate,
    csv_rows,
    skip_rows
) -> str:

    in_maps, out_maps, id_maps = [], [], []
    error_rows = []

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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    wb = openpyxl.load_workbook(tmp_path,data_only=True, keep_vba=True)
    workspace = openpyxl.load_workbook(BytesIO(file_bytes))

    mc = ModelCompiler()
    model = mc.read_and_parse_archive(BytesIO(file_bytes))
    ev = Evaluator(model)
    results = []
    processed_rows = 0
    for row_index, csv_row in enumerate(csv_rows, 1):
        try: 
            for sh, col, r, key, forced in in_maps:
                val = forced if forced is not None else csv_row.get(key, "")
                if val != "" and not forced:
                    try:
                        if isinstance(val, str) and val.replace('.', '').replace('-', '').isdigit():
                            val = float(val)
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid value “{val}” in column “{key}”. ")
                
                ev.set_cell_value(f"{sh}!{col}{r}", val)
                
            out_row = {}
            for sh, col, r, field in out_maps:
                formula_cell = f"{sh}!{col}{r}"

                workspace_sheet = workspace[sh]
                copy_workspace_sheet = wb[sh]
                
                try:
                    curr_cell = workspace_sheet[col+str(r)].value
                    if ref_cells := re.search(r"[A-Za-z]\d+", curr_cell):
                        ref_cell = workspace_sheet[ref_cells.group(0)].value
                        if "IRR" in ref_cell: 
                            list_cells = re.findall(r'([A-Z]+[0-9]+):([A-Z]+[0-9]+)', ref_cell)
                            
                            print()

                            first_num_list = parse_cell_reference(list_cells[0][0])
                            second_num_list = parse_cell_reference(list_cells[0][1])

                            list_cell = []
                            for indx in range(first_num_list[1], second_num_list[1]):
                                list_cell.append(
                                    copy_workspace_sheet[first_num_list[0] + str(indx)].value
                                )
                            result = calculate_irr(list_cell)
                        else:              
                            result = ev.evaluate(formula_cell)
                    out_row[field] = result or 0
                    
                except Exception as e:
                    raise ValueError(f"Formula calculation error in cell {formula_cell}. {str(e)}")
            identity_data = {key: csv_row.get(key, "") for key in id_maps}

            combined_row = {**identity_data, **out_row}
            results.append(combined_row)
            processed_rows += 1
        except (ValueError, TypeError) as e:
            if skip_rows:
                csv_row['id'] = row_index
                error_rows.append(csv_row)
                continue  
            else:   
                raise ValueError(f"Row {row_index} - {str(e)}")
            
    header = id_maps + [m.field for m in template.output_mappings]

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=header)
    writer.writeheader()
    writer.writerows(results)

    header1 = [] if not error_rows else list(error_rows[0].keys())

    sio_error = io.StringIO()
    writer1 = csv.DictWriter(sio_error, fieldnames=header1)
    writer1.writeheader()
    writer1.writerows(error_rows)

    return sio.getvalue(), sio_error.getvalue(), processed_rows
