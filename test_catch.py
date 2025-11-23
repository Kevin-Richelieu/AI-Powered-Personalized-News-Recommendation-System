import requests
import urllib3
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.cs.sjtu.edu.cn"
AJAX_PATH = "/active/ajax_type_list.html"
DEFAULT_HEADERS = {
    # 模拟浏览器 User-Agent
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    # 关键：指定内容类型为表单数据
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    # 关键：模拟 AJAX 请求
    'X-Requested-With': 'XMLHttpRequest' 
}

def catch_article(URL,headers,tag):
    try:
    # 发送请求，requests默认会自动处理重定向
        response = requests.get(URL, headers=headers)
    
        # 检查响应状态码：200 表示成功
        if response.status_code == 200:
            # 设置正确的编码，防止中文乱码
            response.encoding = response.apparent_encoding
            response.encoding = 'utf-8'
            html_content = response.text
            # print(html_content)
        else:
            print(f"请求失败，状态码: {response.status_code}")
            html_content = None

    except requests.exceptions.RequestException as e:
        print(f"发生请求错误: {e}")
        html_content = None

    # 2. 将 HTML 字符串交给 BeautifulSoup 解析
    soup = BeautifulSoup(html_content, 'lxml') 


    extracted_data = []

    # 示例 A: 抓取新闻列表页的标题和二级跳转链接
    # 假设新闻列表项的 class 是 'news-item'
    for item in soup.find_all('div', class_='xw-cont'):
        # 假设标题和链接都在 class 为 'item-title' 的 a 标签里
        title_tag = item.find('div', class_='tit') 
        time_tag = item.find('div',class_='jj')
        content_tag = item.find('div',class_='txt')

        if title_tag:
            title = title_tag.text
            print(title)
            extracted_data.append({
                'title': title,
            })
        if time_tag:
            time = time_tag.find('p')
            print(time)
            extracted_data.append({
                'time': time.text[5:],
            })
        if content_tag:
            all_spans = content_tag.find_all('p') 

            paragraph_list = []

            for span_tag in all_spans:
                # 3. 提取 span 标签中的文本
                text = span_tag.text.strip()
                if text:
                    paragraph_list.append(text)

            # 4. (可选) 将所有段落重新合并，用换行符分隔
            final_article = '\n'.join(paragraph_list)
            print(final_article)

            extracted_data.append({
                'content': final_article,
            })
        extracted_data.append({
            'tag': tag,
        })

    return extracted_data
    
def catch_href(URL,headers):
    try:
        time.sleep(1)
    # 发送请求，requests默认会自动处理重定向
        response = requests.get(URL, headers=headers)
    
        # 检查响应状态码：200 表示成功
        if response.status_code == 200:
            # 设置正确的编码，防止中文乱码
            response.encoding = response.apparent_encoding
            response.encoding = 'utf-8'
            html_content = response.text
            # print(html_content)
        else:
            print(f"请求失败，状态码: {response.status_code}")
            html_content = None

    except requests.exceptions.RequestException as e:
        print(f"发生请求错误: {e}")
        html_content = None

    # 2. 将 HTML 字符串交给 BeautifulSoup 解析
    soup = BeautifulSoup(html_content, 'lxml') 

    url = []
    results = []

    # 示例 A: 抓取新闻列表页的标题和二级跳转链接
    for item in soup.find_all('div', class_='swiper-lm tab'):
        all_hrefs = item.find_all('a')
        if all_hrefs:
            for all_href in all_hrefs:
                tag = all_href.text.strip()
                link = all_href.get('href')
                print(link)
                url.append({
                    'link': link,
                    'tag': tag,
                })
    results.append(url)
    return results

def catch_article_href(url,headers=DEFAULT_HEADERS):
    """
    抓取文章列表页中的所有链接。
    使用 POST 方法，完整的 Payload 结构，并实现多页抓取。
    只返回干净的 URL 字符串列表。
    """
    all_urls = []
    
    # 1. 从输入 URL 中提取 cat_code 和文章基础路径
    parsed_url = urlparse(url)
    path = parsed_url.path 
    code_match = re.search(r'/([^/]+)\.html$', path)
    
    if not code_match:
        print("ERROR: 无法从 URL 路径中提取 cat_code。请确保 URL 以 .html 结尾。")
        return []

    # 提取栏目代号 (例如 xsgz-tzgg-djdy)
    cat_code = code_match.group(1)
    
    # 构造文章链接的基础路径 (例如 https://www.cs.sjtu.edu.cn/xsgz-tzgg-djdy/)
    print(f"INFO: 成功提取 cat_code: {cat_code}")


    # 2. 循环发送 POST 请求，获取所有页面数据
    page = 1
    has_more = True
    AJAX_URL = f"{BASE_URL}{AJAX_PATH}"

    while has_more:
        # 构建完整的 POST 请求体数据
        post_data = {
            'page': str(page), 
            'cat_code': cat_code,
            'type': '',
            'search': '',
            'extend_id': '0',
            'template': 'ajax_news_list1_search' 
        }
        
        # 发送 POST 请求
        time.sleep(1) # 延迟 1 秒，避免请求过快
        try:
            response = requests.post(AJAX_URL, data=post_data, headers=headers, verify=False, timeout=15)
            
            if response.status_code != 200:
                print(f"请求失败，状态码 {response.status_code}: {AJAX_URL}")
                break
                
            response.encoding = response.apparent_encoding
            ajax_html = response.text
            
            # 检查响应是否包含列表项（文章），否则表示页码超出
            if not re.search(r'<li', ajax_html, re.IGNORECASE):
                has_more = False
                print(f"INFO: Page {page} 未发现更多文章，停止翻页。")
                break
                
            ajax_soup = BeautifulSoup(ajax_html, 'lxml')
            
        except requests.exceptions.RequestException as e:
            print(f"发生请求错误: {e}")
            break

        # 3. 从 AJAX 响应中提取文章 ID 并拼接链接
        article_links = ajax_soup.select('li > a') 
        
        if article_links:
            current_page_links = []
            # print(article_links)
            # 匹配文章 ID 的正则表达式: /article_id.html"
            # 例如: .../xsgz-tzgg-djdy/1042.html"
            id_pattern = re.compile(r'\/(\d+)\.html')
            
            for a_tag in article_links:
                link = a_tag.get('href')
                
                if link:
                    # 使用正则表达式匹配并提取文章 ID (例如 '1042')
                    id_match = id_pattern.search(link)
                    if id_match:
                        article_id = id_match.group(1)
                        # 构造最终的干净 URL
                        clean_link = f"{url[:-5]}/{article_id}.html"
                        print("here"+clean_link)
                        current_page_links.append(clean_link)
                
                # 如果没有链接或ID匹配失败，则跳过
            
            if current_page_links:
                all_urls.extend(current_page_links)
                print(f"INFO: Page {page} 成功解析到 {len(current_page_links)} 条链接。")
                page += 1 # 准备请求下一页
            else:
                has_more = False
        else:
            has_more = False # 结束循环

    return all_urls

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 替换为您要抓取的新闻列表页 URL

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
    # 关键：指定内容类型为表单数据
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    # 关键：模拟 AJAX 请求
    'X-Requested-With': 'XMLHttpRequest'
}

URL = "https://www.cs.sjtu.edu.cn/xsgz-tzgg-djdy.html"

urls = catch_href(URL,headers)
for url in urls:
    for sub_url in url:
        tag = sub_url['tag']
        article_lists = catch_article_href(sub_url['link'],headers)
        for article_list in article_lists:
            result = catch_article(article_list,headers,tag)


