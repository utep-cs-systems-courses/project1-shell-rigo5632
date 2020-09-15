#! /usr/bin/env python3

import os, sys, re

redirect ={'inTokens': False, 'fileDescriptor': None, 'file': None, 'previousFD': None}

def getTokens(userInput):
    line = re.split(b'\s', userInput)
    fullPath = re.search('/', line[0].decode())
    tokens = []
    
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
        tokens.append(token.decode()) if token != b'' else None

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
    elif rc == 0:# child
        if redirect['inTokens']:
            os.close(redirect['fileDescriptor'])
            os.open(tokens[len(tokens)-1], redirect['file'])
            os.set_inheritable(redirect['fileDescriptor'], True)
            tokens = tokens[:len(tokens)-1]
            
        if tokens:
            if not fullPath:
                for dir in re.split(":", os.environ['PATH']):
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
                os.write(2, ("%s Cannot be found\n" % tokens[0]).encode())
                sys.exit(0)
        sys.exit(0)
    else:
        exitCode = os.wait()
        if redirect['inTokens']:
            os.dup2(redirect['previousFD'], redirect['fileDescriptor'])
            os.close(redirect['previousFD'])
            redirect['previousFD'] = None
            redirect['inTokens'] = False
            redirect['fileDescriptor'] = None
            redirect['file'] = None
        if exitCode[1] != 0: os.write(1, ('Program Terminated with exit code: %d\n' % exitCode[1]).encode())
        tokens, fullPath = shell()
