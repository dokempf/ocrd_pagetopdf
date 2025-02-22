from __future__ import absolute_import

from typing import Optional, get_args
import os
from shutil import copyfile
from tempfile import TemporaryDirectory
import subprocess

from ocrd_models.ocrd_file import OcrdFileType
from ocrd_utils import (
    resource_filename,
    make_file_id,
    config,
)

from .page_processor import PAGE2PDF


class ALTO2PDF(PAGE2PDF):

    @property
    def executable(self):
        return 'ocrd-altotopdf'

    def setup(self):
        super().setup()
        self.cliparams2 = ["java", "-jar", str(resource_filename('ocrd_pagetopdf', 'PageConverter.jar'))]
        self.cliparams2.extend([
                "-convert-to", "LATEST",
            ])
        if self.parameter['negative2zero']:
            self.cliparams2.extend([
                "-neg-coords", "toZero",
            ])

    def process_page_file(self, *input_files: Optional[OcrdFileType]) -> None:
        """Converts all pages of the document to PDF

        For each page, find the ALTO input file in the first fileGrp,
        together with the image input file in the second fileGrp.

        Then convert ALTO to PAGE with PRImA PageConverter in a temporary location.

        \b
        Next convert the PAGE/image pair with PRImA PageToPdf in a temporary location,
        applying
        - ``textequiv_level`` (i.e. `-text-source`) to retrieve a text layer, if set;
        - ``outlines`` to draw boundary polygons, if set;
        - ``font`` accordingly;
        - ``negative2zero`` (i.e. `-neg-coords toZero`) to repair negative coordintes.

        Copy to the resulting PDF file to the output file group and reference it in the METS.

        Finally, if ``multipage`` is set, then concatenate all generated files to
        a multi-page PDF file, setting ``pagelabels`` accordingly, as well as PDF metadata
        and bookmarks. Reference it with ``multipage`` as ID in the output fileGrp, too.
        If ``multipage_only`` is also set, then remove the single-page PDF files afterwards.
        """
        assert len(input_files) == 2
        assert isinstance(input_files[0], get_args(OcrdFileType))
        assert isinstance(input_files[1], get_args(OcrdFileType))
        assert input_files[0].mimetype in ['application/alto+xml', 'text/xml']
        assert input_files[1].mimetype.startswith('image/')
        alto_file = input_files[0]
        assert os.path.exists(alto_file.local_filename)
        image_file = input_files[1]
        assert os.path.exists(image_file.local_filename)
        page_id = alto_file.pageId
        self._base_logger.info("processing page %s", page_id)
        output_file_id = make_file_id(alto_file, self.output_file_grp)
        output_file = next(self.workspace.mets.find_files(ID=output_file_id), None)
        if output_file and config.OCRD_EXISTING_OUTPUT != 'OVERWRITE':
            # short-cut avoiding useless computation:
            raise FileExistsError(
                f"A file with ID=={output_file_id} already exists {output_file} and neither force nor ignore are set"
            )
        output_file_path = os.path.join(self.output_file_grp, output_file_id + self.parameter['ext'])

        # write image and PAGE into temporary directory and convert
        with TemporaryDirectory(suffix=page_id) as tmpdir:
            alto_path = os.path.join(tmpdir, "alto.xml")
            copyfile(alto_file.local_filename, alto_path)
            page_path = os.path.join(tmpdir, "page.xml")
            converter2 = ' '.join(self.cliparams2 + ["-source-xml", alto_path, "-target-xml", page_path])
            self.logger.debug("Running command: '%s'", converter2)
            result = subprocess.run(converter2, shell=True, text=True, capture_output=True,
                                    # does not show stdout and stderr:
                                    #check=True,
                                    encoding="utf-8")
            # logging commented as long as prima-page-converter#19 is not fixed
            # if result.stdout:
            #     self.logger.debug("PageConverter for %s stdout: %s", page_id, result.stdout)
            # if result.stderr:
            #     self.logger.warning("PageConverter for %s stderr: %s", page_id, result.stderr)
            if result.returncode != 0:
                self.logger.warning("PageConverter for %s stderr: %s", page_id, result.stderr)
                raise Exception("PageConverter command failed", result)
            if not os.path.exists(page_path) or not os.path.getsize(page_path):
                self.logger.warning("PageConverter for %s stderr: %s", page_id, result.stderr)
                raise Exception("PageConverter result is empty", result)
            img_path = os.path.join(tmpdir, "image.png")
            copyfile(image_file.local_filename, img_path)
            out_path = os.path.join(tmpdir, "page.pdf") # self.parameter['ext']
            converter = ' '.join(self.cliparams + ["-xml", page_path, "-image", img_path, "-pdf", out_path])
            # execute command pattern
            self.logger.debug("Running command: '%s'", converter)
            # pylint: disable=subprocess-run-check
            result = subprocess.run(converter, shell=True, text=True, capture_output=True,
                                    # does not show stdout and stderr:
                                    #check=True,
                                    encoding="utf-8")
            if result.stdout:
                self.logger.debug("PageToPdf for %s stdout: %s", page_id, result.stdout)
            if result.stderr:
                self.logger.warning("PageToPdf for %s stderr: %s", page_id, result.stderr)
            if result.returncode != 0:
                raise Exception("PageToPdf command failed", result)
            if not os.path.exists(out_path) or not os.path.getsize(out_path):
                raise Exception("PageToPdf result is empty", result)
            os.makedirs(self.output_file_grp, exist_ok=True)
            copyfile(out_path, output_file_path)

        # add to METS
        self.workspace.add_file(
            file_id=output_file_id,
            file_grp=self.output_file_grp,
            page_id=page_id,
            local_filename=output_file_path,
            mimetype='application/pdf',
        )
