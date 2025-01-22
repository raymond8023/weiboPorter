import json
import sys
import os


class Config:
    # 使用单实例模式
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), os.path.pardir,  "config.json")
        if not hasattr(self, 'initialized'):  # 避免重复初始化
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                for key, value in config_data.items():
                    setattr(self, key, value)
                self.initialized = True
            except Exception as e:
                print(f"init config error: {e}")
                sys.exit(1)  # 终止程序，返回状态码 1

    def __str__(self):
        # 返回所有属性的字符串表示
        return "\n".join(f"{key}: {value}" for key, value in self.__dict__.items())


config = Config()

