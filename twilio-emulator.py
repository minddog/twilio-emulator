#!/usr/bin/python

import sys, signal, os
import urllib, urllib2
import urlparse
import readline
from StringIO import StringIO
from threading import Timer
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from optparse import OptionParser
from datetime import datetime

class TwiMLSyntaxError(Exception):
    def __init__(self, lineno, col, doc):
        self.lineno = lineno
        self.col = col
        self.doc = doc
        self.line = self.doc.split("\n")[self.lineno-2]
        
    def __str__(self):
        return "TwiMLSyntaxError at line %i col %i near %s" \
            % (self.lineno, self.col, self.line)

class ResponseLogger(object):
    def __init__(self, level=0, verbose=False, filename=None):
        if not filename:
            filename = "%s-twilio-log" % datetime.now()
        self.buf = StringIO()
        self.level = level
        self.verbose = verbose
        self.filename = filename
        self.WARN_LEVEL = 2
        self.NOTICE_LEVEL = 4
        self.ERROR_LEVEL = 0
        self.OUTPUT_LEVEL = 0
    def __str__(self):
        return self.buf.getvalue()

    def log(self, log_level, str):
        if(self.level > log_level):
            self.write(str)

    def warn(self, str):
        self.log(self.WARN_LEVEL, str)

    def notice(self, str):
        self.log(self.NOTICE_LEVEL, str)

    def error(self, str):
        self.log(self.ERROR_LEVEL, str)

    def output(self, str):
        self.log(self.OUTPUT_LEVEL, str)

    def write(self, str):
        self.buf.write("[%s] %s\n" % (datetime.now(), str))
        if self.verbose:
            print str
        
    def to_file(self):
        f = open(self.filename, "w+")
        f.write(str(self))
        f.close()

def getResponse(url, method, digits):
    data = None

    if method == 'POST' and digits:
        data = urllib.urlencode( {'Digits' :  digits} )
    elif method == 'GET' and digits:
        purl = urlparse.urlparse(url)
        url = "%s?%s&%s" % \
            ( purl.geturl(), 
              purl.query , 
              urllib.urlencode(
                {'Digits': digits}
                )
              )
        
    logger.notice('[%s] %s \n%s' % (method, url, data))

    try:
        req = urllib2.Request(url, data)
        fd = urllib2.urlopen(req)
    except IOError, e:
        logger.error('[Not Found] %s' % e)
        exit_handler()

    return fd.read()

def end_pause():
    logger.notice("[End Pause]")
    return None

def input_timeout(*args):
    print
    logger.notice("[Gather timed out]")
    
def exit_handler(*args):
    logger.to_file()
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
    action = ""
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
        logger.error("text node for <Say> not found.")
        exit_handler()

    if len(node.childNodes) != 1:
        logger.error("Multiple child nodes for say illegal")
        exit_handler()

    logger.output("[Say] %s" % node.childNodes[0].data.strip())

    return None

def Play(node):
    if not node.hasChildNodes():
        logger.error("text node for <Play> not found.")
        exit_handler()

    if len(node.childNodes) != 1:
        logger.error("Multiple child nodes for play illegal")
        exit_handler()
    
    logger.output("[Play] %s" % node.childNodes[0].data)

    return None

def Pause(node):
    length = 1
    if node.hasAttributes() and \
            node.attributes.has_key('length'):
        length = node.attributes['length'].value
    
    logger.output("[Pause length=%s]" % length)
    t = Timer(float(length), end_pause)
    t.start()
    return None

def Dial(node):
    if not node.hasChildNodes():
        logger.error("text node for <Play> not found.")
        exit_handler()

    if len(node.childNodes) == 1 and \
            node.childNodes[0].nodeType == node.TEXT_NODE:
        logger.notice("[Dial] %s" % node.childNodes[0].data.strip())
        return None

    logger.notice("[Dial with children]")
    [processNode(child) for child in node.childNodes]

    return None

def Number(node):
    if not node.hasChildNodes():
        logger.error("text node for <Number> not found.")
        exit_handler()

    logger.output("[Number] %s" % node.childNodes[0].data.encode('ascii').strip())

    return None

def Redirect(node):
    if len(node.childNodes) != 1:
        logger.error("Redirect Syntax Error")
        exit_handler()

    logger.notice("[Redirect] %s" % node.childNodes[0].data)

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
    logger.output("[Hangup]")
    exit_handler()
    
def processNode(node):
    action = node.nodeName.encode('ascii')
    if node.nodeType == node.TEXT_NODE:
        logger.output(node.data.strip())
    else:
        return eval("%s(node)" % action)

    return None

def emulate(url, method = 'GET', digits = None):
    logger.notice('[Emulation Start] %s' % url)
    response = getResponse(
        url,
        method,
        digits)
    if not response:
        logger.error('[Emulation Failed to start]')
        exit_handler()
    
    try:
        rdoc = parseString(response)
    except ExpatError, e:
        raise TwiMLSyntaxError(e.lineno, e.offset, response)

    try:
        respNode = rdoc.getElementsByTagName('Response')[0]
    except IndexError, e:
        logger.error('[No response node] exiting')
        exit_handler()
    
    if not respNode.hasChildNodes():
        #hangup
        logger.notice('Hanging up')
        exit_handler()
        
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
                if(request['action'] == ''):
                    request['action'] = url
                emulate(request['action'], 
                        request['method'], 
                        request['digits'])
            except TwiMLSyntaxError, e:
                logger.error(e)
                exit_handler()

def main():
    signal.signal(signal.SIGALRM, input_timeout)
    signal.signal(signal.SIGINT, exit_handler)
    
    usage = "usage: %prog [options] [url]"
    parser = OptionParser(usage)
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose",
                      help="Display notices")
    parser.add_option("-o", "--log-output",
                      action="store", dest="filename",
                      help="Where to store log of phone call")
    (options, args) = parser.parse_args(sys.argv)

    if len(args) != 2:
        parser.print_help()
        exit_handler()

    if options.verbose:
        logger.level = 5

    if options.filename:
        logger.filename = options.filename

    url = args[1]
    try:
        emulate(url)
    except TwiMLSyntaxError, e:
        logger.error(e)
        exit_handler()
    logger.notice('[Phone call ended]')

logger = ResponseLogger(1, True)
if __name__ == "__main__":
    main()
