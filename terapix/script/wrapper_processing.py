#!/usr/bin/env python 

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

from xml.parsers.expat import ExpatError
from types import *
from stat import *
import MySQLdb
import os, os.path
import sys, time, string
import marshal, base64, zlib
import xml.dom.minidom as dom
import socket, shutil, re, glob
#
sys.path.insert(0, '..')
from settings import *
from DBGeneric import *

NULLSTRING = ''
userData = {}
username = NULLSTRING

# Hold per-user output directory
CLUSTER_OUTPUT_PATH = NULLSTRING
RWX_ALL = S_IRWXU | S_IRWXG | S_IRWXO 

# Custom exceptions
class WrapperError(Exception): pass
class ExitError(Exception): pass

def debug(msg):
	"""
	Prints message to stdout
	"""
	print "[YWP@%s] %s" % (getNowDateTime()[-8:], msg)
	sys.stdout.flush()

def getNowDateTime(lt = None):
	"""
	Returns local date time
	"""
	if not lt:
		lt = time.time()
	return "%4d-%02d-%02d %02d:%02d:%02d" % time.localtime(lt)[:6]

def copyFileChmodAll(fileName, targetDir):
	"""
	Copy the file fileName to target directory targetDir and 
	chmod the file with the 666 permissions
	@param fileName full path to file
	@param targetDir destination directory
	"""
	try: 
		shutil.copy(fileName, targetDir)
	except Exception, e:
		debug("[Warning] Unable to copy file %s to output directory %s (%s)" % (fileName, targetDir, e))
		return
	
	try: os.chmod(os.path.join(targetDir, os.path.basename(fileName)), RWX_ALL)
	except Exception, e:
		pass

# FIXME: duplicated in PluginManager class...
def getConfigValue(content, keyword):
	"""
	Parses all lines of content looking for a keyword.
	Content must be a list of strings.
	Blank lines are skipped. Comments starting by # are ignored
	Keyword search is case-sensitive.
	@param content list of strings
	@param keyword word search in content
	@returns keyword's value or False
	"""
	for line in content:
		if line.find(keyword) != -1:
			if line[-1] == '\n': line = line[:-1]
			line = re.sub(r'#.*$', '', line)
			res = [k for k in re.split(r'[ \t]', line) if len(k)]
			try: return res[1]
			except: return False

	return False

def getJobClusterId(userData):
	"""
	Gets current job Condor ID
	@returns cluster id string
	"""

	pipe = os.popen(os.path.join(CONDOR_BIN_PATH, 'condor_q -global -xml -l'))
	data = pipe.readlines()
	pipe.close()

	# Condor returns several XML files as output... Output should
	# then be filtered
	files = []
	k = 0
	idxs = []
	for line in data:
		if line.find('version') != -1:
			idxs.append(k)
		k += 1

	k = 0
	idxs.append(len(data))
	while k < len(idxs)-1:
		files.append(data[idxs[k]:idxs[k+1]-1])
		k += 1

	try:
		for file in files:
			doc = dom.parseString(string.join(file[1:]))
			jNode = doc.getElementsByTagName('c')

			# First, try to locate the current job
			for job in jNode:
				jobData = {}
				data = job.getElementsByTagName('a')
				for a in data:
					if a.getAttribute('n') == 'Env':
						# Try to look for YOUPI_USER_DATA environment variable
						# If this is variable is found then this is a Youpi's job so we can keep it
						env = str(a.firstChild.firstChild.nodeValue)
						if env.find('YOUPI_USER_DATA') >= 0:
							m = re.search('YOUPI_USER_DATA=(.*?)$', env)
							XMLUserData = m.groups(0)[0]	
							c = XMLUserData.find(';')
							if c > 0:
								XMLUserData = XMLUserData[:c]

							XMLUserData = marshal.loads(base64.decodestring(str(XMLUserData)))
							try:
								if userData['JobID'] == XMLUserData['JobID']:
									# Job found
									data = job.getElementsByTagName('a')
									for b in data:
										if b.getAttribute('n') == 'ClusterId':
											jobData['ClusterId'] = str(b.firstChild.firstChild.nodeValue)

										elif b.getAttribute('n') == 'ProcId':
											jobData['ProcId'] = str(b.firstChild.firstChild.nodeValue)
									raise ExitError
							except KeyError:
								pass
	except ExitError:
		# Custom error to exit all nested for loops
		pass

	return "%s.%s" % (jobData['ClusterId'], jobData['ProcId'])

def ingestQFitsInResults(fitsinId, g):
	"""
	Stores results from QFits-in outputs.
	"""

	imgName = g.execute("""
SELECT i.name FROM youpi_rel_it AS r, youpi_image AS i, youpi_plugin_fitsin AS f 
WHERE r.task_id=f.task_id 
AND f.id=%s 
AND r.image_id=i.id;
""" % fitsinId)[0][0]

	# Log string that will be stored into DB at the end
	log = '+' + '-' * 20 + (" QualityFITS XML parsing results for %s " % imgName) + '-' * 20 + "\n"
	
	#FIXME imgName is not the right image name to parse xml from Qfits
	qfits_path = os.path.join(CLUSTER_OUTPUT_PATH, imgName, 'qualityFITS')
	log += "From path: %s\n\n" % qfits_path

	# Final XML data to store into DB
	fxdata = {}
	# Keywords of interest
	keywords = {'swarp.xml' : { 'XML_elem'	: 'PARAM',
								'ATTR_name' : 'name',
								'ATTR_values': (('SatLev_Default', 'satlev'),) },
				'scamp.xml' : {	'XML_elem'	: 'FIELD',
								'ATTR_name' : 'name',
								'ATTR_values': (('AstromOffset_Reference', 	'astoffra'), 
												('AstromSigma_Reference', 	'astoffde')) },
				'psfex.xml' : {	'XML_elem'	: 'PARAM',
								'ATTR_name' : 'name',
								'ATTR_values': (('FWHM_Min', 			'psffwhmmin'),
												('FWHM_Mean', 			'psffwhm'),
												('FWHM_Max', 			'psffwhmmax'),
												('Elongation_Min', 		'psfelmin'),
												('Elongation_Mean', 	'psfel'),
												('Elongation_Max', 		'psfelmax'),
												('Chi2_Min', 			'psfchi2min'),
												('Chi2_Mean', 			'psfchi2'),
												('Chi2_Max', 			'psfchi2max'),
												('Residuals_Min', 		'psfresimin'),
												('Residuals_Mean', 		'psfresi'),
												('Residuals_Max', 		'psfresimax'),
												('Asymetry_Min', 		'psfasymmin'),
												('Asymetry_Mean', 		'psfasym'),
												('Asymetry_Max', 		'psfasymmax'),
												('NStars_Accepted_Min', 'nstarsmin'),
												('NStars_Accepted_Mean','nstars'),
												('NStars_Accepted_Max', 'nstarsmax')) },
				# Different file format
				'accept.xml' : { 'Mbkg' : 'bkg'}
			}

	for file, rules in keywords.iteritems():
		try:
			file_path = os.path.join(qfits_path, file)
			doc = dom.parse(file_path)
			# Special case
			if file == 'accept.xml':
				for elem, field in rules.iteritems(): 
					data = doc.getElementsByTagName(elem)[0]
					fxdata[field] = data.firstChild.nodeValue
			else:
				data = doc.getElementsByTagName(rules['XML_elem'])
				for a in data:
					j = 0
					matched = False
					while j < len(rules['ATTR_values']) and not matched:
						if a.getAttribute(rules['ATTR_name']) == rules['ATTR_values'][j][0]:
							matched = True
							if not a.getAttribute('value'):
								log += "[%s] %s: no value found\n" % (file, a.getAttribute(rules['ATTR_name']))
								val = None
							else:
								val = a.getAttribute('value')
	
							fxdata[rules['ATTR_values'][j][1]] = val
						j += 1
		except IOError, e:
			log += "%s\n" % e
		except ExpatError, e:
			log += "[ERROR] in file %s: %s\n" % (file_path, e)

	if not fxdata:
		log += "Command line: %s\n" % string.join(sys.argv[2:], ' ')
		log += "** No results found\n"
	else:
		log += "Summary:\n"
		for field, value in fxdata.iteritems():
			log += "%15s: %s\n" % (field, value)

	# Stores results ingestion log
	try:
		g.setTableName('youpi_plugin_fitsin')
		#
		# QF results ingestion log serialization: base64 encoding over zlib compression
		# To retreive data: zlib.decompress(base64.decodestring(encoded_data))
		#
		g.update(	qflog = base64.encodestring(zlib.compress(log, 9)).replace('\n', ''),
					wheres = {'id': fitsinId} )
	except Exception, e:
		raise WrapperError, e

	if not fxdata:
		debug(log)
		return

	try:
		q = 'UPDATE youpi_plugin_fitsin SET '
		for field, value in fxdata.iteritems():
			if value:
				q += "%s=\"%s\"," % (field, value)

		q = q[:-1]
		q += " WHERE id=%s;" % fitsinId

		res = g.execute(q)
	except Exception, e:
		raise WrapperError, e

	# For debugging purpose
	debug(log)

def task_start_log(userData, start, kind_id = None):
	
	user_id = userData['UserID']
	kind = userData['Kind']

	db = DB(host = DATABASE_HOST,
			user = DATABASE_USER,
			passwd = DATABASE_PASSWORD,
			db = DATABASE_NAME)

	g = DBGeneric(db.con)

	if not kind_id:
		try:
			res = g.execute("SELECT id FROM youpi_processing_kind WHERE name='%s'" % kind)
			kind_id = res[0][0]
		except Exception, e:
			raise WrapperError, e

	res = g.execute("SELECT dflt_group_id, dflt_mode FROM youpi_siteprofile WHERE user_id=%d" % int(user_id))
	perms = {'group_id': res[0][0], 'mode': res[0][1]}
	try:
		g.begin()
		g.setTableName('youpi_processing_task')
		g.insert(	user_id = int(user_id),
					kind_id = int(kind_id),
					clusterId = getJobClusterId(userData),
					start_date = start,
					end_date = getNowDateTime(),
					title = userData['Descr'],
					hostname = socket.getfqdn(),
					results_output_dir = userData['ResultsOutputDir'],
					group_id = perms['group_id'],
					mode = perms['mode'],
					success = 0 )
		task_id = g.con.insert_id()
	except Exception, e:
		raise WrapperError, e

	# Fill this table only if the processing is image related
	try:
		imgID = userData['ImgID']
		g.setTableName('youpi_rel_it')

		if type(imgID) is ListType:
			imgName = None
			for img_id in imgID:
				g.insert(	image_id = img_id,
							task_id = task_id )
		else:
			imgName = g.execute("SELECT name FROM youpi_image WHERE id='%s'" % imgID)[0][0]
			g.insert(	image_id = imgID,
						task_id = task_id )
	except Exception, e:
		imgName = None

	return (imgName, task_id, g)

def task_end_log(userData, g, task_error_log, task_id, success, kind):
	if not success:
		try:
			content = string.join(open(task_error_log, 'r').readlines(), '')
		except IOError:
			content = task_error_log

		# Stores error log into DB
		try:
			g.setTableName('youpi_processing_task')
			g.update(	error_log = base64.encodestring(zlib.compress(content, 9)).replace('\n', ''),
						wheres = {'id': task_id} )
		except Exception, e:
			g.con.rollback()
			raise WrapperError, e

		if kind == 'fitsin':
			# Stores results of QF into DB when unsuccessful (stores at least flat, mask, reg paths and QF config content)
			try:
				g.setTableName('youpi_plugin_fitsin')
				g.insert(	task_id = int(task_id),
							flat = userData['Flat'],
							mask = userData['Mask'],
							reg = userData['Reg'],
							exitIfFlatMissing = userData['ExitIfFlatMissing'],
							#
							# QF config file serialization: base64 encoding over zlib compression
							# To retreive data: zlib.decompress(base64.decodestring(encoded_data))
							#
							qfconfig = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							www = NULLSTRING )
			except Exception, e:
				raise WrapperError, e

		elif kind == 'scamp':
			try:
				g.setTableName('youpi_plugin_scamp')
				g.insert(	task_id = int(task_id),
							config = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							ldac_files = base64.encodestring(marshal.dumps(userData['LDACFiles'])).replace('\n', ''),
							www = os.path.join(	WWW_SCAMP_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							thumbnails = 0,
							aheadPath = userData['AheadPath']
				)
			except Exception, e:
				raise WrapperError, e

		elif kind == 'swarp':
			try:
				g.setTableName('youpi_plugin_swarp')
				g.insert(	task_id = int(task_id),
							config = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							useQFITSWeights = userData['UseQFITSWeights'],
							www = os.path.join(	WWW_SWARP_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							thumbnails = 0,
							headPath = userData['HeadPath'],
							useHeadFiles = userData['UseHeadFiles']
				)
			except Exception, e:
				raise WrapperError, e

		elif kind == 'sex':
			try:
				g.setTableName('youpi_plugin_sex')
				g.insert(	task_id = int(task_id),
							config = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							param  = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ParamFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							www = os.path.join(	WWW_SEX_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							thumbnails = 0,
				)
			except Exception, e:
				raise WrapperError, e

	try:
		g.setTableName('youpi_processing_task')
		g.update(	end_date = getNowDateTime(time.time()),
					success = success,
					wheres = {'id': task_id} )
		g.con.commit()
	except Exception, e:
		g.con.rollback()
		raise WrapperError, e
	
	g.con.close()

def process(userData, kind_id, argv):
	"""
	Execute system call then updates the database consequently.
	exit_code != 0 means problem.
	"""

	user_id = userData['UserID']
	kind = userData['Kind']
	# Log file to store
	storeLog = '_condor_stderr'
	success = 0

	db = DB(host = DATABASE_HOST,
			user = DATABASE_USER,
			passwd = DATABASE_PASSWORD,
			db = DATABASE_NAME)

	g = DBGeneric(db.con)

	start = getNowDateTime(time.time())
	(imgName, task_id, g) = task_start_log(userData, start, kind_id)


	################### PRE-PROCESSING STUFF GOES HERE ########################################

	# Automatic .head (or .ahead for Scamp) file generation
	if kind == 'fitsin':
		try:
			from genimgdothead import genImageDotHead	
			img_id = userData['ImgID']
			data, lenght, missing = genImageDotHead(int(img_id))
			if len(data):
				headname = userData['RealImageName'][0] + '.head'
				f = open(headname, 'w')
				for i in range(lenght):
					for k, v in data.iteritems():
						f.write("%s= %s\n" % (k, v))
					f.write("END\n")
				f.close()
				debug("Generated: %s" % headname)
		except Exception, e:
			debug("Error during automatic .head file generation: %s" % e)

		flatname = g.execute("SELECT flat FROM youpi_image WHERE id=%s" % userData['ImgID'])[0][0]
		if userData['ExitIfFlatMissing']:
			# Check for flat file
			flatFile = os.path.join(userData['Flat'], flatname)
			if not os.path.exists(flatFile):
				exit_code = 1
				success = 0
				debug("Error: FLAT file %s has not been found (and you asked Youpi to halt in this case)" % flatFile)
				debug("Exiting now...")
				task_end_log(userData, g, storeLog, task_id, success, kind)
				debug("Exited (code %d)" % exit_code)
				sys.exit(exit_code)
			else:
				debug("Found FLAT file: %s" % flatFile)
		else:
			debug("No check for FLAT image %s existence (checkbox was unchecked)" % flatname)

		imgName = g.execute("SELECT name FROM youpi_image WHERE id='%s'" % img_id)[0][0]
		if userData['RealImageName'][0] != str(imgName):
			os.mkdir(imgName)
			os.chdir(imgName)
			os.mkdir('qualityFITS')
			os.chmod('qualityFITS', RWX_ALL)
			os.chdir('../')
			os.chmod(imgName, RWX_ALL)


	# Other preprocessing stuff
	elif kind == 'sex':
		img_id = userData['ImgID']
		imgName = g.execute("SELECT name FROM youpi_image WHERE id='%s'" % img_id)[0][0]
		os.mkdir(imgName)
		os.chmod(imgName, RWX_ALL)
		os.system("mv sex-config* sex-param* *.conv *.nnw %s" %(imgName))
		os.chdir(imgName)

		# FIXME: remove this code that won't get executed  at all since the files are not yet
		# transferred... (see Swarp plugin code for a fix)
		fzs = glob.glob('*.fits.fz')
		for fz in fzs:
			debug("Sextractor Preprocessing: uncompressing %s" % fz)
			os.system("%s %s %s" % (CMD_IMCOPY, fz, fz[:-3]))

	################### END OF PRE-PROCESSING  ################################################


	# Execute process, waiting for completion
	cmd_line = string.join(argv, ' ')
	debug("Executing command line: %s\n" % cmd_line)
	try:
		exit_code = os.system(cmd_line)
	except:
		pass
	debug("Command line execution terminated (code %d)" % exit_code)


	################### POST-PROCESSING STUFF GOES HERE ########################################


	debug("Beginning post-processing operations")
	# QualityFITS-In processing
	if kind == 'fitsin':
		if exit_code == 0:
			time.sleep(2)
			data = os.popen('ls */*/.finished 2>&1')
			done = data.readlines()
			data.close()

			if len(done):
				# QF was successful
				success = 1
			else:
				storeLog = '_condor_stdout'

			# Stores results of QF into DB when successful (stores at least flat, mask, reg paths and QF config content)
			try:
				g.setTableName('youpi_plugin_fitsin')
				g.insert(	task_id = int(task_id),
							flat = userData['Flat'],
							mask = userData['Mask'],
							reg = userData['Reg'],
							exitIfFlatMissing = userData['ExitIfFlatMissing'],
							#
							# QF config file serialization: base64 encoding over zlib compression
							# To retreive data: zlib.decompress(base64.decodestring(encoded_data))
							#
							qfconfig = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							www = os.path.join(	WWW_FITSIN_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:],
												imgName,
												'qualityFITS' ) + '/'
				)
				fitsin_id = g.con.insert_id()
	
				# Now results ingestion takes place
				ingestQFitsInResults(fitsin_id, g)
			except Exception, e:
				raise WrapperError, e

	elif kind == 'scamp':
		if exit_code == 0:
			# FIXME: look for scamp.xml; parse it and look for errors in it
			success = 1

			configContent = open(os.path.basename(userData['ConfigFile']), 'r').readlines()
			try:
				if HAS_CONVERT:
					convert = 1
				else:
					convert = 0
					debug("[Warning] convert utility not found. No thumbnails will be generated")
				g.setTableName('youpi_plugin_scamp')
				g.insert(	task_id = int(task_id),
							#
							# Scamp config file serialization: base64 encoding over zlib compression
							#
							config = base64.encodestring(zlib.compress(string.join(configContent, ''), 9)).replace('\n', ''),
							ldac_files = base64.encodestring(marshal.dumps(userData['LDACFiles'])).replace('\n', ''),
							www = os.path.join(	WWW_SCAMP_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							thumbnails = convert,
							aheadPath = userData['AheadPath']
				)
				scamp_id = g.con.insert_id()
			except Exception, e:
				raise WrapperError, e

			# Copy XSL stylesheet
			try:
				xslPath = re.search(r'file://(.*)$', getConfigValue(configContent, 'XSL_URL'))
				if xslPath: copyFileChmodAll(xslPath.group(1), userData['ResultsOutputDir'])
			except TypeError, e:
				# No custom XSL_URL value
				pass

			# Create thumbnails for group #1, if convert cmd available
			if HAS_CONVERT:
				debug("Creating image thumbnails for group #1")
				olds = 	glob.glob(os.path.join(userData['ResultsOutputDir'], 'tn_*.png'))
				for old in olds:
					os.remove(old)
				pngs = glob.glob(os.path.join(userData['ResultsOutputDir'], '*_1.png'))
				for png in pngs:
					os.system("%s %s %s" % (CMD_CONVERT_THUMB, 
											# Source
											png,
											# Destination
											os.path.join(os.path.dirname(png), 'tn_' + os.path.basename(png))))

	elif kind == 'sex':
		if exit_code == 0:
			success = 1

			configContent = open(os.path.basename(userData['ConfigFile']), 'r').readlines()
			try:
				if HAS_CONVERT:
					convert = 1
				else:
					convert = 0
					debug("[Warning] convert utility not found. No thumbnails will be generated")
				g.setTableName('youpi_plugin_sex')
				g.insert(	task_id = int(task_id),
							weightPath = userData['Weight'],
							flagPath = userData['Flag'],
							psfPath = userData['Psf'],
							dualMode = userData['DualMode'],
							dualImage = userData['DualImage'],
							dualweightPath = userData['DualWeight'],
							dualflagPath = userData['DualFlag'],
							#
							# Sex config file serialization: base64 encoding over zlib compression
							#
							config = base64.encodestring(zlib.compress(string.join(configContent, ''), 9)).replace('\n', ''),
							param  = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ParamFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							www = os.path.join(	WWW_SEX_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:]) + '/',
							thumbnails = convert,
				)
				sex_id = g.con.insert_id()
			except Exception, e:
				raise WrapperError, e

			# Copy XSL stylesheet
			try:
				xslPath = re.search(r'file://(.*)$', getConfigValue(configContent, 'XSL_URL'))
				if xslPath: copyFileChmodAll(xslPath.group(1), userData['ResultsOutputDir'])
			except TypeError, e:
				# No custom XSL_URL value
				pass

			# Gets image name
			motif = "CHECKIMAGE_NAME"

			path_cf = userData['ConfigFile']

			cfile = path_cf.split('/')[2]
			f = open(cfile,'r')
			for ligne in f :
				if motif in ligne:
					m = re.findall(r'(\w+\.fits)', ligne)
			
			f.close()

			for current in m:
				name = current.split('.')
				cur = name[0]

				if (os.path.exists(cur +'.fits')):

					os.system(CMD_SWARP + " %s -SUBTRACT_BACK N -WRITE_XML N -PIXELSCALE_TYPE MANUAL -PIXEL_SCALE 4.0 -RESAMPLING_TYPE BILINEAR -IMAGEOUT_NAME %s" % (cur + '.fits', os.path.join(userData['ResultsOutputDir'], 'temp.fits')))
					# Converts produced FITS image into PNG format
					tiff = os.path.join(userData['ResultsOutputDir'], cur + '.tif')
					os.system("%s %s -OUTFILE_NAME %s 2>/dev/null" % (CMD_STIFF,os.path.join(userData['ResultsOutputDir'], 'temp.fits'), tiff))
					os.remove(os.path.join(userData['ResultsOutputDir'], 'temp.fits'))

					os.system("%s %s %s" % (CMD_CONVERT, tiff, os.path.join(userData['ResultsOutputDir'], cur + '.png')))
					if HAS_CONVERT:
						debug("Creating image thumbnails")
						os.system("%s %s %s" % (CMD_CONVERT_THUMB, tiff, os.path.join(userData['ResultsOutputDir'] , 'tn_' + cur + '.png')))
				
					os.remove(tiff)


	elif kind == 'swarp':
		if exit_code == 0:
			# FIXME: look for swarp.xml; parse it and look for errors in it
			success = 1

			configContent = open(os.path.basename(userData['ConfigFile']), 'r').readlines()

			# Final stack image ingestion
			debug("Starting ingestion of final stack image...")
			try:
				from stack_ingestion import run_stack_ingestion
				imgout = getConfigValue(configContent, 'IMAGEOUT_NAME')
				finalStackName = run_stack_ingestion(g, os.path.join(userData['ResultsOutputDir'], imgout), user_id)
				debug("Final stack ingestion complete")
				if finalStackName != imgout:
					# Stack name has changed! 
					# The config file IMAGEOUT_NAME must be modified
					j = 0
					for line in configContent:
						if line.find('IMAGEOUT_NAME') != -1:
							line = re.sub(r'#.*$', '', line)
							res = [k for k in re.split(r'[ \t]', line) if len(k)]
							try: res[1] = finalStackName
							except:
								debug("IMAGEOUT_NAME parameter: could not set value")
								raise
							configContent[j] = string.join(res, '\t')
							break
						j += 1
					if j == len(configContent):
						debug("Could not find IMAGEOUT_NAME parameter in the config file")
						raise WrapperError, "IMAGEOUT_NAME param not found"
					debug("IMAGEOUT_NAME parameter value set to %s" % finalStackName)

					# The stack file has to be renamed on disk
					os.rename(os.path.join(userData['ResultsOutputDir'], imgout), os.path.join(userData['ResultsOutputDir'], finalStackName))
					debug("Renamed %s to %s in %s" % (imgout, finalStackName, userData['ResultsOutputDir']))

			except Exception, e:
				debug("Could not ingest final stack image. Error: %s" % e)
				success = 0
				exit_code = 1

			try:
				if HAS_CONVERT:
					convert = 1
				else:
					convert = 0
					debug("[Warning] convert utility not found. No thumbnails will be generated")
				g.setTableName('youpi_plugin_swarp')
				g.insert(	task_id = int(task_id),
							#
							# Swarp config file serialization: base64 encoding over zlib compression
							#
							config = base64.encodestring(zlib.compress(string.join(configContent, ''), 9)).replace('\n', ''),
							www = os.path.join(	WWW_SWARP_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							weightPath = userData['WeightPath'],
							useQFITSWeights = userData['UseQFITSWeights'],
							headPath = userData['HeadPath'],
							useHeadFiles = userData['UseHeadFiles'],
							thumbnails = convert
				)
				swarp_id = g.con.insert_id()
			except Exception, e:
				raise WrapperError, e

			# Copy XSL stylesheet
			try:
				xslPath = re.search(r'file://(.*)$', getConfigValue(configContent, 'XSL_URL'))
				if xslPath: copyFileChmodAll(xslPath.group(1), userData['ResultsOutputDir'])
			except TypeError, e:
				# No custom XSL_URL value
				pass

			# Gets image name
			imgout = getConfigValue(configContent, 'IMAGEOUT_NAME')
			if imgout:
				# Converts produced FITS image into PNG format
				tiff = os.path.join(userData['ResultsOutputDir'], 'swarp.tif')
				os.system("%s %s -OUTFILE_NAME %s -BINNING 40 2>/dev/null" % (CMD_STIFF, imgout, tiff))
				os.system("%s %s %s" % (CMD_CONVERT, tiff, os.path.join(userData['ResultsOutputDir'], 'swarp.png')))
				if HAS_CONVERT:
					debug("Creating image thumbnails")
					os.system("%s %s %s" % (CMD_CONVERT_THUMB, tiff, os.path.join(userData['ResultsOutputDir'], 'tn_swarp.png')))
			else:
				debug("[Warning] IMAGEOUT_NAME keyword not found in configuration file")

	else:
		# Default: success is set to that task_end_log marks the job as successful
		if exit_code == 0:
			success = 1


	################### END OF POST-PROCESSING  ################################################


	task_end_log(userData, g, storeLog, task_id, success, kind)

	debug("Post-processing operations terminated");
	debug("Exited (code %d)" % exit_code)
	sys.exit(exit_code)

def init_job(userData):
	global username
	debug("Checking/setting environment before running job")

	db = DB(host = DATABASE_HOST,
			user = DATABASE_USER,
			passwd = DATABASE_PASSWORD,
			db = DATABASE_NAME)

	g = DBGeneric(db.con)

	# StartupDelay checks to prevent too many connections to DB
	try:
		delay = userData['StartupDelay']
		time.sleep(delay)
	except KeyError:
		pass

	# Check that argv[1] (processing kind) exists in DB or raise error
	res = g.execute("SELECT id FROM youpi_processing_kind WHERE name='%s'" % userData['Kind'])
	username = g.execute("SELECT username FROM auth_user WHERE id=%s" % userData['UserID'])[0][0]
	g.con.close()

	if not len(res):
		raise WrapperError, "Processing kind not supported: '%s'" % userData['Kind']

	# Exports current hostname to ENV
	os.environ['HOSTNAME'] = socket.getfqdn()

	# Build per-user output path
	user_path = os.path.join(PROCESSING_OUTPUT, username)
	CLUSTER_OUTPUT_PATH = os.path.join(user_path, userData['Kind'])
	custom_dir = userData['ResultsOutputDir']

	try:
		if not os.path.isdir(CLUSTER_OUTPUT_PATH):
			if not os.path.isdir(user_path):
				os.mkdir(user_path)
				# default 0777 used by mkdir does not work as expected with Condor + NFS
				# use chmod instead
				os.chmod(user_path, RWX_ALL)
			if not os.path.isdir(CLUSTER_OUTPUT_PATH):
				os.mkdir(CLUSTER_OUTPUT_PATH)
				os.chmod(CLUSTER_OUTPUT_PATH, RWX_ALL)

		if CLUSTER_OUTPUT_PATH != custom_dir:
			# A custom directory has been defined
			if not os.path.isdir(custom_dir):
				os.mkdir(custom_dir)
				os.chmod(custom_dir, RWX_ALL)

		# Finally, always use userData['ResultsOutputDir'] as output directory
		CLUSTER_OUTPUT_PATH = custom_dir
	except Exception, e:
		error_msg = "Could not create CLUSTER_OUTPUT_PATH directory (%s): %s\n\n*** Maybe check for a NFS issue (automount)?" % (CLUSTER_OUTPUT_PATH, e)
		error_msg += "\nResultsOutputDir=" + custom_dir
		debug("[Error] " + error_msg)
		start = getNowDateTime(time.time())
		imgName, task_id, g = task_start_log(userData, start)
		task_end_log(userData, g, error_msg, task_id, 0, userData['Kind'])
		sys.exit(1)

	# Run processing
	debug("Checks complete, processing data...")
	process(userData, res[0][0], sys.argv[2:])


if __name__ == '__main__':
	debug("Wrapper processing script started")
	#
	# De-serialize data passed as a string into arg 1
	#
	userData = marshal.loads(base64.decodestring(sys.argv[1]))
	# Now, open the userdata file when available to merge its content with userData
	try:
		userdataFile = userData['BigUserData']
		try:
			f = open(userdataFile, 'r')
			data = f.readlines()[0]
		except Exception, e:
			raise WrapperError, "Could not access biguserdata: %s" % e
		userData.update(marshal.loads(base64.decodestring(data)))
	except KeyError:
		debug('No userdata file passed')
		pass

	# Connection object to MySQL database 
	try:
		init_job(userData)
	except MySQLdb.DatabaseError, (code, msg):
		if code == 1040:
			# Too many connections, one more try before aborting
			time.sleep(10)
			try:
				init_job(userData)
			except Exception, e:
				error_msg = "Unable to start job\n%s" % e
				start = getNowDateTime(time.time())
				imgName, task_id, g = task_start_log(userData, start)
				task_end_log(userData, g, error_msg, task_id, 0, userData['Kind'])
				sys.exit(1)
		else:
			debug("[Error] %s: %s" % (code, msg))
			sys.exit(1)

	except IndexError, e:
		debug("[Error] %s" % e)
		sys.exit(1)
