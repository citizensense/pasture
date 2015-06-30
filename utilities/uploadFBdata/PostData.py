#!/usr/bin/python3
import urllib.request
import urllib.parse
import json

class PostData:

    # Simple method to post some data
    def send(self, url, data):
        self.msg = 'Posting data'
        data = urllib.parse.urlencode(data)
        data = data.encode('utf-8')
        request = urllib.request.Request(url)
        # adding charset parameter to the Content-Type header.
        request.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
        try:
            f = urllib.request.urlopen(request, data, 15)
        except urllib.request.URLError:
            self.msg += 'Connection timed out. No network connection.'
            return False
        # Looks like we have a response
        response = f.read().decode('utf-8')
        try:
            return json.loads(response)            
        except Exception as e:
            self.msg += '. Problem. Very likely there is  no network connection'
            return False
    
if __name__ == "__main__":
    import time
    # Initialise the object
    poster = PostData()
    # Now send some data to a locally installed version of frackbox
    url = 'http://192.168.1.100:8787/api'
    url = 'http://frackbox.citizensense.net/api'
    print('Test POST to: {}'.format(url))
    while True:
        data = {'header': 1, 'csv': 2}
        resp = poster.send(url, data)
        print(str(resp))
        print(poster.msg)
        time.sleep(1)

