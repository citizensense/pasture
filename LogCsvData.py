#!/usr/bin/python3
import os, subprocess, sys, time

# Class to save cvs data to file
class LogCsvData:

    # Accept a full filepath, header and csv: "timestamp, val1", "1234, 77.5"
    def log(self, filepath, header, csv):
        try:
            # Lets check if the datafile exists
            if not os.path.isfile(filepath):
                # Create the file
                #print('Create the file: '+filepath)
                self.savestring(filepath, header)
            csv = csv.strip()
            if len(csv) != 0:
                #print('Save the string: '+filepath)
                self.savestring(filepath, csv)
            return True
        except Exception as e:
            print('\n ==== log() exception:\n'+str(e))
            return False
    
    # Create a directory at the specified path
    def createDir(self, path) :
        # Check the new name doesn't already exist
        if not os.path.exists(path):
            os.makedirs(path)
            #print('created:'+path)
            return True
        else :
            #print('path already exists: '+path)
            return False
 
    # Save a string to a file
    def savestring(self, filepath, string, writeorappend="a"):
        with open(filepath, writeorappend) as text_file:
            print(string, file=text_file)

    # Grab the first #n numer of lines.
    def grabheader(self, fullfilepath, nlines):
        if os.path.exists(fullfilepath):  
            thebytes = subprocess.check_output("head -n1 "+fullfilepath, shell=True)
            return thebytes.decode("utf-8").strip()
        else:
            return 'no file found at: '+fullfilepath
    
    # Save the latest data to file 
    def savelatest(self, filepath, header, csv):
        # Try to load a previous file & create if doesn't exist
        try:
            # Create the file
            self.savestring(filepath, header+'\n'+csv, "w")
            success = True
        except:
            success = False
        return success

# Example showing how to to use this class
# TODO: Fix test example
if __name__ == "__main__":
    # Setup elements for this example
    import random
    save = LogCsvData()
    # Generate vars
    header = 'timecode,value1,value2,title'
    time = str(random.randint(2000,50000))
    val1 = str(random.uniform(1, 65000))
    val2 = str(random.uniform(1, 65000))
    val3 = 'aaa'
    csv = time+','+val1+','+val2+','+val3
    # Log the data
    if save.log('data/yourfile.csv', header, csv):
        print('Saved to yourfile.csv')
    # Save the latest
    if save.savelatest('data/someotherfile.csv', header, csv):
        print('Saved to someotherfile.json')

