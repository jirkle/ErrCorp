# coding=UTF-8
import re
import string

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

def wordDistance(s1, s2):
	"""Func for distance metric (Levenshtein), used this impl:
	https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python"""
	
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

def sentenceSimilarity(first, second):
	"""Metric for similarity of two given sentences, returns nuber in range <0,1> TODO: Levenstein?"""
	
	firstBag = bagOfWords(first)
	secndBag = bagOfWords(second)
	if(len(firstBag) == 0 or len(secndBag) == 0): return 0
	similarity = 2 * float(len(firstBag & secndBag))/(len(firstBag)+len(secndBag))
	return similarity

def ispunct(s):
	return all(c in string.punctuation for c in s)