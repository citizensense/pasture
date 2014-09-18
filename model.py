#!/usr/bin/python3
import cherrypy, json, csv, re, time, uuid, os, sys,string, subprocess
from collections import OrderedDict

# TODO: Security check fid variable
# TODO: Add list of 'registered devices' to config
# TODO: Swap apikeys if new marked is created with the same one..
class Model:

    # Construct 'raw' posted data structure where fid=UniqueDirectoryName
    def submission_structure(self):
        #TODO: Send generation of uuid to a quede task as we need to check if it exists or not
        data={
            'info':{
                #START
                'fid':'',
                'apikey':str(uuid.uuid1()),                
                'created':int(time.time()),
                'updated':int(time.time()),
                'title':'',
                'csvfile':'',
                'deviceid': '',
                'datatype':'',
                'lat':'',
                'lon':'',
                'tags':'',
                'createdby':'',
                'submissiondata':'',
                'latest':'{}'
                #FIN
            },
            'postedbody':'',
            'filestosave':[],
            'submitted':{},
            'errors':{},
            'success':{},
            'altresponse':''
        }
        return data 
    
    # Parse the submission and determine what we need to do with it
    def parse_submission(self, data):
        # Grab the submitted data and convert it to JSON with all commas escaped to &#44;
        jsondump = json.dumps(data['submitted'])
        data['info']['submissiondata'] = jsondump.replace(',', '&#44')
        # Check what/who submitted this data, parse it, then fill in our data structure
        plugins=(UploadformSubmission, SpecGatewaySubmission, CitizenSenseKitSubmission)
        for plugin in plugins:
            obj = plugin()
            parsedoutput = obj.checksubmission(data)
            if parsedoutput is not False: break
        # Prepare for json response
        if parsedoutput:
            # All looks OK
            data.pop('filestosave', None)
            data['success']['code'] = '200 OK'
            data['success']['msg'] = 'A new node has been created' 
            # If the module has its own response then send that instead
            if data['altresponse'] is not '':
                return data['altresponse']
        else:
            # The submission hasn't been recognised
            data.pop('filestosave', None)
            data.pop('info', None)
            data.pop("success", None)
            data['errors']['form'] = 'Post structure not recognised' 
        return json.dumps(data)
    
    # CREATE A NEW NODE
    def create_node(self, data):
        fidpath = ''
        valuestring = ''
        # Attempt to create a new fid dir
        try: 
            # Now lets create a unique fid and directory to store data
            data['info']['fid'] = cherrypy.config['filemanager'].createUniqueDirAt(cherrypy.config['datadir'])
            fidpath = os.path.join(cherrypy.config['datadir'], data['info']['fid'])
            # And create and 'original' dir 
            cherrypy.config['filemanager'].createDirAt(os.path.join(fidpath, 'original')) 
        except:
            data['errors']['createdir'] = 'Error: Unable to create directory'
        # Attempt to build new file content
        valuestring = self.gen_valuestring(cherrypy.config['headerlist'], data['info'])
        if valuestring is False: data['errors']['createnode'] = 'Error: Unable to build info.csv'
        # Prep and attempt to save the new data
        infostring = cherrypy.config['headerstring']+"\n"+valuestring
        infopath = os.path.join(fidpath, 'info.csv')
        try:    cherrypy.config['filemanager'].saveStringToFile(infostring, infopath) 
        except: data['errors']['createnode'] = 'Error: Unable to write info.csv'
        # TODO: If there are any fails, then delete the unique directory
        return data
      
    # RETURN A LIST OF ALL NODES WITH TITLE AND GPS
    def view_all(self):
        jsonstr = self.dbgrab_cols(['fid','lat', 'lon','datatype', 'title', 'latest'])
        # Decode the json string saved in the csv
        jsonstr = jsonstr.replace('&#44;', ',')
        jsonstr = jsonstr.replace('"{\\"', '{"')
        jsonstr = jsonstr.replace('}"', '}')
        jsonstr = jsonstr.replace('\\"', '"')
        print(jsonstr)
        return jsonstr
    
    # VIEW AN INDIVIDUAL NODE
    def view_node(self, fid):
        jsonstr = cherrypy.config['filemanager'].grab_csvfile_asjson(fid, 'info.csv')
        return jsonstr

    # UPDATE SPECIFIED FIELDS OF A NODE
    def update_node(self, fid, keyvaluepairs):
        headerlist = cherrypy.config['headerlist']
        headerstring = cherrypy.config['headerstring']
        path = 'data/'+fid+'/info.csv'
        # First load the node
        jsonstr = cherrypy.config['filemanager'].grab_csvfile_asjson(fid, 'info.csv') 
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
        valuestr = self.gen_valuestring(headerlist, infoobj)
        if valuestr is False: return False 
        infostring = headerstring+'\n'+valuestr
        if cherrypy.config['filemanager'].saveStringToFile(infostring, path) is False:
            return False

    # DELETE A NODE
    def delete_node(self, response, fid):
        if cherrypy.config['filemanager'].move_dir('data/'+fid, 'dustbin/'+fid):
            response['success']['completed'] = 'Moved to the rubbish bin'
        else:
            response['errors']['failed'] = "Failed to move to rubbish bin"
        #for item in keyvaluepairs:
        return response
    
    # CHECK IF WE HAVE A VALID USER
    def validuser(self, username='', pwd=''):
        try:
            # TODO: Check if a user is already logged in
            uid = cherrypy.config['users'][username][0]
            password = cherrypy.config['users'][username][1]
            if pwd == password:
                return uid
            else:
                return False
        except:
            return False

    # MODEL UTILITIES
    def gen_valuestring(self, keylist, keyvaluepairs):
        # Build new info.csv file content
        values = []
        try:
            for key in keylist:
                # Escape all commas as we don't want them in our csv
                val = str(keyvaluepairs[key]).replace(',','&#44;')
                values.append(str(keyvaluepairs[key]))
                valuestring = ','.join(values)
        except:
            return False
        return valuestring

    # Grab a colum of data and output as a validated json string
    def dbgrab_cols(self, keys):
        # Convert the key names to position numbers
        posstr = self.grab_colpositions(keys)
        thestr = '{}'
        if posstr is not '':
            # TODO: Speed check! Perhaps its time to convert to mongoDB?? ;) 
            # Grab all the info.csv files via the commandline
            header = cherrypy.config['headerstring']
            com =  " echo '"+header+"' "        # Echo the header into the script 
            com += " | cut -d , -f "+posstr+";" # Only grab the header names we want
            com += " cat data/*/info.csv"       # Grab the contents of all the info.csv files
            com += " | grep -v ^fid "           # Remove the header elements
            com += " | cut -d , -f "+posstr+""  # Grab the specified cols
            # we've recieved a csv list in the order that they are saved in the CSV file
            try:
                csv = subprocess.check_output(com, shell=True).decode("utf-8").strip()
                jsonstr = cherrypy.config['filemanager'].convert_csvtojson(csv)
                return jsonstr
            except:
                return '{"error":"couldn\'t create valid json "}'
    
    # Search for a specific value. Return an fid number if found
    # TODO: Warning!!! Needs to search for key positions!!
    # TODO: Speed test againt a database, pythons native function or other storage engine
    def dbsearchfor_colval(self, col, value, regex='[^"a-zA-Z0-9-]+'):
        positions = self.grab_colpositions(['fid', col])
        # Lets get rid of any nasties: The default only allows alphanumeric characters and a dash
        valuestrip = re.sub(regex, '', value)
        # And perform the search
        com = "cat data/*/info.csv | grep -v ^# | cut -d, -f "+positions+" | grep '"+valuestrip+"' "
        com += "| cut -d, -f1 " # Just return the fid
        #print('====================COM:\n'+com+'\n')
        try:
            thestr = subprocess.check_output(com, shell=True).decode("utf-8").strip()
        except:
            return False
        if thestr == '':
            return False
        return thestr

    # Convert key names to csv of of position values
    def grab_colpositions(self, keys):
        pos = []
        posstr = ''
        for key in keys:
            try:
                pos.append(cherrypy.config['headerlist'].index(key)+1)
            except:
                print('')
        return ','.join(map(str, pos))

    #  Compare two lists and see if their contents match
    def match_keys(self, expected, provided):
        # List of field names we are expecting and specify 
        for key in provided:
            if key not in expected: 
                state = False
            else: 
                state = True
        if len(expected) is not len(provided):
            state = False
        return state
    
    # Really nasty hack!!! Gets the order of the data dict as it is written in the model
    def gen_csvheaders(self):
        data = self.submission_structure()
        mlen = str(len(data['info'])+1)
        # TODO: Refactor info dict into OrderedDict (didn't know they existsed at the time)
        command = "sed -n '/"+'#START'+"/,/"+'#FIN'+"/p' model.py" # Grab the text
        command += "| sed -n \"2,"+mlen+" p\" " # now grab the output between ;lines 2 & 11
        command += "| awk -F \":\" '{print $1}' " # return a col
        command += "| tr '\n' ',' " # replace new lines with a comma
        command += "| tr -d \" '\t\n\r\"" # remove all white space
        command += "| sed '$s/.$//'" # delete the last character
        cherrypy.config['headerstring'] = subprocess.check_output(command, shell=True).decode('utf-8').strip()
        cherrypy.config['headerlist'] = cherrypy.config['headerstring'].split(',')
        print(cherrypy.config['headerstring'])

#==================================================================#
#==============PLUGINS TO HANDLE MULTIPLE TYPES OF DATA SUBMISSION==================#
#===================================================================================#

#========= THE MAIN UPLOAD FORM ============================================#
class UploadformSubmission:

    # [REQUIRED METHOD] Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        self.data = data
        # List of field names we are expecting
        expected = ['gpstype','title', 'deviceid', 'gps', 'apikey', 'file', 'datatype', 'username', 'password']
        submitted = data['submitted'].keys()
        if cherrypy.config['model'].match_keys(expected, submitted) == False:
            return False
        # Now check if this submission has been made by a valid user
        uid = cherrypy.config['model'].validuser(data['submitted']['username'], data['submitted']['password'])
        if uid is False:
            data['errors']['user'] = 'This username/password combination has not been recognised'
            return data
        data['submitted']['username'] = uid
        # Now format each of the variables and save in 'data'
        for key in expected:
            var = getattr(self, "format_"+key)()
        # Things are looking OK so lets create a new node
        newdata = cherrypy.config['model'].create_node(self.data)
        # Return the data
        return self.data
    
    # [REQUIRED METHOD]
    def checkcsvfile(self, data):
        # Lets grab the file path of this csv file and check it exists
        filename = data['info']['csvfile']
        theid = data['info']['fid']
        fullfilepath = cherrypy.config['filemanager'].grab_originalfilepath(theid, filename)
        if fullfilepath is False: return
        # Now grab the first line of the file
        csvheader = cherrypy.config['filemanager'].grabheader(fullfilepath)
        lookslike="sample_timestamp_utc_secs,raw_particle_count,particle_count,humidity,download_timestamp_utc_millis"
        # If it looks familiar Create a task to convert the csv file to a format ready for view
        if csvheader != lookslike: return
        # Create a task to convert the csv file to a format ready for view
        #cherrypy.config['taskmanager'].add( { 'type':'test', 'data': data } )  
        
    def format_gps(self):
        latlon = self.data['submitted']['gps'].split(',')
        try:
            self.data['info']['lat'] = latlon[0]
            self.data['info']['lon'] = latlon[1]
        except:
            return
    
    def format_gpstype(self):
        return

    def format_username(self):
        # Set the created by field
        # self.data['info']['createdby'] = session.userid  
        # if cherrypy.config['users']['f'][0])
        return

    def format_password(self):
        return

    def format_file(self):
        # Check we have a file in the correct format
        filename = self.data['submitted']['file']
        #  Check we can save files of this type
        if cherrypy.config['filemanager'].fileisoneof(filename, 'csv' ) is False:
            return False
        # Now save the filename
        self.data['info']['csvfile'] = filename
        # And save the file
        # TODO: Add save chunks here....
    
    def format_title(self):
        # TODO: Escape commas from the title
        self.data['info']['title'] = self.data['submitted']['title']       
    
    def format_deviceid(self):
        self.data['info']['deviceid'] = self.data['submitted']['deviceid']

    def format_datatype(self):
        self.data['info']['datatype'] = self.data['submitted']['datatype'] 

    def format_apikey(self):
        apikey = self.data['submitted']['apikey']  
        # Check if an APIkey already exists
        fid = cherrypy.config['model'].dbsearchfor_colval('apikey', apikey)
        self.data['info']['apikey'] = apikey   
        # TODO: Check if this user is allowed to edit this node
        # TODO: Associate user id's with specific devices
        # TODO: Create universal file lock system: V.important!!
        print("FOUND API KEY: "+str(fid))
        if fid is not False:
            # The key does exist, so lets replace the old value with a new one
            self.data['info']['apikey'] = self.data['submitted']['apikey']     
            newkey = str(uuid.uuid1())
            cherrypy.config['model'].update_node(fid, {'apikey':newkey})
        return
    
#================== SPEC GATEWAY APPLICATION ================================#
class SpecGatewaySubmission:
    
    # Check if submission is recognised, if it is, return structured data
    # TODO: This is looking a bit messy so tidy up & move try/except to individual calls
    def checksubmission(self, data):
        # List of field names we are expecting. Reject if they don't match
        expected = ['dev_nickname']
        submitted = data['submitted'].keys()
        if cherrypy.config['model'].match_keys(expected, submitted) == False:
            return False
        # Lets see if we have a node to upload this data to
        # TODO: Check if we e allowed to upload to this marker via Username/Password
        fid = cherrypy.config['model'].dbsearchfor_colval('apikey', data['submitted']['dev_nickname'])
        if fid is False:
            data['altresponse'] = '{"result":"KO", "message":"No marker to upload to"}'
            return data
        else:
            # We have a marker so lets read the data                                                 
            # TODO: Create a log so we can track uploads
            try:
                # Looks ok so lets load it
                if data['postedbody'] != '{}': 
                    js = json.loads(data['postedbody'])
                    array = []
                    # Create the csv headera
                    headerlist = ['timestamp']+js['channel_names']
                    header = ','.join(headerlist)
                    # create the csv strings
                    for x in js['data']:
                        array.append( ','.join(map(str, x)) )
                    csv = '\n'.join(array)
                else:
                    # We've been sent empty JSON, but all is ok, lets halt the process
                    data['altresponse'] = '{"result":"OK"}'
                    return data
            except:
                # Could be invalid JSON, so return an error to the gateway
                data['altresponse'] = '{"result":"KO", "message":"Invalid JSON"}'
                return data
            # Now try and save the data to file
            try:
                cherrypy.config['datalogger'].log('data/'+fid+'/data.csv', header, csv)
                latest = OrderedDict() 
                latest["keys"] = headerlist
                latest["values"] = js['data'][-1]
                lateststr = json.dumps(latest)
                cherrypy.config['model'].update_node(fid, {'latest':lateststr})
                data['altresponse'] = '{"result":"OK","message":"Upload successful!","payload":{"successful_records":"1","failed_records":"0"}}'
            except:
                data['altresponse'] = '{"result":"KO","message":"Unable to save data to file"}'
        return data


#================== Citizen Sense Kit submission ============================#
class CitizenSenseKitSubmission:

    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        msg = ''
        self.data = data
        # List of field names we are expecting and specify:
        # TODO: Also count the number of fields
        expectedkeys = ['uid', 'deviceserial', 'data']
        for key in data['submitted'].keys():
            if key not in expectedkeys: 
                return False
        # Now check we have a node to post to
        msg = 'A Citizen Sense Kit submission'
        #if exists(uid):
        # And save the new data to file
        self.data['success']['msg'] = msg
        return self.data

