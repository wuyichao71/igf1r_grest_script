import os
import sys
import argparse
import logging
import yaml
import re


def argParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str, help='The input file')
    parser.add_argument('-o', '--output', action='store_true', help='output mode')
    parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
    args = parser.parse_args()
    return args


def getKeyFromFile(lines):
    key = set()
    for line in lines:
        matches = re.findall(r"\{([^}]*)\}", line)
        key.update(matches)
    return key


def getKeyDict(config_data, key):
    return {k: config_data[k] for k in key}


def lineListtoString(lines):
    oneLine = ""
    for line in lines:
        oneLine += line
    return oneLine


def getUsedBlock(lines, mode):
    inBlock = False
    usedBlock = False
    resultLines = []
    for line in lines:
        processedLine = line.strip()
        tokens = processedLine.split()
        if processedLine.startswith('#<<<<'):
            inBlock = True
            if mode in tokens:
                usedBlock = True
        elif (processedLine.startswith('#>>>>')):
            inBlock = False
            usedBlock = False
            # print(tokens)
        elif (inBlock and usedBlock) or (not inBlock):
            resultLines.append(line)
    return resultLines


def getReplicaNumber(tString):
    NREPLICA = len(tString.split())
    logging.debug(NREPLICA)
    return NREPLICA


def handleConfigData(config):
    resultConfig = dict(config)
    if config['mode'] == 'check':
        resultConfig["NREPLICA"] = 1
    else:
        try:
            tempString = config['GREST_TEMPERATURE']
            lowestTemperature = float(tempString.split()[0])
        except ValueError:
            tempString = readGrestTemperature(config['GREST_TEMPERATURE'])
            resultConfig['GREST_TEMPERATURE'] = tempString
        NREPLICA = getReplicaNumber(tempString)
        logging.debug(NREPLICA)
        resultConfig["NREPLICA"] = NREPLICA
    return resultConfig


def readGrestTemperature(prevOutName):
    # raise ValueError("To be continued!")
    with open(prevOutName, 'r') as inFile:
        for line in inFile:
            processedLine = line.strip()
            if len(processedLine) == 0:
                continue
            if processedLine.startswith('REMD> New parameter set:'):
                finalParameter = processedLine
    commaIndex = finalParameter.index(':')
    logging.debug(commaIndex)
    tokens = finalParameter[commaIndex+1:].split()
    # print(tokens)
    tokens[0] = str(round(float(tokens[0]), 2))
    tempString = ' '.join(tokens)

    return tempString


def output(outname, outString):
    dirname = os.path.dirname(outname)
    if len(dirname) == 0:
        dirname = '.'
    os.makedirs(dirname, exist_ok=True)
    with open(outname, 'w') as out:
        out.write(outString)


def setLoggingLevel(args):
    level = logging.INFO
    if args.debug:
        level=logging.DEBUG
    logging.basicConfig(level=level)


def prepareRstFile(sourceFile, targetTemplate, nrep):
    absSourceFile = os.path.abspath(sourceFile)
    for repi in range(nrep):
        targetFile = targetTemplate.format(repi + 1)
        if '{}' in absSourceFile:
            finalSourceFile = absSourceFile.format(repi + 1)
        else:
            finalSourceFile = absSourceFile
        os.makedirs(os.path.dirname(targetFile), exist_ok=True)
        if os.path.lexists(targetFile) or os.path.exists(targetFile):
            os.unlink(targetFile)
        os.symlink(finalSourceFile, targetFile)


def printLines(lines):
    for line in lines:
        print(line, end="")


args = argParser()

setLoggingLevel(args)

with open(args.input, 'r') as inFile:
    config_data = yaml.safe_load(inFile)
resultConfig = handleConfigData(config_data)

with open(config_data['template'], 'r') as templateFile:
    templateLines = templateFile.readlines()
processedLines = getUsedBlock(templateLines, config_data['mode'])

key = getKeyFromFile(processedLines)
keyDict = getKeyDict(resultConfig, key)
# logging.debug(keyDict)
lineString = lineListtoString(processedLines)
inputString = lineString.format(**keyDict)

prepareRstFile(config_data['rstfileFrom'],
        config_data['IN_RSTFILE'], resultConfig['NREPLICA'])

if args.output:
    output(config_data['outname'], inputString)
