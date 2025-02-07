from modules.utils import handle_request, try_format_time
from modules.config import config
import re
import json
import os




class Weibo:
    def __init__(self, mblog, is_reposted=False):
        # 过渡属性，初始化结束时删除
        self.mblog = mblog
        self.is_reposted = is_reposted
        self.reposted_weibo = None  # 这个属性要在porter.py中才删除
        # 初始化所有固定属性
        self.id = mblog["id"]
        self.bid = ''
        self.user_id = ''
        self.user_name = ''
        self.user_avatar = ''
        self.content = ''
        self.visibility = ''
        self.created_at = ''
        self.region_name = ''
        self.source = ''
        self.pics = ''
        self.video = ''
        self.read_count = ''
        self.play_count = ''
        self.repost_count = ''
        self.comment_count = ''
        self.like_count = ''
        self.reposted_id = ''
        # 检查
        if mblog.get('isLongText') or mblog.get('pic_num', 0) > 9:  # 被删除的微博取不到，所以用get
            self.mblog = self.get_long_weibo()
        # self.print_dict(mblog)
        # self.check_keys() # 检查相关字段
        # 解析构建实例
        self.parse_weibo()
        # 清理过渡属性
        del self.mblog
        del self.is_reposted

    def __str__(self):
        return f"微博id({self.id}): {self.content}"

    def extract_keys(self, data, parent_key='', separator='.'):
        result = set()  # 使用集合去重
        if isinstance(data, dict):  # 如果当前数据是字典
            for key, value in data.items():
                # 构造完整的键
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                # 递归处理值
                result.update(self.extract_keys(value, new_key, separator))
        elif isinstance(data, list):  # 如果当前数据是列表
            for item in data:
                # 跳过索引，直接递归处理列表中的每个元素
                result.update(self.extract_keys(item, parent_key, separator))
        else:  # 如果当前数据是基本类型（非字典或列表）
            if parent_key:  # 如果有父键，则保存
                result.add(parent_key)
        return result

    def print_dict(self, my_var, start=0):
        for k, v in my_var.items():
            if isinstance(v, dict):
                print(f'{" "*start}{k}:')
                self.print_dict(v, start+2)
            else:
                print(f'{" "*start}{k}:{v}')

    def check_keys(self):
        """检查必备字段是否都具备"""
        must_list = ['id', 'text', 'source', 'user.id', 'user.screen_name', 'user.profile_image_url',
                     'reposts_count', 'comments_count', 'attitudes_count', 'isLongText', 'pic_num', 'bid']
        key_list = self.extract_keys(self.mblog)
        # tmp = f"check_keys:{self.mblog['id']}: {self.mblog['text'][:30]}"
        # tmp1 = ""
        # for key in key_list:
        #     if key not in ignore_list:
        #         tmp1 += key + '\n'
        tmp2 = ""
        for key in must_list:
            if key not in key_list:
                tmp2 += key + '\n'
        # if tmp1 or tmp2:
        #     print(tmp)
        # if tmp1:
        #     print(f"未识别的key：\n{tmp1}")
        if tmp2:
            print(f"{self.mblog['id']}: {self.mblog['text'][:30]}缺少必备key：\n{tmp2}")

    def parse_weibo(self):
        """解析mblog中的内容"""
        # 必备字段，认为不可能没有，所以直接取，取不到就报错
        self.created_at = try_format_time(self.mblog["created_at"])
        self.content = self.mblog["text"]
        self.source = self.mblog["source"]
        if self.mblog["user"]:  # 某条被转发的微博被删除后，user可能是null，能取的字段不多
            self.user_id = self.mblog["user"]["id"]
            self.user_name = self.mblog["user"]["screen_name"]
            self.user_avatar = self.mblog["user"]["profile_image_url"]
            self.repost_count = self.mblog["reposts_count"]
            self.comment_count = self.mblog["comments_count"]
            self.like_count = self.mblog["attitudes_count"]
            if self.mblog['pic_num']:
                self.pics = ",".join([pic["large"]["url"] for pic in self.mblog["pics"]])
        self.bid = self.mblog["bid"]
        # 非必备字段，需要判断是否存在
        self.region_name = self.mblog.get("region_name")
        reposted_mblog = self.mblog.get("retweeted_status")
        if reposted_mblog and not self.is_reposted:
            self.reposted_weibo = Weibo(reposted_mblog, True)
            self.reposted_id = self.reposted_weibo.id
        self.visibility = self.mblog.get("title", {}).get("text")
        self.read_count = self.mblog.get("reads_count")
        page_info = self.mblog.get("page_info")
        if page_info:
            """已知的page_info["type"]:
            video: 视频 page_pic.url, page_url, title, *page_urls, play_count
            search_topic、: #话题卡片，不抓取 page_pic.url, page_url, page_title
            article: 头条文章，可以不抓取 page_pic.url, page_url, content1
            topic: 超话，不抓取 page_pic.url, page_url, page_title, content1
            place: 地点，不抓取
            webpage： 网页，不抓取
            hongbao： 红包，不抓取
            """
            type_list = ['video', 'search_topic', 'article', 'topic', 'place', 'webpage']
            if page_info["type"] not in type_list:
                print(f"未知的page_info['type']: {page_info['type']}")
            if page_info["type"] == "video":
                page_media_info = page_info.get("media_info", {})
                page_urls = page_info.get("urls", {})
                if page_urls:
                    page_urls.update(page_media_info)
                else:
                    page_urls = page_media_info
                # hevc_mp4_hd？
                # 已知ts_ld, ts_hd, mp4_ld, mp4_hd似乎无法下载
                url_type_list = ['mp4_720p_mp4', 'mp4_hd_mp4', 'stream_url_hd', 'mp4_ld_mp4', 'stream_url']
                for url_type in url_type_list:
                    if url_type in page_urls:
                        self.video = page_urls.get(url_type)
                        if self.video:
                            break
                self.play_count = page_info.get("play_count")
                for key in page_urls:
                    if key not in url_type_list and key != 'duration':
                        print(f"未知的url_type: {key}")

    def get_long_weibo(self):
        """单独获取单个微博的mblog"""
        url = f"https://m.weibo.cn/detail/{self.id}"
        result = handle_request(url, 'text')
        json_str = re.search(r'\$render_data\s*=\s*(\[.*?\])\s*\[\d*\]\s*\|\|\s*\{\};', result, re.DOTALL)
        if json_str:
            json_str = json_str.group(1)
            return json.loads(json_str)[0]['status']
        else:
            return self.mblog

class Repost:
    def __init__(self, weibo_id, data):
        # 初始化所有固定属性
        self.id = data['id']
        self.weibo_id = weibo_id
        self.created_at	= try_format_time(data['created_at'])
        self.source = data['source']
        self.content = data['text']
        self.user_id = data['user']['id']
        self.user_name = data['user']['screen_name']
        self.user_avatar = data['user']['profile_image_url']
        self.bid = data['bid']
        self.region_name = data.get('region_name', None)
        self.like_count = data['attitudes_count']

class Comment:
    def __init__(self, weibo_id, data, is_reply=False):
        # 初始化所有固定属性
        self.id = data['id']
        self.weibo_id = weibo_id
        self.created_at	= try_format_time(data['created_at'])
        self.source = data['source']
        self.root_id = data.get('rootid')   # 兼容老接口
        self.content = data['text']
        self.user_id = data['user']['id']
        self.user_name = data['user']['screen_name']
        self.user_avatar = data['user']['profile_image_url']
        self.bid = data.get('bid')  # 兼容老接口
        self.like_count = data.get('like_count', data.get("like_counts"))   # 兼容老接口
        self.pic = ''
        if data.get('pic'):
            self.pic = data['pic']["large"]["url"]
        self.is_reply = is_reply

class Like:
    def __init__(self, weibo_id, data):
        # 初始化所有固定属性
        self.id = data['id']
        self.weibo_id = weibo_id
        self.created_at	= try_format_time(data['created_at'])
        self.source = data['source']
        self.user_id = data['user']['id']
        self.user_name = data['user']['screen_name']
        self.user_avatar = data['user']['profile_image_url']

class File:
    def __init__(self, url, category):
        # 初始化所有固定属性
        if url.startswith('//'):
            self.url = 'https:' + url
        else:
            self.url = url
        self.category = category
        self.file_name = os.path.basename(url.split('?')[0])
        self.file_path = f"{config.user_dir}/{category}/{self.file_name}"
        self.is_finish = False
        if self.url.startswith('https://api.youku.com'):
            self.file_name = self.url.split('?')[1].split('=')[1]
            self.file_path = f"{config.user_dir}/{category}/{self.file_name}"
        # if not bool(os.path.splitext(self.file_name)[1]):
        #     print(f"{self.url}: {self.file_path} 没有扩展名...")

    def __str__(self):
        if hasattr(self, 'url') :
            return f'[{self.category}]{self.file_path}: {self.url}, {self.is_finish}'
        else:
            return f'[{self.category}]{self.file_path}: {self.is_finish}'

