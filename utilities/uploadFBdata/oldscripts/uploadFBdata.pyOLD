#!/usr/bin/python3
import urllib.request, urllib.parse, sys, json

class PostData:
    
    def __init__(self, myfile, key):
        # Set vars
        self.url = 'http://frackbox.citizensense.net/api'
        self.myfile = myfile
        self.key = key
        self.chunk = 1000 # Post #n rows of data at a time
        self.rows = 0
        self.validrows = 0
        self.speckheader = 'date_time,sample_timestamp_utc_secs,raw_particle_count,particle_concentration,humidity'
        self.frackboxheader = 'da'
        # Parse data
        self.header = self.grabheader()
        self.datatype = self.checkdatatype()
        print('Parsing values, please wait...')
        self.values = self.grabvalues()
        # Print a readable output
        out = 'Attempting to upload:'
        out += '\n    File: {}'
        out += '\n    Key: {}'
        out += '\n    Url: {}'
        out += '\n    Header: "{}"'
        out += '\n    HeaderList: {}'
        out += '\n    Lines in file: {}'
        out += '\n    Rows of valid data: {}'
        out += '\n    Data type: {}'
        out += '\n    First value[0]: {}'
        print(out.format(myfile, key, self.url, self.header, self.headerlist, self.rows, self.validrows, self.datatype, self.values[0]))
        self.chunkdata()
    
    def checkdatatype(self):
        if self.header == self.speckheader:
            self.datatype = 'SPECK'
            data = self.header.strip().split(',')
            self.headerlist = '["raw_particles","particle_concentration","humidity"]'
        elif self.header == self.frackboxheader:
            self.datatype = 'FRACKBOX'
            self.headerlist = []
        else:
            self.datatype = None
        return self.datatype

    def grabvalues(self):
        values = []
        with open(self.myfile) as f:
            content = f.readlines()
            # Loop through each row of the file
            for row in content:
                data = row.strip().split(',')
                datalen = len(data)
                if self.rows != 0 and self.headerlen == datalen:
                    if self.datatype == 'SPECK':
                        values.append('{},{},{},{}'.format(data[1], data[2], data[3], data[4]))
                    self.validrows = self.validrows+1
                self.rows = self.rows+1
        f.close()   
        return values

    def chunkdata(self):
        if self.datatype == None:
            print('ERROR: Data format not recognised')
            exit()
        n = 0
        chunks = []
        # Now loop through the data and upload n rows at a time
        for datarow in self.values:
            chunks.append(datarow)
            if n >= self.chunk:
                self.postme(chunks)
                chunks = []
                n = 0
            n=n+1
        self.postme(chunks)

    def postme(self, chunks):
        data = '],['.join(chunks)
        data = '[[{}]]'.format(data)
        #print(data)
        if self.datatype == 'FRACKBOX':
            postdata = {
                'akey':self.key,        # The marker key 
                'deviceid': 'ABCDE',    # The ID/Name of the specific frackbox 
                'jsonkeys':self.header, # In this format: [“timestamp”,”co2”,”temp”] 
                'jsonvalues':datarow    # In this format: [“1,2,3”, “1,2,3”, “1,2,3”] 
            }
        elif self.datatype == 'SPECK':
            postdata = {
                'dev_nickname':self.key, 
                'channel_names':self.headerlist,    # In this format as a text string: '[“timestamp”,”co2”,”temp”]' 
                'data':data                       # In this format as a text string: '[“1,2,3”, “1,2,3”, “1,2,3”]' 
            }
        response = self.send(postdata)
        print(response) 
        #exit()

    # Simple method to post some data
    def send(self, data):
        data = urllib.parse.urlencode(data)
        data = data.encode('utf-8')
        request = urllib.request.Request(self.url)
        # adding charset parameter to the Content-Type header.
        request.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
        try:
            f = urllib.request.urlopen(request, data)
            return f.read().decode('utf-8')
        except:
            return {"result":"KO", "msg":"Error with Post.py. Unable to correctly send data"}
    
    def grabheader(self):
        with open(self.myfile) as f:
            content = f.readlines()
        header = content[0].strip()
        self.headerlen = len(header.strip().split(','))
        f.close()   
        return header
    
# Example usage
if __name__ == "__main__":
    # Grab variables from the commandline
    if len(sys.argv) <= 2:
        out =  'Please specify a file and marker key to upload to: '
        out += '\n     $ uploaddata.py filename.csv key'
        print(out)
        exit()
    myfile = sys.argv[1]
    key = sys.argv[2]
    # Initialise the object and attempt to post data
    poster = PostData(myfile, key)
 
