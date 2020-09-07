#! /usr/bin/env python3

import os, sys, re

stdInput = 0
stdDisplay = 1
stdErrorDisplay = 2
while 1:
    rc = os.fork()
    if rc < 0:
        os.write(stdErrorDisplay, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)

    elif rc == 0:                   # child
        tokens = []
        
        os.write(stdDisplay, '$ '.encode())
        userInput = os.read(0, 100)
        
        line = re.split(b'\s', userInput)
        
        for token in line: tokens.append(token.decode()) if token != b'' else None
        if len(tokens) == 1 and tokens[0] == 'exit': sys.exit(2)
        
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
