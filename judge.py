#!/usr/bin/env python3

import inspect
import json
import os
import subprocess
import psutil
import execute

COMPILE_TIMEOUT = 10

def compileTarget(targetPath):
    try:
        p = subprocess.Popen(["g++", "-std=c++11", "-O2", "-o", "temp/target", targetPath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait(COMPILE_TIMEOUT)
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        parent = psutil.Process(p.pid)
        for child in parent.children(recursive=True):
            child.kill()
        p.wait()
        return False

def judge(problemPath, targetPath):
    problemPath = os.path.abspath(problemPath)
    targetPath = os.path.abspath(targetPath)
    scriptName = inspect.getframeinfo(inspect.currentframe()).filename
    scriptPath = os.path.dirname(os.path.abspath(scriptName))
    cwd = os.getcwd()
    os.chdir(scriptPath)
    if compileTarget(targetPath):
        with open(problemPath, "r") as f:
            problem = json.load(f)
        summary = {"time": 0, "memory": 0}
        detail = []
        score = 0
        problemDir = os.path.dirname(problemPath)
        for testdata in problem:
            inputFile = os.path.join(problemDir, testdata["input"])
            answerFile = os.path.join(problemDir, testdata["answer"])
            result = execute.execute(inputFile, answerFile, "temp/target", testdata["time"], testdata["memory"])
            result["id"] = testdata["id"]
            detail.append(result)
            score += testdata["score"] * result["score"]
            if result["status"] != "Accepted" and "status" not in summary:
                summary["status"] = result["status"]
            if result["time"] is None or summary["time"] is None:
                summary["time"] = None
            else:
                summary["time"] = max(summary["time"], result["time"])
            summary["memory"] = max(summary["memory"], result["memory"])
        if "status" not in summary:
            summary["status"] = "Accepted"
        summary["score"] = score
        summary["detail"] = detail
    else:
        summary = {"status": "CompileError", "score": 0, "time": None, "memory": None, "detail": None}
    os.chdir(cwd)
    return summary
