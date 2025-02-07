from modules.utils import handle_request, download_one_file, sqlite_upsert_object, init_sqlite
from modules.config import config
import os
from modules.weibo import File


class User:
    def __init__(self, id):    # 0:普通用户 1:主用户
        # 初始化所有固定属性
        self.id = id
        self.nickname = ''
        self.gender = ''
        self.registration = ''
        self.birthday = ''
        self.location = ''
        self.introduction = ''
        self.avatar = ''
        self.weibo_count = ''
        self.following_count = ''
        self.follower_count = ''

        # 解析用户信息
        self.get_userinfo()
        # 设置并检查用户目录
        self.check_user_dir()
        # 初始创建数据库表（如果未创建）
        init_sqlite()
        # 下载头像，强制覆盖
        file = File(self.avatar, "avatar")
        download_one_file(file, force=True)
        # 插入数据库
        sqlite_upsert_object("users", self)
        del file.url
        sqlite_upsert_object("mappings", file, prime_key='file_name')
        print(f"成功获取用户信息: {self.id}_{self.nickname}")

    def __str__(self):
        """打印用户信息"""
        return ("\n".join(f"{key}: {value}" for key, value in self.__dict__.items())) + "\n"

    def check_user_dir(self):
        """检查用户目录"""
        os.makedirs('./weibo', exist_ok=True)
        config.user_dir = f'./weibo/{self.id}_{self.nickname}'
        # 检查当前的主用户的user_dir是否有相同id的目录，有就改成新名字，没有就新建
        for dir_name in os.listdir('./weibo'):
            dir_path = os.path.join('./weibo', dir_name)
            if os.path.isdir(dir_path) and dir_name.startswith(self.id):
                # 重命名目录
                os.rename(dir_path, config.user_dir)
                break
        else:
            # 如果未找到匹配的目录，创建新目录
            os.makedirs(config.user_dir, exist_ok=True)

    def get_userinfo(self):
        """获取用户信息"""
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=100505{self.id}'
        result = handle_request(url, 'json')
        info = result["data"]["userInfo"]
        # 必备字段，认为不可能没有，所以直接取，取不到就报错
        self.nickname = info["screen_name"]
        self.gender = info["gender"]
        self.introduction = info["description"]
        self.avatar = info["avatar_hd"].replace("/orj480/", "/large/")
        self.weibo_count = info["statuses_count"]
        self.following_count = info["follow_count"]
        self.follower_count = info["followers_count"]
        url = f'https://m.weibo.cn/api/container/getIndex?containerid=230283{self.id}_-_INFO'
        zh_list = ["生日", "所在地", "注册时间"]
        en_list = ["birthday", "location", "registration"]
        result = handle_request(url, 'json')
        cards = result["data"]["cards"]
        if isinstance(cards, list) and len(cards) > 1:
            card_list = cards[0]["card_group"] + cards[1]["card_group"]
            for card in card_list:
                if card.get("item_name") in zh_list:
                    setattr(self, en_list[zh_list.index(card.get("item_name"))], card.get("item_content"))




