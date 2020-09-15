#! /usr/bin/env python3

import os, sys, re

redirect ={'inTokens': False, 'fileDescriptor': None, 'file': None, 'previousFD': None}
pipe = {
    'inTokens': False,
    'split': 0,
    'pr': None,
    'pw': None,
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
            pipe['inTokens'] = True
            pipe['split'] = counter
            token = b''
        elif token == b'&':
            backgroundProcess = True
            token = b''
        tokens.append(token.decode()) if token != b'' else None
        counter += 1
    if pipe['inTokens']:
        pipe['cmd1'] = tokens[:pipe['split']]
        pipe['cmd2'] = tokens[pipe['split']:]
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

def createNewChild(tokens, fullPath, background):
    child = os.fork()
    if child < 0:
        os.write(2, "Error to fork Child".encode())
        sys.exit(1)
    elif child == 0:
        executeCommand(tokens, fullPath)
        sys.exit(0)
    else:
        if background:
            return
        else:
            os.wait()
def createPipe():
    pr, pw = os.pipe()
    stdIn = os.dup(0)
    stdOut = os.dup(1)

    os.dup2(pw, 1)
    childWriteProcess = createNewChild(pipe['cmd1'], fullPath, True)
    os.dup2(pr, 0)
    os.dup2(stdOut, 1)
    childInputProcess = createNewChild(pipe['cmd2'], fullPath, False)
    os.dup2(stdIn, 0)

    os.close(stdIn)
    os.close(stdOut)
    os.close(pr)
    os.close(pw)
    
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
        if pipe['inTokens']: createPipe()
            
        if tokens and not pipe['inTokens']: executeCommand(tokens, fullPath)
        sys.exit(0)
    else:
        exitCode = os.wait() if not backgroundProcess else None
        if pipe['inTokens']: pipe['inTokens'] = False
        if redirect['inTokens']: resetRedirection()
        if exitCode[1] != 0: os.write(1, ('Program Terminated with exit code: %d\n' % exitCode[1]).encode())
        tokens, fullPath = shell()
