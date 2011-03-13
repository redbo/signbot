#!/usr/bin/env python
#python signbot.py redbo.mooo.com 8887

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.web.client import getPage
from protocol import SignProtocol
import time, re, socket, sys, os, htmlentitydefs, traceback

def decode_entities(string):
    questionify = lambda char: (char < 0 or char > 127) and '?' or chr(char)
    def decode_entity(match):
        entity = match.group(1)
        if entity in htmlentitydefs.name2codepoint:
            return questionify(htmlentitydefs.name2codepoint[entity])
        elif entity.startswith('#') and entity[1:].isdigit():
            return questionify(int(entity[1:]))
    return re.sub(r'&([^;\s]+);', decode_entity, string)

class SignControl(DatagramProtocol, SignProtocol):
    def __init__(self, host, port = 8887, group_addr = 1, unit_addr = 1):
        SignProtocol.__init__(self, group_addr, unit_addr)
        self.host = host
        self.port = port
        self.frame_count = 1
        self.updates = {
            #0: '{m4}OH HAI!',
            0: '{0}{r}{ma} {dd}  {g}{12}'
        }

    def send_to_sign(self, data):
        if self.transport:
            self.transport.write(data)
            time.sleep(0.3)

    def startProtocol(self):
        ip = socket.gethostbyname(self.host)
        print "Connecting to %s:%d" % (ip, self.port)
        self.transport.connect(ip, self.port)
        self.transport.reactor.callLater(3600, self.connectionRefused)
        #self.frame_count = 8
        #LoopingCall(self._update_stock, 4, '^DJI', 'DOW').start(600)
        #LoopingCall(self._update_news, 5, 6, 7).start(600)
        #LoopingCall(self._update_weather, 2, 3).start(600) #san antonio
        LoopingCall(self._update_sign).start(180)

    def connectionRefused(self):
        pass
        #self.transport.reactor.stop()

    def _update_stock(self, node, symbol, name):
        def update_stock(page_text):
            try:
                (value, change, volume) = page_text.split(',')
                if change.startswith('-'):
                    change = '{r}%d' % int(float(change))
                else:
                    change = '{g}+%d' % int(float(change))
                value = str(int(float(value)))
                self.updates[node] = '{0}{r}%s{y}: %s %s' % (name, value, change)
            except:
                traceback.print_exc()
        getPage('http://quote.yahoo.com/d/quotes.csv?s=%s&f=l1c1v' % symbol).addCallback(update_stock)

    def _update_news(self, node1, node2, node3):
        def update_news(page_text):
            try:
                matches = [re.sub('<.*?>', '', m).strip() for m in re.findall('<h2>(.*?)</h2>', page_text, re.S)]
                if len(matches) >= 3:
                    self.updates[node1] = '{r}News{y}: ' + decode_entities(matches[0])
                    self.updates[node2] = '{r}News{y}: ' + decode_entities(matches[1])
                    self.updates[node3] = '{r}News{y}: ' + decode_entities(matches[2])
            except:
                traceback.print_exc()
        getPage('http://news.yahoo.com/').addCallback(update_news)

    def _update_weather(self, node1, node2):
        try:
            def update_weather(page_text):
                temp = re.search(r'<div id="yw-temp">(\w*)', page_text, re.S).group(1).strip()
                description = re.search('<div id="yw-cond">(.+?)</div>', page_text, re.S).group(1).strip()
                self.updates[node1] = '{r}Currently{y}: %s, %s\x80' % (description, temp)
                high = re.search('High: (\d+)', page_text, re.S).group(1).strip()
                low = re.search('Low: (\d+)', page_text, re.S).group(1).strip()
                self.updates[node2] = '{0}{r}Low:{y}%s\x80{r} Hi:{y}%s\x80' % (low, high)
        except:
            traceback.print_exc()
        getPage('http://weather.yahoo.com/united-states/texas/san-antonio-12792005/').addCallback(update_weather)

    def _update_sign(self):
        self.test_reset()
        self.pause()
        self.time_sync()
        self.set_frame_count(self.frame_count)
        for node, text in self.updates.items():
            self.set_text(node, text, typeset=False)
        self.resume()

if __name__ == '__main__':
    os.putenv('TZ', 'America/Chicago')
    if len(sys.argv) == 3:
        sign = SignControl(sys.argv[1], int(sys.argv[2]))
        reactor.listenUDP(0, sign, interface='0.0.0.0')
        reactor.run()
        time.sleep(5)
        print "restarting..."
        os.execlp(sys.executable, 'python', *sys.argv)
    else:
        print "%s [host] [port]" % sys.argv[0]

