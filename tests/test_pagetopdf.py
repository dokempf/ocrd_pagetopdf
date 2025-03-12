# pylint: disable=import-error

import os
import pytest

from ocrd import run_processor
from ocrd_utils import MIMETYPE_PAGE
from ocrd_models.constants import NAMESPACES

from ocrd_pagetopdf.page_processor import PAGE2PDF
from ocrd_pagetopdf.alto_processor import ALTO2PDF

ALTO_PARAM = {
    "pagelabel": "pagelabel",
    "multipage": "FULLDOWNLOAD",
    "textequiv_level": "line",
    "outlines": "region",
    "negative2zero": True,
}
PAGE_PARAM = {
    "image_feature_filter": "binarized",
    **ALTO_PARAM
}
MIMETYPE_ALTO = '//text/xml|application/alto[+]xml'

def test_convert(processor_kwargs):
    ws = processor_kwargs['workspace']
    pages = processor_kwargs['page_id'].split(',')
    page1 = pages[0]
    # find last PAGE grp
    file1 = next(reversed(list(ws.find_files(page_id=page1, mimetype=MIMETYPE_PAGE))), None)
    if file1 is None:
        # find last ALTO grp
        file1 = next(reversed(list(ws.find_files(page_id=page1, mimetype=MIMETYPE_ALTO))), None)
        if file1 is None:
            pytest.skip(f"workspace asset {ws.name} has neither PAGE nor ALTO files")
        else:
            print(f"workspace {ws.name} first ALTO fileGrp is {file1.fileGrp}")
            # find last image grp
            file2 = next(reversed(list(ws.find_files(page_id=page1, mimetype="//image/.*"))), None)
            if file2 is None:
                pytest.skip(f"workspace asset {ws.name} has ALTO but no image files")
            print(f"workspace {ws.name} first image fileGrp is {file2.fileGrp}")
            processor_class = ALTO2PDF
            processor_param = ALTO_PARAM
            input_file_grp = file1.fileGrp + "," + file2.fileGrp
            output_file_grp = file1.fileGrp + "-PDF"
    else:
        print(f"workspace {ws.name} first PAGE fileGrp is {file1.fileGrp}")
        processor_class = PAGE2PDF
        processor_param = PAGE_PARAM
        input_file_grp = file1.fileGrp
        output_file_grp = input_file_grp + "-PDF"
    run_processor(processor_class,
                  input_file_grp=input_file_grp,
                  output_file_grp=output_file_grp,
                  parameter=processor_param,
                  **processor_kwargs,
    )
    ws.save_mets()
    assert os.path.isdir(os.path.join(ws.directory, output_file_grp))
    results = [file.pageId for file in ws.find_files(file_grp=output_file_grp, mimetype="application/pdf")]
    assert len(results), "found no output PDF files"
    if ws.name == 'sbb':
        pages.remove('PHYS_0005') # not in all fileGrps
    assert len(results) > len(pages)
    results = ws.find_files(file_grp=output_file_grp, file_id="FULLDOWNLOAD", mimetype="application/pdf")
    result0 = next(results, False)
    assert result0, "found no output multi-page PDF file"
