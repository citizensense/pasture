import cherrypy, json, csv, time, uuid, sys,string, subprocess

class Model:

    # Construct 'raw' posted data structure where fid=UniqueDirectoryName
    def submission_structure(self,fid):
        #TODO: Send generation of uuid to a quede task as we need to check if it exists or not
        data={
            'info':{
                #START
                'fid':fid,
                'uuid':str( uuid.uuid1() ),                
                'timestamp':int(time.time()),
                'csvfile':'',
                'device': '',
                'lat':'',
                'lon':'',
                'title':'',
                'tags':'',
                'submissiondata':''
                #FIN
            },
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
        plugins=(UploadformSubmission, SpecGatewaySubmission )
        for plugin in plugins:
            obj = plugin()
            parsedoutput = obj.checksubmission(data)
            if parsedoutput is not False:
                break
        # Now if we have a csv file, lets check what type and prep for view
        for plugin in plugins:
            obj = plugin()
            parsedoutput = obj.checkcsvfile(data)
            if parsedoutput is not False:
                break
        # Very Dirty hack! Get the order of the data dict as it is written above
        # FIX: Really don't need this, just refactor dict into a list/tuple
        w1 = "#START"
        w2 = "#FIN"
        command = "sed -n '/"+w1+"/,/"+w2+"/p' model.py" # Grab the text
        command += "| sed -n \"2,11 p\" " # now grab the output between ;lines 2 & 11
        command += "| awk -F \":\" '{print $1}' " # return a col
        command += "| tr '\n' ',' " # replace new lines with a comma
        command += "| tr -d \" '\t\n\r\"" # remove all white space
        command += "| sed '$s/.$//'" # delete the last character
        thebytes = subprocess.check_output(command, shell=True)
        headerstring = thebytes.decode("utf-8").strip() 
        headerlist = headerstring.split(',')
        # Create the info.csv value string
        valuestring = ""
        s=''
        for key in headerlist:
            valuestring += s+str(data['info'][key])
            s=','
        # Save this new data to: datadir/fid/info.csv
        infostring = '#'+headerstring+"\n"+valuestring
        fullfilepath = cherrypy.config['filemanager'].grab_datapath(data['info']['fid']) 
        infopath = cherrypy.config['filemanager'].grab_joinedpath(fullfilepath, 'info.csv')
        print('OUR DATA INFO.csv:\n'+infostring)
        cherrypy.config['filemanager'].saveStringToFile(infostring, infopath) 
        return data

    def view_all(self):
        # Grab all the info.csv files via the commandline
        com = "cat data/*/info.csv" # Grab the contents of all the info.csv files
        com += " | grep -v ^# " # Remove all the commented out elements
        com += " | cut -d , -f 1,6,7" # Grab the lan/lon cols
        thebytes = subprocess.check_output(com, shell=True)
        thestr = '{'+thebytes.decode("utf-8").strip()+'}'
        return thestr
        

#===================================================================================#
#==============PLUGINS TO HANDLE MULTIPLE TYPES OF DATA SUBMISSION==================#
#===================================================================================#

#========= THE MAIN UPLOAD FORM ============================================#
class UploadformSubmission:

    # [REQUIRED METHOD] Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        self.data = data
        # List of field names we are expecting and specify 
        expectedkeys = ['gps', 'myFile']
        # Check if we recieved the correct number of fields
        if len(expectedkeys) != len(data['submitted']):
            print('THIS AINT THE UPLOAD FORM')
            return False
        # Now format each of the varibles and save in 'data'
        for key in expectedkeys:
            var = getattr(self, "format_"+key)()
        # Return the data
        print('PARSE UPLOAD FORM:' )
        return self.data
    
    # [REQUIRED METHOD]
    def checkcsvfile(self, data):
        # Lets grab the file path of this csv file and check it exists
        filename = data['info']['csvfile']
        theid = data['info']['fid']
        print('CHECKFILE: '+filename)
        fullfilepath = cherrypy.config['filemanager'].grab_originalfilepath(theid, filename)
        if fullfilepath is False: return
        # Now grab the first line of the file
        csvheader = cherrypy.config['filemanager'].grabheader(fullfilepath)
        lookslike="sample_timestamp_utc_secs,raw_particle_count,particle_count,humidity,download_timestamp_utc_millis"
        # If it looks familiar Create a task to convert the csv file to a format ready for view
        if csvheader != lookslike: return
        # Create a task to convert the csv file to a format ready for view
        #cherrypy.config['taskmanager'].add( { 'type':'test', 'data': data } )  

    # Format the contents of each of the submission fields
    def format_general(self):
        self.data['info']['device'] = 'Upload Form'
        
    def format_gps(self):
        latlon = self.data['submitted']['gps'].split(',')
        self.data['info']['lat'] = latlon[0]
        self.data['info']['lon'] = latlon[1]
        # TODO: Should check if both vars exist

    def format_myFile(self):
        # Check we have a file in the correct format
        filename = self.data['submitted']['myFile']
        validname = cherrypy.config['filemanager'].fileisoneof(filename, 'csv' )
        if validname is False: return
        # Now save the filename
        self.data['info']['csvfile'] = filename

#================== SPEC GATEWAY APPLICATION ================================#
class SpecGatewaySubmission:

    # Check if submission is recognised, if it is, return structured data
    def checksubmission(self, data):
        print('PARSE SPEC GATEWAY')
        return False

    def checkcsvfile(self, data):
        return False


