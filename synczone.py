#!/usr/env/python
import sys
import os
import paramiko
import argparse
import datetime
import glob

# Logfile
log_file = "/var/log/synczone.log"
log_file_open = open("{0}","a".format(log_file))

# Create argument for silently handling output
parser = argparse.ArgumentParser(description='Runs a sync on zone files on the master to the two NS servers.')
parser.add_argument('-q', '--quite' , action="store_true", default=False ,
                    help='Sends output to log file : {0}'.format(log_file))
parser.add_argument('-d', '--domain', help='Specify a single domain to sync manually, instead of detecting a list from /var/named')
args = parser.parse_args()

# Variables
path = "/var/named/"
domains = []
zonetype = ".zone"
ns_list = ['slave1','slave2']
curtime = str(datetime.datetime.utcnow()).split('.')[0]

# Initilize empty lists and dictionaries
stamps = {}
zonelist = []
mtime = {}

# SSH client settins and variable
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Pass argument string as domain or if none is specified, Find list of zone files and append them to empty list : "domains"
if args.d:
	print "You have choosen to specify a domain to sync directly. Proceeding with {0}".format(args.d)
	domains.append(args.d)
else:
    os.chdir("/var/named")
    for file in glob.glob("*.zone"):
        file = file .split('.zone')[0]
        domains.append(str(file))

# Redirect output to logfiles
if args.q:
    sys.stdout = log_file
    print curtime

# Loop over domains in the domains list, concatenate them into full file paths and add them to list of zones
for d in domains:
    zonefile = path + d + zonetype
    zonelist.append(zonefile)

# Loop over zone files and build a dictionary of domain, local timestamps
for f in zonelist:
    stamp = os.stat("{0}".format(f)).st_mtime
    stamps.update({f : int(stamp)})

# Loop over NS servers
for host in ns_list:
    ssh.connect(hostname=host,username='root')

    #Loop over zonelist and grab the remote timestamp and add it to mtime dict
    for f in zonelist:
        (stdin,stdout,stderr) = ssh.exec_command("stat -c %Y {0}".format(f))
        timestamp = int(stdout.read())
        mtime.update({str(f) : timestamp})
    ssh.close()

    # Loop over dictionary of local domains,timestamps and compare the timestamps to remote ones in the mtime dict

    for key ,value in stamps.items():
        if mtime[key] != stamps[key]:
            # If the timestamp is different, sync local copy
            os.system("rsync -avP {0} root@{1}:/var/named".format(key,host))
            print "Zone {0} on {1} was not up to date with local copy and has been sync'd".format(key,host)
            print "TimeStamp was : {0} , should have been : {1}".format(mtime[key],value)
        else:
            if not args.q:
                print "Zone {0} on {1} is up to date with local copy".format(key,host)
                print "Remote timestamp : {0} , Local timestamp : {1}".format(mtime[key],value)
            else:
                print "Zone {0} on {1} is fine".format(key,host)
