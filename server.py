from flask import Flask, request, jsonify, send_from_directory, render_template
from modules.utils import random_wait
import sqlite3
from contextlib import closing
from datetime import datetime
import os
from modules.config import config
from bs4 import BeautifulSoup


PAGE_SIZE = 10

class Server:
    def __init__(self):
        self.cur_user = None
        self.user_list = []
        self.mappings_dict = {}

        self.get_user_list()
        self.app = Flask(__name__)
        self.setup_routes()


    def get_user_list(self):
        user_dirs = [d for d in os.listdir('./weibo') if os.path.isdir(os.path.join('./weibo', d))]
        for user_dir in user_dirs:
            with closing(sqlite3.connect(os.path.join('./weibo', user_dir, 'weibo.db'))) as conn:
                with conn:  # 使用事务
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM users')
                    result = cursor.fetchone()
                    columns = [column[0] for column in cursor.description]
                    user = dict(zip(columns, result))
                    cursor.execute('SELECT file_path FROM mappings WHERE file_name = ?', (os.path.basename(user['avatar'].split('?')[0]),))
                    result = cursor.fetchone()
                    user['avatar'] = result[0].replace('./', '/', 1)  # 只替换最前面的 './'
                    user['user_db'] = os.path.join('./weibo', user_dir, 'weibo.db')
                    self.user_list.append(user)

    def get_mappings_dict(self):
        with closing(sqlite3.connect(self.cur_user['user_db'])) as conn:
            with conn:  # 使用事务
                cursor = conn.cursor()
                cursor.execute('SELECT file_name, file_path FROM mappings where is_finish = 1')
                result = cursor.fetchall()
                self.mappings_dict = {row[0]: row[1] for row in result}

    def setup_routes(self): # 定义路由
        # 提供静态文件服务
        @self.app.route('/<path:path>')
        def serve_static(path):
            return send_from_directory('.', path)

        # 首页接口
        @self.app.route('/', methods=['GET'])
        def index():
            if len(self.user_list) == 1:
                self.cur_user = self.user_list[0]
                return profile(self.cur_user["id"])
            else:
                return render_template('index.html', users=self.user_list)

        # 全部微博接口（每页10条）
        @self.app.route('/profile/<int:user_id>', methods=['GET'])
        def profile(user_id):
            # 定位cur_user，不管有没有page都要先取用户信息（因为头像在这里）
            for user in self.user_list:
                if user['id'] == str(user_id):  # 检查用户 ID
                    self.cur_user = user
                    break   # 找到目标用户
                else:
                    msg = "未找到目标用户!"
                    return render_template('error.html', msg=msg)
            self.get_mappings_dict()
            if 'page' in request.args:
                # 按照page取weibos，返回局部weibos数据后拼接到原页面中
                page = request.args.get('page', type=int)
                with closing(sqlite3.connect(self.cur_user['user_db'])) as conn:
                    with conn:  # 使用事务
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM weibos WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                                       (user_id, PAGE_SIZE, page * PAGE_SIZE,))
                        weibos = cursor.fetchall()
                        columns = [column[0] for column in cursor.description]
                        # 将每一行数据转换为字典
                        weibos_dict = [dict(zip(columns, row)) for row in weibos]
                        # 将字段中的url映射成file_path
                        for weibo_dict in weibos_dict:
                            self.parser_url(weibo_dict)
                return render_template('ajax.html', user=self.cur_user, weibos=weibos_dict)
            else:
                # 没有page就返回基础页面
                return render_template('profile.html', user=self.cur_user)

        # 微博正文接口
        @self.app.route('/weibo/<int:weibo_id>', methods=['GET'])
        def weibo(weibo_id):
            if not self.cur_user:
                msg = "非法进入该页面!"
                return render_template('error.html', msg=msg)
            with closing(sqlite3.connect(self.cur_user['user_db'])) as conn:
                with conn:  # 使用事务
                    cursor = conn.cursor()
                    # 获取目标微博
                    cursor.execute('SELECT * FROM weibos WHERE id = ?', (weibo_id,))
                    weibo = cursor.fetchone()
                    columns = [column[0] for column in cursor.description]
                    weibo_dict = dict(zip(columns, weibo))

                    # 获取所有转发
                    cursor.execute('SELECT * FROM reposts WHERE weibo_id = ? ORDER BY created_at ASC', (weibo_id,))
                    reposts = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    reposts_dict = [dict(zip(columns, row)) for row in reposts]

                    # 获取所有评论
                    cursor.execute(
                        'SELECT *, ROW_NUMBER() OVER (PARTITION BY root_id ORDER BY created_at ASC) AS row_num FROM comments WHERE weibo_id = ?',
                        (weibo_id,))
                    comments = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    comments_dict = [dict(zip(columns, row)) for row in comments]
                self.parser_url(weibo_dict)
                for repost in reposts_dict:
                    self.parser_url(repost)
                for comment in comments_dict:
                    self.parser_url(comment)
                i = 0
                while i < len(comments_dict):
                    if comments_dict[i]['root_id'] != "":
                        if comments_dict[i]['id'] == comments_dict[i]['root_id']:
                            j = i
                            comments_dict[j]['reply'] = []
                            i += 1
                        else:
                            comments_dict[j]['reply'].append(comments_dict[i])
                            del comments_dict[i]
                    else:
                        i += 1
            if self.cur_user['id'] != str(weibo_dict['user_id']):
                msg = "目标用户与微博用户不匹配!"
                return render_template('error.html', msg=msg)
            print(weibo_dict)
            return render_template('weibo.html', user=self.cur_user, weibo=weibo_dict, reposts=reposts_dict, comments=comments_dict)

    def run(self, port=80):
        # webbrowser.open_new(f'http://localhost:{port}/')
        # 启动服务器
        if config.only_localhost:
            self.app.run(host='localhost', port=port) # 仅本机访问
        else:
            self.app.run(host='0.0.0.0', port=port) # 可外部访问

    def parser_url(self, dictionary):
        # user_avatar
        if 'user_avatar' in dictionary and dictionary['user_avatar']:
            dictionary['user_avatar'] = self.mappings_dict.get(os.path.basename(dictionary['user_avatar'].split('?')[0]), dictionary['user_avatar']).replace('./', '/')
        # text
        if 'content' in dictionary and dictionary['content']:
            soup = BeautifulSoup(dictionary['content'], 'html.parser')
            # 查找所有 <span class="url-icon"> 中的 <img> 标签
            for span in soup.find_all('span', class_='url-icon'):
                img = span.find('img')
                if img and 'src' in img.attrs:
                    file_path = self.mappings_dict.get(os.path.basename(img['src'].split('?')[0]), img['src']).replace('./', '/')
                    dictionary['content'] = dictionary['content'].replace(img['src'], file_path)
        # pic/pics
        if 'pic' in dictionary and dictionary['pic']:
            dictionary['pic'] = self.mappings_dict.get(os.path.basename(dictionary['pic'].split('?')[0]), dictionary['pic']).replace('./', '/')
        if 'pics' in dictionary and dictionary['pics']:
            dictionary['pics'] = dictionary['pics'].split(',')
            for i in range(len(dictionary['pics'])):
                dictionary['pics'][i] = self.mappings_dict.get(os.path.basename(dictionary['pics'][i].split('?')[0]), dictionary['pics'][i]).replace('./', '/')
        # video
        if 'video' in dictionary and dictionary['video']:
            dictionary['video'] = self.mappings_dict.get(os.path.basename(dictionary['video'].split('?')[0]), dictionary['video']).replace('./', '/')


if __name__ == '__main__':
    # 创建 Server 实例并运行
    server = Server()
    server.run()






