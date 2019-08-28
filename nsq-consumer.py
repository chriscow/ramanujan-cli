import nsq

def handler(message):
    print (message)
    message.finish()
    return True

r = nsq.Reader(message_handler=handler,
        lookupd_http_addresses=['http://127.0.0.1:4161'],
        topic='test-topic', channel='asdf', lookupd_poll_interval=15)
        
nsq.run()