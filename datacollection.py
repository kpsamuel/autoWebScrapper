# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 18:03:25 2021

@author: samuel
"""
import time
import json
import requests
from bs4 import BeautifulSoup
import pprint
from tqdm import tqdm
from selenium import webdriver

## import custom modules
import errorhandling
import database
dbc = database.databaseConnect()


## ====================== loading the system configurations ============================= ##
try:
    print("[ * ] loading the tool settings.", end=" | status = ")
    with open("config.json", "r") as fp:
        configData = json.load(fp)
    print("success")
    errorhandling.logInfo("loading tool settings.")
except:
    print("failed")
    errorhandling.catchError(custom_message = "loading in config.json file")    
    
## ===================== general helper functions ============================ ##
def getwebdata(url):
    """
    Parameters
    ----------
    url : str
        a website link to be loaded and used for scrapping

    Returns
    -------
    webdata : BeautifulSoup object
        website content parser in BeautifulSoup

    """
    try:
        webdata = ""
        response = requests.get(url)
        if response.status_code == 200:
            webdata = BeautifulSoup(response.text, "html.parser")
        else:
            print("connection to {} failed with response code : ", response.status_code)
    except:
        errorhandling.catchError(custom_message="webpage loading error for url "+str(url))
    return webdata

# ======================== special class for different types of data sources ======================= ##

class fintechFutures():
    """
        this class will scrape the data from the website : https://www.fintechfutures.com/
        this data going to be used for model building and evalution
        this scrapper will be update-mode, which means it will scrape the updating pages data only by comparing to its database
       
        NOTE : class name is similar to the website domain its scrapping
    """    
    
    def __init__(self):
        print("[ # ] starting fintechFutures")
        errorhandling.logInfo(custom_message="starting fintechFutures")
        self.homeurl = "https://www.fintechfutures.com/"
        self.loadSubTopicsURL()
        
        
    def loadSubTopicsURL(self):
        """
            this funtion will load all the subtopics of the website along with the urls.
            example : FinTech, BankingTech, PayTech, RegTech, WealthTech, LendTech, InsureTech
        Returns
        -------
        None.

        """     
        try:
            print("[ * ] loading subtopics of webpage.", end=" status = ")
            webdata = getwebdata(self.homeurl)
            self.data_source_type = {menu.text : menu.find("a").get("href") for menu in webdata.find("ul", {"id":"menu-secondary"}).find_all("li")}
            print("success")
            print("---------------------------------------------------------")
            pprint.pprint(self.data_source_type)
            print("---------------------------------------------------------")
            
        except:
            print("failed")
            errorhandling.catchError(custom_message="loading subtopics")
    
    def pageMetaData(self, subtopics_name):
        """
            this function will load all the metadata of each subtopic of the page.
            this data will be used later to scrape the complete page content
            once data collection prrocess is completed, data of each article will be stored in database.
            
            data collected are : title, article_url, article_excerpt, acrticle_post_date
            
        Parameters
        ----------
        subtopics_name : str
            subtopics of homepage will be loaded and can be used one of them to collect the information of each article

        Returns
        -------
        None.

        """
        print("[ * ] subtopic : ", subtopics_name)
        page_url = self.data_source_type[subtopics_name]
        
        ## getting already present data information
        update_found_flag = -1
        query = {"collection_name" : "fintechFuturesMetadata", 
                 "select_query" : {"subtopics" : subtopics_name}}
        latest_data, op_flag = dbc.getLatestData(querydata=query)
        if op_flag == 0:
            print("[ % ] found existing subtopic data. looking for update initialized")
            pprint.pprint(latest_data)
            
        ## loading all the article pages 
        article_urls = []
        while True:
            page_articles = []
            try:
                print("connecting page : ", page_url, end=" status : ")
                fintech_webdata = getwebdata(page_url)
                time.sleep(3)
                for article in fintech_webdata.find_all("div", {"class":"search-content left"}):
                    article_info = {}
                    article_info["subtopics"] = subtopics_name
                    article_info["title"] = article.find("a").text.strip()
                    article_info["article_url"] = article.find("a").get("href")
                    article_info["article_excerpt"] = article.find("p").text.strip()
                    article_info["article_post_date"] = article.find("li").text.strip()
                    article_info["system_datetime"] = str(time.time())
                    
                    if (op_flag == 0):
                        if (article_info["article_url"] == latest_data["article_url"]):
                            update_found_flag = 0
                            break
                    else:
                        page_articles.append(article_info)
                        article_urls.append(article_info["article_url"])
                
                ## inserting data into db
                query = {"collection_name" : "fintechFuturesMetadata", "data" : page_articles}
                dbc.insertData(querydata=query)
                print("success")
                
                if update_found_flag == 0:
                    print("[ !! ] updated new articles. terminating process")
                    errorhandling.logInfo(custom_message="found already existing articles. terminating process")
                    break
                
                ## getting next page url, if None means no next page is present and hence terminate                
                page_url = fintech_webdata.find("a", {"class":"next page-numbers"}).get("href")
                if page_url == None:
                    print("[ * ] completed the all page loading")
                    errorhandling.logInfo(custom_message="completed the all page loading")
                    break
            except:
                errorhandling.catchError(custom_message="failed for the file : "+page_url)
                break
        
        ## calling content of each article reading
        self.pageContent(articles_urls=article_urls)
        
        
        
    def pageContent(self, articles_urls):
        """
            this funtion will scrape all the article content and insert in database.
            
            data collected are : written_by, article_content, taginfo, related_articles
            
        Parameters
        ----------
        articles_urls : list
            list of article urls which contents to be extracted

        Returns
        -------
        None.

        """
        try:
            for article_url in tqdm(articles_urls, desc="reading article contents"):
                article_data = {}
                article_webdata = getwebdata(article_url)
                time.sleep(3)
                
                article_data["article_url"] = article_url
                try:
                    article_data["written_by"] = article_webdata.find("li", {"class":"profile"}).text.strip()
                except:
                    article_data["written_by"] = "None"
                    errorhandling.warningLog(custom_message="'written_by' data missing for page :"+article_url)
                try:
                    article_data["article_content"] = " ".join([paragraph.text for paragraph in article_webdata.find("div", {"class":"columns small-12 single-post-content_text-container"}).find_all("p")])
                except:
                    article_data["article_content"] ="None"
                    errorhandling.warningLog(custom_message="'article_content' data missing for page :"+article_url)
                try:
                    tag_element = article_webdata.find("div", {"class":"columns small-12 tag FinTech"})
                    if tag_element == None:
                        tag_element = article_webdata.find("div", {"class":"columns small-12 tag reset"})
                    
                    article_data["taginfo"] = [{"tag":tag.text, "tagurl":tag.get("href")}  for tag in tag_element.find_all("a")]
                except:
                    article_data["taginfo"] = "None"
                    errorhandling.warningLog(custom_message="'taginfo' data missing for page :"+article_url)
                try:
                    article_data["related_articles"] = [{"article_title" : related_article.text.strip("\n").strip(), "article_url":related_article.find("a").get("href")} for related_article in article_webdata.find_all("li",{"class":"post-related-list"})]
                except:
                    article_data["related_articles"] = "None"
                    errorhandling.warningLog(custom_message="'related_articles' data missing for page :"+article_url)
            
                ## inserting data into db
                query = {"collection_name" : "fintechFuturesArticle", "data" : article_data}
                dbc.insertData(querydata=query)
                
        except:
            errorhandling.catchError(custom_message="page content error "+article_url)
            
class yourstory():
    
    def __init__(self, sector):
        self.page_number = 1
        self.sector = sector
        self.homeurl = "https://yourstory.com/companies/search?page={}&sector={}".format(self.page_number, self.sector)
        self.chrome = webdriver.Chrome(executable_path="chromedriver.exe")

    
    def getCompanyInformation(self):
        self.chrome.get(self.homeurl)
        self.company_information = []
        page_url = self.homeurl
        
        while True:
            print(page_url)
            time.sleep(2)
            self.chrome.get(page_url)
            time.sleep(3)
            try:
                company_rawdata = [tag.text.split("\n") for tag in self.chrome.find_elements_by_css_selector("tr.hit")]
                if len(company_rawdata) == 0:
                    break
                
                for info in company_rawdata:
                    try:
                        company_name = info[0]
                    except:
                        company_name = "None"
                    try:
                        company_type = info[1]
                    except:
                        company_type = "None"
                    try:
                        company_location = info[2]
                    except:
                        company_location = "None"
                    
                    self.company_information.append({"company_name" : company_name,
                                                     "company_type" : company_type,
                                                     "company_location" : company_location,
                                                     "sector" : self.sector})
                    
                page_url = "https://yourstory.com/companies/search?page={}&sector={}".format(self.page_number, self.sector)
                self.page_number += 1
            except Exception as err_msg:
                print("error : ", err_msg)
                break
        print("[ * ] completed task")
        self.chrome.quit()
        
        ## insert data into database
        query = {"collection_name" : "yourstory", "data" : self.company_information}
        dbc.insertData(query)
## ====================== code testing ========================= ##
"""
# use this for yourstory

ys = yourstory(sector="Financial Services")
ys.getCompanyInformation()
"""


#    for fintechFutures
#    this function will be called if pageContent needs to be update seperatly
    
ff = fintechFutures()
ff.pageMetaData(subtopics_name="BankingTech")
"""
query = {"collection_name" : "fintechFuturesMetadata", 
         "select_query" : {"subtopics" : "BankTech"}}
data, _ = dbc.selectData(querydata = query)
article_urls = [articleinfo["article_url"] for articleinfo in data]
ff.pageContent(articles_urls = article_urls)
"""