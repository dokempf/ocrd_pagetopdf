from __future__ import absolute_import

from datetime import datetime
from typing import Dict, List, Optional
import os.path
from tempfile import TemporaryDirectory
from logging import getLogger
import subprocess

from ocrd_models.constants import NAMESPACES as NS

def get_metadata(mets):
    mets = mets._tree.getroot()
    metshdr = mets.find('.//mets:metsHdr', NS)
    createdate = metshdr.attrib.get('CREATEDATE', '') if metshdr is not None else ''
    modifieddate = metshdr.attrib.get('LASTMODDATE', '') if metshdr is not None else ''
    creator = mets.xpath('.//mets:agent[@ROLE="CREATOR"]/mets:name', namespaces=NS)
    titlestring = ""
    titleinfos = mets.findall('.//mods:titleInfo', NS)
    for titleinfo in titleinfos:
        if titleinfo.getparent().tag == "{%s}relatedItem" % NS['mods']:
            continue
        title = titleinfo.find('.//mods:title', NS)
        titlestring += title.text if title is not None else ""
        for subtitle in titleinfo.findall('.//mods:subtitle', NS):
            titlestring += " - " + subtitle.text if subtitle else ""
        part = titleinfo.find('.//mods:partNumber', NS)
        titlestring += " - " + part.text if part else ""
        part = titleinfo.find('.//mods:partName', NS)
        titlestring += " - " + part.text if part else ""
        break
    author = (mets.xpath('.//mods:name[mods:role/text()="aut"]'
                        '/mods:namePart[@type="family" or @type="given"]', namespaces=NS) +
              mets.xpath('.//mods:name[mods:role/text()="cre"]'
                         '/mods:namePart[@type="family" or @type="given"]', namespaces=NS))
    author = next((part.text for part in author
                   if part.attrib["type"] == "given"), "") \
        + next((" " + part.text for part in author
                if part.attrib["type"] == "family"), "")
    origin = mets.find('.//mods:originInfo', NS)
    if origin is not None:
        publisher = origin.find('.//mods:publisher', NS)
        publdate = origin.find('.//mods:dateIssued', NS)
        digidate = origin.find('.//mods:dateCaptured', NS)
    publisher = publisher.text + " (Publisher)" if publisher is not None else ""
    publdate = publdate.text if publdate is not None else ""
    digidate = digidate.text if digidate is not None else ""
    def iso8601toiso32000(datestring):
        date = datetime.fromisoformat(datestring)
        offset = date.utcoffset()
        tz_hours, tz_seconds = divmod(offset.seconds if offset else 0, 3600)
        tz_minutes = tz_seconds // 60
        datestring = date.strftime("%Y%m%d%H%M%S")
        datestring += f"Z{tz_hours}'{tz_minutes}'"
        return datestring
    access = mets.find('.//mods:accessCondition', NS)
    return {
        'Author': author,
        'Title': titlestring,
        'Keywords': publisher,
        'Description': "",
        'Creator': creator[0].text if len(creator) else "",
        'Published': publdate,
        # only via XMP: 'Access condition': access.text if access is not None else "",
        'CreationDate': iso8601toiso32000(createdate) if createdate else "",
        'ModDate': iso8601toiso32000(modifieddate) if modifieddate else "",
    }

def read_from_mets(mets, filegrp, page_ids, pagelabel='pageId'):
    file_names = []
    pagelabels = []
    file_ids = []
    for f in mets.find_files(mimetype='application/pdf', fileGrp=filegrp, pageId=page_ids or None):
        # ignore existing multipage PDFs
        if f.pageId:
            file_names.append(f.local_filename)
            if pagelabel != "pagenumber":
                pagelabels.append(getattr(f, pagelabel, ""))
            file_ids.append(f.ID)
    return file_names, pagelabels, file_ids

def create_pdfmarks(directory: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None) -> str:
    pdfmarks = os.path.join(directory, 'pdfmarks.ps')
    with open(pdfmarks, 'w') as marks:
        if metadata:
            marks.write("[ ")
            for metakey, metaval in metadata.items():
                if metaval:
                    marks.write(f"/{metakey} ({metaval})\n")
            marks.write("/DOCINFO pdfmark\n")
        # fixme: add XMP-embedded metadata:
        # - DC (https://www.loc.gov/standards/mods/mods-dcsimple.html)
        # - MODS-RDF (https://www.loc.gov/standards/mods/modsrdf/primer-2.html)
        if pagelabels:
            marks.write("[{Catalog} <<\n\
                    /PageLabels <<\n\
                    /Nums [\n")
            for idx, pagelabel in enumerate(pagelabels):
                #marks.write(f"1 << /S /D /St 10>>\n")
                marks.write(f"{idx} << /P ({pagelabel}) >>\n")
            marks.write("] >> >> /PUT pdfmark")
    return pdfmarks

def pdfmerge(inputfiles: List[str], outputfile: str, pagelabels: Optional[List[str]] = None, metadata: Dict[str,str] = None, log=None) -> None:
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
            raise Exception("gs command for multipage PDF %s failed" % outputfile, result.args, result.stdout, result.stderr)
