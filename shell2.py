#! /usr/bin/env python3

import os, sys, re

redirect ={'inTokens': False, 'fileDescriptor': None, 'file': None, 'previousFD': None}
pipe = {
    'inTokens': False,
    'split': 0,
    'pr': None,
    'pw': None,
    'stdIn': os.dup(0),
    'stdOut': os.dup(1)
    'cmd1': None,
    'cmd2': None
}
backgroundProcess = False

def executeCommand(tokens, fullPath):
    if not fullPath:
        for dir in re.split(':', os.environ['PATH']):
            program = "%s/%s" % (dir, tokens[0])
            try:
                os.execve(program, tokens, os.environ)
            except FileNotFoundError:
                pass
        os.write(2, ("%s Cannot be found\n" % tokens[0]).encode())
        sys.exit(0)
    else:
        try:
            os.execve(tokens[0], tokens, os.environ)
        except FileNotFoundError:
            pass
        os.write(2, ('%s Cannot be found\n' % tokens[0]).encode())
        sys.exit(0)
                
def resetRedirection():
    os.dup2(redirect['previousFD'], redirect['fileDescriptor'])
    os.close(redirect['previousFD'])
    redirect['inTokens'] = False
    redirect['fileDescriptor'] = None
    redirect['file'] = None
    redirect['previousFD'] = None

def handleRedirection(redirect):
    os.close(redirect['fileDescriptor'])
    os.open(tokens[len(tokens)-1], redirect['file'])
    os.set_inheritable(redirect['fileDescriptor'], True)
    return tokens[:len(tokens)-1]

def getTokens(userInput):
    line = re.split(b'\s', userInput)
    fullPath = re.search('/', line[0].decode())
    tokens = []
    counter = 0
    
    for token in line:
        if token == b'>':
            redirect['inTokens'] = True
            redirect['fileDescriptor'] = 1
            redirect['file'] = os.O_CREAT | os.O_WRONLY
            redirect['previousFD'] = os.dup(1)
            token = b''
        elif token == b'<':
            redirect['inTokens'] = True
            redirect['fileDescriptor'] = 0
            redirect['file'] = os.O_RDONLY
            redirect['previousFD'] = os.dup(0)
            token = b''
        elif token == b'|':
            pipe['pr'], pipe['pw'] = os.pipe()
            os.set_inheritable(pipe['pr'], True)
            os.set_inheritable(pipe['pw'], True)
            pipe['inTokens'] = True
            pipe['split'] = counter
        elif token == b'&':
            backgroundProcess = True
            token = b''
        tokens.append(token.decode()) if token != b'' else None
        counter += 1

    if len(tokens) == 1 and tokens[0] == 'exit': sys.exit(0)
    if len(tokens) == 2 and tokens[0] == 'cd':
        try:
            os.chdir(tokens[1])
            tokens = []
            fullPath = None
        except:
            os.write(2, 'Path not found'.encode())
        finally:
            return None, None
    
    return tokens, fullPath
        

def shell():
    #prompt = os.environ['PS1'] if os.environ['PS1'] != '' else '$ '
    prompt = '$ '
    
    os.write(1, prompt.encode())
    userInput = os.read(0, 1024)

    return getTokens(userInput)

tokens, fullPath = shell()
while True:
    rc = os.fork()
    if rc < 0:
        os.write(stdErrorDisplay, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)
    elif rc == 0: # child1
        if redirect['inTokens']: tokens = handleRedirection(redirect)
        if pipe['inTokens']:
            if pipe['instruction']:
                os.dup2(pipe['pw'], 1)
                for fd in range(0, pipe['pw']+1):
                    if fd != 1: os.close(fd)
                os.execve('/usr/bin/ls', [' '], os.environ)
        if tokens: executeCommand(tokens, fullPath)
        sys.exit(0)
    else:
        exitCode = os.wait()
        if redirect['inTokens']: resetRedirection()
        if exitCode[1] != 0: os.write(1, ('Program Terminated with exit code: %d\n' % exitCode[1]).encode())
        tokens, fullPath = shell()
