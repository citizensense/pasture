#!/usr/bin/python3
import cherrypy, json, csv, re, time, uuid, os, sys,string, subprocess
from collections import OrderedDict
import cherrypy, os
from controllers import Root, WebService
from taskmanager import TaskManager
from model import Model
from utilities import FileManager
from LogCsvData import *
import config

model = Model()
filemanager = FileManager()
headerlistt = ["fid","apikey","created","updated","title","csvfile","deviceid","datatype","lat","lon","tags","createdby","submissiondata","latest"]
headerstringg =  ','.join(headerlistt)

# UPDATE SPECIFIED FIELDS OF A NODE
def update_node(self, fid, keyvaluepairs):
    headerlist = headerlistt
    headerstring = headerstringg
    path = 'data/'+fid+'/info.csv'
    # First load the node
    jsonstr = filemanager.grab_csvfile_asjson(fid, 'info.csv') 
    try:
        infoobj = json.loads(jsonstr)
    except:
        return False
    # Loop through the key value pairs and save new values to infobj
    for key in keyvaluepairs:
        # Make sure there are no commas
        val = str(keyvaluepairs[key])
        val = val.replace(',', '&#44;')
        if key in infoobj:
            infoobj[key] = val
    valuestr = model.gen_valuestring(headerlistt, infoobj)
    if valuestr is False: return False 
    infostring = headerstring+'\n'+valuestr
    if filemanager.saveStringToFile(infostring, path) is False:
        return False

update_node(model, '000000001',{'latest':'A latest strinssssg'})



