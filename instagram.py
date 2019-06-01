import requests
import json
import os
import getopt
import time
from pyquery import PyQuery as pq

BaseUrl = "https://www.instagram.com/graphql/query/"


class Spider(object):

    def __init__(self,
                 author="",
                 sleep=1,
                 proxy=None):
        self.QueryHash = 'f2405b236d85e8296cf30347c9f08c2a'
        self.author = author
        self.EndCursor = False
        self.search_url = BaseUrl + author
        self.proxy = proxy
        self.req = requests.session()
        self.id = 0
        self.sleep = sleep
        self.TwoQueryHash = '477b65a610463740ccdb83135b2014db'

        self.init()
        if not self._restore():
            self.first()

    def init(self):
        # 给一些参数赋予默认值
        if self.proxy:
            self.proxy = {"http:": "http://{0}".format(self.proxy),
                          "https": "https://{0}".format(self.proxy)}
        self.req.headers.setdefault("user-agent",
                                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                    'Chrome/74.0.3729.131 Safari/537.36')

    def first(self):
        """Id、游标、默认12条数据,均可以在请求的html文本中找到"""
        try:
            res = self.req.get('https://www.instagram.com/' + self.author, proxies=self.proxy, timeout=10)
            if res.status_code != 200:
                print(res.text)
                exit(1)
            doc = pq(res.text)
            json_raw = doc("body script").html().lstrip("window._sharedData =").rstrip(";").strip()
            json_data = json.loads(json_raw, strict=False)
            # print(json.loads(json_raw, strict=False))
            user_data = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
            self.id = user_data['id']

            if user_data['edge_owner_to_timeline_media']['page_info']['has_next_page']:
                self.EndCursor = user_data['edge_owner_to_timeline_media']['page_info']['end_cursor']
            for v in user_data['edge_owner_to_timeline_media']['edges']:
                data = {"type": "image", "urls": []}
                data.setdefault("shortcode", v['node']['shortcode'])
                if v['node']['__typename'] == 'GraphImage':
                    data["type"] = "video" if v['node']['is_video'] else "image"
                    data["urls"].append(v['node']['display_url'])
                    print(v['node']['display_url'])
                elif v['node']['__typename'] == 'GraphSidecar':
                    data["type"] = "video" if v['node']['is_video'] else "image"
                    if 'edge_sidecar_to_children' in v['node']:
                        for children in v['node']['edge_sidecar_to_children']['edges']:
                            data["urls"].append(children['node']['display_url'])
                            print(children['node']['display_url'])
                    else:
                        r = self.req.get(BaseUrl,
                                         params=self._gen_params_2(v['node']['shortcode']),
                                         proxies=self.proxy,
                                         timeout=10)
                        self._next_short(r.json(), v['node']['shortcode'])

                elif v['node']['__typename'] == 'GraphVideo':
                    if v['node']['is_video'] and "video_url" in v['node']:
                        data["urls"].append(v['node']['video_url'])
                        print(v['node']['display_url'])
                else:
                    print(v['node'])
                self._save(self.author, data)
            print("首页默认数据保存完毕")
            if self.EndCursor:
                print("存在下一页数据,继续爬取中...")

        except Exception as e:
            print(e)
            if self.EndCursor:
                self._save_position()
            exit(1)

    def next(self, dic={}) -> bool:
        """ 解析下一次的数据,保存到文件中
            :param dic:
            :return:
            """
        if dic["status"] == "ok":
            self.EndCursor = dic["data"]["user"]['edge_owner_to_timeline_media']['page_info']['end_cursor']
            for v in dic["data"]["user"]['edge_owner_to_timeline_media']['edges']:
                # data = []
                data = {"type": "image", "urls": []}
                data.setdefault("shortcode", v['node']['shortcode'])
                if v['node']['__typename'] == 'GraphImage':
                    data["type"] = "video" if v['node']['is_video'] else "image"
                    data["urls"].append(v['node']['display_url'])
                    print(v['node']['display_url'])
                elif v['node']['__typename'] == 'GraphSidecar':
                    data["type"] = "image"
                    if 'edge_sidecar_to_children' in v['node']:
                        for children in v['node']['edge_sidecar_to_children']['edges']:
                            data["urls"].append(children['node']['display_url'])
                            print(children['node']['display_url'])
                elif v['node']['__typename'] == 'GraphVideo':
                    data["type"] = "video" if v['node']['is_video'] else "image"
                    if v['node']['is_video']:
                        data["urls"].append(v['node']['display_url'])
                        print(v['node']['display_url'])
                    else:
                        print("1", v['node'])
                else:
                    print(v['node'])

                if not data:
                    print(v['node'])
                    exit(100)
                self._save(self.author, data)
            return True
        elif dic['status'] == "fail" and self.EndCursor:
            print("爬取速度过快,服务器禁止爬取了")

        self._save_position()
        return False

    def _next_short(self, dic={}, shortcode="") -> bool:
        if dic['status'] == "ok":
            data = {"type": "image", "urls": []}
            data.setdefault("shortcode", shortcode)
            if 'edge_sidecar_to_children' in dic['data']['shortcode_media']:
                for children in dic['data']['shortcode_media']['edge_sidecar_to_children']['edges']:
                    data["type"] = "video" if children['node']['is_video'] else "image"
                    data["urls"].append(children['node']['display_url'])
                    print(children['node']['display_url'])
            self._save(self.author, data)

    @staticmethod
    def _save(filename, data={}):
        if not data['urls']:
            return
        with open("{0}/{1}.{2}".format("./data", filename, "json"), "a+", encoding="utf-8") as f:
            json.dump(data, f)
            f.write("\n")

    def gen_params(self):
        params = {
            "query_hash": self.QueryHash,
            "variables": """{"id": "%s", "first": 12, "after": "%s"}""" % (self.id, self.EndCursor)
        }
        return params

    def _gen_params_2(self, short_code):
        params = {
            "query_hash": self.TwoQueryHash,
            "variables": """{"shortcode":"%s","child_comment_count":3,"fetch_comment_count":40,
            "parent_comment_count":24,"has_threaded_comments":true}""" % short_code
        }
        return params

    def start(self):

        if self.EndCursor:
            while True:
                try:
                    res = self.req.get(BaseUrl, params=self.gen_params(), proxies=self.proxy, timeout=10)
                    if self.next(res.json()):
                        time.sleep(self.sleep)
                        continue
                    else:
                        print(res.url)
                        break
                except Exception as e:
                    print(e)
                    self._save_position()
                    exit(1)

    def _restore(self) -> bool:
        # 从指定游标恢复爬取
        try:
            with open("{0}/{1}.{2}".format("./data", self.author, "log"), "r", encoding="utf-8") as f:
                self.QueryHash, self.id, self.EndCursor = f.read().split(" ")
                if self.EndCursor == 'None':
                    print("该账号已爬取完毕,请检查")
                    exit(0)
                return True
        except FileNotFoundError as e:
            print(e)
            return False
        except Exception as e:
            print(e)
            exit(1)

    def _save_position(self):
        """
        爬取过程中,如果出现错误,保存当前的查询参数,用于下次恢复
        """
        with open("{0}/{1}.{2}".format("./data", self.author, "log"), "w+", encoding="utf-8") as f:
            f.write("{0} {1} {2}".format(self.QueryHash, self.id, self.EndCursor))


def init():
    os.makedirs("./data", exist_ok=True)


def load_conf() -> list:
    try:
        data = []
        with open("author.list") as f:
            for k, line in enumerate(f.readlines()):
                if k == 0:
                    continue
                name, proxy = line.rstrip("\n").split("|")
                if not proxy:
                    proxy = None
                data.append({'name': name, 'proxy': proxy})
        return data
    except Exception as e:
        print(e)
        print("配置写法错误\n正确的写法如: nba|127.0.0.1:1081 或 nba|")
        exit(1)


if __name__ == '__main__':
    try:
        import sys
        opts, args = getopt.getopt(sys.argv[1:], 'x:', ['name=', 'proxy=', 'sleep='])
        if len(opts) == 0:
            raise getopt.GetoptError("请传入参数值")
    except getopt.GetoptError as err:
        print(err)
        print("Usage: python %s --name test --proxy 127.0.0.1:1080" % os.path.basename(__file__))
        sys.exit(2)

    init()

    Author = []
    Proxy = None
    Sleep = 1
    for o, a in opts:
        if o == '--name':
            Author.append(a)
        if o == "--proxy":
            Proxy = a
        if o == "--sleep":
            Sleep = int(a)

    for au in Author:
        spider = Spider(author=au, sleep=Sleep, proxy=Proxy)
        spider.start()
