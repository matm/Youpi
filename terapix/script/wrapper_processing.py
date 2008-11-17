#!/usr/bin/env python 

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

# Custom exceptions
class WrapperError(Exception): pass

def getNowDateTime(lt = time.time()):
	"""
	Returns local date time
	"""
	return "%4d-%02d-%02d %02d:%02d:%02d" % time.localtime(lt)[:6]

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
		print log
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
	print log

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

	try:
		g.begin()
		g.setTableName('youpi_processing_task')
		g.insert(	user_id = int(user_id),
					kind_id = int(kind_id),
					start_date = start,
					end_date = getNowDateTime(),
					title = userData['Descr'],
					hostname = socket.getfqdn(),
					results_output_dir = userData['ResultsOutputDir'],
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
							#
							# QF config file serialization: base64 encoding over zlib compression
							# To retreive data: zlib.decompress(base64.decodestring(encoded_data))
							#
							qfconfig = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							www = NULLSTRING )
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

	start = getNowDateTime(time.time())

	# First, Execute process and wait for completion
	try:
		exit_code = os.system(string.join(argv, ' '))
	except:
		pass

	(imgName, task_id, g) = task_start_log(userData, start, kind_id)

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

	elif kind == 'skel':
		if exit_code == 0:
			success = 1

	elif kind == 'scamp':
		if exit_code == 0:
			# FIXME: look for scamp.xml; parse it and look for errors in it
			success = 1

			try:
				if HAS_CONVERT:
					convert = 1
				else:
					convert = 0
				g.setTableName('youpi_plugin_scamp')
				g.insert(	task_id = int(task_id),
							#
							# Scamp config file serialization: base64 encoding over zlib compression
							#
							config = base64.encodestring(zlib.compress(string.join(open(os.path.basename(userData['ConfigFile']), 'r').readlines(), ''), 9)).replace('\n', ''),
							ldac_files = base64.encodestring(marshal.dumps(userData['LDACFiles'])).replace('\n', ''),
							www = os.path.join(	WWW_SCAMP_PREFIX, 
												username, 
												userData['Kind'], 
												userData['ResultsOutputDir'][userData['ResultsOutputDir'].find(userData['Kind'])+len(userData['Kind'])+1:] ),
							thumbnails = convert
				)
				scamp_id = g.con.insert_id()
			except Exception, e:
				raise WrapperError, e

			# Copy XSL stylesheet
			pipe = os.popen("/usr/local/bin/scamp -dd|grep XSL_URL 2>&1") 
			data = pipe.readlines()
			pipe.close()

			xslPath = re.search(r'file://(.*)$', data[0]).group(1)
			shutil.copy(xslPath, userData['ResultsOutputDir'])

			# Create thumbnails for group #1, if convert cmd available
			if HAS_CONVERT:
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
	else:
		# Put other processing stuff here
		pass

	task_end_log(userData, g, storeLog, task_id, success, kind)


def init_job(userData):
	global username

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

	# Build per-user output path
	user_path = os.path.join(PROCESSING_OUTPUT, username)
	CLUSTER_OUTPUT_PATH = os.path.join(user_path, userData['Kind'])
	custom_dir = userData['ResultsOutputDir']

	try:
		RWX_ALL = S_IRWXU | S_IRWXG | S_IRWXO 
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
		start = getNowDateTime(time.time())
		imgName, task_id, g = task_start_log(userData, start)
		task_end_log(userData, g, error_msg, task_id, 0, userData['Kind'])
		sys.exit(1)

	# Run processing
	process(userData, res[0][0], sys.argv[2:])


if __name__ == '__main__':
	#
	# De-serialize data passed as a string into arg 1
	#
	userData = marshal.loads(base64.decodestring(sys.argv[1]))

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
			print "Error %s: %s" % (code, msg)
			sys.exit(1)

	except IndexError, e:
		print "Error:", e
		sys.exit(1)
