# run.py
from zhSpider import ZhihuSpider
import sys

def main():
    spider = ZhihuSpider()
    print("请设置知乎Cookie：")
    cookie = input().strip()
    if cookie:
        spider.set_cookie(cookie)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'query':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        articles = spider.query_articles(category=category)
        
        print(f"\n{'='*80}")
        print(f"{'标题':<50} {'赞同数':<10} {'分类':<10} {'创建时间'}")
        print(f"{'='*80}")
        
        for article in articles:
            title, url, upvotes, category, created_time = article
            print(f"{title[:47]+'...':<50} {upvotes:<10} {category:<10} {created_time}")
    else:
        spider.run()

if __name__ == "__main__":
    main()