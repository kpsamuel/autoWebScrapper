# -*- coding: utf-8 -*-
"""
Created on Sat Aug  7 11:28:22 2021

@author: samuel
"""
import json
from pymongo import MongoClient



## ====================== loading the system configurations ============================= ##

with open("config.json", "r") as fp:
    configData = json.load(fp)
    

class databaseConnect():
    
    def __init__(self):
        """
            this function will make the client connect to database and flag the signal for successful connection
            else flags for error during connection

        Returns
        -------
        None.

        """
        
        try:
            print("[ * ] connecting to database.", end=" | status = ")
            client = MongoClient(host = configData["dbhost"],
                         port = configData["dbport"])
            self.database = client[configData["dbname"]]
            self.connection_status = 0
            print("success")
        except Exception as err_msg:
            print("failed")
            self.connection_status = -1
            print("[ ! ] database connection failed. error message :"+str(err_msg))
            
    def insertData(self, querydata):
        """
            this function will be used to insert data into database.

        Parameters
        ----------
        querydata : dict
            parameter should hold key as per
            querydata = {
                        "collection_name" : <name of the collection in which data need to insert>,
                        "data" : data to be inserted. type can be only "dict" or "list", other datatypes will not be inserted, if any error check mongodb documentataion we per error code.
                }

        Returns
        -------
        operation_status : int
            the status of insert operation
            1 = none
            0 = success
           -1 = error

        """
        try:
            operation_status = 1
            error_message = ""
            ## checking for database connection is success
            
            if self.connection_status == 0:
                dbcollection = self.database[querydata["collection_name"]]
                
                if isinstance(querydata["data"], dict):
                    dbcollection.insert_one(querydata["data"])
                
                if isinstance(querydata["data"], list):
                    dbcollection.insert_many(querydata["data"])
                operation_status = 0
        except Exception as err_msg:
            print("[ ! ] failed to perform insert operation. error message : "+str(err_msg))
            operation_status = -1
            error_message = err_msg
        
        return operation_status, error_message
            
    
    def selectData(self, querydata):
        """
            this function is used to make select operation to mongoDB.

        Parameters
        ----------
        querydata : dict
            select query data as per key.
            querydata = {
                        "collection_name" :  <name of the collection from which data need to be selected>,
                        "select_query" : {<key_name> : <value>}
                }

        Returns
        -------
        data : list
            data retrived from the selected collection.
            NOTE : default "data" is empty list, in case of failuer also empty list is returned, 
                   so request to check the "operation_status" also.
            
        operation_status : int
            the status of select operation
            1 = none
            0 = success
           -1 = error

        """
        try:
            operation_status = 1
            data = []
            
            ## checking for database connection is success
            if self.connection_status == 0:
                dbcollection = self.database[querydata["collection_name"]]
                data = [log for log in dbcollection.find(querydata["select_query"], {"_id":False})]
                operation_status = 0
        except Exception as err_msg:
            print("[ ! ] failed to perform select operation. error message : "+str(err_msg))
            operation_status = -1
        
        return data, operation_status        
    
    
    def getLatestData(self, querydata):
        """
            this function will get the latest record from the collection, based on the "select_query"

        Parameters
        ----------
        querydata : dict
            DESCRIPTION.
            querydata = {"collection_name" : <name of the collection from which data need to be selected>,
                         "select_query" : {<key_name> : <value>}}

        Returns
        -------
        data : dict
            DESCRIPTION.
            will return single record based on the "select_query"
            
        operation_status : int
            the status of select operation
            1 = none
            0 = success
           -1 = error
        """

        try:
            operation_status = 1
            data = {}
            
            ## checking for database connection is success
            if self.connection_status == 0:
                dbcollection = self.database[querydata["collection_name"]]
                data = [log for log in dbcollection.find(querydata["select_query"]).sort("_id", 1)]
                if len(data)>1:
                    data = data[0]
                    operation_status = 0
        except Exception as err_msg:
            print("[ ! ] failed to perform select operation. error message : "+str(err_msg))
            operation_status = -1
        
        return data, operation_status 
    
    
    def updateData(self, querydata):
        operation_status = 1  #default status to be failed. 0 for success
        try:
            if self.connection_status == 0:
                dbcollection = self.database[querydata["collection_name"]]
            
                dbcollection.remove(querydata["select_query"])
                
                
                if isinstance(querydata["updateData"], dict):
                    dbcollection.insert_one(querydata["updateData"])
                if isinstance(querydata["updateData"], list):
                    dbcollection.insert_many(querydata["updateData"])
                operation_status = 0
        except Exception as err_msg:
            print("[ ! ] failed to perform update operation. error message : "+str(err_msg))
            
        return operation_status
    