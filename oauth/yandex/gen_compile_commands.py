#!/usr/bin/env python3

import os
import sys
import subprocess
import json

'''
    Скрипт создает compile_commands.json
    файл может использоваться различными clang утилитами
    # https://clangd.llvm.org/
'''

if __name__ == '__main__':
    CWD = os.getcwd()
    make = subprocess.Popen(["make", "-n"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if make.stdout is None:
        sys.exit(-1)

    compile_commands = []

    for _line in make.stdout:
        line = _line.decode().strip()
        for word in line.split(" "):
            if word.endswith(".cpp") and not word.startswith("/"):
                compile_commands.append({"command": line, "directory": CWD, "file": word})
                break

    with open("compile_commands.json", "w") as file:
        json.dump(compile_commands, fp=file)
