from dotenv import load_dotenv
import os

load_dotenv()
# Scrapy settings for govoportunidades project

#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "govoportunidades"

SPIDER_MODULES = ["govoportunidades.spiders"]
NEWSPIDER_MODULE = "govoportunidades.spiders"
# MONGO_URI = "mongodb://localhost:27017"
# MONGO_DATABASE = "govoportunidades"
ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "govoportunidades (+http://www.yourdomain.com)"

# Obey robots.txt rules
# ROBOTSTXT_OBEY = True

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "govoportunidades.middlewares.GovoportunidadesSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "govoportunidades.middlewares.GovoportunidadesDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
   "govoportunidades.pipelines.NotificationDedupPipeline": 150,
   "govoportunidades.pipelines.SQLitePipeline": 200,
   "govoportunidades.pipelines.NotificationPipeline": 300,
   # "govoportunidades.pipelines.MongoDBPipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

MAIL_HOST = os.getenv("SCRAPY_MAIL_HOST")
MAIL_PORT = os.getenv("SCRAPY_MAIL_PORT")
MAIL_USER = os.getenv("SCRAPY_MAIL_USER")
MAIL_PASS = os.getenv("SCRAPY_MAIL_PASS")
MAIL_FROM = os.getenv("SCRAPY_MAIL_FROM", MAIL_USER)
MAIL_TLS = True
MAIL_SSL = False

# Email addresses to send notifications to
MAIL_TO = os.getenv("SCRAPY_MAIL_TO", "").split(",")

# Keywords to search for in the scraped content
KEY_WORDS = os.getenv("SCRAPY_KEY_WORDS", "").split(",")

# Path to the SQLite database file
EDITAIS_DB_PATH = os.getenv("EDITAIS_DB_PATH", "editais.db")