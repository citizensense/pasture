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
        #if path0=='viewall':
        #    return cherrypy.config['model'].view_all()
        # View a single node
        #elif path0=='view' and len(path1)>0:
        #    return cherrypy.config['model'].view_node(path1)
        return "0:"+path0+' 1:'+path1+' 2:'+path2

    # Response to a DELETE request
    def DELETE(self, *vpath):
        #cherrypy.session.pop('mystring', None)
        path0=path1=''
        pathlen = len(vpath)
        if pathlen >= 1:path0 = vpath[0] 
        if pathlen >= 2:path1 = vpath[1]
        # Move a folder to the 'dustbin' directory
        response = {"success":{},"errors":{}}
        if path0 == 'deletenode':
            response = cherrypy.config['model'].delete_node(response, path1)
        else:    
            response['errors']['DELETE'] = 'Unrecognised command'
        return json.dumps(response)

    # Response to a POST
    def POST(self, *args, **kwargs):
        # Initialise our data structure
        data=cherrypy.config['model'].database_structure()
        # Grab the post body
        cl = cherrypy.request.headers['Content-Length']
        #data['locals']['postedbody'] = cherrypy.request.body.read(int(cl)).decode("utf-8")
        #data['locals']['path'] = args
        # Lets print what we've been posted
        #print('================POSTED=================')
        #print(kwargs)
        #print(args)
        #print(data['postedbody'])
        #print('=====================================\n')
        # Lets see what's been posted & validate the submission
        #for key in kwargs:
        #    # Check if we need to save a file
        #    if type(kwargs[key]) is cherrypy._cpreqbody.Part:
        #        data['locals']['filestosave'].append(kwargs[key])
        #        data['locals']['submitted'][key] = kwargs[key].filename 
        #    # Nope its a list or string
        #    else:
        #        data['locals']['submitted'][key] = kwargs[key]
        # Parse the submission and save the data if its valid
        data = cherrypy.config['model'].parse_submission(data)
        # Issue a response to the POST
        #print('===RETURN TO POST====================')
        #print(data)
        return '{}'#data
    
    # Write changes
    def PUT(self, another_string):
        cherrypy.session['mystring'] = "PUT:"+another_string
    
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
        return valid

class ExampleSession:
    @cherrypy.expose
    def default(self, param):
        cherrypy.session['mystring'] = "test";
        bob = cherrypy.session['mystring']
        cherrypy.session.pop('mystring', None) 
