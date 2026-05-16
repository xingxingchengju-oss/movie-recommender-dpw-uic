"""
2 Browser Driver Class
- Chrome driver class
- Edge driver class

I commented the edge driver class.
If you want to use the edge driver, please uncomment the code and comment the chrome driver class.
"""

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager


# class BrowserDriver:

#     def __init__(self):

#         options = webdriver.ChromeOptions()
#         options.add_argument("--disable-blink-features=AutomationControlled")
#         options.add_argument("--start-maximized")

#         self.driver = webdriver.Chrome(
#             service=Service(ChromeDriverManager().install()), options=options
#         )

#     def get_page(self, url):

#         self.driver.get(url)

#     def current_page(self):

#         return self.driver.page_source

#     def close(self):

#         self.driver.quit()


# # For Edge browser
from selenium import webdriver
from selenium.webdriver.edge.service import Service


class BrowserDriver:
    def __init__(self):
        options = webdriver.EdgeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")

        # 指定你的 Edge Driver 路径
        edge_driver_path = r"D:\edgedriver_win64\msedgedriver.exe"

        self.driver = webdriver.Edge(service=Service(edge_driver_path), options=options)

    def get_page(self, url):
        self.driver.get(url)

    def current_page(self):
        return self.driver.page_source

    def close(self):
        self.driver.quit()
