WORDS_TXT = 'Words.txt'
JSON_FILE = 'process.dict'
OUT_HTML = 'out.html'

DIFFICULT_CHAR = "!"
MEDIUM_CHAR = "*"
EASY_CHAR = ""

DIFFICULT_COLOR = 'orange'
MEDIUM_COLOR = 'yellow'
EASY_COLOR = 'gray'



import urllib
import urllib2
from collections import defaultdict
from collections import OrderedDict
import json
import sys
import random
import re
import SocketServer
import BaseHTTPServer
import json

class MagooshDataRetriever(object):
	URL = 'https://gre.magoosh.com/flashcards/vocabulary/%s/%s'
	
	def __init__(self, fileName):
		self.fileName = fileName
		self.map = self.loadMap(self.fileName)
		
	def retrieve(self, category, word):
		if word not in self.map:
			print "Get:", category, word
			content = self.extractHtml(urllib.urlopen(self.URL).read())
			self.map[word] = content
			self.saveMap(self.map, self.fileName)
		else:
			content = self.map[word]
		return content

	@staticmethod
	def extractHtml(content):
		start = "<div class='back'>"
		content = content[content.index(start) + len(start):]
		end = "<div class='flashcard-actions'>"
		content = content[:content.index(end)]
	
		start = content.index('<div class="flashcard-review-label')
		end = start + content[start:].index('</div>') + "</div>"
		return content[:start] + content[end:]
		
	@staticmethod
	def loadMap(fileName):
		with open(fileName) as f:
			return json.load(f)

	@staticmethod
	def saveMap(obj, fileName):
		with open(fileName, 'w') as f:
			json.dump(f, obj, indent=2)


class Word(object):
	WORD_HTML = """
		<span class='word-%s' style='background-color: %s'>
			<a href='#' onclick=\"toggleDiv('%s'); return false\">%s</a>
		</span>
	"""
	DESC_HTML = """
		<div id='%s' class='explanation explanation-%s' style='display:none'>
		%s
		<a href='javascript:void(0)' onclick='mark(\"%s\", 0); return false;'>
			Easy
		</a> |
		<a href='javascript:void(0)' onclick='mark(\"%s\", 1); return false;'>
			Medium
		</a> |
		<a href='javascript:void(0)' onclick='mark(\"%s\", 2); return false;'>
			Difficult
		</a>
	</div>
	"""
	
	def __init__(self, category, text, retrieveFn):
		self.isDifficult = text.strip().endswith(DIFFICULT_CHAR)
		self.isMedium = text.strip().endswith(MEDIUM_CHAR)
		self.word = text.rstrip(DIFFICULT_CHAR + MEDIUM_CHAR)
		self.category = category
		self.description = retrieveFn(category, self.word)
	
	def wordHtml(self):
		color = [
					[EASY_COLOR, MEDIUM_COLOR][self.isMedium],
					DIFFICULT_COLOR
				][self.isDifficult]
		return self.WORD_HTML%(self.word, color, self.word, self.word)
	
	def descriptionHtml(self):
		w, d = self.word, self.description
		params = (w,w,d,w,w,w)
		return self.DESC_HTML%params

class Deck(object):
	def __init__(self, fileName):
		self.fileName = fileName
		self.map = self.load(self.fileName)
	
	def html(self):
		dw = list(x for x in sum(self.map.values(), []) if x.isDifficult)
		mw = list(x for x in sum(self.map.values(), []) if x.isMedium)
		
		s = ("<h1>Difficult Words (%d)</h1>"%len(dw) +
			"".join(
				x.wordHtml()+x.descriptionHtml()+["<br>",""][bool((index+1)%10)]
				for index, x in enumerate(dw)
			) + 
			"<hr>")
		s = s + ("<h1>Medium level difficulty Words(%d)</h1>"%len(mw) +
			"".join(
				x.wordHtml()+x.descriptionHtml()+["<br>",""][bool((index+1)%10)]
				for index, x in enumerate(mw)
			) + "<hr>")
		s = s + ("<h1>All words</h1>" +
			"".join([
				"<h3>%s</h3>"%title + "".join(
					x.wordHtml()+x.descriptionHtml()+
					["<br>",""][bool((index+1)%10)]
					for index, x in enumerate(self.shuffle(words))
				)
				for title, words in self.map.items()
			])
		)
		return s
	
	@staticmethod
	def load(fileName):
		dictionary = OrderedDict()
		curTitle = None
		curGroup = None
		magoosh = MagooshDataRetriever(JSON_FILE)
		
		with open(fileName) as f:
			for line in f:
				if not line.strip():
					continue
				line = line.strip()
				if line[0] == '#':
					curGroup = []
					curTitle = line[1:].strip()
					dictionary[curTitle] = curGroup
					continue
				for word in line.split():
					word = word.strip()
					curGroup.append(Word(curTitle, word, magoosh.retrieve))
		return dictionary
	
	@staticmethod
	def shuffle(lst):
		random.shuffle(lst)
		return lst

def regenerate():
	deck = Deck('Words.txt')
	
	with open(OUT_HTML, 'w') as out:
		print>>out, "<html><body>"
		print>>out, deck.html().encode('utf-8')
		print>>out, "<script>"
		print>>out, 'var COLORS = ["%s", "%s", "%s"];'%(EASY_COLOR, MEDIUM_COLOR,
			 	DIFFICULT_COLOR)
		print>>out, """
		function toggleDiv(id) {
			var state = document.getElementById(id).style.display;
			Array.prototype.forEach.call(document.getElementsByClassName('explanation'), function(elem) {
				elem.style.display = 'none';
			});
			Array.prototype.forEach.call(document.getElementsByClassName('explanation-' + id), function(elem) {
				elem.style.display = state== 'block' ? 'none' : 'block';
			});
		}
		
		function mark(id, diffLevel) { //level = 1 for medium, 2 for difficult
			if ([0,1,2].indexOf(diffLevel) == -1)
				return;
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function() {
				if (xhr.readyState == 4) {
					obj = JSON.parse(xhr.responseText);
					if (obj.state >= 0) {
						Array.prototype.forEach.call(document.getElementsByClassName('word-' + id), function(x) {
							x.style.backgroundColor = COLORS[obj.state]
						})
					}
					
				}
			}
			xhr.open('POST', '/words/' + id, true);
			xhr.send(diffLevel + "");
		}
		</script>
		</body>
		"""
		print>>out, "</html>"

def serve(port):
	class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
		def do_POST(self):
			word = self.path[self.path.index("words/") + len("words/"):]
			print "Word: ", word
			state = int(self.rfile.read(1))
			result = state if self.updateState(word, state) else -1
			regenerate()
			self.send_response(200)
			self.end_headers()
			self.wfile.write(json.dumps({"state": result}))
			
		def do_GET(self):
			regenerate()
			self.send_response(200)
			self.end_headers()
			with open(OUT_HTML) as f:
				self.wfile.write(f.read())
			self.wfile.close()
		
		@staticmethod
		def updateState(word, state):
			updated = False
			with open(WORDS_TXT) as f:
				lines = list(x.strip() for x in f)
			with open(WORDS_TXT, "w") as f:
				for line in lines:
					if word in line:
						find = word + "[%s]?(?=(\\t|$))"%"".join([
							MEDIUM_CHAR, DIFFICULT_CHAR])
						replace = word + [EASY_CHAR, MEDIUM_CHAR,
									DIFFICULT_CHAR][state]
						newline = re.sub(find, replace, line)
						updated = updated or newline != line
						print>>f, newline
					else:
						print>>f, line
			return updated
	
	httpd = SocketServer.TCPServer(("", port), Handler)

	print "serving at port", port
	httpd.serve_forever()
	
def main():
	if len(sys.argv) > 1 and "-serve" == sys.argv[1]:
		serve(int(sys.argv[2]))
	else:
		print "Generating latest HTML"
		regenerate()
	
if __name__ == '__main__':
	main()
