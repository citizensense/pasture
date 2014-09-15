import cherrypy, json, csv, time, uuid, os, sys,string, subprocess

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
                'submissiondata':''
                #FIN
            },
            'filestosave':[],
            'submitted':{},
            'errors':{},
            'success':{} 
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
        else:
            # The submission hasn't been recognised
            data.pop('filestosave', None)
            data.pop('info', None)
            data.pop("success", None)
            data['errors']['form'] = 'Post structure not recognised' 
        print(data)
        return data
    
    # CREATE A NEW NODE
    def create_node(self, data):
        try:
            # Really nasty hack!!! Gets the order of the data dict as it is written in the model
            # TODO: Refactor dict into OrderedDict
            command = "sed -n '/"+'#START'+"/,/"+'#FIN'+"/p' model.py" # Grab the text
            command += "| sed -n \"2,11 p\" " # now grab the output between ;lines 2 & 11
            command += "| awk -F \":\" '{print $1}' " # return a col
            command += "| tr '\n' ',' " # replace new lines with a comma
            command += "| tr -d \" '\t\n\r\"" # remove all white space
            command += "| sed '$s/.$//'" # delete the last character
            headerstring = subprocess.check_output(command, shell=True).decode('utf-8').strip()
            # Now lets create a unique fid and directory to store data
            fid = cherrypy.config['filemanager'].createUniqueDirAt(cherrypy.config['datadir'])
            fidpath = os.path.join(cherrypy.config['datadir'], fid)
            data['info']['fid'] = fid
            # And create and 'original' dir 
            cherrypy.config['filemanager'].createDirAt(os.path.join(fidpath, 'original')) 
            # Create a new info.csv file content
            headerlist = headerstring.split(',')
            valuestring = ""
            s=''
            for key in headerlist:
                valuestring += s+str(data['info'][key])
                s=','
            # Save this new data to: datadir/fid/info.csv
            # TODO: Check against ../../ etc being added to the fid!
            infostring = '#'+headerstring+"\n"+valuestring
            infopath = os.path.join(fidpath, 'info.csv')
            cherrypy.config['filemanager'].saveStringToFile(infostring, infopath) 
        except:
            data['errors']['createnode'] = 'Error: Unable to create directory or info.csv'
        return data
    
    # RETURN A LIST OF ALL NODES WITH TITLE AND GPS
    def view_all(self):
        # TODO: Abstract subprocess calls so a global try/except can be applied
        # TODO: Perform a speedcheck against python native csv handler
        # Grab all the info.csv files via the commandline
        com = "cat data/*/info.csv"     # Grab the contents of all the info.csv files
        com += " | grep -v ^# "         # Remove all the commented out elements
        com += " | cut -d , -f 1,8,9,10"# Grab the lan/lon cols
        com += " | sed 's/.*/\"&],/' "  # Format so we have a json string
        com += " | sed 's/,/\":[\"/1' " # Format so we have a json string
        com += " | sed 's/,/\",/1' "    # Format so we have a json string
        com += " | sed 's/\[,\]/[]/'"   # Replace any empty strings
        com += " | sed '$s/,$//'  "     # Delete the last character from the string
        thebytes = subprocess.check_output(com, shell=True)
        thestr = '{'+thebytes.decode("utf-8").strip()+'}'
        return thestr
    
    # VIEW AN INDIVIDUAL NODE
    def view_node(self, fid):
        jsonstr = cherrypy.config['filemanager'].grab_csvfile_asjson(fid, 'info.csv')
        dataheader = cherrypy.config['filemanager'].grab_fileheader(fid, 'info.csv')
        jsonstr = '{"info":'+jsonstr+'}'
        return jsonstr
    
    def delete_node(self, response, fid):
        print('DELETE: '+str(fid)+'\n')
        if cherrypy.config['filemanager'].move_dir('data/'+fid, 'dustbin/'+fid):
            response['success']['completed'] = 'Moved to the rubbish bin'
        else:
            response['errors']['failed'] = "Failed to move to rubbish bin"
        return response

    # MODEL UTILITIES
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
        return
    
#================== SPEC GATEWAY APPLICATION ================================#
class SpecGatewaySubmission:
    
    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        print('THIS AINT THE SPECK GATEWAY APPLICATION')
        return False

    def checkcsvfile(self, data):
        return False

#================== Citizen Sense Kit submission ============================#
class CitizenSenseKitSubmission:

    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        msg = ''
        self.data = data
        # List of field names we are expecting and specify: TODO: Also count the number of fields
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

