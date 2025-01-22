from modules.utils import handle_request
from modules.config import config
import re
import json

url = 'https://m.weibo.cn/detail/5125022128276759'
result = handle_request(config.cookie, url, 'text')
# print(result)
def print_dict(my_var, start=0):
    for k, v in my_var.items():
        if isinstance(v, dict):
            print(f'{" "*start}{k}:')
            print_dict(v, start+2)
        else:
            print(f'{" "*start}{k}:{v}')

match = re.search(r'\$render_data\s*=\s*(\[.*?\])\s*\[\d*\]\s*\|\|\s*\{\};', result, re.DOTALL)
if match:
    json_str = match.group(1)

    # 将 JSON 字符串转换为 Python 字典
    render_data = json.loads(json_str)[0]
    print_dict(render_data)

# 清理控制字符
cleaned_json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)