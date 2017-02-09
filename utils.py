# coding=UTF-8
import bz2
import lzma
import re
import string
import io
import urllib.request
import unitok

from UnicodeHack import hack_regexp

unitokConfig = None
errCorpConfig = None

caps = None
decimalPoint = None
digits = None
abbrs = None
websites = None
digitsSentenceEndings = None

def init():
	global caps
	global decimalPoint
	global digits
	global abbrs
	global websites
	global digitsSentenceEndings
	caps = errCorpConfig.caps
	decimalPoint = errCorpConfig.decimalPoint
	digits = errCorpConfig.digits
	abbrs = errCorpConfig.reList["abbrs"]
	websites = errCorpConfig.reList["websites"]
	digitsSentenceEndings = errCorpConfig.reList["digitsSentenceEndings"]	

###############################################################################
#
#  Text processing functions
#   -splitBySentences, lemma, bagOfWords, wordDistance, sentenceSimilarity,
#    textClean, sentenceClean
#
###############################################################################

def tokenize(text):
	out = io.StringIO()
	re_list = unitokConfig.re_list
	tokens = unitok.tokenize_recursively(text, re_list)
	unitok.print_tokens(tokens, out, True, False)
	text = out.getvalue()
	out.close()
	return text

# Function for text lemmatization
def lemma(text):
	return lemmaClean(text) #No lemma just remove unnecessary chars

# Generates bag of words
def bagOfWords(sentence, doLemma=True, minWordLen=0):
	sentence = errCorpConfig.reList["punctuation"].sub(' ', sentence)
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
def textClean(text):
	text = re.sub(r"&lt;", r"<", text) #Replace inline markup
	text = re.sub(r"&gt;", r">", text) #Replace inline markup
	
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
def sentenceClean(text, trimToSentenceStart=True, trimToSentenceEnd=True):
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
		text = re.subn(hack_regexp(r"^.*?(\\p{Lu}|\\p{Ll}|[\"\'])"), r"\1", text, re.U)
		if(text[1] == 0):
			text = ""
		else:
			text = text[0]
	text = re.sub(r"(\s+)", r" ",text, re.M) #Remove more spaces
	return text.strip()

def lemmaClean(text):
	return re.sub(r"[0-9]", r" ", text) #Remove digits	

# Funkce z http://stackoverflow.com/questions/4576077/python-split-text-on-sentences
def splitBySentences(rev, doClean=True):
	text = rev.text
	if(text == None): return None
	if(doClean): text = textClean(text)
	reList = errCorpConfig.reList
	
	
	text = " " + text + "  "
	text = text.replace("\n"," ")
	text = abbrs.sub(" \\1<prd>", text)
	text = websites.sub("<prd>",text)
	text = re.sub("\s" + caps + "[.] "," \\1<prd> ", text)
	text = re.sub(caps + "[.]" + caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>\\3<prd>",text)
	text = re.sub(caps + "[.]" + caps + "[.]","\\1<prd>\\2<prd>",text)
	text = re.sub(" " + caps + "[.]"," \\1<prd>",text)
	text = digitsSentenceEndings.sub("\\1<stop>",text)
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
	if(doClean): 
		for i in range(0, len(sentences)):
			sentences[i] = sentenceClean(sentences[i])
	rev.text = [x for x in sentences if x != ""]		
	return rev

###############################################################################
#
#  Support functions
#   -printUsage, openStream
#
###############################################################################

# Prints usage information
def printUsage():
	print('-h\t--help\t\tPrint help')
	print('-l\t--lang\t\tLang of processed dumps [czech|english]')
	print('-r\t--robots\tFlag: Include revisions made by bots')
	print('Input:')
	print('-p\t--paths\t\tLocal paths to dump files [dumpPath(, dumpPath)*]')
	print('-d\t--dumpUrls\tRemote paths to dump files [dumpDownloadUrl(, dumpDownloadUrl)*]')
	print('-u\t--pageUrls\tUrl paths to pages [pageUrl(, pageUrl)*]')    
	print('Output:')
	print('-o\t--output\tOutput path')
	print('-f\t--outputFormat\tOutput format [txt|se]')
	print('-F\t--outputFilter\tFlag: Additional SVM (support vector machines) filter at the output')

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

"""Recursion of error construction"""
def seConstructError(errors):
	if(len(errors) <= 1):
		return tokenize(errors[0][1])
	
	last = errors[-1]
	errContent = last[1]
	errType = last[0]
	
	return ("<err type=\"%s\">\n" % errType) + seConstructError(errors[:-1]) + ("\n</err>\n<corr type=\"%s\">\n%s\n</corr>" % (errType, tokenize(errContent)))

def writeStream(stream, errors, writeFormat="se"):
	if writeFormat == "se":
		for error in errors:
			output = seConstructError(error)
			stream.write(output)
			stream.write("\n")
		stream.flush()
	if writeFormat == "txt":
		for error in errors:
			stream.write("Komentáře editací: %s\nstart: %s\n" % (error[0][0], error[0][1]))
			for i in range(1, len(error)):
				stream.write("%s: %s\n" % (error[i][0], error[i][1]))
			stream.write("\n")
		stream.flush()
		
# Downloads file from url
def downloadFile(url):
	fileName = url.split('/')[-1]
	print("Starting background downloading of %s" % url)
	urllib.request.urlretrieve(url, fileName)
	return fileName