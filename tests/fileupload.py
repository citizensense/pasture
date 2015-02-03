# Import dependencies
import os
import cherrypy
from cherrypy.lib import static

# Setup core variables
localDir = os.path.dirname(__file__)
absDir = os.path.join(os.getcwd(), localDir)
conf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

# Main dispatchers
class FileDemo(object):
    
    def index(self):
        return """
        <html><body>
            <h2>Upload a file</h2>
            <form action="upload" method="post" enctype="multipart/form-data">
            filename: <input type="file" name="myFile" /><br />
            <input type="submit" />
            </form>
            <h2>Download a file</h2>
            <a href='download'>This one</a>
        </body></html>
        """
    index.exposed = True
    
    def upload(self, myFile):
        out = """<html>
        <body>
            myFile length: %s<br />
            myFile filename: %s<br />
            myFile mime-type: %s
        </body>
        </html>"""
        # Read the file in chuncks and write it out
        size = 0
        while True:
            data = myFile.file.read(8192)
            if not data:
                break
            with open(myFile.filename, "ba") as mynewfile:
                mynewfile.write(data)
                mynewfile.close()
            size += len(data)
        return out % (size, myFile.filename, myFile.content_type)
    upload.exposed = True
    
    def download(self):
        path = os.path.join(absDir, "pdf_file.pdf")
        return static.serve_file(path, "application/x-download",
                                 "attachment", os.path.basename(path))
    download.exposed = True

if __name__ == '__main__':
    cherrypy.quickstart(FileDemo(), config=conf)

