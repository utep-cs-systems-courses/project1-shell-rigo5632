#! /usr/bin/ python 3

import os
import re
import sys

stdInput  = 0 # keyboard input
stdOutput = 1 # display output
stdError  = 2 # error output
constants = {'shellPrompt': '$ ', 'noSpace': '', 'emptySpace':' '}

while 1:
    os.write(stdOutput, constants['shellPrompt'].encode())
    userInput = os.read(stdInput, 10000)
    words = re.split(b'\W+', userInput)

    tokens = []
    for token in words: tokens.append(token) if token != b'' else None
    
    if len(tokens) == 1 and tokens[0].decode() == 'exit' : break

    for i in range(len(tokens)):
        os.write(stdOutput, tokens[i])
        os.write(stdOutput, constants['noSpace'].encode() if i+1 == len(tokens) else constants['emptySpace'].encode())
exit()
