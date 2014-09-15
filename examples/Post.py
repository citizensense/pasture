#!/usr/bin/python3
import urllib.request
import urllib.parse

class PostData:

    # Simple method to post some data
    def send(self, url, data):
        data = urllib.parse.urlencode(data)
        data = data.encode('utf-8')
        request = urllib.request.Request(url)
        # adding charset parameter to the Content-Type header.
        request.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
        try:
            f = urllib.request.urlopen(request, data)
            print(f.read().decode('utf-8'))
        except:
            print('ERROR: Failed To Access Webpage')

# Example usage
if __name__ == "__main__":
    # Initialise the object
    poster = PostData()
    dfile = 'data9thSeptFixed.csv'
    # Now grab the header of the csv file
    csvheader = subprocess.check_output("head -n1 "+dfile, shell=True).decode("utf-8").strip()     
    # Now send some data to a locally installed version of frackbox
    url = 'http://localhost:8787/api/addto/000000004'
    postdata = {
        'key':'612d6f2c-3ba0-11e4-991f-7c7a91472dae', 
        'deviceid':'6794560212', 
        'csvheader':csvheader,
        'csvvalues':csvvalues
    }
    response = poster.send(url, postdata)
    print(response)

