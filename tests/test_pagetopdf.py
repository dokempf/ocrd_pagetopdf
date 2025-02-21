# pylint: disable=import-error

import os

from ocrd import run_processor
from ocrd_utils import MIMETYPE_PAGE
from ocrd_models.constants import NAMESPACES

from ocrd_pagetopdf.page_processor import PAGE2PDF

PARAM = {
    "pagelabel": "pagelabel",
    "multipage": "FULLDOWNLOAD",
    "textequiv_level": "line",
    "outlines": "region",
    "negative2zero": True,
    "image_feature_filter": "binarized",
}

def test_convert(workspace_aufklaerung):
    run_processor(PAGE2PDF,
                  input_file_grp="OCR-D-GT-PAGE",
                  output_file_grp="OCR-D-GT-PDF",
                  parameter=PARAM,
                  **workspace_aufklaerung,
    )
    ws = workspace_aufklaerung['workspace']
    ws.save_mets()
    assert os.path.isdir(os.path.join(ws.directory, 'OCR-D-GT-PDF'))
    results = ws.find_files(file_grp='OCR-D-GT-PDF', mimetype="application/pdf")
    result0 = next(results, False)
    assert result0, "found no output PDF files"
    assert len(list(results)) > 1
    results = ws.find_files(file_grp='OCR-D-GT-PDF', file_id="FULLDOWNLOAD", mimetype="application/pdf")
    result0 = next(results, False)
    assert result0, "found no output multi-page PDF file"
