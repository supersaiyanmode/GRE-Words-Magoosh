WORDS_TXT = 'Words.txt'
JSON_FILE = 'process.dict'
OUT_HTML = 'out.html'

DIFFICULT_COLOR = 'orange'
EASY_COLOR = 'white'



import urllib
import urllib2
from collections import defaultdict
from collections import OrderedDict
import json
import sys
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
			content = self.extractHtml(urllib.urlopen(url).read())
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
		<span id='word-%s' style='background-color: %s'>
			<a href='#' onclick=\"toggleDiv('%s'); return false\">%s</a>
		</span>
	"""
	DESC_HTML = """
		<div id='%s' class='explanation' style='display:none'>
		%s
		<a href='javascript:void(0)' onclick='mark(\"%s\"); return false;'>
			MARK
		</a>
	</div>
	"""
	
	def __init__(self, category, text, retrieveFn):
		self.isDifficult = text.strip().endswith("*")
		self.word = text.rstrip("*")
		self.category = category
		self.description = retrieveFn(category, self.word)
	
	def wordHtml(self):
		params = (self.word, [EASY_COLOR,DIFFICULT_COLOR][self.isDifficult],
				self.word, self.word)
		return self.WORD_HTML%params
	
	def descriptionHtml(self):
		params = (self.word, self.description, self.word)
		return self.DESC_HTML%params

class Deck(object):
	def __init__(self, fileName):
		self.fileName = fileName
		self.map = self.load(self.fileName)
	
	def html(self):
		return "".join([
			"<h3>%s</h3>"%title + "".join([
				x.wordHtml()+x.descriptionHtml()+["<br>",""][bool((index+1)%10)]
				for index, x in enumerate(words)
			])
			for title, words in self.map.items()
		])
	
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

def regenerate():
	deck = Deck('Words.txt')
	
	with open(OUT_HTML, 'w') as out:
		print>>out, "<html><body>"
		print>>out, deck.html().encode('utf-8')
		print>>out, """
		<script>
		function toggleDiv(id) {
			var state = document.getElementById(id).style.display;
			Array.prototype.forEach.call(document.getElementsByClassName('explanation'), function(elem) {
				elem.style.display = 'none';
			});
			if (state == 'block')
				document.getElementById(id).style.display = 'none';
			else
				document.getElementById(id).style.display = 'block';
		}
		
		function mark(id) {
			var xhr = new XMLHttpRequest();
			xhr.onreadystatechange = function() {
				if (xhr.readyState == 4) {
					obj = JSON.parse(xhr.responseText);
					document.getElementById('word-' + id).style.backgroundColor = (obj.marked == true)? "orange": "white";
				}
			}
			xhr.open('POST', '/mark/' + id, true);
			xhr.send(null);
		}
		</script>
		</body>
		"""
		print>>out, "</html>"

def serve(port):
	class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
		def do_POST(self):
			word = self.path[self.path.index("mark/") + len("mark/"):]
			print "Word: ", word
			marked = None
			with open(WORDS_TXT) as f:
				lines = list(x.strip() for x in f)
			with open(WORDS_TXT, "w") as f:
				for line in lines:
					if word in line:
						if word + "*" in line:
							print>>f, line.replace(word + "*", word)
							marked = False
						elif word in line:
							print>>f, line.replace(word, word + "*")
							marked = True
						else:
							print>>f, line
					else:
						print>>f, line
			regenerate()
			self.send_response(200)
			self.end_headers()
			self.wfile.write(json.dumps({"marked": marked}))
			
		def do_GET(self):
			self.send_response(200)
			self.end_headers()
			with open(OUT_HTML) as f:
				self.wfile.write(f.read())
			self.wfile.close()
	
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
