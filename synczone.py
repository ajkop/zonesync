#!/usr/bin/python
import sys
import os
import paramiko
import argparse
import datetime
import glob
import hashlib

# My first class
class Synczones():
    def __init__(self):
        self.path = "/var/named/"
        self.hasher = hashlib.md5
        self.ns_list= ['slave1','slave2']
        self.log_file = "/var/log/synczone.log"
        self.curtime = str(datetime.datetime.utcnow()).split('.')[0]
        self.parser()

    def parser(self):
        parser = argparse.ArgumentParser(description='Runs a sync on zone files on the master to the two NS servers.')
        parser.add_argument('-q', '--quite' , dest='q', action="store_true", default=False ,
                            help='Sends output to log file : {0}'.format(self.log_file))
        parser.add_argument('-d', '--domain', dest='d' ,help='Specify a single domain to sync manually, instead of detecting a list from /var/named')
        self.args = parser.parse_args()

    # Get list of domains in /var/named and add to list for later use
    def getdomlist(self):
        self.domains = []
        self.zonetype = ".zone"
        if self.args.d:
            newdom = self.args.d
            self.domains.append(newdom)
        else:
            os.chdir(self.path)
            for file in glob.glob("*" + self.zonetype):
                file = file .split(self.zonetype)[0]
                self.domains.append(str(file))
        return self.domains

    #Iterate over domain list and translate to full file path
    def getzonelist(self):
        zonetype = ".zone"
        self.zonelist = []
        for d in self.getdomlist():
            self.zonefile = self.path + d + zonetype
            self.zonelist.append(str(self.zonefile))
        return self.zonelist

    # Method to iterate over zonelist and get the hash
    def gethash(self, zone):
        hasher = self.hasher()
        rzonefile = open(zone,'rb')
        buf = rzonefile.read()
        a = hasher.update(buf)
        self.md5hash = (str(hasher.hexdigest()))
        return self.md5hash

    # Get dict of timestamp and hash for later comparison
    def getlocaldict(self):
        self.complist = []
        self.compdict = {}
        for zone in self.getzonelist():
            stamp = os.stat("{0}".format(zone)).st_mtime
            filehash = self.gethash(zone)
            self.complist.append(int(stamp))
            self.complist.append(str(filehash))
            self.compdict.update({ zone : self.complist})
        return self.compdict

    # Connect to specified host and run getcompdict and store as remotedict, return it for calling later.
    def getremotedict(self,host):
        hasher = self.hasher()
        self.rcompdict = {}
        self.rcomplist = []
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host,username='root')
        sftp = ssh.open_sftp()
        for z in self.getzonelist():
            infile = sftp.open(z,'r')
            readfile = infile.read()
            infile.close()
            a = hasher.update(readfile)
            self.rmd5hash = (str(hasher.hexdigest()))
            self.rstamp = sftp.stat("{0}".format(z)).st_mtime
            self.rcomplist.append(self.rstamp)
            self.rcomplist.append(self.rmd5hash)
            self.rcompdict.update({z :self.rcomplist})
        ssh.close()
        return self.rcompdict

    def executecompare(self):
        szl = self.getlocaldict()
        for host in self.ns_list:
            szr = self.getremotedict(host)
            for key, value in szl.items():
                if szr[key] != szl[key]:
                    os.system("rsync -avP {0} root@{1}:/var/named".format(key,host))
                    print "Zone {0} on {1} was not up to date with local copy and has been sync'd".format(key,host)
                    print "Timestamp / Hash  was : {0} , should have been : {1}".format(szr[key],value)
                else:
                    if not self.args.q:
                        print "Zone {0} on {1} is up to date with local copy".format(key,host)
                        print "Remote timestamp / Hash : {0} , Local timestamp / Hash: {1}".format(szr[key],value)
                    else:
                        print "Zone {0} on {1} is fine".format(key,host)

# If script is run from shell, do the followibng.
if __name__ == "__main__":
    app = Synczones()
    if app.args.q:
        log = open('{0}'.format(app.log_file),'a')
        sys.stdout = log
        sys.stderr = log
        print app.curtime

    if app.args.d:
        print "You have choosen to specify a domain to sync directly. Proceeding with {0}".format(app.args.d)

    app.executecompare()
