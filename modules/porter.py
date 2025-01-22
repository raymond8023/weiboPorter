from modules.utils import handle_request, retry, download_one_file, sqlite_query, random_wait, sqlite_upsert_object
from modules.config import config
import sqlite3
from contextlib import closing
from datetime import datetime
import math
import random
from time import sleep
from tqdm import tqdm
from modules.weibo import Weibo
from copy import deepcopy



class Porter:
    def __init__(self, user):
        self.user = user
        self.weibo_id_list = [item[0] for item in sqlite_query(f"SELECT id FROM weibos")]
        self.max_page = math.ceil(self.user.weibo_count / 10)
        self.random_wait_pages = random.randint(*config.random_wait_pages)
        self.ported_count = sqlite_query(f"SELECT count(1) FROM weibos WHERE id = '{self.user.id}'")[0] # 搬运微博计数（只计算目标用户的微博）



    def start(self):
        """启动weibo搬运工"""
        # 待验证
        start_page = self.max_page - math.floor(self.ported_count / 10)
        print(f"将从第{start_page}页开始搬运微博...")
        for page in range(start_page, 0, -1):
            if self.random_wait_pages:
                self.random_wait_pages -= 1
            else:
                random_wait()
                self.random_wait_pages = random.randint(*config.random_wait_pages)


            page = 1


            self.init_lists()
            self.get_one_page(page) # 初步获取page页的weibo
            self.update_weibo_list()    # 调整、补充细节
            print(self.reposted_list)
            self.download_files()
            self.insert_sqlite()


            break

    def init_lists(self):
        self.weibo_list = []
        self.reposted_list = [] # 被转发指目标用户转发别人的原始微博
        self.repost_list = []   # 转发指目标用户的微博被别人转发
        self.comment_list = []
        self.like_list = []
        self.download_list = []

    def get_one_page(self, page):
        """获取一页微博并初步解析，一次请求，得到一个待处理的weibo_list"""
        print(f"正在搬运第{self.max_page - page + 1}/{self.max_page}个页面...")
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=230413{self.user.id}&page={page}'
        result = retry(handle_request,config.cookie, url, 'json')
        cards = result["data"]["cards"]
        for card in reversed(cards):
            if card["card_type"] == 11 and card.get("card_group"):
                card = card.get("card_group")[0]
            if card["card_type"] == 9:
                self.weibo_list.append(Weibo(card["mblog"]))
                self.ported_count += 1
        for weibo in self.weibo_list:
            print(weibo)
        print(f"{'-' * 30}已获取{self.user.nickname}({self.user.id})的第{page}页微博{'-' * 30}")

    def update_weibo_list(self):
        """遍历weibo_list：id存在的，忽略；转发的，要将reposted_weibo取出并删除字段；有转发、评论、点赞的，要单独获取？需要下载的，下载文件？"""
        i = 0
        while i < len(self.weibo_list):
            if self.weibo_list[i].id in self.weibo_id_list:
                del self.weibo_list[i]
            else:
                if hasattr(self.weibo_list[i], 'reposted_weibo'):
                    self.reposted_list.append(deepcopy(self.weibo_list[i].reposted_weibo))
                    del self.weibo_list[i].reposted_weibo
                if self.weibo_list[i].repost_count:
                    pass
                if self.weibo_list[i].comment_count:
                    pass
                if self.weibo_list[i].like_count:
                    pass
                i += 1
        i = 0
        while i < len(self.reposted_list):
            if self.reposted_list[i].id in self.weibo_id_list:
                del self.reposted_list[i]
            else:
                i += 1

    def download_files(self):
        pass

    # self.download_list

    def insert_sqlite(self):
        for weibo in self.weibo_list:
            sqlite_upsert_object("weibos", weibo)
        for weibo in self.reposted_list:
            sqlite_upsert_object("weibos", weibo)
        for repost in self.repost_list:
            sqlite_upsert_object("reposts", repost)
        for comment in self.comment_list:
            sqlite_upsert_object("comments", comment)
        for like in self.like_list:
            sqlite_upsert_object("likes", like)
