# -*- coding: utf-8 -*-
"""
Created on Tue Aug 31 14:27:44 2021

@author: samuel
"""
import time
import json
import os


## importing custom file / modules
import database
import autowebelementsearch
import errorhandling

dbc = database.databaseConnect()

with open("config.json", "r") as file:
    configData = json.load(file)

def startScrapping(scrapping_information):
    print("[ # ] scrapping information : ", scrapping_information)
    account_path = os.path.join(configData["templates"], scrapping_information["account_id"])
    template_filepath = os.path.join(account_path,"template")
    
    ## website mining process
    start_time = time.time()
    wm = autowebelementsearch.webmining(webtemplate_filepath = template_filepath, 
                                        mining_mode = "online",
                                        account_path = account_path,
                                        scrapping_information = scrapping_information)
    wm.startmining()
    
    ## website scrapping process
    mapper_filepath = os.path.join(account_path, "mapper.json")
    ws = autowebelementsearch.webscrapper(web_mapper_filepath = mapper_filepath, 
                                          scrapping_mode = "online",
                                          account_path = account_path,
                                          scrapping_information = scrapping_information)
    ws.startscrapping()
    end_time = time.time()
    took_time = end_time - start_time
    
    scrapping_information["status"] = "completed"
    scrapping_information["processing_time"] = took_time
    query = {"collection_name":"scrappingRequests",
             "select_query" : {"request_id" : scrapping_information["request_id"]},
              "updateData" : scrapping_information}
    op_flag = dbc.updateData(querydata = query)
    if op_flag == 1:
        errorhandling.warningLog(custom_message="failed to update the operation status. request_id : " + scrapping_information["request_id"])


def startWatcher():
    
    query = {"collection_name":"scrappingRequests", 
             "select_query":{"status":"in-progress"}}
    
    new_scrap_requests, flag = dbc.selectData(query)
    for request_info in new_scrap_requests:
        startScrapping(request_info)
        
        
## ==================== starting job monitoring service ==================== ##
if __name__ == "__main__":
    startWatcher()