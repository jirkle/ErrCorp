# coding=UTF-8
import difflib
import re
import Levenshtein
import Utils
from intervaltree import IntervalTree

class ErrorClassifier(object):
	errorType = "other"
	
	def __init__(self, newSent, oldSent, diff):
		self.oldSent = oldSent
		self.newSent = newSent
		self.diff = diff
		self.err = oldSent[diff[2]:diff[3]]
		self.corr = newSent[diff[0]:diff[1]]
		self.classify()
	
	def classify(self):
		if(self.__isPunct()):
			self.errorType = "punct"
		elif(self.__isTypographical()):
			self.errorType = "typographical"
		else:
			self.errBag = Utils.bagOfWords(self.err)
			self.corrBag = Utils.bagOfWords(self.corr)
			if(self.__isSpelling()):
				self.errorType = "spelling"
			elif(self.__isLexicoSemantic()):
				self.errorType = "lexicosemantic"
			elif(self.__isStylistic()):
				self.errorType = "style"
			else:
				self.errorType = "unclassified"
		return self.errorType
	
	def __isPunct(self):
		oldPunct = context["errCorpConfig"].reList["classifierpunctuation"].sub('', self.err)
		newPunct = context["errCorpConfig"].reList["classifierpunctuation"].sub('', self.corr)
		if(oldPunct == newPunct):
			return True
		else:
			return False

	def __isTypographical(self):
		oldPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.err).lower()
		newPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.corr).lower()
		if(oldPunct == newPunct):
			return True
		else:
			return False
	
	def __isSpelling(self):
		if(len(self.errBag) == len(self.corrBag)):
			if(Levenshtein.distance(self.err, self.corr) < context["typoTreshold"]):
				return True
		return False

	def __isLexicoSemantic(self):
		if((self.err == "" and len(self.corrBag) < context["wordTreshold"]) or (self.corr == "" and len(self.errBag) < context["wordTreshold"])):
			return True
		if((len(self.corrBag) >= len(self.errBag) and len(self.corrBag - self.errBag) <= 1) or (len(self.corrBag) < len(self.errBag) and len(self.errBag - self.corrBag) <= 1)):
			return True
		return False
	
	def __isStylistic(self):
		oldBag = Utils.bagOfWords(self.oldSent)
		newBag = Utils.bagOfWords(self.newSent)
		if(len(self.corrBag - oldBag) == 0):
			return True
		if(len(oldBag ^ newBag) < context["wordTreshold"]): 
			return True
		return False

	def getStart(self):
		return self.diff[0]
	
	def getEnd(self):
		return self.diff[1]
		
	def getStartString(self): 
		return "<err type=\""+ self.errorType + "\">" + self.err + "</err><corr>"
		
	def getEndString(self):
		return "</corr>"
	
	def getErrorType(self):
		return self.errorType
