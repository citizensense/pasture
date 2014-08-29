#========Asyschronosly manage tasks============================================#
# Creates a queue of tasks to complete one by one in a thread
# Helpfull Multithreading Resource: 
#   http://www.troyfawkes.com/learn-python-multithreading-queues-basics
#==============================================================================#
import cherrypy, threading, time, uuid   
from queue import Queue
from utilities import Switch 

class TaskManager:

    # Initialise the object
    def __init__(self):
        self.q = Queue(maxsize=0)
        thread = threading.Thread(target=self.loop)
        thread.start()

    # Continuously loop through tasks that need to be completed
    def loop(self):
        # General Application loop
        while True:
            mytime = str(time.time())
            thistask = self.q.get()
            # Lets check what type of task we have
            for case in Switch(thistask['type']):
                # Create a new node
                if case('parse_submission'):
                    cherrypy.config['model'].parse_submission(thistask['data'])
                    break
                # A test so we can easily track things
                if case('test'):
                    break
            print("COMPLETED "+thistask['type']+" UID: "+thistask['uid']+" START:"+thistask['start']+" FIN: "+mytime)
            self.q.task_done()
    
    # Add a new task to the queue in the form of: {'type':'create_node','data':data}
    def add(self, task):
        task['uid'] = str( uuid.uuid1() )
        print('ADDED NEW TASK TO THE QUEUE: '+task['uid'])
        task['start'] = str(time.time())
        self.q.put(task)
        return task['uid']

