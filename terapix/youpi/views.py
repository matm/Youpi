##############################################################################
#
# Copyright (c) 2008-2009 Terapix Youpi development team. All Rights Reserved.
#                    Mathias Monnerville <monnerville@iap.fr>
#                    Gregory Semah <semah@iap.fr>
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
##############################################################################

# vim: set ts=4

from django.contrib import auth
from django.contrib.auth import views
from django.contrib.auth.models import * 
from django.contrib.auth.decorators import login_required
from django.contrib.gis.db import models
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden, HttpResponseNotFound, HttpResponseRedirect, HttpResponseBadRequest
from django.db.models import get_models
from django.db.models import Q
from django.utils.datastructures import *
from django.template import Template, Context, RequestContext
#
from terapix.youpi.models import *
from terapix.youpi.auth import Permissions
from terapix.script.preingestion import preingest_table
from terapix.script.DBGeneric import *
from terapix.script.ingestion import getNowDateTime
#
import cjson as json
import MySQLdb, pyfits
import pprint, re, glob, string
import math, md5, random
import marshal, base64
import os, os.path, sys, pprint
import socket, time
from types import *
from copy import deepcopy
#
from settings import *

# Custom views
from terapix.exceptions import *
from terapix.youpi.pluginmanager import PluginManagerError, PluginError
from terapix.youpi.cviews.shoppingcart import *
from terapix.youpi.cviews.condor import *
from terapix.youpi.cviews.preingestion import *
from terapix.youpi.cviews.plot import *
from terapix.youpi.cviews.processing import *
from terapix.youpi.cviews.tags import *

@login_required
@profile
def index(request):
	"""
	This is the main entry point (root) of the web application.
	This is a callback function (as defined in django's urls.py file).
	"""

	return render_to_response('index.html', {	
							'selected_entry_id'			: 'home',
						},
						context_instance = RequestContext(request))

@login_required
@profile
def preferences(request):
	"""
	Preferences template
	"""
	import ConfigParser
	config = ConfigParser.RawConfigParser()

	# Looks for themes
	theme_dirs = glob.glob(os.path.join(MEDIA_ROOT, 'themes', '*'))
	themes = []

	for dir in theme_dirs:
		try:
			config.read(os.path.join(dir, 'META'))
		except:
			# No META data, theme not conform
			pass

		if not os.path.isfile(os.path.join(dir, 'screenshot.png')):
			# No screenshot available, theme not conform
			continue

		themes.append({	'name' 			: config.get('Theme', 'Name'),
						'author' 		: config.get('Theme', 'Author'),
						'author_uri'	: config.get('Theme', 'Author URI'),
						'description' 	: config.get('Theme', 'Description'),
						'version' 		: config.get('Theme', 'Version'),
						'short_name'	: os.path.basename(dir),
						})

	for k in range(len(themes)):
		if themes[k]['short_name'] == request.user.get_profile().guistyle:
			break

	policies = CondorNodeSel.objects.filter(is_policy = True).order_by('label')
	selections = CondorNodeSel.objects.filter(is_policy = False).order_by('label')
	try:
		p = request.user.get_profile()
		config = marshal.loads(base64.decodestring(str(p.dflt_condor_setup)))
	except EOFError:
		config = None

	return render_to_response('preferences.html', {	
						'themes'			: themes,
						'plugins' 			: manager.plugins, 
						'current_theme'		: themes[k],
						'policies'			: policies,
						'selections'		: selections,
						'config'			: config,
						'selected_entry_id'	: 'preferences', 
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def condor_setup(request):
	"""
	Condor cluster setup
	"""
	return render_to_response('condorsetup.html', {	
						'custom_condor_req' : request.user.get_profile().custom_condor_req,
						'selected_entry_id'	: 'condorsetup', 
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def documentation(request):
	"""
	Documentation template
	"""
	return render_to_response('documentation.html', {	
						'selected_entry_id'	: 'documentation',
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def cart_view(request):
	"""
	Renders shopping cart view.
	"""

	cartHasData = False
	if 'cart' not in request.session:
		request.session['cart'] = {'plugins' : {}}

	for plugin, dataList in request.session['cart']['plugins'].iteritems():
		plugObj = manager.getPluginByName(plugin)
		if len(dataList):
			plugObj.setData(dataList)
			cartHasData = True
		else:
			plugObj.removeData()

	policies = CondorNodeSel.objects.filter(is_policy = True).order_by('label')
	selections = CondorNodeSel.objects.filter(is_policy = False).order_by('label')

	return render_to_response('shoppingcart.html', {	
					'plugins' 			: manager.plugins, 
					'cartHasData' 		: cartHasData, 
					# Cluster node available policies + selections
					'policies'			: policies,
					'selections'		: selections,
					'selected_entry_id'	: 'shoppingcart', 
					'misc' 				: manager,
				},
				context_instance = RequestContext(request))

@login_required
@profile
def processing(request):
	return render_to_response('processing.html', { 	
						'plugins' 			: manager.plugins,
						'processing_output' : PROCESSING_OUTPUT,
						'selected_entry_id'	: 'processing',
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def preingestion(request):
	"""
	Related to preIngestion step
	"""
	
	return render_to_response('preingestion.html', {	
						'hostname'			: socket.gethostname(), 
						'selected_entry_id'	: 'preingestion', 
					},
					context_instance = RequestContext(request))

@login_required
@profile
def ing(request):
	"""
	Related to ingestion step.
	This is a callback function (as defined in django's urls.py file).
	"""

	q = Image.objects.all().count()
	return render_to_response('ingestion.html', {	
						'ingested' 			: q, 
						'selected_entry_id'	: 'ing', 
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def monitoring(request):
	"""
	Related to monitoring.
	This is a callback function (as defined in django's urls.py file).
	"""

	return render_to_response('monitoring.html', {	
						'selected_entry_id'	: 'monitoring',
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def results(request):
	"""
	Related to results page.
	This is a callback function (as defined in django's urls.py file).
	"""

	dirs = []
	ts = Processing_task.objects.all()
	for t in ts:
		if t.results_output_dir not in dirs:
			dirs.append(t.results_output_dir)

	return render_to_response('results.html', {	
						'plugins' 			: manager.plugins, 
						'selected_entry_id'	: 'results', 
						'outputDirs' 		: dirs,
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def reporting(request):
	"""
	Page to generate reports.
	"""

	return render_to_response('reporting.html', {	
						'plugins' 			: manager.plugins, 
						'selected_entry_id'	: 'reporting', 
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def tags(request):
	"""
	Related to tags page.
	This is a callback function (as defined in django's urls.py file).
	"""

	return render_to_response('tags.html', { 'selected_entry_id': 'tags' }, 
			context_instance = RequestContext(request))

@login_required
@profile
def render_plugin(request, pluginId):
	try:
		plugin = manager.getPluginByName(pluginId)
	except PluginManagerError, msg:
		return HttpResponseNotFound("Error: %s" % msg)

	return render_to_response('processing_plugin.html', { 	
						'plugin' 			: plugin,
						'selected_entry_id'	: 'processing', 
						'processing_output' : PROCESSING_OUTPUT,
					}, 
					context_instance = RequestContext(request))

@login_required
@profile
def soft_version_monitoring(request):
	return render_to_response( 'softs_versions.html', {	
				'report' 			: len(SOFTS), 
				'selected_entry_id'	: 'monitoring', 
			},
			context_instance = RequestContext(request))

@login_required
@profile
def show_ingestion_report(request, ingestionId):
	ing = Ingestion.objects.filter(id = ingestionId)[0]
	report = ing.report
	if report:
		report = str(zlib.decompress(base64.decodestring(ing.report)))
	else:
		report = 'No report found... maybe the processing is not finished yet?'

	return render_to_response( 'ingestion_report.html', {	
				'report' 			: report, 
				'selected_entry_id'	: 'ing', 
			},
			context_instance = RequestContext(request))

@login_required
@profile
def single_result(request, pluginId, taskId):
	"""
	Same content as the page displayed by related plugin.
	"""

	plugin = manager.getPluginByName(pluginId)
	if not plugin:
		return HttpResponseNotFound("""<h1><span style="color: red;">Invalid URL. Result not found.</h1></span>""")

	try:
		task = Processing_task.objects.filter(id = int(taskId))[0]
	except IndexError:
		# TODO: set a better page for that
		return HttpResponseNotFound("""<h1><span style="color: red;">Result not found.</h1></span>""")

	return render_to_response( 'single_result.html', {	
					'pid' 				: pluginId, 
					'tid'	 			: taskId,
					'selected_entry_id'	: 'results', 
					'plugin' 			: plugin,
				}, 
				context_instance = RequestContext(request))


def logout(request):
	auth.logout(request)
	# Redirect to home page
	return HttpResponseRedirect(AUP)

def browse_api(request, type):
	if type == 'py' or type == 'python':
		path = 'py/html/'
	elif type == 'js' or type == 'javascript':
		path = 'js/'
	else:
		return HttpResponseNotFound('No API of that name exits.')

	# Redirect to API doc
	return HttpResponseRedirect('http://clix.iap.fr:8001/' + path)

def local_ingestion(request):
	"""
	Callback for running a local ingestion.
	This is a callback function (as defined in django's urls.py file).
	"""
	path  = request.POST['path']
	connectionObject = MySQLdb.connect(host = DATABASE_HOST, user = DATABASE_USER, passwd = DATABASE_PASSWORD, db = DATABASE_NAME)
		
	if connectionObject:
		os.chdir(path)
		try:
			verify = request.POST['verify']
		except MultiValueDictKeyError:
			verify = '0'
		
		list_fits1 = glob.glob('*.fits')
		f = open('/tmp/verify.log', 'wa')
		
		while list_fits1 <> []:
			fitsfile = list_fits1.pop()
		
			fitsverify = os.popen("fitsverify -q -e %s" % fitsfile)
			k = fitsverify.readlines()
			fitsverify.close()

			if (verify == '1'):
				f.write(str(k)+'\n')
	
			r = pyfits.open(fitsfile)
			h1 = r[1].header
			
			# DBinstrument
			instrname, telescope, detector = (h1['instrume'], h1['telescop'],  h1['detector'])
			
			# DBimage
			object = h1['object']
			
			# DBchannel
			chaname = h1['filter']
			
			# DBrun
			runame = h1['runid']
			
			c = connectionObject.cursor()
	
			#
			# RUN DATABASE INGESTION
			#
			c.execute('start transaction')
			test = c.execute("select Name from youpi_run where name='%s'" % runame)
			if test == 0:
				if (detector == 'MegaCam' or  telescope == 'CFHT 3.6m' or instrname == 'MegaPrime'):
					test1 = c.execute("insert into youpi_run set Name='%s', instrument_id=2" % runame)
					if test1:
						connectionObject.commit()
					else:
						connectionObject.rollback()
	
				elif (detector == 'WIRCam' or telescope == 'CFHT 3.6m' or instrname == 'WIRCam'):
					test2 = c.execute("insert into youpi_run set Name='%s', instrument_id=3" % runame)
					if test2:
						connectionObject.commit()
					else:
						connectionObject.rollback()
	
			else:
				print 'Run known'
				
			#
			# CHANNEL DATABASE INGESTION
			#
			c.execute('start transaction')
			tust = c.execute("select Name from youpi_channel where name='%s'" % chaname)
			if (tust == 0):
				
				if (detector == 'MegaCam' and  telescope == 'CFHT 3.6m' and instrname == 'MegaPrime'):
					test3 = c.execute("insert into youpi_channel set Name='%s', instrument_id=2" % chaname)
					if test3:
						connectionObject.commit()
					else:
						connectionObject.rollback()
	
					
				elif (detector == 'WIRCam' and telescope == 'CFHT 3.6m' and instrname == 'WIRCam'):
					test4 = c.execute("insert into youpi_channel set Name='%s', instrument_id=3" % chaname)
					if test4:
						connectionObject.commit()
					else:
						connectionObject.rollback()
	
			else:
				print "channel known"
		f.close()
			

		#
		# IMAGE
		#
		os.chdir(path)
		list_fits2 = glob.glob('*.fits')
		for fitsfile in list_fits2:
			
			checksum = md5.md5(open(fitsfile, 'rb').read()).hexdigest()
			r = pyfits.open(fitsfile)
			h1 = r[1].header
			
			# DBinstrument
			i = h1['instrume']
			t = h1['telescop']
			det = h1['detector']
			
			# DBimage
			o = h1['object']
			a = h1['airmass']
			e = h1['exptime']
			d = h1['DATE-OBS']
			eq = h1['equinox']
			
			# DBchannel
			chaname = h1['filter']
			
			# DBrun
			runame = h1['runid']
			c.execute('start transaction')
			mj = fitsfile.replace('.fits', '')
			tast = c.execute("select name from youpi_image where name='%s'" % mj)
	
			if tast == 1:
				break
			elif tast == 0:
				weight = re.search('_weight.fits', fitsfile)
				if weight:
					break
	
				testa = c.execute("select Name from youpi_run where name='%s'" % runame)
				m = fitsfile.replace('.fits', '')
	
				if testa == 1:
					if (det == 'MegaCam' or  t == 'CFHT 3.6m' or i == 'MegaPrime'):
						c.execute("select id from youpi_run where instrument_id = 2 and Name='%s'" % runame)
						rows = c.fetchone()

						c.execute("select id from youpi_channel where instrument_id = 2 and Name='%s'" % chaname)
						row = c.fetchone()
						
						c.execute("insert into youpi_image set run_id='%s', calibrationkit_id=1, instrument_id=2, channel_id='%s', Name='%s', object='%s', airmass='%s', exptime='%s', dateobs='%s', equinox='%s', checksum='%s'" % (rows[0], row[0], m, o, a, e, d, eq, checksum))
			
					elif (det == 'WIRCam' or t == 'CFHT 3.6m' or i == 'WIRCam'):
						c.execute("select id from youpi_run where instrument_id=3 and Name='%s'" % runame)
						rows = c.fetchone()
						
						c.execute("select id from youpi_channel where instrument_id=3 and Name='%s'" % chaname)
						row = c.fetchone()
	
						c.execute("insert into youpi_image set run_id='%s', calibrationkit_id=2, instrument_id=3, channel_id='%s', Name='%s', object='%s', airmass='%s', exptime='%s', dateobs='%s', equinox='%s', checksum='%s'" % (rows[0],row[0],m,o,a,e,d,eq,checksum))
			
			connectionObject.commit()
	else:
		print 'Not connected to the Database'
	rows = open('/tmp/verify.log', 'r').readlines()
	return render_to_response('popup.htm', {'names': rows})



def aff_img(request,image_name):
	"""
	Displays (popup) an image image_name.
	This is a callback function (as defined in django's urls.py file).
	"""

	db = MySQLdb.connect(host = DATABASE_HOST, user = DATABASE_USER, passwd = DATABASE_PASSWORD, db = DATABASE_NAME)
	cursor = db.cursor()
	cursor.execute("SELECT * FROM youpi_image where name='%s'" % image_name)
	list_param = []
	for rows in cursor.fetchall():
		list_param.append({'rows':rows})
	db.close()

	return render_to_response('popup.htm', {'names': rows})

def open_populate(request, behaviour, tv_name, path):
	"""
	This function returns a list of JSON objects to generate a dynamic Ajax treeview.
	The argument path is a path to directory structure (see views.py for further details). it 
	is equal to the value of 'openlink' in a JSON branch definition.

	This function is specific to tafelTreeview.
	"""

	#
	# The POST request will always contain a branch_id variable when the present function 
	# is called dynamically by the tree issuing the Ajax query
	#
	try:
		nodeId = request.POST['branch_id']
	except:
		# May be usefull for debugging purpose
		return HttpResponse("Path debug: %s, %s, %s" % (path, behaviour, tv_name))

	json = []
	fitsSearchPattern = '*.fits'
	regFitsSearchPattern = '^.*\.fits$'

	if behaviour == 'binary_tables':
		# Patterns change
		fitsSearchPattern = 'mcmd.*.fits'
		regFitsSearchPattern = '^mcmd\..*\.fits$'

	# Look for data
	data = glob.glob("/%s/*" % str(path))

	dirs = []
	for e in data:
		if os.path.isdir(e):
			dirs.append(e)
		elif os.path.isfile(e):
			if re.match(regFitsSearchPattern, e):
				# This is a fits file
				json.append( {
					'id'  : os.path.basename(e),
					'txt' : os.path.basename(e),
					'img' : 'forward.png'
				})


	for d in dirs:
		# Check if this directory contains any FITS file
		fitsFiles = glob.glob("%s/%s" % (d, fitsSearchPattern))

		label = os.path.split(d)[1]
		id = "%s_%s" % (str(path), label)
		id = id.replace('/', '_')
		if len(fitsFiles):
			nodeText = """%s <font class="image_count">(%d)</font>""" % (label, len(fitsFiles))
		else:
			nodeText = label

		json.append( {
			'id' : id,
			'txt' : nodeText,
			'canhavechildren' : 1,
			'onopenpopulate' : str(tv_name) + '.branchPopulate',
			'syspath' : "/%s/%s/" % (str(path), label),
			'openlink' : AUP + "/populate/%s/%s/%s/%s/" % (str(behaviour), str(tv_name), str(path), label),
			'num_fits_children' : len(fitsFiles)
		})
			

	return HttpResponse(str(json), mimetype = 'text/plain')


def open_populate_generic(request, patterns, fb_name, path):
	"""
	This function returns a list of JSON objects to generate a dynamic Ajax treeview.
	The argument path is a path to directory structure (see views.py for further details). it 
	is equal to the value of 'openlink' in a JSON branch definition.

	This function is specific to tafelTreeview.

	patterns: file search patterns (comma-separated list)
	fb_name: FileBrowser global variable name
	path: path to data
	"""

	if path[0] == '/':
		path = path[1:]

	#
	# The POST request will always contain a branch_id variable when the present function 
	# is called dynamically by the tree issuing the Ajax query
	#
	try:
		nodeId = request.POST['branch_id']
	except:
		# May be usefull for debugging purpose
		return HttpResponse("Path debug: %s, %s, %s" % (path, patternList, fb_name))

	json = []

	patternList = patterns.split(',')
	regSearchPatternList = []
	for pat in patternList:
		regSearchPatternList.append(pat.replace('.', '\.').replace('*', '.*'))

	# Look for data
	data = glob.glob("/%s/*" % str(path))

	dirs = []
	for e in data:
		if os.path.isdir(e):
			dirs.append(e)
		elif os.path.isfile(e):
			for rsp in regSearchPatternList:
				if re.match(rsp, e):
					# This is a file
					json.append( {
						'id'  : os.path.basename(e),
						'txt' : os.path.basename(e),
						'img' : 'forward.png'
					})
					break

	for d in dirs:
		# Check if this directory contains any file matching searchPattern
		files = []
		for pat in patternList:
			files.extend(glob.glob("%s/%s" % (d, pat)))

		label = os.path.split(d)[1]
		id = "%s_%s" % (str(path), label)
		id = id.replace('/', '_')
		if len(files):
			nodeText = """%s <font class="image_count">(%d)</font>""" % (label, len(files))
		else:
			nodeText = label

		json.append( {
			'id' : id,
			'txt' : nodeText,
			'canhavechildren' : 1,
			'onopenpopulate' : str(fb_name) + '.getResultHandler()',
			'syspath' : "/%s/%s/" % (str(path), label),
			'openlink' : AUP + "/populate_generic/%s/%s/%s/%s/" % (str(patterns), str(fb_name), str(path), label),
			'num_children' : len(files)
		})
			

	return HttpResponse(str(json), mimetype = 'text/plain')

def history_ingestion(request):
	"""
	Return a JSON object with data related to ingestions' history
	"""

	try:
		limit = request.POST['limit']
	except Exception, e:
		return HttpResponseForbidden()

	try:
		limit = int(limit)
	except ValueError, e:
		# Unlimitted
		limit = 0

	res = Ingestion.objects.all().order_by('-start_ingestion_date')

	if limit > 0:
		res = res[:limit]

	#
	# We build a standard header that can be used for table's header.
	# header var must be a list not a tuple since it get passed 'as is' to the json 
	# dictionary
	#
	header = ['start', 'duration', 'ID', 'user', 'fitsverify', 'qsostatus', 'multiple', 'exit', 'log']

	data = []
	for ing in res:
			#
			# Unicode strings have to be converted to basic strings with str()
			# in order to get a valid JSON object.
			# Each header[j] is a list of (display value, type[, value2]).
			# type allows client-side code to known how to display the value.
			#
			data.append({	header[0] 	: [str(ing.start_ingestion_date), 'str'],
							header[1] 	: [str(ing.end_ingestion_date-ing.start_ingestion_date), 'str'],
							header[2] 	: [str(ing.label), 'str'],
							header[3] 	: [str(ing.user.username), 'str'],
							header[4]	: [ing.check_fitsverify, 'check'],
							header[5] 	: [ing.check_QSO_status, 'check'],
							header[6]	: [ing.check_multiple_ingestion, 'check'],
							header[7]	: [ing.exit_code, 'exit'],
							header[8]	: ['View log', 'link', str(AUP + "/history/ingestion/report/%d/" % ing.id)]
			})

	# Be aware that JS code WILL search for data and header keys
	json = { 'data' : data, 'header' : header }

	# Return a JSON object
	return HttpResponse(str(json), mimetype = 'text/plain')

def remap(idList):
	"""
	Build a list of ranges from an integer suite:

	IN:  1,2,3,4,6,7,8,9,11,12,13,20,22,23,24,25,30,40,50,51,52,53,54,60
	OUT: 1-4,6-9,11-13,20-20,22-25,30-30,40-40,50-54,60-60
	"""

	idList = idList.split(',')
	idList = [int(id) for id in idList]
	idList.sort()
	
	ranges = []
	i = idList[0]
	ranges.append(i)
	
	for k in range(len(idList)-1):
		if idList[k+1] > idList[k]+1:
			ranges.append(idList[k])
			ranges.append(idList[k+1])
	
	ranges.append(idList[-1])
	
	maps = ''
	for k in range(0, len(ranges)-1, 2):
		maps += "%s-%s," % (ranges[k], ranges[k+1])
	
	return maps[:-1]

def unremap(ranges):
	"""
	Build an integer suite from a list of ranges:

	IN:  1-4,6-9,11-13,20-20,22-25,30-30,40-40,50-54,60-60
	OUT: 1,2,3,4,6,7,8,9,11,12,13,20,22,23,24,25,30,40,50,51,52,53,54,60
	"""

	ranges = ranges.split(',')
	idList = ''

	for r in ranges:
		r = r.split('-')
		r = [int(j) for j in r]
		idList += string.join([str(j) for j in range(r[0], r[1]+1)], ',') + ','

	return idList[:-1]

def processing_imgs_remap_ids(request):
	"""
	Rewrite idList to prevent too long GET queries
	"""
	try:
		idList = request.POST['IdList']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	return HttpResponse(str({'mapList' : remap(idList)}), mimetype = 'text/plain')

def processing_imgs_from_idlist(request, ids):
	"""
	Builds an SQL query based on POST data, executes it and returns a JSON object containing results.
	"""

	# Build integer list from ranges
	ids = unremap(ids)

	# Now executes query
	db = DB(host = DATABASE_HOST,
			user = DATABASE_USER,
			passwd = DATABASE_PASSWORD,
			db = DATABASE_NAME)

	g = DBGeneric(db.con)
	query = """
SELECT a.id, a.name, b.name, a.object, c.name, a.alpha, a.delta 
FROM youpi_image AS a, youpi_run AS b, youpi_channel AS c
WHERE a.id IN (%s)
AND a.run_id = b.id
AND a.channel_id = c.id
ORDER BY a.name
""" % ids

	try:
		res = g.execute(query);
	except MySQLdb.DatabaseError, e:
		return HttpResponseServerError("Error: %s [Query: \"%s\"]" % (e, query))

	xml = """<?xml version="1.0" encoding="utf-8"?>
<rows>
	<head>
        <column width="50" type="ch" align="center" color="lightblue" sort="str">Select</column>
        <column width="100" type="ro" align="center" sort="str">Name</column>
        <column width="100" type="ro" align="center" sort="str">Run ID</column>
        <column width="100" type="ro" align="center" sort="str">Object</column>
        <column width="100" type="ro" align="center" sort="str">Channel</column>
        <column width="120" type="ro" align="center" sort="int">Ra</column>
        <column width="120" type="ro" align="center" sort="int">Dec</column>
		<settings>
			<colwidth>px</colwidth>
		</settings>
	</head>"""

	for img in res:
		xml += "<row id=\"%s\"><cell>1</cell><cell>%s</cell><cell>%s</cell><cell>%s</cell><cell>%s</cell><cell>%s</cell><cell>%s</cell></row>" % img
	
	xml += '</rows>'

	return HttpResponse(xml, mimetype = 'text/xml')

def processing_imgs_from_idlist_post(request):
	"""
	Builds an SQL query based on POST data, executes it and returns a JSON object containing results.
	"""

	try:
		ids = request.POST['Ids']
		page = request.POST.get('Page', 0)
		pageStatus = request.POST.get('PageStatus', None)
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	# Build integer list from ranges
	ids = unremap(ids).split(',')

	# Pagination handling
	count = len(ids)
	if page == 0:
		currentPage = 1
	else:
		currentPage = int(page)
	maxPerPage = IMS_MAX_PER_PAGE
	nbPages = count / maxPerPage
	if count % maxPerPage > 0:
		nbPages += 1

	# Finds window boundaries
	wmin = maxPerPage * (currentPage-1)
	if count - wmin > maxPerPage:
		window = ids[wmin: wmin + maxPerPage]
	else:
		window = ids[wmin:]

	# Get image data for currentPage
	images = Image.objects.filter(id__in = window)

	content = []
	for img in images:
		rels = Rel_tagi.objects.filter(image = img)
		tags = Tag.objects.filter(id__in = [r.tag.id for r in rels]).order_by('name')
		if tags:
			cls = 'hasTags'
		else:
			cls = ''
		content.append([int(img.id), 
						str("<span class=\"imageTag %s\">%s.fits</span><div style=\"width: 200px;\">%s</div>" % 
							(cls, 		# Class name
							 img.name, 	# Image name
							 string.join([str("<span class=\"tagwidget\" style=\"%s;\">%s</span>" % (t.style, t.name)) for t in tags], '')))])

	return HttpResponse(str({'TotalPages': int(nbPages), 'CurrentPage': currentPage, 'Headers': ['Image Name/Tags'], 'Content' : content}), mimetype = 'text/plain')

def get_selected_ids_from_pagination(request):
	"""
	Returns a list of ids of selected images (in pagination mode)
	"""

	try:
		ids = request.POST['Ids']
		pageStatus = request.POST['PageStatus'].split('_')
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	# Build integer list from ranges
	ids = unremap(ids).split(',')
	range = IMS_MAX_PER_PAGE
	idList = []

	k = j = 0
	pages = []
	while j < len(pageStatus):
		pages.append(ids[k:k+range])
		k += range
		j += 1

	k = 0
	for page in pages:
		ps = pageStatus[k].split(',')
		if ps[0] == 's':
			for unchecked in ps[1:]:
				del page[int(unchecked)]
		elif ps[0] == 'u':
			tmp = []
			for checked in ps[1:]:
				tmp.append(page[int(checked)])
			page = tmp
		else:
			return HttpResponse(str({'Error': 'pageStatus POST data bad formatted'}))

		idList.extend(page)
		k += 1

	count = len(idList)
	idList = string.join(idList, ',')

	return HttpResponse(str({'idList': str(idList), 'count': int(count)}), mimetype = 'text/plain')

def processing_plugin(request):
	"""
	Entry point for client-side JS code to call any registered plugin's method
	"""

	try:
		pluginName = request.POST['Plugin']
		method = request.POST['Method']
	except Exception, e:
		raise PostDataError, e

	plugin = manager.getPluginByName(pluginName)
	try:
		res = eval('plugin.' + method + '(request)')
	except Exception, e:
		raise PluginEvalError, e

	# Response must be a JSON-like object
	return HttpResponse(str({'result' : res}), mimetype = 'text/plain')

def batch_view_content(request, fileName):
	"""
	Parse XML content of file fileName to find out selections.
	"""

	fileName = '/tmp/' + request.user.username + '_' + fileName
	try:
		f = open(fileName)
		data = f.readlines()
		f.close()
	except IOError:
		return HttpResponseNotFound('File not found.')

	return HttpResponse(string.join(data), mimetype = 'text/xml')

def batch_view_selection(request):
	"""
	Returns selection content
	"""

	try:
		xmlstr = request.POST['XML']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	doc = dom.parseString(xmlstr)
	data = doc.getElementsByTagName('selection')[0]
	sel = batch_parse_selection(data);

	imgs = Image.objects.filter(id__in = sel['idList'].split(',')).order_by('name');

	return HttpResponse(str({'name' : str(sel['name']), 'data' : [[str(img.name), str(img.path)] for img in imgs]}), mimetype = 'text/plain')

def get_circle_from_multipolygon(alpha_center, delta_center, radius, p):
	"""
	Returns a MySQL MULTIPOLYGON object describing a circle with a resolution of p points.
	"""

	# Computing selection circle based (p points)
	rot = []
	p -= 1
	if p % 2 == 0:
		t = p/2
	else:
		t = p/2+1

	for i in range(t):
		rot.append(2*math.pi*(i+1)/p)

	ro = deepcopy(rot)
	ro.reverse()
	ro = ro[1:]
	for i in range(len(ro)):
		ro[i] = -ro[i]
	rot.extend(ro)

	p1x, p1y = alpha_center + radius, delta_center

	points = [p1x, p1y]

	for i in range(len(rot)):
		points.append(math.cos(rot[i])*(p1x - alpha_center) - math.sin(rot[i])*(p1y - delta_center) + alpha_center)
		points.append(math.sin(rot[i])*(p1x - alpha_center) + math.cos(rot[i])*(p1y - delta_center) + delta_center)

	points.append(p1x)
	points.append(p1y)

	strf = 'MULTIPOLYGON((('
	for j in range(0, len(points), 2):
		strf += "%f %f," % (points[j], points[j+1])
	strf = strf[:-1] + ')))'

	return strf

def batch_parse_selection(sel):
	"""
	Parse a single XML DOM selection.
	"""

	label = sel.getElementsByTagName('label')[0].firstChild.nodeValue
	alpha_center = float(sel.getElementsByTagName('alpha')[0].firstChild.nodeValue)
	delta_center = float(sel.getElementsByTagName('delta')[0].firstChild.nodeValue)
	radius = float(sel.getElementsByTagName('radius')[0].firstChild.nodeValue)

	imgs = Image.objects.filter(centerfield__contained = get_circle_from_multipolygon(alpha_center, delta_center, radius, 16))
	
	return {'xml' : str(sel.toxml()), 'name' : str(label), 'count' : len(imgs), 'idList' : string.join([str(img.id) for img in imgs], ',')}

def batch_parse_content(request):
	"""
	Parse XML content of file fileName to find out selections.
	This comes AFTER dtd validation so nothing to worry about.
	"""

	try:
		fileName = request.POST['Filename']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	import xml.dom.minidom as dom
	f = '/tmp/' + request.user.username + '_' + fileName
	doc = dom.parse(f)
		
	data = doc.getElementsByTagName('selection')
	selections = []
	for sel in data:
		selections.append(batch_parse_selection(sel))

	return HttpResponse(str({'result' : {'nbSelections' : len(selections), 'selections' : selections}}), mimetype = 'text/plain')
	
def upload_file(request):
	"""
	Uploads a file into temporary directory.
	exit_code != 0 if any problem found.
	"""

	exitCode = 0
	errMsg = ''
	try:
		try:
			files = request.FILES
			keys = files.keys()
		except:
			raise Exception, "Bad file submitted"

		if len(keys):
			k = keys[0]
			content = files[k]['content']
		else:
			raise Exception, "Could not get file content"

		# Valid XML file, save it to disk
		filename = files[k]['filename']
		f = open('/tmp/' + request.user.username + '_' + filename, 'w')
		f.write(content)
		f.close()
		
	except Exception, e:
		exitCode = 1
		content = ''
		filename = ''
		errMsg = str(str(e))

	return HttpResponse(str({'filename' : str(filename), 'length' : len(content), 'exit_code' : exitCode, 'error_msg' : errMsg }), mimetype = 'text/html')

def get_report(request, pluginId, reportId):
	"""
	Generate a report
	"""
	try:
		plugObj = manager.getPluginByName(pluginId)
	except PluginManagerError:
		# Not found
		return HttpResponseNotFound()

	try:
		return plugObj.getReport(reportId)
	except TypeError:
		# Bad report Id
		return HttpResponseNotFound()

def ims_get_image_list(request):
	"""
	Parse content of fileName and returns an image selection
	"""

	try:
		fileName = request.POST['Filename']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	errMsg = ''
	try:
		f = open('/tmp/' + request.user.username + '_' + fileName)
		lines = f.readlines()
		f.close()
	except Exception, e:
		errMsg = "%s" % e

	lines = [li[:-1] for li in lines]
	warnings = []
	# Separate lines with image name only (to issue only one SQL query)
	nameonly = []
	# ...from lines with image name and checksum (one SQL query per line)
	namemd5 = []
	idList = []
	j = 0
	for line in lines:
		sp = line.split(',')
		if len(sp) == 1:
			sp[0] = sp[0].strip()
			imgs = Image.objects.filter(name = sp[0])
			if not imgs:
				warnings.append(str("Line %d: image '%s' not found") % (j+1, sp[0]))
			else:
				idList.append(int(imgs[0].id))
		elif len(sp) == 2:
			sp[0] = sp[0].strip()
			sp[1] = sp[1].strip()
			namemd5.append(sp)
			imgs = Image.objects.filter(name = sp[0], checksum = sp[1])
			if not imgs:
				warnings.append(str("Line %d: image '%s' (%s) not found") % (j+1, sp[0], sp[1]))
			else:
				idList.append(int(imgs[0].id))
		else:
			# Line not well-formatted
			errMsg = "Line %d is not well-formatted: should be image_name[, md5sum]" % j+1
			break
		j += 1

	return HttpResponse(str({'warnings': warnings, 'error' : str(errMsg), 'foundCount' : len(idList), 'total' : len(lines), 'idList' : idList}), mimetype = 'text/plain')

def save_condor_node_selection(request):
	"""
	Save Condor nodes selection
	"""
	try:
		selHosts = request.POST['SelectedHosts'].split(',')
		label = request.POST['Label']
	except Exception, e:
		return HttpResponseServerError('Incorrect POST data.')

	sels = CondorNodeSel.objects.filter(label = label, is_policy = False)
	if sels:
		return HttpResponse(str({'Error' : str("'%s' label is already used, please use another name." % label)}), 
					mimetype = 'text/plain')

	nodesel = base64.encodestring(marshal.dumps(selHosts)).replace('\n', '')
	sel = CondorNodeSel(user = request.user, label = label, nodeselection = nodesel)
	sel.save()

	return HttpResponse(str({'Label' : str(label), 'SavedCount' : len(selHosts)}), mimetype = 'text/plain')

def save_condor_policy(request):
	"""
	Save Condor custom policy
	"""
	try:
		label = request.POST['Label']
		serial = request.POST['Serial']
	except Exception, e:
		return HttpResponseServerError('Incorrect POST data.')

	try:
		sels = CondorNodeSel.objects.filter(label = label, is_policy = True)
		if sels:
			if sels[0].user != request.user:
				# Only owner can update its policy
				return HttpResponse(str({'Error' : 'Only selection owner can update its policies. Policy not overwritten.'}), mimetype = 'text/plain')
			else:
				sel = sels[0]
				sel.nodeselection = serial
		else:
			sel = CondorNodeSel(user = request.user, label = label, nodeselection = serial, is_policy = True)

		sel.save()
		
	except Exception, e:
		return HttpResponse(str({'Error' : "%s" % e}), mimetype = 'text/plain')

	return HttpResponse(str({'Label' : str(label), 'Policy' : str(serial)}), mimetype = 'text/plain')

def save_condor_custom_reqstr(request):
	"""
	Save Condor custom requirement string
	"""
	try:
		reqstr = request.POST['Req']
	except Exception, e:
		return HttpResponseServerError('Incorrect POST data.')

	try:
		p = request.user.get_profile()
		p.custom_condor_req = reqstr
		p.save()
	except Exception, e:
		return HttpResponse(str({'Error' : "%s" % e}), mimetype = 'text/plain')

	return HttpResponse(str({'Status' : str('saved')}), mimetype = 'text/plain')

def del_condor_node_selection(request):
	"""
	Delete Condor node selection. 
	No deletion is allowed if at least one policy is using that selection.
	No deletion is allowed if at least Condor Default Setup rules is using that selection.
	"""

	try:
		label = request.POST['Label']
	except Exception, e:
		return HttpResponseServerError('Incorrect POST data.')

	profiles = SiteProfile.objects.all()
	for p in profiles:
		try:
			data = marshal.loads(base64.decodestring(str(p.dflt_condor_setup)))
		except EOFError:
			# No data found, unable to decodestring
			data = None

		if data:
			for plugin in data.keys():
				if data[plugin]['DS'].find(label) >= 0:
					return HttpResponse(str({'Error' : str("Cannot delete selection '%s'. User '%s' references it in his/her default selection preferences menu." 
								% (label, p.user.username))}), mimetype = 'text/plain')

	pols = CondorNodeSel.objects.filter(is_policy = True)
	if pols:
		for pol in pols:
			if pol.nodeselection.find(label) >= 0:
				return HttpResponse(str({'Error' : str("Some policies depends on this selection. Unable to delete selection '%s'." % label)}), 
					mimetype = 'text/plain')

	sel = CondorNodeSel.objects.filter(label = label, is_policy = False)[0]
	sel.delete()

	return HttpResponse(str({'Deleted' : str(label)}), mimetype = 'text/plain')

def del_condor_policy(request):
	"""
	Delete Condor policy
	"""

	try:
		label = request.POST['Label']
	except Exception, e:
		return HttpResponseServerError('Incorrect POST data.')

	profiles = SiteProfile.objects.all()
	for p in profiles:
		try:
			data = marshal.loads(base64.decodestring(str(p.dflt_condor_setup)))
		except EOFError:
			# No data found, unable to decodestring
			data = None

		if data:
			for plugin in data.keys():
				if data[plugin]['DP'].find(label) >= 0:
					return HttpResponse(str({'Error' : str("Cannot delete policy '%s'. User '%s' references it in his/her default selection preferences menu." 
								% (label, p.user.username))}), mimetype = 'text/plain')

	sel = CondorNodeSel.objects.filter(label = label, is_policy = True)[0]
	sel.delete()

	return HttpResponse(str({'Deleted' : str(label)}), mimetype = 'text/plain')

def get_condor_node_selections(request):
	"""
	Returns Condor nodes selections.
	"""

	sels = CondorNodeSel.objects.filter(is_policy = False).order_by('label')

	return HttpResponse(str({'Selections' : [str(sel.label) for sel in sels]}), mimetype = 'text/plain')

def get_condor_policies(request):
	"""
	Returns Condor policies.
	"""

	sels = CondorNodeSel.objects.filter(is_policy = True).order_by('label')

	return HttpResponse(str({'Policies' : [str(sel.label) for sel in sels]}), mimetype = 'text/plain')

def get_condor_selection_members(request):
	"""
	Returns Condor selection members.
	"""

	try:
		name = request.POST['Name']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	data = CondorNodeSel.objects.filter(label = name, is_policy = False)
	error = ''

	if data:
		members = marshal.loads(base64.decodestring(str(data[0].nodeselection)))
		members = [str(s) for s in members]
	else:
		members = '';
		error = 'No selection of that name.'

	return HttpResponse(str({'Members' : members, 'Error' : error}), mimetype = 'text/plain')

def get_policy_data(request):
	"""
	Returns policy serialized data
	"""

	try:
		name = request.POST['Name']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	data = CondorNodeSel.objects.filter(label = name, is_policy = True)
	error = serial = ''

	if data:
		serial = str(data[0].nodeselection)
	else:
		error = 'No policy of that name.'

	return HttpResponse(str({'Serial' : serial, 'Error' : error}), mimetype = 'text/plain')

@login_required
@profile
def set_current_theme(request):
	"""
	Set default user theme
	"""
	try:
		name = request.POST['Name']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	p = request.user.get_profile()
	p.guistyle = name
	p.save()

	return HttpResponse(str({'Default': str(name)}), mimetype = 'text/plain')

@login_required
@profile
def pref_save_condor_config(request):
	"""
	Save per-user default condor setup
	"""

	kinds = ('DB', 'DP', 'DS')
	try:
		defaults = [request.POST[p].split(',') for p in kinds]
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	condor_setup = {}
	k = 0
	for plugin in manager.plugins:
		condor_setup[plugin.id] = {}
		j = 0
		for kind in kinds:
			try:
				if len(defaults[j][k]):
					condor_setup[plugin.id][kind] = str(defaults[j][k])
				else:
					condor_setup[plugin.id][kind] = ''
			except IndexError:
				condor_setup[plugin.id][kind] = ''
			j += 1
		k += 1

	try:
		p = request.user.get_profile()
		p.dflt_condor_setup = base64.encodestring(marshal.dumps(condor_setup)).replace('\n', '')
		p.save()
	except Exception, e:
		return HttpResponse(str({'Error': str(e)}), mimetype = 'text/plain')

	return HttpResponse(str({'Setup': str(condor_setup)}), mimetype = 'text/plain')

@login_required
@profile
def pref_load_condor_config(request):
	"""
	Load per-user default condor setup. Can be empty if user never saved its Condor default 
	config.
	"""

	try:
		p = request.user.get_profile()
		data = marshal.loads(base64.decodestring(str(p.dflt_condor_setup)))
	except EOFError:
		# No data found, unable to decodestring
		config = None

	return HttpResponse(str({'config': str(data)}), mimetype = 'text/plain')

@login_required
@profile
def get_image_info(request):
	"""
	Returns information about image
	"""

	try:
		id = request.POST['Id']
	except Exception, e:
		return HttpResponseBadRequest('Incorrect POST data')

	try:
		img = Image.objects.filter(id = int(id))[0]
	except Exception, e:
		return HttpResponse(str({'Error': "%s" % e}), mimetype = 'text/plain')

	data = {
		'name': 		str(img.name + '.fits'),
		'path': 		str(img.path),
		'alpha': 		str(img.alpha),
		'delta': 		str(img.delta),
		'exptime': 		str(img.exptime),
		'checksum': 	str(img.checksum),
		'flat': 		str(img.flat),
		'mask': 		str(img.mask),
		'reg': 			str(img.reg),
		'qsostatus': 	str(img.QSOstatus),
		'instrument': 	str(img.instrument.name),
		'run': 			str(img.run.name),
		'channel': 		str(img.channel.name),
		'ingestion':		str(img.ingestion.label),
		'ing start':	str(img.ingestion.start_ingestion_date),
		'ing end':	str(img.ingestion.end_ingestion_date),
		'ing by':	str(img.ingestion.user.username),
	}

	return HttpResponse(str({'info': data}), mimetype = 'text/plain')

@login_required
@profile
def stats_ingestion(request):
	"""
	Returns stats about ingestion
	"""

	total_images = Image.objects.all().count()
	instruments = Instrument.objects.all().order_by('name')
	imgs_per_instru = []
	for inst in instruments:
		imgcount = Image.objects.filter(instrument = inst).count()
		percent = imgcount*100./total_images
		imgs_per_instru.append({'instrument': str(inst.name), 'count': int(imgcount), 'percent': percent})

	channels = Channel.objects.all().order_by('name')
	imgs_per_channel = []
	for c in channels:
		imgCount = Image.objects.filter(channel = c).count()
		percent = imgCount*100./total_images
		imgs_per_channel.append({'channel': str(c.name), 'count': int(imgCount), 'percent': percent})

	data = {
		'totalImages' 			: int(total_images),
		'totalPerInstrument' 	: imgs_per_instru,
		'imgsPerChannel': imgs_per_channel,
	}

	return HttpResponse(str({'info': data}), mimetype = 'text/plain')

@login_required
@profile
def stats_processing(request):
	"""
	Returns stats about processings
	"""

	total_tasks = Processing_task.objects.all().count()
	kinds = Processing_kind.objects.all().order_by('name')
	tasks_per_kind = []
	for k in kinds:
		taskcount = Processing_task.objects.filter(kind = k).count()
		percent = taskcount*100./total_tasks
		tasks_per_kind.append({'kind': str(k.name), 'count': int(taskcount), 'percent': percent})

	failed_tasks = Processing_task.objects.filter(success = 0).count()

	data = {
		'tasksTotal' 	: int(total_tasks),
		'failedTasks'	: int(failed_tasks),
		'tasksPerKind' 	: tasks_per_kind,
	}

	return HttpResponse(str({'info': data}), mimetype = 'text/plain')

@login_required
@profile
def get_condor_log_files_links(request):
	"""
	Returns a dictionnary with entries for the log, error and output filenames 
	that should be used by plugins generating Condor submission files.
	@return Dictionnary with paths to Condor log files
	"""

	post = request.POST
	try:
		taskId = post['TaskId']
	except Exception, e:
		raise PluginError, "POST argument error. Unable to process data."

	task = Processing_task.objects.filter(id = taskId)[0]
	pattern = os.path.join(CONDOR_LOG_DIR, task.kind.name.upper() + '.%s.' + task.clusterId)
	logs = {
		'log': pattern % 'log', 
		'error': pattern % 'err', 
		'out': pattern % 'out',
	}
	sizes = {'log': 0, 'error': 0, 'out': 0}

	for kind, path in logs.iteritems():
		try:
			sizes[kind] = int(os.path.getsize(path))
			logs[kind] = str("""<a href="/youpi/cluster/log/%s/%s/" target="_blank">%s</a>""" % (kind, taskId, logs[kind][logs[kind].rfind('/')+1:]))
		except OSError:
			logs[kind] = ''

	return HttpResponse(str({'logs': logs, 'sizes': sizes}), mimetype = 'text/plain')

@login_required
@profile
def show_condor_log_file(request, kind, taskId):
	"""
	Display Condor log file for a given kind and taskId
	@param kind one of 'log', 'error', 'out'
	@param taskId task Id
	"""

	if kind not in ('log', 'error', 'out'):
		return HttpResponseBadRequest('Bad request')

	try:
		task = Processing_task.objects.filter(id = taskId)[0]
	except:
		return HttpResponseBadRequest('Bad request')

	pattern = os.path.join(CONDOR_LOG_DIR, task.kind.name.upper() + '.%s.' + task.clusterId)

	logs = {
		'log': pattern % 'log', 
		'error': pattern % 'err', 
		'out': pattern % 'out',
	}

	try:
		f = open(logs[kind], 'r')
		data = string.join(f.readlines(), '')
		if not data:
			data = 'Empty file.'
		f.close()
	except IOError:
		data = 'Log file not found on server (has it been deleted?)'

	return HttpResponse(str(data), mimetype = 'text/plain')

@login_required
@profile
def get_permissions(request):
	"""
	Returns permissions for a given entity.
	The return value is a JSON object like:

	{'user' : {'read': true, 'write': true},
	 'group': {'read': true, 'write': false},
	 'others': {'read': false, 'write': false}}
	"""

	post = request.POST
	try:
		# Target entity
		target = post['Target']
		# Unique key to identify an element in table
		key = post['Key']
	except Exception, e:
		raise PluginError, "POST argument error. Unable to process data."

	ent = None
	if target == 'tag':
		tag = Tag.objects.filter(name = key)[0]
		ent = tag
	elif target == 'task':
		task = Processing_task.objects.filter(id = key)[0]
		ent = task
	elif target == 'imgsel':
		# Image selections
		sel = ImageSelections.objects.filter(name = key)[0]
		ent = sel
	elif target == 'config':
		config = ConfigFile.objects.filter(id = key)[0]
		ent = config
	else:
		raise PermissionsError, "Permissions for target %s not supported" % target

	perms = Permissions(ent.mode)
	isOwner = ent.user == request.user
	groups = [g.name for g in request.user.groups.all()]

	# Current user permissions
	cuser_read = cuser_write = False
	if (isOwner and perms.user.read) or \
		(ent.group.name in groups and perms.group.read) or \
		perms.others.read:
		cuser_read = True
	if (isOwner and perms.user.write) or \
		(ent.group.name in groups and perms.group.write) or \
		perms.others.write:
		cuser_write = True

	return HttpResponse(json.encode({
		'mode'			: str(perms), 
		'perms'			: perms.toJSON(), 
		'isOwner'		: isOwner,
		'username'		: ent.user.username,
		'groupname'		: ent.group.name,
		'groups'		: groups,
		'currentUser' 	: {'read': cuser_read, 'write': cuser_write},
	}), mimetype = 'text/plain')

@login_required
@profile
def set_permissions(request):
	"""
	Sets permissions for a given entity.
	The return value is a JSON object like:
	Perms is a string like: 1,1,1,0,0,0 specifying read/write bits for user/group/others respectively
	"""

	post = request.POST
	try:
		# Target entity
		target = post['Target']
		# Unique key to identify an element in table
		key = post['Key']
		# New perms to apply
		perms = post['Perms']
		group = post['Group']
	except Exception, e:
		raise PluginError, "POST argument error. Unable to process data."

	# Deserialize perms
	perms = [int(i) for i in perms.split(',')]
	# Owner can always read
	u = 4
	g = o = 0
	if perms[1] == 1: u += 2
	# Group
	if perms[2] == 1: g += 4
	if perms[3] == 1: g += 2
	# Others
	if perms[4] == 1: o += 4
	if perms[5] == 1: o += 2
	perms = "%d%d%d" % (u, g, o)

	group = Group.objects.filter(name = group)[0]
	isOwner = False
	error = ''

	if target == 'tag':
		tag = Tag.objects.filter(name = key)[0]
		ent = tag
	elif target == 'task':
		task = Processing_task.objects.filter(id = key)[0]
		ent = task
	elif target == 'imgsel':
		# Image selections
		sel = ImageSelections.objects.filter(name = key)[0]
		ent = sel
	elif target == 'config':
		config = ConfigFile.objects.filter(id = key)[0]
		ent = config
	else:
		raise PermissionsError, "Permissions for target %s not supported" % target

	if ent.user != request.user:
		error = 'Operation Not Allowed'
	else:
		ent.mode = perms
		ent.group = group
		ent.save()

	return HttpResponse(json.encode({'Error': error, 'Mode': ent.mode}), mimetype = 'text/plain')

@login_required
@profile
def get_user_default_permissions(request):
	"""
	Returns user default permissions
	{'default_mode': <mode>, 'default_group': <group>'}
	"""

	p = request.user.get_profile()

	return HttpResponse(str({
		'perms'	: Permissions(p.dflt_mode).toJSON(),
		'default_group'	: str(p.dflt_group),
	}), mimetype = 'text/plain')

if __name__ == '__main__':
	print 'Cannot be run from the command line.'
	sys.exit(2)
