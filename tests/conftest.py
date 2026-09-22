"""Shared fixtures. The tools are hyphenated scripts, so they are loaded by path."""

import importlib.util
import os
import sys

import openpyxl
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import qa_common  # noqa: E402

HEADER = ["country_code", "city", "postal_code", "address", "business_name",
          "franchise_flag", "franchise_name", "branch_count", "category", "subcategory", "website"]


def load_tool(filename):
    name = filename.replace("-", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(**values):
    base = {h: "" for h in HEADER}
    base.update(values)
    return [base[h] for h in HEADER]


def write_workbook(path, sheets):
    """sheets: {name: [header, *rows]} (rows as lists)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    wb.save(path)
    return str(path)


@pytest.fixture(autouse=True)
def quiet_logs():
    qa_common.setup_logging()
    qa_common.LOG.setLevel("WARNING")
