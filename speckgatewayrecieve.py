import cherrypy
import simplejson

class Root(object):

    @cherrypy.expose
    def update(self):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = simplejson.loads(rawbody)
        print(body)
        # do_something_with(body)
        msg = '{"result":"OK","message":"Upload successful!","payload":{"successful_records":"1","failed_records":"0"}}'
        return msg
        #return "Updated %r." % (body,)

    @cherrypy.expose
    def index(self):
        return """
<html>
<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js"></script>
<script type='text/javascript'>
function Update() {
    $.ajax({
      type: 'POST',
      url: "update",
      contentType: "application/json",
      processData: false,
      data: $('#updatebox').val(),
      success: function(data) {alert(data);},
      dataType: "text"
    });
}
</script>
<body>
<input type='textbox' id='updatebox' value='{}' size='20' />
<input type='submit' value='Update' onClick='Update(); return false' />
</body>
</html>
"""

cherrypy.quickstart(Root())
