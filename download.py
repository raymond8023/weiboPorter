from requests.adapters import HTTPAdapter
import os
from modules.config import config
import requests


def download_one_file(url, file_type, category, force=False):
    """下载单个文件(图片/视频)"""
    file_path = f'./{url.split("/")[-1].split("?")[0]}'
    try:
        if not os.path.isfile(file_path) or force:  # 如果文件已存在就不下载
            session = requests.Session()
            session.mount(url, HTTPAdapter(max_retries=config.max_retries))
            downloaded = session.get(url, timeout=config.request_timeout)
            with open(file_path, 'wb') as file:
                file.write(downloaded.content)
    except Exception as e:
        print(f'download failed:{url}, {e}')

url = "https://wx3.sinaimg.cn/large/002TLsr9ly8hrvt29nqryj60dw0dw0t902.jpg"
download_one_file(url, 'xxx', '')