"""
Management utility to create Youpi users.
"""

import os
from optparse import make_option
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('--password', dest = 'password', default = None, 
			help="Specifies the user password. If not specified, it will be set to the username's value."),
		make_option('--activate', action = 'store_true', dest = 'active', default = False,
			help="Activate the user account so that he is able to log in."),
	)
	help = 'Used to create a Youpi user account.'
	args = 'username'

	def handle(self, *args, **options):
		try: username = args[0]
		except IndexError:
			raise CommandError("You must give a username as first argument.")

		password = options.get('password', None)
		if not password:
			password = username

		try:
			user = User.objects.get(username = username)
			raise CommandError("User %s already exists." % username)
		except User.DoesNotExist:
			user = User.objects.create_user(username, '', password)
			user.is_staff= False
			user.is_active = options.get('active')
			user.save()

		print "Youpi user '%s' created successfully." % username
