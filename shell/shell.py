#! /usr/bin/env python3

import os, sys, re

# holds flags for when redirection (<, >) are found
redirect ={'inTokens': False, 'fileDescriptor': None, 'file': None, 'previousFD': None}

# Store the flags when a pipeline is found (|)
pipe = {'inTokens': False, 'split': 0, 'cmd1': None, 'cmd2': None}

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
    #print(1)
    # resets stdIn/stdOut depending on the type of redirection
    os.dup2(redirect['previousFD'], redirect['fileDescriptor'])
    os.close(redirect['previousFD'])
    redirect['inTokens'] = False
    redirect['fileDescriptor'] = None
    redirect['file'] = None
    redirect['previousFD'] = None

# Sets the type of redirection (input/output)
def handleRedirection(redirect):
    #print(1)
    #print(tokens)
    os.close(redirect['fileDescriptor'])
    os.open(tokens[len(tokens)-1], redirect['file'])
    os.set_inheritable(redirect['fileDescriptor'], True)
    return tokens[:len(tokens)-1]

def getCmds(line):
    a = []
    for cmds in line:
        a.append(re.split(b'\s', cmds))
    if len(a) <= 2:
        return a[0], False
    else:
        return a, True

#cleans line from any trash it might have(new line, empty spaces)
# it also sets flags for pipes or rediretion
def cleanLine(line):
    tokens = []
    counter = 0
    for token in line:
        token = token.decode()
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
    return tokens

def getPipeCmds(tokens):
    pipe['cmd1'] = tokens[:pipe['split']]
    pipe['cmd2'] = tokens[pipe['split']:]

# Gets tokens from String
def getTokens(userInput):
    line = re.split(b'\n', userInput)
    line, multipleCmds = getCmds(line)
    if multipleCmds:
        for i in range(len(line)):
            line[i] = cleanLine(line[i])
        line = line[:-1]
        for cmds in line:
            if pipe['inTokens']: getPipeCmds(cmds)
            if len(cmds) == 1 and cmds[0] == 'exit':sys.exit(0)
            if len(cmds) == 2 and cmds[0] == 'cd':
                try:
                    os.chdir(cmds[1])
                except:
                    os.write(2, 'Path not found'.encode())
                finally:
                    return line[1], False, False
        fullPath = re.search('/', line[0][0])
        return line, fullPath, True
    else:
        tokens = cleanLine(line)
        if not tokens: return None, None, False
        fullPath = re.search('/', tokens[0])
        if pipe['inTokens']: getPipeCmds(tokens)
        if len(tokens) == 1 and tokens[0] == 'exit': sys.exit(0) #Exit Shell
        if tokens[0] == 'cd':               #Moves Directories
            try:
                os.chdir(tokens[1])
            except:
                os.write(2, 'Path not found'.encode())
            finally:
                if len(tokens) >= 3:
                    return tokens[2:], fullPath, False
                else:
                    return None, None, False
        return tokens, fullPath, False 

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

def newChildProcess(cmd, fullpath):
    if not cmd: return
    newChild = os.fork()
    if newChild < 0:
        os.write(2, 'Fork Failed'.encode())
    elif newChild == 0:
        executeCommand(cmd, fullPath)
    else:
        child = os.wait() if not backgroundProcess else None

def shell():
    prompt = '$ ' if 'PS1' not in os.environ else os.environ['PS1']
    os.write(1, prompt.encode())
    
    userInput = os.read(0, 1024) #reads 1 MByte up to input
    if not userInput: sys.exit(1)
    return getTokens(userInput)

tokens, fullPath, multipleCmds = shell()
while True:
    rc = os.fork()
    if rc < 0:
        os.write(stdErrorDisplay, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)
    elif rc == 0: # child
        if multipleCmds:
            for cmd in tokens:
                newChildProcess(cmd, fullPath)
            sys.exit(0)
        if redirect['inTokens']: tokens = handleRedirection(redirect)
        if pipe['inTokens']: pipeFunctionality()
        if tokens and not pipe['inTokens']: executeCommand(tokens, fullPath)
        sys.exit(0)
    else: #parent
        exitCode = os.wait() if not backgroundProcess else None
        if pipe['inTokens']: pipe['inTokens'] = False
        if redirect['inTokens']: resetRedirection()
        if exitCode[1] != 0: os.write(1, ('Program Terminated with exit code: %d\n' % exitCode[1]).encode())
        backgroundProcess = False
        tokens, fullPath, multipleCmds = shell()
