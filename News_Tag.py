import os
import time
import logging
import configparser
import requests
from newspaper import Article
import mysql.connector
from mysql.connector import Error
from bs4 import BeautifulSoup
from openai import OpenAI 

# 日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_tagging.log'),
        logging.StreamHandler()
    ]
)

class NewsTagger:
    def __init__(self, config_path='config.ini'):
        """初始化配置、数据库连接和DeepSeek客户端"""
        self.config = self.load_config(config_path)
        self.db_connection = self.connect_to_database()
        self.tag_mapping = self.init_tags()
        self.headers = eval(self.config['requests']['headers'])
        
        # 初始化DeepSeek客户端
        self.deepseek_client = OpenAI(
            api_key=self.config['deepseek']['api_key'],  
            base_url=self.config['deepseek']['base_url'] 
        )

    def load_config(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件 {config_path} 不存在")
        
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        return config

    def connect_to_database(self):
        try:
            connection = mysql.connector.connect(
                host=self.config['database']['host'],
                user=self.config['database']['user'],
                password=self.config['database']['password'],
                database=self.config['database']['database']
            )
            if connection.is_connected():
                logging.info("数据库连接成功")
                return connection
        except Error as e:
            logging.error(f"数据库连接失败: {e}")
            raise

    def init_tags(self):
        cursor = self.db_connection.cursor(dictionary=True)
        tag_mapping = {}

        try:
        
            cursor.execute("SELECT TagName, Type FROM Tag")
            required_tags = [(row['TagName'], row['Type']) for row in cursor.fetchall()]
        
            if not required_tags:
                logging.warning("Tag表中没有任何标签数据，tag_mapping将为空")
                return tag_mapping
        
            cursor.execute("SELECT TagID, TagName FROM Tag")
            existing_tags = {row['TagName']: row['TagID'] for row in cursor.fetchall()}

            for tag_name, tag_type in required_tags:
                if tag_name in existing_tags:
                    tag_mapping[tag_name] = existing_tags[tag_name]
                else:
                    logging.warning(f"标签 {tag_name} 在Tag表中不存在，已跳过")

            logging.info(f"标签初始化完成，从Tag表读取到 {len(required_tags)} 个标签")
            return tag_mapping
        
        except Error as e:
            self.db_connection.rollback()
            logging.error(f"标签初始化失败: {e}")
            raise
        finally:
            cursor.close()

    def get_untagged_news(self):
        cursor = self.db_connection.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT NewsID, URL FROM News 
                WHERE NewsID NOT IN (SELECT DISTINCT NewsID FROM News_Tag)
            """)
            untagged_news = cursor.fetchall()
            logging.info(f"找到 {len(untagged_news)} 条未处理的新闻")
            return untagged_news
        except Error as e:
            logging.error(f"获取未处理新闻失败: {e}")
            return []
        finally:
            cursor.close()

    def extract_news_content(self, url):
        """新闻内容提取函数"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            html_content = response.text

            if "mp.weixin.qq.com" in url:
                content = self._parse_wechat_article(html_content, url)
            else:
                content = self._parse_with_newspaper(url, headers)
                if not content or len(content.strip()) < 100:
                    logging.info(f"newspaper3k解析失败，尝试通用解析: {url}")
                    content = self._parse_general_article(html_content, url)

            if content:
                content = '\n'.join([line.strip() for line in content.split('\n') if line.strip()])
                max_length = 5000
                if len(content) > max_length:
                    content = content[:max_length] + "..."
                    logging.info(f"内容过长，已截断至 {max_length} 字符: {url}")
                return content
            else:
                logging.warning(f"所有解析策略均失败，无法提取内容: {url}")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"请求URL失败 (URL: {url}): {str(e)}")
            return None
        except Exception as e:
            logging.error(f"提取新闻内容异常 (URL: {url}): {str(e)}", exc_info=True)
            return None

    def _parse_wechat_article(self, html_content, url):
        soup = BeautifulSoup(html_content, 'lxml')
        content_div = soup.find('div', class_='rich_media_content')
        if not content_div:
            logging.warning(f"未找到微信公众号正文标签: {url}")
            return None
        content = content_div.get_text(strip=True, separator='\n')
        return content

    def _parse_with_newspaper(self, url, headers):
        try:
            article = Article(url, headers=headers)
            article.download()
            if not article.is_downloaded:
                logging.warning(f"newspaper3k下载失败: {url}")
                return None
            article.parse()
            return article.text.strip()
        except Exception as e:
            logging.error(f"newspaper3k解析失败 (URL: {url}): {str(e)}")
            return None

    def _parse_general_article(self, html_content, url):
        soup = BeautifulSoup(html_content, 'lxml')
        common_content_tags = [
            ('article', None),
            ('div', 'article-content'),
            ('div', 'content'),
            ('div', 'main-content'),
            ('div', 'post-content'),
            ('div', 'news-content'),
            ('div', 'detail-content'),
            ('div', {'id': ['content', 'main-content', 'news-content']}),
        ]

        for tag_name, attr in common_content_tags:
            if attr is None:
                content_elem = soup.find(tag_name)
            elif isinstance(attr, str):
                content_elem = soup.find(tag_name, class_=attr)
            else:
                content_elem = soup.find(tag_name, **attr)
            
            if content_elem:
                content = content_elem.get_text(strip=True, separator='\n')
                if len(content) > 100:
                    return content

        p_tags = soup.find_all('p')
        if p_tags:
            content = '\n'.join([p.get_text(strip=True) for p in p_tags if p.get_text(strip=True)])
            if len(content) > 100:
                return content

        return None

    def call_deepseek_api(self, content):
        """调用DeepSeek API（基于官方OpenAI SDK示例）"""
        if not content:
            return []
        
        # 提示词
        prompt = f"""
        请严格分析以下新闻内容，判断它属于下列哪些标签。判断标准：
        - 微信公众号：该网站属于微信公众号内容，所给url包含mp.weixin关键词等；
        - 师生成就：包含教师/学生获得的荣誉、奖项、科研成果、竞赛成绩、优秀评选等；
        - 文体活动：包含运动、艺术等课外活动；
        - 其他标签：按名称字面意思，内容相关即可匹配。
        
        可选标签列表：
        {'、'.join(self.tag_mapping.keys())}
        
        输出要求：
        1. 只返回匹配的标签名称，每个标签单独一行；
        2. 不返回任何解释或额外内容；
        3. 即使只有一项匹配也必须列出，无匹配则返回空。
        
        新闻内容：
        {content}
        """

        try:
            # 调用API
            response = self.deepseek_client.chat.completions.create(
                model="deepseek-reasoner",  # chat太笨了，这里一定要用reasoner
                messages=[
                    {"role": "system", "content": "你是一个精准的标签匹配助手，只返回符合要求的标签"},
                    {"role": "user", "content": prompt}
                ],
                stream=False,  
                temperature=0.2  
            )

            # 解析SDK返回结果（注意结构与直接HTTP请求不同）
            tags_text = response.choices[0].message.content.strip()
            if not tags_text:
                return []
            
            # 处理返回的标签列表
            matched_tags = [line.strip() for line in tags_text.split('\n') if line.strip()]
            valid_tags = [tag for tag in matched_tags if tag in self.tag_mapping]
            return valid_tags

        except Exception as e:
            logging.error(f"DeepSeek API调用失败: {str(e)}")
            return []

    def save_tag_mapping(self, news_id, tag_names):
        if not tag_names:
            logging.info(f"新闻 {news_id} 没有匹配的标签，无需保存")
            return True

        cursor = self.db_connection.cursor()
        try:
            insert_data = [
                (news_id, self.tag_mapping[tag_name]) 
                for tag_name in tag_names
            ]
            cursor.executemany(
                "INSERT IGNORE INTO News_Tag (NewsID, TagID) VALUES (%s, %s)",
                insert_data
            )
            self.db_connection.commit()
            logging.info(f"新闻 {news_id} 成功匹配 {len(insert_data)} 个标签")
            return True
        except Error as e:
            self.db_connection.rollback()
            logging.error(f"保存标签映射失败 (新闻ID: {news_id}): {e}")
            return False
        finally:
            cursor.close()

    def process_news(self):
        untagged_news = self.get_untagged_news()
        for news in untagged_news:
            news_id = news['NewsID']
            url = news['URL']
            logging.info(f"开始处理新闻 (ID: {news_id}, URL: {url})")

            content = self.extract_news_content(url)
            if not content:
                logging.warning(f"跳过新闻 {news_id} (无法提取内容)")
                continue

            matched_tags = self.call_deepseek_api(content)
            logging.info(f"新闻 {news_id} 匹配到标签: {matched_tags}")

            self.save_tag_mapping(news_id, matched_tags)

            time.sleep(2)  

        logging.info("所有未处理新闻处理完毕")

    def close(self):
        if self.db_connection and self.db_connection.is_connected():
            self.db_connection.close()
            logging.info("数据库连接已关闭")

if __name__ == "__main__":
    try:
        tagger = NewsTagger()
        tagger.process_news()
    except Exception as e:
        logging.critical(f"程序运行失败: {str(e)}", exc_info=True)
    finally:
        if 'tagger' in locals():
            tagger.close()