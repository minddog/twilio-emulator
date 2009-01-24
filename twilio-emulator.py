#!/usr/bin/python

import sys, signal, os
import urllib2
import urlparse
import readline
from threading import Timer
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

class TwiMLSyntaxError(Exception):
    def __init__(self, lineno, col, doc):
        self.lineno = lineno
        self.col = col
        self.doc = doc
        self.line = self.doc.split("\n")[self.lineno-2]
        
    def __str__(self):
        return "TwiMLSyntaxError at line %i col %i near %s" \
            % (self.lineno, self.col, self.line)

def getResponse(url, method, digits):
    data = None

    if method == 'POST' and digits:
        data = "Digits=%s" % digits
    elif method == 'GET' and digits:
        purl = urlparse.urlparse(url)
        url = "%s?%s&Digits=%s" % \
            ( purl.geturl(), purl.query , digits)
        
    print '[%s] %s \n%s' % (method, url, data)
    try:
        req = urllib2.Request(url, data)
        fd = urllib2.urlopen(req)
    except IOError, e:
        print '[Not Found]', e
        sys.exit(1)

    return fd.read()

def end_pause():
    print "[End Pause]"
    return None

def input_timeout(*args):
    print "[Gather timed out]"

def exit_handler(*args):
    sys.stdout.flush()
    sys.exit(0)


def timed_input(prompt, timeout):
    signal.alarm(timeout)
    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        input = sys.stdin.readline()
    except KeyboardInterrupt, e:
        exit_handler()
    except IOError, e:
        input = None

    signal.alarm(0)
    return input

def Gather(node):
    # See Verb Attributes
    # Source: http://www.twilio.com/docs/api_reference/TwiML/gather
    numDigits = -1
    timeout = 5
    method = "POST"
    action = "#"
    finishOnKey = "#"
    if node.attributes.has_key('numDigits'):
        numDigits = node.attributes['numDigits'].value

    if node.attributes.has_key('timeout'):
        timeout = node.attributes['timeout'].value

    if node.attributes.has_key('method'):
        method = node.attributes['method'].value

    if node.attributes.has_key('action'):
        action = node.attributes['action'].value

    if node.attributes.has_key('finishOnKey'):
        finishOnkey = node.attributes['finishOnKey'].value

    if node.hasChildNodes():
        [processNode(child) for child in node.childNodes]
           
    prompt = "[Gather timeout=%s numDigits=%s]> " % \
                       (timeout,
                        numDigits)
                        
    digits = timed_input(prompt, int(timeout))
    if not digits:
        return None

    request = { 
        'action' : action, 
        'method' : method,
        'digits' : digits
        }

    return request

def Say(node):
    if not node.hasChildNodes():
        print "text node for <Say> not found."
        sys.exit(1)

    if len(node.childNodes) != 1:
        print "Multiple child nodes for say illegal"
        sys.exit(1)

    print "[Say] %s" % node.childNodes[0].data.strip()

    return None

def Play(node):
    if not node.hasChildNodes():
        print "text node for <Play> not found."
        sys.exit(1)

    if len(node.childNodes) != 1:
        print "Multiple child nodes for play illegal"
        sys.exit(1)
    
    print "[Play] %s" % node.childNodes[0].data

    return None

def Pause(node):
    length = 1
    if node.hasAttributes() and \
            node.attributes.has_key('length'):
        length = node.attributes['length'].value
    
    print "[Pause length=%s]" % length
    t = Timer(float(length), end_pause)
    t.start()
    return None

def Dial(node):
    if not node.hasChildNodes():
        print "text node for <Play> not found."
        sys.exit(1)

    if len(node.childNodes) == 1 and \
            node.childNodes[0].nodeType == node.TEXT_NODE:
        print "[Dial] %s" % node.childNodes[0].data.strip()
        return None

    print "[Dial with children]"
    [processNode(child) for child in node.childNodes]

    return None

def Number(node):
    if not node.hasChildNodes():
        print "text node for <Number> not found."
        sys.exit(1)

    print "[Number] %s" % node.childNodes[0].data.encode('ascii').strip()

    return None

def Redirect(node):
    if len(node.childNodes) != 1:
        print "Redirect Syntax Error"
        sys.exit(1)

    print "[Redirect] ", node.childNodes[0].data

    request = { 
        'action' : node.childNodes[0].data, 
        'method' : 'GET',
        'digits' : None
        }

    return request

def Record(node):
    action = ""
    method = "POST"
    timeout = 5
    finishOnKey = "123456789*#"
    maxLength = 3600

    if node.attributes.has_key('action'):
        action = node.attributes['action'].value

    if node.attributes.has_key('method'):
        method = node.attributes['method'].value

    if node.attributes.has_key('timeout'):
        timeout = node.attributes['timeout'].value

    if node.attributes.has_key('finishOnKey'):
        finishOnKey = node.attributes['finishOnKey'].value

    if node.attributes.has_key('maxLength'):
        maxLength = node.attributes['maxLength'].value

    prompt = "[Record maxLength=%s timeout=%s action=%s]" % \
        (maxLength, timeout, action)

    digits = timed_input(prompt, int(timeout))

    request = {
        'action' : action,
        'method' : method,
        'digits' : digits,
        }

    return request

def Hangup(node):
    print "[Hangup]"
    sys.exit(0)

def processNode(node):
    action = node.nodeName.encode('ascii')
    if node.nodeType == node.TEXT_NODE:
        print node.data.strip()
    else:
        return eval("%s(node)" % action)

    return None

def emulate(url, method = 'GET', digits = None):
    print '[Emulation Start] %s' % url
    response = getResponse(
        url,
        method,
        digits)
    if not response:
        print '[Emulation Failed to start]'
        sys.exit(1)
    
    try:
        rdoc = parseString(response)
    except ExpatError, e:
        raise TwiMLSyntaxError(e.lineno, e.offset, response)

    # finally:
        # exit_handler()

    try:
        respNode = rdoc.getElementsByTagName('Response')[0]
    except IndexError, e:
        print '[No response node] exiting'
        sys.exit(1)
    
    if not respNode.hasChildNodes():
        #hangup
        print 'Hanging up'
        sys.exit(0)
        
    nodes = respNode.childNodes
    for node in nodes:
        if node.nodeType == node.TEXT_NODE:
            # ignore
            pass
        if node.nodeType == node.ELEMENT_NODE:
            request = processNode(node)
            if not request:
                continue
            try:
                emulate(request['action'], 
                        request['method'], 
                        request['digits'])
            except TwiMLSyntaxError, e:
                print e
                exit_handler()

def main():
    signal.signal(signal.SIGALRM, input_timeout)
    signal.signal(signal.SIGINT, exit_handler)

    
    if len(sys.argv) > 1:
        try:
            emulate(sys.argv[1])
        except TwiMLSyntaxError, e:
            print e
            exit_handler()
        print '[Phone call ended]'
        
    else:
        print "twilio-emulator.py [url]"


if __name__ == "__main__":
    main()
