#!/usr/local/bin/python
##########################################################
#  tapelib 0.9                                           #
#                                                        #
#    DESCRIPTION                                         #
#    and extracts information about reel/scene/take #s,  #
#    along with timecodes and TARball index files within #
#    S-two LTO4 backup tapes for ARRI D21 DPX frames.    #
#                                                        #
#    Copyright (C) 2010 Walter Arrighetti, PhD           #
#    All Rights Reserved.                                #
##########################################################
import subprocess
import tarfile
import fnmatch
import random
import string
import stat
import time
import sys
import os
import re

VERSION = "0.9"

if 'HOST' in os.environ.keys():	HostName = os.environ['HOST']
elif 'HOSTNAME' in os.environ.keys():	HostName = os.environ['HOSTNAME']
elif 'COMPUTERNAME' in os.environ.keys():	HostName = os.environ['COMPUTERNAME']
else:	HostName = "unknown"
if (('OS' in os.environ.keys()) and os.environ['OS'].lower().startswith('win')) or (('OSTYPE' in os.environ.keys()) and os.environ['OSTYPE'].lower().startswith('win')):
	Default_Tape_Library, isWindows, dirsep, isWin32API = "Changer0", True, '\\', False
	Default_Tape_Drives = ["Tape1", "Tape0"]
else:
	Default_Tape_Library, isWindows, dirsep, isWin32API = "lib", False, '/', False
	Default_Tape_Drives = ["/dev/nst2", "/dev/nst3"]

if 'HOST' in os.environ.keys():	HostName = os.environ['HOST']
elif 'HOSTNAME' in os.environ.keys():	HostName = os.environ['HOSTNAME']
elif 'COMPUTERNAME' in os.environ.keys():	HostName = os.environ['COMPUTERNAME']
else:	HostName = "unknown"
if (('OS' in os.environ.keys()) and os.environ['OS'].lower().startswith('win')) or (('OSTYPE' in os.environ.keys()) and os.environ['OSTYPE'].lower().startswith('win')):
	isWindows, dirsep = True, '\\'
	_mt, _mtx, _tapeinfo = "C:\\Program Files (x86)\\mtx\\scsitape", "C:\\Program Files (x86)\\mtx\\mtx", "C:\\Program Files (x86)\\mtx\\tapeinfo"
	try:
		import win32file
		isWin32API = True
	except:	isWin32API = False
else:
	isWindows, dirsep, isWin32API = False, '/', False
	_mt, _mtx, _tapeinfo = "mt", "mtx", "mt"

TAR_PER_TAPE,	TAR_PER_FILE,	TAR_PER_FOLDER	=	0, 1, 2
SINGLE_TAR,		MULTI_TAR,		MIXED_TAR		=	TAR_PER_TAPE,	TAR_PER_FILE,	TAR_PER_FOLDER
TAR_PER_REEL,	TAR_PER_FRAME,	TAR_PER_SCENE	=	TAR_PER_TAPE,	TAR_PER_FILE,	TAR_PER_FOLDER

SI = True

full_perm = stat.S_ISUID|stat.S_ISGID|stat.S_IREAD|stat.S_IWRITE|stat.S_IEXEC|stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH|stat.S_IWUSR|stat.S_IWGRP|stat.S_IWOTH|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH|stat.S_IEXEC|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH

class return_codes:
	INVALID_INPUT_FILENAME = 4
	INPUT_FILE_IO_ERROR = 5
	OUTPUT_FILE_IO_ERROR = 6
	INVALID_TIMECODE = 7
	INVALID_FRAME_INTERVAL = 8
	INVALID_SYNTAX = 9
	EDL_DID_NOT_MATCH = 10
	NO_MATCH = 11
	TARMAP_ERROR = 12
	NO_TAPES_LEFT = 13
	TAPE_LIBRARY_ERROR = 14
	TAPE_SEEK_ERROR = 15
	TARBALL_IO_ERROR = 16
	TAPE_RESTORE_ERROR = 17
	INVALID_PATH = 18
class ANSIchar:
	f0 = '\033[39m';	fK = '\033[30m';	fW = '\033[37m';	fR = '\033[31m';	fG = '\033[32m';	fB = '\033[34m'
	fC = '\033[36m';	fM = '\033[35m';	fY = '\033[33m';	fh0 = '\033[99m';	fhK = '\033[90m';	fhW = '\033[97m'
	fhR = '\033[91m';	fhG = '\033[92m';	fhB = '\033[94m';	fhC = '\033[96m';	fhM = '\033[95m';	fhY = '\033[93m'
	b0 = '\033[49m';	bK = '\033[40m';	bW = '\033[47m';	bR = '\033[41m';	bG = '\033[42m';	bB = '\033[44m'
	bC = '\033[46m';	bM = '\033[45m';	bY = '\033[43m';	bh0 = '\033[109m';	bhK = '\033[100m';	bhW = '\033[107m'
	bhR = '\033[101m';	bhG = '\033[102m';	bhB = '\033[104m';	bhC = '\033[106m';	bhM = '\033[105m';	bhY = '\033[103m'
	Bon = '\033[1m';	Boff = '\033[22m';	B2 = '\033[2m';	Ion = '\033[3m';	Ioff = '\033[23m';	Uon = '\033[4m';	Uoff = '\033[24m';	U2 = '\033[24m'
	Von = '\033[7';		Voff = '\033[27m';	BLINK = '\033[5m';	noBLINK = '\033[25m';	qBLINK = '\033[6m'
	curON = '\033[25h';	curOFF = '\033[25l';	savepos = '\033[s';	restrpos = '\033[u';	reset = '\033[0m'
	def up(self,n=1):	return '\033[' + n + 'A'	# moves the cursor up/down/left/right by n places
	def dw(self,n=1):	return '\033[' + n + 'B'
	def r(self,n=1):		return '\033[' + n + 'C'
	def l(self,n=1):		return '\033[' + n + 'D'
	def nl(self,n=1):	return '\033[' + n + 'E'	# moves @ beginning of n lines down
	def pl(self,n=1):	return '\033[' + n + 'F'	# moves @ beginning of n lines up
	def col(self,m):		return '\033[' + n + 'G'	# moves @ column m [and row n]
	def pos(self,m,n):	return '\033[' + n + ';' + m + 'H'
	def pos2(self,m,n):	return '\033[' + n + ';' + m + 'f'
	clrscr = '\033[2J';	clrlin = '\033[2K'
	def lin0(self,n=1):	return '\033[' + n + 'K'	# erases current line (0=>, 1=<)
	def PgUp(self,n=1):	return '\033[' + n + 'S'	# scrolls page up by n lines
	def PgDwn(self,n=1):	return '\033[' + n + 'T'	# scrolls page down by n lines
	def disable(self):
		self.fK = '';	self.fW = '';	self.fR = '';	self.fG = '';	self.fB = '';	self.fC = '';	self.fM = '';	self.fY = ''
		self.fhK = '';	self.fhW = '';	self.fhR = '';	self.fhG = '';	self.fhB = '';	self.fhC = '';	self.fhM = '';	self.fhY = ''
		self.bK = '';	self.bW = '';	self.bR = '';	self.bG = '';	self.bB = '';	self.bC = '';	self.bM = '';	self.bY = ''
		self.bhK = '';	self.bhW = '';	self.bhR = '';	self.bhG = '';	self.bhB = '';	self.bhC = '';	self.bhM = '';	self.bhY = ''
		self.Bon = '';	self.Boff = '';	self.B2 = '';	self.Bon = '';	self.Boff = '';	self.Bon = '';	self.Boff = ''
		self.Ion = '';	self.Ioff = '';	self.Uon = '';	self.Uoff = '';	self.U2 = '';	self.Von = '';	self.Voff = ''
		self.BLINK = '';	self.noBLINK = '';	self.qBLINK = '';	self.clrscr = '';	self.clrlin = '';	self.reset = ''
c, rc = ANSIchar(), return_codes()
if isWindows:	c.disable()


print c.fhW+c.Bon+"tapelib"+c.Boff+' '+str(VERSION)+c.reset+" - SCSI Tape Library pilot"
print "Copyright (C) 2010 Walter Arrighetti, PhD\n"


if isWindows:
	LTOtapelib = "Changer0"
	LTOdrives = ["Tape0", "Tape1"]
else:
	strs = subprocess.Popen(["cat","/proc/scsi/sg/device_strs"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
	LTOtapelib = []
	LTOdrives = {}
	scsi = []
	tapedevnum = 0
	ti = {}
	for line in strs[0].splitlines():
		st = line.split('\t')
		scsi.append((st[0],st[1]))
	for l in range(len(scsi)):
		#print "line %03d:  %s"%(l,scsi[l][1])
		if scsi[l][1].startswith("Ultrium 4") or scsi[l][1].startswith("ULT3580"):
	#		print "line %03d:  %s"%(l,scsi[l][1])
			LTOdrives["st%d"%tapedevnum] = "sg%d"%l
			LTOdrives["nst%d"%tapedevnum] = "sg%d"%l
			tapedevnum += 1
		elif scsi[l][1].startswith("Scalar"):	LTOtapelib.append("sg%d"%l)
	if not isWindows and len(LTOtapelib)>0 and not os.path.exists("/dev/tapelib"):
		try:	os.link("/dev/%s"%LTOtapelib[0],"/dev/tapelib")
		except:	print ' '+c.fhR+'*'+c.fR+' '+c.Uon+"ERROR"+c.Uoff+'!'+c.reset+": Unable to create device link file "+c.fG+"/dev/tapelib"+c.reset
#	else:
#		print "Tape library device file "+c.fG+"/dev/tapelib"+c.reset+" already exists"

class SCSItapedev:
	"""
	The following integer variables and booleans are defined:
		stat      0 if no errors, otherwise either WRONG_DEVICE=1 or ERROR=2 if errors occurred during last operation.
		BOT, EOT    whether at the Beginning/End-of-Tape
		busy        whether drive is busy
		online      whether drive is online (i.e. a tape is inside)
		onFM        whether tape head is over a filemark
		Min/MaxBlockSize  minimum/maximum supported block sizes
		BlockPos/BlockNo  current absolute block number (reported by 'tapeinfo' and 'mt' respectively
		FileNo            current absolute file number (reported by 'mt')
	The following methods are defined and described in their respective definitions: 
		status(), rewind(), forward(), eject(), seek(), retension(), writeEOF(), erase(), setblk()
	"""
	global LTOdrives
	def __init__(self, device="st0", relog=None):
		global isWindows
		self.OK, self.WRONG_DEVICE, self.ERROR = 0, 1, 2
		if (('OS' in os.environ.keys()) and os.environ['OS'].lower().startswith('win')) or (('OSTYPE' in os.environ.keys()) and os.environ['OSTYPE'].lower().startswith('win')):
			self._Win = True
			self._temp = "C:\\mt_%s.log"%device
			self._RewDrive = self._NoRewDrive = self._SCSIdev = device
			if 'PROGRAMFILES(X86)' in os.environ.keys():	self._mt, self._tapeinfo = os.path.join(os.environ['PROGRAMFILES(X86)'],"GnuWin32","bin","scsitape"), os.path.join(os.environ['PROGRAMFILES(X86)'],"GnuWin32","bin","tapeinfo")
			elif 'PROGRAMFILES' in os.environ.keys():	self._mt, self._tapeinfo = os.path.join(os.environ['PROGRAMFILES'],"GnuWin32","bin","scsitape"), os.path.join(os.environ['PROGRAMFILES'],"GnuWin32","bin","tapeinfo")
			else:	return None
		else:
			self._RewDrive, self._NoRewDrive = ("/dev/%s"%device), ("/dev/n%s"%device)
			self._SCSIdev = "/dev/%s"%LTOdrives[device]
			self._Win, self._temp = False, "/tmp/mt_%s.log"%device[-1]
			self._mt = "mt"	#subprocess.Popen(["which","mt"],stdout=subprocess.PIPE).communicate()[0]
			self._tapeinfo = "tapeinfo"	#subprocess.Popen(["which","tapeinfo"],stdout=subprocess.PIPE).communicate()[0]
		self.BOT = self.EOT = self.EOM = self.EOF = self.busy = self.online = self.onFM = False
		self.MinBlockSize = self.MaxBlockSize = self.BlockSize = self.BlockPos = self.BlockNo = self.FileNo = -1
#			whichstr = open(self._temp+"LOG","w")
#			subprocess.call(["which","mt"],stdout=whichstr)
#			whichstr.close()
#			whichstr = open(self._temp+"LOG","r")
#			whichstrO = whichstr.readlines()
#			whichstr.close()
#			print whichstrO
#			if len(whichstrO)>0:	self._mt = self._tapeinfo = whichstrO
#			else:	self._mt = self._tapeinfo = "mt"
#			del whichstr, whichstrO
		self.info = self.tapeinfo = {}
#		self.flags = []
#		self.drive_type = self.soft_errors = ""
#		self.statword = self.sense_key_error = self.residue_count = self.file_no = self.block_no = self.blocking = self.density = self.density_type = 0
		if not relog:
			if self._Win:
				if "TMP" in os.environ.keys():	self._temp = os.path.join(os.environ["TMP"],"tmp.log")
				else:	self._temp = os.path.join(os.environ["HOMEPATH"],"tmp.log")
			else:	self._temp = "/tmp/tmp.log"	#os.tempnam(os.getcwd(),"mt_")
			self._statmsg = open(self._temp,"a+")
			self.prefix = ""
#		else:
#		if relog:
#			self._statmsg = relog[0]
#			self._prefix = relog[1]
#		else:
#		self._statmsg = open(self._temp,"w+")
#		self._prefix = ""

		self.stat = self.status()
	def __del__(self):
		self._statmsg.close()
#		os.remove(self._temp)
	def status(self, no_update=False):
		"""Updates a tape drive's and its tape's information and puts them in "info" and "tapeinfo" dictionaries, respectively. 
		Updates class booleans/integers BOT, EOT, EOF, busy, offline, onFM, BlockPos/BlockNo, BlockSize, FileNo, MinBlockSize/MaxBlockSize. 
		Returns 0 if no error; 1 otherwise."""
#		print >>self._statmsg, "[%s]  %s%s"%(time.strftime("%Y-%m-%d %H:%M:%S"),self._prefix,"STATUS request.")
#		if self._Win:	callret = subprocess.call([self._tapeinfo,"-f",self._SCSIdev],stdout=self._statmsg,stderr=self._statmsg)
#		else:	callret = subprocess.call([self._tapeinfo,"-f",self._SCSIdev],stdout=self._statmsg,stderr=self._statmsg)
#########################################################################
#	TAPEINFO STATUS PARSING
		self._statstr = subprocess.Popen([self._tapeinfo,"-f",self._SCSIdev],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
		if self._statstr[1] and (self._statstr[1]!="" or len(self._statstr[1].splitlines())>1):	return 1
		self.info = {}
		for line in self._statstr[0].splitlines():
			if line.startswith("Product Type: "):	self.info["type"] = line[14:]
			elif line.startswith("SerialNumber: "):	self.info["S/N"] = string.translate(line[14:],None,"\x00\xFF'")
			elif line.startswith("Attached Changer API: "):
				if line[22:].lower().startswith("yes"):	self.info["changer API"] = True
				else:		self.info["changer API"] = False
			elif line.startswith("Ready: "):
				if line[7:].lower().startswith("yes"):	self.info["busy"] = False
				else:		self.info["busy"] = True
			elif line.startswith("Medium Type: "):
				if line[13:].startswith("0x"):	self.info["medium code"] = int(line[15:],16)
				elif line[13:].isdigit():	self.info["medium code"] = int(line[13:])
			elif line.startswith("Density Code: "):
				if line[14:].startswith("0x"):	self.info["density code"] = int(line[16:],16)
				elif line[14:].isdigit():	self.info["density code"] = int(line[14:])
			elif line.startswith("CompType: "):
				if line[10:].startswith("0x"):	self.info["compression type"] = int(line[12:],16)
				elif line[10:].isdigit():	self.info["compression type"] = int(line[10:])
			elif line.startswith("CompType: "):
				if line[12:].startswith("0x"):	self.info["decompression type"] = int(line[14:],16)
				elif line[12:].isdigit():	self.info["decompression type"] = int(line[12:])
			elif line.startswith("DataCompEnabled: "):
				if line[17:].lower().startswith("no"):	self.info["compression"] = False
				else:		self.info["compression"] = True
			elif line.startswith("DataCompCapable: "):
				if line[17:].lower().startswith("no"):	self.info["compression capable"] = False
				else:		self.info["compression capable"] = True
			elif line.startswith("DataDeCompEnabled: "):
				if line[19:].lower().startswith("no"):	self.info["decompression"] = False
				else:		self.info["decompression"] = True
			elif line.startswith("SCSI ID: ") and line[9:].isdigit():	self.info["SCSI ID"] = int(line[9:])
			elif line.startswith("SCSI LUN: ") and line[10:].isdigit():	self.info["SCSI LUN"] = int(line[10:])
			elif line.startswith("MinBlock: ") and line[10:].isdigit():	self.info["min block size"] = int(line[10:])
			elif line.startswith("MaxBlock: ") and line[10:].isdigit():	self.info["max block size"] = int(line[10:])
			elif line.startswith("BlockSize: ") and line[11:].isdigit():	self.info["block size"] = int(line[11:])
			elif line.startswith("Block Position: ") and line[16:].isdigit():	self.info["current block"] = int(line[16:])
#			elif line.startswith("") and line[:].isdigit():	self.info[""] = int(line[:])
#			elif line.startswith("") and line[:].isdigit():	self.info[""] = int(line[:])
		if "min block size" in self.info.keys():	self.MinBlockSize = self.info["min block size"]
		if "max block size" in self.info.keys():	self.MaxBlockSize = self.info["max block size"]
		if "block size" in self.info.keys():	self.BlockSize = self.info["block size"]
		if "current block" in self.info.keys():	self.BlockPos = self.info["current block"]
#		print "Min/Max Block and Block Pos: %d %d %d"%(self.MinBlockSize,self.MaxBlockSize,self.BlockPos)
#	MT STATUS PARSING
		self.BOT = self.EOT = self.EOM = self.EOF = self.busy = self.online = self.onFM = False
		self.BlockNo = self.FileNo = -1
		self._statstr = subprocess.Popen([self._mt,"-f",self._NoRewDrive,"status"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
#		print self._mt
#		print self._statstr
		if len(self._statstr)!=2 or self._statstr[1] and (self._statstr[1]!="" or len(self._statstr[1].splitlines())>1):	return 1
		self.tapeinfo = {}
		for line in self._statstr[0].splitlines():
			if line.startswith("mt: "):# and line.lower().endswith("no medium found"):
				self.full = False
			else:	self.full = True
			if line.startswith("drive type = "):	self.tapeinfo["drive type"] = line[13:]
			elif line.startswith("drive status = "):
				if line[15:17]=="0x":	self.tapeinfo["drive status"] = int(line[17:],16)
				elif line[15:].isdigit():	self.tapeinfo["drive status"] = int(line[15:])
			elif line.startswith("sense key error = "):	self.tapeinfo["sense key error"] = int(line[18:])
			elif line.startswith("residue count = "):	self.tapeinfo["residue count"] = int(line[16:])
			elif line.startswith("file number = "):	self.tapeinfo["file"] = int(line[14:])
			elif line.startswith("block number = "):	self.tapeinfo["block"] = int(line[15:])
			elif line.startswith("Soft error count since last status="):	self.tapeinfo["soft error count"] = line[35:]
			elif line.startswith("Tape block size ") and line[16:].find(' ')>=0:
				self.tapeinfo["block size"] = int(line[16:16+line[16:].find(' ')])
				dens_code = line[16:].find("Density code 0x")+16
				if dens_code>=16:	self.tapeinfo["density code"] = int(line[dens_code:dens_code+2],16)
		if self._statstr[0].splitlines()[-1].upper().find("BOT")>=0:	self.BOT = True
		if self._statstr[0].splitlines()[-1].upper().find("EOT")>=0 or self._statstr[0].splitlines()[-1].upper().find("EOM")>=0:	self.EOT = True
		if self._statstr[0].splitlines()[-1].upper().find("EOF")>=0:	self.EOF = True
		if self._statstr[0].splitlines()[-1].upper().find("ONLINE")>=0:	self.online = True
		if self._statstr[0].splitlines()[-1].upper().find("ONFM")>=0:	self.onFM = True
		if "file" in self.tapeinfo.keys():	self.FileNo = self.tapeinfo["file"]
		if "block" in self.tapeinfo.keys():	self.BlockNo = self.tapeinfo["block"]
		if "busy" in self.tapeinfo.keys():	self.busy = self.tapeinfo[""]

#########################################################################
#Product Type: Tape Drive
#Vendor ID: 'B\uffffA'
#Product ID: '\uffff\uffff\uffff\uffff'
#Revision: ')'
#ActivePartition: 0
#EarlyWarningSize: 35086
#NumPartitions: 0
#MaxPartitions: 0
#########################################################################
		if "busy" in self.info.keys():	self.busy = self.info["busy"]
		if "min block size" in self.info.keys():	self.MinBlockSize = self.info["min block size"]
		if "max block size" in self.info.keys():	self.MaxBlockSize = self.info["max block size"]
		if "block size" in self.info.keys():	self.BlockSize = self.info["block size"]
		if "current block" in self.info.keys():	self.BlockPos = self.info["current block"]
		if "file" in self.tapeinfo.keys():	self.FileNo = self.tapeinfo["file"]
		if "block" in self.tapeinfo.keys():	self.BlockNo = self.tapeinfo["block"]
		return 0
	def eject(self):
		"""Ejects the tape."""
		if self._Win:	eject_str = "eject"
		else:	eject_str = "offline"
		self.stat = subprocess.Popen([self._mt,"-f",self._RewDrive,eject_str],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def rewind(self, count=-1, file=False, filemark=False):
		"""Rewinds the tape. Completely rewinds it if optionless; otherwise acts by 'count' records, 
		or 'count' filemarks (if 'filemark' is True). WARNING!: In Windows, always rewinds by *Tapemarks*."""
		if count<0:	self.stat = subprocess.call([self._mt,"-f",self._RewDrive,"rewind"],stdout=self._statmsg,stderr=self._statmsg)
		else:
			if self._Win or (file and not filemark):	rew_str = "bsf"
			elif filemark:	rew_str = "bsfm"
			else:	rew_str = "bsr"
			self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,rew_str,str(count)],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def forward(self, count=-1, file=False, filemark=False):
		"""Forwards the tape (completely if optionless) by 'count' records, 
		or 'count' filemarks (if 'filemark' is True). WARNING!: In Windows, always acts by *Tapemarks*."""
		if count<0:
			if self._Win:	ffw_str = "eod"
			else:	ffw_str = "eom"
			self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,ffw_str],stdout=self._statmsg,stderr=self._statmsg)
		else:
			if self._Win or (file and not filemark):	ffw_str = "fsf"
			elif filemark:	ffw_str = "fsfm"
			else:	ffw_str = "fsr"
			self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,ffw_str,str(count)],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def seek(self, count, file=False, filemark=False):
		"""Seeks a tape for a specific block number 'count' (or file/filemark if respective parameter is True). 
		WARNING!: In Windows, always seeks by absolute logical positions (*Tapemarks*)."""
		if self._Win:	seek_str = "seek"
		elif file and not filemark:	seek_str = "asf"
		elif filemark:	seek_str = "asm"
		else:	seek_str = "seek"
		self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,seek_str,str(count)],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def retension(self):
		"""Retensions a tape, i.e. fast-forwards it to the end then completely rewinds it."""
		if self._Win:	ret_str = "rewind"
		else:	ret_str = "retension"
		self.stat = subprocess.call([self._mt,"-f",self._RewDrive,ret_str],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def writeEOF(self, count=1):
		"""Writes 'count' EOF filemarks from current tape position (one if 'count' not specified)."""
		if self._Win:	mark_str = "mark"
		else:	mark_str = "eof"
		self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,mark_str,str(count)],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def erase(self):
		"""Completely erases a tape's contents."""
		self.stat = subprocess.Popen([self._mt,"-f",self._RewDrive,"erase"],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat
	def setblk(self, blk=0):
		"""Sets the GNU blocking factor of the drive to 'blk' records/block, i.e. 512*blk bytes/block."""
		if blk<=0:	blocking = 0
		elif self._Win:	blocking = 512*blk
		else:	blocking = blk
		self.stat = subprocess.call([self._mt,"-f",self._NoRewDrive,"setblk",str(blocking)],stdout=self._statmsg,stderr=self._statmsg)
		self.status(True)
		return self.stat


class SCSItapelib:
	"""
	The following variables are defined:
		storages  Number of internal storage slots (numbered starting from 1);  free_storages is the number of free ones
		IEslots   Number of Import/Export (I/E) bay's slots (numbered starting from 1);  free_IEslots is the number of free ones
		drives    Number of drives (numbered strating from 0; class internally stores tape drives' names, defined by 'drvlst' parameter passed upon class instance declaration);  free_drives is the number of free ones
		scsi      List of SCSItapedev classes for each drive
		drive     List of triples for each drive storing whether is full, previous absolute slot and tape label
		stor      List of couples storing whether a storage slot is full and its tape label
		IEslot    List of couples storing whether a I/E bay slot is full and its tape label
	The following methods are defined:
		drive_full(k)   Whether 'k'th drive is full; if True, drive_label(k) returns its tape label
		stor_full(k)    Whether 'k'th storage slot is full; if True, stor_label(k) returns its tape label
		IE_full(k)      Whether 'k'th I/E bay slot is full; if True, IE_label(k) returns its tape label
	Other methods mass_import(), mass_export(), status(), inventory(), move(), load(), unload(), first(), next() and position() are described in their respective definitions.
	"""
	def __init__(self, device="tapelib", drives=["st0"], storages=35, IEslots=6):
		self.CHANGER_ERROR = -1
		self.DRIVE_ERROR = -2
		self.MOVEMENT_ERROR = -3
		self.INVALID_STORAGE_SLOT = -4
		self.INVALID_IEBAY_SLOT = -5
		self.INVALID_DRIVE_NUMBER = -6
		self.CHANGER_NOT_FOUND = -7
		self.DRIVE_NOT_FOUND = -8
		self.NO_TAPE = -9
		self.DRIVE_BUSY = -10
		self.CHANGER_BUSY = -11
		self.SLOT_FULL = -12
		self.SLOT_EMPTY = -13
		self.DRIVE_FULL = -14
		self.NO_EMPTY_SLOTS = -15
		self.NO_EMPTY_DRIVES = -16
		self.NO_MORE_SLOTS = -17
		self.NO_MORE_DRIVES = -18
		self.BARCODE_ERROR = -19
		if (('OS' in os.environ.keys()) and os.environ['OS'].lower().startswith('win')) or (('OSTYPE' in os.environ.keys()) and os.environ['OSTYPE'].lower().startswith('win')):
			self._Win, self._Changer = True, device
			self._temp = "C:\\mtx_%s.log"%device
			if 'PROGRAMFILES(X86)' in os.environ.keys():
				self._mtx = os.path.join(os.environ['PROGRAMFILES(X86)'],"GnuWin32","bin","mtx")
				self._loaderinfo = os.path.join(os.environ['PROGRAMFILES(X86)'],"GnuWin32","bin","loaderinfo")
			elif 'PROGRAMFILES' in os.environ.keys():
				self._mtx = os.path.join(os.environ['PROGRAMFILES'],"GnuWin32","bin","mtx")
				self._loaderinfo = os.path.join(os.environ['PROGRAMFILES'],"GnuWin32","bin","loaderinfo")
			else:	return None
		else:
			self._Changer, self._mtx, self._loaderinfo = ("/dev/%s"%device), "mtx", "loaderinfo"
			self._Win, self._temp = False, "/tmp/mtx_%s.log"%device[-1]
		self._scsi = self.drivestat = self.stat = self._drive_busy = []
		self.drive = []
		self.stor = []
		self.IEslot = []
		self.storages, self.IEslots, self.drives = storages, IEslots, len(drives)
		self.free_storages, self.free_IEslots, self.free_drives = 0, 0, 0
		self._last = time.time()
		
		self._statstr = ["",""]
		self._statstr = subprocess.Popen([self._loaderinfo,"-f",self._Changer],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
#		self.statstr, l = self._statmsg[0].splitlines(), 0
		if self._statstr[1] and (self._statstr[1]!="" or len(self._statstr[1].splitlines())>1):	return None
		self.info = {}
		for line in self._statstr[0].splitlines():
			if line.startswith("Product Type: "):	self.info["type"] = string.translate(line[14:],None,'\x00\xff')
			elif line.startswith("Vendor ID: "):	self.info["vendor ID"] = string.translate(line[14:],None,"\x00\xff'")
			elif line.startswith("Product ID: "):	self.info["product ID"] = string.translate(line[14:],None,"\x00\xff'")
			elif line.startswith("Revision: "):	self.info["firmware"] = string.translate(line[14:],None,"\x00\xff'")
			elif line.startswith("Attached Changer: "):
				if line[18:].lower().startswith("yes"):	self.info["attached changer"] = True
				else:		self.info["attached changer"] = False
			elif line.startswith("Bar Code Reader: "):
				if line[17:].lower().startswith("yes"):	self.info["barcode reader"] = True
				else:		self.info["barcode reader"] = False
			elif line.startswith("EAAP: "):
				if line[6:].lower().startswith("yes"):	self.info["EAAP"] = True
				else:		self.info["EAAP"] = False
			elif line.startswith("Number of Medium Transport Elements: ") and line[37:].isdigit():	self.info["transports #"] = int(line[37:])
			elif line.startswith("Number of Storage Elements: ") and line[28:].isdigit():	self.info["storages #"] = int(line[28:])
			elif line.startswith("Number of Import/Export Elements: ") and line[34:].isdigit():	self.info["I/E #"] = int(line[34:])
			elif line.startswith("Number of Data Transfer Elements: ") and line[34:].isdigit():	self.info["drives #"] = int(line[34:])
			elif line.startswith("Transport Geometry Descriptor Page: "):
				if line[36:].lower().startswith("yes"):	self.info["transport geometry descriptor"] = True
				else:	self.info["transport geometry descriptor"] = False
			elif line.startswith("Invertable: "):
				if line[12:].lower().startswith("yes"):	self.info["invertable"] = True
				else:	self.info["invertable"] = False
			elif line.startswith("Device Configuration Page: "):
				if line[27:].lower().startswith("yes"):	self.info["device configuration"] = True
				else:	self.info["device configuration"] = False
		if "storages #" in self.info.keys():	self.storages = self.info["storages #"]
		if "I/E #" in self.info.keys():	self.IEslots = self.info["I/E #"]
		if "drives #" in self.info.keys():
			self.drives = self.info["drives #"]
			if self.drives != len(drives):	return None
#		self._temp = os.tempnam(os.getcwd(),"mtx_")
#		os.mkfifo(self._temp)
#		self._statmsg = open(self._temp,"w+")
		for i in range(self.drives):
			self._scsi.append(SCSItapedev(drives[i])) #drive[i], relog=(self._statmsg,"Drive #%d:\t"%i)
			self.drivestat.append(0)
			self.drive.append((False,-1,None))
			self._drive_busy.append(False)
#			if type(self._scsi[i])==type(1) and self._scsi[i]!=0:	self.drivestat[i] = self.DRIVE_ERROR
#			else:	self._scsi[i].status()
		for j in range(self.storages):	self.stor.append((False,None))
		for k in range(self.IEslots):		self.IEslot.append((False,None))
		self.statmsg = ""
#		self.status()
#	def __del__(self):
#		self._statmsg.close()
##		os.remove(self._temp)
#		for i in range(self.drives):	self._scsi[i].__del__()
#		del self._scsi, self.drive, self.drivestat, self.status, self.stor, self.IEslot, self._time
	def status(self, drv=-1):
		"""If no drive number is passed, updates a tape library's information; 
		otherwise, updates tape drive information for 'drv'."""
#		if self._statmsg:	self._statmsg.close()
		self._statmsg = open(self._temp,"w+")
		if drv >= 0:
			if drv>=len(scsi.drives):	return self.INVALID_DRIVE_NUMBER
			self._scsi[drv].status()
		else:
			self._statmsg = subprocess.Popen([self._mtx,"-f",self._Changer,"status"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
			self.statstr, l = self._statmsg[0].splitlines(), 0
			if not self.statstr[0].startswith("  Storage Changer %s"%self._Changer):	return self.CHANGER_NOT_FOUND
			self.free_storages, self.free_IEslots, self.free_drives = self.storages, self.IEslots, self.drives
			for line in self.statstr:
#				if line.startswith("  Storage Changer"):
#					linere = re.match(r"  Storage Changer \S+[:](\d{1,2}) Drives, (\d{1,3}) Slots(?: [(] (\d{1,2}) Import/Export [)])?",line)
#					if linere:	print linere.groups()
#					else:	print "\n\nNO LINE\n\n"
				if line.startswith("Data Transfer Element "):
					space = line[22:].find(':')+22
					if line[22:space].isdigit():
						i = int(line[22:space])
						if line[space+1:space+6].lower()=="empty":
							self.drive[i] = (False, -1, None)
#							print "Drive #%d is %s"%(i,repr(self.drive[i]))
						else:
							self.free_drives -= 1
							loaded = line[space+6:].find('(Storage Element ')+space+23
							if loaded>=space+23 and line[loaded:loaded+2].isdigit():	prev_elem = int(line[loaded:loaded+2])
							else:	prev_elem = -1
#							print "PREV ELEM: %d"%prev_elem
							tag = line[space+6:].find("VolumeTag = ")+space+18
							if tag>=space+18:	cur_label = string.translate(line[tag:],None,"\x00\xFF\x20'")
							else:	cur_label = None
							self.drive[i] = (True, prev_elem, cur_label)
				elif line.startswith("      Storage Element ") and line.find("IMPORT/EXPORT")<0:
					space = line[22:].find(':')+22
					if line[22:space].isdigit():
						j = int(line[22:space])-1
						if line[space+1:space+6].lower()=="empty":
							self.stor[j] = (False, "")
#							print "Storage #%d is %s"%(j,repr(self.stor[j]))
						else:
							self.free_storages -= 1
							tag = line[space+1:].find("VolumeTag=")+space+11
							if tag>=space+11:	cur_label = string.translate(line[tag:],None,"\x00\xFF\x20'")
							else:	cur_label = None
							self.stor[j] = (True, cur_label)
#							print "Storage #%d is %s"%(j,repr(self.stor[j]))
#						else:
#							self.stor[j] = (False, None)
				elif line.startswith("      Storage Element "):
					space = line[22:].find(':')+22
#					imp_left = line[22:].find('IMP')+space
#					print "space=%d  imp_left=%d  -  %s"%(space,imp_left,line[22:24])
					if line[22:24].isdigit():	
						k = int(line[22:24])-self.storages-1
						ielen = line.find("IMPORT/EXPORT:")+14
						if line[ielen:ielen+5].lower()=="empty":
							self.IEslot[k] = (False, None)
#							print "I/E slot #%d is %s"%(k,repr(self.IEslot[k]))
						else:
							self.free_IEslots -= 1
							tag = line[space+1:].find("VolumeTag=")+space+11
							if tag>=space+11:	cur_label = string.translate(line[tag:],None,"\x00\xFF\x20'")
							else:	cur_label = None
							self.IEslot[k] = (True, cur_label)
#							print "I/E slot #%d is %s"%(k,repr(self.IEslot[k]))
			self._last = time.time()
			if not (0<=self.free_drives<=self.drives and 0<=self.free_storages<=self.storages and 0<=self.free_IEslots<=self.IEslots):	return self.CHANGER_ERROR
	def shelf(self, blink=None, status=None, check=True, stdout=sys.stdout):
		"""Outputs an ASCII representation of the tape library's slots  (stdout argument is the default output file).
		    check     Boolean which, if True (default), re-checks the library's inventory (may take seconds).
			blink     Dictionary with ["drives","storage","IE"] as keys, whose values are lists of slots' numbers to be highlighted (hi-intensity in their respective colour)
			status    More complex dictionary whose values are sub-dictionaries like blink's with slot numbers' lists as subvalues;
			          status' keys are strings which allow to give a slot's 'meaning' the proper colouring:
				"in"      standard slots: White text; background is Blue for drives, Cyan for storages, Magenta for I/E bay
				"OK"      slots which were successfully processed (black in Light Green background)
				"error"   slots which reported severe error(s) (black in Light Red background)
				"warning" slots which reported some warning or minor error (black in Light Yellow background)
				"exclude" excluded slots: (dark gray text, normal-intensity background)
				"blink"   highlighted slots: White text, Hi-intensity background (like "in"'s colours)
		"""
		if (('OS' in os.environ.keys()) and os.environ['OS'].lower().startswith('win')) or (('OSTYPE' in os.environ.keys()) and os.environ['OSTYPE'].lower().startswith('win')):
			empty=busy=OK=ERR=WRN=ERRold=NOdrv=NOstor=NOslot=ONdrv=ONstor=ONslot=Hdrv=Hstor=Hslot=Bdrv=Bstor=Bslot=ONno=nolbl=OFF=''
#	f0 = '\033[39m';	fK = '\033[30m';	fW = '\033[37m';	fR = '\033[31m';	fG = '\033[32m';	fB = '\033[34m'
#	fC = '\033[36m';	fM = '\033[35m';	fY = '\033[33m';	fh0 = '\033[99m';	fhK = '\033[90m';	fhW = '\033[97m'
#	fhR = '\033[91m';	fhG = '\033[92m';	fhB = '\033[94m';	fhC = '\033[96m';	fhM = '\033[95m';	fhY = '\033[93m'
#	b0 = '\033[49m';	bK = '\033[40m';	bW = '\033[47m';	bR = '\033[41m';	bG = '\033[42m';	bB = '\033[44m'
#	bC = '\033[46m';	bM = '\033[45m';	bY = '\033[43m';	bh0 = '\033[109m';	bhK = '\033[100m';	bhW = '\033[107m'
#	bhR = '\033[101m';	bhG = '\033[102m';	bhB = '\033[104m';	bhC = '\033[106m';	bhM = '\033[105m';	bhY = '\033[103m'
		else:
			empty, busy = '\033[100m\033[30m', '\033[93m\033[104m\033[5m',	#	DGrey, LBlue (yellow+blink)
			OK, ERR, WRN, ERRold = '\033[102m\033[30m', '\033[101m\033[30m', '\033[103m\033[30m', '\033[41m\033[30m',	# LGreen, LRed, Red
			NOdrv, NOstor, NOslot = '\033[44m\033[90m', '\033[46m\033[90m', '\033[45m\033[90m',
			ONdrv, ONstor, ONslot = '\033[44m\033[97m', '\033[46m\033[97m', '\033[45m\033[97m'	# Blue, Cyan, Magenta
			Hdrv, Hstor, Hslot = '\033[104m\033[30m', '\033[106m\033[30m', '\033[105m\033[30m',	# LBlue, LCyan, LMagenta
			Bdrv, Bstor, Bslot = '\033[104m\033[97m', '\033[106m\033[97m', '\033[105m\033[97m',	# LBlue, LCyan, LMagenta
			ONno, nolbl, OFF = '', '\033[3m', '\033[0m'
		line, s = [], ""
		empty_slot = empty + '|________|' + OFF
		no_label = nolbl + " no label "
		colorD = {
			"in":{"drives":ONdrv, "storage":ONstor, "IE":ONslot }, 
			"OK":{"drives":OK, "storage":OK, "IE":OK }, 
			"error":{"drives":ERR, "storage":ERR, "IE":ERR }, 
			"warning":{"drives":WRN, "storage":WRN, "IE":WRN }, 
			"exclude":{"drives":NOdrv, "storage":NOstor, "IE":NOslot }, 
			"blink":{"drives":Hdrv, "storage":Hstor, "IE":Hslot }  }
		Cdrv, Cstor, Cslot = ONdrv, ONstor, ONslot
		if check:	self.status()
		for i in range(self.drives):
			s += "Drive #%d: "%i
			if blink and type(blink)==type({}) and "drives" in blink.keys() and blink["drives"]!=None and i in blink["drives"]:	Cdrv = Bdrv
			elif status and type(status)==type({}):
				for S in status.keys():
					if S in ["in","OK","error","warning","exclude","in","blink"] and "drives" in status[S].keys() and status[S]["drives"] and i in status[S]["drives"]:
						Cdrv = colorD[S]["drives"]
						break
			else:	Cdrv = ONdrv
			if not self.drive_full(i):	s += empty_slot
			elif not self.drive_label(i):	s += Cdrv + no_label + OFF
			else:	s += Cdrv + string.center(self.drive_label(i),10) + OFF
			if i!=self.drives-1:	s += ' '*((80-18*(self.drives-1)-4)//self.drives)
		line.append(s);	s=""
		line.append("");	line.append("____________________________Internal Storage____________________________")
		sll = (self.storages*15)/75
		for l in range(sll):
			for j in range(5*l+1, min(self.storages,5*(l+1))+1):
				s += "%02d:"%j
				if blink and type(blink)==type({}) and "storage" in blink.keys() and blink["storage"]!=None and j in blink["storage"]:	Cstor = Bstor
				elif status and type(status)==type({}):
					for S in status.keys():
						if S in ["in","OK","error","warning","exclude","in","blink"] and "storage" in status[S].keys() and status[S]["storage"]!=None and j in status[S]["storage"]:
							Cstor = colorD[S]["storage"]
							break
				else:	Cstor = ONstor
				if not self.stor_full(j):	s += empty_slot
				elif not self.stor_label(j):	s += Cstor + no_label + OFF
				else:	s += Cstor + string.center(self.stor_label(j),10) + OFF
				if j!=self.storages:	s += "  "	#' '*((80-13*(sll/self.storages)-4)//self.storages)
			if l!=sll-1:	line.append(s);	s="\x00"
		line.append(s);	s="\x00"
		line.append("");	line.append("   ________________________Import/Export Tray________________________   ")
		sll = (self.IEslots*25)/75
		for l in range(sll):
			for k in range(3*l+1, min(self.IEslots,3*(l+1))+1):
				s += "  %02d:"%k
				if blink and type(blink)==type({}) and "IE" in blink.keys() and blink["IE"]!=None and k in blink["IE"]:	Cslot = Bslot
				elif status and type(status)==type({}):
					for S in status.keys():
						if S in ["in","OK","error","warning","exclude","in","blink"] and "IE" in status[S].keys() and status[S]["IE"]!=None and k in status[S]["IE"]:
							Cslot = colorD[S]["IE"]
							break
				else:	Cslot = ONslot
				if not self.IE_full(k):	s += empty_slot
				elif not self.IE_label(k):	s += Cslot + no_label + OFF
				else:	s += Cslot + string.center(self.IE_label(k),10) + OFF
				if k!=self.IEslots:	s += "  "	#' '*((80-13*(sll/self.IEslots)-4)//self.IEslots)
			if l!=sll-1:	line.append(s);	s="\x00"
		line.append(s);	s="\x00";	line.append("")
		for l in range(len(line)):	line[l] = string.center(line[l],80)
#		if self._Win:	print >>stdout,''.join(line)
#		else:	print >>stdout,"\n\r".join(line)
		print >>stdout,"\n\r".join(line)
	#	HIGH-LEVEL FUNCTIONS		
	def drive_busy(self,i):	return self._drive_busy[i]
	def drive_full(self,i):	return self.drive[i][0]
	def drive_label(self,i):	return self.drive[i][2]
	def drive_previous(self,i):	return self.drive[i][1]
	def stor_full(self,j):	return self.stor[j-1][0]
	def stor_label(self,j):	return self.stor[j-1][1]
	def IE_full(self,k):	return self.IEslot[k-1][0]
	def IE_label(self,k):	return self.IEslot[k-1][1]
	def mass_import(self, IEslots=None, shelf=False, stdout=sys.stdout, shelfout=sys.stdout):
		"""Sequentially imports some or all of the tapes in the I/E bay into available Storage Slots (preferring sequential slots, if ever; random otherwise). 
		If a list of 1-based I/E bay slots is given, only imports from that slots. 
		If a dictionary is given, import tapes whose source I/E bay and target storage slots are its keys:values, respectively. 
		mass_import() always returns a dictionary whose keys are the actually-moved source I/E bay slots and values are the corresponding target Storage Slots."""
		print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"MASS IMPORT request")
		movOK = []
		if type(IEslots) == type(dict):		# Import movements taken from a source:target dictionary
			if len(IEslots)>self.IEslots or len(IEslots)>self.storages:	return self.NO_MORE_SLOTS
			if not set(IEslots.keys()).issubset(set(range(1,self.IEslots+1))):	return self.INVALID_IEBAY_SLOT
			if not set(IEslots.values()).issubset(set(range(1,self.storages+1))):	return self.INVALID_STORAGE_SLOT
			if len(IEslots.keys())!=len(set(IEslots.keys())):
				print >>stdout, "\tERROR: I/E bay slot(s) multiply specified as movement sources."
				return self.INVALID_IEBAY_SLOT
			if len(IEslots.values())!=len(set(IEslots.values())):
				print >>stdout, "\tERROR: Storage Slot(s) multiply specified as movement targets."
				return self.INVALID_STORAGE_SLOT
			self.status()
			for k in sorted(IEslots.keys()):			# Checks for the presence of a tape in each Import bay slots
				if not self.IE_full(k):
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"I/E bay slot #%d is EMPTY!"%k)
					return self.SLOT_EMPTY
			for k in sorted(IEslots.values()):			# Checks for the availability of each storage slots
				if self.stor_full(k):
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"Storage slot #%d is FULL!"%k)
					return self.SLOT_FULL
			slots = sorted(IEslots.keys())
			movOK = [ [IEslots[k],False] for k in slots ]
		elif IEslots==None:
			if self.free_storages < 1:
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"No empty Storage Slots available to import to!"%k)
					return self.NO_EMPTY_SLOTS
			slots = []
			counter, maxcount = 0, self.free_storages
			for k in range(1,self.IEslots+1):
				if self.IE_full(k):
					slots.append(k)
					counter += 1
				if counter >= maxcount:	break
			if counter == 0:
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"No more full I/E slots to import.")
					return self.NO_MORE_SLOTS
			counter = len(slots)
			for j in range(1,self.storages+1):
				if counter<=0:	break
				if not self.stor_full(j):
					movOK.append([j,False])
					counter -= 1
		else:
			if not IEslots:	slots = range(1,self.IEslots+1)
			else:	slots = sorted(IEslots)
			movOK = [ [0,False] for k in slots ]
			self.status()
			if self.free_storages < len(slots):	return self.NO_EMPTY_SLOTS
			k = 1
			while k <= self.storages-len(slots)+1:
				one_gap = True
				for i in range(len(slots)):
					if self.stor_full(k+i):
						k += i
						one_gap = False
						break
					else:	start_slot = k
				if one_gap:	break
				k += 1
			if one_gap:		# Ingest the tapes into one consecutive Storage Slots' gap, starting from one_gap
				for k in range(len(slots)):	movOK[k][0] = start_slot+k
			else:			# Randomly ingests the tapes into the first free Storage Slots
				start_slot = 0
				for k in range(self.storages):
					if i == len(slots):	break
					elif not self.stor_full(k+1):
						movOK[i][0] = k+1
						start_slot += 1
		retry = OK = 0
		if len(movOK)<=0:	return dict(zip(  ))
		print >>stdout, "\t",
		for k in range(len(slots)):	print >>stdout, "%d >> %d"%(slots[k],movOK[k][0]),
		if shelf:	lib.shelf(blink={"IE":slots}, check=False, stdout=shelfout)
		while OK<len(movOK) and retry<=len(movOK):	# Gives a # of movement tries equal to the # of tapes to move +1
#			OK = 0
			for tape in range(len(movOK)):
				if movOK[tape][1]:	break	# This tape has been successfully moved before
				else:
					self.move(slots[tape], movOK[tape][0], srcstor=False, targstor=True)
					if self.stor_full(movOK[tape][0]) and not self.IE_full(slots[tape]):	# Checks whether single movement was successful
						movOK[tape][1], OK = True, OK+1
			retry += 1
		if OK==len(movOK):	print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"Mass-import operation completed.")
		else:	print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"ERROR: %d out of %d tapes moved!"%(OK,len(movOK)))
		return dict(zip(  [slots[k] for k in range(len(slots)) if movOK[k][1]],  [movOK[k][0]  for k in range(len(slots)) if movOK[k][1]]  ))
	def mass_export(self, Sslots=None, shelf=False, stdout=sys.stdout, shelfout=sys.stdout):
		"""Sequentially exports some tapes from a list of Storage Slots into available I/E bay slots (preferring sequential destination slots, if ever; random otherwise). 
		If a dictionary is given, import tapes whose *target* I/E bay and *source* Storage Slots are its keys:values, respectively; 
		this is a "reversed" dictionary in order to provide 'inverse' operation to the ones returned by mass_import(). 
		If no Storage Slots are specified, exports as many as possible, up to fill up the I/E bay.
		mass_export() always returns a dictionary whose keys are the actually-moved target I/E bay slots and values are the corresponding source Storage Slots."""
		print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"MASS EXPORT request:")
		movOK = []
		if type(Sslots) == type(dict):		# Import movements taken from a source:target dictionary
			if len(Sslots)>self.IEslots or len(Sslots)>self.storages:	return self.NO_MORE_SLOTS
			if not set(Sslots.keys()).issubset(set(range(1,self.IEslots+1))):	return self.INVALID_IEBAY_SLOT
			if not set(Sslots.values()).issubset(set(range(1,self.storages+1))):	return self.INVALID_STORAGE_SLOT
			if len(Sslots.keys())!=len(set(Sslots.keys())):
				print >>stdout, "\tERROR: I/E bay slot(s) multiply specified as movement targets."
				return self.INVALID_IEBAY_SLOT
			if len(Sslots.values())!=len(set(Sslots.values())):
				print >>stdout, "\tERROR: Storage Slot(s) multiply specified as movement sources."
				return self.INVALID_STORAGE_SLOT
			self.status()
			for k in sorted(Sslots.values()):			# Checks for the presence of a tape in each Storage Slots
				if not self.stor_full(k):
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"Storage slot #%d is EMPTY!"%k)
					return self.SLOT_EMPTY
			for k in sorted(Sslots.keys()):			# Checks for the availability of each storage slots
				if self.IE_full(k):
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"I/E bay slot #%d is FULL!"%k)
					return self.SLOT_FULL
			slots = sorted(Sslots.values())
			movOK = [ None for l in Sslots.keys() ]
			for s in len(slots):
				for key in Sslots.keys():
					if slots[s]==Sslots[key]:
						movOK[s] = [key,False]
						break
		elif Sslots==None:
			if self.free_IEslots < 1:
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"No empty I/E bay slots available to export to!"%k)
					return self.NO_EMPTY_SLOTS
			slots = []
			counter, maxcount = 0, self.free_IEslots
			for k in range(1,self.storages+1):
				if self.stor_full(k):
					slots.append(k)
					counter += 1
				if counter >= maxcount:	break
			if counter == 0:
					print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"No more full Storage slots to export."%k)
					return self.NO_MORE_SLOTS
			counter = len(slots)
			for j in range(1,self.IEslots+1):
				if counter<=0:	break
				if not self.IE_full(j):
					movOK.append([j,False])
					counter -= 1
		else:
			slots = sorted(Sslots)
			movOK = [ [0,False] for k in slots ]
			self.status()
			if self.free_IEslots < len(slots):	return self.NO_EMPTY_SLOTS
			k = 1
			while k <= self.IEslots-len(slots)+1:
				one_gap = True
				for i in range(len(slots)):
					if self.IE_full(k+i):
						k += i
						one_gap = False
						break
					else:	start_slot = k
				if one_gap:	break
				k += 1
			if one_gap:		# Ingest the tapes into one consecutive free I/E bay slots' gap, starting from one_gap
				for k in range(len(slots)):	movOK[k][0] = start_slot+k
			else:			# Randomly ingests the tapes into the first free I/E bay slots
				start_slot = 0
				for k in range(self.IEslots):
					if i == len(slots):	break
					elif not self.IE_full(k+1):
						movOK[i][0] = k+1
						start_slot += 1
		retry = OK = 0
		print >>stdout, "\t",
		for k in range(len(slots)):	print >>stdout, "%d << %d"%(slots[k],movOK[k][0]),
		print >>stdout, ""
		if shelf:	lib.shelf(blink={"storage":slots}, stdout=shelfout)
		while OK<len(movOK) and retry<=len(movOK):	# Gives a # of movement tries equal to the # of tapes to move +1
#			OK = 0
			for tape in range(len(movOK)):
				if movOK[tape][1]:	break	# This tape has been successfully moved before
				else:
					self.move(slots[tape], movOK[tape][0], srcstor=True, targstor=False)
					if self.IE_full(movOK[tape][0]) and not self.stor_full(slots[tape]):	# Checks whether single movement was successful
						movOK[tape][1], OK = True, OK+1
			retry += 1
		if OK==len(movOK):	print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"Mass-export operation completed.")
		else:	print >>stdout, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"ERROR: %d out of %d tapes moved!"%(OK,len(movOK)))
		return dict(zip(  [movOK[k][0] for k in range(len(slots)) if movOK[k][1]],  [slots[k]  for k in range(len(slots)) if movOK[k][1]]  ))
	#	MID-LEVEL FUNCTIONS  (mtx aliases)
	def inventory(self):
		"""Updates the library's inventory, i.e. the list of tapes (as well as their labels) in both 
		the library's storage slots, I/E bay slots and drives themselves."""
		print >>self._statmsg, "[%s]  %s"%(time.strftime("%Y-%m-%d %H:%M:%S"),"INVENTORY request.")
		callret = subprocess.call([self.mtx,"-f",self.Changer,"inventory"],stdout=self._statmsg,stderr=self._statmsg)
		self.status()
	def move(self, source, target, srcstor=True, targstor=True):
		"""Moves a tape from 'src'th slot to 'target'th slot; 'srcstor' and 'targstor' are booleans specifying whether 
		such slots are the simple storage ones (True) or the slots in the I/E bay (False)."""
		if time.time() > self._last+5:	self.status()
		if srcstor:
			if not 1<=source<=self.storages:	return self.INVALID_STORAGE_SLOT
#			if not self.stor_full(source):	return self.SLOT_EMPTY
		elif not srcstor:
			if not 1<=source<=self.IEslots:	return self.INVALID_IEBAY_SLOT
#			elif not self.IE_full(source):	return self.SLOT_EMPTY
		if targstor:
			if not 1<=target<=self.storages:	return self.INVALID_STORAGE_SLOT
#			if self.stor_full(target):	return self.SLOT_FULL
		elif not targstor:
			if not 1<=target<=self.IEslots:	return self.INVALID_IEBAY_SLOT
#			if self.IE_full(target):	return self.SLOT_FULL
		s, t = source, target
		if not srcstor:	s += self.storages
		if not targstor:	t += self.storages
		if s != t:
			self._statmsg = subprocess.call([self._mtx,"-f",self._Changer,"eepos","0","transfer",str(s),str(t)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#			self.statstr = self._statmsg.readlines()
		else:	self.statstr = ""
#		self.status()
	def load(self, source, drive=-1, storage=True):
		"""Loads tape from 'src'th slot into 'drv'th drive (or into the first free drive if none specified). 
		'src' is stored in the drive's information in order to recall its tape's previous slot position."""
		if time.time() > self._last+5:	self.status()
		if storage:
			if not 1<=source<=self.storages:	return self.INVALID_STORAGE_SLOT
			if not self.stor_full(source):	return self.SLOT_EMPTY
		elif not storage:
			if not 1<=source<=self.IEslots:	return self.INVALID_IEBAY_SLOT
#			if not self.IE_full(source):	return self.SLOT_EMPTY
		if drive >= len(self.drive):	return self.INVALID_DRIVE_NUMBER
		elif drive < 0:
			drv = -1
			for k in range(self.drives):
				if not self.drive_full(k):
					drv = k
					break
			if drv<0:	return self.NO_MORE_DRIVES
		else:	drv = drive
		if storage:	src = source
		else:	src = source + self.storages
		self._drive_busy[drv] = True
		self._statmsg = subprocess.call([self._mtx,"-f",self._Changer,"load",str(src),str(drv)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		self._drive_busy[drv] = False
#		self.statstr = self._statmsg.readlines()
		self.status()
		self.drive[drv] = (self.drive[drv][0], src-1, self.drive[drv][2])
	def unload(self, drive, target=-1, storage=True):
		"""Unloads tape from 'drv'th drive into either: 'trg'th slot (if specified), into its previous slot, 
		or into the first free one (from internal storage or I/E bay according to its previous position)."""
		if time.time() > self._last+5:	self.status()
		if not 0<=drive<self.drives:	return self.INVALID_DRIVE_NUMBER
		trg = -1
		if target<=0:
			if self.drive_previous(drive) >= 0:
				if 0<=self.drive_previous(drive)<self.storages and not self.stor_full(self.drive_previous(drive)+1):
					trg = self.drive_previous(drive)
				elif self.storages<=self.drive_previous(drive)<self.storages+self.IEslots and not self.IE_full(self.drive_previous(drive)-self.storages+1):
					trg = self.drive_previous(drive)
			elif trg<0 or storage:
				for k in range(self.storages):
					if not self.stor_full(k+1):
						trg = k
						break
				if trg<0:
					for k in range(self.IEslots):
						if not self.IE_full(k+1):
							trg = self.storages+k
							break
				if trg<0:	return self.SLOT_FULL
			elif not storage:
				for k in range(self.IEslots):
					if not self.IE_full(k+1):
						trg = self.storages+k
						break
				if trg<0:
					for k in range(self.storages):
						if not self.stor_full(k+1):
							trg = k
							break
				if trg<0:	return self.SLOT_FULL
			else:	return self.SLOT_FULL
		elif storage:
			if 0<target<=self.storages:	trg = target
			else:	return self.INVALID_STORAGE_SLOT
		elif not storage:
			if 0<target<=self.IEslots:	trg = self.storages + target
			else:	return self.INVALID_IEBAY_SLOT
#		else:	return self.
		self._drive_busy[drive] = True
		self._statmsg = subprocess.call([self._mtx,"-f",self._Changer,"unload",str(trg),str(drive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		self._drive_busy[drive] = False
#		self.statstr = self._statmsg.readlines()
		self.status()
	def first(self, drive):
		""" Loads the *First* tape into the drive. 
		WARNING!: Previous-slot data are not updated for any drives; do not use it along with move(), load() and unload() !"""
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		callret = subprocess.call([self._mtx,"-f",self._Changer,"first",str(drv)],stdout=self._statmsg,stderr=self._statmsg)
		self.statstr = self._statmsg.readlines()
		self.status()
	def last(self, drive):
		""" Loads the *Last* tape into the drive. 
		WARNING!: Previous-slot data are not updated for any drives; do not use it along with move(), load() and unload() !"""
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		callret = subprocess.call([self._mtx,"-f",self._Changer,"last",str(drv)],stdout=self._statmsg,stderr=self._statmsg)
		self.statstr = self._statmsg.readlines()
		self.status()	
	def next(self, drive):
		""" Loads the *Next* tape into the drive. 
		WARNING!: Previous-slot data are not updated for any drives; do not use it along with move(), load() and unload() !"""
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		callret = subprocess.call([self._mtx,"-f",self._Changer,"next",str(drv)],stdout=self._statmsg,stderr=self._statmsg)
		self.statstr = self._statmsg.readlines()
		self.status()
	def previous(self, drive):
		""" Loads the *Previous* tape into the drive. 
		WARNING!: Previous-slot data are not updated for any drives; do not use it along with move(), load() and unload() !"""
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		callret = subprocess.call([self._mtx,"-f",self._Changer,"previous",str(drv)],stdout=self._statmsg,stderr=self._statmsg)
		self.statstr = self._statmsg.readlines()
		self.status()
	def position(self, slot, storage=True):
		""" Positions the robot arm in front of 'slot' (either internal strages or the I/E bay according to 'storage')."""
		if storage:
			if 1<=slot<=self.storages:	s = slot
			else:	return self.INVALID_STORAGE_SLOT
		else:
			if 1<=slot<=self.IEslots:	s = slot+self.storages
			else:	return self.INVALID_IEBAY_SLOT
		callret = subprocess.call([self._mtx,"-f",self._Changer,"position",str(s-1)],stdout=self._statmsg,stderr=self._statmsg)
		self.statstr = self._statmsg.readlines()
		self.status()
	#	MID-LEVEL FUNCTIONS  (mt aliases)
	def rewind(self, drv, count=-1, file=False, filemark=False):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].rewind(count=count,file=file,filemark=filemark)
		self._drive_busy[drv] = False
	def forward(self, drv, count=-1, file=False, filemark=False):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].forward(count=count,file=file,filemark=filemark)
		self._drive_busy[drv] = False
	def seek(self, drv, count, file=False, filemark=False):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].forward(count=count,file=file,filemark=filemark)
		self._drive_busy[drv] = False
	def retension(self, drv):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].retension()
		self._drive_busy[drv] = False
	def writeEOF(self, drv, count=1):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].writeEOF(count=count)
		self._drive_busy[drv] = False
	def erase(self, drv):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._drive_busy[drv] = True
		self._scsi[drv].erase()
		self._drive_busy[drv] = False
	def setblk(self, drv, blk=0):
		if not 0<=drv<self.drives:	return self.INVALID_DRIVE_NUMBER
		self._scsi[drv].setblk(blk=blk)
###################################################################
###################################################################
###################################################################
###################################################################



OKstr, ERRstr, EMPTYstr, WARNstr = "      ["+c.fhG+"  OK  "+c.reset+"]","      ["+c.fhR+"ERROR!"+c.reset+"]", "      ["+c.fhR+"EMPTY!"+c.reset+"]","      ["+c.fhY+"  OK  "+c.reset+"]"
OKmsg = ' '+c.fhG+'*'+c.reset+' '
WRNmsg = ' '+c.fhY+'*'+c.reset+' '+c.fY+c.Uon+"WARNING"+c.Uoff+c.Ion+'!'+c.reset+": "
ERRmsg = ' '+c.fhR+'*'+c.reset+' '+c.fR+c.Uon+"ERROR"+c.Uoff+c.Ion+'!'+c.reset+": "



def sizeprint(mag, SI=True, decimaldigits=-1):
	size,prefix=float(mag),''
	if SI:
		if size > 1000000000000000L:
			size /= 1000000000000000L
			prefix='P'
		elif size > 1000000000000L:
			size /= 1000000000000L
			prefix='T'
		elif size > 1000000000:
			size /= 1000000000
			prefix='G'
		elif size > 1000000:
			size /= 1000000
			prefix='M'
		elif size > 1024:
			size /= 1000
			prefix='k'
	else:
		if size > 1125899906842624L:
			size /= 1125899906842624L
			prefix='Pi'
		elif size > 1099511627776L:
			size /= 1099511627776L
			prefix='Ti'
		elif size > 1073741824L:
			size /= 1073741824L
			prefix='Gi'
		elif size > 1048576:
			size /= 1048576
			prefix='Mi'
		if size > 2047:
			size /= 1024
			prefix='ki'
	if decimaldigits<=0:
		if size%1==0 or decimaldigits==0:	return "%d%s"%(int(size),prefix)
		else:
			if prefix in ['M','Mi']:	return ("%.01f%s"%(size,prefix))
			elif prefix in ['k','ki']:	return ("%d%s"%(int(math.ceil(size)),prefix))
			else:	return ("%.02f%s"%(size,prefix))
	return (("%%.%df%%s"%decimaldigits)%(size,prefix))



def question_YN(question):
	var = ' '
	while var[0].upper() not in "YN":
		var = raw_input(question)
		if len(var)==0 or answ=='':	return True
		elif var.upper().startswith("N"):	return False
		elif var.upper().startswith("Y"):	return True
		else:	var = ' '


		
def syntax():
	global rc
	print """    Syntax:  tapelib [COMMAND1 [COMMAND2 [... [COMMANDn]...]]

 Creates a device-file /dev/tapelib for the first tape library and performs
 trasnfer/move/import/export/(un)load operations easily showing ASCII scheme of
 tape positions. Only guaranteed to work with barcode-provided tapes!
 
   import[:1,2,...]  Imports into storage from I/E bay slots #1,2,... (or all)
   export[:1,2,...]  Exports into I/E bay from storage slots #1,2,... (or all)
          'command'  Iteratively performs "command" on each tape slots loading/
                     unloading them into 'drives:', *OR* only on tapes given by
                     either 'slots:' and 'IE:' commands. Use character "#" for
                     a drive device-file placeholder. Commands are passed to
                     current shell, so additional substitutions can be later
                     performed by the shell itself: watch out using "'" chars.
    drive:0[,1,...]  Performs the I/O command queue on drive(s) #0,1,...
    slots:1[,2,...]  Performs the I/O command queue from storage slot(s)...
       IE:1[,2,...]  Performs the I/O command queue from I/E bay slot(s)...

 Import operations are run first; then 'command'-driven ones the same order of
 the command line; export ones are at last (better include at most *one* import
 and/or *one* export operation).
 """
	sys.exit(rc.INVALID_SYNTAX)



def run_command(command, drv, stdout=sys.stdout, stderr=sys.stderr):
	global Default_Tape_Drives
#	cmd = command.split()
	for arg in range(len(cmd)):
		if '#' in cmd[arg]:	command = cmd[arg].replace('#',Default_Tape_Drives[drv])
	return subprocess.call(command, stdout=stdout, stderr=stderr)



def detect_SCSI_devices(filter=None, sg=True, onlydev=True, list=False):
	if isWindows:
		if 'COMMONPROGRAMFILES' not in os.environ.keys():	return None
		lsscsi = os.path.join(os.environ['COMMONPROGRAMFILES'],"lsscsi.linux")
		device_strs = os.path.join(os.environ['COMMONPROGRAMFILES'],"device_strs.linux")
		if not os.path.isfile(lsscsi):	return None
		try:	scsi = open(lsscsi,"rb").read()
		except:	return None
		if not os.path.isfile(device_strs):	strs = ""
		else:
			try:	strs = open(device_strs,"rb").read()
			except:	strs = ""
	else:
		device_strs = "/proc/scsi/sg/device_strs"
		if not os.path.isfile(device_strs):	return None
		lsscsi = "/usr/bin/lsscsi"
		if not os.path.isfile(lsscsi):
			lsscsi = "/usr/sbin/lsscsi"
			if not os.path.isfile(lsscsi):
				lsscsi = "/bin/lsscsi"
				if not os.path.isfile(lsscsi):
					lsscsi = "/sbin/lsscsi"
					if not os.path.isfile(lsscsi):	return None
		scsi = subprocess.Popen(["lsscsi"],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
		strs = subprocess.Popen(["cat",device_strs],stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()[0]
	dev = []
	for line in scsi.splitlines():
		if ((not list) or not line.startswith("  ")):
			pre_device = re.search(r"(\[\d{1,2}:\d{1,2}:\d{1,2}:\d{1,2}\])\s+(\S+)\s+(?:(\S+)\s+)?(\S+(?:\s?\S+)+)\s+(\S+)\s+(\-|(?:[/]dev[/]\S+)|(?:[Tt]ape\d{1,2})|(?:[Cc]hanger\d{1,2}))",line)
			if not pre_device:	return None
			device = pre_device.groups();	del pre_device
			if not device and not list:	return None
			dict = {	"name":device[3], "addr":device[0], "type":device[1], "manufacturer":device[2]	}
			if len(dict)>4:	dict["firmware"] = device[4]
			if len(dict["addr"])>2:
				addr = re.match(r"\[(\d{1,2}):(\d{1,2}):(\d{1,2}):(\d{1,2})\]",dict["addr"])
				if addr:
					try:	dict["address"] = map(int, addr.groups())
					except:	continue
					if len(dict["address"])!=4:	del dict["address"];	continue
			if len(device)==5 and device[4]!="-":
				if (isWindows and (device[4].lower().startswith("changer") or device[4].lower().startswith("tape"))) or ((not isWindows) and device[4].startswith("/dev/")):
					dict["dev"] = device[4]
			elif len(device)>5 and  device[5]!="-":
				if (isWindows and (device[5].lower().startswith("changer") or device[5].lower().startswith("tape"))) or ((not isWindows) and device[5].startswith("/dev/")):
					dict["dev"] = device[5]
			dev.append(dict)
	if sg:					#	Detects SCSI-generic devices' node-names and puts them as "dev" keys
		if isWindows:	sgN = 0
		strs_sl = strs.splitlines()
		for m in range(len(strs_sl)):
			if len(strs_sl[m].split('\t'))>2:
				device = strs_sl[m].split('\t')
				for n in range(len(dev)):
					if ("dev" not in dev[n].keys()):
						if device[1]==dev[n]["name"] and device[0]==dev[n]["manufacturer"] and device[2]==dev[n]["firmware"]:
							if isWindows:	dev[n]["dev"] = "Changer%d"%sgN;	sgN += 1
							elif os.path.exists("/dev/sg%d"%m):	dev[n]["dev"] = "/dev/sg%d"%m
	if filter and onlydev:	return [ D for D in dev if ("dev" in D.keys()) and D["type"].lower()==filter.lower() ]
	elif filter and not onlydev:	return [ D for D in dev if D["type"].lower()==filter.lower() ]
	elif onlydev and not filter:	return [ D for D in dev if "dev" in D.keys() ]
	return dev


default_tape_type = "LTO4"
def detect_tapes(tape_type=default_tape_type):
	TapeDevice = {	"lib":{}, "dev":[], "check dB":False, "check tape":False, "lib name":{}, "dev name":{}, "type":{}	}
	drv = detect_SCSI_devices(filter="tape")
	lib = detect_SCSI_devices(filter="mediumx")
	if drv==None or lib==None:	return None
	for mx in lib:
		TapeDevice["lib"][mx["dev"]] = []
		TapeDevice["lib name"][mx["dev"]] = mx["manufacturer"]+' '+mx["name"]
		for tape in drv:
			if tape["address"][0:3]==mx["address"][0:3]:
				TapeDevice["lib"][mx["dev"]].append(tape["dev"])
				break
		for retape in drv:
			if retape["dev"]!=tape["dev"] and retape["name"]==tape["name"] and retape["manufacturer"]==tape["manufacturer"]:
				if abs(retape["address"][0]-tape["address"][0])<=1:
					TapeDevice["lib"][mx["dev"]].append(retape["dev"])
					TapeDevice["lib name"][mx["dev"]] = mx["manufacturer"]+' '+mx["name"]
	for tape in drv:
		TapeDevice["dev name"][tape["dev"]] = tape["manufacturer"]+' '+tape["name"]
		TapeDevice["type"][tape["dev"]] = tape_type
	if ("lib" not in TapeDevice.keys()) or (not len(TapeDevice["lib"])):
		for tape in drv:	TapeDevice["dev"].append(tape["dev"])
	else:
		for tape in drv:
			for lib in TapeDevice["lib"].values():
				if tape["dev"] not in lib:	TapeDevice["dev"].append(tape["dev"])
	if len(TapeDevice["dev"]) or len(TapeDevice["lib"]):	return TapeDevice
	else:	return None



def init_lib(tapeinfo):
	global lib
	print "Initializing Tape library, scanning tapes and drives",
	if 'lib' in tapeinfo.keys() and len(tapeinfo['lib']):
		tapelib = tapeinfo['lib'].keys()[0]
		tapedrv = tapeinfo['lib'][tapelib][0]
		lib = SCSItapelib(tapelib, drives=tapeinfo['lib'][tapelib])#	, storages=35, IEslots=6)
	else:	return None
	lib.status()
	if not lib:	print "                  "+ERRmsg+'\n'+ERRstr + "Unable to initialize tape library "+c.fG+tapelib+c.reset
	else:
		print "                  "+OKmsg
		for slot in range(lib.drives):
			if lib.drive_full(slot):
				if (lib.free_storages>0 or lib.free_IEslots>0):
					print "Unloading residual Tape from drive #%02d....."%slot,
					lib.unload(slot)
					if lib.drive_full(slot):	print "                           "+ERRmsg
					else:	print "                           "+OKmsg
				else:
					print ERRstr + "All drives "+c.Uon+"free"+c.Uoff+" and no free slots to unload them to!"
					sys.exit(lib.DRIVE_FULL)
		lib.status()
		if lib.free_drives==0:
			print WRNstr + " No "+c.Uon+"free"+c.Uoff+" tape drives into library and unable to unload them.\n           Please free some space."
			sys.exit(lib.DRIVE_FULL)
	if not touse_slots:
		touse_slots = [ el for el in range(1,lib.storages+1) if lib.stor_full(el) ]
		if len(touse_slots)<1:
			print ERRstr + "No tapes inside the library's internal storage"
			sys.exit(rc.NO_TAPES_LEFT)
	else:
		touse_slots = [ el for el in touse_slots if (1<=el<=lib.storages and lib.stor_full(el)) ]
		if len(touse_slots)<1:
			print WRNstr + "No tapes in the specified slots."
			sys.exit(rc.NO_TAPES_LEFT)
	jukebox = [ {
		"slot":el, "stor":True, "BC":lib.stor_label(el), 
		"todo":True, "in":lib.stor_full(el), "done":False, "err":0
	} for el in sorted(touse_slots) ]



def main():
	cmdQ, cmd, incmd, Islots, Eslots, command, isimport, isexport = [], [], False, None, None, "", False, False
	storage = IE = drive = []
	stat = None

	print "Initializing Tape library, scanning tapes and drives",
	tapeinfo = detect_tapes()
	if 'lib' in tapeinfo.keys() and len(tapeinfo['lib']):
		tapelib = tapeinfo['lib'].keys()[0]
		tapedrv = tapeinfo['lib'][tapelib][0]
		lib = SCSItapelib(tapelib, drives=tapeinfo['lib'][tapelib])#	, storages=35, IEslots=6)
	else:	sys.exit(-1)
	lib.status()
#	lib.shelf(check=True)

	if lib and type(lib)!=type(1):	print OKstr
	else:
		lib = SCSItapelib("tapelib", ["st2","st3"])
		if lib and type(lib)!=type(1):	print OKstr
		else:
			print ERRstr+"\n "+c.fhR+'*'+c.reset+'Error initializing tape library device "%s" with drives %s !'%(sg,repr(Default_Tape_Drives))
			sys.exit(rc.TAPE_LIBRARY_ERROR)



	for n in range(1,len(sys.argv[1:])+1):
		arg = sys.argv[n]
		if (arg.lower().startswith("import:") or arg.lower().startswith("export:")) and len(arg)>7:
			slots = None
			try:
				slots = map(int,arg[7:].split(','))
				for k in slots:
					if k<0:	raise IOError
			except:
				print "Invalid mass Import/Export slots' syntax in operation #%d: Skipped.\nSyntax is import|export:1[,2[,...[,n]]]"%n
				continue
			if arg.lower().startswith("import"):	isimport, Islots = True, slots
			elif arg.lower().startswith("export"):	isexport, Eslots = True, slots
		elif arg.lower()=="import":	isimport, Islots = True, None
		elif arg.lower()=="export":	isexport, Eslots = True, None
		elif arg.lower().startswith("drive:") and len(cmd)>6:
			try:
				drive = map(int,arg[6:].split(','))
				for k in drive:
					if k<0:	raise IOError
			except:
				print "Invalid drive slots' syntax in operation #%d: Skipped.\nSyntax is drive:1[,2[,...[,n]]]"%n
				continue
		elif arg.lower().startswith("slots:") and len(arg)>6:
			try:
				storage = map(int,arg[6:].split(','))
				for k in storage:
					if k<0:	raise IOError
			except:
				print "Invalid storage slots' syntax in operation #%d: Skipped.\nSyntax is storage:1[,2[,...[,n]]]"%n
				continue
		elif arg.lower().startswith("IE:") and len(arg)>3:
			try:
				IE = map(int,arg[3:].split(','))
				for k in IE:
					if k<0:	raise IOError
			except:
				print "Invalid I/E bay slots' syntax in operation #%d: Skipped.\nSyntax is IE:1[,2[,...[,n]]]"%n
				continue
		else:	cmdQ.append(arg)
	#	if n<len(sys.argv[1:]):
	#		key = raw_input("Press "+c.fhY+'Q'+c.reset+" to quit, "+c.fhR+'['+c.reset+"any other key"+c.fhR+']'+c.reset+" to continue...")
	#		if key.upper().startswith('Q'):
	#			lib.shelf()
	#			del lib
	#			sys.exit(0)
	if incmd:	print "Unfinished command!";	syntax()
	del cmd, incmd
	
	if isimport:
		lib.shelf(blink={"IE":Islots})
		lib.mass_import(Islots)
	if len(cmdQ)>0 and (len(drive)>0 or len(storage)>0 or len(IE)>0):
		drive_stat = dict([ [i,"exclude"] for i in range(lib.drives) if i not in drive ])
		storage_stat = dict([ [j,"exclude"] for j in range(1,lib.storages+1) if j not in storage ])
		IE_stat = dict([ [k,"exclude"] for k in range(1,lib.IEslots+1) if k not in IE ])
	#	print drive_stat
	#	print storage_stat
	#	print IE_stat
	#	drive_stat = storage_stat = IE_stat = []
		stat = {"exclude":{
			"drive":[slot[0] for slot in drive_stat.keys()], 
			"storage":[slot[0] for slot in storage_stat.keys()], 
			"IE":[slot[0] for slot in IE_stat.keys()]  }}
	#	lib.shelf(blink={"drives":drive,"storage":storage, "IE":IE})
		lib.shelf(status=stat, check=False)

		drv = 0		# drv is #0, but a two-drive multi-threading routine will be in order soon
		for slot in storage:
			if not lib.drive_full(drv) and lib.stor_full(slot):
				print "LOADING TAPE FROM STORAGE SLOT #%d INTO DRIVE #%d..."%(slot,drv),
				lib.load(slot, drv, storage=True)
				for n in range(len(cmdQ)):
					command = cmdQ[n]
					if '#' in command:	command.replace('#',c.fhY+Default_Tape_Drives[drv]+c.fhW)
					print "RUNNING COMMAND: " + c.fhW + command + c.reset
					(out, msg) = run_command(cmdQ[n], drv)
					if len(out)==0 and len(msg)>0:	storage_stat[slot] = "error"
					elif len(out)>0 and len(msg)==0:	storage_stat[slot] = "OK"
					else:	storage_stat[slot] = "warning"
				if lib.drive_full(drv):
					if not lib.stor_full(slot):
						print "UNLOADING TAPE FROM DRIVE #%d INTO STORAGE SLOT #%d..."%(drv,slot),
						lib.unload(drv, slot, storage=True)
					else:
						print "UNLOADING TAPE FROM DRIVE #%d INTO A FREE STORAGE SLOT..."%drv,
						lib.unload(drv, storage=True)
			if storage_stat[slot] == "OK":	stat["OK"]["storage"].append(slot)
			elif storage_stat[slot] == "error":	stat["warning"]["error"].append(slot)
			else :	stat["warning"]["storage"].append(slot)
			lib.shelf(status=stat, check=False)
		for slot in IE:
			if not lib.drive_full(drv) and lib.IE_full(slot):
				print "LOADING TAPE FROM I/E BAY SLOT #%d INTO DRIVE #%d..."%(slot,drv),
				lib.load(slot, drv, storage=False)
				for n in range(len(cmdQ)):
					command = cmdQ[n]
					if '#' in command:	command.replace('#',c.fhY+Default_Tape_Drives[drv]+c.fhW)
					print "RUNNING COMMAND: " + c.fhW + command + c.reset
					(out, msg) = run_command(cmdQ[n], drv)
					if len(out)==0 and len(msg)>0:	IE_stat[slot] = "error"
					elif len(out)>0 and len(msg)==0:	IE_stat[slot] = "OK"
					else:	IE_stat[slot] = "warning"
				if lib.drive_full(drv):
					if not lib.IE_full(slot):
						print "UNLOADING TAPE FROM DRIVE #%d INTO I/E BAY SLOT #%d..."%(drv,slot),
						lib.unload(drv, slot, storage=False)
					else:
						print "UNLOADING TAPE FROM DRIVE #%d INTO A FREE I/E BAY SLOT..."%drv,
						lib.unload(drv, storage=False)
			if storage_stat[slot] == "OK":	stat["OK"]["IE"].append(slot)
			elif storage_stat[slot] == "error":	stat["warning"]["IE"].append(slot)
			else :	stat["warning"]["IE"].append(slot)
			lib.shelf(status=stat, check=False)
		del command, drive_stat, storage_stat, IE_stat, stat["exclude"]
		print cmdQ
		print cmd


	if isexport:
		lib.shelf(blink={"storage":Eslots}, status=stat)
		lib.mass_export(Eslots)

	print "\n"
	try:	lib.shelf(status=stat)
	except:
		try:	lib.shelf(status=stat)
		except:
			print "\r "+c.fhR+'*'+c.reset+' Error communicating with tape library (idle?)'
			sys.exit(rc.TAPE_LIBRARY_ERROR)
	del lib
	sys.exit(0)




main()
