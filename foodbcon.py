import pika
import sys
import time
from collections import deque
#####################################################################################

# define variables that will be used throughout
host = "localhost"
foodb_temp_queue = '02-food-B'



#######################################################################################
# defining deque for foodb

foodb_temp_deque = deque(maxlen=20)  # limited to the 20 most recent readings

# Send a Food B Alert if the foodb temp changes less that 1 degree in 10 mins


foodb_alert_limit = 1 # if temp increases by this amount, then send a Food B alert


#######################################################################################
## define delete_queue
def delete_queue(host: str, queue_name: str):
    """
    Delete queues each time we run the program to clear out old messages.
    """
    conn = pika.BlockingConnection(pika.ConnectionParameters(host))
    ch = conn.channel()
    ch.queue_delete(queue=queue_name)
########################################################################################
# define a callback function to be called when a message is received
# defining callback for Food B queue

def foodb_callback(ch, method, properties, body):
    """ Define behavior on getting a message about the Food B temperature.  Since the producer 
    ignored the blanks in the code, the consumer will not be receiving any of the blank rows."""
    # decode the binary message body to a string
    message = body.decode()
    print(f" [x] Received {message} on 02-food-B")
    # acknowledge the message was received and processed 
    # (now it can be deleted from the queue)
    ch.basic_ack(delivery_tag=method.delivery_tag)
    # sleep in seconds
    time.sleep(.5)


    # def foodb deque queue
    # adding message to the foodb deque
    foodb_temp_deque.append(message)

    # identifying first item in the deque
    foodb_deque_temp = foodb_temp_deque[0]

    # splitting date & timestamp from temp in column
    # will now have date & timestamp in index 0 and temp in index 1
    # this will be looking at what occurred 10 mins prior
    foodb_deque_split = foodb_deque_temp.split(",")

    # converting temp in index 1 to float and removing last character  
    foodb_temp_1 = float(foodb_deque_split[1][:-1])
   
    # defining current foodb temp
    foodb_curr_temp = message
    # splitting date & timestamp from temp in column
    # will now have date & timestamp in index 0 and temp in index 1
    # this will be looking at what occurred  10 mins prior
    foodb_curr_column = foodb_curr_temp.split(",")     
    # converting temp in index 1 to float and removing last character    
    foodb_now_temp = float(foodb_curr_column[1][:-1])
    
    # defining foodb temp change and calculating the difference
    # rounding difference to 1 decimal point
    foodb_temp_change = round(foodb_now_temp - foodb_temp_1, 1)
    # defining foodb alert
    if foodb_temp_change < foodb_alert_limit:
        print(f"Alert- Food B Stall!!! The temperature of the foodb has increased by less than 1 F in 10 min (20 readings). \n          foodb temp decrease = {foodb_temp_change} degrees F = {foodb_now_temp} - {foodb_temp_1}")
        
    

# define a main function to run the program
def main(hn: str, qn: str):
    """ Continuously listen for task messages on a named queue."""

    # when a statement can go wrong, use a try-except block
    try:
        # try this code, if it works, keep going
        # create a blocking connection to the RabbitMQ server
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=hn))

    # except, if there's an error, do this
    except Exception as e:
        print()
        print("ERROR: connection to RabbitMQ server failed.")
        print(f"Verify the server is running on host={hn}.")
        print(f"The error says: {e}")
        print()
        sys.exit(1)

    try:
        # use the connection to create a communication channel
        channel = connection.channel()

        # use the channel to declare a durable queue
        # a durable queue will survive a RabbitMQ server restart
        # and help ensure messages are processed in order
        # messages will not be deleted until the consumer acknowledges
        channel.queue_declare(queue=foodb_temp_queue, durable=True)

        # The QoS level controls the # of messages
        # that can be in-flight (unacknowledged by the consumer)
        # at any given time.
        # Set the prefetch count to one to limit the number of messages
        # being consumed and processed concurrently.
        # This helps prevent a worker from becoming overwhelmed
        # and improve the overall system performance. 
        # prefetch_count = Per consumer limit of unaknowledged messages      
        channel.basic_qos(prefetch_count=1) 

        # configure the channel to listen on a specific queue,  
        # use the callback function named callback,
        # and do not auto-acknowledge the message (let the callback handle it)
        channel.basic_consume( queue=foodb_temp_queue, on_message_callback=foodb_callback)
        # print a message to the console for the user
        print(" [*] Ready for work. To exit press CTRL+C")

        # start consuming messages via the communication channel
        channel.start_consuming()

    # except, in the event of an error OR user stops the process, do this
    except Exception as e:
        print()
        print("ERROR: something went wrong.")
        print(f"The error says: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print(" User interrupted continuous listening process.")
        sys.exit(0)
    finally:
        print("\nClosing connection. Goodbye.\n")
        connection.close()


# Standard Python idiom to indicate main program entry point
# This allows us to import this module and use its functions
# without executing the code below.
# If this is the program being run, then execute the code below
if __name__ == "__main__":
    
    # call the main function with the information needed
    main(host, foodb_temp_queue)