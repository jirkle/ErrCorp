# coding=UTF-8
import re
import string
import Levenshtein

context = None

###############################################################################
#
#  Text processing functions
#   -tokenize, lemma, lemmaClean, bagOfWords, wordDistance,
#    sentenceSimilarity, textClean, sentenceClean, splitBySentences
#
###############################################################################

def lemmaClean(text):
	"""Clean before lemmatization -> removing digits"""
	
	return re.sub(r"[0-9]", r" ", text) #Remove digits

def lemma(text):
	"""Function for text lemmatization"""
	
	return lemmaClean(text) #No lemma just remove unnecessary chars

def bagOfWords(sentence, doLemma=True, minWordLen=0):
	"""Generates bag of words"""
	
	sentence = context["errCorpConfig"].reList["punctuation"].sub(' ', sentence)
	if(doLemma):
		sentence = lemma(sentence)
	words = sentence.split()
	words = [w for w in words if len(w) > minWordLen]
	return set(words)

def sentenceSimilarity(first, second):
	"""Metric for similarity of two given sentences, returns nuber in range <0,1> TODO: Levenstein?"""
	
	firstBag = bagOfWords(first)
	secndBag = bagOfWords(second)
	if(len(firstBag) == 0 or len(secndBag) == 0): return 0
	similarity = 2 * float(len(firstBag & secndBag))/(len(firstBag)+len(secndBag))
	return similarity

def ispunct(s):
	return all(c in string.punctuation for c in s)