#!/usr/bin/env python
import json
import logging
import subprocess
import os
import argparse


userid = [
        {"id": "u10374", "label": "Shinobu"},
        {"id": "u12262", "label": "Wu"},
        {"id": "u12831", "label": "Marzouk"},
        {"id": "u10338", "label": ""},
        {"id": "u10339", "label": ""}
]
projects = [
        {
            "source": "fugaku",
            "group": "hp150272",
            "name": "「富岳」で目指すシミュレーション・AI駆動型次世代医療・創薬 : 2025-04-01 - 2026-03-31",
            "expected1": 590074,
            "expected2": 590074
        },
        {
            "source": "fugaku",
            "group": "hp250059",
            "name": "SIMULATION STUDY OF THE MOLECULAR MECHANISM OF THE PATHOGENIC ALA711-GLU714 DELETION MUTATION IN THE IGF1R/INSR HYBRID HETERODIMER : 2025-04-01 - 2026-03-31",
            "expected1": 613500,
            "expected2": 901500,
        }
]

yearStart = 2025
monthStart = 4
termMonth = 6


def argParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', type=str, help='output directory')
    parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
    args = parser.parse_args()
    return args


def generateTimeRangeSequence(m):
    thisMonth = (monthStart + m - 1) % 12 + 1
    nextMonth = (monthStart + m) % 12 + 1
    thisYear = yearStart + (monthStart + m - 1) // 12;
    nextYear = yearStart + (monthStart + m) // 12;
    string = f"{thisYear}{thisMonth:02d}01000000:{nextYear}{nextMonth:02d}01000000"
    return string


def NStoNH(ns):
    return ns / 3600


def getNHPerMonth(group, user, m):
    timeSeq = generateTimeRangeSequence(m)
    logging.debug(timeSeq)
    cmd = ['/usr/local/bin/pjstata', '-g', group, '-u', user, '-s', timeSeq]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = result.stdout.decode().split('\n')
    totalNS = 0
    for line in lines[1:]:
        processedLine = line.strip()
        if len(processedLine) == 0:
            continue
        totalNS += int(processedLine[167:184])
    return NStoNH(totalNS)


def getNHPerUser(group, user):
    NHUserList = []
    for i in range(12):
        NH = getNHPerMonth(group, user, i)
        NHUserList.append(NH)
    return NHUserList


def getNHPerGroup(group, userList):
    NHGroupList = []
    for userInfo in userList:
        logging.debug(userInfo['id'])
        NHUserList = getNHPerUser(group, userInfo['id'])
        NHGroupList.append(NHUserList)
    return NHGroupList


def getNH(outputDir, groupList, userList):
    for gi, groupInfo in enumerate(groupList):
        NHGroupList = getNHPerGroup(groupInfo['group'], userList)
        if outputDir is not None:
            outname = os.path.join(outputDir, f'project{gi+1}.json')
            outputJson(outname, NHGroupList, groupInfo)
        else:
            printNHGroupList(NHGroupList, userList)


def outputJson(outname, groupList, groupInfo):
    result = {
            'name': groupInfo['name'],
            'expected1': groupInfo['expected1'],
            'expected2': groupInfo['expected2'],
            'source': groupInfo['source'],
            }
    result['data1'] = []
    result['data2'] = []
    addDataToResult(result['data1'], groupList)
    addDataToResult(result['data2'], groupList, termMonth)

    dirname = os.path.dirname(outname)
    if len(dirname) == 0:
        dirname = '.'
    os.makedirs(os.path.dirname(outname), exist_ok=True)
    with open(outname, 'w') as out:
        json.dump(result, out, ensure_ascii=False, indent=4)


def printNHGroupList(groupList, userList):
    result = {'data1': [], 'data2': []}
    addDataToResult(result['data1'], groupList)
    addDataToResult(result['data2'], groupList, termMonth)
    print('#' * (10 * len(userList)))
    for user in userList:
        print(f"{user['id']:10s}", end="")
    print()
    print('#' * (10 * len(userList)))
    printTermNH(result['data1'])
    print('#' * (10 * len(userList)))
    printTermNH(result['data2'])
    print('#' * (10 * len(userList)))
    print()


def printTermNH(data):
    for monthList in data:
        for d in monthList:
            print(f"{d:10.0f}", end="")
        print()



def addDataToResult(data, groupList, startMonth=0):
    data.append([0. for i in groupList])
    for mi in range(termMonth):
        userPerMonth = []
        for ui in range(len(groupList)):
            userPerMonth.append(groupList[ui][startMonth + mi])
        data.append(userPerMonth)


def setLoggingLevel(args):
    level = logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)


args = argParser()
setLoggingLevel(args)
getNH(args.output, projects, userid)
