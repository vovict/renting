import sys
import traceback
import random
import requests
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup


KEYWORDS = [
    # '竹园', '菊园', '柳浪家园', '绿苑', '紫成嘉园', '菊花盛苑',
    # '六郎庄新村', '远东公寓', '百草园', '兰园', '梅园', '润千秋佳苑',
    # '百旺家', '标石公寓', '马连洼', '软件园'
    '金域', '华府', '博雅德园', '领秀', '融泽嘉园',
    '回龙观', '龙域', '西二旗', '龙泽'
]

STOPWORDS = {'求租', '短租', '丝竹园', '一居', '1居', '开间'}

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ('     
    'KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
    # 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (
    # KHTML, like Gecko) Chrome/48.0.2564.48 Safari/537.36',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) '                   
    'AppleWebKit/533.21.1 (KHTML, like Gecko) Version/5.0.5 '            
    'Safari/533.21.1',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) ' 
    'like Gecko',
    'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, '          
    'like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.11082',
    'Opera/9.80 (Windows NT 6.2; WOW64) Presto/2.12.388 Version/12.17',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:43.0) Gecko/20100101 '       
    'Firefox/43.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11) AppleWebKit/601.1.56 '
    '(KHTML, like Gecko) Version/9.0 Safari/601.1.56',
    'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; WOW64; '        
    'Trident/6.0)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) '             
    'Gecko/20100101 Firefox/24.0',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'
]


class BaseParser(object):

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/64.0.3282.186 Safari/537.36',
        }

    def get_res(self, url, params=None):
        self.headers['User-Agent'] = random.choice(user_agents)
        res = requests.get(url, headers=self.headers, params=params)
        if res.status_code != requests.codes.ok:
            return None
        else:
            return res.content


class SMTHParser(BaseParser):

    def __init__(self):
        super(SMTHParser, self).__init__()
        self.base_url = 'https://www.newsmth.net/bbsbfind.php'
        self.params = {
            'q': 1,
            'board': 'HouseRent',
            'title': '菊园',
            'title2': '',
            'title3': '',
            'userid': '',
            'dt': 60
        }
    
    def parse(self):
        title_item_map = {}
        for keyword in KEYWORDS:
            self.params['title'] = keyword.encode('gbk')
            html = self.get_res(self.base_url, self.params)
            if html is not None:
                html = html.decode('gbk', errors='ignore')
                items = self.parse_html(html)
                for item in items:
                    title = item['title']
                    reject = False
                    for w in STOPWORDS:
                        if w in title:
                            reject = True
                            break
                    if title not in title_item_map and not reject:
                        title_item_map[title] = item
        return sorted(list(title_item_map.values()),
                      key=lambda x: x['date_time'], reverse=True)


    def parse_html(self, html):
        items = []
        for l in html.splitlines():
            if l.startswith('ta') and 'Re' not in l:
                try:
                    content = re.search('\((.*)\)', l).group(1).strip()
                    if not content:
                        continue
                    # ipdb.set_trace()
                    # userid = re.search('<a href="bbsqry.php?userid=(?P<userid>\w+?)">(?P=userid)</a>', content)
                    userid = re.search('>(.+)<', content.split(',')[2])[1]
                    date_time = content.split(',')[3].strip().replace(' ', '0').replace('&nbsp;', ' ').strip("'")
                    date_time = datetime.strptime(date_time, '%b %d').strftime('%m-%d')
                    title = re.search('>(.+)<', content.split(',', 4)[4])[1].strip()
                    url = 'https://www.newsmth.net/nForum/#!article/HouseRent/' + \
                        re.search('id=(\d+)">', content.split(',', 4)[4])[1].strip()
                    item = {'post_user': userid, 'date_time': date_time,
                            'title': title, 'url': url}
                    items.append(item)
                except Exception as e:
                    print(sys.exc_info()[0:2])
                    print(traceback.extract_tb(sys.exc_info()[2]))
        return reversed(items)


class DoubanParser(BaseParser):

    def __init__(self):
        super(DoubanParser, self).__init__()
        self.groups = {
            '625354': '北京租房（真的没有中介）小组',
            '576564': '西二旗上地房东租房',
            '605457': '上地西二旗合租群',
            'FZG': '北京租房无中介联盟',
            '279962': '北京租房（非中介）',

            'zhufang': '北京无中介租房（寻天使投资）',
            'opking': '北京个人租房 （真房源|无中介）',
            '257523': '北京租房房东联盟(中介勿扰)',
            '465554': '北京 租房 房东 直租（非中介）',
            'bjzft': '北京租房团（不欢迎中介）',
        }
        self.base_url = 'https://www.douban.com/group/search'
        self.params = {
            'cat': 1013,
            'group': '625354',
            'q': '柳浪家园',
            'sort': 'time',
        }

    def parse(self):
        title_item_map = {}
        for group_id, group_name in self.groups.items():
            # print(group)
            self.params['group'] = group_id
            for keyword in KEYWORDS:
                # print('----', keyword)
                self.params['q'] = keyword
                html = self.get_res(self.base_url, self.params)
                if html is None:
                    continue
                html = html.decode('utf8', errors='ignore')
                items = self.parse_html(html)
                for item in items:
                    title = item['title'].strip() + '_' + item['post_user']
                    if title not in title_item_map:
                        item['group'] = group_name
                        title_item_map[title] = item
        return sorted(list(title_item_map.values()), key=lambda x: x['date_time'], reverse=True)

    def parse_html(self, html):
        items = []
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table', class_='olt')
        if table is None:
            return []
        for tr in table.tbody.find_all('tr', recursive=False):
            try:
                tds = tr.find_all('td', recursive=False )
                date_time = tds[1]['title']
                if datetime.today() - datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S') > timedelta(30):
                    break
                url = tds[0].a['href']
                title = tds[0].a['title']
                reply_num = tds[2].span.text
                item = {'post_user': '', 'date_time': date_time,
                        'title': title, 'url': url, 'reply_num': reply_num}
                items.append(item)
            except Exception as e:
                print(sys.exc_info()[0:2])
                print(traceback.extract_tb(sys.exc_info()[2]))
        return items


class FiveEightParser(BaseParser):

    def __init__(self):
        super(FiveEightParser, self).__init__()
        self.base_url = 'https://bj.58.com/haidian/hezu/0/d2/' \
                        '?minprice=2000_3500&PGTID=&ClickID=2'
        self.params = {
            'minprice': '2000_3500',
            'PGTID': '0d30000a-0047-749f-17ad-def6e8738d26',
            'ClickID': '2',
        }

    def parse(self):
        html = self.get_res(self.base_url, self.params)
        if html is None:
            return None
        html = html.decode('utf8', errors='ignore')
        items = self.parse_html(html)
        return items

    def parse_html(self, html):
        items = []
        soup = BeautifulSoup(html, 'lxml')
        ul = soup.find('ul', class_='listUl')
        if ul is None:
            return []
        for li in ul.find_all('li', recursive=False):
            div = li.find('div', class_='des')
            if div is None:
                continue
            a_tag = div.find('a', class_='strongbox')
            url = 'https::' + a_tag['href']
            title = a_tag.text.strip()
            for keyword in KEYWORDS:
                if keyword in title:
                    item = {'post_user': '', 'date_time': '',
                            'title': title, 'url': url, 'reply_num': ''}
                    items.append(item)
                    break
            # try:
            # except Exception as e:
            #     print(sys.exc_info()[0:2])
            #     print(traceback.extract_tb(sys.exc_info()[2]))
        return items


def print_(items):
    for item in items:
        print(item)
    print()


def make_html(items, head):
    html = '<table>\n'
    html += '<th>%s</th>\n' % head
    for item in items:
        html += '<tr>\n'
        for key in ['date_time', 'title', 'post_user', 'group', 'reply_num']:
            if key in item and item[key]:
                value = item[key]
                html += '<td>'
                if key == 'title':
                    html += '<a href="%s" target="_blank">%s</a>' % (item['url'], value)
                else:
                    html += value
                html += '</td>\n'
        html += '</tr>\n'
    html += '</table>\n'
    return html



if __name__ == '__main__':
    html = ''

    parser = SMTHParser()
    items = parser.parse()
    print_(items)
    html += make_html(items, '水木社区')

    parser = DoubanParser()
    items = parser.parse()
    print_(items)
    html += make_html(items, '豆瓣')

    parser = FiveEightParser()
    items = parser.parse()
    print_(items)
    html += make_html(items, '58同城')

    open('index.html', 'w', encoding='utf8').write(html)
