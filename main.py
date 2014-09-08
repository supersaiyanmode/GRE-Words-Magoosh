WORDS_TXT = 'Words.txt'
OUT_HTML = 'out.html'
DIFFICULT_COLOR = 'orange'
EASY_COLOR = 'white'

import urllib
import urllib2
from collections import defaultdict
from collections import OrderedDict
import json
import sys
import atexit
import SocketServer
import BaseHTTPServer
import json

def readWords(fileName):
	dictionary = OrderedDict()
	difficultyDict = {}
	curSet = None
	with open(fileName) as f:
		for line in f:
			if not line.strip():
				continue
			line = line.strip()
			if line[0] == '#':
				curSet = set()
				dictionary[line[1:]] = curSet
				continue
			for word in line.split():
				word = word.strip()
				diff = word.endswith("*")
				word = word.rstrip("*")
				curSet.add(word)
				difficultyDict[word] = diff
	return dictionary, difficultyDict

def getWord(tag, word):
	print "Get:", tag, word
	url = 'https://gre.magoosh.com/flashcards/vocabulary/%s/%s'%(tag, word)
	content = urllib.urlopen(url).read()
	start = "<div class='back'>"
	content = content[content.index(start) + len(start):]
	end = "<div class='flashcard-actions'>"
	content = content[:content.index(end)]
	
	start = content.index('<div class="flashcard-review-label')
	end = start + content[start:].index('</div>') + "</div>"
	return content[:start] + content[end:]

processDict = {}

def loadProcessDict():
	with open("process.dict") as f:
		global processDict
		processDict = json.load(f)

def dumpProcessDict():
	with open("process.dict","w") as f:
		print>>f, json.dumps(processDict,indent=2)
		
def loadWords(d1):
	for tag, words in d1.items():
		for word in words:
			if word not in processDict:
				processDict[word] = getWord(tag,word)
			else:
				pass #print "Loaded from cache:", word
atexit.register(dumpProcessDict)


def getTemplate(word, desc, difficult):
	s0 = "<span id='word-%s' style='background-color: %s'>"%(word, DIFFICULT_COLOR if difficult else EASY_COLOR)
	s1 = "<a href='#' onclick=\"toggleDiv(\'%s\'); return false\">%s</a>"%(word, word)
	s2 = "</span>"
	s3 = "<div id='%s' class='explanation' style='display:none'>"%word + desc + "<a href='javascript:void(0)' onclick='mark(\"" + word + "\"); return false;'>MARK</a></div>"
	return s0 + s1 + s2 + s3

def regenerate():
	d1,diffDict = readWords('Words.txt')
	loadProcessDict()
	loadWords(d1)
	
	with open(OUT_HTML, 'w') as out:
		print>>out, "<html><body>"
		for tag, words in d1.items():
			print>>out, "<h3>%s</h3>"%tag
			for index, word in enumerate(words):
				diff = diffDict[word]
				try:
					desc = processDict.get(word,"").encode('utf-8')
				except:
					print word, processDict[word]
				print >> out, getTemplate(word, desc, diff)
				if (index+1) % 10 == 0:
					print >> out, "<br>"
		
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
