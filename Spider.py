from urllib.parse import urlencode
from bs4 import BeautifulSoup
import re
import requests
import os
import time
from multiprocessing.pool import Pool

# 定义爬虫所用到的user-agent(用户代理)放入headers中
agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 ' \
        '(KHTML, like Gecko) Chrome/63.0.3239.26 ' \
        'Safari/537.36 Core/1.63.6721.400 QQBrowser/10.2.2243.400'
headers = {
    'user-agent': agent
}
# 获取今天日期（建立一个以日期为名的主文件夹）
TODAY = time.strftime('%Y-%m-%d')


# 建立文件夹（对文件夹是否已经存在进行判断）
def mkdir(folder_name):
    # 若不存在，则建立文件夹
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name


# 解析top100的列表页面，返回页面的内容
def get_page_response(page):
    # ajax请求的json数据
    params = {
        'p': page,
        'type': 'week',
        'data': ''
    }
    # ajax请求的url
    base_url = 'https://bcy.net/coser/index/ajaxloadtoppost?'
    # 拼接url
    url = base_url + urlencode(params)
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text.encode('utf-8')
    except requests.ConnectionError:
        return None


# 得到所有作品的url
def get_work_urls(response):
    soup = BeautifulSoup(response, 'lxml')
    #
    # 寻找页面li标签
    all_li = soup.find_all('li', class_=re.compile('js-smallCards _box'))

    urls = []
    ranks = []
    # 寻找li标签中的a标签提取url，span标签可以提取排名
    for li in all_li:
        a = li.find('a')
        rank = li.find('span')
        urls.append(a['href'])
        ranks.append(rank.text)
    return urls, ranks


# 得到页面所有图片的url
def get_image_urls(content):
    # 构造pattern寻找页面内容中的图片url
    pattern = re.compile('"path(.*?)w650', re.S)
    items = re.findall(pattern, content)
    # 对提取内容进行修改，得到正确的url
    for i in range(len(items)):
        items[i] = items[i].replace(r'\\u002F', '/')
        items[i] = items[i][5:-1]
    return items


# 下载图片
def download_image(urls, ranks):
    # url的前缀
    prefix_url = 'https://bcy.net'
    for (suffix_url, rank) in zip(urls, ranks):
        # 拼接获得正确的url
        url = prefix_url + suffix_url
        content = requests.get(url, headers=headers).text
        # 获得所有图片的url
        image_urls = get_image_urls(content)
        # 利用标题为每组图片建立文件夹
        soup = BeautifulSoup(content, 'html5lib')
        title = soup.title.string
        # 需要去掉标题的非法字符（文件夹名字）
        unvalid_str = '<>,\/|,:,"",*,?'
        for ch in unvalid_str:
            title = title.replace(ch, '')
        # 建立文件夹(日期为根目录)将排名也写入文件夹名字中
        fold_name = mkdir(TODAY + '\\' + str(rank) + '.' + title)
        # 循环下载所有图片
        for i in range(len(image_urls)):
            try:
                # requests下载数据
                pic = requests.get(image_urls[i], stream=True, headers=headers, timeout=12)
                # 构建下载路径
                file_local_url = fold_name + '\\' + str(i) + '.jpg'
                if os.path.exists(file_local_url):
                    print('pic has been downloaded!')
                else:
                    with open(file_local_url, 'wb', buffering=4 * 1024) as fp:
                        fp.write(pic.content)
                        fp.flush()
            except:
                pass
        print("TOP " + str(rank) + " 下载完成")

# 主函数
def main(page):
    # 建立以日期为名的根目录
    mkdir(TODAY)
    # 得到top100列表页面的内容
    response = get_page_response(page)
    # 获得所有的COS图的链接，以及COS的排名
    urls, ranks = get_work_urls(response)
    # 下载图片
    download_image(urls, ranks)


if __name__ == '__main__':
    pool = Pool()
    # 一共6组ajax请求
    groups = ([x+1 for x in range(6)])
    # map()实现多线程下载
    pool.map(main, groups)
    # 关闭
    pool.close()
    # 如果主线程阻塞后，让子进程继续运行完成之后，在关闭所有的主进程
    pool.join()
