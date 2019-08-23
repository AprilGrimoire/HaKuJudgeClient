#!/usr/bin/env python3

import inspect
import os
import time
import threading
import subprocess
import multiprocessing
import resource
import json

tooMuchTime = False
runtimeError = False

"""
@param timeout: timeout int second
"""
def runTarget(dataInPath, dataAnsPath, timeout):
    testdataIn = open(dataInPath, "r")
    testdataOut = open("target.out", "w")
    try:
        p = subprocess.run(["chroot",  "--userspec=nobody:nobody", "work", "/judge/target"], stdin=testdataIn, stdout=testdataOut, stderr=subprocess.DEVNULL, timeout=timeout)
        if p.returncode != 0:
            global runtimeError
            runtimeError = True
    except subprocess.TimeoutExpired:
        global tooMuchTime
        tooMuchTime = True
    testdataIn.close()
    testdataOut.close()

"""
@param timeLimit: timelimit in ms
@param memoryLimit: memorylimit in KB
"""
def _execute(dataInPath, dataAnsPath, targetPath, timeLimit, memoryLimit, queue):
    dataInPath = os.path.abspath(dataInPath)
    dataAnsPath = os.path.abspath(dataAnsPath)
    targetPath = os.path.abspath(targetPath)
    scriptName = inspect.getframeinfo(inspect.currentframe()).filename
    scriptPath = os.path.dirname(os.path.abspath(scriptName))
    os.chdir(scriptPath)
    os.system("rm -rf work")
    os.system("cp -r virtualroot work")
    os.system("cp {} work/judge/".format(targetPath))
    runTarget(dataInPath, dataAnsPath, timeLimit / 1000 * 2)
    # convert ms to s
    # real time can be at most 2 * user time
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = dict()
    result["memory"] = usage[2]
    if tooMuchTime:
        result["status"] = "TimeLimitExceeded"
        result["time"] = None
    else:
        result["time"] = usage[0]
        if runtimeError:
            result["status"] = "RuntimeError"
        elif result["time"] > timeLimit:
            result["status"] = "TimeLimitExceeded"
        elif result["memory"] > memoryLimit:
            result["status"] = "MemoryLimitExceeded"
        else:
            if os.system("diff -w target.out {} > /dev/null".format(dataAnsPath)):
                result["status"] = "WrongAnswer"
            else:
                result["status"] = "Accepted"
                result["score"] = 1
    if "score" not in result:
        result["score"] = 0
    queue.put(result)

"""
@param timeLimit: timelimit in ms
@param memoryLimit: memorylimit in byte
"""
def execute(dataInPath, dataAnsPath, targetPath, timeLimit, memoryLimit):
    # a new process needs to be started to get time and memory usage
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_execute, args=(dataInPath, dataAnsPath, targetPath, timeLimit, memoryLimit, q))
    p.start()
    return q.get()
