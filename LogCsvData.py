#!/usr/bin/python3
import os, subprocess, sys, time

# Class to log data capturted by the kit
class LogCsvData:

    # Accept a full filepath, header and csv: "timestamp, val1", "1234, 77.5"
    def log(self, datafilepath, header, csv):
        try:
            # Lets check if the datafile exists
            if not os.path.isfile(datafilepath):
                # Create the file
                self.savestring(datafilepath, header)
            csv = csv.strip()
            if len(csv) != 0: 
                self.savestring(datafilepath, csv)
            return True
        except:
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
    if save.log('data.csv', header, csv):
        print('Saved to data.csv')
    # Save the latest
    if save.savelatest('latest.csv', header, csv):
        print('Saved to latest.json')

