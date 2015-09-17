#!/usr/bin/python
from __future__ import division
import json
import subprocess
import urllib2
import re
import sys
import getopt

JBOSS_HOME = "/opt/jboss-eap-6.2"

def usage():
	print sys.argv[0],"usage:";
	print """		-m <monitoing attributes> [ heap-memory-usage | jdbc-connections | active-sessions ]
		-d <monitoing parameters> [ Required: jdbc-connections | active-sessions ]
		-s <monitoing parameters> [ Optional: active-sessions ]
		-u <monitoing parameters> [ Optional: active-sessions ]
		-w <warning levels>	
		-c <critical levels>
	eg:
		check_jboss -m heap-memory-usage -w 10 -c 20
		check_jboss -m active-sessions -d jenkins.war -w 10 -c 20
	"""

def jbosscli (JBOSS_HOME,ARG) :
	cmd=JBOSS_HOME + "/bin/jboss-cli.sh"
	output = subprocess.Popen([cmd , '-c' , ARG], stdout=subprocess.PIPE).communicate()[0]
	output = output.replace('=>',':')
	output = re.sub(r'\dL','', output)
	return output

def heapmemoryusage (JBOSS_HOME,WARN,CRIT) :
	ARG = "/core-service=platform-mbean/type=memory:read-attribute(name=heap-memory-usage)"
	try: 
		output = json.loads(jbosscli(JBOSS_HOME,ARG))
	except ValueError:
		print "CRITICAL : JBOSS CLI excution failed."
		sys.exit(2)
	else:
		if output["outcome"] == "success":
			usedpercentage = int(output["result"]["used"] * 100 / output["result"]["max"])
			threshold(usedpercentage,WARN,CRIT,"Heap-memory-usage","%")
		else:
			print "CRITICAL : JBOSS CLI excution failed."
			sys.exit(2)

def threshold(VALUE,WARN,CRIT,ARG1,ARG2):
	VALUE = int(VALUE)
	WARN = int(WARN)
	CRIT = int(CRIT)
	if ( VALUE >= CRIT ):
		print "CRITICAL : " + ARG1 + " = " + str(VALUE) + ARG2
		sys.exit(2)
	elif ( VALUE >= WARN ):
		print "WARNING : " + ARG1 + " = " + str(VALUE) + ARG2
		sys.exit(1)
	else:
		print "OK : " + ARG1 + " = " + str(VALUE) + ARG2
		sys.exit(0)

def sqlconnections (JBOSS_HOME,_data,WARN,CRIT):
	ARG = "/subsystem=datasources/data-source=" + _data + "/statistics=pool :read-resource(recursive=true, include-runtime=true)"
	output = json.loads(jbosscli(JBOSS_HOME,ARG))
	if output["outcome"] == "success":
		ActiveCount = int(output["result"]["ActiveCount"])
		AvailableCount = int(output["result"]["AvailableCount"])
		usedpercentage = float( ActiveCount * 100 / AvailableCount)
		string = "JDBC-Connections" + _data
		threshold(usedpercentage,WARN,CRIT,string,"%")
	else:
		sys.exit(2)

def activesessions (JBOSS_HOME,_data,_sub,_ut,WARN,CRIT):
	ARG = "/deployment=" + _data + _sub + _ut + ":read-attribute(name=active-sessions)"
	output = json.loads(jbosscli(JBOSS_HOME,ARG))
	if output["outcome"] == "success":
		activesessions = int(output["result"])
		threshold(activesessions,WARN,CRIT,"Active-Sessions","")
	else:
		sys.exit(2)

def main(argv,JBOSS_HOME):
	if len(sys.argv) < 2:
		usage()
		sys.exit(2)

	try:
		opts, args = getopt.getopt(argv, "h:m:w:c:d:s:u:")
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h"):
			usage()
			sys.exit()
		if opt in ("-m"):
			_monitor = arg
		if opt in ("-d"):
			_data = arg
		if opt in ("-s"):
			_sub = arg			
		if opt in ("-u"):
			_ut = arg	
		if opt in ("-w"):
			_warning = arg
		if opt in ("-c"):
			_critical = arg

	try:
		_monitor
		_warning
		_critical
	except NameError:
		print "Required parameters not passed, Check usage"
		usage()
		sys.exit(2)
	else:
		if _monitor == "heap-memory-usage":
			heapmemoryusage(JBOSS_HOME,_warning,_critical)
		if _monitor == "jdbc-connections":
			try: _data
			except NameError:
				print "Required parameters not passed, Check usage"
				usage()
				sys.exit(2)
			else:
				sqlconnections(JBOSS_HOME,_data,_warning,_critical)
				
		if _monitor == "active-sessions":
			try: _data
			except NameError:
				print "Required parameters not passed, Check usage"
				usage()
				sys.exit(2)
			else:
				try: _sub
				except NameError:
					subdeployment = ""
				else:
					subdeployment = "subdeployment=" + _sub
				try: _ut
				except NameError:
					subsystem = "/subsystem=web"
				else:
					subsystem = "/subsystem=" + _ut
				activesessions(JBOSS_HOME,_data,subdeployment,subsystem,_warning,_critical)
				

if __name__ == "__main__":
	main(sys.argv[1:],JBOSS_HOME)