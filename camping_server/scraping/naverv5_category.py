from selenium import webdriver
import camping_server.config as config
import time
import pandas as pd
import re


class CategoryScraping:
    """
    네이버 지도 v5 '캠핑장' 카테고리별 하이라이트 리뷰 크롤링
    """
    def __init__(self, keyword):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()
        self.url = f"https://map.naver.com/v5/search/{keyword}"
        self.driver.get(self.url)

    def switch_iframe(self):
        """main search list iframe switch (1)"""
        iframe = self.driver.find_element_by_xpath('//*[@id="searchIframe"]')
        self.driver.switch_to.frame(iframe)
        time.sleep(1)

        try:
            items = self.driver.find_elements_by_xpath('//*[@id="_pcmap_list_scroll_container"]/ul/li')
            items[0].find_element_by_xpath('div[1]/a').click()
        except:
            pass # 메인에서 바로 iframe으로 진입되는 경우
        finally:
            self.driver.switch_to.default_content()
            time.sleep(1)
            try:
                iframe = self.driver.find_element_by_css_selector('#entryIframe')
                time.sleep(1)
                self.driver.switch_to.frame(iframe)
                time.sleep(1)
            except:
                pass

    def move_tab(self):
        """enter iframe + click review tab (2)"""
        try:
            title = self.driver.find_element_by_xpath('//*[@id="_title"]/span[1]').text
        except:
            title = ''
            return title

        menus = self.driver.find_element_by_xpath('//*[@id="app-root"]/div/div[2]/div[3]/div/div/div/div').text
        menus = str(menus).split(' ')

        try:
            review_idx = menus.index('리뷰')
            self.driver.find_element_by_xpath(
                f'//*[@id="app-root"]/div/div[2]/div[3]/div/div/div/div/a[{review_idx + 1}]').click()
        except:
            print('Index Error')
            self.driver.switch_to.default_content()

        return title

    def get_categories(self):
        """ all categories (3)"""
        global category
        category = ''
        time.sleep(2)

        try: # category no such element scroll down
            category = self.driver.find_element_by_xpath(
                '//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/div[1]/div')
        except:
            self.driver.execute_script('window.scrollTo(0, 1000);')
            category = self.driver.find_element_by_xpath(
                '//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/div[1]/div')
        finally:
            return category

    def click_cagetory(self, category, idx=1):
        """
        click category (4)
        category : str
            target category
        idx : int
            target category a tag index
        """
        target_category = category.find_element_by_xpath(
            f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/div[1]/div/a[{idx + 1}]')

        print(f'current target category : {target_category.text}')
        time.sleep(2)
        webdriver.ActionChains(self.driver).move_to_element(target_category).click(target_category).perform()

        return target_category

    def scroll_down(self, count=5):
        """
        selected category scroll down (5)
        count : int
            scroll down count
        """
        while count:
            self.driver.execute_script('window.scrollTo(0, 10000);')
            time.sleep(2)
            try:  # scroll more button not exist
                self.driver.find_element_by_xpath(
                    '//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[2]/a').click()
            except:
                break
            count -= 1

        time.sleep(1)
        try:  # user review li element
            elements = self.driver.find_elements_by_xpath(
                '//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li')
        except:
            print('No Element')
        else:
            return elements

    def get_reviews(self, title, target_category, idx=0):
        """
        selected category review scraping (6)
        title : str
            camping title
        target_category : str
            selected category
        idx : int
            highlight review span tag index
        """
        try:
            span = self.driver.find_element_by_xpath(
                f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div[1]/div[5]/a')
        except:
            try:
                span = self.driver.find_element_by_xpath(
                    f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div[1]/div[4]/a')
            except:
                try:
                    span = self.driver.find_element_by_xpath(
                        f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div/div[4]/a')
                except:
                    try:
                        span = self.driver.find_element_by_xpath(
                            f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div/div[5]/a')
                    except:
                        print('No Highlight review div')

        try:
            info = {}
            highlight = span.find_element_by_class_name('highlight').text
            info['category'] = target_category.text
            info['title'] = title
            info['highlight_review'] = highlight

            # date, visit count, reservation info
            try:
                info['visit_info'] = self.driver.find_element_by_xpath(f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div/div[2]/div[2]').text
            except:
                info['visit_info'] = self.driver.find_element_by_xpath(f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div/div[3]/div[2]').text

            # user review count / picture num / mean star info
            try:
                info['user_info'] = self.driver.find_element_by_xpath(f'//*[@id="app-root"]/div/div[2]/div[5]/div[4]/div[4]/div[1]/ul/li[{idx + 1}]/div/div[1]/a/div/div[2]').text
            except:
                pass
        except:
            print('NoSuchElement Error')
        return info

    def save_res(self, reviews):
        naverv5_df = pd.DataFrame()

        for review in reviews:
            naverv5_df = naverv5_df.append(review, ignore_index=True)

        naverv5_df.to_csv(config.Config.PATH + '/v5_category.csv', encoding="utf-8-sig", header=True)