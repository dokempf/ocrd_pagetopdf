from __future__ import absolute_import

from typing import Optional, get_args
import itertools
import os
from shutil import copyfile
from tempfile import TemporaryDirectory
import subprocess

import numpy as np
from scipy.sparse.csgraph import minimum_spanning_tree
from shapely.geometry import Polygon, LineString
from shapely.geometry.polygon import orient
from shapely import set_precision
from shapely.ops import unary_union, nearest_points

from ocrd import Processor, Workspace
from ocrd.mets_server import ClientSideOcrdMets
from ocrd_models.ocrd_file import OcrdFileType
from ocrd_utils import (
    coordinates_of_segment,
    points_from_polygon,
    polygon_from_points,
    resource_filename,
    make_file_id,
    REGEX_FILE_ID,
    config,
)
from ocrd_models.ocrd_page import (
    TextRegionType,
    BorderType,
    PageType,
    OcrdPage,
    to_xml
)
from ocrd_modelfactory import page_from_file
from ocrd_validators.page_validator import (
    CoordinateConsistencyError,
    CoordinateValidityError,
    PageValidator
)

from . import multipagepdf


class PAGE2PDF(Processor):

    @property
    def executable(self):
        return 'ocrd-pagetopdf'

    def setup(self):
        self.cliparams = ["java", "-jar", str(resource_filename('ocrd_pagetopdf', 'PageToPdf.jar'))]
        if not self.parameter['textequiv_level']:
            self.logger.warning("If you want to add a text layer, set 'textequiv_level'!")
        else:
            self.cliparams.extend([
                "-text-source", self.parameter['textequiv_level'][0]
            ])
        if self.parameter['font']:
            self.cliparams.extend([
                "-font", self.resolve_resource(self.parameter['font'])
            ])
        if self.parameter['outlines']:
            self.cliparams.extend([
                "-outlines", self.parameter['outlines'][0]
            ])
        self.cliparams.extend(self.parameter['script-args'].split())

    def process_workspace(self, workspace: Workspace) -> None:
        super().process_workspace(workspace)
        if self.parameter['multipage']:
            output_file_id = self.parameter['multipage']
            if not REGEX_FILE_ID.fullmatch(output_file_id):
                output_file_id = output_file_id.replace(':', '_')
                output_file_id = re.sub(r'^([^a-zA-Z_])', r'id_\1', output_file_id)
                output_file_id = re.sub(r'[^\w.-]', r'', output_file_id)
            output_file_path = os.path.join(self.output_file_grp, self.parameter['multipage'])
            if not output_file_path.lower().endswith('.pdf'):
                output_file_path += '.pdf'
            self.logger.info("aggregating multi-page PDF to %s", output_file_path)
            pdffiles, pagelabels = multipagepdf.read_from_mets(
                workspace.mets, self.output_file_grp, self.page_id,
                pagelabel=self.parameter['pagelabel']
            )
            if not pdffiles:
                self.logger.warning("No single-page files, skipping multi-page output '%s'", output_file_path)
                return
            if isinstance(workspace.mets, ClientSideOcrdMets):
                # we cannot use METS Server for MODS queries
                # instantiate (read and parse) METS from disk (read-only, metadata are constant)
                ws = Workspace(workspace.resolver, workspace.directory,
                               mets_basename=os.path.basename(workspace.mets_target))
                metadata = multipagepdf.get_metadata(ws.mets)
            else:
                metadata = multipagepdf.get_metadata(workspace.mets)
            multipagepdf.pdfmerge(
                pdffiles, output_file_path,
                pagelabels=pagelabels, metadata=metadata,
                log=self.logger)
            workspace.add_file(
                file_id=output_file_id,
                file_grp=self.output_file_grp,
                local_filename=output_file_path,
                mimetype="application/pdf",
                page_id=None,
                force=config.OCRD_EXISTING_OUTPUT == 'OVERWRITE',
            )

    def process_page_file(self, input_file: OcrdFileType) -> None:
        """Converts all pages of the document to PDF

        Open and deserialize PAGE input files and their respective images,
        then go to the page hierarchy level... FIXME
        """
        assert isinstance(input_file, get_args(OcrdFileType))
        page_id = input_file.pageId
        self._base_logger.info("processing page %s", page_id)
        self._base_logger.debug(f"parsing file {input_file.ID} for page {page_id}")
        try:
            page_ = page_from_file(input_file)
            assert isinstance(page_, OcrdPage)
            input_pcgts = page_
        except ValueError as err:
            # not PAGE and not an image to generate PAGE for
            self._base_logger.error(f"non-PAGE input for page {page_id}: {err}")
            return
        output_file_id = make_file_id(input_file, self.output_file_grp)
        output_file = next(self.workspace.mets.find_files(ID=output_file_id), None)
        if output_file and config.OCRD_EXISTING_OUTPUT != 'OVERWRITE':
            # short-cut avoiding useless computation:
            raise FileExistsError(
                f"A file with ID=={output_file_id} already exists {output_file} and neither force nor ignore are set"
            )
        output_file_path = os.path.join(self.output_file_grp, output_file_id + self.parameter['ext'])

        # --- equivalent of process_page_pcgts vvv
        pcgts = input_pcgts
        page = pcgts.get_Page()
        # get maximally annotated image matching requested features
        feature_selector = self.parameter['image_feature_selector']
        feature_filter = self.parameter['image_feature_filter']
        page_image, page_coords, _ = self.workspace.image_from_page(
            page, page_id,
            feature_filter=feature_filter,
            feature_selector=feature_selector
        )
        # get matching PAGE (transform all coordinates)
        page.set_Border(None)
        page.set_orientation(None)
        for region in page.get_AllRegions():
            region_polygon = coordinates_of_segment(region, page_image, page_coords)
            region.get_Coords().set_points(points_from_polygon(region_polygon))
            if isinstance(region, TextRegionType):
                for line in region.get_TextLine():
                    line_polygon = coordinates_of_segment(line, page_image, page_coords)
                    line.get_Coords().set_points(points_from_polygon(line_polygon))
                    for word in line.get_Word():
                        word_polygon = coordinates_of_segment(word, page_image, page_coords)
                        word.get_Coords().set_points(points_from_polygon(word_polygon))
                        for glyph in word.get_Glyph():
                            glyph_polygon = coordinates_of_segment(glyph, page_image, page_coords)
                            glyph.get_Coords().set_points(points_from_polygon(glyph_polygon))
        page.set_imageWidth(page_image.width)
        page.set_imageHeight(page_image.height)
        page.set_imageFilename("image.png")
        if self.parameter['negative2zero']:
            self._repair(pcgts)

        # write image and PAGE into temporary directory and convert
        with TemporaryDirectory(suffix=page_id) as tmpdir:
            img_path = os.path.join(tmpdir, "image.png")
            page_path = os.path.join(tmpdir, "page.xml")
            out_path = os.path.join(tmpdir, "page.pdf") # self.parameter['ext']
            with open(img_path, "wb") as img_file:
                page_image.save(img_file, format="PNG")
            with open(page_path, "w") as page_file:
                page_file.write(to_xml(pcgts))
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
            if not os.path.exists(out_path):
                raise Exception("PageToPdf result is empty", result)
            os.makedirs(self.output_file_grp, exist_ok=True)
            copyfile(out_path, output_file_path)
        # --- equivalent of process_page_pcgts ^^^

        # add to METS
        self.workspace.add_file(
            file_id=output_file_id,
            file_grp=self.output_file_grp,
            page_id=page_id,
            local_filename=output_file_path,
            mimetype='application/pdf',
        )

    def _repair(self, pcgts):
        # instead of ad-hoc repairs, just run the PAGE validator,
        # then proceed as in ocrd-segment-repair
        report = PageValidator.validate(
            ocrd_page=pcgts,
            page_textequiv_consistency='off',
            check_baseline=False)
        page = pcgts.get_Page()
        for error in report.errors:
            if isinstance(error, (CoordinateConsistencyError,CoordinateValidityError)):
                if error.tag == 'Page':
                    element = page.get_Border()
                elif error.tag.endswith('Region'):
                    element = next((region
                                    for region in page.get_AllRegions()
                                    if region.id == error.ID), None)
                elif error.tag == 'TextLine':
                    element = next((line
                                    for region in page.get_AllRegions(classes=['Text'])
                                    for line in region.get_TextLine()
                                    if line.id == error.ID), None)
                elif error.tag == 'Word':
                    element = next((word
                                    for region in page.get_AllRegions(classes=['Text'])
                                    for line in region.get_TextLine()
                                    for word in line.get_Word()
                                    if word.id == error.ID), None)
                elif error.tag == 'Glyph':
                    element = next((glyph
                                    for region in page.get_AllRegions(classes=['Text'])
                                    for line in region.get_TextLine()
                                    for word in line.get_Word()
                                    for glyph in word.get_Glyph()
                                    if glyph.id == error.ID), None)
                else:
                    self.logger.error("Unrepairable error for unknown segment type: %s",
                                      str(error))
                    continue
                if not element:
                    self.logger.error("Unrepairable error for unknown segment element: %s",
                              str(error))
                    continue
                try:
                    if isinstance(error, CoordinateConsistencyError):
                        ensure_consistent(element)
                    else:
                        ensure_valid(element)
                except Exception as e:
                    self.logger.error(str(e)) # exc_info=e
                    continue
                self.logger.info("Fixed %s for %s '%s'", error.__class__.__name__,
                                 error.tag, error.ID)
            else:
                self.logger.warning("Ignoring other validation error: %s", str(error))


# remaineder is from ocrd_segment:

def join_polygons(polygons, scale=20):
    """construct concave hull (alpha shape) from input polygons by connecting their pairwise nearest points"""
    # ensure input polygons are simply typed and all oriented equally
    polygons = [orient(poly)
                for poly in itertools.chain.from_iterable(
                        [poly.geoms
                         if poly.geom_type in ['MultiPolygon', 'GeometryCollection']
                         else [poly]
                         for poly in polygons])]
    npoly = len(polygons)
    if npoly == 1:
        return polygons[0]
    # find min-dist path through all polygons (travelling salesman)
    pairs = itertools.combinations(range(npoly), 2)
    dists = np.zeros((npoly, npoly), dtype=float)
    for i, j in pairs:
        dist = polygons[i].distance(polygons[j])
        if dist < 1e-5:
            dist = 1e-5 # if pair merely touches, we still need to get an edge
        dists[i, j] = dist
        dists[j, i] = dist
    dists = minimum_spanning_tree(dists, overwrite=True)
    # add bridge polygons (where necessary)
    for prevp, nextp in zip(*dists.nonzero()):
        prevp = polygons[prevp]
        nextp = polygons[nextp]
        nearest = nearest_points(prevp, nextp)
        bridgep = orient(LineString(nearest).buffer(max(1, scale/5), resolution=1), -1)
        polygons.append(bridgep)
    jointp = unary_union(polygons)
    assert jointp.geom_type == 'Polygon', jointp.wkt
    # follow-up calculations will necessarily be integer;
    # so anticipate rounding here and then ensure validity
    jointp2 = set_precision(jointp, 1.0)
    if jointp2.geom_type != 'Polygon' or not jointp2.is_valid:
        jointp2 = Polygon(np.round(jointp.exterior.coords))
        jointp2 = make_valid(jointp2)
    assert jointp2.geom_type == 'Polygon', jointp2.wkt
    return jointp2

def make_valid(polygon):
    """Ensures shapely.geometry.Polygon object is valid by repeated rearrangement/simplification/enlargement."""
    points = list(polygon.exterior.coords)
    # try by re-arranging points
    for split in range(1, len(points)):
        if polygon.is_valid or polygon.simplify(polygon.area).is_valid:
            break
        # simplification may not be possible (at all) due to ordering
        # in that case, try another starting point
        polygon = Polygon(points[-split:]+points[:-split])
    # try by simplification
    for tolerance in range(int(polygon.area + 1.5)):
        if polygon.is_valid:
            break
        # simplification may require a larger tolerance
        polygon = polygon.simplify(tolerance + 1)
    # try by enlarging
    for tolerance in range(1, int(polygon.area + 2.5)):
        if polygon.is_valid:
            break
        # enlargement may require a larger tolerance
        polygon = polygon.buffer(tolerance)
    assert polygon.is_valid, polygon.wkt
    return polygon

def merge_poly(poly1, poly2):
    poly = poly1.union(poly2)
    if poly.geom_type == 'MultiPolygon':
        #poly = poly.convex_hull
        poly = join_polygons(poly.geoms)
    if poly.minimum_clearance < 1.0:
        poly = Polygon(np.round(poly.exterior.coords))
    poly = make_valid(poly)
    return poly

def clip_poly(poly1, poly2):
    poly = poly1.intersection(poly2)
    if poly.is_empty or poly.area == 0.0:
        return None
    if poly.geom_type == 'GeometryCollection':
        # heterogeneous result: filter zero-area shapes (LineString, Point)
        poly = unary_union([geom for geom in poly.geoms if geom.area > 0])
    if poly.geom_type == 'MultiPolygon':
        # homogeneous result: construct convex hull to connect
        #poly = poly.convex_hull
        poly = join_polygons(poly.geoms)
    if poly.minimum_clearance < 1.0:
        # follow-up calculations will necessarily be integer;
        # so anticipate rounding here and then ensure validity
        poly = Polygon(np.round(poly.exterior.coords))
        poly = make_valid(poly)
    return poly

def page_poly(page):
    return Polygon([[0, 0],
                    [0, page.get_imageHeight()],
                    [page.get_imageWidth(), page.get_imageHeight()],
                    [page.get_imageWidth(), 0]])

# same as polygon_for_parent pattern in other processors
def ensure_consistent(child, at_parent=False):
    """Make segment coordinates fit into parent coordinates.

    Ensure that the coordinate polygon of ``child`` is fully
    contained in the coordinate polygon of its parent.

    \b
    To achieve that when necessary, either
    - enlarge the parent to the union of both,
      if ``at_parent``
    - shrink the child to the intersection of both,
      otherwise.

    In any case, ensure the resulting polygon is valid.

    If the parent is at page level, and there is no Border,
    then use the page frame (and assume `at_parent=False`).

    If ``child`` is at page level, and there is a Border,
    then use the page frame as parent (and assume `at_parent=False`).
    """
    if isinstance(child, PageType):
        if not child.get_Border():
            return
        childp = Polygon(polygon_from_points(child.get_Border().get_Coords().points))
        parentp = page_poly(child)
        at_parent = False # clip to page frame
        parent = child
    elif isinstance(child, BorderType):
        childp = Polygon(polygon_from_points(child.get_Coords().points))
        parentp = page_poly(child.parent_object_)
        at_parent = False # clip to page frame
        parent = child.parent_object_
    else:
        points = child.get_Coords().points
        polygon = polygon_from_points(points)
        parent = child.parent_object_
        childp = Polygon(polygon)
        if isinstance(parent, PageType):
            if parent.get_Border():
                parentp = Polygon(polygon_from_points(parent.get_Border().get_Coords().points))
            else:
                parentp = page_poly(parent)
                at_parent = False # clip to page frame
        else:
            parentp = Polygon(polygon_from_points(parent.get_Coords().points))
    # ensure input coords have valid paths (without self-intersection)
    # (this can happen when shapes valid in floating point are rounded)
    childp = make_valid(childp)
    parentp = make_valid(parentp)
    if childp.within(parentp):
        return
    # enlargement/clipping is necessary
    if at_parent:
        # enlarge at parent
        unionp = merge_poly(childp, parentp)
        polygon = unionp.exterior.coords[:-1] # keep open
        points = points_from_polygon(polygon)
        parent.get_Coords().set_points(points)
    else:
        # clip to parent
        interp = clip_poly(childp, parentp)
        if interp is None:
            raise Exception("Segment '%s' does not intersect its parent '%s'" % (
                child.id, parent.id))
        polygon = interp.exterior.coords[:-1] # keep open
        points = points_from_polygon(polygon)
        child.get_Coords().set_points(points)

def ensure_valid(element):
    changed = False
    coords = element.get_Coords()
    points = coords.points
    polygon = polygon_from_points(points)
    array = np.array(polygon, int)
    if array.min() < 0:
        array = np.maximum(0, array)
        changed = True
    if array.shape[0] < 3:
        array = np.concatenate([
            array, array[::-1] + 1])
        changed = True
    polygon = array.tolist()
    poly = Polygon(polygon)
    if not poly.is_valid:
        poly = make_valid(poly)
        polygon = poly.exterior.coords[:-1]
        changed = True
    if changed:
        points = points_from_polygon(polygon)
        coords.set_points(points)
