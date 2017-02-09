# coding=UTF-8
import getopt
import sys
import os
import io
import xml.etree.ElementTree as ET
import difflib
import re
from multiprocessing import Pool
from collections import deque

import WikiExtractor
import utils

# Maximal distance of two words to be considered as typo
typoTreshold = 2

# Minimal length of word for typo matching
typoMinWordLen = 4

# Minimal treshold that should old & new sentences from revision diff have to be
# considered as two similar sentences. Similarity is returned by sentenceSimilarity function.
sentenceTreshold = 0.7

# Multiprocessing - Pool processes count
poolProcesses = 8

# Count of WikiPages
pagesCount = 372696


corpBuffer = []

# Settings from command line = default settings
preserveRobotRevisions = False
filterOutput = False
lang = "english"
dumpPaths = []
dumpDownloads = []
pageDownloads = []
outputFolder = "export/"
outputFormat = "txt"

supportedLangs = ("czech", "english")
supportedOutputFormats = ("txt", "se")

unitokConfig = None
errCorpConfig = None

outputStream = None

# Base classes
class page(object):
	title = "Some interesting title"
	revisions = []
	def __init__(self):
		title = ""
		revisions = []
	
class revision(object):
	timestamp = "Long long time ago"
	comment = "Wonderfull improvements of content"
	text = "To be or not to be, that is the question!"
	author = "Interesting author"
	contentFormat = "wikimarkup" #[wikimarkup|html|plaintext]

	def __init__(self):
		self.timestamp = ""
		self.comment = ""
		self.text = ""
		self.author = ""
		self.contentFormat = "wikimarkup"

###############################################################################
#
# Extractor functions
#  -main, processStream, renderPageRevisions, renderRevision, removeBadRevisions, 
#   processPage, processRevisions, processStacks, writeCorpBuffer, 
#   resolveEvolution, classifyEditType, findTypos, extractTypos, appendRev
#
###############################################################################

def appendRev(textList, oldRev, newRev):
	"""Searches the textList. If any list (within textList) ends with oldRev then appeds newRev at it's end.
	Otherwise it creates new list and inserts it in the textList"""
	
	founded = False
	for k in range(0, len(textList)):
		#if(textList[k][-1]==newRev):
		#	break #TODO search revision list to find right place for adding old Version
		if(textList[k][-1]==oldRev):
			textList[k] = textList[k] + (newRev,)
			founded = True
			break
	if not founded:
		textList.append((oldRev, newRev))	

def extractTypos(oldSent, newSent):
	"""Extracts typos from old & new sentence version and writes them into the stream. Key idea -
	difference of old sentence's & new sentence's word's sets gives us set of words which has been changed.
	If we look through the new sentence's words for each this word and get the one with the least word
	distance lesser than typo treshold it might be the correction"""
	
	oldBag = utils.bagOfWords(oldSent, minWordLen=typoMinWordLen)
	newBag = utils.bagOfWords(newSent, minWordLen=typoMinWordLen)
	difference = oldBag - newBag
	typos = []
	for word in difference:
		candidates = [(x, utils.wordDistance(word, x)) for x in newBag]
		candidates = [(x, d) for (x, d) in candidates if d <= typoTreshold]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			typos.append((word, candidates[0][0]))
	return typos	


def findTypos():
	"""Iterates through corp buffer & extracts typos where revisions are marked as typos"""
	
	typos = []
	for error in corpBuffer:
		for i in range(1, len(error)):
			if(error[i][0]=="typos"):
				oldSent = error[i-1][1]
				newSent = error[i][1]
				t = extractTypos(oldSent, newSent)
				for typo in t:
					appendRev(typos, typo[0], typo[1])
	typos = [[["typos", x[0]],["typos", x[1]]]for x in typos]
	return typos

def classifyEditType(oldSentenceList, newSentenceList):
	"""Classifies revision and returns edit type"""
	
	oldBag = utils.bagOfWords(oldSentenceList[1])
	newBag = utils.bagOfWords(newSentenceList[1])
	comment = newSentenceList[0]
	if(oldBag - newBag == 0):
		return "order"
	if(errCorpConfig.typoFilter.search(comment)):
		return "typos"
	if(errCorpConfig.editFilter.search(comment)):
		return "edits"
	return "other"

def resolveEvolution():
	"""Resolves evolution - 
	Changes structure of corp buffer to list of evolution lists:
	[[[allComments, baseSentence], [comment, edit], ...], ...]"""
	
	global corpBuffer
	evolutionLinks = []
	toRemove = set()
	for i in range(0, len(corpBuffer)):
		for j in range(i, len(corpBuffer)):
			if(corpBuffer[i][2] == corpBuffer[j][1]):
				toRemove.add(corpBuffer[i])
				toRemove.add(corpBuffer[j])
				appendRev(evolutionLinks, i, j)
				break
	evolutionDeques = []
	for ev in evolutionLinks:
		queue = []
		oldSentenceList = ["", corpBuffer[ev[0]][1]]
		queue.append(oldSentenceList) #Append first oldest sentence
		allComments = ""
		for l in ev:
			allComments += corpBuffer[l][0] + "<separator>"
			newList = [corpBuffer[l][0], corpBuffer[l][2]]
			newList[0] = classifyEditType(oldSentenceList, newList)
			queue.append(newList) #Append newer versions of sentence
			oldSentenceList = newList
		queue[0][0] = allComments
		evolutionDeques.append(queue)
	#Normalize corpBuffer to have the same structure as evolution deques & remove matched evolution sentences
	corpBuffer = [[[x[0], x[1]], [classifyEditType(["", x[1]], [x[0], x[2]]), x[2]]] for x in corpBuffer if x not in toRemove]
	corpBuffer = evolutionDeques + corpBuffer


def writeCorpBuffer():
	"""Processes and flushes buffer to disk"""
	
	global corpBuffer
	resolveEvolution()
	typos = findTypos()
	if len(typos) > 0:
		utils.writeStream(outputStream, typos, outputFormat)
	if len(corpBuffer) > 0:
		utils.writeStream(outputStream, corpBuffer, outputFormat)
	corpBuffer = []	

def processStacks(oldStack, newStack, comment):
	"""Processes sentence's stacks - old sentences are matched to sentences from new sentence's stack"""
	
	if(len(oldStack) == 0 or len(newStack) == 0):
		return
	oldStack = deque([x for x in oldStack if x not in newStack])
	while len(oldStack) > 0:
		oldSent = oldStack.popleft()
		candidates = [(x, utils.sentenceSimilarity(oldSent, x)) for x in newStack]
		candidates = [(x, similarity) for (x, similarity) in candidates if similarity > sentenceTreshold]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			corpBuffer.append((comment, oldSent, candidates[0][0]))

def processRevisions(oldRev, newRev):
	"""Compares two revisions and constructs old and new stacks of sentences for further processing"""

	if(oldRev == None or newRev == None or oldRev.text == None or newRev.text == None):
		return
	oldStack = deque()
	newStack = deque()
	for line in difflib.unified_diff(oldRev.text, newRev.text):
		if line.startswith(' '): #Skip unnecessary output
			continue
		elif line.startswith('---'):
			continue
		elif line.startswith('+++'):
			continue
		elif line.startswith('-'): #Write diff lines from old revision to stack
			oldStack.append(line[1:])
		elif line.startswith('+'): #Write diff lines from new revision to stack
			newStack.append(line[1:])
	processStacks(oldStack, newStack, newRev.comment)

def removeBadRevisions(page):
	"""Function for removing bot or reverted revisions."""
	
	page.revisions = [x for x in page.revisions if x != None and x.comment != None]
	if(not preserveRobotRevisions):
		page.revisions = [x for x in page.revisions if not errCorpConfig.botFilter.search(x.comment)]
	
	toRevert = []
	prev = None
	for rev in page.revisions:
		if(errCorpConfig.revertFilter.search(rev.comment)):
			toRevert.append(rev)
			toRevert.append(prev)
		prev = rev
	toRevert = set(toRevert)
	page.revisions = [x for x in page.revisions if x not in toRevert]

def processPage(page):
	"""Removes reverted revisions, goes through revs and sends every two neighbous to processing"""
	
	newRev = page.revisions[0]
	for i in range(1, len(page.revisions) - 1):
		oldRev = newRev
		newRev = page.revisions[i - 1]
		if(newRev.comment != None):
			processRevisions(oldRev, newRev)
	writeCorpBuffer()

def renderRevision(rev, title):
	"""Renders revision in HTML/WikiMarkup to plaintext; TODO Html conversion"""
	
	if(rev.text != None): 
		if(rev.contentFormat == "wikimarkup"):
			text = re.sub("\n(\s\n)*", "<stop>", rev.text) #Replace more paragraphs endings
			out = io.StringIO()
			extractor = WikiExtractor.Extractor(0, 0, title, text.split("\n"))
			extractor.extract(out)
			rev.text = out.getvalue()
			out.close()
			rev = utils.splitBySentences(rev)
			rev.contentFormat = "plaintext"
			return rev
		else:
			return rev
	else:
		return rev	

def renderPageRevisions(page):
	"""Renders all revs in wiki markup/html into plain text and then cleans output text"""
	
	pool = Pool(processes=poolProcesses)
	poolAsyncResults = []
	for rev in page.revisions:
		poolAsyncResults.append(pool.apply_async(renderRevision, args=(rev, page.title)))
		#rev = renderRevision(rev, page.title)
	for i in range(0, len(poolAsyncResults) - 1):
		try:
			page.revisions[i] = poolAsyncResults[i].get()	#collect results from pool
		except:
			page.revisions[i].text = None
	page.revisions = [x for x in page.revisions if x != None]
	
def processStream(fileStream):
	"""Processes XML stream in export schema https://www.mediawiki.org/xml/export-0.8.xsd"""
	
	pagesProcessed = 0    
	curPage = page()
	curRevision = revision()

	skip = False
	for event, elem in ET.iterparse(fileStream):
		if event == 'end':
			if elem.tag.endswith('title'):
				pagesProcessed += 1
				curPage.title = elem.text
				if(errCorpConfig.excludeFilter.search(curPage.title)):
					print("Skipping page   #%s: %s" % (pagesProcessed, curPage.title))
					skip = True
					continue
				else:
					print("Processing page #%s: %s" % (pagesProcessed, curPage.title))
					skip = False
			if(not skip):
				if elem.tag.endswith('timestamp'):
					curRevision.timestamp = elem.text
				elif elem.tag.endswith('comment'):
					curRevision.comment = elem.text
				elif elem.tag.endswith('text'):
					if(elem.text != None or elem.text != ""):
						curRevision.text = elem.text
				elif elem.tag.endswith('revision'):
					curPage.revisions.append(curRevision)
					curRevision = revision()
				elif elem.tag.endswith('page'):
					removeBadRevisions(curPage)
					renderPageRevisions(curPage)
					#pool.apply(processPage, args=(curPage,))
					processPage(curPage)
					curPage = page()
					curPage.revisions = []
			elem.clear()
			
def main():
	"""Main func"""
	
	pool = Pool(processes=1)
	downloadResult = None
	if(len(dumpDownloads) > 0):
		url = dumpDownloads.popleft()
		downloadResult = pool.apply_async(utils.downloadFile, args=(url,))
		
	for path in dumpPaths:
		print("Processing file %s" % (path,))
		stream = utils.openStream(path)
		processStream(stream)
	try:
		filePath = downloadResult.get()	#wait for download end
		
		while len(dumpDownloads) > 0:
			print("Processing file %s" % filePath)
			url = dumpDownloads.popleft()
			downloadResult = pool.apply_async(utils.downloadFile, args=(url,))
			stream = utils.openStream(filePath)
			processStream(stream)
			stream.close()
			os.remove(filePath)
			filePath = downloadResult.wait()
		print("Processing file %s" % filePath)	
		stream = utils.openStream(filePath)
		processStream(stream)
		stream.close()
		os.remove(filePath)				
			
	except OSError:
		pass


if __name__ == "__main__":
	print("Preparing environment")
	try:
		opts, args = getopt.getopt(sys.argv[1:], "p:d:u:l:o:f:hrF",
		                           ["paths=", "dumpUrls=", "pageUrls=" "lang=", "robots", "help", "outputFilter", "output=", "outputFormat="])
	except getopt.GetoptError:
		utils.printUsage()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			utils.printUsage()
			sys.exit()
		elif opt in ("-l", "--lang"):
			lang = arg
			if lang not in supportedLangs:
				print("%s language is not supported, switching to English" % lang)
				lang = "en"	    
		elif opt in ("-r", "--robots"):
			preserveRobotRevisions = True
		elif opt in ("-p", "--paths"):
			dumpPaths = deque([x.strip() for x in arg.split(",")])
		elif opt in ("-d", "--dumpUrls"):
			dumpDownloads = deque([x.strip() for x in arg.split(",")])
		elif opt in ("-u", "--pageUrls"):
			pageDownloads = deque([x.strip() for x in arg.split(",")])
		elif opt in ("-o", "--output"):
			outputFolder = arg
		elif opt in ("-f", "--outputFormat"):
			outputFormat = arg
			if outputFormat not in supportedOutputFormats:
				print("%s output format is not supported, switching to text output" % outputFormat)
				outputFormat = "txt"
		elif opt in ("-F", "--outputFilter"):
			filterOutput = True		
	outputStream = io.open('export/output.txt', 'w')
	from importlib import import_module
	errCorpConfig = import_module("confs." + lang)
	unitokConfig = import_module("unitok-confs." + lang)
	
	utils.unitokConfig = unitokConfig
	utils.errCorpConfig = errCorpConfig
	utils.init()
	print("Environment prepared")
	main()