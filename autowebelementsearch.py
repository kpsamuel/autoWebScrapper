# -*- coding: utf-8 -*-
"""
Created on Sun Aug  8 15:12:05 2021

@author: samuel
"""
import re 
import json
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import difflib
from pprint import pprint
import time
import os
import shutil
import pandas as pd

## importing custom files / modules
import errorhandling
import database

dbc = database.databaseConnect()

## ================ helper functions ======================= ##
def loadwebsite(url):
    """
        this function loads the website of given url.
        make sure network is connected.

    Parameters
    ----------
    url : str
        website url to be loaded.
        
    Returns
    -------
    webdata : BeautifulSoup Object
        returns the BeautifulSoup object if the website response is 200.
        or else it will return empty string and print the error message when request is made.

    """
    webdata = ""
    response = requests.get(url)
    if response.status_code == 200:
        webdata = BeautifulSoup(response.text, "html.parser")
    else:
        print("[ ! ] failed to request the web : {} reponse code : {}".format(url, response.status_code))
    return webdata
    
def cleantext(sentence):
    """
        this function will cleanup the input sentences.
        cleaning process includes removing all the special characters.

    Parameters
    ----------
    sentence : str
        input sentence to be cleaned from special chars

    Returns
    -------
    str
        return sentences after removing all the special chars

    """
    
    return re.sub('[^A-Za-z0-9]+', ' ', sentence).strip()
    
## ================ operational classes ==================== ##
    
class webmining():
    
    def __init__(self, webtemplate_filepath, scrapping_information, mining_mode = "online", account_path="."):
        
        """
            webminig will find the most relevate tag and attributes to get the requied data.
            webmining supports 'online' and 'offline' way of searching the tags and attributes
            webmining once completed, it will save the 'mapper.json' file in the folder created by the name of 'template_name'
            'mapper.json' is used for webdata scrapping
        """

        self.webtemplate_filepath = webtemplate_filepath
        self.mining_mode = mining_mode
        self.account_path = account_path
        self.scrapping_information = scrapping_information
        
        
    def startmining(self):
        """
            this function will start the minig process
            steps of mining are:
                    a. load the template
                    b. select the mining mode (offline / online)
                    c. if offline mode - download the webpages listed in 'urls_to_scrap'
                    d. scan and get all the unique tags of webpages
                    e. loop through all the tags and scrap the webpage and match the text from template.
                    f. saving most matched all the tags and attributes in 'web_mapper' key and save the final results into 'mapper.json'
                    
                    NOTE : scrapped data matches with the text in mapper and get the score, score used in sequence matcher
        Returns
        -------
        None.

        """
        try:
            self.webtemplate_filepath = os.path.join(self.webtemplate_filepath, os.listdir(self.webtemplate_filepath)[0])
            
            print("[ * ] starting webmining for template : ", self.webtemplate_filepath)
            print("[ ! ] web mining mode : ", self.mining_mode)
            self.webtemplate = self.loadWebTemplate()
            
            if self.mining_mode == "offline":
                self.downloadwebpages()
                with open(self.offline_webpage_filepath, "rb") as fip:
                    self.webdata = BeautifulSoup(fip.read())
            else:
                self.webdata = loadwebsite(url = self.webtemplate["website"])
            
            self.webtags = set([tag.name for tag in self.webdata.find_all()])
            tag_list = ["div", "a", "h1", "h2", "h3", "h4", "ul", "li", "p"]
            print("[ * ] website tag elements count : ", len(self.webtags), "\n")
            time.sleep(3)
            
            self.web_element_mapped = []
            for info_ext in self.webtemplate["data"]:
                
                ## minig for text type data
                if info_ext["type"] == "text":
                    for data_key, data_sample in info_ext["information"].items():
                        final_tag_dimension = {}
                        text_match_score = 0.0
                        print("--------------------------------------------------------")
                        for tag_name in self.webtags:
                            time.sleep(2)
                            tag_dimension_score = self.searchElementMap(information_type="text", 
                                                                         tag_name = tag_name, 
                                                                         search_sample=data_sample,
                                                                         data_key = data_key)
                            
                            if tag_dimension_score["score"] > text_match_score:
                                final_tag_dimension = {
                                    "data_key" : data_key,
                                    "tag_name" : tag_name,
                                    "tag_dimension" : tag_dimension_score["dimension_map"],
                                    "match_score" : tag_dimension_score["score"]
                                    }
                                
                            if (tag_dimension_score["score"] == 1.0):
                                break
                        self.web_element_mapped.append(final_tag_dimension)
            ## saving the mined webmapper
            self.savemapper()
        except:
            errorhandling.catchError(custom_message="webminner failed for request_id : "+self.scrapping_information["request_id"])
            
                
    def loadWebTemplate(self):
        """
            a. load the template

        Returns
        -------
        webtemplate : dict
            webtemplate whose data to be minied

        """
        print("[ * ] loading webtemplate. status = ", end="")
        try:
            with open(self.webtemplate_filepath, "r") as fp:
                webtemplate = json.load(fp)
            
            print("success")
            return webtemplate
        except Exception as err_msg:
            print("failed. error message : "+str(err_msg))
            errorhandling.catchError(custom_message="failed to load webtemplate. request_id : "+self.scrapping_information["request_id"])
    
    def downloadwebpages(self):
        """
            c. if offline mode - download the webpages listed in 'urls_to_scrap'
            
                the downloaded web pages will be saved in 'temp' folder
                
        Returns
        -------
        None.

        """
        try:
            print("[ * ] downloading website.", end=" status = ")
                
            
            download_filepath = os.path.join(self.account_path, "temp")
            if "temp" not in os.listdir(self.account_path):
                os.makedirs(download_filepath)
            
            webdata = loadwebsite(url = self.webtemplate["website"])
            filename = webdata.title.text.replace(" ","_") + ".html"
            self.offline_webpage_filepath = os.path.join(download_filepath, filename)
            
            html = webdata.prettify("utf-8")
            with open(self.offline_webpage_filepath, "wb") as file:
                file.write(html)
            
            print("success")
            
        except Exception as err_msg:
            print("failed. error message : "+str(err_msg))
            errorhandling.catchError(custom_message="failed to download webpage. request_id : "+self.scrapping_information["request_id"])
            
    
    def mineWebElements(self, tag_name):
        """
            d. scan and get all the unique tags of webpages

            this function will get all the attributes fiven 'tag_name'

        Parameters
        ----------
        tag_name : str
            tag name whose all the attributes need to be scanned

        Returns
        -------
        webelement_map : dict
            mapped tag and its attributes list

        """
        try:
            webelement_map = {tag_name : []}
            
            for webobj in  self.webdata.find_all(tag_name):
                emap = {}
                for attr_name, attr_value in webobj.attrs.items():
                    if isinstance(attr_value, list):
                        attr_value = " ".join(attr_value)
                    emap[attr_name] = attr_value
                webelement_map[tag_name].append(emap)
            return webelement_map
        except:
            errorhandling.catchError(custom_message="failed to process mining web elements. request_id : "+self.scrapping_information["request_id"])
            return {tag_name : []}
        
    
    def searchElementMap(self, information_type, tag_name, search_sample, data_key):
        """
            e. loop through all the tags and scrap the webpage and match the text from template.
            
            this function will map the best fit tag with attribute for searching "search_sample"
            best fit match is found from sequence matcher with extracted_text and "search_sample"

        Parameters
        ----------
        information_type : str
            type of web information to be extracted i.e. text, url, image, video
            
        tag_name : str
            one of the tag name which is already minied from loaded webpage
            
        search_sample : str
            sample of text, urls to be searched these data is loaded from template    
        
        data_key : str
            key name of the 'search_sample' to be mapped
 
        Returns
        -------
        tag_dimension : dict
            the best fit map of tag, attribute for given 'search_sample'
            this will also have the score computed from sequence matcher

        """
        try:
            break_flag = -1
            match_score = 0.0
            tag_dimension = {"dimension_map" : {},
                             "score" : match_score}
            
            if information_type == "text":
                finding_text = cleantext(search_sample)
                object_dimension = self.mineWebElements(tag_name = tag_name)
                
                for dimension_map in tqdm(object_dimension[tag_name], desc="mining for data : {} with tag : {}".format(data_key, tag_name)):
                    for tag in self.webdata.find_all(tag_name, dimension_map):
                        extracted_text = cleantext(tag.text)
                        score = difflib.SequenceMatcher(None, finding_text, extracted_text).ratio()
            
                        if score > match_score:
                            tag_dimension = {"dimension_map" : dimension_map,
                                             "score" : score}
                            match_score = score
                            
                        if finding_text == extracted_text:
                            break_flag = 0
                            break
                    if break_flag == 0:
                        break
            return tag_dimension        
        except:
            errorhandling.catchError(custom_message="failed to search element maps. request_id : "+self.scrapping_information["request_id"])
            
            
    def savemapper(self):
        """
            f. saving most matched all the tags and attributes in 'web_mapper' key and save the final results into 'mapper.json'
                    
            this function will save all the tag and attribute mapped to given information to be extracted.
            'mapper.json' is saved in folder name 'template_name' from template
            
        Returns
        -------
        None.

        """
        time.sleep(2)
        try:        
            print("[ * ] saving the webmapper.", end=" status = ")
                
            self.webtemplate.update({"web_mapper" : self.web_element_mapped})
            
            output_filepath = os.path.join(self.account_path, "mapper.json")
            with open(output_filepath, "w") as fop:
                json.dump(self.webtemplate, fop)
                
            print("sucess")
            print("\t\t > mapper location : ", output_filepath)
            
            req_mapper = self.webtemplate
            req_mapper.update(self.scrapping_information)
            query = {"collection_name" : "scrappingInformation",
                     "data" : req_mapper}
            dbc.insertData(querydata = query)
            
        except Exception as err_msg:
            print("failed. error message :"+str(err_msg))    
            errorhandling.catchError(custom_message="failed to save the mapper. request_id : "+self.scrapping_information["request_id"])

class webscrapper():
    
    def __init__(self, web_mapper_filepath, scrapping_information, scrapping_mode = "online", account_path = "."):
        print("[ * ] starting webscrapping for template : ", web_mapper_filepath)
        print("[ ! ] web scrapping mode : ", scrapping_mode)
        
        
        """
            webscrapper will load the 'mapper.json' created by the webminig operation.
            webscrapper have offline and online mode of scrapping.
            'offline' mode, will download all the webpage which are in the key 'urls_to_scrap' in 'mapper.json' file
            downloaded webpages is saved in 'temp' folder
            'online' mode, will directly starts scrapping using 'web_mapper' key, which holds tag and attributes information.
            and later all the scrapped data is save in 'data' folder.
            
        """
        self.web_mapper_filepath = web_mapper_filepath
        self.scrapping_mode = scrapping_mode
        self.account_path = account_path
        self.scrapping_information = scrapping_information
        self.loadWebMapper()
        
        
    def loadWebMapper(self):
        """
            a. load the 'mapper.json' which is generated from mining process.
                
            this function will load 'mapper.json' template which have all the tag and attributes to be used for scarpping

        Returns
        -------
        None.

        """
        print("[ * ] loading webmapper. status = ", end="")
        self.webmapper = ""
        try:
            with open(self.web_mapper_filepath, "r") as fp:
                self.webmapper = json.load(fp)
                #webmapper = webmapper["web_mapper"]
                
            print("success")
            
        except Exception as err_msg:
            print("failed. error message : "+str(err_msg))
            errorhandling.catchError(custom_message="failed to load webmapper. request_id : "+self.scrapping_information["request_id"])
            
    def downloadwebpages(self):
        """
            c. if offline mode, than download all the webpages from key 'urls_to_scrap' into 'temp' folder
                
            this function will download all the webpages and saves in "temp" folder

        Returns
        -------
        None.

        """
        try:
            self.downloadpages_metadata = []
            
            self.download_filepath = os.path.join(self.account_path, "temp")
            if "temp" not in os.listdir(self.account_path):
                os.makedirs(self.download_filepath)
            else:
                shutil.rmtree(self.download_filepath)
                os.makedirs(self.download_filepath)
                
            page_count = 1
            for website_url in tqdm(self.webmapper["urls_to_scrap"], desc="downloading websites"):
                webdata = loadwebsite(url = website_url)
                filename = webdata.title.text.replace(" ","_") + "_page_{}.html".format(page_count)
                self.offline_webpage_filepath = os.path.join(self.download_filepath, filename)
                
                html = webdata.prettify("utf-8")
                with open(self.offline_webpage_filepath, "wb") as file:
                    file.write(html)
                self.downloadpages_metadata.append({
                    "page_name" : filename, "page_url" : website_url})
                
                page_count += 1    
                
        except Exception as err_msg:
            print("failed. error message : {} for url {}".format(err_msg, website_url))
            errorhandling.catchError(custom_message="failed to download webpage {} for request_id : {}".format(website_url, self.scrapping_information["request_id"]))
            
            
    def startscrapping(self):
        """
            this function will start the scrapping process.
            steps of scrapping are:
                a. load the 'mapper.json' which is generated from mining process.
                b. check for (offline / online) scrapping mode.
                c. if offline mode, than download all the webpages from key 'urls_to_scrap' into 'temp' folder
                d. loop throught all the downloaded webpages and start scrapping using the 'web_mapper' key from 'mapper.json'
                e. collect all the information and reformat data
                f. save the collected data
                
        Returns
        -------
        None.

        """
        try:
            self.all_page_processed_data = {}    
            print("[ * ] scrapping started. mode : ", self.scrapping_mode)
            time.sleep(2)
            
            if self.scrapping_mode == "offline":
                self.downloadwebpages()
                
                for saved_webpage_info in tqdm(self.downloadpages_metadata, desc="scrapping downloaded webpages"):
                    time.sleep(2)
                    
                    with open(os.path.join(self.download_filepath, saved_webpage_info["page_name"]), "rb") as fip:
                        self.webdata = BeautifulSoup(fip.read())
                    
                    webpage_data = self.processwebpages()
                    self.all_page_processed_data[saved_webpage_info["page_url"]] = {"page_name" : saved_webpage_info["page_name"], 
                                                                           "data" : webpage_data}
    
            elif self.scrapping_mode == "online":
                page_count = 1
                for webpage_url in self.webmapper["urls_to_scrap"]:
                    self.webdata = loadwebsite(webpage_url)
                    page_name = self.webdata.title.text.replace(" ","_") + "_page_{}.html".format(page_count)
                    webpage_data = self.processwebpages()
                    self.all_page_processed_data[webpage_url] = {"page_name" : page_name,
                                                                 "data" : webpage_data}
    
                    page_count += 1
            
            self.reformat()
            self.savescrapperdata()
        except:
            errorhandling.catchError(custom_message="failed to process the scrapping request. request_id : "+self.scrapping_information["request_id"])
            
            
    def processwebpages(self):
        """
            e. collect all the information and reformat data
                
            this function will scrap the data based on tag and attribute mapped

        Returns
        -------
        webpage_data : TYPE
            DESCRIPTION.

        """
        try:
            webpage_data = {}
            for search_element in self.webmapper["web_mapper"]:
                searched_element_data = [cleantext(taglog.text) for taglog in self.webdata.find_all(search_element["tag_name"], search_element["tag_dimension"])]
                webpage_data[search_element["data_key"]] = searched_element_data
            return webpage_data
        except:
            errorhandling.catchError(custom_message = "failed to process webpages. request_id" + self.scrapping_information["request_id"])
            return {}
        
            
    def reformat(self):
        """
            e. collect all the information and reformat data
            
            this function will reformat data, which means it will pair each data_key into list of dict
            
            NOTE : 'non-reformatted' data is missing the 'data_key' values miss-matched and 
                    in which its missed is stored in variable 'class_obejct.skipped_webpages'
        Returns
        -------
        None.

        """
        try:
            self.all_page_reformated_data = []
            self.skipped_webpages = {}
            self.reformat_success_flag = -1
            
            for page_key in tqdm(self.all_page_processed_data.keys(), desc="reformatting page data"):
                datapoints = self.all_page_processed_data[page_key]["data"].keys()
                data_counts = {data_key : len(self.all_page_processed_data[page_key]["data"][data_key]) for data_key in datapoints}
                match_count = list(set(data_counts.values()))
                
                if len(match_count) == 1:
                    data = pd.DataFrame(self.all_page_processed_data[page_key]["data"])
                    data = data.to_dict(orient="records")
                    self.all_page_reformated_data.append(data)
                    self.reformat_success_flag = 0
                else:
                    self.skipped_webpages.update({"page_key" : page_key,
                                                 "data_count" : data_counts})
                    self.reformat_success_flag = -1
                    
                    
            if len(self.skipped_webpages) > 1:
                print("[ ! ] reformating skilled pages due to page data in-consistency")
                pprint(self.skipped_webpages)        
        except:
            errorhandling.catchError(custom_message="failed to reformat data request_id : "+self.scrapping_information["request_id"])
            
    def savescrapperdata(self):
        """
            f. save the collected data
                
            this function will save the scrapped data into json format.
            save mode is of 2 types 'reformatted' and 'non-reformatted'

        Returns
        -------
        None.

        """
        time.sleep(2)
        try:
            output_folderpath = os.path.join(self.account_path, "data")
            if "data" not in os.listdir(self.account_path):
                os.mkdir(output_folderpath)
            
            output_filepath = os.path.join(output_folderpath, self.webmapper["template_name"]+".json")
            
            if self.reformat_success_flag == 0:
                print("[ * ] saving reformatted data", end=" status = ")
                data_to_save = self.all_page_reformated_data
            else:
                print("[ * ] saving non-reformatted data", end=" status = ")
                data_to_save = self.all_page_processed_data
            
            with open(output_filepath, "w") as fop:
                json.dump(data_to_save, fop)
            
            if len(data_to_save) == 1:
                data_to_save = data_to_save[0]
            
            for data_record in data_to_save:
                data_record.update({"account_id" : self.scrapping_information["account_id"],
                                    "request_id" : self.scrapping_information["request_id"]})
                
            query = {"collection_name" : "scrappedData",
                     "data" : data_to_save}
            dbc.insertData(querydata = query)
            
            print("success")
            print("\t > ", output_filepath)
            
        except:
            msg = "failed to save scrapped data. request_id : "+self.scrapping_information["request_id"]
            errorhandling.catchError(custom_message=msg)
            
            

## ===================== code execution example =============================== ##
## website mining process
# start_time = time.time()
# wm = webmining(webtemplate_filepath="google_cloud_press_release.json", mining_mode="online")
# wm.startmining()

## website scrapping process
# ws = webscrapper(web_mapper_filepath="google_cloud_press_release/mapper.json", scrapping_mode="online")
# ws.startscrapping()
# end_time = time.time()
# print("[ # ] process took time : ", end_time - start_time)