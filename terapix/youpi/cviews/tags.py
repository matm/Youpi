
import time
from types import *
#
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseServerError, HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.template import RequestContext
#
from terapix.youpi.models import *
from terapix.youpi.cviews import *
#
from settings import *

def fetch_tags(request):
	"""
	Returns all available tags
	"""

	tags = Tag.objects.all().order_by('name')
	data = [{'name': str(tag.name), 'style': str(tag.style), 'comment': str(tag.comment), 'username': str(tag.user.username), 'date': str(tag.date)} for tag in tags] 

	return HttpResponse(str({'tags' : data}), mimetype = 'text/plain')

def get_tag_info(request):
	"""
	Returns one tag's information or empty dictionnary if tag does not exist
	"""

	try:
		name = request.POST['Name']
	except Exception, e:
		return HttpResponseForbidden()

	tag = Tag.objects.filter(name__exact = name)

	if tag:
		tag = tag[0]
		info = {
			'name': str(tag.name),
			'style': str(tag.style),
			'date': str(tag.date),
			'comment': str(tag.comment),
			'username': str(tag.user.username),
		}
	else:
		info = {}

	return HttpResponse(str({'info' : info}), mimetype = 'text/plain')

def save_tag(request):
	"""
	Saves new tag to DB.
	"""

	try:
		name = request.POST['Name']
		comment = request.POST.get('Comment', '')
		# CSS style
		style = request.POST['Style']
	except Exception, e:
		return HttpResponseForbidden()

	try:
		tag = Tag(name = name, user = request.user, comment = comment, style = style)
		tag.save()
	except Exception, e:
		return HttpResponse(str({'Error' : str(e)}), mimetype = 'text/plain')

	return HttpResponse(str({'saved' : str(name)}), mimetype = 'text/plain')

def update_tag(request):
	"""
	Updates tag
	"""

	try:
		key = request.POST['NameOrig']
		name = request.POST['Name']
		comment = request.POST.get('Comment', '')
		style = request.POST['Style'] # CSS style
	except Exception, e:
		return HttpResponseForbidden()

	tag = Tag.objects.filter(name__exact = key)[0]
	try:
		tag.name = name
		tag.comment = comment
		tag.style = style
		tag.save()
	except Exception, e:
		return HttpResponse(str({'Error' : str(e)}), mimetype = 'text/plain')

	return HttpResponse(str({'updated' : str(name), 'oldname' : str(key)}), mimetype = 'text/plain')

def delete_tag(request):
	"""
	Deletes tag
	"""

	try:
		name = request.POST['Name']
	except Exception, e:
		return HttpResponseForbidden()

	try:
		tag = Tag.objects.filter(name__exact = name)[0]
		tag.delete()
		# FIXME
		# Delete associations in youpi_rel_tagi
	except Exception, e:
		return HttpResponse(str({'Error' : str(e)}), mimetype = 'text/plain')

	return HttpResponse(str({'deleted' : str(name)}), mimetype = 'text/plain')

def tag_mark_images(request):
	"""
	Marks image(s) with tag(s)
	"""

	try:
		tags = eval(request.POST['Tags'])
		idList = eval(request.POST['IdList'])[0]
	except Exception, e:
		return HttpResponseForbidden()

	# Marked image count
	marked = 0
	images = Image.objects.filter(id__in = idList)
	tags = Tag.objects.filter(name__in = tags)
	imgtags = Rel_tagi.objects.filter(image__in = images)

	try:
		for img in images:
			newrel = False
			for tag in tags:
				try:
					tagi = Rel_tagi(image = img, tag = tag)
					tagi.save()
					newrel = True
				except IntegrityError:
					# Already tagged
					pass
			if newrel:
				marked += 1
	except Exception, e:
		return HttpResponse(str({'Error' : str(e)}), mimetype = 'text/plain')

	return HttpResponse(str({'marked' : marked}), mimetype = 'text/plain')

def tag_unmark_images(request):
	"""
	Unmarks image(s) with tag(s)
	"""

	try:
		tags = eval(request.POST['Tags'])
		idList = eval(request.POST['IdList'])[0]
	except Exception, e:
		return HttpResponseForbidden()

	# Unmarked image count
	unmarked = 0
	images = Image.objects.filter(id__in = idList)
	tags = Tag.objects.filter(name__in = tags)
	imgtags = Rel_tagi.objects.filter(image__in = images, tag__in = tags)

	for rel in imgtags:
		rel.delete()
		unmarked += 1

	return HttpResponse(str({'unmarked' : int(unmarked)}), mimetype = 'text/plain')

