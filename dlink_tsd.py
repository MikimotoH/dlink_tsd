#!/usr/bin/env python3
# coding: utf-8
from fuzzywuzzy import fuzz
import harvest_utils
from harvest_utils import waitClickable, waitVisible, waitText, getElems, \
        getElemText,getFirefox,driver,dumpSnapshot,\
        getText,getNumElem
from selenium.webdriver.support.ui import Select
from selenium.webdriver.remote.webelement import WebElement
from infix_operator import Infix
import os
from os import path
import time
import sys
import sqlite3
import hashlib

fzeq=Infix(fuzz.token_set_ratio)
partialeq=Infix(fuzz.partial_token_set_ratio)
dlDir= path.abspath('firmware_files/')
driver=None
maxCurDwl=100
conn=None
modelName=""

def uprint(msg:str):
    sys.stdout.buffer.write((msg+'\n').encode('utf8'))

def curDownloading()->[str]:
    files = os.listdir(dlDir)
    return [_ for _ in files if _.endswith('.part')]

def sha1(data)->str:
    return hashlib.sha1(data).hexdigest()

def getFileSha1(fileName)->str:
    with open(fileName,mode='rb') as fin:
        data = fin.read()
        return sha1(data)

def waitDownloading():
    curDwl = curDownloading()
    if len(curDwl) < maxCurDwl:
        return
    while True:
        curDwl = curDownloading()
        if len(curDwl) < maxCurDwl:
            break
        print("Too many Downloadings=%s, wait 5 seconds"%curDwl)
        time.sleep(5)
    completed = list(set(curDwl) - set(curDownloading()))
    print("completed=",completed)
    global conn
    csr=conn.cursor()
    for fileName in completed:
        fileSha1 = getFileSha1(dlDir+fileName)
        csr.execute("UPDATE dlink SET(file_sha1=:fileSha1)"
            " WHERE file_name=:fileName", locals())
        conn.commit()
        print("UPDATE %(fileName)s with SHA1=%(fileSha1)"%locals())

def sql(query:str, var=None):
    global conn
    csr=conn.cursor()
    csr.execute(query, var)
    if not query.upper().startswith("SELECT"):
        conn.commit()

def clickDownloadableElem(elem:WebElement)->str:
    pollFreq=1
    filesOld=os.listdir(dlDir)
    fileName=getElemText(elem)
    href = elem.get_attribute('href')
    assert href is not None
    uprint('fileName="%s" href="%s"'%(fileName,href))
    sql("UPDATE dlink SET href=:href WHERE"
        " file_name=:fileName",locals())
    uprint("UPDATE dlink SET href=%(href)s WHERE"
        " file_name=%(fileName)s"%locals())
    return
    # if fileName in filesOld:
    #     print('"%s" is already downloaded'%fileName)
    #     return
    # elem.click()
    # for trial in range(60):
    #     filesNew=os.listdir(dlDir)
    #     if len(filesNew) > len(filesOld):
    #         filesAdded = list(set(filesNew) - set(filesOld))
    #         print("filesAdded=", filesAdded)
    #         return filesAdded[0]
    #     time.sleep(pollFreq)
    # print("Error: Not downloadable element: "+fileName)


def harvestPage2():
    global modelName
    modelName=getText('big > strong')
    print("Page2 modelName=",modelName)
    global driver
    numRows = getNumElem('tr#rsq')
    if numRows==0:
        return
    for iRow in range(2, numRows+1):
        row = waitClickable('tr#rsq:nth-child(%d)'%iRow)
        rowText = getElemText(row)
        uprint('Row%d %s'%(iRow, rowText))
        if 'firmware' not in rowText.lower():
            print(' -- bypass')
            continue
        uprint('Click '+rowText)
        row.click()
        modelName=getText('big > strong')
        print('Page3 modelName=%s'%modelName)
        desc=getText('.prodtd > table:nth-child(4) > tbody:nth-child(1) '
                '> tr:nth-child(2) > td:nth-child(2)')
        uprint("Description="+desc)
        for fn9 in getElems('.fn9'):
            fileName = getElemText(fn9)
            fileExt = path.splitext(fileName)[1].lower()
            uprint('filaName="%s"'%fileName)
            if fileExt in ['.doc', '.docx', '.txt','.pdf','.htm','.html','.xls']:
                uprint(' -- fileName "%s" doesn\'t look like a firmware file'%fileName)
            global conn
            csr=conn.cursor()
            model=modelName
            csr.execute(
                "INSERT OR REPLACE INTO dlink(model,file_name,desc)"
                "VALUES(:model,:fileName,:desc)",locals()
                )
            uprint('INSERT OR REPLACE INTO "%(model)s","%(fileName)s","%(desc)s"'%
                locals())
            # waitDownloading()
            clickDownloadableElem(fn9)
        global driver
        driver.back()

def main():
    startPfxIdx = int(sys.argv[1]) if len(sys.argv)>1 else 1
    startSfxIdx = int(sys.argv[2]) if len(sys.argv)>2 else 1
    global driver,conn
    harvest_utils.driver=getFirefox(dlDir)
    driver = harvest_utils.driver
    conn=sqlite3.connect('dlink_tsd.sqlite3')
    csr=conn.cursor()
    csr.execute("CREATE TABLE IF NOT EXISTS dlink("
        "model TEXT,"
        "file_name TEXT PRIMARY KEY,"
        "desc TEXT,"
        "href TEXT,"
        "file_sha1 TEXT)"
        );
    conn.commit()
    driver.get('http://tsd.dlink.com.tw/')
    modelPfxSel = Select(waitClickable(
        'select.quickFindAndSearchForm:nth-child(4)'))
    numModelPfx=len(modelPfxSel.options)
    for pfxIdx in range(startPfxIdx,numModelPfx):
        modelPfxSel.select_by_index(pfxIdx)
        modelSfxSel = Select(waitClickable(
            'select.quickFindAndSearchForm:nth-child(6)'))
        numModelSfx=len(modelSfxSel.options)
        for sfxIdx in range(startSfxIdx,numModelSfx):
            print("pfxIdx=%d, sfxIdx=%d"%(pfxIdx,sfxIdx))
            startSfxIdx=1
            modelSfxSel.select_by_index(sfxIdx)
            pfxTxt =modelPfxSel.options[pfxIdx].text
            sfxTxt =modelSfxSel.options[sfxIdx].text
            modelName=pfxTxt+'-'+sfxTxt
            print("Page1: modelName=",modelName)
            goBtn=waitClickable('.prodtd > p:nth-child(3) > a:nth-child(7)')
            goBtn.click()
            harvestPage2()
            driver.back()
            modelPfxSel = Select(waitClickable(
                'select.quickFindAndSearchForm:nth-child(4)'))
            modelPfxSel.select_by_index(pfxIdx)
            modelSfxSel = Select(waitClickable(
                'select.quickFindAndSearchForm:nth-child(6)'))
    # wait until all '.part' vanished
    while True:
        files = os.listdir(dlDir)
        downloading = [_ for _ in files if _.endswith('.part')]
        if downloading:
            print('-- Downloading : %s  wait 3 seconds'%downloading)
            time.sleep(3)
        else:
            break
    print('-- terminate firefox')
    driver.quit()


if __name__=='__main__':
    try:
        main()
    except Exception as ex:
        import ipdb; ipdb.set_trace()
        print(str(ex))
        dumpSnapshot(str(ex))
