#! /usr/bin/env python3

import os, sys, re

stdInput = 0
stdDisplay = 1
stdErrorDisplay = 2

while True:
    rc = os.fork()
    if rc < 0:
        os.write(stdErrorDisplay, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)

    elif rc == 0:                   # child
        tokens = []
        redirect = {'inTokens': False, 'fileDescriptor': None, 'file': None}
        
        prompt = os.environ['PS1'] if os.environ['PS1'] != '' else '$ '
        os.write(stdDisplay, prompt.encode())
        userInput = os.read(0, 100)
        
        line = re.split(b'\s', userInput)
        print(line)
        
        for token in line:
            if token == b'>':
                redirect['inTokens'] = True
                redirect['fileDescriptor'] = 1
                redirect['file'] = os.O_CREAT | os.O_WRONLY
                token = b''
            elif token == b'<':
                redirect['inTokens'] = True
                redirect['fileDescriptor'] = 0
                redirect['file'] = os.O_RDONLY
                token = b''
            tokens.append(token.decode()) if token != b'' else None

        if len(tokens) == 1 and tokens[0] == 'exit': sys.exit(2)
        
        if redirect['inTokens']:
            os.close(redirect['fileDescriptor'])
            os.open(tokens[len(tokens)-1], redirect['file'])
            os.set_inheritable(redirect['fileDescriptor'], True)
            tokens = tokens[:len(tokens)-1]
            redirect['inTokens'] = False
            redirect['fileDescriptor'] = None
            redirect['file'] = None
            
        if tokens:
            for dir in re.split(":", os.environ['PATH']):
                program = "%s/%s" % (dir, tokens[0])
                try:
                    os.execve(program, tokens, os.environ)
                except FileNotFoundError:
                    pass
            os.write(2, ("Child:    Could not exec %s\n" % tokens[0]).encode())
            sys.exit(1)
        sys.exit(0)
    else:
        childPidCode = os.wait()
        if childPidCode[1] == 512: sys.exit(1)
