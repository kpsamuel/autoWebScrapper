# -*- coding: utf-8 -*-
"""
Created on Mon Sep  6 11:04:15 2021

@author: samuel
"""
import json
import database
import pandas as pd

dbc = database.databaseConnect()

query = {"collection_name" : "fintechFuturesMetadata",
         "select_query" : {}}

metadata, flag = dbc.selectData(query)
metadata = pd.DataFrame(metadata)


query = {"collection_name" : "fintechFuturesArticle",
         "select_query" : {}}

articledata, flag = dbc.selectData(query)


final_data = articledata
for idx in range(len(final_data)):
    match_metadata = metadata[metadata["article_url"] == final_data[idx]["article_url"]].to_dict(orient="records")[0]
    final_data[idx]["subtopics"] = match_metadata["subtopics"]
    final_data[idx]["title"] = match_metadata["title"]
    final_data[idx]["article_excerpt"] = match_metadata["article_excerpt"]
    final_data[idx]["article_post_date"] = match_metadata["article_post_date"]
    
    
with open("fintech_scrapped_data.json", "w") as fp:
    json.dump(final_data, fp)