# main.py
from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from difflib import SequenceMatcher
import os

app = FastAPI(title="CNKI 论文标题检索服务", description="使用原始 find_closest_title 匹配算法，返回最相似论文标题")

# =================== 配置参数 ===================
CHROMEDRIVER_PATH = r"E:\chromedriver-win64\chromedriver.exe"  # 修改为你本地路径
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
]

# =================== 工具函数 ===================

def init_browser():
    """初始化浏览器，带防检测配置"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=Service(CHROMEDRIVER_PATH), options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
          """
    })

    return driver

def find_closest_title(title: str, result_titles: List[str]) -> int:
    """根据字符匹配度选择最接近的搜索结果（原版逻辑）"""
    max_similar = 0
    best_index = 0
    for i, t in enumerate(result_titles):
        common_chars = sum(c in t for c in title)
        if common_chars > max_similar:
            max_similar = common_chars
            best_index = i
    return best_index

@app.get("/search")
def search_paper(query: str = Query(..., min_length=1)):
    """
    检索知网中与输入标题最相似的论文标题。
    
    - 使用原始 find_closest_title 算法（按字符出现次数匹配）
    - 不过滤“模拟器”等关键词（可后续添加）
    - 返回最佳匹配标题
    """
    if not query or len(query.strip()) == 0:
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    try:
        driver = init_browser()
        driver.get("https://www.cnki.net/")
        time.sleep(random.uniform(1, 2))

        # 搜索框输入
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "txt_SearchText"))
        )
        search_box.clear()
        for char in query:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        driver.find_element(By.CLASS_NAME, "search-btn").click()

        time.sleep(random.uniform(2, 3))

        # 获取搜索结果
        try:
            results = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, '//div[@id="gridTable"]//a[@class="fz14"]'))
            )
            result_titles = [r.text.strip() for r in results]
        except Exception as e:
            print(f"未找到结果: {e}")
            result_titles = []

        # 使用原始函数找最佳匹配
        if not result_titles:
            best_title = ""
        else:
            idx = find_closest_title(query, result_titles)
            best_title = result_titles[idx]

        driver.quit()

        return {
            "query": query,
            "best_match": best_title,
            "total_results": len(result_titles),
            "message": "成功检索并匹配" if best_title else "未找到结果"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败：{str(e)}")

@app.get("/")
def root():
    return {"message": "CNKI 论文标题检索服务已启动，请访问 /search?query=xxx 查询"}