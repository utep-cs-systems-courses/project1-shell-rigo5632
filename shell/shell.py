#! /usr/bin/env python3

import os, sys, re

# holds flags for when redirection (<, >) are found
redirect ={'inTokens': False, 'fileDescriptor': None, 'file': None, 'previousFD': None}

# Store the flags when a pipeline is found (|)
pipe = {
    'inTokens': False,
    'split': 0,
    'cmd1': None,
    'cmd2': None
}

# Have we seen the background token? (&)
backgroundProcess = False

# Executes Command with tokens, can also execute full path cmds (eg, /usr/bin/ls)
def executeCommand(tokens, fullPath):
    if not fullPath:
        #runs tokens
        for dir in re.split(':', os.environ['PATH']):
            program = "%s/%s" % (dir, tokens[0])
            try:
                os.execve(program, tokens, os.environ)
            except FileNotFoundError:
                pass
        os.write(2, ("%s Cannot be found\n" % tokens[0]).encode())
        sys.exit(0)
    else:
        # runs full path command
        try:
            os.execve(tokens[0], tokens, os.environ)
        except FileNotFoundError:
            pass
        os.write(2, ('%s Cannot be found\n' % tokens[0]).encode())
        sys.exit(0)
    sys.exit(0)

# Resets redirection flags once child has finished executing redirection
def resetRedirection():
    # resets stdIn/stdOut depending on the type of redirection
    os.dup2(redirect['previousFD'], redirect['fileDescriptor'])
    os.close(redirect['previousFD'])
    redirect['inTokens'] = False
    redirect['fileDescriptor'] = None
    redirect['file'] = None
    redirect['previousFD'] = None

# Sets the type of redirection (input/output)
def handleRedirection(redirect):
    os.close(redirect['fileDescriptor'])
    os.open(tokens[len(tokens)-1], redirect['file'])
    os.set_inheritable(redirect['fileDescriptor'], True)
    return tokens[:len(tokens)-1]

# Gets tokens from String
def getTokens(userInput):
    line = re.split('\s', userInput)
    fullPath = re.search('/', line[0])
    tokens = []
    counter = 0
    
    for token in line:    
        if token == '>':       #redirection Output setup of flags
            redirect['inTokens'] = True
            redirect['fileDescriptor'] = 1
            redirect['file'] = os.O_CREAT | os.O_WRONLY
            redirect['previousFD'] = os.dup(1)
            token = ''
        elif token == '<':     #redirection Input setup of flags
            redirect['inTokens'] = True
            redirect['fileDescriptor'] = 0
            redirect['file'] = os.O_RDONLY
            redirect['previousFD'] = os.dup(0)
            token = ''
        elif token == '|':     #pipes flag setup
            pipe['inTokens'] = True
            pipe['split'] = counter
            token = ''
        elif token == '&':     #background flag set up
            backgroundProcess = True
            token = ''
        tokens.append(token) if token != '' else None
        counter += 1
        
    if pipe['inTokens']:    #gets 2 cmds made when using pipes
        pipe['cmd1'] = tokens[:pipe['split']]
        pipe['cmd2'] = tokens[pipe['split']:]
        
    if len(tokens) == 1 and tokens[0] == 'exit': sys.exit(0) #Exit Shell
    if len(tokens) == 2 and tokens[0] == 'cd':               #Moves Directories
        try:
            os.chdir(tokens[1])
        except:
            os.write(2, 'Path not found'.encode())
        finally:
            return None, None
        
    return tokens, fullPath

# Sets up for pipe cmds
def pipeFunctionality():
    pr, pw = os.pipe()
    for fd in (pr, pw): os.set_inheritable(fd, True)

    newChild = os.fork()
    if newChild < 0:
        os.write(2, 'Fork Failed'.encode())
        sys.exit(1)
    elif newChild == 0: # executes 1 cmd
        os.dup2(pw, 1)
        for fd in (pr, pw): os.close(fd)
        executeCommand(pipe['cmd1'], fullPath)
    else: #executes 2 cmd with cmd 1 as input
        os.dup2(pr, 0)
        for fd in (pr, pw): os.close(fd)

        executeCommand(pipe['cmd2'], fullPath)

def shell():
    prompt = '$ ' if 'PS1' not in os.environ else os.environ['PS1']
    os.write(1, prompt.encode())

    try:
        userInput = str(input())
    except EOFError:
        sys.exit(1)
    return getTokens(userInput)

tokens, fullPath = shell()
while True:
    rc = os.fork()
    if rc < 0:
        os.write(stdErrorDisplay, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)
    elif rc == 0: # child
        if redirect['inTokens']: tokens = handleRedirection(redirect)
        if pipe['inTokens']: pipeFunctionality()
        if tokens and not pipe['inTokens']: executeCommand(tokens, fullPath)
        sys.exit(0)
    else: #parent
        exitCode = os.wait() if not backgroundProcess else None
        if pipe['inTokens']: pipe['inTokens'] = False
        if redirect['inTokens']: resetRedirection()
        if exitCode[1] != 0: os.write(1, ('Program Terminated with exit code: %d\n' % exitCode[1]).encode())
        tokens, fullPath = shell()
