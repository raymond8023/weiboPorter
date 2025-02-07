import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from lxml import etree
import os
from modules.config import config
import sqlite3
from contextlib import closing
from time import sleep
from datetime import datetime
import re
import random
from tqdm import tqdm


RETRY_STRATEGY = Retry(
    total=config.max_retries,  # 最大重试次数
    backoff_factor=1,  # 重试间隔时间（指数退避）
    status_forcelist=[500, 502, 503, 504, 408, 429],  # 需要重试的状态码
)

_request_counter = random.randint(*config.random_wait_requests)

def check_cookie():
    # 将 Cookie 字符串转换为字典
    cookies = {}
    for item in config.cookie.split(';'):
        key, value = item.strip().split('=', 1)  # 按第一个等号分割
        cookies[key] = value
    # 尝试取用户页看能成功不
    url = f'https://m.weibo.cn/profile/{config.user_id_list[0]}'
    result = handle_request(url , 'text')
    uid = re.search(r"uid:\s*'([^']*)'", result)
    if uid:
        uid = uid.group(1)
        if uid != '':
            # 检查是否有过期时间字段
            if 'ALF' in cookies:
                expires_time = datetime.fromtimestamp(int(cookies['ALF']))  # 获取过期时间
                current_time = datetime.now()
                # 判断是否过期或即将过期（小于12个小时）
                if (expires_time - current_time).total_seconds() / 3600 > 12:
                    print("cookie 正常")
                    return
                else:
                    raise Exception(f"cookie 过期或即将过期，过期时间: {expires_time}")
    else:
        raise Exception("cookie 或 user_id 无效")

def handle_request(url, return_type='html'):
    """处理requests，返回type类型的数据，加入指数退让的retry机制"""
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'
    headers = {'User_Agent': user_agent, 'Cookie': config.cookie}
    response = None
    retries = 0
    while retries < config.max_retries:
        try:
            request_counter()
            print(url)
            response = requests.get(url, headers=headers, timeout=config.request_timeout)
            response.raise_for_status()  # 检查状态码是否为 2xx
            break
        except Exception as e:
            retries += 1
            print(f"handle_request尝试{retries}/{config.max_retries}:{e}, url={url}, return_type={return_type}")
            if retries < config.max_retries:
                sleep(config.delay_factor * 2 ** retries)  # 指数退避一段时间后重试
            else:
                error_file = f'{config.user_dir}/request_failed.txt'
                with open(error_file, 'a', encoding='utf-8-sig') as f:
                    f.write(f'失败:{e}, url={url}, return_type={return_type}')
                print(f'handle_request失败:{e}, url={url}, return_type={return_type}')
    if return_type == 'html':
        return etree.HTML(response.content)
    elif return_type == 'json':
        return response.json()
    elif return_type == 'text':
        return response.text
    elif return_type == 'raw':
        return response

def download_one_file(file, force=False):
    """下载单个文件(图片/视频)"""
    try:
        if not os.path.isfile(file.file_path) or force:  # 如果文件已存在就不下载
            request_counter()
            print(f'download: {file.url}')
            os.makedirs(os.path.dirname(file.file_path), exist_ok=True)
            session = requests.Session()
            session.mount(file.url, HTTPAdapter(max_retries=RETRY_STRATEGY))
            downloaded = session.get(file.url, timeout=config.request_timeout)
            # 如果没有扩展名，就从返回的header中尝试获取扩展名
            if not bool(os.path.splitext(file.file_path)[1]):
                content_type = downloaded.headers.get('Content-Type', '').lower()
                if 'image/jpeg' in content_type:
                    file.file_path += '.jpg'
                elif 'image/png' in content_type:
                    file.file_path += '.png'
                elif 'video/mp4' in content_type:
                    file.file_path += '.mp4'
                elif 'video/quicktime' in content_type:
                    file.file_path += '.mov'
                elif 'video/webm' in content_type:
                    file.file_path += '.webm'
                elif 'image/gif' in content_type:
                    file.file_path += '.gif'
                elif 'text/html' in content_type:
                    file.file_path += '.txt'
            with open(file.file_path, 'wb') as f:
                f.write(downloaded.content)
            file.is_finish = True
            return 1
        elif os.path.isfile(file.file_path):
            file.is_finish = True
            return 1
    except Exception as e:
        error_file = f'{config.user_dir}/download_failed.txt'
        with open(error_file, 'a', encoding='utf-8-sig') as f:
            f.write(f'{file.file_path} : {file.url}\n')
        print(f'download failed:{file.url}, {e}')
    return 0

def sqlite_upsert_object(table, obj, prime_key='id'):
    """插入/更新obj对象到数据库的table表中"""
    obj_dict = vars(obj)
    columns = ', '.join(obj_dict.keys())
    placeholders = ', '.join('?' * len(obj_dict))
    update_columns = ', '.join([f"{key} = ?" for key in obj_dict.keys()])
    with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
        with conn:  # 使用事务
            cursor = conn.cursor()
            sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT({prime_key}) DO UPDATE SET {update_columns};'
            cursor.execute(sql, tuple(obj_dict.values()) * 2)

def sqlite_query(sql):
    """查询一行数据，返回对象"""
    with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
        with conn:  # 使用事务
            cursor = conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()  # 获取所有数据
            if len(result) == 1:  # 如果只有一行数据
                return result[0]  # 返回单行数据
            else:  # 如果有多行数据
                return result  # 返回所有数据

def random_wait():
    seconds = random.randint(*config.random_wait_seconds)
    # tqdm.write(f"休息 {seconds} 秒，马上回来...")
    sleep(0.1)  # 防止进度条乱跳
    for i in tqdm(range(seconds), leave=False):
        sleep(1)

def request_counter():
    global _request_counter
    # print(_request_counter)
    _request_counter -= 1
    if _request_counter <= 0:
        random_wait()
        _request_counter = random.randint(*config.random_wait_requests)

def try_format_time(time_str):
    """自定义过滤器：用户渲染模板中统一时间格式"""
    try:
        # 尝试解析时间字符串
        dt = datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
        # 返回格式化后的时间
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        # 如果解析失败，返回原始字符串
        return time_str

def init_sqlite():
    """初始化数据库，建表"""
    with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
        with conn:  # 使用事务
            cursor = conn.cursor()
            # 如果users不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id text NOT NULL PRIMARY KEY,
                    nickname text,
                    gender text,
                    registration text,
                    birthday text,
                    location text,                            
                    introduction text,
                    avatar text,
                    weibo_count text,
                    following_count text,
                    follower_count text
                )
            ''')
            # 如果weibos不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weibos (
                    id text NOT NULL PRIMARY KEY,
                    bid text NOT NULL,
                    user_id text,
                    user_name text,
                    user_avatar text,
                    content text,
                    visibility text,                    
                    created_at text,
                    region_name text,
                    source text,                    
                    pics text,
                    video text,    
                    read_count text,
                    play_count text,      
                    repost_count text,
                    comment_count text,
                    like_count text,
                    reposted_id text
                )
            ''')
            # 如果comments不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id text NOT NULL PRIMARY KEY,
                    weibo_id text,
                    created_at text,
                    source text,
                    root_id text,
                    content text,
                    user_id text,
                    user_name text,
                    user_avatar text,
                    bid text,
                    like_count text,
                    pic text,
                    is_reply BOOLEAN DEFAULT FALSE
                )
            ''')
            # 如果reposts不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reposts (
                    id text NOT NULL PRIMARY KEY,
                    weibo_id text,
                    created_at text,
                    source text,
                    content text,
                    user_id text,
                    user_name text,
                    user_avatar text,
                    bid text,                    
                    region_name text,
                    like_count text
                )
            ''')
            # 如果likes不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS likes (
                    id text NOT NULL PRIMARY KEY,
                    weibo_id text,
                    created_at text,
                    source text,
                    user_id text,
                    user_name text,
                    user_avatar text
                )
            ''')
            # 如果mappings不存在则创建
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mappings (
                    file_name text NOT NULL PRIMARY KEY,
                    category text,
                    file_path text,
                    is_finish BOOLEAN DEFAULT FALSE
                )
            ''')
