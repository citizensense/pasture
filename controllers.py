# Imports and base vars
import cherrypy, os, os.path, re, time, shutil, random, string, itertools, json
from utilities import Switch
from jinja2 import Environment, PackageLoader
ENV = Environment(loader=PackageLoader('controllers', 'templates'))
#TODO: Make this a session variable
MSG = []  

#======ROOT=====================================================#
class Root(object):
    @cherrypy.expose
    def index(self):
        template = ENV.get_template('index.html')
        return template.render(the='variables', go='here it is')

#======/api==POST-GET-PUT-DELETE-BACKEND=============================================#
class WebService(object):
    exposed = True
    
    # Initialise the WebService
    def __init__(self):  
        self.allowedfileuploads = 'jpg jpeg pdf gif csv txt zip'  

    # Response to a GET request
    @cherrypy.tools.accept(media='text/plain')
    def GET(self, *vpath, **kwargs):
        path0=path1=path2=''
        pathlen = len(vpath)
        if pathlen >= 1:
            path0 = vpath[0] 
        if pathlen >= 2:
            path1 = vpath[1] 
        if pathlen >= 3:
            path2 = vpath[2]    
        # Return List of all nodes: /api/view 
        if path0=='view' and path1=='all':
            return cherrypy.config['model'].view_all()
            
        return "0:"+path0+' 1:'+path1+' 2:'+path2
    
    # Response to a POST
    def POST(self, *args, **kwargs):
        # Prep vars for saving data
        datadir = os.path.join(os.path.dirname(__file__), cherrypy.config['datadir'])
        # Generate a unique folder/ID for the data using a lock so as to avoid a race condition
        fid = cherrypy.config['filemanager'].createUniqueDirAt(datadir)
        # The new folder has been created so lets construct our paths to write to
        fidpath = os.path.join(datadir, fid)
        fidfilespath = cherrypy.config['filemanager'].createDirAt(os.path.join(fidpath, 'original')) 
        data=cherrypy.config['model'].submission_structure(fid)

        # Lets see what's been posted & validate the data
        # TODO: We only need to validate an empty submission or invalid filetypes
        #       As the plugins called from model.py validate submission data and generate errors
        for key in kwargs:
            # Check if we need to save a file
            if type(kwargs[key]) is cherrypy._cpreqbody.Part:
                # Check we are allowed to save files with this suffix
                # TODO: Check mimetype in addition to filename
                validmsg = self.VALID(kwargs[key].filename, 'filenamestring')
                if validmsg is True:
                    resp = cherrypy.config['filemanager'].saveAsChunks(kwargs[key], fidfilespath)
                    data['submitted'][key] = kwargs[key].filename   
                else :
                    data['submitted'][key] = ''
                    data['errors'][key] = validmsg 
            # Nope its a string
            else :
                # Checkif string variable is valid
                validmsg = self.VALID(kwargs[key], 'string') 
                if validmsg is True:
                    data['submitted'][key] = kwargs[key]
                else :
                    data['submitted'][key] = ''
                    data['errors'][key] = validmsg
        
        # Create a new node OR if there are errors delete the directory
        if len(data['errors']) < 1 : 
            # Add "create_node" job to the task manager     
            #cherrypy.config['taskmanager'].add( {'type':'parse_submission', 'data': data} ) 
            data = cherrypy.config['model'].parse_submission(data)  
            # data['success']['code'] = '200 OK'
            # data['success']['msg'] = 'A new node is being analysed and submitted' 
        else :
            # Delete the data directory
            # TODO: Turn this into a task using filemanager
            shutil.rmtree(fidpath)
        
        # Issue a JSON response to the POST
        return json.dumps(data)
    
    # Write changes
    def PUT(self, another_string):
        cherrypy.session['mystring'] = "PUT:"+another_string
    
    # Response to a DELETE request
    def DELETE(self):
        cherrypy.session.pop('mystring', None)

    def MESSAGES(self):
        jsonstr =  json.dumps(MSG)
        MSG.clear()
        return jsonstr
    
    # Validate a POST/GET variable
    def VALID(self, var, vartype=''):
        valid = False
        for case in Switch(vartype):
            if case('string'):
                # Check if the string is empty
                valid = True if var.strip() != '' else 'Empty Field' 
                break
            if case('filenamestring'):
                # Only the allowed file types can be saved
                if cherrypy.config['filemanager'].fileisoneof(var, self.allowedfileuploads):
                    valid = True
                else:
                    valid = 'Can only post ('+self.allowedfileuploads+') files.' 
            if case('gps'):
                break
            if case('int'):
                break
            if case('float'):
                break
        return valid

class ExampleSession:
    @cherrypy.expose
    def default(self, param):
        cherrypy.session['mystring'] = "test";
        bob = cherrypy.session['mystring']
        cherrypy.session.pop('mystring', None) 
