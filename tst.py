
import os
import requests
from requests.adapters import HTTPAdapter

urls = ["https://f.us.sinaimg.cn/004AWTbIlx07jGkkjG7u01040201pjWI0k010.mp4?label=mp4_ld&template=640x360.28&ori=0&ps=1CwnkDw1GXwCQx&Expires=1738913655&ssig=4MlGo4eccl&KID=unistore,video"]

session = requests.Session()
session.mount('https://', HTTPAdapter(max_retries=5))
for url in urls:
    file_path = os.path.basename(url.split('?')[0])
    downloaded = session.get(url, timeout=10)
    # 如果没有扩展名，就从返回的header中尝试获取扩展名
    if not bool(os.path.splitext(file_path)[1]):
        content_type = downloaded.headers.get('Content-Type', '').lower()
        if 'image/jpeg' in content_type:
            file_path += '.jpg'
        elif 'image/png' in content_type:
            file_path += '.png'
        elif 'video/mp4' in content_type:
            file_path += '.mp4'
        elif 'video/quicktime' in content_type:
            file_path += '.mov'
        elif 'video/webm' in content_type:
            file_path += '.webm'
        elif 'image/gif' in content_type:
            file_path += '.gif'
        elif 'text/html' in content_type:
            file_path += '.txt'
    with open(file_path, 'wb') as f:
        f.write(downloaded.content)