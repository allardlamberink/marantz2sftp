import json
import requests
import re
import time
import pysftp
import settings
from datetime import date, datetime, timedelta
from os import path, getcwd
#from progressbar import ProgressBar, Bar, Percentage, FileTransferSpeed


s = requests.Session()
base_url = settings.recorder_base_url
login_payload_json = {'edtPwd': '%s' % settings.recorder_password}
local_file_path='/tmp/'

def sftp_get_cinfo():
    sftp_hostname=settings.sftp_hostname
    sftp_user=settings.sftp_user
    sftp_key_file=path.join(getcwd(), settings.sftp_key_filename)
    sftp_port=settings.sftp_port
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    cinfo = {'host':sftp_hostname, 'username':sftp_user, 'private_key':sftp_key_file, 'port':sftp_port, 'cnopts':cnopts}
    return cinfo


class downloadItem:
    def __init__(self, fileno, filename, filesize, filedate):
        self.fileno = fileno
        self.filename = filename
        self.filesize = filesize
        self.filedate = filedate


class pageItem:
    def __init__(self, content, sectime, usectime, rdfolder):
        self.content = content
        self.sectime = sectime
        self.usectime = usectime
        self.rdfolder = rdfolder


def parseFileList(page_content):
    downloadItems = []
    try:
        page_content = page_content.rsplit('<table class="tbMainFileList" cols="4">')[1]
        #file_items = re.findall('trLine">\s+(.+?)</tr>', page_content)
        file_items = re.findall('trLine">\s+((.+<\/td>\s+)+)+<\/tr>', page_content)
        for file_item in file_items:
            file_item = file_item[0]
            fileno = re.findall('doDownload\((.+?),', file_item)[0]
            filename = re.findall('doDownload\(.+">(.+?)</a>', file_item)[0].replace('<br>','')  # todo weghalen <br>
            filesize_and_date = re.findall('tdFileList">(.+?)</td>', file_item)
            filesize = filesize_and_date[0]
            # Aug,12.2018 AM 09:58:40
            filedate = datetime.strptime(filesize_and_date[1],'%b,%d.%Y %p %H:%M:%S')
            downloadItems.append(downloadItem(fileno, filename, filesize, filedate))
            # laatste item is de nieuwste opname
    except Exception as ex:
        print("unexpected error while parsing html filelist")
    return downloadItems


def getPageContent():
    page_content0 = None
    print("trying to post login data")
    r = s.post('{0}Pwd.cgi?cmd=chk'.format(base_url), data=login_payload_json)
    print("login finished")
    start_remove_string='location.href="../cgi-bin/'
    end_remove_string='";'
    start_idx=r.text.find(start_remove_string) + len(start_remove_string)
    end_idx=r.text.rfind(end_remove_string)
    
    if start_idx==0 or end_idx==0:
        print("error, redir url not found, try again")
        print("start_idx={0} and end_idx={1}".format(start_idx, end_idx))
    else:
        redir_url = '{0}{1}'.format(base_url, r.text[start_idx:end_idx])
        new = s.get(redir_url)
        print("redir_url={0}".format(redir_url))
        start_idx = redir_url.rfind('sectime')
        if start_idx > 0:
            sectime_str=redir_url[start_idx+8:]
            sectime = int(sectime_str)
            print("trying to get MainRecStatus")    

            k6 = s.get('{0}MainRecStatus.cgi?cmd=init&sectime={1}'.format(base_url, sectime))
            print("trying to get MainRecControl")    
            k7 = s.get('{0}MainRecControl.cgi?cmd=init&sectime={1}'.format(base_url, sectime))
            print("trying to get MainFileList")    
            page_content = s.get('{0}MainFileList.cgi?cmd=init&sectime={1}'.format(base_url, sectime))
            page_content0 = pageItem(page_content, sectime, None, None)
        else:
            print("error, no sectime found")
    return page_content0


def update_session(page_item):
    pageItem0 = None
    page_content = page_item.content
    rdfolder_value = 1
    start_idx_usect = page_content.text.rfind('usectime')
    end_idx_usect = page_content.text[start_idx_usect:].find('\n')
    usectime_str = page_content.text[start_idx_usect+17:start_idx_usect+end_idx_usect-2]
    print("usectime_str={0}".format(usectime_str))
    usectime=int(usectime_str)
    payload2 = {'sectime': page_item.sectime, 'usectime': usectime, 'mainlistsectime': 1543153200,
                'mainlistusectime': 567, 'pagesectime': 1543153200, 'pageusectime': 571,
                'hdRecStatus': 5, 'edtStatus': ''}

    print("trying to post payload2")
    s.post('{0}MainRecStatus.cgi?cmd=init'.format(base_url), data=payload2)
    payload = {'sectime': page_item.sectime, 'usectime': usectime, 'rdfolder': rdfolder_value}
    print("trying to post session")
    print("sleep 1")
    time.sleep(1)
    k4 = s.get('{0}Session.cgi'.format(base_url))
    pageItem0 = pageItem(page_item.content, page_item.sectime, usectime, rdfolder_value)
    return pageItem0

def download_file(page_item, file_item):
    dest_file_name = None
    print("sleep 3")
    time.sleep(3)
    print("trying to post download req.")
    # payload = sectime, usectime, rdfolder
    payload = {'sectime': page_item.sectime, 'usectime': page_item.usectime, 'rdfolder': page_item.rdfolder}
    r3 = s.post('{0}MainFileList.cgi?cmd=download&fileno={1}'.format(base_url,file_item.fileno), data=payload, stream=True)
    if r3.status_code == 200:
        local_file_name = path.join(local_file_path, file_item.filename)
        print("now trying to save to {0}".format(local_file_name))

        size = (int(file_item.filesize[:-2]) * 1024) + 1024
        print("calcsize = {0} and filesize = {1}".format(size, file_item.filesize))
        #pbar = ProgressBar(maxval=size).start()
        file_content = []
        with open(local_file_name, 'wb') as f:
            for buf in r3.iter_content(1024):
                if buf:
                    f.write(buf)
                    progress = f.tell()
                    if progress % 1024000 == 0:  # elke MB loggen
                        print("progress={0}".format(progress))
                    #pbar.update(progress)
        #pbar.finish()
        dest_file_name = local_file_name
        print("finished downloading and saving")
    else:
        print("kan niet doorgaan: status_code is niet 200, maar {0}".format(r3.status_code))
    return dest_file_name

def sftp_upload_file(cinfo, dest_file_path):
    print("inside upload func")
    try:
        with pysftp.Connection(**cinfo) as sftp:
            with sftp.cd('records'):
                if not sftp.exists(path.basename(dest_file_path)):
                    sftp.put(dest_file_path)  # upload file to public/ on remote
                else:
                    print("bestand staat al op ftp, geen verdere actie...")
    except Exception as ex:
        print("fout bij FTP met reden: {0}".format(ex.args))


def sftp_check_exists(cinfo, dest_file_path):
    print("inside sftp check exists")
    # bewust True, want dat is fail-safe
    file_exists = True
    try:
        splitted_path = path.split(dest_file_path)
        if len(splitted_path)==2:
            filename = splitted_path[1]
            directory = splitted_path[0]
            with pysftp.Connection(**cinfo) as sftp:
                with sftp.cd(directory):
                    if not sftp.exists(filename):
                        file_exists = False
        else:
            print("fout bij splitsen sftp destination file path")
    except Exception as ex:
        print("fout bij sFTP check exists  met reden: {0}".format(ex.args))
    finally:
        return file_exists


def lambda_handler(event, context):
    result = False
    page_item = getPageContent()
    page_item = update_session(page_item)
    page_content = page_item.content
    dwnldItems = parseFileList(page_content.text)
    # todo automatisch /manueel uit args halen:
    automatic = True
    #dwnldItems = parseFileList(example_page_content)
    #dwnldItems = parseFileList(rr4)
    dwnldItems_json = {}
    for dwnld in dwnldItems:
        dwnldItems_json.update({dwnld.fileno: {"filename": dwnld.filename, "filesize": dwnld.filesize, "filedate": dwnld.filedate}})

    if automatic:
        print("automatic")
        today_or_next_sunday = (datetime.today() + timedelta( (6-date.today().weekday()) % 7 ))
        search_date = today_or_next_sunday
        #search_date = datetime(2019, 9, 1, 12, 59, 0)   # debug datetime
        print("search_date = {0}".format(search_date))

        search_date_min = datetime.min
        search_date_max = datetime.min
        if search_date.hour > 7 and search_date.hour < 14:
            print ("ochtenddienst")
            search_date_min = datetime(search_date.year, search_date.month, search_date.day, 7, 0, 0)
            search_date_max = datetime(search_date.year, search_date.month, search_date.day, 14, 0, 0)
        elif search_date.hour >= 14 and search_date.hour < 22:
            print ("avonddienst")
            search_date_min = datetime(search_date.year, search_date.month, search_date.day, 14, 0, 0)
            search_date_max = datetime(search_date.year, search_date.month, search_date.day, 22, 0, 0)
        else:
            print ("geen avond en geen morgendienst")
        matches = [it for it in dwnldItems if ((it.filedate > search_date_min and it.filedate < search_date_max) and (it.filesize[:-2]>10000))]
    else:
        print("manual")
        choosen_fileno = input("Type dienstnummer om te downloaden: ")
        print("Gekozen dienstnummer: %s" % choosen_fileno)
        matches = [it for it in dwnldItems if (int(it.fileno) == choosen_fileno)]

    if len(matches) == 1:
        print ("fileno={0}".format(matches[0].fileno))
        print ("filedate={0}".format(matches[0].filedate))
        print ("filename={0}".format(matches[0].filename))

        dest_base_path = '/records/'
        dest_file_name = matches[0].filename
        dest_file_full_path = path.join(dest_base_path, dest_file_name)

        sftp_file_exists = sftp_check_exists(sftp_get_cinfo(), dest_file_full_path)
        if not sftp_file_exists:
            print("sftp file bestaat nog niet, kan doorgaan..")
            downloaded_local_file_path = download_file(page_item, matches[0])
            print("download gereed, upload wordt gestart...")
            if downloaded_local_file_path is not None:
                sftp_upload_file(sftp_get_cinfo(), downloaded_local_file_path)
                print("upload gereed")
                result = True
            else:
                print("fout bij downloaden...")
            # todo verwijderen oude files...
        else:
            print("sftp file bestaat al, kan niet doorgaan, exit now..")
    elif len(matches) > 1:
        print("meerdere diensten gevonden")
        # todo: zoeken op basis van filesize en dan de grootste downloaden
    else:
        print("geen diensten gevonden, kan niet doorgaan met download")

    print("finished")
    return {
        'statusCode': 200,
        'body': json.dumps('lambdatest json={0}'.format(result))
    }


if __name__ == "__main__":
    print("this is an aws lambda function, which starts in the lambda_handler() function")
