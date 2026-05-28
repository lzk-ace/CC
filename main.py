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
        print(f"获取access_token失败，错误信息: {e}")
        if 'response' in locals():
            print(f"微信接口返回的原始内容: {response.text[:300]}")
        sys.exit(1)


def get_weather(region):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    key = config.get("weather_key")
    region_url = f"https://geoapi.qweather.com/v2/city/lookup?location={region}&key={key}"
    
    try:
        res_region = requests.get(region_url, headers=headers)
        region_data = res_region.json()
        
        if str(region_data.get("code")) == "404":
            print("推送消息失败，请检查地区名是否有误！")
            sys.exit(1)
        elif str(region_data.get("code")) == "401":
            print("推送消息失败，请检查和风天气key是否正确！")
            sys.exit(1)
            
        location_id = region_data["location"][0]["id"]
        
        weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={key}"
        res_weather = requests.get(weather_url, headers=headers)
        weather_data = res_weather.json()
        
        weather = weather_data["now"]["text"]
        temp = weather_data["now"]["temp"] + u"\N{DEGREE SIGN}" + "C"
        wind_dir = weather_data["now"]["windDir"]
        return weather, temp, wind_dir
        
    except Exception as e:
        print(f"获取天气信息失败: {e}")
        if 'res_region' in locals():
            print(f"地区接口返回内容: {res_region.text[:300]}")
        if 'res_weather' in locals():
            print(f"天气接口返回内容: {res_weather.text[:300]}")
        sys.exit(1)


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]
    
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        try:
            birthday_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print("请检查生日的日子是否在今年存在")
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
        # 优化：直接使用 .days 属性获取天数差
        birth_day = (birth_date - today).days
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = (birth_date - today).days
        
    return birth_day


def get_ciba():
    # 优化：改用 https 协议，防止被网络环境拦截
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


def send_message(to_user, access_token, region_name, weather, temp, wind_dir, note_ch, note_en):
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
    
    # 优化：直接使用 .days 获取相爱天数
    love_days = str((today - love_date).days)
    
    birthdays = {}
    for k, v in config.items():
        if k[0:5] == "birth":
            birthdays[k] = v
            
    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {"value": f"{today} {week}", "color": get_color()},
            "region": {"value": region_name, "color": get_color()},
            "weather": {"value": weather, "color": get_color()},
            "temp": {"value": temp, "color": get_color()},
            "wind_dir": {"value": wind_dir, "color": get_color()},
            "love_day": {"value": love_days, "color": get_color()},
            "note_en": {"value": note_en, "color": get_color()},
            "note_ch": {"value": note_ch, "color": get_color()}
        }
    }
    
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
            print(f"[{to_user}] 推送消息成功")
        else:
            print(f"[{to_user}] 推送消息发生未知错误: {res_data}")
            
    except Exception as e:
        print(f"请求微信推送接口异常: {e}")
        if 'response' in locals():
            print(f"微信接口返回原始内容: {response.text[:300]}")


if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            # 优化：使用 ast.literal_eval 代替 eval，更安全且不要求强行修改原有的配置格式
            config = ast.literal_eval(f.read())
    except FileNotFoundError:
        print("推送消息失败，请检查 config.txt 文件是否与程序位于同一路径")
        sys.exit(1)
    except Exception as e:
        print(f"推送消息失败，请检查配置文件格式是否正确: {e}")
        sys.exit(1)

    accessToken = get_access_token()
    users = config.get("user", [])
    region = config.get("region")
    
    weather, temp, wind_dir = get_weather(region)
    note_ch = config.get("note_ch", "")
    note_en = config.get("note_en", "")
    
    if note_ch == "" and note_en == "":
        note_ch, note_en = get_ciba()
        
    for user in users:
        send_message(user, accessToken, region, weather, temp, wind_dir, note_ch, note_en)
