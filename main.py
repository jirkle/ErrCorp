# coding=UTF-8
import sys
import os
import bz2
import xml.etree.ElementTree as ET
import re
import difflib
import time
import WikiExtractor
import io
import StringIO
import string
from multiprocessing import Pool
from collections import deque

#Czech excluded pages
excludeFilter = r".*((Hlavní\sstrana)|(Main\sPage)|([rR]ozcestník)|(Nápověda\:)|(Wikipedista\:)|(Wikipedie\:)|(Diskuse\:)|(MediaWiki\:)|(Portál\:)|(Šablona\:)|(Kategorie\:)).*"

#Comment filters
typoFilter = ur".*(([Tt]ypo)|([Cc]l[\s\:])|([Cc]leanup)|([Cc]u[\s\:])|([Pp]řeklep)|([Pp]ravopis)|([Kk]osmetické)|([Dd]robnost)|([Oo]prav)|([Oo]pr\s)|(\-\>)).*"
editFilter = ur".*(([Cc]opyedit)|([Cc]pyed)|([Cc]e[\s\:])|([Ee]dit)|([Pp]řepsání)|([Tt]ypografie)|([Rr]evize)).*"
revertFilter = ur"(.*(([Rr]evert)|([Rr]vrt)|([Rr]v[\s\:])|(rvv)|([Ee]ditace\s([0-9]\s)*uživatele)|(vrácen)|(zrušen)|(vandal)|([Vv]erze\s([0-9]\s)*uživatele)).*)|(rv)"

#Maximal distance of two words to be considered as typo
typoTreshold = 2
#Minimal length of word for typo matching
typoMinWordLen = 4

#Minimal treshold that should old & new sentences from revision diff have to be considered as two similar sentences. Similarity is returned by sentenceSimilarity function.
sentenceTreshold = 0.7

#Multiprocessing - Pool processes count
poolProcesses = 8

#Count of WikiPages
pagesCount = 372696

woOutputStream = io.open('wo.txt', 'wb')
typoOutputStream = io.open('typos.txt', 'wb')
editOutputStream = io.open('edit.txt', 'wb')
otherOutputStream = io.open('other.txt', 'wb')
corpBuffer = []

class page:
    title = "Some interesting title"
    revisions = []
    def __init__(self):
	title = ""
	revisions = []

class revision:
	timestamp = "Long long time ago"
	comment = "Wonderfull improvements of content"
	text = "To be or not to be, that is the question!"
	
	def __init__(self):
	    self.timestamp = ""
	    self.comment = ""
	    self.text = ""

###############################################################################
#
#  Utility functions
#
###############################################################################


#Funkce z http://stackoverflow.com/questions/4576077/python-split-text-on-sentences, TODO: licence?
caps = "([A-Z])"
prefixes = "(Mr|St|Mrs|Ms|Dr|MUDr|JuDr|Mgr|Bc|atd|tzv|řec|lat|it|např|př)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|cz)"
digits = "([0-9])"
decimalPoint = "[.|,]"

def splitBySentences(text):
	if(text == None): return None
	text = " " + text + "  "
	text = text.replace("\n"," ")
	text = re.sub(prefixes,"\\1<prd>",text)
	text = re.sub(websites,"<prd>\\1",text)
	if "Ph.D" in text: text = text.replace("Ph.D.","Ph<prd>D<prd>")
	if "n.l" in text: text = text.replace("n.l.","n<prd>l<prd>")
	if "n. l" in text: text = text.replace("n. l.","n<prd> l<prd>")
	text = re.sub("\s" + caps + "[.] "," \\1<prd> ",text)
	text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
	text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
	text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>",text)
	text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
	text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
	text = re.sub(" " + caps + "[.]"," \\1<prd>",text)
	text = re.sub(digits + decimalPoint + digits,"\\1<prd>\\2",text)
	text = re.sub(digits + "[\.]", "\\1<prd>",text)
	if "”" in text: text = text.replace(".”","”.")
	if "\"" in text: text = text.replace(".\"","\".")
	if "!" in text: text = text.replace("!\"","\"!")
	if "?" in text: text = text.replace("?\"","\"?")
	text = text.replace(".",".<stop>")
	text = text.replace("?","?<stop>")
	text = text.replace("!","!<stop>")
	text = text.replace("<prd>",".")
	sentences = text.split("<stop>")
	sentences = sentences[:-1]
	sentences = [s.strip() for s in sentences]
	return sentences

'''Function for text lemmatization'''
def lemma(text):
    text = cleanUp(text, True, True).decode('utf-8','ignore').encode("utf-8") #No lemma just remove unnecessary chars
    return text

'''Generates bag of words'''
def bagOfWords(sentence, doLemma=True, minWordLen=0):
	if(doLemma):
		sentence = lemma(sentence)
	words = re.split("\s", sentence, flags=re.MULTILINE)
	words = [w for w in words if len(w) > minWordLen]
	return set(words)

'''Func for distance metric (Levenshtein), used this impl: https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python'''
def wordDistance(s1, s2):
    if len(s1) < len(s2):
        return wordDistance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]



'''Generates num <0,1> which represents similarity of two given sentences'''
def sentenceSimilarity(first, second):
	firstBag = bagOfWords(first)

	secndBag = bagOfWords(second)
	if(len(firstBag) == 0 or len(secndBag) == 0): return 0
	similarity = 2 * float(len(firstBag & secndBag))/(len(firstBag)+len(secndBag))
	return similarity

def cleanUp(text, removeDigits=False, removePunctuation=False):
    #text = re.sub("[(\\br)]"," ",text) #Clean text
    text = re.sub("===.*?===","",text) #Remove headings
    text = re.sub("==.*?==","",text) #Remove headings
    text = re.sub("=","",text) #Remove rest equal signs
    text = re.sub("\*",", ",text) #Replace bullets
    text = re.sub("[„“]","\"",text) #Clean text
    text = re.sub("\"+","\"",text) #Remove more apostrophes
    text = re.sub("[…]","\.\.\.",text) #Clean text
    #text = re.sub("(\xc2\xa0)"," ",text) #Clean text
    text = re.sub("\[.*?\|(.*?)\]","\\1 ",text) #Clean text
    text = re.sub("[\[\]]","",text) #Clean text
    text = re.sub("(\s+)"," ",text) #Remove more spaces
    if(removeDigits):
	text = re.sub("[0-9]"," ",text) #Remove more spaces
    if(removePunctuation):
	text = ''.join([i for i in text if (i not in string.punctuation)])
    return text


###############################################################################
#
#  Extractor functions
#
###############################################################################

def findTypos(oldSent, newSent, comment):
    if(not re.search(typoFilter, comment, re.M)):
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

def findWO(oldSent, newSent, comment):
    oldBag = bagOfWords(cleanUp(oldSent, True))
    newBag = bagOfWords(cleanUp(newSent, True))    
    if(oldBag - newBag == 0):
	woOutputStream.write("%s\n%s\n%s\n\n" % (comment.encode("utf-8"), oldSent, newSent))
	return True
    else:
	return False

def findEdits(oldSent, newSent, comment):
    if (not re.search(editFilter, comment, re.M)):
	return False
    editOutputStream.write("%s\n%s\n%s\n\n" % (comment.encode("utf-8"), oldSent, newSent))

def writeToCorpBuffer(oldSent, newSent):
	global corpBuffer
	corpBuffer.append((oldSent, newSent))

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
			otherOutputStream.write("%s\n%s\n%s\n\n" % (comment.encode("utf-8"), sentTuple[0], sentTuple[1]))
		woOutputStream.flush()
		typoOutputStream.flush()
		editOutputStream.flush()
		otherOutputStream.flush()
		corpBuffer = []

def processStacks(oldStack, newStack):
	if(len(oldStack) == 0 or len(newStack) == 0):
		return
	while len(oldStack) > 0:
		oldSent = oldStack.popleft()
		candidates = [(x, sentenceSimilarity(oldSent, x)) for x in newStack]
		candidates = [(x, similarity) for (x, similarity) in candidates if similarity > sentenceTreshold]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			writeToCorpBuffer(oldSent, candidates[0][0])		

def processRevisions(oldRev, newRev):
	if(oldRev == None or newRev == None or oldRev.text == None or newRev.text == None):
		return
	oldStack = deque()
	newStack = deque()
	lastSymbol = ''
	for line in difflib.unified_diff(oldRev.text, newRev.text):
	    if line.startswith(' '): #Skip unnecessary output
		continue
	    elif line.startswith('---'):
		continue
	    elif line.startswith('+++'):
		continue
	    elif line.startswith('-'): #Write diff lines from old revision to stack
		if(lastSymbol == '+'):
		    processStacks(oldStack, newStack)
		    newStack = deque()
		    oldStack = deque()				
		oldStack.append(line[1:])
		lastSymbol = '-'
	    elif line.startswith('+'): #Write diff lines from new revision to stack
		lastSymbol = '+'
		newStack.append(line[1:])
	processStacks(oldStack, newStack)

def removeRevertedRevs(page):
    previous = None
    for rev in page.revisions:
	if(rev == None or rev.comment == None):
	    page.revisions.remove(rev)
	elif(re.search(revertFilter, cleanUp(rev.comment), re.U)):
	    try:
		page.revisions.remove(rev)
	    except:
		pass
	    try:
		page.revisions.remove(previous)
	    except:
		pass
	previous = rev

def processPage(page):
	#print("Zacinam zpracovavat stranku")
	removeRevertedRevs(page)
	newRev = page.revisions[0]
	for i in range(1, len(page.revisions) - 1):
		oldRev = newRev
		newRev = page.revisions[i - 1]
		if(newRev.comment != None):
		    processRevisions(oldRev, newRev)
		writeCorpBuffer(newRev.comment)
	#print("Koncim zpracovani stranky")
		

def normalizeText(text):
	if(text != None):  
		out = StringIO.StringIO()
		extractor = WikiExtractor.Extractor(0, "", text.split("\n"))
		extractor.extract(out)
		text = out.getvalue()
		out.close()
		text = cleanUp(text).decode('utf-8','ignore').encode("utf-8")
		text = splitBySentences(text)
		return text
	else:
		return ""

def decodeToUtf8(unicodeText):
	if(unicodeText == None): return None
	if(type(unicodeText) is str):
		return unicodeText.encode("utf-8", 'ignore')
	else:
		return unicodeText.encode("utf-8", 'ignore')

if __name__ == "__main__":
	pool = Pool(processes=poolProcesses)
	file = bz2.BZ2File("../cswiki.xml.bz2", "rb")
	pagesProcessed = 0
	curPage = page()
	curRevision = revision()
	poolAsyncResults = []
	skip = False
	for event, elem in ET.iterparse(file):
		if event == 'end':
			if elem.tag.endswith('title'):
			    pagesProcessed += 1
			    curPage.title = decodeToUtf8(elem.text)
			    if(re.search(excludeFilter, curPage.title, re.M)):
				print("Přeskakuji stránku  #%s: %s" % (pagesProcessed, curPage.title))
				skip = True
				continue
			    else:
				print("Zpracovávám stránku #%s: %s" % (pagesProcessed, curPage.title))
				skip = False
			if(not skip):
				if elem.tag.endswith('timestamp'):
					curRevision.timestamp = decodeToUtf8(elem.text)
				elif elem.tag.endswith('comment'):
					curRevision.comment = elem.text
				elif elem.tag.endswith('text'):
				    #try:
					#curRevision.text = normalizeText(elem.text)
				    poolAsyncResults.append(pool.apply_async(normalizeText, args=(elem.text,)))
				    #except:
				    #	curRevision.text = None
				elif elem.tag.endswith('revision'):
					curPage.revisions.append(curRevision)
					curRevision = revision()
				elif elem.tag.endswith('page'):
					for i in range(0, len(poolAsyncResults) - 1):
					    try:
						curPage.revisions[i].text = poolAsyncResults[i].get()	#collect results from pool
					    except:
						curPage.revisions[i].text = None
					#pool.apply(processPage, args=(curPage,))
					processPage(curPage)
					curPage = page()
					curPage.revisions = []
					poolAsyncResults = []
			elem.clear()