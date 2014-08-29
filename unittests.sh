# 
echo "Check the server is up"
RESP=$(wget --server-response http://pasture.citizensense.net 2>&1 | awk '/^  HTTP/{print $2}')
echo "Server response: $RESP"
