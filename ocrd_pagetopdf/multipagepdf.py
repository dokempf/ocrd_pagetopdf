from __future__ import absolute_import

from typing import Dict, List, Optional
import os.path
from tempfile import TemporaryDirectory
from logging import getLogger
import subprocess

from ocrd_models.constants import NAMESPACES as NS

def get_metadata(mets):
    title = mets._tree.getroot().find('.//mods:title', NS)
    subtitle = mets._tree.getroot().find('.//mods:subtitle', NS)
    title = title.text if title is not None else ""
    title += "Subtitle: "+subtitle.text if subtitle else ""
    publisher = mets._tree.getroot().find('.//mods:publisher', NS)
    author = mets._tree.getroot().find('.//mods:creator', NS)
    return {
        'Author': author.text if author is not None else "",
        'Title': title,
        'Keywords': publisher.text+" (Publisher)" if publisher is not None else "",
    }

def read_from_mets(mets, filegrp, page_ids, pagelabel='pageId'):
    inputfiles = []
    pagelabels = []
    for f in mets.find_files(mimetype='application/pdf', fileGrp=filegrp, pageId=page_ids or None):
        # ignore existing multipage PDFs
        if f.pageId:
            inputfiles.append(f.local_filename)
            if pagelabel != "pagenumber":
                pagelabels.append(getattr(f, pagelabel, ""))
    return inputfiles, pagelabels

def create_pdfmarks(directory: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None) -> str:
    pdfmarks = os.path.join(directory, 'pdfmarks.ps')
    with open(pdfmarks, 'w') as marks:
        if metadata:
            marks.write("[ ")
            for metakey, metaval in metadata.items():
                if metaval:
                    marks.write(f"/{metakey} ({metaval})\n")
            marks.write("/DOCINFO pdfmark\n")
        if pagelabels:
            marks.write("[{Catalog} <<\n\
                    /PageLabels <<\n\
                    /Nums [\n")
            for idx, pagelabel in enumerate(pagelabels):
                #marks.write(f"1 << /S /D /St 10>>\n")
                marks.write(f"{idx} << /P ({pagelabel}) >>\n")
            marks.write("] >> >> /PUT pdfmark")
    return pdfmarks

def pdfmerge(inputfiles: List[str], outputfile: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None, log=None) -> bool:
    if log is None:
        log = getLogger('ocrd.processor.pagetopdf')
    inputfiles = ' '.join(inputfiles)
    with TemporaryDirectory() as tmpdir:
        pdfmarks = create_pdfmarks(tmpdir, pagelabels, metadata)
        result = subprocess.run(
            "gs -sDEVICE=pdfwrite -dNOPAUSE -dBATCH -dSAFER "
            f"-sOutputFile={outputfile} {inputfiles} {pdfmarks}",
            shell=True, text=True, capture_output=True,
            # does not show stdout and stderr:
            #check=True,
            encoding="utf-8",
        )
        if result.stdout:
            log.debug("gs stdout: %s", result.stdout)
        if result.stderr:
            log.warning("gs stderr: %s", result.stderr)
        if result.returncode != 0:
            log.error("gs command for multipage PDF %s failed - %s", outputfile, result)
            return False
    return True
