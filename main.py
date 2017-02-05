# coding=UTF-8
import getopt
import sys
import io
import xml.etree.ElementTree as ET
import difflib
from multiprocessing import Pool
from collections import deque

import WikiExtractor
from UnicodeHack import hack_regexp
from utils import *

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
lang = "en"
supportedLangs = ("cs", "en")
dumpPaths = ["../cswiki.xml.bz2"]
dumpDownloads = []
pageDownloads = []
outputFolder = "export/"

woOutputStream = None
typoOutputStream = None
editOutputStream = None
otherOutputStream = None

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
	format = "wiki-markup" #[wikimarkup | plaintext]

	def __init__(self):
		self.timestamp = ""
		self.comment = ""
		self.text = ""
		self.author = ""
	    
# Comment filters
excludeFilter = {
	'cs':re.compile(r'.*((Hlavní\sstrana)|([rR]ozcestník)|(Nápověda:)|(Wikipedista:)|(Wikipedie:)|(Diskuse:)|(MediaWiki:)|(Portál:)|(Šablona:)|(Kategorie:)).*', re.U),
	'en':re.compile(r'.*((Main\sPage)).*', re.U)
}
	    
typoFilter = {
	'cs':re.compile(r'.*(([Tt]ypo)|([Cc]l[\s\:])|([Cc]leanup)|([Cc]u[\s\:])|([Pp]řeklep)|([Pp]ravopis)|([Kk]osmetické)|([Dd]robnost)|([Oo]prav)|([Oo]pr[\s\:])|(\-\>)).*', re.U),
	'en':re.compile(r'.*(([Tt]ypo)|([Cc]l[\s\:])|([Cc]leanup)|([Cc]u[\s\:])|(\-\>)).*', re.U)
}
	    
editFilter = {
	'cs':re.compile(r'.*(([Cc]opyedit)|([Cc]pyed)|([Ee]dit)|([Pp]řepsání)|([Tt]ypografie)|([Rr]evize)).*', re.U),
	'en':re.compile(r'.*(([Cc]opyedit)|([Cc]pyed)|([Cc]e[\s\:])|([Ee]dit)|([Tt]ypography)).*', re.U)
}
	    
revertFilter = {
	'cs':re.compile(r'(.*(([Rr]evert)|([Rr]vrt)|([Rr]v[\s\:])|(rvv)|([Ee]ditace\s([0-9]\s)*uživatele)|(vrácen)|(zrušen)|(vandal)|([Vv]erze\s([0-9]\s)*uživatele)).*)|(rv)', re.U),
	'en':re.compile(r'(.*(([Rr]evert)|([Rr]vrt)|([Rr]v[\s\:])|(rvv)|(vandalism)).*)|(rv)', re.U)
}
	    
botFilter = {
	'cs':re.compile(r'(.*(([Rr]obot)|([Bb]ot[\s\:])|([Bb]otCS)|(WPCleaner)).*)', re.U),
	'en':re.compile(r'(.*(([Rr]obot)|([Bb]ot[\s\:])|(WPCleaner)).*)', re.U)
}

###############################################################################
#
# Extractor functions
#  -main, processStream, normalizeText, removeBadRevisions, processPage, processRevisions,
#   processStacks, writeCorpBuffer, findEdits, findTypos, findWO
#
###############################################################################

# Extracts word order corrections from old & new sentence version and writes them into the stream. 
# Key idea - if difference of old sentence's & new sentence's word's sets is equals 0 then the only 
# thing that could've changed is word order
def findWO(oldSent, newSent, comment):
	oldBag = bagOfWords(oldSent)
	newBag = bagOfWords(newSent)
	if(oldBag - newBag == 0):
		woOutputStream.write("%s\n%s\n%s\n\n" % (comment.encode("utf-8"), oldSent, newSent))
		return True
	else:
		return False

# Extracts typos from old & new sentence version and writes them into the stream. Key idea -
# difference of old sentence's & new sentence's word's sets gives us set of words which has been changed.
# If we look through the new sentence's words for each this word and get the one with the least word
# distance lesser than typo treshold it might be the correction
def findTypos(oldSent, newSent, comment):
	if(not typoFilter[lang].search(comment)):
		return False
	oldBag = bagOfWords(oldSent, minWordLen=typoMinWordLen)
	newBag = bagOfWords(newSent, minWordLen=typoMinWordLen)
	difference = oldBag - newBag
	writed=False
	for word in difference:
		candidates = [(x, wordDistance(word, x)) for x in newBag]
		candidates = [(x, d) for (x, d) in candidates if d <= typoTreshold]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			typoOutputStream.write("%s -> %s\n" % (word, candidates[0][0]))
			writed=True
	return writed

# Extracts edits from old & new sentence version and writes them into the stream.
# Key idea - comment contains predefined words
def findEdits(oldSent, newSent, comment):
	if (not editFilter[lang].search(comment)):
		return False
	editOutputStream.write("%s\n%s\n%s\n\n" % (comment, oldSent, newSent))

# Processes and flushes buffer to disk
def writeCorpBuffer(comment):
	global corpBuffer
	if len(corpBuffer) > 0:
		for sentTuple in corpBuffer:		    
			founded = False
			founded = findWO(sentTuple[0], sentTuple[1], comment)
			if(not founded):
				founded = findTypos(sentTuple[0], sentTuple[1], comment)
			if(not founded):
				founded = findEdits(sentTuple[0], sentTuple[1], comment)
			if(not founded):
				otherOutputStream.write("%s\n%s\n%s\n\n" % (comment, sentTuple[0], sentTuple[1]))
		woOutputStream.flush()
		typoOutputStream.flush()
		editOutputStream.flush()
		otherOutputStream.flush()
		corpBuffer = []

# Processes sentence's stacks - old sentences are matched to sentences from new sentence's stack
def processStacks(oldStack, newStack):
	if(len(oldStack) == 0 or len(newStack) == 0):
		return
	while len(oldStack) > 0:
		oldSent = oldStack.popleft()
		candidates = [(x, sentenceSimilarity(oldSent, x)) for x in newStack]
		candidates = [(x, similarity) for (x, similarity) in candidates if similarity > sentenceTreshold]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			corpBuffer.append((oldSent, candidates[0][0]))

# Compares two revisions and constructs old and new stacks of sentences for further processing
def processRevisions(oldRev, newRev):
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
	processStacks(oldStack, newStack)

# Function for removing bot or reverted revisions. TODO - bug - doesn't match all reverted revs
def removeBadRevisions(page):
	previous = None
	for rev in page.revisions:
		if(rev == None or rev.comment == None):
			try:
				page.revisions.remove(rev)
			except:
				pass
		elif(not preserveRobotRevisions):
			if(botFilter[lang].search(rev.comment)):
				try:
					page.revisions.remove(rev)
				except:
					pass
	for rev in page.revisions:
		if(revertFilter[lang].search(rev.comment)):
			try:
				page.revisions.remove(rev)
			except:
				pass
			try:
				page.revisions.remove(previous)
			except:
				pass
		previous = rev

# Removes reverted revisions, goes through revs and sends every two neighbous to processing
def processPage(page):
	removeBadRevisions(page)
	newRev = page.revisions[0]
	for i in range(1, len(page.revisions) - 1):
		oldRev = newRev
		newRev = page.revisions[i - 1]
		if(newRev.comment != None):
			processRevisions(oldRev, newRev)
		writeCorpBuffer(newRev.comment)

# Renders wiki markup into plain text via WikiExtractor and then cleans output text
def normalizeText(text, title):
	if(text != None):  
		out = io.StringIO()
		extractor = WikiExtractor.Extractor(0, 0, title, text.split("\n"))
		extractor.extract(out)
		text = out.getvalue()
		out.close()
		text = cleanUpText(text)
		text = splitBySentences(text)
		for i in range(0, len(text)):
			text[i] = cleanUpSentence(text[i], trimToSentenceStart=True)
		return text
	else:
		return ""

def processStream(fileStream):
	pool = Pool(processes=poolProcesses)
	pagesProcessed = 0    
	curPage = page()
	curRevision = revision()
	poolAsyncResults = []
	skip = False
	for event, elem in ET.iterparse(fileStream):
		if event == 'end':
			if elem.tag.endswith('title'):
				pagesProcessed += 1
				curPage.title = elem.text
				if(excludeFilter[lang].search(curPage.title)):
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
						poolAsyncResults.append(pool.apply_async(normalizeText, args=(elem.text,curPage.title)))
						#curRevision.text = normalizeText(elem.text, curPage.title)
				elif elem.tag.endswith('revision'):
					curPage.revisions.append(curRevision)
					curRevision = revision()
				elif elem.tag.endswith('page'):
					for i in range(0, len(poolAsyncResults) - 1):
						try:
							curPage.revisions[i].text = poolAsyncResults[i].get()	#collect results from pool
							curPage.revisions[i].format = "plaintext"
						except:
							curPage.revisions[i].text = None
					#pool.apply(processPage, args=(curPage,))
					processPage(curPage)
					curPage = page()
					curPage.revisions = []
					poolAsyncResults = []
			elem.clear()
    

def main():
	for path in dumpPaths:
		print("Processing file %s" % (path,))
		stream = openStream(path)
		processStream(stream)

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "p:d:u:l:o:hrf",
		                           ["paths=", "dumpUrls=", "pageUrls=" "lang=", "robots", "help", "outputFilter", "output="])
	except getopt.GetoptError:
		printUsage()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			printUsage()
			sys.exit()
		elif opt in ("-l", "--lang"):
			lang = arg
			if lang not in supportedLangs:
				print("%s language is not supported, switching to English", lang)
				lang = "en"	    
		elif opt in ("-r", "--robots"):
			preserveRobotRevisions = True
		elif opt in ("-f", "--outputFilter"):
			filterOutput = True
		elif opt in ("-p", "--paths"):
			dumpPaths = [x.strip() for x in arg.split(",")]
		elif opt in ("-d", "--dumpUrls"):
			dumpDownloads = [x.strip() for x in arg.split(",")]
		elif opt in ("-u", "--pageUrls"):
			pageDownloads = [x.strip() for x in arg.split(",")]
		elif opt in ("-o", "--output"):
			outputFolder = arg
	woOutputStream = io.open('export/wo.txt', 'w')
	typoOutputStream = io.open('export/typos.txt', 'w')
	editOutputStream = io.open('export/edit.txt', 'w')
	otherOutputStream = io.open('export/other.txt', 'w')    
	main()