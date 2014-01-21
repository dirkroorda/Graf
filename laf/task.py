import os
import imp
import sys
import time
import subprocess
import collections

import array
import pickle

from .laf import Laf

class Feature(object):
    '''This class is responsible for making the information in a single feature accessible to 
    tasks.

    It has a reference to the underlying information of the feature, it stores its *kind*
    (node or edge) as string (``node`` or ``edge``).

    It also gives a feature a fully qualified name that can act as an identifier.
    In fact, these names will be used as member names of the :class:`Features` class, when its objects
    store sets of features. 

    A feature's data may come from the source or the annox or both. They get merged here, and from 
    then on it is impossible to see where a feature value comes from.

    If you want to separate features from annox and source, give features in the annox other names,
    or give their containing annotations other labels, or put them in other
    annotation spaces.

    '''
    def __init__(self, laftask, aspace, alabel, fname, kind, extra=False):
        '''Upon creation, makes references to the feature data corresponding to the feature specified.

        Args:
            laftask(:class:`LafTask <laf.task.LafTask>`):
                The task executing object that has all the data.
            aspace, alabel, fname, kind:
                The annotation space, annotation label, feature name, feature kind (node or edge)
                that together identify a single feature.
            extra (bool):
                indication of where to look for the feature data, because up till now annox feature data
                sits in another dictionary than source feature data.
        '''
        self.source = laftask
        self.fspec = "{}:{}.{} ({})".format(aspace, alabel, fname, kind)
        self.local_name = "{}_{}_{}{}".format(aspace, alabel, fname, '' if kind == 'node' else '_e')
        self.edge_name = "{}_{}_{}".format(aspace, alabel, fname)
        self.kind = kind
        ref_label = 'xfeature' if extra else 'feature'
        self.lookup = collections.defaultdict(lambda: None, laftask.data_items[ref_label][(aspace, alabel, fname, kind)])

    def add_data(self, laftask, aspace, alabel, fname, kind):
        '''Upon creation, makes references to the feature data corresponding to the feature specified.

        Args:
            laftask(:class:`LafTask <laf.task.LafTask>`):
                The task executing object that has all the data.
            aspace, alabel, fname, kind:
                The annotation space, annotation label, feature name, feature kind (node or edge)
                that together identify a single feature.
        '''
        lookup = laftask.data_items['xfeature'][(aspace, alabel, fname, kind)]
        for ne in lookup:
            self.lookup[ne] = lookup[ne]

    def v(self, ne):
        '''Look the feature value up for a node or edge.

        Args:
            ne (int):
                node or edge, identified by an integer.

        Returns:
            the value of this feature for that node or edge.
        '''
        return self.lookup[ne]

    def s(self, value=None):
        '''Iterator that yields the node set that has a defined value for this feature.

        The node set is given in the canonical node set order.

        Args:
            value (str):
                if given, yields only nodes whose feature value for this feature
                is equal to it.

        Returns:
            the next node that has a defined value for this feature.
        '''
        order = self.source.data_items['node_sort_inv']
        domain = sorted(self.lookup, key=lambda x:order[x])
        if value == None:
            for n in domain:
                yield n
        else:
            for n in domain:
                if self.lookup[n] == value:
                    yield n

class Features(object):
    '''This class is responsible for holding a bunch of features and makes them 
    accessible by member names.
    '''
    def __init__(self, feature_objects):
        '''Upon creation, a set of features is taken in,
        their *local_name* members are used to create
        member names in this class.

        Args:
            feature_objects (iterable of :class:`Feature`)
        '''
        self.F = {}
        for (fn, fo) in feature_objects.items():
            exec("self.{} = fo".format(fo.local_name))
            self.F[fo.local_name] = fo.lookup

class Connections(object):
    '''This class is responsible for making adjacency information accessible to tasks.

    Adjacency information is the information needed to walk from node to node.
    Laf-Fabric organizes adjacency information in a *connections* dictionary::

        connections[«edge_feature_name»][«edge_feature_value»][«node_from»][«node_to»] = None

    for every ``«node_from»`` from which there is an edge to ``«node_to»``
    having the feature named ``«edge_feature_name»`` with value ``«edge_feature_value»``.

    The adjacency information will also be made available by member names::

        C.«edge_feature_name»[«edge_feature_value»][«node_from»][«node_to»] = None

    '''
    def __init__(self, laftask, feature_objects):
        '''Upon creation, from the edge features the adjacency information will
        be gathered.

        Args:
            laftask(:class:`LafTask <laf.task.LafTask>`):
                The task executing object that has all the data.
            feature_objects(dict):
                feature information for the declared features.
                This information is the combination of info found in the source
                and in the annox.
            edge_features(dict):
                the set of features for edges.
        '''
         
        connections = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: None))))
        edges_from = laftask.data_items["edges_from"]
        edges_to = laftask.data_items["edges_to"]
        other_edges = laftask.given['other_edges']
        edges_seen = {}
        for (feature, feature_obj) in feature_objects.items():
            if feature[3] == 'node':
                continue
            feature_name = feature_obj.edge_name
            feature_map = feature_obj.lookup
            for (edge, fvalue) in feature_map.items():
                if other_edges:
                    edges_seen[edge] = None
                node_from = edges_from[edge - 1]
                node_to = edges_to[edge - 1]
                connections[feature_name][fvalue][node_from][node_to] = None
        if other_edges:
            for edge in range(len(edges_from)):
                if edge + 1 in edges_seen:
                    continue
                node_from = edges_from[edge]
                node_to = edges_to[edge]
                connections[''][''][node_from][node_to] = None

        self.C = connections

        for fn in connections:
            fnrep = fn if fn != '' else '_none_'
            exec("self.{} = connections['{}']".format(fnrep, fn))

class XMLid(object):
    '''This class is responsible for making the original XML identifiers available
    to tasks.

    It has a reference to the relevant tables organized by *kind*
    (node or edge). There are methods to map and inverse map.
    '''
    def __init__(self, laftask, kind):
        '''Upon creation, makes a reference to the XMLid data corresponding to the kind specified.

        Args:
            laftask(:class:`LafTask <laf.task.LafTask>`):
                The task executing object that has all the data.
            kind:
                The kind (node or edge)
                for which to make available the identifiers.
        '''
        self.local_name = kind
        self.kind = kind
        self.code = laftask.data_items['xid_int'][kind]
        self.rep = laftask.data_items['xid_rep'][kind]

    def r(self, int_code):
        '''Get the XML identifier corresponding to an integer.

        Args:
            int_code (int):
                an integer code for an XML identifier in the LAF source

        Returns:
            the XML identifier that the integer stands for
        '''
        return self.rep[int_code]

    def i(self, xml_id):
        '''Get the integer code of an XML identifier.

        Args:
            xml_id (int):
                an XML identifier in the LAF source

        Returns:
            the integer code of the XML identifier
        '''
        return self.code[xml_id]

class XMLids(object):
    '''This class is responsible for holding a bunch of XML mappings (node and or edge) and makes them 
    accessible by member names.
    '''
    def __init__(self, xmlid_objects):
        '''Upon creation, a set of xmlid objects (node and or edge) is taken in,

        Args:
            xmlid_objects (iterable of :class:`XMLid`)
        '''
        for xo in xmlid_objects:
            exec("self.{} = xo".format(xo.local_name))

class PrimaryData(object):
    '''This class is responsible for giving access to the primary data.
    '''
    def __init__(self, laftask):
        '''Upon creation, the primary data is pointed to.

        Args:
            laftask(:class:`LafTask <laf.task.LafTask>`):
                The task executing object that has all the data.
        '''
        self.all_data = laftask.data_items['data']
        '''Member that holds the primary data as a single UNICODE string.
        '''
        self.laftask = laftask

    def data(self, node):
        '''Gets the primary data to which a node is linked.

        Args:
            node(int):
                The node in question

        Returns:
            None:
                if the node is not linked to regions of primary data
            List of (N, text):
                all positions *N* to which the node is linked, where *text* is the primary data
                stretch starting at position *N* that is linked to the node.
                *text* may be empty.
                The list is normalized: all stretches are maximal, non overlapping and occur
                in the order of the primary data (ascending *N*). 
        '''
        laftask = self.laftask
        regions = laftask.getitems(laftask.data_items['node_anchor'], laftask.data_items['node_anchor_items'], node)
        if not regions:
            return None
        all_text = self.all_data
        result = []
        for i in range(len(regions) // 2):
            result.append((regions[2*i], all_text[regions[2*i]:regions[2*i+1]])) 
        return result

class LafTask(Laf):
    '''Task processor.

    This class is responsible for running user tasks.
    It will import a user task, read directives for data pre-loading, and it will generate an
    API for the task, in the form of data structures for nodes and edges and 
    objects that can do feature lookups.

    A task processor must know where the source data is and where the result is going to.
    And it must be able to *import*: and :py:func:`imp.reload`: the tasks.
    To that end the search path for modules will be adapted according to the *task_dir* setting
    in the main configuration file.
    '''

    def __init__(self, settings):
        '''Upon creation, the configuration settings are stored in the object as is.

        Args:
            settings (:py:class:`configparser.ConfigParser`):
                entries corresponding to the main configuration file
        '''
        Laf.__init__(self, settings)

        self.result_files = []
        '''List of handles to result files created by the task through the method :meth:`add_output`'''

        cur_dir = os.getcwd()
        task_dir = self.settings['locations']['task_dir']
        task_include_dir = None if task_dir == '<' else task_dir if task_dir.startswith('/') else '{}/{}'.format(cur_dir, task_dir)
        if task_include_dir != None:
            sys.path.append(task_include_dir)

    def API(self):
        '''Return references to API data structures and methods of this class.

        
        This is what is returned (the names given are not necessarily the names by which they are used
        in end user tasks. You can give convenient, local names to these methods, e.g::

            (msg, P, NN, F, C, X) = laftask.API()

        Using these names, here is the API specification:

        msg(text, newline=True, withtime=True):
            For delivering console output, such as progress messages.
            See :meth:`progress <laf.timestamp.Timestamp.progress>`.

        P(:class:`PrimaryData`):
            Object containing the primary data and the information to which portions of it nodes are linked.
            ``P.all_data`` is the primary datastring itself, and ``P.data(n)`` gives the data that is attached to node ``n``.
            In this case, the data is returned as a tuple of pairs *(p, text)*, where *text* is a piece of text from
            the primary data and *p* its starting point in the text. The fragments come in the order in which they appear in the
            primary data and the fragments are maximal. They do not overlap, and there are no duplicates.
            A fragment can be empty.
            This happens when a region is merely a pointer and not an interval.

        NN(test=function, value=something):
            An iterator that delivers nodes in the canonical order described in :func:`model <laf.model.model>`.

            *test* must be a callable with one argument of type integer. Only nodes for which *test* delivers *something*
            are passed through, all others are skipped.

        F(:class:`Features`):
            Object containing all features declared in the task as a member. For example, the feature ``shebanq:ft.suffix`` is
            accessible as ``F.shebanq_ft_suffix`` if it is a node feature, or ``F.shebanq_ft_suffix_e`` if it is an edge feature.
            These feature objects in turn have a method to look features up. See :class:`Feature`.
            Empty annotations correspond with a feature with an empty name, having the value ``''`` (empty string) for each node
            or edge in its domain. For example, an empty edge annotation in the annotation space ``shebanq`` having label ``mother``,
            corresponds to the feature ``shebanq:mother.`` and is accessible as ``F.shebanq_mother__e``
            (note the empty feature name between the two ``_``s and note the ``_e`` suffix to indicate that this is an edge feature.

        C(:class:`Connections`):
            Object containing the adjacency information for each node.
            The adjacency information tells for each node how it is connected by outgoing edges to another node. 
            This information is organized as a dictionary::

                C.«feature_name».[«feature_value»][«node_from»][«node_to»] = None

            For edges annotated with an empty annotation, «feature_name» has the form::

                «annotation space»_«annotation label»__

            and the «feature_value» is ``''`` (the empty string).

            For edges that have not been annotated by one of the
            loaded edge features the «feature_name» is completely empty (``''``) and the «feature_value» as well.
            This only works if you declare the empty edge feature.

        X(:class:`XMLids`):
            Object containg members for XML identifier mappings for nodes and or edges, depending on what the task
            has specified. ``X.node`` contains mappings for nodes, ``X.edge`` for edges. These objects in turn have methods to 
            perform the mappings in individual cases. See :class:`XMLid`.
        ''' 

        def next_node(test=None, value=None, values=None):
            '''API: iterator of all nodes in primary data order that have a
            given value for a given feature.

            See also :meth:`next_node`.

            Args:
                test (callable):
                    Function to test whether a node should be passed on.
                    Optional. If not present, all nodes will be passed on and the parameters
                    *value* and *values* do not have effect.

                value, values (any type, list(any type)):
                    Only effective if the parameter *test* is present.
                    The values found in *value* and *values* are collected in a dictionary.
                    All nodes node, whose *test(node)* result is in this dictionary
                    are passed on, and none of the others.
            '''

            if test != None:
                test_values = {}
                if value != None:
                    test_values[value] = None
                if values != None:
                    for val in values:
                        test_values[val] = None
                for node in self.data_items["node_sort"]:
                    if test(node) in test_values:
                        yield node
            else:
                for node in self.data_items["node_sort"]:
                    yield node

        feature_objects = {}

        for feature in self.loaded['feature']:
            feature_objects[feature] = Feature(self, *feature)
        for feature in self.loaded['annox']:
            if feature in feature_objects:
                feature_objects[feature].add_data(*feature)
            else:
                feature_objects[feature] = Feature(self, *feature, extra=True)

        xmlid_objects = []

        for kind in self.given['xmlids']:
            xmlid_objects.append(XMLid(self, kind))

        return (
            self.progress,
            PrimaryData(self) if self.given['primary'] else None,
            next_node,
            Features(feature_objects),
            Connections(self, feature_objects),
            XMLids(xmlid_objects)
        )

    def run(self, source, annox, task, force_compile={}, load=None, function=None, stage=None):
        '''Run a task.

        That is:
        * Load the data
        * (Re)load the task code
        * Initialize the task
        * Run the task code
        * Finalize the task

        Args:
            source (str):
                key for the source

            annox (str):
                name of the extra annotation package

            task (str):
                the chosen task

            load (dict):
                a dictionary specifying what to load

            force_compile (dict):
                whether to force (re)compilation of the LAF source for either 'source' or 'annox'.
        '''
        if stage == None or stage == 'init':
            self.check_status(source, annox, task)
            self.stamp.reset()
            self.compile_all(force_compile)
            self.stamp.reset()

            if load == None:
                exec("import {}".format(task))
                exec("imp.reload({})".format(task))
                load = eval("{}.load".format(task))
            self.adjust_all(load)

            if function == None:
                function = eval("{}.task".format(task))

            self.stamp.reset()

            self.init_task()

        if stage == None or stage == 'execute':
            function(self) 

        if stage == None or stage == 'final':
            self.finish_task()

    def add_output(self, file_name):
        '''Opens a file for writing and stores the handle.

        Every task is advised to use this method for opening files for its output.
        The file will be closed by LAF-Fabric when the task terminates.

        Args:
            file_name (str):
                name of the output file.
                Its location is the result directory for this task and this source.

        Returns:
            A handle to the opened file.
        '''
        result_file = "{}/{}".format(self.env['result_dir'], file_name)
        handle = open(result_file, "w")
        self.result_files.append(handle)
        return handle

    def add_input(self, file_name):
        '''Opens a file for reading and stores the handle.

        Every task is advised to use this method for opening files for its input.
        The file will be closed by LAF-Fabric when the task terminates.

        Args:
            file_name (str):
                name of the input file.
                Its location is the result directory for this task and this source.

        Returns:
            A handle to the opened file.
        '''
        result_file = "{}/{}".format(self.env['result_dir'], file_name)
        handle = open(result_file, "r")
        self.result_files.append(handle)
        return handle

    def result(self, file_name=None):
        '''The location where the files of this task can be found

        Args:
            file_name (str):
                the name of the file, without path information.
                Optional. If not present, returns the path to the output directory.

        Returns:
            the path to *file_name* or the directory of the output files.
        '''
        if file_name == None:
            return self.env['result_dir']
        else:
            return "{}/{}".format(self.env['result_dir'], file_name)

    def init_task(self):
        '''Initializes the current task.

        Provide a log file, reset the timer, and issue a progress message.
        '''
        self.add_logfile()
        self.stamp.reset()
        self.progress("BEGIN TASK={} SOURCE={}".format(self.env['task'], self.env['source']))

    def finish_task(self):
        '''Finalizes the current task.

        Open result files will be closed.

        There will be a progress message, and a directory listing of the result directory,
        for the convenience of the user.
        '''

        for handle in self.result_files:
            if handle and not handle.closed:
                handle.close()
        self.result_files = []

        self.progress("END TASK {}".format(self.env['task']))
        self.flush_logfile()

        msg = []
        result_dir = self.env['result_dir']
        self.progress("Results directory:\n{}".format(result_dir))
        for name in sorted(os.listdir(path=result_dir)):
            path = "{}/{}".format(result_dir, name) 
            size = os.path.getsize(path)
            mtime = time.ctime(os.path.getmtime(path))
            msg.append("{:<30} {:>12} {}".format(name, size, mtime))
        self.progress("\n".join(msg), withtime=False)

        self.finish_logfile()

    def getitems_dict(self, data, data_items, elem):
        '''Get related items from an arrayified data structure.

        If a relation between integers and sets of integers has been stored as a double array
        by the :func:`arrayify() <laf.model.arrayify>` function,
        this is the way to look up the set of related integers for each integer.

        Args:
            data (array):
                see next

            data_items (array):
                together with *data* the arrayified data

            elem (int):
                the integer for which we want its related set of integers.

        Returns:
            a dict of the related integers, with values none.
        '''
        data_items_index = data[elem - 1]
        n_items = data_items[data_items_index]
        items = {}
        for i in range(n_items):
            items[data_items[data_items_index + 1 + i]] = None
        return items

    def getitems(self, data, data_items, elem):
        '''Get related items from an arrayified data structure.

        If a relation between integers and sets of integers has been stored as a double array
        by the :func:`arrayify() <laf.model.arrayify>` function,
        this is the way to look up the set of related integers for each integer.

        Args:
            data (array):
                see next

            data_items (array):
                together with *data* the arrayified data

            elem (int):
                the integer for which we want its related set of integers.

        Returns:
            a list of the related integers.
        '''
        data_items_index = data[elem - 1]
        n_items = data_items[data_items_index]
        return data_items[data_items_index + 1:data_items_index + 1 + n_items]

    def hasitem(self, data, data_items, elem, item):
        '''Check whether an integer is in the set of related items
        with respect to an arrayified data structure (see also :meth:`getitems_dict`).

        Args:
            data (array):
                see next

            data_items (array):
                together with *data* the arrayified data

            elem (int):
                the integer for which we want its related set of integers.

            item (int):
                the integer whose presence in the related items set is to be tested.

        Returns:
            bool: whether the integer is in the related set or not.
        '''
        return item in self.getitems_dict(data, data_items, elem) 

    def hasitems(self, data, data_items, elem, items):
        '''Check whether a set of integers intersects with the set of related items
        with respect to an arrayified data structure (see also :meth:`getitems_dict`).

        Args:
            data (array):
                see next

            data_items (array):
                together with *data* the arrayified data

            elem (int):
                the integer for which we want its related set of integers.

            items (array or list of integers):
                the set of integers
                whose presence in the related items set is to be tested.

        Returns:
            bool:
                whether one of the integers is in the related set or not.
        '''
        these_items = self.getitems_dict(data, data_items, elem) 
        found = None
        for item in items:
            if item in these_items:
                found = item
                break
        return found

    def get_task_mtime(self, task):
        '''Get the last modification date of the file that contains the task code
        '''
        task_dir = self.settings['locations']['task_dir']
        if task_dir == '<':
            return time.time()
        else:
            return os.path.getmtime('{}/{}.py'.format(task_dir, task))

    def __del__(self):
        '''Upon destruction, all file handles used by the task will be closed.
        '''
        for handle in self.result_files:
            if handle and not handle.closed:
                handle.close()
        Laf.__del__(self)



