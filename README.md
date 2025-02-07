# weiboPorter 微博搬运工

- [weiboPorter](#weiboporter-微博搬运工)
  - [功能](#功能)
  - [运行环境](#运行环境)
  - [使用说明](#使用说明)
    - [1.搬运脚本](#1搬运脚本)
    - [2.安装依赖](#2安装依赖)
    - [3.程序设置](#3程序设置)
    - [4.运行脚本](#4运行脚本)

## 功能
项目出于备份微博的初衷，旨在爬取指定用户（通过user_id）所有微博及相关转发、评论、点赞（可选）内容到本地，通过sqlite保存。为了便于查看，可以启动服务器端，按照m.weibo.cn类似的风格在本地复现。主要功能包括：
* 搬运微博
* * 搬运用户**原创和转发**的微博
* * 搬运用户**原创和转发**微博下的评论（可选）
* * 搬运用户**原创和转发**微博下的转发（可选）
* * 搬运用户**原创和转发**微博下的点赞（可选）
* * 写入**SQLite数据库**
* 搬运图片/视频
* * 搬运用户**原创和转发**微博中的原始**图片**（可选）
* * 搬运用户**原创和转发**微博中的**视频**（可选）
* 复现微博
* * 将备份的微博内容复现成类似m.weibo.cn的风格

## 使用说明

### 1.搬运脚本

```bash
git clone https://github.com/raymond8023/weiboPorter.git
```

运行上述命令，将本项目搬运到当前目录，如果搬运成功当前目录会出现一个名为"weiboPorter"的文件夹；

### 2.安装依赖

```bash
pip install -r requirements.txt
```

### 3.程序设置

打开**config.json**文件，你会看到如下内容：

```
{
    "user_id_list": [""],
    "repost_download": 1,
    "comment_download": 1,
    "like_download": 1,
    "pic_download": 1,
    "video_download": 1,
    "random_wait_pages": [1, 5],
    "random_wait_requests": [3, 17],
    "random_wait_seconds": [5, 10],
	"max_retries": 5,
    "delay_factor": 2,
    "request_timeout": 10,
    "cookie": "",
    "only_localhost": 0
}
```

下面讲解每个参数的含义与设置方法。

**设置user_id_list（必须）**

user_id_list是我们要爬取的微博的user_id，可以是一个，也可以是多个，例如：

```
"user_id_list": ["1223178222", "1669879400", "1729370543"],
```

上述代码代表我们要连续爬取user_id分别为“1223178222”、 “1669879400”、 “1729370543”的三个用户的微博。

1.打开网址<https://weibo.cn>，搜索我们要找的人，如"迪丽热巴"，进入她的主页；

![](https://github.com/dataabc/media/blob/master/weiboSpider/images/user_home.png)
2.按照上图箭头所指，点击"资料"链接，跳转到用户资料页面；

![](https://github.com/dataabc/media/blob/master/weiboSpider/images/user_info.png)
如上图所示，迪丽热巴微博资料页的地址为"<https://weibo.cn/1669879400/info>"，其中的"1669879400"即为此微博的user_id。

事实上，此微博的user_id也包含在用户主页(<https://weibo.cn/u/1669879400?f=search_0>)中，之所以我们还要点击主页中的"资料"来获取user_id，是因为很多用户的主页不是"<https://weibo.cn/user_id?f=search_0>"的形式，而是"<https://weibo.cn/个性域名?f=search_0>"或"<https://weibo.cn/微号?f=search_0>"的形式。其中"微号"和user_id都是一串数字，如果仅仅通过主页地址提取user_id，很容易将"微号"误认为user_id。

**设置可选项（可不修改）**

```
    "repost_download": 1,
    "comment_download": 1,
    "like_download": 1,
    "pic_download": 1,
    "video_download": 1,
```

repost_download 是否搬运转发

comment_download 是否搬运评论

like_download 是否搬运点赞

pic_download 是否搬运图片

video_download 是否搬运视频

值为1代表是，0代表否，默认全部都是1。

**设置random_wait参数（可不修改）**

```
    "random_wait_pages": [1, 5],
    "random_wait_requests": [3, 17],
    "random_wait_seconds": [5, 10],
```

random_wait_pages表示每爬取random.randint(1,5)页，会触发一次等待

random_wait_requests表示每请求random.randint(3,17)次，会触发一次等待

random_wait_seconds表示每次等待random.randint(5,10)秒

为了避免被封，默认值较保守，如有必要可以自行调整

**设置下载重试参数（可不修改）**

```
	"max_retries": 5,
    "delay_factor": 2,
    "request_timeout": 30,
```

max_retries表示下载失败时最多重试5次

delay_factor表示回退因子为2秒

request_timeout表示最大等待时间是30秒

这三个参数一般不用修改

**设置cookie（必须）**

使用自己的cookie可搬运仅自己可见或好友可见的微博。

```
"cookie": "your cookie",
```

1.用Chrome打开<https://passport.weibo.cn/signin/login>；

2.输入微博的用户名、密码，登录，如图所示：
![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie1.png)
登录成功后会跳转到<https://m.weibo.cn>;

3.按F12键打开Chrome开发者工具，在地址栏输入并跳转到<https://weibo.cn>，跳转后会显示如下类似界面:
![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie2.png)
4.依此点击Chrome开发者工具中的Network->Name中的weibo.cn->Headers->Request Headers，"Cookie:"后的值即为我们要找的cookie值，复制即可，如图所示：
![](https://github.com/dataabc/media/blob/master/weiboSpider/images/cookie3.png)

**设置only_localhost（可不修改）**

```
"only_localhost": 0,
```

值为1，仅支持localhost访问；默认为0，表示可以从其他地址访问。

### 4.运行脚本

运行weiboPorter.py启动搬运工

搬运完成后，可运行server.py启动复现服务器

## 注意事项
* 为了支持“断点续爬”和持续更新，爬取微博按照时间顺序进行，默认原微博在整个爬取过程中不会进行删除（可以新增），若有已爬取的微博删除，可能会导致漏爬。另外这样的代价就是不支持只爬取部分时间段内的内容。
* 搬运文件时文件名只保存了url的最后一段，可能有极小概率会出现不同文件重名的情况？如有必要可以考虑取更长的内容作为文件名（如整个url去掉不兼容的符号）。
* 所有url保留原始值，在复现的时候按规则转换成本地文件路径。
* 置顶微博认为它在时间线上仍存在，不作任何特殊处理，复现时不置顶。
* 由于微博评论格式调整（大约2016年7月前后），更早期的评论数据只能用另一种方式搬运，某些情况下无法完全获得（官网也不显示）。因为结合了两种方式，评论的创建时间格式不一样，需要在使用时区分处理。

## 特别感谢
本项目参考了weibo-crawler和weiboSpider，特此感谢。