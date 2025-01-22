import requests
from requests.adapters import HTTPAdapter
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


def check_cookie():
    # 将 Cookie 字符串转换为字典
    cookies = {}
    for item in config.cookie.split(';'):
        key, value = item.strip().split('=', 1)  # 按第一个等号分割
        cookies[key] = value
    # 尝试取用户页看能成功不
    url = f'https://m.weibo.cn/profile/{config.user_id_list[0]}'
    result = handle_request(config.cookie, url , 'text')
    uid = re.search(r"uid:\s*'([^']*)'", result).group(1)
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

def retry(func, *args, **kwargs):
    """反复尝试执行函数 func，最多尝试 config.retry[0] 次。"""
    retries = 0
    while retries < config.max_retries:
        try:
            result = func(*args, **kwargs)  # 尝试执行函数
            return result  # 如果成功，返回结果
        except Exception as e:
            retries += 1
            print(f"尝试 {retries}/{config.max_retries} 失败: {e} func={func.__name__}, args={args}, kwargs={kwargs}")
            if retries < config.max_retries:
                sleep(config.delay_factor ** retries)  # 等待一段时间后重试
            else:
                error_file = f'{config.user_dir}/retry_failed.txt'
                with open(error_file, 'a', encoding='utf-8-sig') as file:
                    file.write(f'func={func.__name__}, args={args}, kwargs={kwargs}\n')
                print(f'retry failed: {e} func={func.__name__}, args={args}, kwargs={kwargs}')

def handle_request(cookie, url, return_type='html'):
    """处理requests，返回type类型的数据"""
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'
    headers = {'User_Agent': user_agent, 'Cookie': cookie}
    response = requests.get(url, headers=headers, timeout=config.request_timeout)
    response.raise_for_status()  # 检查状态码是否为 2xx
    if return_type == 'html':
        return etree.HTML(response.content)
    elif return_type == 'json':
        return response.json()
    elif return_type == 'text':
        return response.text

def download_one_file(url, file_type, category, force=False):
    """下载单个文件(图片/视频)"""
    file_path = f'{config.user_dir}/{file_type}/{category}/{url.split("/")[-1]}'
    try:
        if not os.path.isfile(file_path) or force:  # 如果文件已存在就不下载
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            session = requests.Session()
            session.mount(url, HTTPAdapter(max_retries=config.max_retries))
            downloaded = session.get(url, timeout=config.request_timeout)
            with open(file_path, 'wb') as file:
                file.write(downloaded.content)
    except Exception as e:
        error_file = f'{config.user_dir}/download_failed.txt'
        with open(error_file, 'a', encoding='utf-8-sig') as file:
            file.write(f'{file_path} : {url}\n')
        print(f'download failed:{url}, {e}')

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
            # # 如果comments不存在则创建
            # cursor.execute('''
            #     CREATE TABLE IF NOT EXISTS comments (
            #         id text NOT NULL PRIMARY KEY,
            #         is_primary INT CHECK (is_active IN (0, 1)),
            #         nickname text,
            #         gender text,
            #         location text,
            #         birthday text,
            #         introduction text,
            #         verification text,
            #         talent text,
            #         education text,
            #         work text,
            #         weibo_count INT,
            #         following_count INT,
            #         follower_count INT,
            #         page_count INT,
            #         page_ported INT,
            #         avatar text
            #     )
            # ''')

def sqlite_upsert_object(table, obj):
    """插入/更新obj对象到数据库的table表中"""
    obj_dict = vars(obj)
    columns = ', '.join(obj_dict.keys())
    placeholders = ', '.join('?' * len(obj_dict))
    update_columns = ', '.join([f"{key} = ?" for key in obj_dict.keys()])
    with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
        with conn:  # 使用事务
            cursor = conn.cursor()
            sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {update_columns};'
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
    tqdm.write(f"休息 {seconds} 秒，马上回来...")
    for i in tqdm(range(seconds), leave=False):
        sleep(1)
