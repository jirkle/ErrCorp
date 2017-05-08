# coding=UTF-8
import Levenshtein
import Utils

context = None

class ErrorClassifier(object):
	errorType = "other"
	
	def __init__(self, newSent, oldSent, diff, comment):
		self.oldSent = oldSent
		self.newSent = newSent
		self.diff = diff
		self.err = oldSent[diff[2]:diff[3]]
		self.corr = newSent[diff[0]:diff[1]]
		self.comment = comment
		self.classify()
	
	def classify(self):
		if(self.__isPunct()):
			self.errorType = "punct"
		elif(self.__isTypographical_1()):
			self.errorType = "typographical"
		else:
			self.errBag = Utils.bagOfWords(self.err)
			self.corrBag = Utils.bagOfWords(self.corr)
			if(self.__isSpelling()):
				self.errorType = "spelling"
			elif(self.__isTypographical_2()):
				self.errorType = "typographical"			
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

	def __isTypographical_1(self):
		oldPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.err)
		newPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.corr)
		if(oldPunct == newPunct):
			return True
		else:
			return False
	
	def __isTypographical_2(self):
		oldPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.err).lower()
		newPunct = context["errCorpConfig"].reList["punctSpace"].sub('', self.corr).lower()
		if(oldPunct == newPunct):
			return True
		else:
			return False	
	
	def __isSpelling(self):
		if(self.err.lower() == self.corr.lower()):
			return True
		if(len(self.errBag) == len(self.corrBag)):
			if(Levenshtein.distance(self.err, self.corr) < context["typoTreshold"]):
				return True
		return False

	def __isLexicoSemantic(self):
		if(len(self.corrBag) >= len(self.errBag)):
			if(len(self.corrBag - self.errBag) <= context["wordTreshold"]):
				return True
		else:
			if(len(self.errBag - self.corrBag) <= context["wordTreshold"]):
				return True
		return False
	
	def __isStylistic(self):
		oldBag = Utils.bagOfWords(self.oldSent)
		newBag = Utils.bagOfWords(self.newSent)
		if(len(self.corrBag - oldBag) == 0):
			return True
		if(len(oldBag ^ newBag) <= 2 * context["wordTreshold"]): 
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
