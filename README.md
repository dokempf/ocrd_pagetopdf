# ocrd-pagetopdf

> OCR-D wrapper for prima-page-to-pdf

[![Python CI](https://github.com/UB-Mannheim/ocrd_pagetopdf/actions/workflows/ci.yml/badge.svg)](https://github.com/UB-Mannheim/ocrd_pagetopdf/actions/workflows/ci.yml)
[![Docker CD](https://github.com/UB-Mannheim/ocrd_pagetopdf/actions/workflows/docker.yml/badge.svg)](https://github.com/UB-Mannheim/ocrd_pagetopdf/actions/workflows/docker.yml)
[![PyPI CD](https://img.shields.io/pypi/v/ocrd-pagetopdf.svg)](https://pypi.org/project/ocrd-pagetopdf/)

Contents:
 * [Introduction](#introduction)
 * [Requirements](#requirements)
 * [Installation](#installation)
    * [With Docker](#with-docker)
    * [Native, from PyPI](#native-from-pypi)
    * [Native, from git](#native-from-git)
 * [Usage](#usage)
    * [ocrd-pagetopdf](#ocrd-pagetopdf)
    * [ocrd-altotopdf](#ocrd-altotopdf)
 * [FAQ](#faq)

## Introduction

This package offers [OCR-D](https://ocr-d.de/en/spec) compliant
[workspace processors](https://ocr-d.de/en/spec/cli) for conversion of OCR data
represented in [METS](https://ocr-d.de/en/spec/mets) (on the document level)
and [PAGE](https://ocr-d.de/en/spec/page)
or [ALTO](https://www.loc.gov/standards/alto/)
(on the page level) to PDF.

It transforms both the scan image (_facsimile_) and annotations (_text overlay_),
optionally drawing _polygon outlines_ for text regions / lines / words / glyphs.

Optionally _validates_ the structural annotation and fixes its coordinates before
attempting conversion.

The text layer is generated from the textual annotation on the configured _level_
of the structural hierarchy (region / line / word / glyph). It is rendered with a
configurable _font_ (which is useful to make sure all codepoints are covered by
adequate glyphs, esp. in historic prints and manuscripts).

The _page labels_ can be configured to use various attributes from the
physical pages of the METS.

A _table of contents_ will be added according to the labels of the
recursive `mets:div` logical structure.

## Requirements

- GNU `make`
- Python 3 with `pip` and `venv`
- [OCR-D](https://github.com/OCR-D/core)
- Java runtime (OpenJDK &ge;8 works for [PageToPdf](https://github.com/PRImA-Research-Lab/prima-page-to-pdf/releases) 1.1.2)

## Installation

### With Docker

This is the best option if you want to run the software in a container.

You need to have [Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)


    docker pull ocrd/pagetopdf


To run with docker:


    docker run -v path/to/workspaces:/data ocrd/pagetopdf ocrd-pagetopdf ...

### Native, from PyPI

This is the best option if you want to use the stable, released version.

After installing Python and Java, simply do:


    pip install ocrd_pagetopdf


### Native, from git

Use this option if you want to change the source code or install the latest, unpublished changes.

We strongly recommend to use [venv](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/).

After installing `make`, assuming you are on a Debian/Ubuntu OS, you can do:

    sudo make deps-ubuntu

Otherwise, simulate this step and install requirements with equivalent actions on your system:

    make -n deps-ubuntu
    ...

Finally, to install the Python package, do:

    make install
    # or equivalently:
    pip install .


## Usage

The command-line interface `ocrd-pagetopdf` conforms to [OCR-D processor](https://ocr-d.de/en/spec/cli) specifications.

Assuming you have an [OCR-D workspace](https://ocr-d.de/en/user_guide#preparing-a-workspace) in your current working directory, simply do:

    ocrd-pagetopdf -I PAGE-FILGRP -O PDF-FILEGRP -P textequiv_level word

This will run the script and create PDF files for each page with a text layer based on word-level annotations.

In order to create an additional multipage file for the entire document, named `merged.pdf`,
concatenating the single page PDFs in physical order and with page labels and contents, do:

    ocrd-pagetopdf -I PAGE-FILGRP -O PDF-FILEGRP -P textequiv_level word -P multipage merged

In case your workspace does not contain fulltext in **PAGE** format, but **ALTO**, there is a dedicated
processor CLI `ocrd-altotopdf`, with some limitations compared to the former:

- You need to _manually_ select the fileGrp providing the images which match the annotation coordinates,
  passing it as second input fileGrp. (The image references are required by PAGE, but not by ALTO.)
- The images are _not_ generated on-the-fly according to all annotations (from existing `AlternativeImage`s,
  or by cropping via coordinates into the higher-level image, and deskewing when applicable), and _not_
  chosen via `input_feature_selector` / `input_feature_filter` mechanism. Instead, only the original
  images can be used here.
- The annotations are _not_ tested comprehensively regarding validity and consistency of coordinates and
  then repaired. Instead, only superficial checks and repairs can be applied (like negative coordinates).

Assuming you have a workspace representing a typical [DFG-conforming](https://dfg-viewer.de/) METS,
with `FULLTEXT` for ALTO and `DEFAULT` for the original images, do:

    ocrd-altotopdf -I FULLTEXT,DEFAULT -O PDF-FILEGRP -P textequiv_level word -P multipage merged

For more options and explanations, see below.

### ocrd-pagetopdf

<details><summary>OCR-D CLI</summary>


<pre>
Usage: ocrd-pagetopdf [worker|server] [OPTIONS]

  Convert text and layout annotations from PAGE to PDF format (overlaying original image with text layer and polygon outlines)

  > Converts all pages of the document to PDF

  > For each page, open and deserialize PAGE input file and its
  > respective image. Then extract a derived image of the (cropped,
  > deskewed, binarized...) page, with features depending on
  > ``image_feature_selector`` (a comma-separated list of required image
  > features, cf. :py:func:`ocrd.workspace.Workspace.image_from_page`)
  > and ``image_feature_filter`` (a comma-separated list of forbidden
  > image features).

  > Next, generate a temporary PAGE output file for that very image
  > (adapting all coordinates if necessary). If ``negative2zero`` is
  > set, validate and repair invalid or inconsistent coordinates.

  > Convert the PAGE/image pair with PRImA PageToPdf, applying
  > - ``textequiv_level`` (i.e. `-text-source`) to retrieve a text layer, if set;
  > - ``outlines`` to draw boundary polygons, if set;
  > - ``font`` accordingly.

  > Copy the resulting PDF file to the output file group and reference
  > it in the METS.

  > Finally, if ``multipage`` is set, then concatenate all generated
  > files to a multi-page PDF file, setting ``pagelabels`` accordingly,
  > as well as PDF metadata and bookmarks. Reference it with
  > ``multipage`` as ID in the output file group, too. If
  > ``multipage_only`` is also set, then remove the single-page PDF
  > files afterwards.

Subcommands:
    worker      Start a processing worker rather than do local processing
    server      Start a processor server rather than do local processing

Options for processing:
  -m, --mets URL-PATH             URL or file path of METS to process [./mets.xml]
  -w, --working-dir PATH          Working directory of local workspace [dirname(URL-PATH)]
  -I, --input-file-grp USE        File group(s) used as input
  -O, --output-file-grp USE       File group(s) used as output
  -g, --page-id ID                Physical page ID(s) to process instead of full document []
  --overwrite                     Remove existing output pages/images
                                  (with "--page-id", remove only those).
                                  Short-hand for OCRD_EXISTING_OUTPUT=OVERWRITE
  --debug                         Abort on any errors with full stack trace.
                                  Short-hand for OCRD_MISSING_OUTPUT=ABORT
  --profile                       Enable profiling
  --profile-file PROF-PATH        Write cProfile stats to PROF-PATH. Implies "--profile"
  -p, --parameter JSON-PATH       Parameters, either verbatim JSON string
                                  or JSON file path
  -P, --param-override KEY VAL    Override a single JSON object key-value pair,
                                  taking precedence over --parameter
  -U, --mets-server-url URL       URL of a METS Server for parallel incremental access to METS
                                  If URL starts with http:// start an HTTP server there,
                                  otherwise URL is a path to an on-demand-created unix socket
  -l, --log-level [OFF|ERROR|WARN|INFO|DEBUG|TRACE]
                                  Override log level globally [INFO]
  --log-filename LOG-PATH         File to redirect stderr logging to (overriding ocrd_logging.conf).

Options for information:
  -C, --show-resource RESNAME     Dump the content of processor resource RESNAME
  -L, --list-resources            List names of processor resources
  -J, --dump-json                 Dump tool description as JSON
  -D, --dump-module-dir           Show the 'module' resource location path for this processor
  -h, --help                      Show this message
  -V, --version                   Show version

Parameters:
   "image_feature_selector" [string - ""]
    comma-separated list of required image features (e.g.
    binarized,despeckled,cropped,deskewed,rotated-90)
   "image_feature_filter" [string - ""]
    comma-separated list of forbidden image features (e.g.
    binarized,despeckled,cropped,deskewed,rotated-90)
   "font" [string - ""]
    Font file to be used in PDF file. If unset, AletheiaSans.ttf is used.
    (Make sure to pick a font which covers all glyphs!)
   "outlines" [string - ""]
    What segment hierarchy to draw coordinate outlines for. If unset, no
    outlines are drawn.
    Possible values: ["", "region", "line", "word", "glyph"]
   "textequiv_level" [string - ""]
    What segment hierarchy level to render text output from. If unset, no
    text is rendered.
    Possible values: ["", "region", "line", "word", "glyph"]
   "negative2zero" [boolean - false]
    Repair invalid or inconsistent coordinates before trying to convert.
   "ext" [string - ".pdf"]
    Output filename extension
   "multipage" [string - ""]
    Merge all PDFs into one multipage file. The value is used as METS
    file ID and file basename for the PDF.
   "multipage_only" [boolean - false]
    When producing a `multipage`, do not add single-page files into the
    output fileGrp (but use a temporary directory for them).
   "pagelabel" [string - "pageId"]
    Parameter for 'multipage': Set the labels used as page outlines.

    - 'pageId': physical page ID,

    - 'pagenumber': use consecutive numbers,

    - 'pagelabel': use '@ORDERLABEL - @LABEL',

    - 'basename': use the name of the input file,

    - 'local_filename': use the href relative path of the input file,

    - 'url': use the href URL of the input file,

    - 'ID': use the file ID of the input file
    Possible values: ["pagenumber", "pagelabel", "pageId", "basename",
    "basename_without_extension", "local_filename", "ID", "url"]
   "script-args" [string - ""]
    Extra arguments to PageToPdf (see https://github.com/PRImA-Research-
    Lab/prima-page-to-pdf)
</pre>

</details>

### ocrd-altotopdf

<details><summary>OCR-D CLI</summary>


<pre>
Usage: ocrd-altotopdf [worker|server] [OPTIONS]

  Convert text and layout annotations from ALTO to PDF format (overlaying original image with text layer and polygon outlines)

  > Converts all pages of the document to PDF

  > For each page, find the ALTO input file in the first fileGrp,
  > together with the image input file in the second fileGrp.

  > Then convert ALTO to PAGE with PRImA PageConverter in a temporary
  > location.

  > Next convert the PAGE/image pair with PRImA PageToPdf in a temporary location,
  > applying
  > - ``textequiv_level`` (i.e. `-text-source`) to retrieve a text layer, if set;
  > - ``outlines`` to draw boundary polygons, if set;
  > - ``font`` accordingly;
  > - ``negative2zero`` (i.e. `-neg-coords toZero`) to repair negative coordintes.

  > Copy to the resulting PDF file to the output file group and
  > reference it in the METS.

  > Finally, if ``multipage`` is set, then concatenate all generated
  > files to a multi-page PDF file, setting ``pagelabels`` accordingly,
  > as well as PDF metadata and bookmarks. Reference it with
  > ``multipage`` as ID in the output fileGrp, too. If
  > ``multipage_only`` is also set, then remove the single-page PDF
  > files afterwards.

Subcommands:
    worker      Start a processing worker rather than do local processing
    server      Start a processor server rather than do local processing

Options for processing:
  -m, --mets URL-PATH             URL or file path of METS to process [./mets.xml]
  -w, --working-dir PATH          Working directory of local workspace [dirname(URL-PATH)]
  -I, --input-file-grp USE        File group(s) used as input
  -O, --output-file-grp USE       File group(s) used as output
  -g, --page-id ID                Physical page ID(s) to process instead of full document []
  --overwrite                     Remove existing output pages/images
                                  (with "--page-id", remove only those).
                                  Short-hand for OCRD_EXISTING_OUTPUT=OVERWRITE
  --debug                         Abort on any errors with full stack trace.
                                  Short-hand for OCRD_MISSING_OUTPUT=ABORT
  --profile                       Enable profiling
  --profile-file PROF-PATH        Write cProfile stats to PROF-PATH. Implies "--profile"
  -p, --parameter JSON-PATH       Parameters, either verbatim JSON string
                                  or JSON file path
  -P, --param-override KEY VAL    Override a single JSON object key-value pair,
                                  taking precedence over --parameter
  -U, --mets-server-url URL       URL of a METS Server for parallel incremental access to METS
                                  If URL starts with http:// start an HTTP server there,
                                  otherwise URL is a path to an on-demand-created unix socket
  -l, --log-level [OFF|ERROR|WARN|INFO|DEBUG|TRACE]
                                  Override log level globally [INFO]
  --log-filename LOG-PATH         File to redirect stderr logging to (overriding ocrd_logging.conf).

Options for information:
  -C, --show-resource RESNAME     Dump the content of processor resource RESNAME
  -L, --list-resources            List names of processor resources
  -J, --dump-json                 Dump tool description as JSON
  -D, --dump-module-dir           Show the 'module' resource location path for this processor
  -h, --help                      Show this message
  -V, --version                   Show version

Parameters:
   "font" [string - ""]
    Font file to be used in PDF file. If unset, AletheiaSans.ttf is used.
    (Make sure to pick a font which covers all glyphs!)
   "outlines" [string - ""]
    What segment hierarchy to draw coordinate outlines for. If unset, no
    outlines are drawn.
    Possible values: ["", "region", "line", "word", "glyph"]
   "textequiv_level" [string - ""]
    What segment hierarchy level to render text output from. If unset, no
    text is rendered.
    Possible values: ["", "region", "line", "word", "glyph"]
   "negative2zero" [boolean - false]
    Repair invalid or inconsistent coordinates before trying to convert.
   "ext" [string - ".pdf"]
    Output filename extension
   "multipage" [string - ""]
    Merge all PDFs into one multipage file. The value is used as METS
    file ID and file basename for the PDF.
   "multipage_only" [boolean - false]
    When producing a `multipage`, do not add single-page files into the
    output fileGrp (but use a temporary directory for them).
   "pagelabel" [string - "pageId"]
    Parameter for 'multipage': Set the labels used as page outlines.

    - 'pageId': physical page ID,

    - 'pagenumber': use consecutive numbers,

    - 'pagelabel': use '@ORDERLABEL - @LABEL',

    - 'basename': use the name of the input file,

    - 'local_filename': use the href relative path of the input file,

    - 'url': use the href URL of the input file,

    - 'ID': use the file ID of the input file
    Possible values: ["pagenumber", "pagelabel", "pageId", "basename",
    "basename_without_extension", "local_filename", "ID", "url"]
   "script-args" [string - ""]
    Extra arguments to PageToPdf (see https://github.com/PRImA-Research-
    Lab/prima-page-to-pdf)
</pre>

</details>


## FAQ

- `Illegal reflective access by com.itextpdf.text.io.ByteBufferRandomAccessSource$1 to method java.nio.DirectByteBuffer.cleaner()`
   If that appears, try installing OpenJDK 8.

- `java.lang.NullPointerException` 
  If that appears, try (a little workaround) and set negative coordinates to zero:
  
      ocrd-pagetopdf -I PAGE-FILGRP -O PDF-FILEGRP ... -P negative2zero true

- Some letters are illegible?
  Please note that the standard displayed font ([AletheiaSans.ttf](https://github.com/PRImA-Research-Lab/prima-aletheia-web/raw/master/war/aletheiasans-webfont.ttf)) does not support all Unicode glyphs. In case yours are missing, set a (monospace) Unicode font yourself:
  
      ocrd-pagetopdf -I PAGE-FILGRP -O PDF-FILEGRP ... -P font /usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf
  
  Fonts can also be referenced by file name if they are installed as [processor resources](https://ocr-d.de/en/spec/cli#processor-resources). A number of options have been preconfigured, cf. `ocrd resmgr list-available -e ocrd-pagetopdf`.

- The multipage file's page labels can be configured, e.g. consecutively via `pagelabel=pagenumber` or from `@ORDERLABEL` and `@LABEL` via `pagelabel=pagelabel`:
  
      ocrd-pagetopdf -I PAGE-FILGRP -O PDF-FILEGRP ... -P pagelabel pagelabel

