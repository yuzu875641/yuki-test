import json
import requests
import urllib.parse
import time
import datetime
import random
import os
from cache import cache

# ==============================================================================
# 設定とAPIリスト
# ==============================================================================
max_api_wait_time = 4
max_time = 20

# APIリストをグローバル定数として定義し、動的な変更を避ける
apis = [r'https://inv-server-w268.vercel.app/', r'https://inv-server-x88u.vercel.app/', r'https://inv-server-odic.vercel.app/', r'https://inv-server-8ode.vercel.app/', r'https://inv-server-sfjw.vercel.app/', r'https://inv-server-u8ps.vercel.app/', r'https://inv-server-qudk.vercel.app/', r'https://inv-server-2j8x.vercel.app/', r'https://inv-server-woad.vercel.app/', r'https://lekker.gay/', r'https://nyc1.iv.ggtyler.dev/', r'https://invidious.nikkosphere.com/', r'https://invidious.rhyshl.live/', r'https://invid-api.poketube.fun/', r'https://inv.tux.pizza/',r'https://pol1.iv.ggtyler.dev/', r'https://yewtu.be/', r'https://youtube.alt.tyil.nl/']

# BBSのURLを直接設定（セキュリティと安定性のため、外部依存を削除）
url = os.environ.get('BBS_URL', r'https://your-default-bbs-url.com/')
version = "1.0"

class APItimeoutError(Exception):
    pass

def is_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

# ==============================================================================
# APIリクエスト関数の修正
# グローバルリストの変更をなくし、より安全な処理に変更しました。
# ==============================================================================
def apirequest(request_url):
    shuffled_apis = random.sample(apis, len(apis))
    starttime = time.time()
    for api in shuffled_apis:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + request_url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                print(api + request_url)
                return res.text
            else:
                print(f"エラー: {api}")
        except:
            print(f"タイムアウト: {api}")
    raise APItimeoutError("APIがタイムアウトしました")

def apichannelrequest(request_url):
    shuffled_apis = random.sample(apis, len(apis))
    starttime = time.time()
    for api in shuffled_apis:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + request_url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー: {api}")
        except:
            print(f"タイムアウト: {api}")
    raise APItimeoutError("APIがチャンネルを返しませんでした")

def apicommentsrequest(request_url):
    shuffled_apis = random.sample(apis, len(apis))
    starttime = time.time()
    for api in shuffled_apis:
        if time.time() - starttime >= max_time - 1:
            break
        try:
            res = requests.get(api + request_url, timeout=max_api_wait_time)
            if res.status_code == 200 and is_json(res.text):
                return res.text
            else:
                print(f"エラー: {api}")
        except:
            print(f"タイムアウト: {api}")
    raise APItimeoutError("APIがタイムアウトしました")


# ==============================================================================
# データ取得と検索ロジック
# get_search関数のフィルタリングロジックを簡素化しました。
# ==============================================================================
def get_info(request):
    global version
    return json.dumps([version, os.environ.get('RENDER_EXTERNAL_URL'), str(request.scope["headers"]), str(request.scope['router'])[39:-2]])

def get_data(videoid):
    t = json.loads(apirequest(r"api/v1/videos/" + urllib.parse.quote(videoid)))
    
    quality_list = []
    if "formatStreams" in t:
        for stream in t["formatStreams"]:
            if stream.get("qualityLabel"):
                quality_list.append({"quality": stream.get("qualityLabel"), "url": stream.get("url")})
    
    if "adaptiveFormats" in t:
        for stream in t["adaptiveFormats"]:
            if stream.get("mimeType", "").startswith("video") and stream.get("qualityLabel"):
                quality_list.append({"quality": stream.get("qualityLabel"), "url": stream.get("url")})

    unique_qualities = {item['quality']: item for item in quality_list}.values()

    def sort_key(item):
        quality = item['quality'].replace('p', '').replace('+', '')
        return int(quality) if quality.isdigit() else 0

    sorted_quality_list = sorted(list(unique_qualities), key=sort_key, reverse=True)

    videourls = [sorted_quality_list[0]['url']] if sorted_quality_list else []
    
    return [
        [{"id": i["videoId"], "title": i["title"], "authorId": i["authorId"], "author": i["author"]} for i in t["recommendedVideos"]],
        videourls,
        t["descriptionHtml"].replace("\n", "<br>"),
        t["title"],
        t["authorId"],
        t["author"],
        t["authorThumbnails"][-1]["url"],
        sorted_quality_list
    ]

def get_search(q, page, filter_type):
    api_filter = None
    if filter_type == 'playlist':
        api_filter = 'playlist'
    elif filter_type == 'channel':
        api_filter = 'channel'
    
    url_suffix = f"api/v1/search?q={urllib.parse.quote(q)}&page={page}&hl=jp"
    if api_filter:
        url_suffix += f"&type={api_filter}"

    try:
        response = apirequest(url_suffix)
        items = json.loads(response)

        results = []
        for item in items:
            try:
                processed_item = load_search(item)
                
                if processed_item['type'] == 'video':
                    is_live = item.get('isLive', False)
                    is_short = item.get('isShort', False)
                    if (filter_type == 'live' and is_live) or \
                       (filter_type == 'short' and is_short) or \
                       (filter_type not in ['live', 'short']):
                        results.append(processed_item)
                else:
                    results.append(processed_item)
            except ValueError as ve:
                print(f"Error processing item: {str(ve)}")
                continue
        
        return results

    except json.JSONDecodeError:
        raise ValueError("Failed to decode JSON response.")
    except Exception as e:
        raise ValueError(f"API request error: {str(e)}")

def load_search(i):
    if i["type"] == "video":
        return {
            "title": i["title"],
            "id": i["videoId"],
            "authorId": i["authorId"],
            "author": i["author"],
            "length": str(datetime.timedelta(seconds=i["lengthSeconds"])),
            "published": i["publishedText"],
            "type": "video"
        }
    elif i["type"] == "playlist":
        if not i["videos"]:
            raise ValueError("Playlist is empty.")
        return {
            "title": i["title"],
            "id": i["playlistId"],
            "thumbnail": i["videos"][0]["videoId"],
            "count": i["videoCount"],
            "type": "playlist"
        }
    else:
        thumbnail_url = (
            i["authorThumbnails"][-1]["url"]
            if i["authorThumbnails"][-1]["url"].startswith("https")
            else "https://" + i["authorThumbnails"][-1]["url"]
        )
        return {
            "author": i["author"],
            "id": i["authorId"],
            "thumbnail": thumbnail_url,
            "type": "channel"
        }
        
def get_channel(channelid):
    t = json.loads(apichannelrequest(r"api/v1/channels/" + urllib.parse.quote(channelid)))
    if t["latestVideos"] == []:
        print("APIがチャンネルを返しませんでした")
        raise APItimeoutError("APIがチャンネルを返しませんでした")
    return [[{"title": i["title"], "id": i["videoId"], "authorId": t["authorId"], "author": t["author"], "published": i["publishedText"], "type": "video"} for i in t["latestVideos"]], {"channelname": t["author"], "channelicon": t["authorThumbnails"][-1]["url"], "channelprofile": t["descriptionHtml"]}]

def get_playlist(listid, page):
    t = json.loads(apirequest(r"/api/v1/playlists/" + urllib.parse.quote(listid) + "?page=" + urllib.parse.quote(str(page))))["videos"]
    return [{"title": i["title"], "id": i["videoId"], "authorId": i["authorId"], "author": i["author"], "type": "video"} for i in t]

def get_comments(videoid):
    t = json.loads(apicommentsrequest(r"api/v1/comments/" + urllib.parse.quote(videoid) + "?hl=jp"))["comments"]
    return [{"author": i["author"], "authoricon": i["authorThumbnails"][-1]["url"], "authorid": i["authorId"], "body": i["contentHtml"].replace("\n", "<br>")} for i in t]

def get_replies(videoid, key):
    t = json.loads(apicommentsrequest(fr"api/v1/comments/{videoid}?hmac_key={key}&hl=jp&format=html"))["contentHtml"]

def get_level(word):
    for i1 in range(1, 13):
        with open(f'Level{i1}.txt', 'r', encoding='UTF-8', newline='\n') as f:
            if word in [i2.rstrip("\r\n") for i2 in f.readlines()]:
                return i1
    return 0

def check_cokie(cookie):
    print(cookie)
    if cookie == "True":
        return True
    return False

from fastapi import FastAPI, Depends, HTTPException, Response, Cookie, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse as redirect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Union

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/css", StaticFiles(directory="./css"), name="static")
app.mount("/word", StaticFiles(directory="./blog", html=True), name="static")
app.add_middleware(GZipMiddleware, minimum_size=1000)

from fastapi.templating import Jinja2Templates
template = Jinja2Templates(directory='templates').TemplateResponse

@app.get("/", response_class=HTMLResponse)
def home(response: Response, request: Request, yuki: Union[str, None] = Cookie(None)):
    if check_cokie(yuki):
        response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
        return template("home.html", {"request": request})
    print(check_cokie(yuki))
    return redirect("/word")

@app.get('/watch', response_class=HTMLResponse)
def video(v: str, response: Response, request: Request, yuki: Union[str, None] = Cookie(None), proxy: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7 * 24 * 60 * 60)
    videoid = v
    data = get_data(videoid)
    if (data == "error"):
        return template("error.html", {"request": request, "status_code": "502 - Bad Gateway", "message": "ビデオ取得時のAPIエラー、再読み込みしてください。", "home": False}, status_code=502)
    
    recommended_videos = data[0]
    videourls = data[1]
    description = data[2]
    videotitle = data[3]
    authorid = data[4]
    author = data[5]
    authoricon = data[6]
    quality_list = data[7]
    
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
    
    return template('video.html', {
        "request": request,
        "videoid": videoid,
        "videourls": videourls,
        "res": recommended_videos,
        "description": description,
        "videotitle": videotitle,
        "authorid": authorid,
        "authoricon": authoricon,
        "author": author,
        "proxy": proxy,
        "quality_list": quality_list
    })

# main.py の既存のコードに以下のエンドポイントを追加します

@app.get('/edu', response_class=HTMLResponse)
def edu_page(v: str, response: Response, request: Request, yuki: Union[str, None] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7 * 24 * 60 * 60)
    videoid = v
    try:
        data = get_data(videoid)
        comments = get_comments(videoid)
    except APItimeoutError as e:
        return template("error.html", {"request": request, "status_code": "502 - Bad Gateway", "message": "APIエラー: 再読み込みしてください。", "home": False}, status_code=502)

    recommended_videos, _, description, videotitle, authorid, author, authoricon, quality_list = data
    
    video_src = f"https://www.youtubeeducation.com/embed/{videoid}?autoplay=0&amp;mute=0&amp;controls=1&amp;start=0&amp;origin=https%3A%2F%2Fcreate.kahoot.it&amp;playsinline=1&amp;showinfo=0&amp;rel=0&amp;iv_load_policy=3&amp;modestbranding=1&amp;fs=1&amp;embed_config=%7B%22enc%22%3A%22AXH1ezlOjk7uPL54v707Eu6ElkRzL15Jh-Gf0uru6jRzXmddU0uVPO6Q-pb0QyEd8YIer6BYFO-ZqYXPeXnbyBqX3hsHrmDSkGrmgmv-MxIiV6bO-fuGKTBfuL7BEniN-oDUAvQNcxFfNvJfxlC7NWHeo4ffwiZIJg%3D%3D%22%2C%22hideTitle%22%3Atrue%7D&amp;enablejsapi=1&amp;widgetid=1&amp;forigin=https%3A%2F%2Fcreate.kahoot.it%2Fstory%2Fcreate%2F4570ae24-1cc0-44aa-a790-eb46bcc71292%3Fcourseid%3Dempty&amp;aoriginsup=1&amp;gporigin=https%3A%2F%2Fcreate.kahoot.it%2Fauth%2Flogin%3Fnext%3D%252Fstory%252Fcreate%252F4570ae24-1cc0-44aa-a790-eb46bcc71292%253Fcourseid%253Dempty&amp;vf=6"
    
    return template('edu.html', {
        "request": request,
        "videosrc": video_src,
        "videoInfo": {
            "title": videotitle,
            "channelId": authorid,
            "channelName": author,
            "channelIcon": authoricon,
            "description": description
        },
        "recommendedVideos": recommended_videos,
        "comments": comments,
        "quality_list": quality_list
    })

@app.get('/nocookie', response_class=HTMLResponse)
def nocookie_page(v: str, response: Response, request: Request, yuki: Union[str, None] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    response.set_cookie(key="yuki", value="True", max_age=7 * 24 * 60 * 60)
    videoid = v
    try:
        data = get_data(videoid)
        comments = get_comments(videoid)
    except APItimeoutError as e:
        return template("error.html", {"request": request, "status_code": "502 - Bad Gateway", "message": "APIエラー: 再読み込みしてください。", "home": False}, status_code=502)
        
    recommended_videos, _, description, videotitle, authorid, author, authoricon, quality_list = data

    video_src = f"https://www.youtube-nocookie.com/embed/{videoid}"

    return template('nocookie.html', {
        "request": request,
        "videosrc": video_src,
        "videoInfo": {
            "title": videotitle,
            "channelId": authorid,
            "channelName": author,
            "channelIcon": authoricon,
            "description": description
        },
        "recommendedVideos": recommended_videos,
        "comments": comments,
        "quality_list": quality_list
    })

@app.get("/search", response_class=HTMLResponse)
def search(q: str, response: Response, request: Request, page: Union[int, None] = 1, filter: Union[str, None] = 'all', yuki: Union[str, None] = Cookie(None), proxy: Union[str, None] = Cookie(None)):
    if not check_cokie(yuki):
        return redirect("/")
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)

    try:
        results = get_search(q, page, filter)

        if isinstance(results, dict) and "error" in results:
            error_detail = results.get("error", "Unknown error occurred.")
            raise HTTPException(status_code=500, detail=f"Search API error: {error_detail}")

        next_page_url = f"/search?q={q}&page={page + 1}&filter={filter}"

        return template("search.html", {
            "request": request,
            "results": results,
            "word": q,
            "next": next_page_url,
            "proxy": proxy,
            "current_filter": filter
        })
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/hashtag/{tag}")
def search_by_tag(tag: str, response: Response, request: Request, page: Union[int, None] = 1, yuki: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    return redirect(f"/search?q={tag}")

@app.get("/channel/{channelid}", response_class=HTMLResponse)
def channel(channelid: str, response: Response, request: Request, yuki: Union[str, None] = Cookie(None), proxy: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
    t = get_channel(channelid)
    return template("channel.html", {"request": request, "results": t[0], "channelname": t[1]["channelname"], "channelicon": t[1]["channelicon"], "channelprofile": t[1]["channelprofile"], "proxy": proxy})

@app.get("/answer", response_class=HTMLResponse)
def set_cokie(q: str):
    t = get_level(q)
    if t > 5:
        return f"level{t}\n推測を推奨する"
    elif t == 0:
        return "level12以上\nほぼ推測必須"
    return f"level{t}\n覚えておきたいレベル"

@app.get("/playlist", response_class=HTMLResponse)
def playlist(list: str, response: Response, request: Request, page: Union[int, None] = 1, yuki: Union[str, None] = Cookie(None), proxy: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
    return template("search.html", {"request": request, "results": get_playlist(list, str(page)), "word": "", "next": f"/playlist?list={list}", "proxy": proxy})

@app.get("/info", response_class=HTMLResponse)
def viewlist(response: Response, request: Request, yuki: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    response.set_cookie("yuki", "True", max_age=60 * 60 * 24 * 7)
    return template("info.html", {"request": request, "Youtube_API": apis[0], "Channel_API": apis[0], "Comments_API": apis[0]})

@app.get("/suggest")
def suggest(keyword: str):
    return [i[0] for i in json.loads(requests.get(r"http://www.google.com/complete/search?client=youtube&hl=ja&ds=yt&q=" + urllib.parse.quote(keyword)).text[19:-1])[1]]

@app.get("/comments")
def comments(request: Request, v: str):
    return template("comments.html", {"request": request, "comments": get_comments(v)})

@app.get("/thumbnail")
def thumbnail(v: str):
    return Response(content=requests.get(fr"https://img.youtube.com/vi/{v}/0.jpg").content, media_type=r"image/jpeg")

@app.get("/bbs", response_class=HTMLResponse)
def view_bbs(request: Request, name: Union[str, None] = "", seed: Union[str, None] = "", channel: Union[str, None] = "main", verify: Union[str, None] = "false", yuki: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    res = HTMLResponse(requests.get(fr"{url}bbs?name={urllib.parse.quote(name)}&seed={urllib.parse.quote(seed)}&channel={urllib.parse.quote(channel)}&verify={urllib.parse.quote(verify)}", cookies={"yuki": "True"}).text)
    return res

@cache(seconds=5)
def bbsapi_cached(verify, channel):
    return requests.get(fr"{url}bbs/api?t={urllib.parse.quote(str(int(time.time() * 1000)))}&verify={urllib.parse.quote(verify)}&channel={urllib.parse.quote(channel)}", cookies={"yuki": "True"}).text

@app.get("/bbs/api", response_class=HTMLResponse)
def view_bbs_api(request: Request, t: str, channel: Union[str, None] = "main", verify: Union[str, None] = "false"):
    print(fr"{url}bbs/api?t={urllib.parse.quote(t)}&verify={urllib.parse.quote(verify)}&channel={urllib.parse.quote(channel)}")
    return bbsapi_cached(verify, channel)

@app.get("/bbs/result")
def write_bbs(request: Request, name: str = "", message: str = "", seed: Union[str, None] = "", channel: Union[str, None] = "main", verify: Union[str, None] = "false", yuki: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    t = requests.get(fr"{url}bbs/result?name={urllib.parse.quote(name)}&message={urllib.parse.quote(message)}&seed={urllib.parse.quote(seed)}&channel={urllib.parse.quote(channel)}&verify={urllib.parse.quote(verify)}&info={urllib.parse.quote(get_info(request))}", cookies={"yuki": "True"}, allow_redirects=False)
    if t.status_code != 307:
        return HTMLResponse(t.text)
    return redirect(f"/bbs?name={urllib.parse.quote(name)}&seed={urllib.parse.quote(seed)}&channel={urllib.parse.quote(channel)}&verify={urllib.parse.quote(verify)}")

@cache(seconds=30)
def how_cached():
    return requests.get(fr"{url}bbs/how").text

@app.get("/bbs/how", response_class=PlainTextResponse)
def view_commands(request: Request, yuki: Union[str, None] = Cookie(None)):
    if not (check_cokie(yuki)):
        return redirect("/")
    return how_cached()

@app.get("/load_instance")
def home():
    global url
    try:
        url_from_file = requests.get(r'https://raw.githubusercontent.com/mochidukiyukimi/yuki-youtube-instance/main/instance.txt').text.rstrip()
        url = url_from_file
        return {"status": "success", "message": "BBS URL updated from GitHub."}
    except Exception as e:
        print(f"Failed to load BBS URL: {e}")
        return {"status": "error", "message": "Failed to load BBS URL from GitHub. Using default."}

@app.exception_handler(404)
def notfounderror(request: Request, exc):
    return template("error.html", {"request": request, "status_code": "404 - Not Found", "message": "未実装か、存在しないページです。", "home": True}, status_code=404)

@app.exception_handler(500)
def page_error(request: Request, exc):
    return template("APIwait.html", {"request": request}, status_code=500)

@app.exception_handler(APItimeoutError)
def APIwait(request: Request, exception: APItimeoutError):
    return template("APIwait.html", {"request": request}, status_code=500)
