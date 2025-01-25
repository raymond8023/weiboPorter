from modules.utils import handle_request, random_wait, sqlite_query
from modules.config import config
from time import sleep

import re
import json

# https://m.weibo.cn/comments/hotflow?id=43658866&mid=43658866&max_id_type=0&max_id=0
cur_count = 0
comment_list = []
total_number = 0

class Comment:
    def __init__(self, data):
        global total_number
        self.created_at	= data['created_at']
        self.id = data['id']
        self.text	 = data['text']
        self.user_id = data['user']['id']
        self.user_name = data['user']['screen_name']
        self.user_avatar = data['user']['profile_image_url']
        self.recomments = data['comments']
        self.max_id = data['max_id']
        self.total_number = data['total_number']
        self.bid = data['bid']
        self.like_count = data['like_count']




def get_comments(id, max_id):
    global cur_count, total_number
    url = f'https://m.weibo.cn/comments/hotflow?max_id_type=0&mid={id}'
    url = f'https://m.weibo.cn/profile/1434712204'
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'
    headers = {'User_Agent': user_agent, 'Cookie': config.cookie}

    try:
        import requests
        response = requests.get(url, headers=headers, timeout=config.request_timeout)
        response.raise_for_status()  # 检查状态码是否为 2xx
        print(response.text)
    except:
        print("error")
        re

# # get_comments('5103422221062369', '0')
# config.user_dir = './weibo/1434712204_枚楚曦/'
# ported_count = sqlite_query(f"SELECT count(1) FROM weibos WHERE user_id = '{config.user_id_list[0]}'")[0] # 搬运微博计数（只计算目标用户的微博）
# print(ported_count)

import os

os.makedirs('/weibo', exist_ok=True)

var
config = {
    env: 'prod',
    version: '2.12.6',
    login: [1][0],
    st: '4dcd8f',
    uid: '1434712204',
    pageConfig: [null][0] | | {},
    preferQuickapp: '0',
    wm: ''
}
var $render_data = [{
    "hotScheme": "https://m.weibo.cn/p/index?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot&luicode=20000061&lfid=3439466943518422",
    "appScheme": "https://m.weibo.cn?luicode=20000061&lfid=3439466943518422",
    "callUinversalLink": false,
    "callWeibo": false,
    "schemeOrigin": false,
    "appLink": "sinaweibo://detail?mblogid=3439466943518422&luicode=20000061&lfid=3439466943518422",
    "xianzhi_scheme": "xianzhi://mblogshow?mid=3439466943518422",
    "third_scheme": "sinaweibo://detail?mblogid=3439466943518422&luicode=20000061&lfid=3439466943518422",
    "status": {
        "visible": {
            "type": 0,
            "list_id": 0
        },
        "created_at": "Fri Apr 27 16:44:42 +0800 2012",
        "id": "3439466943518422",
        "mid": "3439466943518422",
        "can_edit": false,
        "text": "神演技啊~~好吧我凌乱了~~~你~你想怎样！！！ <a  href=\"https://weibo.cn/sinaurl?u=http%3A%2F%2Fv.youku.com%2Fv_show%2Fid_XMzg3MTk3ODQ4.html\" data-hide=\"\"><span class='url-icon'><img style='width: 1rem;height: 1rem' src='https://h5.sinaimg.cn/upload/2015/09/25/3/timeline_card_small_video_default.png'></span><span class=\"surl-text\">【Mike隋出品】老外屌丝中文哥超强12人模仿！！！</span></a>  （分享自 <a href='/n/优酷网'>@优酷网</a>） ",
        "source": "微博视频号",
        "favorited": false,
        "pic_ids": [],
        "is_paid": false,
        "mblog_vip_type": 0,
        "user": {
            "id": 1434712204,
            "screen_name": "枚楚曦",
            "profile_image_url": "https://tva1.sinaimg.cn/crop.0.0.640.640.180/5583f88cjw8f5edyulhpaj20hs0hsmy6.jpg?KID=imgbed,tva&Expires=1737800753&ssig=91Bt6scEsA",
            "profile_url": "https://m.weibo.cn/u/1434712204?luicode=20000061&lfid=3439466943518422",
            "close_blue_v": false,
            "description": "an idealist who has no ideality。",
            "follow_me": false,
            "following": false,
            "follow_count": 336,
            "followers_count": "298",
            "cover_image_phone": "https://tva1.sinaimg.cn/crop.0.0.640.640.640/549d0121tw1egm1kjly3jj20hs0hsq4f.jpg",
            "avatar_hd": "https://ww1.sinaimg.cn/orj480/5583f88cjw8f5edyulhpaj20hs0hsmy6.jpg",
            "badge": {
                "unread_pool": 1,
                "unread_pool_ext": 1,
                "user_name_certificate": 1,
                "hongbao_2020": 2,
                "pc_new": 7,
                "hongbaofei2022_2021": 2
            },
            "statuses_count": 1797,
            "verified": false,
            "verified_type": 220,
            "gender": "m",
            "mbtype": 0,
            "svip": 0,
            "urank": 24,
            "mbrank": 0,
            "followers_count_str": "298",
            "verified_reason": "",
            "like": false,
            "like_me": false,
            "special_follow": false
        },
        "reposts_count": 0,
        "comments_count": 0,
        "reprint_cmt_count": 0,
        "attitudes_count": 0,
        "mixed_count": 0,
        "pending_approval_count": 0,
        "isLongText": false,
        "show_mlevel": 0,
        "darwin_tags": [],
        "ad_marked": false,
        "mblogtype": 0,
        "item_category": "status",
        "rid": "0_0_0_5057879570841889828_0_0_0",
        "number_display_strategy": {
            "apply_scenario_flag": 19,
            "display_text_min_number": 1000000,
            "display_text": "100万+"
        },
        "content_auth": 0,
        "is_show_mixed": false,
        "comment_manage_info": {
            "comment_manage_button": 1,
            "comment_permission_type": 0,
            "approval_comment_type": 0,
            "comment_sort_type": 0
        },
        "pic_num": 0,
        "mlevel": 0,
        "detail_bottom_bar": 0,
        "page_info": {
            "type": "video",
            "object_type": 11,
            "url_ori": "http://t.cn/zOjN3DO",
            "page_pic": {
                "width": "412",
                "url": "https://vthumb.ykimg.com/054104085301C1446A0A4604E5A934AD",
                "height": "231"
            },
            "page_url": "https://weibo.cn/sinaurl?luicode=20000061&lfid=3439466943518422&u=http%3A%2F%2Fv.youku.com%2Fv_show%2Fid_XMzg3MTk3ODQ4.html",
            "object_id": "1007002:85c0fc78651d7ceb3de96a39badd7e9e",
            "page_title": "【Mike隋出品】老外屌丝中文哥超强12人模仿！！！",
            "title": "【Mike隋出品】老外屌丝中文哥超强12人模仿！！！",
            "content1": "【Mike隋出品】老外屌丝中文哥超强12人模仿！！！",
            "content2": "我国英语教材传奇人物李雷请来一帮外国屌丝来宣布一件和她女朋友韩梅梅的重大消息。。。\r\n美国人\r\n法国人\r\n日本人\r\n俄罗斯人\r\n。。。\r\n一群屌丝聚在一起用什么语言聊天呢？？？\r\n更多精彩视频请密切关注Mike隋！\r\n微博：@Mike隋\r\n谢谢观看~",
            "video_orientation": "horizontal",
            "play_count": "44万次播放",
            "media_info": {
                "stream_url": "https://api.youku.com/videos/player/file?data=WcEl1o6uZdzNNVGszT0RRNHwwfDB8MTAwNTB8MAO0O0OO0O0O",
                "stream_url_hd": "https://api.youku.com/videos/player/file?data=WcEl1o6uZdzNNVGszT0RRNHwwfDF8MTAwNTB8MAO0O0OO0O0O",
                "duration": 272.51200000000000045474735088646411895751953125
            },
            "urls": null
        },
        "bid": "ygyImeLiK",
        "reads": 0,
        "status_title": "Mike隋出品",
        "ok": 1
    },
    "call": 1
}][0] | | {};
var
__wb_performance_data = {v: "v8", m: "mainsite", pwa: 1, sw: 0};

