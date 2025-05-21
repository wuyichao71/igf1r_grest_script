#!/usr/bin/env bash


main() {
    jobInfo=$(pjstat --data |grep "$jobHead")
    dirList=$(ls -hvd ${jobDir%%/}/*_{tune,eq}*)
    if [[ -z $jobInfo ]]; then
        # getFirstJobDir
        getFinalStep
        getNextJobDir
        cd $nextDir
        debug "$prevDir --> $nextDir"
        setParameter
        checkDirectory
        makeJobDirectory
    else
        echo "There are some job running!"
    fi
}

error() {
    msg=$1
    echo $msg 1>&2
    exit -1
}

debug() {
    echo "DEBUG: " $1 >&2
}

checkDirectory() {
    outFile="output/out.1.0"
    if ! [[ -e $outFile ]]; then
        notHaveOutput=1
    elif ! grep 'total time' $outFile > /dev/null; then
        brokenOutput=1
    fi

    rstFile="${head}_rep1.rst"
    # debug "$rstFile"
    if ! [[ -e $rstFile ]]; then
        outHaveRstfile=1
    else
        rstSize=$(stat --format="%s" $rstFile)
        if [[ rstSize -eq 0 ]]; then
            brokenRst=1
        fi
    fi

    if [[ $brokenOutput -eq 1 || $brokenRst -eq 1 ]]; then
        makeBackupDir
        if [[ $brokenOutput -eq 1 ]]; then
            backup output output.*
            backup stdout
        fi
        if [[ $brokenRst -eq 1 ]]; then
            backup ${head}_rep*
        fi
    fi
}

getFinalStep() {
    for dirname in $dirList
    do
        basename=$(basename $dirname)
        tmp=$(echo $basename | awk -F'_' '{print $1}')
    done
    finalStep=$tmp
    debug "finalStep: ${finalStep}"
}

makeBackupDir() {
    last=$(ls -hvd * |grep 'backup\.' |awk -F. 'END{print $2}')
    last=${last:--1}
    ((last++))
    backupDir=backup.$last
    mkdir -p $backupDir
}

backup() {
    for i in $@
    do
        mv $i $backupDir
    done
}

getFirstJobDir() {
    for dirname in $dirList
    do
        break
    done
    firstDirname=$dirname
}

getNextJobDir() {
    prevDirname="../data"
    finished=1
    for dirname in $dirList
    do
        outFile=${dirname}/output/out.1.0
        if ! [[ -e $outFile ]]; then
            finished=0
            break
        fi

        if ! grep 'total time' $outFile > /dev/null; then
            finished=0
            break
        fi
        prevDirname=$dirname
    done
    if [[ $finished -eq 1 ]]; then
        echo "The tune is finished!"
        exit
    fi
    nextDir=$dirname
    prevDir=$prevDirname
}

getRstName() {
    if [[ $rstfileDir == "data" ]]; then
        rstname="step4.3_equilibration.rst"
    else
        oldTuneSetup=$(echo $rstfileDir | awk -F'_' '{print $2}')
        if [[ $oldTuneSetup =~ ^tune ]]; then
            oldHead="tune"
        elif [[ $oldTuneSetup =~ ^eq ]]; then
            oldHead="eq"
        else
            error "The ${rstfileDir} directory setup is unknown!"
        fi
        rstname="${oldHead}_rep{}.rst"
    fi
}

setParameter() {
    curBasename=$(basename $nextDir)
    rstfileDir=$(basename $prevDir)
    tuneStep=$(echo $curBasename | awk -F'_' '{print $1}')
    tuneSetup=$(echo $curBasename | awk -F'_' '{print $2}')
    getRstName
    if [[ $tuneSetup =~ ^tune ]]; then
        head="tune"
        mode="tune"
        exchangePeriod=${tuneSetup##tune}
        nstep=150000
    elif [[ $tuneSetup =~ ^eq ]]; then
        head="eq"
        mode="equilbrium"
        if [[ $tuneStep == 1 ]]; then
            exchangePeriod=0
            nstep=600000
        elif [[ $tuneStep == $finalStep ]]; then
            exchangePeriod=600
            nstep=1500000
        else
            error "Can't get the exchange period!"
        fi
    else
        error "The ${curBasename} directory setup is unknown!"
    fi
    if [[ $tuneStep -gt 2 ]]; then
        useOutput=1
        outname="../${rstfileDir}/output/out.1.0"
    fi
    rstfileFrom="../${rstfileDir}/${rstname}"
}

makeJobDirectory() {
    if ! [[ -e prepare.py ]]; then
        ln -s ../template/prepare.py
    fi

    makePrepareInput
    python prepare.py prepare.yml -o
    makeSubFile
    pjsub sub.sh
}

makePrepareInput() {
    gawk \
        -v mode="$mode" \
        -v exchangePeriod="$exchangePeriod" \
        -v nstep="$nstep" \
        -v head="$head" \
        -v rstfileFrom="$rstfileFrom" \
        -v useOutput="$useOutput" \
        -v outname="$outname" \
        -v step="$tuneStep" \
        '{
        if ($1 ~ /^mode:/) {
            print "mode: \"" mode "\""
        } else if ($1 ~ /^EXCHANGE_PERIOD:/) {
            print "EXCHANGE_PERIOD: " exchangePeriod
        } else if ($1 ~ /^NSTEP:/) {
            print "NSTEP: " nstep
        } else if ($1 ~ /^ENEOUT_PERIOD:/) {
            if (step == 1) {
                print "ENEOUT_PERIOD: " 600
            } else {
                print "ENEOUT_PERIOD: " exchangePeriod
            }
        } else if (match($1, /^OUT_(.*)FILE:/, subStr)) {
            suffix = tolower(subStr[1])
            print $1" \"" head "_rep{}." suffix "\""
        } else if ($1 ~ /^rstfileFrom:/) {
            print $1 " \"" rstfileFrom "\""
        } else if ($1 ~ /^outname:/) {
            print $1 " \"" head ".inp\""
        } else if ($1 ~ /^GREST_TEMPERATURE:/) {
            if (useOutput) {
                print $1 " \"" outname "\""
            } else {
                print $0
            }
        } else {
            print $0
        }
    }' ../template/prepare.yml >prepare.yml
}

makeSubFile() {
    gawk -v head="$head" \
        -v exchangePeriod="$exchangePeriod" \
        -v nstep="$nstep" \
        -v jobhead="$jobHead" \
        -v head="$head" \
        -v exchangePeriod="$exchangePeriod" \
        '{
        if ($0 ~ /^#PJM -L "elapse/) {
            second = int(6000 * nstep / 150000)
            h = (second / 3600)
            m = (second % 3600 / 60)
            s = (second % 60)
            printf "#PJM -L \"elapse=%02d:%02d:%02d\"\n", h, m, s
        } else if ($0 ~ /#PJM -N/) {
            print "#PJM -N \"" jobhead "-" head exchangePeriod "\""
        } else if ($0 ~ /^inpname/) {
            print "inpname=" head ".inp"
        } else {
            print $0
        }
    }' ../template/sub.sh >sub.sh
}


# global variable
jobHead=$1
jobDir=$2
check=$3
main
