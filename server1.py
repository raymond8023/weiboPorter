from flask import Flask, request, jsonify, send_from_directory, render_template
from modules.utils import random_wait, parser_url
import sqlite3
from contextlib import closing
from datetime import datetime
import webbrowser
import threading
import os



app = Flask(__name__)
PAGE_SIZE = 10


# 提供静态文件服务
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('./templates', path)


# 首页接口
@app.route('/', methods=['GET'])
def index():
    users = []
    user_dirs = [d for d in os.listdir('./weibo/') if os.path.isdir(os.path.join('./weibo/', d))]
    for user_dir in user_dirs:
        with closing(sqlite3.connect(os.path.join('./weibo/', user_dir, 'weibo.db'))) as conn:
            with conn:  # 使用事务
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users ')
                user = cursor.fetchone()
                columns = [column[0] for column in cursor.description]
                users.append(parser_url(dict(zip(columns, user))))
    if len(user_dirs) == 1:
        return profile(["用户id"])
    else:
        return render_template('index.html', users=users)

# 全部微博接口（每页10条）
@app.route('/profile/<int:user_id>', methods=['GET'])
def profile(user_id):
    # 不管有没有page都要先取用户信息（因为头像在这里）
    with open('../weibo/users.csv', mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)  # 使用 DictReader
        for row in reader:
            if row['用户id'] == str(user_id):  # 检查用户 ID
                user = row  # 找到目标用户
                break
        else:
            msg = "未找到目标用户!"
    if 'page' in request.args:
        # 按照page取weibos，返回局部weibos数据后拼接到原页面中
        page = request.args.get('page', type=int)
        with closing(sqlite3.connect('../weibo/weibodata.db')) as conn:
            with conn:  # 使用事务
                cursor = conn.cursor()
                if request.method == 'GET':
                    # 获取所有微博
                    cursor.execute('SELECT * FROM weibo WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
                                   (user_id, PAGE_SIZE, page * PAGE_SIZE,))
                    weibos = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]
                    # 将每一行数据转换为字典
                    weibos_dict = [dict(zip(columns, row)) for row in weibos]
        return render_template('ajax.html', user=user, weibos=weibos_dict)
    else:
        # 没有page就返回基础页面
        return render_template('profile.html', user=user)


# 微博正文接口
@app.route('/weibo/<int:weibo_id>', methods=['GET'])
def weibo(weibo_id):
    with closing(sqlite3.connect('../weibo/weibodata.db')) as conn:
        with conn:  # 使用事务
            cursor = conn.cursor()
            if request.method == 'GET':
                # 获取目标微博
                cursor.execute('SELECT * FROM weibo WHERE id = ?', (weibo_id,))
                weibo = cursor.fetchone()
                columns = [column[0] for column in cursor.description]
                weibo_dict = dict(zip(columns, weibo))  # 将每一行数据转换为字典
                # 获取所有转发
                cursor.execute('SELECT * FROM reposts WHERE weibo_id = ? ORDER BY created_at ASC', (weibo_id,))
                reposts = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                reposts_dict = [dict(zip(columns, row)) for row in reposts]
                i = 0
                while i < len(reposts_dict):
                    print(reposts_dict[i]['created_at'])
                    dt = datetime.strptime(reposts_dict[i]['created_at'], '%a %b %d %H:%M:%S %z %Y')
                    reposts_dict[i]['created_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    i += 1
                # 获取所有评论
                cursor.execute(
                    'SELECT *, ROW_NUMBER() OVER (PARTITION BY root_id ORDER BY created_at ASC) AS row_num FROM comments WHERE weibo_id = ?',
                    (weibo_id,))
                comments = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                comments_dict = [dict(zip(columns, row)) for row in comments]
                i = 0
                while i < len(comments_dict):
                    try:
                        dt = datetime.strptime(comments_dict[i]['created_at'], '%a %b %d %H:%M:%S %z %Y')
                        comments_dict[i]['created_at'] = dt.strftime('%Y-%m-%d')
                    except ValueError:
                        print(ValueError)
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
    with open('../weibo/users.csv', mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)  # 使用 DictReader
        for row in reader:
            if row['用户id'] == str(weibo_dict['user_id']):  # 检查用户 ID
                user = row  # 找到目标用户
                break
        else:
            msg = "未找到目标用户!"
            return render_template('error.html', msg=msg)
    return render_template('weibo.html', user=user, weibo=weibo_dict, reposts=reposts_dict, comments=comments_dict)

def open_browser():
    # 等待 Flask 应用启动
    random_wait()
    # 打开浏览器
    webbrowser.open_new('http://localhost/')

# 启动服务器
if __name__ == '__main__':
    # threading.Thread(target=open_browser).start()
    app.run(host='localhost', port=80)
    # app.run(host='0.0.0.0', port=80)
