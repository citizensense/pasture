#!/usr/bin/python3
# This app requires a few modules to be installed:
# To Install on Arch linux:  pacman -S python-cherrypy python-jinja
# Core imports
import cherrypy, os
from controllers import Root, WebService
from taskmanager import TaskManager
from model import Model
from utilities import FileManager
import config

# Config
def get_config():
    # Global config - applies to all application instances
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8787,
        'server.max_request_body_size':416000000,
        'datadir': 'data',
        'dustbin': 'dustbin',
        'taskmanager': TaskManager(),
        'model': Model(),
        'filemanager': FileManager(),
        'headerstring':'',
        'headerlist':[],
        'users':config.init() 
    })
    # Generate the headerstr * headerlist
    # TODO: Remove this once the Orderdict is substituted
    cherrypy.config['model'].gen_csvheaders()
    # Per application config: Define routes
    return {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/api': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        },
        '/public': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './public'
        },
        # Simple authentification used for validating speck gateway application
        # TODO: Create plugin specific hook so this plugin doesn't live here
        '/api/bodytrack/jupload': {
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'localhost',
            'tools.auth_basic.checkpassword': validate_password
        }
    }

# Allows us to access username/password sent by the Speck
# TODO: Implement proper authenification, this is a hack for the moment...
# TODO: Implement 'plugin' specific hook so this code doesn't live here!
def validate_password(self, username, password):
    print('USERNAME: '+username)
    print('PASSWORD: '+password)
    return True
    if username in USERS and USERS[username] == password:
           return True
    return False

# Base structure
def get_app(config=None):
    # Load the config
    config = config or get_config()
    # Dispatch different controller classes via urls
    root = Root()
    root.api = WebService()
    cherrypy.quickstart(root, '/', config)
    # Mount the root to a new app instance
    #cherrypy.tree.mount(root,"/", config)
    # Or create another app with (potentially) a different config
    #cherrypy.tree.mount(ExampleHelloWorld(), '/', config)

# Start the app
def start():
    get_app()
    #cherrypy.engine.signals.subscribe() # Poss extra
    #cherrypy.engine.start()
    #cherrypy.engine.block()

if __name__ == '__main__':
    start()


