from modules.utils import handle_request, download_one_file, sqlite_query, random_wait, sqlite_upsert_object
from modules.config import config
import math
import random
from time import sleep
from modules.weibo import Weibo, Comment, Repost, Like, File
from copy import deepcopy
from bs4 import BeautifulSoup
import os



class Porter:
    def __init__(self, user):
        # 初始化所有固定属性
        self.user = user
        self.weibo_list = []
        self.weibo_id_list = [item[0] for item in sqlite_query(f"SELECT id FROM weibos")]
        self.repost_list = []   # 转发指目标用户的微博被别人转发
        self.repost_id_list = [item[0] for item in sqlite_query(f"SELECT id FROM reposts")]
        self.comment_list = []
        self.comment_id_list = [item[0] for item in sqlite_query(f"SELECT id FROM comments")]
        self.like_list = []
        self.like_id_list = [item[0] for item in sqlite_query(f"SELECT id FROM likes")]
        self.download_list = [] # 记录待下载的url
        self.file_list = [item[0] for item in sqlite_query(f"SELECT DISTINCT file_name FROM mappings WHERE is_finish = 1")]   # 记录所有文件名
        self.max_page = math.ceil(self.user.weibo_count / 10)
        self.random_wait_pages = random.randint(*config.random_wait_pages)
        self.ported_count = sqlite_query(f"SELECT count(1) FROM weibos WHERE user_id = '{self.user.id}'")[0] # 搬运微博计数（只计算目标用户的微博）

    def start(self):
        """启动weibo搬运工"""
        # 待验证
        start_page = self.max_page - math.floor(self.ported_count / 10)
        print(f"将从第{start_page}页开始搬运微博...")
        for page in range(start_page, 0, -1):
            self.random_wait_pages -= 1
            if self.random_wait_pages <= 0:
                random_wait()
                self.random_wait_pages = random.randint(*config.random_wait_pages)

            # page = 170  # 调试用
            # 按照相同逻辑逐页搬运
            self.init_lists()
            self.get_one_page(page) # 初步获取page页的weibo
            self.update_weibo_list()    # 调整、补充细节
            self.download_files()
            self.insert_sqlite()
            print(f'共搬运{self.ported_count}条微博')
            # break   # 调试用
        print(f'搬运{self.user.nickname}微博完毕！')

    def init_lists(self):
        """每爬取一页前重置相关list"""
        self.weibo_list = []
        self.repost_list = []   # 转发指目标用户的微博被别人转发
        self.comment_list = []
        self.like_list = []
        self.download_list = []

    def get_one_page(self, page):
        """获取一页微博并初步解析，一次请求，得到一个待处理的weibo_list"""
        new_count = 0
        weibo_count = 0
        print(f"正在搬运第{self.max_page - page + 1}/{self.max_page}个页面...")
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=230413{self.user.id}&page={page}'
        result = handle_request(url, 'json')
        cards = result["data"]["cards"]
        for card in reversed(cards):
            if card["card_type"] == 11 and card.get("card_group"):
                card = card.get("card_group")[0]
            if card["card_type"] == 9:
                weibo_count += 1
                if card['mblog']["id"] not in self.weibo_id_list:
                    self.weibo_list.append(Weibo(card["mblog"]))
                    self.weibo_id_list.append(card['mblog']["id"])
                    new_count += 1
        # 展示该页微博、被转微博概览，同时将被转的微博提升出来
        for weibo in self.weibo_list:
            print(weibo)
            if weibo.reposted_weibo:
                if weibo.reposted_weibo.id not in self.weibo_id_list:
                    self.weibo_list.append(deepcopy(weibo.reposted_weibo))
                    self.weibo_id_list.append(weibo.reposted_weibo.id)
            del weibo.reposted_weibo
        print(f"{'-' * 30}已获取{self.user.nickname}({self.user.id})的第{page}页微博{new_count}/{weibo_count}条{'-' * 30}")

    def update_weibo_list(self):
        """遍历weibo_list中目标用户的微博，获取其转发、评论、点赞"""
        for weibo in self.weibo_list:
            if str(weibo.user_id) == str(self.user.id):  # 自己的微博
                if weibo.repost_count and config.repost_download:
                    self.get_reposts(weibo.id)
                if weibo.comment_count and config.comment_download:
                    self.get_comments(weibo.id)
                if weibo.like_count and config.like_download:
                    self.get_likes(weibo.id)
            self.parse_download(weibo)
        for repost in self.repost_list:
            self.parse_download(repost)
        for comment in self.comment_list:
            self.parse_download(comment)
        for like in self.like_list:
            self.parse_download(like)

    def get_reposts(self, weibo_id):
        """根据微博id获取所有转发"""
        repost_count = 0  # 用来记录某条微博一共搬运了多少评论及回复
        page = 0
        while True:
            page += 1
            url = f'https://m.weibo.cn/api/statuses/repostTimeline?id={weibo_id}&page={page}'
            result = handle_request(url, 'json')
            data = result.get('data')
            if not data:
                print(f"{weibo_id}取得了{repost_count}条转发[no data]")
                return
            reposts = data.get("data")
            for repost in reposts:
                if repost['id'] not in self.repost_id_list:
                    self.repost_list.append(Repost(weibo_id, repost))
                    self.repost_id_list.append(repost['id'])
                    repost_count += 1
            max_page = data.get("max")
            if page >= max_page:
                print(f"{weibo_id}取得了{repost_count}条转发[max_page]")
                return
            sleep(0.1)
            random_wait()

    def get_comments(self, weibo_id):
        """根据微博id获取所有评论"""
        comment_count = 0   # 用来记录某条微博一共搬运了多少评论及回复
        max_id = 0
        old_enable = False
        page = 0
        while True:
            if not old_enable:  # 新接口
                url = f'https://m.weibo.cn/comments/hotflow?id={weibo_id}&mid={weibo_id}&max_id_type=0&max_id={max_id}'
                try:
                    result = handle_request(url, 'json')
                except ValueError as e:  # 如果解析失败会抛出 ValueError
                    print("新接口获取失败")
                    old_enable = True
                    continue
            else:
                page += 1
                url = f'https://m.weibo.cn/api/comments/show?id={weibo_id}&page={page}'
                result = handle_request(url, 'json')
            data = result.get('data')
            if not data:
                print(f"{weibo_id}取得了{comment_count}条评论[no data]")
                return
            comments = data.get('data')
            for comment in comments:
                if comment['id'] not in self.comment_id_list:
                    self.comment_list.append(Comment(weibo_id, comment))
                    self.comment_id_list.append(comment['id'])
                    comment_count += 1
                if comment.get('comments', False):
                    replies = comment['comments']
                    if comment['max_id'] == 0:  # 直接就能取完
                        for reply in replies:
                            if reply['id'] not in self.comment_id_list:
                                self.comment_list.append(Comment(weibo_id, reply, True))
                                self.comment_id_list.append(reply['id'])
                                comment_count += 1
                    else:   # 不能直接取完，需要单独获取
                        comment_count += self.get_replies(weibo_id, comment['id'])
            if not old_enable:  # 新接口
                max_id = data.get("max_id")
                if max_id == 0:
                    print(f"{weibo_id}取得了{comment_count}条评论[max_id]")
                    return
            else:  # 老接口
                max_page = data.get("max")
                if page >= max_page:
                    print(f"{weibo_id}取得了{comment_count}条评论[max_page]")
                    return
            sleep(0.1)
            random_wait()

    def get_replies(self, weibo_id, comment_id):
        """根据评论id获取所有该评论的回复"""
        relpy_count = 0 # 记录某个评论有几条回复
        max_id = 0
        while True:
            url = f'https://m.weibo.cn/comments/hotFlowChild?cid={comment_id}&max_id={max_id}&max_id_type=0'
            result = handle_request(url, 'json')
            replies = result.get('data')
            if not replies:
                return relpy_count
            for reply in replies:
                if reply['id'] not in self.comment_id_list:
                    self.comment_list.append(Comment(weibo_id, reply, True))
                    self.comment_id_list.append(reply['id'])
                    relpy_count += 1
            max_id = result.get("max_id")
            if max_id == 0:
                return relpy_count
            sleep(0.1)
            random_wait()

    def get_likes(self, weibo_id):
        """根据微博id/获取所有点赞"""
        like_count = 0  # 用来记录某条微博一共搬运了多少评论及回复
        page = 0
        while True:
            page += 1
            url = f'https://m.weibo.cn/api/attitudes/show?id={weibo_id}&page={page}'
            result = handle_request(url, 'json')
            data = result.get('data')
            if not data:
                print(f"{weibo_id}取得了{like_count}条点赞[no data]")
                return
            likes = data.get("data")
            if likes:
                for like in likes:
                    if like['id'] not in self.like_id_list:
                        self.like_list.append(Like(weibo_id, like))
                        self.like_id_list.append(like['id'])
                        like_count += 1
            max_page = data.get("max")
            if page >= max_page:
                print(f"{weibo_id}取得了{like_count}条点赞[max_page]")
                return
            sleep(0.1)
            random_wait()

    def parse_download(self, obj):
        """从搬运的信息中提取需要下载的文件信息Weibo, Repost, Comment, Like"""
        # user_avatar
        if hasattr(obj, 'user_avatar') and obj.user_avatar:
            if os.path.basename(obj.user_avatar.split('?')[0]) not in self.file_list:
                file = File(obj.user_avatar, 'avatar')
                self.download_list.append(file)
                self.file_list.append(file.file_name)
        # text
        if hasattr(obj, 'content') and obj.content:
            # print(obj.content)
            soup = BeautifulSoup(obj.content, 'html.parser')
            # 查找所有 <span class="url-icon"> 中的 <img> 标签
            for span in soup.find_all('span', class_='url-icon'):
                img = span.find('img')
                if img and 'src' in img.attrs:
                    if os.path.basename(img['src'].split('?')[0]) not in self.file_list:
                        file = File(img['src'], 'url-icon')
                        self.download_list.append(file)
                        self.file_list.append(file.file_name)
        # pic/pics
        if hasattr(obj, 'pic') and obj.pic and config.pic_download:
            if os.path.basename(obj.pic.split('?')[0]) not in self.file_list:
                file = File(obj.pic, 'pic')
                self.download_list.append(file)
                self.file_list.append(file.file_name)
        if hasattr(obj, 'pics') and obj.pics and config.pic_download:
            for url in obj.pics.split(','):
                if os.path.basename(url.split('?')[0]) not in self.file_list:
                    file = File(url, 'pic')
                    self.download_list.append(file)
                    self.file_list.append(file.file_name)
        # video
        if hasattr(obj, 'video') and obj.video and config.video_download:
            if os.path.basename(obj.video.split('?')[0]) not in self.file_list:
                file = File(obj.video, 'video')
                self.download_list.append(file)
                self.file_list.append(file.file_name)

    def download_files(self):
        """下载文件，不覆盖"""
        download_count = 0
        for file in self.download_list:
            download_count += download_one_file(file)
        print(f"download_list完成: {download_count}/{len(self.download_list)}")
        for file in self.download_list:
            if not file.is_finish:
                print(file)


    def insert_sqlite(self):
        for repost in self.repost_list:
            sqlite_upsert_object("reposts", repost)
        for comment in self.comment_list:
            sqlite_upsert_object("comments", comment)
        for like in self.like_list:
            sqlite_upsert_object("likes", like)
        for file in self.download_list:
            del file.url
            sqlite_upsert_object("mappings", file, prime_key='file_name')
        # 插入微博放到最后，因为一旦完成插入就认为这条微博相关的数据都已经搬运完了，因此记ported_count+1
        for weibo in self.weibo_list:
            sqlite_upsert_object("weibos", weibo)
            if str(weibo.user_id) == str(self.user.id):  # 自己的微博
                self.ported_count += 1
