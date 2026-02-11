"""
extract_excel.py — Excel Sheet Preprocessing

Provides get_structured_xlsx_sheet() for loading and normalizing an
Excel file into a structured openpyxl sheet (merged cells expanded,
cell values preprocessed).
"""

import re
import openpyxl

from utils.sheet_utils import sheet2structure


def preprocess_cell(value):
    """Normalize a single cell value to string."""
    value = str(value)
    return value


def preprocess_sheet(sheet):
    """Apply preprocess_cell() to every non-merged cell in the sheet."""
    from openpyxl.cell.cell import MergedCell
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell, MergedCell):
                continue
            if cell.value is not None:
                cell.value = preprocess_cell(cell.value)
    return sheet


def get_structured_xlsx_sheet(file):
    """Load an Excel file, expand merged cells, and preprocess all values."""
    wb = openpyxl.load_workbook(file, data_only=True)
    sheet = wb.active
    sheet = sheet2structure(sheet)
    sheet = preprocess_sheet(sheet)
    return sheet
