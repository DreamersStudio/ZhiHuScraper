# zhSpider.py
import requests
import json
import time
import random
import sqlite3
import jieba
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urljoin
import traceback

class ZhihuSpider:
    def __init__(self):
        self.base_url = "https://www.zhihu.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cookie': '',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
        self.session = requests.Session()
        self.initialize_database()
        self.categories = {
            'tech': ['编程', '技术', '计算机', 'Python', '人工智能', '开发'],
            'finance': ['理财', '投资', '金融', '股票', '基金'],
            'career': ['职场', '工作', '面试', '求职', '创业'],
            'life': ['生活', '健康', '美食', '旅行', '情感'],
            'education': ['教育', '学习', '考试', '留学', '考研']
        }

    def initialize_database(self):
        self.conn = sqlite3.connect('zhihu_articles.db')
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            upvotes INTEGER NOT NULL,
            category TEXT NOT NULL,
            created_time DATETIME NOT NULL,
            collect_time DATETIME NOT NULL
        )
        ''')
        self.conn.commit()
        print("数据库初始化完成")

    def set_cookie(self, cookie_str):
        self.headers['Cookie'] = cookie_str
        self.session.headers.update(self.headers)
        print("Cookie已更新")

    def make_request(self, url, method='GET', params=None, data=None, json_data=None):
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=self.headers,
                timeout=10
            )
            print(f"请求 {url} 状态码: {response.status_code}")
            if response.status_code == 200:
                return response
            else:
                print(f"请求失败: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"请求异常: {str(e)}")
            return None

    def get_hot_topics(self):
        topics = []
        # 方法1：从热榜获取
        response = self.make_request("https://www.zhihu.com/topics/hot")
        if response:
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                print(f"页面标题: {soup.title.text if soup.title else 'No title'}")
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/question/' in href or '/p/' in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in topics:
                            topics.append(full_url)
            except Exception as e:
                print(f"解析热榜页面出错: {str(e)}")

        # 方法2：从知乎首页获取
        response = self.make_request("https://www.zhihu.com")
        if response:
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/question/' in href or '/p/' in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in topics:
                            topics.append(full_url)
            except Exception as e:
                print(f"解析首页出错: {str(e)}")

        print(f"总共找到 {len(topics)} 个话题")
        if topics:
            print("示例URL:")
            for url in topics[:3]:
                print(f"- {url}")
        return topics

    def get_article_content(self, url):
        try:
            time.sleep(random.uniform(1, 3))
            print(f"获取文章: {url}")
            response = self.make_request(url)
            if not response:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            if 'zhuanlan.zhihu.com' in url:
                title = soup.select_one('h1.Post-Title')
                content = soup.select_one('div.Post-RichText')
                vote = soup.select_one('button.VoteButton--up')
            else:
                title = soup.select_one('h1.QuestionHeader-title')
                content = soup.select_one('div.RichText.ztext')
                vote = soup.select_one('button.Button.VoteButton.VoteButton--up')

            if title and content:
                title_text = title.get_text(strip=True)
                content_text = content.get_text(strip=True)
                upvotes = 0
                
                if vote:
                    vote_text = vote.get_text(strip=True)
                    vote_match = re.search(r'\d+', vote_text)
                    if vote_match:
                        upvotes = int(vote_match.group())

                print(f"找到文章: {title_text[:30]}... (赞同数: {upvotes})")
                return {
                    'title': title_text,
                    'content': content_text,
                    'upvotes': upvotes,
                    'url': url
                }
            return None
        except Exception as e:
            print(f"获取文章内容出错 {url}: {str(e)}")
            print(traceback.format_exc())
            return None

    def classify_article(self, content):
        words = list(jieba.cut(content))
        scores = {category: sum(1 for word in words if any(kw in word for kw in keywords))
                 for category, keywords in self.categories.items()}
        return max(scores.items(), key=lambda x: x[1])[0] if scores else 'others'

    def save_article(self, article_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO articles (title, url, content, upvotes, category, created_time, collect_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                article_data['title'],
                article_data['url'],
                article_data['content'],
                article_data['upvotes'],
                article_data['category'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"保存文章失败: {str(e)}")
            return False

    def run(self):
        print("开始爬取知乎文章...")
        while True:
            try:
                print("\n获取热门话题...")
                topics = self.get_hot_topics()
                
                if not topics:
                    print("未获取到话题，等待1分钟后重试...")
                    time.sleep(60)
                    continue

                successful_count = 0
                for url in topics:
                    try:
                        article_data = self.get_article_content(url)
                        if article_data and article_data['upvotes'] >= 1000:
                            article_data['category'] = self.classify_article(article_data['content'])
                            if self.save_article(article_data):
                                successful_count += 1
                                print(f"已保存: {article_data['title'][:30]}... (赞同: {article_data['upvotes']})")
                    except Exception as e:
                        print(f"处理文章出错 {url}: {str(e)}")
                        continue

                print(f"\n本轮完成，保存了 {successful_count} 篇文章")
                print("等待5分钟后开始下一轮...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                print("\n程序已停止")
                break
            except Exception as e:
                print(f"发生错误: {str(e)}")
                print(traceback.format_exc())
                time.sleep(60)
                
        self.conn.close()

    def query_articles(self, category=None, min_upvotes=1000):
        cursor = self.conn.cursor()
        if category:
            cursor.execute('''
            SELECT title, url, upvotes, category, created_time 
            FROM articles 
            WHERE category = ? AND upvotes >= ?
            ORDER BY upvotes DESC
            ''', (category, min_upvotes))
        else:
            cursor.execute('''
            SELECT title, url, upvotes, category, created_time 
            FROM articles 
            WHERE upvotes >= ?
            ORDER BY upvotes DESC
            ''', (min_upvotes,))
        return cursor.fetchall()