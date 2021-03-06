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
from subprocess import call, Popen, PIPE


# Parse arguments
parser = argparse.ArgumentParser(description='Backup script, using rsync.')
parser.add_argument('config', default=sys.path[0]+os.sep+'backup.ini', help='configuration file')
parser.add_argument('--dry-run', '-n', action='store_true', help='perform a trial run')
parser.add_argument('--verbose', '-v', action='count', help='increase verbosity')
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
def rsync(source, destination, speed=0, rsync=None):
	command = [ '/usr/bin/rsync', '-avz', '--del', '--no-perms', '--no-owner', '--no-group']
	if args.dry_run:
		command.append('--dry-run')
	if args.verbose>0:
		command.append('-'+('v'*args.verbose))
	if rsync:
		command.append('--rsync-path')
		command.append(rsync)
	if speed > 0:
		command.append('--bwlimit=' + speed)
	if re.search(':/', destination) or re.search(':/', source):
		command.append('-e')
		command.append('/usr/bin/ssh')
	# Create sync folder
	if not os.path.exists(destination + os.sep + 'current'):
		os.makedirs(destination + os.sep + 'current')
	# Sync
	command.append(source + os.sep)
	command.append(destination + os.sep + 'current' + os.sep)
	return command


def execute(command, location):
	if args.verbose>0:
		p = Popen(command, stdout=PIPE)
		g = Popen(['/bin/grep', '-v', 'uptodate'], stdin=p.stdout)
		p.stdout.close();
		g.communicate()
		if g.returncode>1:
			sys.exit(1)
	else:
		p = Popen(command, stdout=PIPE, stderr=PIPE)
		g = Popen(['/bin/grep', '-v', 'uptodate'], stdin=p.stdout, stdout=PIPE, stderr=PIPE)
		p.stdout.close();
		out, err = g.communicate()
		if g.returncode>1:
			print 'Backup of {} failed.'.format(location)
			print ''
			print 'This is the error:'.format(location)
			print
			print err
			print ''
			print ''
			print 'This is the full output:'
			print ''
			print out
			sys.exit(1)


# Make backup
for location in locations:
	for folder in re.compile('[\s,:]+').split(config.get(location, 'folders')):
		destination = config.get('global', 'backupdir') + os.sep + location + os.sep + folder
		if not config.has_option(location, 'type') or config.get(location, 'type') != 'local':
			rsyncpath = config.get(location, 'rsync') if config.has_option(location, 'rsync') else None
			source = config.get(location, 'host') + ':' + config.get(location, 'home') + os.sep + folder
			# Sync
			execute(rsync(source, destination, config.get(location, 'speed'), rsyncpath), location)
			# Link
			if not args.dry_run:
				execute([ '/bin/cp', '-rl', destination + os.sep + 'current', destination + os.sep + today], location)
		else:
			source = config.get(location, 'home') + os.sep + folder
			# Create destination folder
			if not os.path.exists(destination):
				os.makedirs(destination)
			# Link
			if not args.dry_run:
				execute([ '/bin/cp', '-rl', source, destination + os.sep + today ], location)
		# Clean up
		for backup in filter(re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}$').match, sorted(os.listdir(destination))):
			if not re.search('-01$', backup) and backup < twoweeksago:
				call([ '/bin/rm', '-rf', destination + os.sep + backup ])
	print 'Backup of {} succeeded.'.format(location)
