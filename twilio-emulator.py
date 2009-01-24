#!/usr/bin/python

import sys
import urllib2
import urlparse
import readline
from xml.dom.minidom import parseString

def getResponse(url, method, digits):
    data = None

    if method == 'POST' and digits:
        data = "Digits=%s" % digits
    elif method == 'GET' and digits:
        purl = urlparse.urlparse(url)
        url = "%s?%s&Digits=%s" % ( purl.geturl(), purl.query , digits)
        
    print '[%s] %s \n%s' % (method, url, data)
    req = urllib2.Request(url, data)
    fd = urllib2.urlopen(req)
    return fd.read()

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
            
    digits = input("Digits Required %s> " % numDigits)
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

    print "[Say] %s" % node.childNodes[0].data

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
    if node.attributes.hasKey('length'):
        length = nodes.attributes['length'].value
    
    print "[Pause length=%s]" % length
    return None

def Dial(node):
    if not node.hasChildNodes():
        print "text node for <Play> not found."
        sys.exit(1)

    if len(node.childNodes) == 1 and \
            node.childNodes[0].nodeType == node.TEXT_NODE:
        print "[Dial] %s" % node.childNodes[0].data

    if node.hasChildNodes():
        print "[Dial with children]"
        [processNode(child) for child in node.childNodes]

    return None

def Number(node):
    if not node.hasChildNodes():
        print "text node for <Number> not found."
        sys.exit(1)

    print "[Number] %s" % node.childNodes[0].data

    return None

def Redirect(node):
    print "Redirecting"
    if len(node.childNodes) != 1:
        print "Redirect Syntax Error"
        sys.exit(1)

    request = { 
        'action' : node.childNodes[0].data, 
        'method' : 'GET',
        'digits' : None
        }

    return request

def processNode(node):
    action = node.nodeName.encode('ascii')
    print "processing node: %s" % action
    if node.nodeType == node.TEXT_NODE:
        print node.data
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
    
    rdoc = parseString(response)
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
            emulate(request['action'], 
                    request['method'], 
                    request['digits'])

    print '[Phone call ended]'

if len(sys.argv) > 1:
    emulate(sys.argv[1])
else:
    print "twilio-emulator.py [url]"
