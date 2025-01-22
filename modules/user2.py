from modules.utils import handle_html, string_to_int, download_one_file, sqlite_insert_object
from modules.config import config
import os
import sqlite3
from contextlib import closing


class User2:
    def __init__(self, id, is_primary=False):    # 0:普通用户 1:主用户
        # 给每个属性都要赋初值，保证写入数据库时无误
        self.id = id
        self.is_primary = is_primary

        # 检查主用户（爬取对象）的数据目录是否已正确建立，并初始化数据库
        self.init_user()
        # 检查这个用户资料是否已经存在
        if not self.check_user():
            # 解析首页
            if self.is_primary:
                self.index_parser()
            # 解析用户详情页
            self.info_parser()
            # 解析头像
            self.avatar_parser(original=self.is_primary)
            # 插入数据库
            self.insert_user()
        else:
            # 用户已存在，要不要读出来？
            pass

    def __str__(self):
        """打印用户信息"""
        # 过滤掉空字符串和 0 的属性
        non_empty_attrs = [f"{key}: {value}" for key, value in self.__dict__.items() if value != '' and value != 0]
        # 将非空属性拼接成字符串
        return ("\n".join(non_empty_attrs) if non_empty_attrs else "Empty user") + "\n"

    def init_user(self):
        # 如果还没有设置user_dir，且不是主用户就报错
        if not hasattr(config, 'user_dir') and not self.is_primary:
            raise Exception("错误: user_dir 未设置，且 is_primary 为 False")
        if self.is_primary:
            # 通过主用户获取user_dir
            url = f'https://weibo.cn/{self.id}/info'
            selector = handle_html(config.cookie, url)
            nickname = selector.xpath("//div[@class='c'][3]/text()")[0]
            if nickname == '微博会员：':
                # 是cookie本人的需要特殊处理
                nickname = selector.xpath("//div[@class='c'][4]//text()")[1]
            nickname = nickname.split(':', 1)[1]
            config.user_dir = f'./weibo/{self.id}_{nickname}/'
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
            # 初始化数据库，建表
            with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
                with conn:  # 使用事务
                    cursor = conn.cursor()
                    # 如果users不存在则创建
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id text NOT NULL PRIMARY KEY,
                            is_primary INT CHECK (is_primary IN (0, 1)),
                            nickname text,
                            gender text,
                            location text,
                            birthday text,
                            introduction text,
                            verification text,
                            talent text,
                            education text,
                            work text,
                            weibo_count INT,
                            following_count INT,
                            follower_count INT,
                            page_count INT,
                            page_ported INT,
                            avatar text
                        )
                    ''')
                    # # 如果weibos不存在则创建
                    # cursor.execute('''
                    #     CREATE TABLE IF NOT EXISTS weibos (
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

    def check_user(self):
        with closing(sqlite3.connect(f'{config.user_dir}/weibo.db')) as conn:
            with conn:  # 使用事务
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE id = ?', (self.id,))
                result = cursor.fetchone()
                return True if result else False

    def index_parser(self):
        """解析首页"""
        url = f'https://weibo.cn/{self.id}/profile'
        selector = handle_html(config.cookie, url)
        user_info = selector.xpath("//div[@class='tip2']/*/text()")
        self.weibo_count = string_to_int(user_info[0][3:-1])
        self.following_count = string_to_int(user_info[1][3:-1])
        self.follower_count = string_to_int(user_info[2][3:-1])
        if selector.xpath("//input[@name='mp']") == []:
            self.page_count = 1
        else:
            self.page_count = (int)(selector.xpath("//input[@name='mp']")
                             [0].attrib['value'])

    def info_parser(self):
        print("info")
        """解析详细资料页"""
        url = f'https://weibo.cn/{self.id}/info'
        selector = handle_html(config.cookie, url)
        basic_info = selector.xpath("//div[@class='c'][3]/text()")
        if basic_info[0] == '微博会员：':
            # 是cookie本人的需要特殊处理
            basic_info = selector.xpath("//div[@class='c'][4]//text()")
            # 转换成相同的格式
            i = 0
            while i < len(basic_info):
                basic_info[i] += basic_info[i+1]
                del basic_info[i+1]
                i += 1
        zh_list = ['昵称', '性别', '地区', '生日', '简介', '认证', '达人']
        en_list = ['nickname', 'gender', 'location', 'birthday', 'introduction', 'verification', 'talent']
        for item in basic_info:
            if item.split(':', 1)[0] in zh_list:
                setattr(self, en_list[zh_list.index(item.split(':', 1)[0])],
                        item.split(':', 1)[1].replace('\u3000', ''))

    def avatar_parser(self, original=False):
        print("avatar")
        """解析并下载头像"""
        # 进入相册
        url = f'https://weibo.cn/{self.id}/photo?tf=6_008'
        selector = handle_html(config.cookie, url)
        # 头像相册
        result = selector.xpath('//img[@alt="头像相册"]/../@href')
        if len(result) == 0:    # 只有自己时会特殊吗？
            url = "https://weibo.cn/album/albumlist"
            selector = handle_html(config.cookie, url)
            result = selector.xpath('//img[@alt="头像相册"]/../@href')
        url = "https://weibo.cn" + result[0]
        selector = handle_html(config.cookie, url)
        # 取第一个是当前在用的
        result = selector.xpath('//div[@class="c"][3]//a/@href')
        if len(result) == 0:    # 只有自己时会特殊吗？
            result = selector.xpath('//div[@class="c"][4]//a/@href')
        url = "https://weibo.cn" + result[0]
        selector = handle_html(config.cookie, url)
        # 进入原图
        url = selector.xpath('//div[@class="c"][4]//a/@href')[0]
        if original:
            download_one_file(url, self, "img", "avatar", True)
        else:
            download_one_file(url.replace("/large/", "/square/"), self, "img", "avatar")
        self.avatar = url.split('/')[-1]

    def insert_user(self):
        sqlite_insert_object("users", self)


