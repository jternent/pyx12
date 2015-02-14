#####################################################################
# Copyright 
#   John Holland <john@zoner.org>
# All rights reserved.
#
# This software is licensed as described in the file LICENSE.txt, which
# you should have received as part of this distribution.
#
######################################################################

"""
Parse a ANSI X12N data file.  Validate against a map and codeset values.
Create XML, HTML, and 997/999 documents based on the data file.
"""

import logging

# Intrapackage imports
import pyx12.error_handler
import pyx12.error_997
import pyx12.error_999
import pyx12.error_html
import pyx12.errors
import pyx12.map_index
import pyx12.map_if
import pyx12.x12file
from pyx12.map_walker import walk_tree
import pyx12.x12xml_simple


def x12n_document(param, src_file, fd_997, fd_html,
                  fd_xmldoc=None, xslt_files=None, map_path=None):
    """
    Primary X12 validation function
    @param param: pyx12.param instance
    @param src_file: Source document
    @type src_file: string
    @param fd_997: 997/999 output document
    @type fd_997: file descriptor
    @param fd_html: HTML output document
    @type fd_html: file descriptor
    @param fd_xmldoc: XML output document
    @type fd_xmldoc: file descriptor
    @rtype: boolean
    """
    logger = logging.getLogger('pyx12')
    errh = pyx12.error_handler.err_handler()

    # Get X12 DATA file
    try:
        src = pyx12.x12file.X12Reader(src_file)
    except pyx12.errors.X12Error:
        logger.error('"%s" does not look like an X12 data file' % (src_file))
        return False

    #Get Map of Control Segments
    map_file = 'x12.control.00501.xml' if src.icvn == '00501' else 'x12.control.00401.xml'
    logger.debug('X12 control file: %s' % (map_file))
    control_map = pyx12.map_if.load_map_file(map_file, param, map_path)
    map_index_if = pyx12.map_index.map_index(map_path)
    node = control_map.getnodebypath('/ISA_LOOP/ISA')
    walker = walk_tree()
    icvn = fic = vriic = tspc = None
    cur_map = None  # we do not initially know the X12 transaction type
    #XXX Generate TA1 if needed.

    if fd_html:
        html = pyx12.error_html.error_html(errh, fd_html, src.get_term())
        html.header()
        err_iter = pyx12.error_handler.err_iter(errh)
    if fd_xmldoc:
        xmldoc = pyx12.x12xml_simple.x12xml_simple(fd_xmldoc, param.get('simple_dtd'))

    #basedir = os.path.dirname(src_file)
    #erx = errh_xml.err_handler(basedir=basedir)

    valid = True
    for seg in src:
        #find node
        orig_node = node
        error_items = [] # [('seg', err_cde, err_str, err_value, src_line)]
        if seg.get_seg_id() == 'ISA':
            node = control_map.getnodebypath('/ISA_LOOP/ISA')
            walker.forceWalkCounterToLoopStart('/ISA_LOOP', '/ISA_LOOP/ISA')
        elif seg.get_seg_id() == 'GS':
            node = control_map.getnodebypath('/ISA_LOOP/GS_LOOP/GS')
            walker.forceWalkCounterToLoopStart('/ISA_LOOP/GS_LOOP', '/ISA_LOOP/GS_LOOP/GS')
        else:
            # from the current node, find the map node matching the segment
            # keep track of the loops traversed
            try:
                # try to find match
                #(_find_node, _find_pop_loops, _find_push_loops) = walker.find(node, seg)
                #if _find_node:
                #    pass
                    # get missing and count errors for nodes between the start and end
                    #errors = walker.wander(node, seg, _find_pop_loops, _find_push_loops)
                    # do matched segment counting
                    #(isOk, errorCode, errorString) = walker.check_seg_usage(child, seg_data)
                    #if not isOk:
                    #    error_items.append(('seg', errorCode, errorString, None, src.get_cur_line()))
                #else:
                    # was not matched
                #    (isOk, errorCode, errorString) = walk_tree.format_seg_not_found_error(node, seg)
                #    error_items.append(('seg', errorCode, errorString, None, src.get_cur_line()))
                (node, pop_loops, push_loops, error_items) = walker.walk(node, seg, errh,
                    src.get_seg_count(), src.get_cur_line(), src.get_ls_id())
            except pyx12.errors.EngineError:
                logger.error('Source file line %i' % (src.get_cur_line()))
                raise

        if node is None:
            # was not found
            node = orig_node
        else:
            if seg.get_seg_id() == 'ISA':
                errh.add_isa_loop(seg, src)
                icvn = seg.get_value('ISA12')
                errh.handle_errors(src.pop_errors())
            elif seg.get_seg_id() == 'IEA':
                errh.handle_errors(src.pop_errors())
                errh.close_isa_loop(node, seg, src)
                # Generate 997
                #XXX Generate TA1 if needed.
            elif seg.get_seg_id() == 'GS':
                fic = seg.get_value('GS01')
                vriic = seg.get_value('GS08')
                map_file_new = map_index_if.get_filename(icvn, vriic, fic)
                if map_file != map_file_new:
                    map_file = map_file_new
                    if map_file is None:
                        err_str = "Map not found.  icvn={}, fic={}, vriic={}".format(icvn, fic, vriic)
                        raise pyx12.errors.EngineError(err_str)
                    cur_map = pyx12.map_if.load_map_file(map_file, param, map_path)
                    src.check_837_lx = True if cur_map.id == '837' else False
                    logger.debug('Map file: %s' % (map_file))
                    #apply_loop_count(orig_node, cur_map)
                    #reset_isa_counts(cur_map)
                #reset_gs_counts(cur_map)
                node = cur_map.getnodebypath('/ISA_LOOP/GS_LOOP/GS')
                errh.add_gs_loop(seg, src)
                errh.handle_errors(src.pop_errors())
            elif seg.get_seg_id() == 'BHT':
                # special case for 4010 837P
                if vriic in ('004010X094', '004010X094A1'):
                    tspc = seg.get_value('BHT02')
                    logger.debug('icvn=%s, fic=%s, vriic=%s, tspc=%s' % (icvn, fic, vriic, tspc))
                    map_file_new = map_index_if.get_filename(icvn, vriic, fic, tspc)
                    logger.debug('New map file: %s' % (map_file_new))
                    if map_file != map_file_new:
                        map_file = map_file_new
                        if map_file is None:
                            err_str = "Map not found.  icvn={}, fic={}, vriic={}, tspc={}".format(icvn, fic, vriic, tspc)
                            raise pyx12.errors.EngineError(err_str)
                        cur_map = pyx12.map_if.load_map_file(map_file, param, map_path)
                        src.check_837_lx = True if cur_map.id == '837' else False
                        logger.debug('Map file: %s' % (map_file))
                        #apply_loop_count(node, cur_map)
                        node = cur_map.getnodebypath('/ISA_LOOP/GS_LOOP/ST_LOOP/HEADER/BHT')
                errh.add_seg(node, seg, src.get_seg_count(), src.get_cur_line(), src.get_ls_id())
                errh.handle_errors(src.pop_errors())
            elif seg.get_seg_id() == 'GE':
                errh.handle_errors(src.pop_errors())
                errh.close_gs_loop(node, seg, src)
            elif seg.get_seg_id() == 'ST':
                errh.add_st_loop(seg, src)
                errh.handle_errors(src.pop_errors())
            elif seg.get_seg_id() == 'SE':
                errh.handle_errors(src.pop_errors())
                errh.close_st_loop(node, seg, src)
            else:
                errh.add_seg(node, seg, src.get_seg_count(), src.get_cur_line(), src.get_ls_id())
                errh.handle_errors(src.pop_errors())

            valid &= node.is_valid(seg, errh)

        if fd_html:
            if node is not None and node.is_first_seg_in_loop():
                html.loop(node.get_parent())
            err_node_list = []
            while True:
                try:
                    err_iter.next()
                    err_node = err_iter.get_cur_node()
                    err_node_list.append(err_node)
                except pyx12.errors.IterOutOfBounds:
                    break
            html.gen_seg(seg, src, err_node_list)

        if fd_xmldoc:
            xmldoc.seg(node, seg)

    src.cleanup()  # Catch any skipped loop trailers
    errh.handle_errors(src.pop_errors())

    if fd_html:
        html.footer()
        del html

    if fd_xmldoc:
        del xmldoc

    #If this transaction is not a 997/999, generate one.
    if fd_997 and fic != 'FA':
        if vriic and vriic[:6] == '004010':
            try:
                visit_997 = pyx12.error_997.error_997_visitor(fd_997, src.get_term())
                errh.accept(visit_997)
                del visit_997
            except Exception:
                logger.exception('Failed to create 997 response')
        if vriic and vriic[:6] == '005010':
            try:
                visit_999 = pyx12.error_999.error_999_visitor(fd_997, src.get_term())
                errh.accept(visit_999)
                del visit_999
            except Exception:
                logger.exception('Failed to create 999 response')
    del node
    del src
    del control_map
    try:
        del cur_map
    except UnboundLocalError:
        pass
    try:
        if not valid or errh.get_error_count() > 0:
            return False
        else:
            return True
    except Exception:
        print(errh)
        return False
