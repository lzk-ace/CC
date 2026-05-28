import random
import sys
import ast
import requests
from time import localtime
from datetime import datetime, date
from zhdate import ZhDate


def get_color():
    # 获取随机颜色
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    color_list = get_colors(100)
    return random.choice(color_list)


def get_access_token():
    app_id = config.get("app_id")
    app_secret = config.get("app_secret")
    post_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    
    try:
        response = requests.get(post_url)
        data = response.json()
        return data['access_token']
    except Exception as e:
        print(f"获取 access_token 失败，错误信息: {e}")
        if 'response' in locals():
            print(f"微信接口返回的原始内容: {response.text[:300]}")
        sys.exit(1)


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]
    
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        try:
            birthday_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print("请检查农历生日的日期是否正确")
            sys.exit(1)
        birthday_month = birthday_date.month
        birthday_day = birthday_date.day
        year_date = date(year, birthday_month, birthday_day)
    else:
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        year_date = date(year, birthday_month, birthday_day)
        
    if today > year_date:
        if birthday_year[0] == "r":
            r_last_birthday = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last_birthday.month, r_last_birthday.day)
        else:
            birth_date = date((year + 1), birthday_month, birthday_day)
        birth_day = (birth_date - today).days
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = (birth_date - today).days
        
    return birth_day


def get_ciba():
    url = "https://open.iciba.com/dsapi/"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        note_en = data.get("content", "")
        note_ch = data.get("note", "")
        return note_ch, note_en
    except Exception as e:
        print(f"获取金山词霸每日一句失败：{e}")
        return "今日由于网络原因，无法获取金句", "Failed to get quote today due to network issues."


def send_message(to_user, access_token, note_ch, note_en):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday
    today = datetime.date(datetime(year=year, month=month, day=day))
    week = week_list[today.isoweekday() % 7]
    
    love_year = int(config["love_date"].split("-")[0])
    love_month = int(config["love_date"].split("-")[1])
    love_day = int(config["love_date"].split("-")[2])
    love_date = date(love_year, love_month, love_day)
    
    love_days = str((today - love_date).days)
    
    birthdays = {}
    for k, v in config.items():
        if k[0:5] == "birth":
            birthdays[k] = v
            
    # 构建推送数据，已移除所有天气相关的字段
    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {"value": f"{today} {week}", "color": get_color()},
            "love_day": {"value": love_days, "color": get_color()},
            "note_en": {"value": note_en, "color": get_color()},
            "note_ch": {"value": note_ch, "color": get_color()}
        }
    }
    
    # 动态添加生日字段
    for key, value in birthdays.items():
        birth_day = get_birthday(value["birthday"], year, today)
        if birth_day == 0:
            birthday_data = f"今天{value['name']}生日哦，祝{value['name']}生日快乐！"
        else:
            birthday_data = f"距离{value['name']}的生日还有{birth_day}天"
        data["data"][key] = {"value": birthday_data, "color": get_color()}
        
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        res_data = response.json()
        errcode = res_data.get("errcode")
        
        if errcode == 40037:
            print(f"[{to_user}] 推送消息失败，请检查模板id是否正确")
        elif errcode == 40036:
            print(f"[{to_user}] 推送消息失败，请检查模板id是否为空")
        elif errcode == 40003:
            print(f"[{to_user}] 推送消息失败，请检查微信号是否正确")
        elif errcode == 0:
            print(f"[{to_user}] 推送消息成功 🎉")
        else:
            print(f"[{to_user}] 推送消息发生未知错误: {res_data}")
            
    except Exception as e:
        print(f"请求微信推送接口异常: {e}")
        if 'response' in locals():
            print(f"微信接口返回原始内容: {response.text[:300]}")


if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = ast.literal_eval(f.read())
    except FileNotFoundError:
        print("推送消息失败，请检查 config.txt 文件是否与程序位于同一路径")
        sys.exit(1)
    except Exception as e:
        print(f"推送消息失败，请检查配置文件格式是否正确: {e}")
        sys.exit(1)

    # 1. 获取微信 accessToken
    accessToken = get_access_token()
    users = config.get("user", [])
    
    # 2. 获取每日金句
    note_ch = config.get("note_ch", "")
    note_en = config.get("note_en", "")
    
    if note_ch == "" and note_en == "":
        note_ch, note_en = get_ciba()
        
    # 3. 开始向每个用户推送消息（去除了天气参数）
    for user in users:
        send_message(user, accessToken, note_ch, note_en)
