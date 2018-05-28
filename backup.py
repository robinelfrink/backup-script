#!/usr/bin/env python

#
# Backup using rsync
# 


import argparse
import ConfigParser
from datetime import date
from datetime import timedelta
import os
import re
import sys
from subprocess import call


# Parse arguments
parser = argparse.ArgumentParser(description='Backup script, using rsync.')
parser.add_argument('config', default=sys.path[0]+os.sep+'backup.ini', help='Configuration file')
args = parser.parse_args()


# Read configuration
config = ConfigParser.ConfigParser()
config.read(args.config)


# Set variables
locations = config.sections()
locations.remove('global')
today = date.today().strftime('%Y-%m-%d')
twoweeksago = (date.today() - timedelta(days=14)).strftime('%Y-%m-%d')


# Create rsync command line
def rsync(source, destination, speed=0):
	command = [ '/usr/bin/rsync', '-avz', '--del' ]
	if speed > 0:
		command.append('--bwlimit=' + speed)
	if re.search(':/', destination):
		command.append('-e')
		command.append('/usr/bin/ssh')
	# Create sync folder
	if not os.path.exists(destination + os.sep + 'current'):
		os.makedirs(destination + os.sep + 'current')
	# Sync
	command.append(source + os.sep)
	command.append(destination + os.sep + 'current' + os.sep)
	return command


# Make backup
for location in locations:
	for folder in re.compile('[\s,:]+').split(config.get(location, 'folders')):
		destination = config.get('global', 'backupdir') + os.sep + location + os.sep + folder
		if not config.has_option(location, 'type') or config.get(location, 'type') != 'local':
			source = config.get(location, 'host') + ':' + config.get(location, 'home') + os.sep + folder
			# Sync
			result = call(rsync(source, destination, config.get(location, 'speed')))
			# Link
			result = call([ '/bin/cp', '-rl', destination + os.sep + 'current', destination + os.sep + today])
		else:
			source = config.get(location, 'home') + os.sep + folder
			# Create destination folder
			if not os.path.exists(destination):
				os.makedirs(destination)
			# Link
			result = call([ '/bin/cp', '-rl', source, destination + os.sep + today ])
		# Clean up
		for backup in filter(re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}$').match, sorted(os.listdir(destination))):
			if not re.search('-01$', backup) and backup < twoweeksago:
				call([ '/bin/rm', '-rf', destination + os.sep + backup ])
