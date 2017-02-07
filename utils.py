# coding=UTF-8
import bz2
import lzma
import re
import string
import urllib.request

from UnicodeHack import hack_regexp

rePunctuation = re.compile('[%s]' % re.escape(string.punctuation))

###############################################################################
#
#  Support functions
#   -printUsage, openStream
#
###############################################################################

# Prints usage information
def printUsage():
	print('-h\t--help\t\tPrint help')
	print('-l\t--lang\t\tLang of processed dumps [cs|en]')
	print('-r\t--robots\tFlag: Include revisions made by bots')
	print('-f\t--outputFilter\tFlag: Additional SVM (support vector machines) filter at the output')
	print('Input:')
	print('-p\t--paths\t\tLocal paths to dump files [dumpPath(, dumpPath)*]')
	print('-d\t--dumpUrls\tRemote paths to dump files [dumpDownloadUrl(, dumpDownloadUrl)*]')
	print('-u\t--pageUrls\tUrl paths to pages [pageUrl(, pageUrl)*]')    
	print('Output:')
	print('-o\t--output\tOutput path')

# Opens compressed files (7z, bz2) & uncompressed xml
def openStream(path):
	if(path.lower().endswith('.bz2')):
		return bz2.BZ2File(path, "r")
	elif(path.lower().endswith('.xml')):
		return open(path, "r")
	elif(path.lower().endswith('.7z')):
		raise Exception('7zip files are not supported yet')
		#return lzma.open(path, "r")
	else:
		return None

# Downloads file from url
def downloadFile(url):
	fileName = url.split('/')[-1]
	print("Starting background downloading of %s" % url)
	urllib.request.urlretrieve(url, fileName)
	return fileName

###############################################################################
#
#  Text processing functions
#   -splitBySentences, lemma, bagOfWords, wordDistance, sentenceSimilarity,
#    cleanUpText, cleanUpSentence
#
###############################################################################
	
	
# Funkce z http://stackoverflow.com/questions/4576077/python-split-text-on-sentences, TODO: licence?
caps = hack_regexp(r"(\\p{Lu})")
prefixes = r"\s+(Mr|St|Mrs|Ms|Dr|MUDr|JuDr|Mgr|Bc|atd|tzv|řec|lat|it|např|př|vs|Et|tj)[.]"
suffixes = r"(Inc|Ltd|Jr|Sr|Co)"
starters = r"(Mr|Mrs|Ms|Dr|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = hack_regexp(r"(\\p{Lu}[.]\\p{Lu}[.](?:\\p{Lu}[.])?)")
websites = r"[.](com|net|org|io|gov|cz)\s"
digits = r"([0-9])"
digitsSentenceEndings = r"((roce|(z\slet)|(z\sroků))\s*[0-9\-\s]*)[.]"
decimalPoint = r"[.|,]"
	
def splitBySentences(text):
	if(text == None): return None
	text = " " + text + "  "
	text = text.replace("\n"," ")
	text = re.sub(prefixes," \\1<prd>",text)
	text = re.sub(websites,"<prd>\\1 ",text)
	text = text.replace("Ph.D.","Ph<prd>D<prd>")
	text = text.replace("n.l.","n<prd>l<prd>")
	text = text.replace("n. l.","n<prd> l<prd>")
	text = re.sub("\s" + caps + "[.] "," \\1<prd> ",text)
	text = re.sub(acronyms+" "+starters,"\\1<stop> \\2",text)
	text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
	text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>",text)
	text = re.sub(" "+suffixes+"[.] "+starters," \\1<stop> \\2",text)
	text = re.sub(" "+suffixes+"[.]"," \\1<prd>",text)
	text = re.sub(" " + caps + "[.]"," \\1<prd>",text)
	text = re.sub(digitsSentenceEndings,"\\1<stop>",text)
	text = re.sub(digits + decimalPoint + "\s*" + digits,"\\1<prd> \\2",text)
	text = re.sub(digits + "[\.]\s*", "\\1<prd> ",text)
	text = text.replace(".\"","\".")
	text = text.replace("!\"","\"!")
	text = text.replace("?\"","\"?")
	text = text.replace("\.*,","<prd>,")
	text = text.replace(".",".<stop>")
	text = text.replace("?","?<stop>")
	text = text.replace("!","!<stop>")
	text = text.replace("<prd>",".")
	sentences = re.split("<stop>", text, flags=re.MULTILINE)
	sentences = [s.strip() for s in sentences]
	return sentences

# Function for text lemmatization
def lemma(text):
	text = cleanUpSentence(text, True) #No lemma just remove unnecessary chars
	return text

# Generates bag of words
def bagOfWords(sentence, doLemma=True, minWordLen=0):
	sentence = rePunctuation.sub(' ', sentence)
	if(doLemma):
		sentence = lemma(sentence)
	words = sentence.split()
	words = [w for w in words if len(w) > minWordLen]
	return set(words)

# Func for distance metric (Levenshtein), used this impl: https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
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

# Metric for similarity of two given sentences, returns nuber in range <0,1>
def sentenceSimilarity(first, second):
	firstBag = bagOfWords(first)
	secndBag = bagOfWords(second)
	if(len(firstBag) == 0 or len(secndBag) == 0): return 0
	similarity = 2 * float(len(firstBag & secndBag))/(len(firstBag)+len(secndBag))
	return similarity

# Cleans up the text - removes rests from wiki markup, replaces special character (e.g. '…' -> '...', '„' -> '"')
def cleanUpText(text):
	text = re.sub(r"\/\*(.*?)\*\/", r"\1", text) #Replace comments
	text = re.sub(r"\[.*?\|(.*?)\]", r"\1", text) #Remove wiki interlinks
	text = re.sub(r"[‘’ʹ՚‛ʻʼ՝ʽʾ]", r"'", text) #Preserve only one type of single quotes
	text = re.sub(r"[„“˝”ˮ‟″‶〃＂“]", r'"', text) #Preserve only one type of double quotes
	text = re.sub(r"[‐‑‒−–⁃➖˗﹘-]", r"-", text) #Preserve only one type of hyphens
	
	#Mark headings to be start of sentences and preserve heading text
	text = re.sub(r"======(.*?)======", r". \1:", text)
	text = re.sub(r"=====(.*?)=====", r". \1:", text)
	text = re.sub(r"====(.*?)====", r". \1:", text) 
	text = re.sub(r"===(.*?)===", r". \1:", text)
	text = re.sub(r"==(.*?)==", r". \1:", text)
	text = re.sub(r"=", r" ", text) #Remove rest equal signs
	
	text = re.sub(r"\.\.\.", r"…", text) #Clean text
	text = re.sub(r"\s*\.(\s*\.)*", r". ", text) #Remove more dots
	text = re.sub(r"…", r"...", text) #Clean 	text
	
	text = re.sub(r"(\s+)", r" ", text) #Remove more spaces
	return text

# Cleans up the sentence
def cleanUpSentence(text, removeDigits=False, trimToSentenceStart=False):
	if(text == None):
		return None
	text = re.sub(r"^(\s*(\*)*\s*)", r" ", text, re.U) #Replace bullets at the start
	text = re.sub(r"([:,\.])(\s*(\*)*\s*)", r"\1 ", text, re.U) #Replace bullets at the start
	text = re.sub(r"\*", r"; ", text, re.U) #Replace bullets
	text = re.sub(r"\s*;(\s*;)*", r";", text, re.U) #Remove more semi-colons
	text = re.sub(r"([:;.,-])+\s*[:;.,-]+", r"\1 ", text, re.U) #Remove odd punctuation combinations
	
	text = re.sub(r"\'(\s*\')*", r"'", text, re.U) #Remove more single quotes
	text = re.sub(r"\"(\s*\")*", r'"', text, re.U) #Remove more double quotes
	text = re.sub(r"\s*,(\s*,)*\s*", r", ", text, re.U) #Remove more commas
	text = re.sub(r"\s*:(\s*:)*\s*", r": ", text, re.U) #Remove more colons
	text = re.sub(r"-(\s*-)*", r"-", text, re.U) #Remove more hyphens
		
	text = re.sub(r"[\[\]]", r" ", text) #Clean rest brackets
	
	text = re.sub(r"([\(\{\[])\s*", r"\1", text, re.U) #Remove spaces after starting brackets
	text = re.sub(r"\s*([\)\}\]])", r"\1", text, re.U) #Remove spaces before closing brackets	
    
	if(trimToSentenceStart):
		text = re.subn(hack_regexp(r"^.*?(\\p{Lu}|[\"\'])"), r"\1", text, re.U)
		if(text[1] == 0):
			text = ""
		else:
			text = text[0]
	if(removeDigits):
		text = re.sub(r"[0-9]", r" ", text) #Remove digits
	text = re.sub(r"(\s+)", r" ",text, re.M) #Remove more spaces
	return text.strip()