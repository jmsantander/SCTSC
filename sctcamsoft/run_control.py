# Justin Vandenbroucke
# Created Apr 27 2013
# Handle run numbering.
# Automatically keep track of most recent run number and increment it.
# Uses a simple text file method

import os
import socket
import fnmatch
import shutil
import sys

def incrementRunNumber(outdirname):
	# Handle automatic run number incrementing using a local text file
	#dirname = os.getenv('TARGET_DATA')
	"""
	homedir = os.environ['HOME']
	print homedir
	if not os.path.exists('%s/target5and7data/test_suite_output'%(homedir)):
		userdict = {'colinadams':'cadams', 'tmeures':'meures', 'rfedora':'rfedora', 'justin':'justin'}
		whitneyUser = os.environ['USER']
		cobUser = userdict[whitneyUser]
		os.system('umount {}@cobalt02.icecube.wisc.edu:/data/wipac/CTA/target5and7data'.format(cobUser))
		os.system('sshfs {}@cobalt02.icecube.wisc.edu:/data/wipac/CTA/target5and7data ~{}/target5and7data/'.format(cobUser,whitneyUser))
		#os.system('udata')
		#os.system('data')
	"""
	runFilename = '%s/previousRun.txt' % outdirname
	file = open(runFilename,'r')
	previousRun = int(file.read())
	file.close()
	runID = previousRun + 1
	runString = "%d" % runID
	file = open(runFilename,'w')
	file.write(runString)
	file.close()


	if(runID%10000==0):
		cleanOldRuns(runID, outdirname)

	print("Starting Run %d.", runID)
	return runID

def getHostName():
	name = socket.gethostname()
	print("Host name is %s.", name)
	return name

def getDataDirname(hostname):
	homedir = os.environ['HOME']
	outdirname = '%s/target5and7data/' % homedir

	if os.path.exists(outdirname):
		print("Ready for writing to %s", outdirname)
	else:
		print("ERROR in getDataDirname(): output directory does not exist: %s.", outdirname)
		sys.exit(1)


	return outdirname



def cleanOldRuns(runID, outdirname):
	dstDir = outdirname + '/runs_{}_through_{}'.format(runID-10000, runID-1)
	try:
		os.mkdir(dstDir)
		os.chmod(dstDir, 0o777)
	except:
		print('Unable to create cleanup directory.')
	for file in os.listdir(outdirname):
		if(fnmatch.fnmatch(file, '*.log') or fnmatch.fnmatch(file, '*.fits') ):
			src = outdirname + '/' + file
			dst = dstDir + '/' + file
			try:
				shutil.move(src, dst)
			except:
				logging.error("Unable to move old files to cleanup directory.")
