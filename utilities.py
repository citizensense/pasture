#GENERAL HELPER CLASSES: FileManager, Switch 
import cherrypy, os, csv, json, threading, subprocess
from collections import OrderedDict

# TODO: Needs a massive cleanup!!
#=======MANAGE FILES==========================================================#
class FileManager:

    # initialise the object
    def __init__(self): 
        self.lock = threading.Lock() 

    def grab_filepath(self, fid, filename):
        datapath = self.grab_datapath(fid) 
        return self.grab_joinedpath(datapath, filename)
        
    def grab_filecontent(self, fid, filename):
        filepath = self.grab_filepath(fid, filename)
        if os.path.isfile(filepath):
            with open (filepath, "r") as myfile:
                content=myfile.read();
            return content
        else:
            return False
    
    # Convert csvfile to a json key:value object
    # TODO: Convert more than just the first line, its ok for now but...
    # TODO: Error check!!
    def grab_csvfile_asjson(self, fid, filename):
        filepath = self.grab_filepath(fid, filename)
        array = list(csv.reader(open(filepath)))
        ordered = OrderedDict()
        for i in range(len(array[0])):
            key = array[0][i]
            value = array[1][i]
            ordered[key] = value
        return json.dumps(ordered)

    # Generate the filepath to the datadir when given an fid or uuid
    def grab_datapath(self, theid, whichpath='fidpath'):
        # Check if theid is a uuid
        if len(theid) > 20:
            fid = 'we need to discover the fid'
        else:
            fid = theid
        # Now lets build the path
        datadir = os.path.join(os.path.dirname(__file__), cherrypy.config['datadir'])  
        fidpath = os.path.join(datadir, fid)  
        # And finally return the full path
        if whichpath is 'fidpath':
            return fidpath
        elif whichpath is 'original':
            return os.path.join(fidpath, 'original')
    
    # Grab the full path to a file uploaded in the 'original' dir in 'data/fid/original'
    def grab_originalfilepath(self, theid, filename):
        originalpath = self.grab_datapath(theid, 'original')
        fullfilepath = os.path.join(originalpath, filename)  
        if not os.path.exists(fullfilepath): 
            return False
        else:
            return fullfilepath
    
    # Grab the full filepath when given two segments
    def grab_joinedpath(self, left, right):
        return os.path.join(left, right)  
           
    # Save a string to a file
    def saveStringToFile(self, string, filepath):
        with open(filepath, "w") as text_file:
            print(string, file=text_file)
    
    # Save a downloaded file in chunks
    def saveAsChunks(self, myFile, basePath):
        filepath = os.path.join(basePath, myFile.filename)
        out = "length: %s Name: %s Mimetype: %s"
        size = 0
        while True:
            data = myFile.file.read(8192)
            if not data:
                break
            with open(filepath, "ba") as mynewfile:
                mynewfile.write(data)
                mynewfile.close()
            size += len(data)
        return out % (size, myFile.filename, myFile.content_type)
    
    # Check if the file has one of a collection of filetypes 
    def fileisoneof(self, filename, allowedfiletypes):
        msg = ''
        allowed = allowedfiletypes.split()
        dotpos = filename.rfind('.')
        suffix = filename[ dotpos+1 : filename.__len__() ]   
        if dotpos > -1 and suffix in allowed:
            return True
        else :
            return False

    # Create a directory at the specified path
    def createDirAt(self, fullpath) :
        # Check the new name doesn't already exist
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)
            return fullpath
        else :
            return "Error: No Directory Created"

    # Create a new unique directory in the style of "0000001"
    def createUniqueDirAt(self, parentdir):
        # Make sure this can only be run once at a time
        self.lock.acquire() 
        # Grab the most recently modified directory
        try:
            recent = max([os.path.join(parentdir,d) for d in os.listdir(parentdir)], key=os.path.getmtime) 
        except:
            recent = "0"
        recent = recent.replace(parentdir+'/', '') 
        # Convert directory name to an int
        recentint = int(recent)
        # Generate a new directory name and filepath incremended by one
        newdir=str(recentint+1)
        newdir=newdir.zfill(9)
        newfullpath = parentdir+'/'+newdir
        # Check the new name doesn't already exist
        success = self.createDirAt(newfullpath)
        # We done what we've needed so lets release the lock
        self.lock.release() 
        return newdir
    
    # Grab the first line of a file
    def grabheader(self, fullfilepath):
        if os.path.exists(fullfilepath):  
            thebytes = subprocess.check_output("head -n1 "+fullfilepath, shell=True)
            # Output is returned as bytes so we need to convert it to a string
            return thebytes.decode("utf-8").strip()
        else:
            return 'no file found at: '+fullfilepath

# Nice switch statement object
class Switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration
    
    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args: # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


