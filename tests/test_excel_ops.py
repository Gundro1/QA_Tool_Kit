import openpyxl

from conftest import load_tool, write_workbook

ops = load_tool("excel-ops.py")


def test_clean_keeps_every_sheet(tmp_path, capsys):
    path = write_workbook(tmp_path / "d.xlsx", {
        "Franchise": [["business_name"], ["  Acme  "]],
        "Solo": [["business_name"], [" Solo Shop"]],
        "Change log": [["note"], ["kept"]],
    })
    ops.clean_excel(path)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Franchise", "Solo", "Change log"]
    assert wb["Franchise"]["A2"].value == "Acme"
    assert wb["Solo"]["A2"].value == "Solo Shop"
