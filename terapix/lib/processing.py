##############################################################################
#
# Copyright (c) 2008-2010 Terapix Youpi development team. All Rights Reserved.
#                    Mathias Monnerville <monnerville@iap.fr>
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
##############################################################################

"""
:mod:`processing` --- common functions
======================================

Some common functions for dealing with Youpi processings
"""

from terapix.youpi.models import Processing_task

def _get_kw(query):
    """
    Looks into the SQL string query to check whether a WHERE or AND condition is needed.
    @param query SQL string query
    @return WHERE or AND keyword
    """
    if query.find('WHERE') > 0: kw = 'AND'
    else: kw = 'WHERE'
    return kw

def find_tasks(tags=[], task_id=None, kind=None, user=None, success=False, failure=False, sort_by='-end_date'):
    """
    Find processing tasks matching some criteria.

    All parameters are optional.

    `tags` is a list of tags applied to images used for a processing. `task_id` refers to 
    unique task id (useful to query only one task). `kind` relates to the  processing kind 
    (i.e. scamp, swarp, fitsin, psfex, sex etc.). `user` is the processing's owner name.

    Set `success` to ``True`` to only select successful processings, or `failure` to ``True`` 
    to get only failed processings.

    This function returns a list of matched tasks, or an empty list if there is no match.
    """
    from django.db import connection
    import re
    cur = connection.cursor()

    if task_id:
        task_q = """
SELECT ta.id FROM youpi_processing_task AS ta
WHERE ta.id=%d
""" % task_id
    else:
        if not tags:
            task_q = """
SELECT ta.id FROM youpi_processing_task AS ta
"""
        else:
            task_q = """
SELECT ta.id
FROM youpi_processing_task AS ta, youpi_rel_it AS relit, youpi_rel_tagi AS tagi, youpi_tag AS t 
WHERE tagi.tag_id=t.id 
AND relit.image_id=tagi.image_id 
AND ta.id=relit.task_id 
AND t.name='%s'
"""

    if kind:
        task_q = task_q.replace('youpi_processing_task AS ta', 'youpi_processing_task AS ta, youpi_processing_kind AS k')
        task_q += "%s ta.kind_id=k.id AND k.name='%s'" % (_get_kw(task_q), kind)
    if user:
        task_q = task_q.replace('youpi_processing_task AS ta', 'youpi_processing_task AS ta, auth_user AS auth')
        task_q += "%s ta.user_id=auth.id AND auth.username='%s'" % (_get_kw(task_q), user)
    if not (success and failure):
        if success:
            task_q += " %s ta.success=1" % _get_kw(task_q)
        if failure:
            task_q += " %s ta.success=0" % _get_kw(task_q)

    if not tags:
        cur.execute(task_q)
        res = cur.fetchall()
        res = map(lambda x: int(x[0]), res)
    else:
        if len(tags) == 1:
            cur.execute(task_q % tags[0])
            res = [r[0] for r in cur.fetchall()]
        else:
            # Multiple tags
            prevtids = []
            for tag in tags:
                q = task_q % tag
                if prevtids:
                    q += " AND task_id IN (%s)" % ','.join(prevtids)
                cur.execute(q)
                res = cur.fetchall()
                tmp = [str(r[0]) for r in res]
                prevtids = tmp
                if not res: break
            res = [int(r) for r in tmp]

    return Processing_task.objects.filter(id__in=res).order_by(sort_by)

