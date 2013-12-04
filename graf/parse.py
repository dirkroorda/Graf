# -*- coding: utf8 -*-

import os

from xml.sax import parse as saxparse, SAXException
from xml.sax.handler import ContentHandler

import array
import collections

aspace_not_given = "_original_"

good_regions = 0
linked_nodes = 0
good_edges = 0
good_annots = 0
good_feats = 0

faulty_regions = 0
unlinked_nodes = 0
faulty_edges = 0
faulty_annots = 0
faulty_feats = 0

annotation_files = []

identifiers_r = {}
identifiers_n = {}
identifiers_e = {}
identifiers_a = {}

id_region = 0
id_node = 0
id_edge = 0
id_annot = 0

region_begin = array.array('I')
region_end = array.array('I')
node_region_list = []
edges_from = array.array('I')
edges_to = array.array('I')
feature = collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: {}
))))
feature_val_int = collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: collections.defaultdict(
    lambda: {}
))))

class HeaderHandler(ContentHandler):
    '''Handlers used by SAX parsing the GrAF header file.

    We just collect the contents of the *loc* attributes of the *annotation* elements.
    These are the annotation files that we have to fetch and compile.
    '''
    stamp = None

    def __init__(self, stamp):
        self._tag_stack = []
        self.stamp = stamp
        pass

    def startElement(self, name, attrs):
        self._tag_stack.append(name)
        if name == "annotation":
            annotation_files.append(attrs["loc"])

    def endElement(self, name):
        self._tag_stack.pop()

    def characters(self, ch):
        name = self._tag_stack[-1]

class AnnotationHandler(ContentHandler):
    '''Handlers used by SAX parsing the annotation files themselves

    We have to collect all elements *region*, *node* and subelement *link*, *edge*, *annotationSpace*, *a* (annotation) and *f* (feature).
    From these elements we retrieve identifiers and other attributes.
    We map all identifiers to integers.
    When we have to associate one piece of data to other pieces, we create arrays of those integers.

    .. note::
        The parse process is presupposes that regions are encountered before nodes that link to them,
        nodes before edges that connect them, nodes and edges before annotations that target them.
        The creator of the LAF resource can organize the files that way. The parser reads the annotation file in the
        order specified in the Graf header file.

    Here is a description of the arrays we create:

    *region_begin*, *region_end*
        Every region has an *anchors* attribute specifying a point or interval in the primary data. We consider a point *i* as the interval *i .. i*.
        *region_begin* contains the start anchor of region *i* for each *i*, and *region_end* the end anchor.

    *edges_from*, *edges_to*
        Every edge goes from one node to an other. *edges_from* contains the from node of edge *i* for each *i*, and *edges_end* the to node.

    There is also a list of arrays:

    *node_region_list*
        Element *i* of this list contains an array with the regions attached to node *i*.

    And finally, two dictionaries:

    *feature*
        All feature values, keyed by annotation space, annotation label, feature name, kind (node or edge),
        and finally reference (id of target node or edge).
        The values are stored as integer. The mapping to the real value is stored separately.

    *feature_val_int*
        Mapping from real feature values to integer codes. Same values go to same codes, hence space is conserved.
        These mappings are set up per individual feature.

    .. note::
        We work with annotation spaces and annotation labels and we distinguish between features in
        annotations that are targeted at nodes or at edges.
        Features for nodes and features for edges occupy separate name spaces.
    '''

    file_name = None
    nid = None
    aid = None
    stamp = None

    truth = {
        'yes': True,
        '1': True,
        'on': True,
        'true': True,
    }

    def __init__(self, annotation_file, stamp):
        self.file_name = annotation_file
        self._tag_stack = []
        self.stamp = stamp
        self.aempty = None
        self.aspace_default = aspace_not_given
        self.aspace = None
        self.alabel = None
        self.atype = None
        self.aref = None
        self.node_link = None

    def startElement(self, name, attrs):
        self._tag_stack.append(name)
        if name == "annotationSpace":
            if "as.id" in attrs:
                self.aspace = attrs["as.id"]
                if "default" in attrs:
                    default = attrs["default"]
                    if default.casefold() in self.truth:
                        self.aspace_default = self.aspace
            if self.aspace == None:
                self.aspace = self.aspace_default
        elif name == "region":
            global faulty_regions
            global good_regions
            global id_region
            rid = attrs["xml:id"]
            id_region += 1
            identifiers_r[rid] = id_region
            anchors = attrs["anchors"].split(" ")
            if len(anchors) != 2:
                faulty_regions += 1
                msg = "ERROR: invalid anchor spec '{}' for region {} in {}".format(attrs["anchors"], rid, self.file_name)
                self.stamp.progress(msg)
                region_begin.append(0)
                region_end.append(0)
            else:
                good_regions += 1
                region_begin.append(int(anchors[0]))
                region_end.append(int(anchors[1]))
        elif name == "node":
            global id_node
            nid = attrs["xml:id"]
            id_node += 1
            identifiers_n[nid] = id_node
            self.node_link = None
            self.nid = nid 
        elif name == "link":
            self.node_link = attrs["targets"].split(" ")
        elif name == "edge":
            global faulty_edges
            global good_edges
            global id_edge
            eid = attrs["xml:id"]
            id_edge += 1
            identifiers_e[eid] = id_edge
            from_node = attrs["from"]
            to_node = attrs["to"]
            if not from_node or not to_node:
                faulty_edges += 1
                msg = "ERROR: invalid from/to spec from='{}' to='{}' for edge {} in {}".format(from_node, to_node, eid, self.file_name)
                self.stamp.progress(msg)
                print(msg)
            else:
                good_edges += 1
                edges_from.append(identifiers_n[from_node])
                edges_to.append(identifiers_n[to_node])
        elif name == "a":
            global faulty_annots
            global good_annots
            global id_annot
            aid = attrs["xml:id"]
            id_annot += 1
            identifiers_a[aid] = id_annot
            self.aid = aid
            self.aempty = True
            if "as.id" in attrs:
                self.aspace = attrs["as.id"]
            else:
                self.aspace = self.aspace_default
            self.alabel = attrs["label"]
            node_or_edge = attrs["ref"]
            if not self.alabel or not node_or_edge:
                faulty_annots += 1
                msg = "ERROR: invalid annotation spec label='{}' ref='{}' for annotation {} in {}".format(self.alabel, node_or_edge, self.aid, self.file_name)
                self.stamp.progress(msg)
                print(msg)
            else:
                self.aref = None
                self.atype = None
                if node_or_edge in identifiers_n:
                    self.aref = identifiers_n[node_or_edge]
                    self.atype = True
                elif node_or_edge in identifiers_e:
                    self.aref = identifiers_e[node_or_edge]
                    self.atype = False
                else:
                    msg = "ERROR: invalid annotation target ref='{} (no node, no edge)' for annotation {} in {}".format(node_or_edge, self.aid, self.file_name)
                    self.stamp.progress(msg)
                    print(msg)
                good_annots += 1
        elif name == "f":
            global faulty_feats
            self.aempty = False
            fname = attrs["name"]
            if not fname:
                faulty_feats += 1
                msg = "ERROR: invalid feature spec name='{}' value='{}' for feature in annotation in file {}".format(fname, value, self.aid, self.file_name)
                self.stamp.progress(msg)
                print(msg)
            value = attrs["value"]
            self.add_feature_instance(fname, value)

    def endElement(self, name):
        if name == "node":
            global unlinked_nodes
            global linked_nodes
            if not self.node_link:
                unlinked_nodes += 1
                node_region_list.append(array.array('I', []))
            else:
                linked_nodes += 1
                node_region_list.append(array.array('I',[identifiers_r[r] for r in self.node_link]))
        elif name == "a":
            if self.aempty:
                fname = ''
                value = 1
                self.add_feature_instance(fname, value)

        self._tag_stack.pop()

    def characters(self, ch):
        pass

    def add_feature_instance(self, fname, value):
        global good_feats
        this_fv_id = None
        if value in feature_val_int[self.aspace][self.alabel][fname][self.atype]:
            this_fv_id = feature_val_int[self.aspace][self.alabel][fname][self.atype][value]
        else:
            this_fv_id = len(feature_val_int[self.aspace][self.alabel][fname][self.atype])
            feature_val_int[self.aspace][self.alabel][fname][self.atype][value] = this_fv_id
        good_feats += 1
        feature[self.aspace][self.alabel][fname][self.atype][self.aref] = this_fv_id

def parse(graf_header_file, stamp):
    '''Parse a GrAF resource.
    
    Parses a GrAF resource, starting by SAX parsing its header file and subsequently parsing all
    files mentioned in that header file.

    Args:
        graf_header_file (str):
            path to the GrAF header file

    Returns:
        a tuple of items which comprise the parse results.

    Every member of the returned tuple is itself a tuple of 3 pieces of information:

    #. A *key* which acts as a name for this part of the result data
    #. The data itself, as described in :class:`AnnotationHandler`
    #. A boolean indicating whether this data is a temporary result or a permanent result

    Temporary results will be discarded after the remodeling step, permanent results will be incorporated in 
    the task-executing object.
    '''

    global annotation_files
    annotation_files = []
    saxparse(graf_header_file, HeaderHandler(stamp))

    for annotation_file in annotation_files:
        msg = "parsing {}".format(annotation_file)
        stamp.progress(msg)
        saxparse(annotation_file, AnnotationHandler(annotation_file, stamp))

    msg = '''END PARSING
{:>10} good   regions  and {:>5} faulty ones
{:>10} linked nodes    and {:>5} unlinked ones
{:>10} good   edges    and {:>5} faulty ones
{:>10} good   annots   and {:>5} faulty ones
{:>10} good   features and {:>5} faulty ones
{:>10} distinct xml identifiers
'''.format(
        good_regions, faulty_regions,
        linked_nodes, unlinked_nodes,
        good_edges, faulty_edges,
        good_annots, faulty_annots,
        good_feats, faulty_feats,  
        id_region + id_node + id_edge + id_annot
    )
    stamp.progress(msg)
    return (
        ("xid_int", {True: identifiers_n, False: identifiers_e}, True),
        ("region_begin", region_begin, True),
        ("region_end", region_end, True),
        ("node_region_list", node_region_list, False),
        ("edges_from", edges_from, True),
        ("edges_to", edges_to, True),
        ("feature", feature, True),
        ("feature_val_int", feature_val_int, True),
    )


