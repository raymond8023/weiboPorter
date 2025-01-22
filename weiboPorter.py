from modules.config import config
from modules.porter import Porter
from modules.user import User
from modules.utils import check_cookie, random_wait



if __name__ == "__main__":
    for user_id in config.user_id_list:
        check_cookie()
        user = User(user_id)
        porter = Porter(user)
        porter.start()
        random_wait()

