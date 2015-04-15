# Imports and base vars
import cherrypy, os, os.path, re, time, shutil, random, string, itertools, json, uuid
import logging
from utilities import Switch
from jinja2 import Environment, PackageLoader
from model import *
ENV = Environment(loader=PackageLoader('controllers', 'templates'))

#======ROOT=====================================================#
class Root(object):
    @cherrypy.expose
    def index(self, *args, **kwargs):
        template = ENV.get_template('index.html')
        try:
            passwd = cherrypy.config['CONFIG']['FRACKBOXPASSWORD']
            if kwargs['show'] == passwd:
                return template.render(showhide='/api/viewall')
        except:
            pass
        return template.render(showhide='/api/viewmarkers')
        return "<html><body><h1>Service Temporarily Unavailable</h1>Website is down due to maintenance.</body></html>"

#======/api==POST-GET-PUT-DELETE-BACKEND=============================================#
class WebService(object):
    exposed = True
    
    # Initialise the WebService
    def __init__(self):  
        self.allowedfileuploads = 'jpg jpeg pdf gif csv txt zip'  

    # Response to a GET request
    @cherrypy.tools.accept(media='text/plain')
    def GET(self, *vpath, **kwargs):
        model = Model();
        model.kwargs = kwargs
        path0=path1=path2=''
        pathlen = len(vpath)
        if pathlen >= 1:
            path0 = vpath[0] 
        if pathlen >= 2:
            path1 = vpath[1] 
        if pathlen >= 3:
            path2 = vpath[2]    
        # Return List of all nodes: /api/view 
        if path0=='viewall':
            return model.view_all()
        if path0=='viewmarkers':
            return model.view_all(' AND datatype!="frackbox"')
        # View a single node
        elif path0=='view' and len(path1)>0:
            return model.view_node(path1)
        # View single node as an html table
        elif path0=='viewhtml' and len(path1)>0:
            cherrypy.response.headers['Content-Type']= 'text/html'
            return model.view_node_html(path1)
        return "0:"+path0+' 1:'+path1+' 2:'+path2

    # Response to a DELETE request   
    def DELETE(self, *vpath, **kwargs):
        logging.debug('DELETE REQUEST:')
        logging.debug(vpath)
        model = Model();
        #cherrypy.session.pop('mystring', None)
        #TODO: Could be much neater!
        path0=path1=''
        pathlen = len(vpath)
        user = passw = sessionid = ''
        if pathlen >= 1:path0 = vpath[0] 
        if pathlen >= 2:anid = vpath[1]
        if pathlen >= 3:user = vpath[2]   
        if pathlen >= 4:passw = vpath[3]   
        if pathlen >= 5:sessionid = vpath[4]   
        # Move a folder to the 'dustbin' directory
        response = {"success":{},"errors":{}}
        if path0 == 'deletenode':
            response = model.delete_node(response, anid, user, passw)
        elif path0=='delete' and anid== 'annotation':
            user = vpath[3]
            passw =  vpath[4]
            if user == 'none' or passw == 'none':user=passw=''
            data = {'username':user, 'password':passw, 'sessionid':sessionid}
            response = model.delete_annotation(vpath[2], data)    
        else:
            response['errors']['DELETE'] = 'Unrecognised command'
        return json.dumps(response)

    # Response to a POST
    def POST(self, *args, **kwargs):
        logging.debug('POST REQUEST')
        # Initialise our data structure
        model = Model()  
        dbstruct = model.database_structure()
        # Grab the database fields and zero the values
        dbfields = model.grab_dbfields()
        dbfields = dbfields.fromkeys(dbfields['nodes'], '')
        # Contruct the data object
        data = dbstruct['locals'] 
        data['info'] = dbfields
        # Grab the post body
        cl = cherrypy.request.headers['Content-Length']
        data['body'] = cherrypy.request.body.read(int(cl)).decode("utf-8")
        data['path'] = args
        # Lets see what's been posted & validate the submission
        for key in kwargs:
            # Check if we need to save a file
            if type(kwargs[key]) is cherrypy._cpreqbody.Part:
                data['filestosave'].append(kwargs[key])
                data['submitted'][key] = kwargs[key].filename 
            # Nope its a list or string
            else:
                data['submitted'][key] = kwargs[key]
        # Parse the POST submission and determin what to do with the data
        data = model.parse_submission(data)
        # Issue a response to the POST
        logging.debug('POST RESPONSE')
        logging.debug(data)
        return data
    
    # Write changes 
    def PUT(self, *path, **data):
        logging.debug('PUT REQUEST') 
        model = Model();
        # Checking for the following kind of URL: update/annotation/23
        command = self.grab(path, 0)
        target = self.grab(path, 1)
        targetid = self.grab(path, 2)
        url = '/api/{}/{}/{}'.format(command, target, targetid)
        # Check we have all three vars and that this is an update command
        if command and target and targetid and command=='update':
            # Shall we update the annotation?
            if target=='annotation':
                resp = model.update_annotation(targetid, data)
                response = json.dumps(resp)
        else:
            cherrypy.response.headers['Content-Type']= 'text/json' 
            resp = {'code':'KO', 'msg':'Error updating: Incomplete or invalid URL\n{}'.format(url)} 
            response = json.dumps(resp)
        logging.debug('PUT RESPONSE')
        logging.debug(response)
        return response
    
    def MESSAGES(self):
        jsonstr =  json.dumps(MSG)
        MSG.clear()
        return jsonstr
    
    def grab(self, array, index):
        try:
            var=array[index]
        except: 
            var=False
        return var

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
