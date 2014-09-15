# This file has been provided as an example
# Rename it to 'config.py' for it to be used in the application 
# TODO: Replace with more rpobiust authentification

# All users on the site
USERS = {
    # Username: [password, permissions:masteradmin|speck|speckNfrack]
    'admin':    ['apassword', 'masteradmin'],
    'anon':     ['123456789', 'speck']
}

# Known devices
DEVICES = {
    # DeviceID: type
    '123'     : 'frackbox',
    '456'     : 'frackbox'
}
