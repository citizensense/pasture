# This file has been provided as an example                                                              
# Rename it to 'config.py' for it to be used in the application                                          
    
def init():
    SERVERPORT=9797
    FRACKBOXPASSWORD = "letmesee*frackbox*"
    USERS = {    
        'admin':   {'uid':1, 'password':'changethis password',  'permissions':'admin'}    
     }   
    MACS = [        
      'frackboxMACaddress',
      'frackboxMACaddress2'
    ]                                      
    return {'users':USERS, 'MACS':MACS, 'FRACKBOXPASSWORD':FRACKBOXPASSWORD, 'SERVERPORT':SERVERPORT}


