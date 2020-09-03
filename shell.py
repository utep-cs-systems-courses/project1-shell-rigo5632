#! /usr/bin/ python 3

import os
import re
import sys

stdInput  = 0 # keyboard input
stdOutput = 1 # display output
stdError  = 2 # error output
prompt = '$ '

while 1:
    os.write(stdOutput, prompt.encode())
    userInput = os.read(stdInput, 20)

    tokens = re.split(b' ', userInput)

    for i in range(len(tokens)):
        os.write(stdOutput, tokens[i])
        os.write(stdOutput, ''.encode() if i+1 == len(tokens) else ' '.encode())
exit()
