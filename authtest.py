#!/usr/bin/python3
# Example from: http://gr33ndata.blogspot.co.uk/2009/10/cherrypy-custom-authentication.html
import cherrypy, json
 
class RootServer:
    @cherrypy.expose
    def index(self):
        return """This is a public page!"""
 
class WebAPI:
    exposed = True

    @cherrypy.expose
    def GET(self, *args, **kwargs):
        return "GET secure"

    def POST(self, *args, **kwargs):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl)).decode("utf-8")
        speckdata = json.loads(rawbody)
        #print(speckdata["channel_names"])
        # Loop through the data
        msg = "POST secure section"
        print(msg)
        print(kwargs)
        return '{"result":"OK","message":"Upload successful!","payload":{"successful_records":"1","failed_records":"0"}}'

# Exampel usage
if __name__ == '__main__':
    # Define users with passwords
    users = {"admin": "secretPassword",
             "fred": "fred",
             "speck":"speck"}
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8787,
    })
    conf = {
            '/api':  {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(), 
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
        }
    }
    root = RootServer()
    root.api = WebAPI()
    cherrypy.quickstart(root, '/', config=conf)

#if __name__ == '__main__':
#    cherrypy.config.update({
#        'server.socket_host': '0.0.0.0',
#        'server.socket_port': 8787,
#    })
    #cherrypy.tools.authenticate = cherrypy.Tool('before_handler', authenaticate)

#    cherrypy.tools.basic_auth = cherrypy.Tool('before_handler', my_basic_auth_tool )
 #   cherrypy.quickstart(MyServer(),"/",{})
