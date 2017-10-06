# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import cgi
import os.path
import sys
from zipfile import ZipFile
import time
import sys
import os
import re
import multiprocessing
import subprocess

def unzip(dir, path, fileFilterPattern):
    """
    日本語名対応ZIP解凍処理
    :param dir: 出力先ディレクトリ
    :param path: 入力ファイル(ZIP)
    :param fileFilterPattern: ファイル名フィルタ正規表現(ファイル名のマッチ結果がNoneではないものを出力)
    :return:
    """
    repatter = re.compile(fileFilterPattern)

    with ZipFile(path) as zf:
        (namel, infol) = (zf.namelist(), zf.infolist())
        jobs = []
        #pool = multiprocessing.Pool(10)

        for (member, info) in zip(namel, infol):
            name = member.encode('cp437').decode('sjis')
            timestamp = time.mktime(time.strptime('%d/%02d/%02d %02d:%02d:%02d' % info.date_time, '%Y/%m/%d %H:%M:%S'))
            print('inflating: %s [%d]' % (name, timestamp))
            if name.endswith('/'):
                # ディレクトリは作成
                os.makedirs(os.path.join(dir, name), exist_ok=True)
                os.utime(os.path.join(dir, name), (timestamp, timestamp))
                continue
            else:
                # ファイルは出力
                if repatter.search(name) is None:
                    continue
                #result_async = pool.apply_async(filewrite_worker, (dir, name, member, timestamp, zf,), callback=filewrite_callback)

                if len(jobs) >= 10:
                    while len(jobs) >= 10:
                        jobs = [job for job in jobs if job.is_alive()]
                        time.sleep(0.001)

                job = multiprocessing.Process(target=filewrite_worker, args=(dir, name, member, timestamp, zf.read(member),))
                jobs.append(job)
                job.start()


        #pool.close()
        #pool.join()

        [job.join() for job in jobs]

        print('Finish')

                #filewrite_worker(dir, name, member, timestamp, zf)
                #with open(os.path.join(dir, name), 'wb') as f:
                #    f.write(zf.read(member))
                #os.utime(os.path.join(dir, name), (timestamp, timestamp))

def filewrite_callback(res):
    print('(Callback) ' + str(res))


def filewrite_worker(dir, name, member, timestamp, data):
    with open(os.path.join(dir, name), 'wb') as f:
        f.write(data) #zf.read(member)
    os.utime(os.path.join(dir, name), (timestamp, timestamp))
    return name

def parser():
    usage = 'Usage: python {} folderPath extractPath [--help]'\
            .format(__file__)
    arguments = sys.argv
    if len(arguments) == 1:
        print(usage)
        sys.exit(-1)
    # ファイル自身を指す最初の引数を除去
    arguments.pop(0)
    # 引数
    folderPath = arguments[0]
    if folderPath.startswith('-'):
        print(usage)
        sys.exit(-1)
    # - で始まるoption
    options = [option for option in arguments if option.startswith('-')]

    if '-h' in options or '--help' in options:
        print(usage)
        sys.exit(-1)

    return folderPath


if __name__ == '__main__':
    folderPath = parser()
    # authenticity_tokenの取得
    s = requests.Session()
    r = s.get('http://XXX.XXX.XXX.XXX:7700/WebConsole/login.do')
    soup = BeautifulSoup(r.text)
    loginPath = soup.find('form').get('action')
    # auth_token = soup.find(attrs={'name': 'authenticity_token'}).get('value')
    # payload['authenticity_token'] = auth_token

    # ログイン
    payload = {
        'user': 'XXXX',
        'password': 'XXXX'
    }
    r = s.post('http://XXX.XXX.XXX.XXX:7700' + loginPath, data=payload)
    #print(r.text)

    # ダウンロード
    payload = {
        'triggerEnabledValue': 'true',
        'project': 'true',
        'projectLatestVersion': 'false'
    }
    r = s.post('http://XXX.XXX.XXX.XXX:7700/WebConsole/export.do', data=payload, stream=True)
    local_filename = cgi.parse_header(r.headers['Content-Disposition'])[-1]['filename']
    filePath = os.path.join(folderPath, local_filename)

    # ダウンロード処理
    with open(filePath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                # f.flush() commented by recommendation from J.F.Sebastian

    # ZIP解凍
    popen = subprocess.Popen('dataspider_backup.bat ' + filePath + ' ' + folderPath, shell=True)
    popen.wait()
    # Python内でZIPを解凍するより7z.exeなど外部コマンドのほうが早かった。
    ## dataspider_backup.bat
    #### "C:\Program Files\7-Zip\7z.exe" x -y %1 -o%~2 -xr!*.class
    #### xcopy /e %~2\%~n1\* %~2
    #### rmdir /s /q %~2\%~n1\
    #### del /Q %1
    
    # こちらは廃止
    #zfile = zipfile.ZipFile('export_20170620115013.zip')

