# -*- coding: utf-8 -*-
"""
Created on Tue Aug 31 11:48:16 2021

@author: samuel
"""
import datetime
import uuid
import json
import os
from flask import Flask, jsonify, request, make_response
from flask_restful import Resource, Api
from werkzeug.utils import secure_filename


## importing custom files / modules
import database
import errorhandling

## setting up and loading tool configuration
app = Flask(__name__)
api = Api(app)
dbc = database.databaseConnect()


with open("config.json", "r") as file:
    configData = json.load(file)
    
## doing local setups

if configData["templates"] not in os.listdir():
    os.mkdir(configData["templates"])
    
class appStatus(Resource):
    """
        api to checkt the status of tool
    """    
    def get(self):
        return make_response(jsonify({"status":200, "message":"server is up and running"}))

class registerAccount(Resource):
    
    def post(self):
        try:
            request_datetime = str(datetime.datetime.now())        
            project_name = request.form.get("project_name")
            account_id = str(uuid.uuid1())
            
            web_template = request.files["web_template"]
            template_filename = secure_filename(web_template.filename)
            accound_folder_path = os.path.join(os.path.join(configData["templates"], account_id), "template")
            os.makedirs(accound_folder_path)
            filepath = os.path.join(accound_folder_path, template_filename)
            web_template.save(filepath)
            
            requestdata = {
                "project_name" : project_name,
                "datetime" : request_datetime,
                "account_id" : account_id
                }
            
            query = {"collection_name":"registeredaccounts",
                     "data" : requestdata}
            op_flag, msg = dbc.insertData(querydata=query)
            
            if op_flag == 0:
                status = 201
                message = "account {} registered successfully. your accound_id : {}".format(project_name, account_id)
            else:
                status = 501
                message = "account {} registration failed. error message : {}".format(project_name, msg)
                os.remove(filepath)  ## deleting the saved template file, as its failed to get registered
    
            return make_response(jsonify({"status" : status, "message" : message}))
        except Exception as ecp_msg:
            errorhandling.catchError(custom_message = "failed to process new registration request") 
            msg = "failed to process new registration request. error message : "+str(ecp_msg)
            return make_response(jsonify({"status":502, "message": msg}))
            
class scrapRequest(Resource):
    
    def get(self):
        try:
            request_data = request.get_json(force=True)
            request_data["request_id"] = str(uuid.uuid1())
            request_data["datetime"] = str(datetime.datetime.today())
            request_data["status"] = "in-progress"
            
            query = {"collection_name" : "scrappingRequests", 
                     "data" : request_data}
            flag, err = dbc.insertData(query)
            if flag == 0:
                return make_response(jsonify({"status" : 202, "message": "scrapping request received successfully. your request_id : "+request_data["request_id"]}))
            else:
                return make_response(jsonify({"status" : 502, "message": "scrapping request failed to receive. error message : "+str(err)}))
        except Exception as ecp_msg:
            errorhandling.catchError(custom_message = "failed to process new scrapping request") 
            msg = "failed to process new scrapping request. error message : "+str(ecp_msg)
            return make_response(jsonify({"status":502, "message": msg}))
            
### ==================================== api end points ====================================== ###
api.add_resource(appStatus, "/api/v1/appstatus")
api.add_resource(registerAccount, "/api/v1/registeraccount")
api.add_resource(scrapRequest, "/api/v1/scraprequest")


### ======================================= app run ========================================== ###
if __name__ == "__main__":
    app.run(debug=False, host=configData.get("apiHostName"), port=configData.get("apiPortNumber"))

