while true
do 
  echo "text" | nc -l 8787| head --bytes 2000 
done
