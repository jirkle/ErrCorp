# coding=UTF-8
import getopt
import sys
import os
import io
import bz2
import xml.etree.ElementTree as ET
import urllib
import datetime
import time
from collections import deque
from multiprocessing import Pool

import WikiDownload
import PageProcessor
import ErrorExtractor
import PostProcessor
import Exporter
import Utils

# Settings from command line & default settings
context = {
  # Command line flag: Include revisions made by bots
  "preserveRobotRevisions": False,
  # Command line flag: Allows evolution of errors through revisions, implemented but yet experimental
  "allowNesting": False,
  # Command line flag: Script informs only about current processed page, estimated time and corp stats
  "mute": False,
  # Default lang
  "lang": ("english", "en"),
  # First is name of language file in confs directory, second language abbreviation for mwclient (MediaWiki api endpoint)
  "supportedLangs": (("english", "en"), ("czech", "cs")),
  # Maximal distance of error and correction to be considered as typo (used by classifier)
  "typoTreshold": 2,
  # Maximal word distance used by classifier
  "wordTreshold": 2,
  # Minimal treshold that should old & new sentences from revision diff have to be
  # considered as two similar sentences. Similarity is returned by Utils.sentenceSimilarity function.
  "sentenceTreshold": 0.7,
  # Multiprocessing - Pool processes count
  "poolProcesses": 8,
  "dumpPaths": [],
  "dumpDownloads": [],
  "pageDownloads": [],
  "outputFolder": "export/",
  "outputFormat": "se",
  "outputStreamFull": None,
  "outputStreamOrphans": None,
  # Supported output formats by Exporter
  "supportedOutputFormats": ("txt", "se"),
  "separator": ";",
  "unitokConfig": None,
  "errCorpConfig": None,
  "pagesCount": 378675,
  "skipped": 0,
  "startTime": None,
  "processedPages": 0,
  "timeout": 5
}

p = dict()

def printUsage():
	"""Prints usage information"""
	
	print('-h\t--help\t\tPrint help')
	print('-l\t--lang\t\tLang of processed dumps [czech|english]')
	print('-s\t--separator\tSeparator char, default [;]')
	print('-r\t--robots\tFlag: Include revisions made by bots')
	print('-n\t--nesting\tFlag: If present, nesting of errors are allowed, yet experimental')
	print('-m\t--mute\tFlag: Script informs only about current processed page, estimated time and corp stats')
	print('Input, all combinations are allowed:')
	print('-p\t--paths\t\tLocal paths to dump files [dumpPath(, dumpPath)*]')
	print('-d\t--dumpUrls\tRemote paths to dump files [dumpDownloadUrl(, dumpDownloadUrl)*]')
	print('-a\t--articleName\tUrl paths to pages [pageUrl(, pageUrl)*]')    
	print('Output:')
	print('-o\t--output\tOutput path')
	print('-f\t--outputFormat\tOutput format [txt|se]')
	
def openStream(path):
	"""Opens compressed files (7z, bz2) & uncompressed xml"""
	
	if(path.lower().endswith('.bz2')):
		return bz2.BZ2File(path, "r")
	elif(path.lower().endswith('.xml')):
		return open(path, "r")
	elif(path.lower().endswith('.7z')):
		raise Exception('7zip files are not supported yet')
		#return lzma.open(path, "r")
	else:	
		return None
		
def downloadFile(url):
	"""Downloads file from url"""
	
	fileName = url.split('/')[-1]
	print("Starting background downloading of %s" % url)
	urllib.request.urlretrieve(url, fileName)
	return fileName

def processPage(page):
	page = PageProcessor.normalize(page)
	if(not context["mute"]):
		print("Extracting errors")
	page = ErrorExtractor.extract(page)
	if(len(page["revisions"]) == 0 or len(page["errors"]) == 0):
		context["processedPages"] +=1
		print("No errors extracted")
		return
	if(not context["mute"]):
		print("Post processing errors")
	page = PostProcessor.process(page)
	if(not context["mute"]):
		print("Flushing to corpora")
	Exporter.exportToStream(page)
	context["processedPages"] +=1
	delta = datetime.datetime.now() - context["startTime"]
	remainingTime = context["pagesCount"]/float(context["processedPages"]) * delta
	print("Estimated remaining time: %s" % str(remainingTime))
	
	
def processStream(fileStream):
	"""Processes XML stream in export schema https://www.mediawiki.org/xml/export-0.8.xsd"""
	
	context["processedPages"] = 0    
	curPage = { "name": "", "revisions": [], "errors": [] }
	curRevision = { "user": "", "timestamp": "", "comment": "", "*": "", "format": "wikimarkup"}

	skip = False
	for event, elem in ET.iterparse(fileStream):
		if event == 'end':
			if elem.tag.endswith('title'):
				curPage["name"] = elem.text
				if(context["errCorpConfig"].excludeFilter.search(curPage["name"])):
					print("Skipping page   #%s: %s" % (context["processedPages"] + 1, curPage["name"]))
					context["processedPages"] += 1
					context["skipped"] += 1
					skip = True
					continue
				else:
					print("Processing page #%s: %s" % (context["processedPages"] + 1, curPage["name"]))
					skip = False
			if(not skip):
				if elem.tag.endswith('timestamp'):
					curRevision["timestamp"] = elem.text
				elif elem.tag.endswith('username'):
					curRevision["user"] = elem.text
				elif elem.tag.endswith('ip'):
					curRevision["user"] = elem.text
					curRevision["annon"] = ""
				elif elem.tag.endswith('comment'):
					curRevision["comment"] = elem.text
				elif elem.tag.endswith('text'):
					if(elem.text != None or elem.text != ""):
						curRevision["*"] = elem.text
				elif elem.tag.endswith('revision'):
					curPage["revisions"].append(curRevision)
					curRevision = { "user" : "", "timestamp": "", "comment": "", "*": "", "format": "wikimarkup" }
				elif elem.tag.endswith('page'):
					#pool.apply(processPage, args=(curPage,))
					processPage(curPage)
					curPage = { "revisions" : [] }
			elem.clear()
			
def main():
	"""Main func"""
	#Download articles through wiki api if any
	global p
	context["startTime"] = datetime.datetime.now()
	context["outputStreamFull"].write("<errcorp>")
	context["outputStreamOrphans"].write("<errcorp>")	
	processed = 0
	for page in context["pageDownloads"]:
		print("Downloading page %s" % page)
		p = WikiDownload.get_page(page)
		print("Processing page %s" % page)
		processPage(p)
		processed +=1
		print("Done %s%%" % (float(processed)/len(context["pageDownloads"])*100))
	pool = Pool(processes=1)

	#Start downloading first dump online if any
	downloadResult = None
	url = None
	if(len(context["dumpDownloads"]) > 0):
		url = context["dumpDownloads"].popleft()
		downloadResult = pool.apply_async(downloadFile, args=(url,))
	
	#Process local dumps if any
	for path in context["dumpPaths"]:
		print("Processing file %s" % (path,))
		stream = openStream(path)
		processStream(stream)
	
	#Wait for download of first online dump an process them all (if any)
	try:
		fileName = url.split('/')[-1]
		time.sleep(1)
		while(not downloadResult.ready()):
			print("Downloaded %s bytes of %s" % (os.stat(fileName).st_size, fileName), end="\r")
			time.sleep(10)
		filePath = downloadResult.get()	#wait for download end
		
		while len(context["dumpDownloads"]) > 0:
			print("Processing file %s" % filePath)
			url = context["dumpDownloads"].popleft()
			fileName = url.split('/')[-1]
			downloadResult = pool.apply_async(downloadFile, args=(url,))
			stream = openStream(filePath)
			processStream(stream)
			stream.close()
			os.remove(filePath)
			while(not downloadResult.ready()):
				print("Downloaded %s bytes of %s" % (os.stat(fileName).st_size, fileName), end="\r")
				time.sleep(10)			
			filePath = downloadResult.wait()
		print("Processing file %s" % filePath)	
		stream = openStream(filePath)
		processStream(stream)
		stream.close()
		os.remove(filePath)	
	except:
		pass
	context["outputStreamFull"].write("</errcorp>")
	context["outputStreamOrphans"].write("</errcorp>")	


if __name__ == "__main__":
	print("Preparing environment")
	try:
		opts, args = getopt.getopt(sys.argv[1:], "p:d:a:l:o:f:s:hmnr",
		                           ["paths=", "dumpUrls=", "articleName=" "lang=", "output=", "outputFormat=", "separator=", "robots", "help", "nesting", "mute"])
	except getopt.GetoptError:
		printUsage()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			printUsage()
			sys.exit()
		elif opt in ("-l", "--lang"):
			try:
				context["lang"] = [supLang for supLang in context["supportedLangs"] if arg in supLang][0]
			except:
				print("%s language is not supported, switching to English" % arg)
				context["lang"] = context["supportedLangs"][0]
		elif opt in ("-r", "--robots"):
			context["preserveRobotRevisions"] = True
		elif opt in ("-n", "--nesting"):
			context["allowNesting"] = True
		elif opt in ("-m", "--mute"):
			context["mute"] = True				
		elif opt in ("-p", "--paths"):
			context["dumpPaths"] = deque([x.strip() for x in arg.split(context["separator"])])
		elif opt in ("-d", "--dumpUrls"):
			context["dumpDownloads"] = deque([x.strip() for x in arg.split(context["separator"])])
		elif opt in ("-a", "--articleName"):
			context["pageDownloads"] = deque([x.strip() for x in arg.split(context["separator"])])
		elif opt in ("-o", "--output"):
			context["outputFolder"] = arg
		elif opt in ("-s", "--separator"):
			context["separator"] = arg
		elif opt in ("-f", "--outputFormat"):
			context["outputFormat"] = arg
			if context["outputFormat"] not in context["supportedOutputFormats"]:
				print("%s output format is not supported, switching to text output" % context["outputFormat"])
				context["outputFormat"] = "txt"
	#Create output file and output path if it doesn't exists
	if not os.path.exists(context["outputFolder"]):
		os.makedirs(context["outputFolder"])
	context["outputStreamFull"] = io.open('%soutput.%s' % (context["outputFolder"], context["outputFormat"]), 'w+', encoding="utf-8")
	context["outputStreamOrphans"] = io.open('%soutput-orphans.%s' % (context["outputFolder"], context["outputFormat"]), 'w+', encoding="utf-8")
	
	from importlib import import_module
	context["errCorpConfig"] = import_module("confs." + context["lang"][0] + "-err-corp")
	context["unitokConfig"] = import_module("confs." + context["lang"][0])
	
	Exporter.context = context
	PageProcessor.context = context
	ErrorExtractor.context = context
	PostProcessor.__init__(context)
	Utils.context = context
	
	if(len(context["pageDownloads"]) > 0):
		WikiDownload.init(context["lang"][1])	
	print("Environment prepared")
	main()
