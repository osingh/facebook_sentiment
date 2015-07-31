#!/usr/bin/python
# -*- coding: utf-8 -*-

from textblob import TextBlob
import facebook
import hashlib

import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado import gen
from tornado.web import StaticFileHandler
import json
import time
#from bson.json_util import dumps
from json import dumps
from tornado.ioloop import IOLoop
from tornado import gen

graph = facebook.GraphAPI(access_token='CAACEdEose0cBAH0UbuBfTMZBYf8cZBPsAZAhQgRkhR6krBJor4di2V9TNHJHmJx7ggArZCsDDHxTdtKuu15IRmRz4PBWUZBE1QbPRhdZBwytDZBGmn0j8BWyVaS0y7PtbcGAca6NCNMYggw6F7AEVHdRrjDbfLPJ33JedLu7i2FEAmFNkcDHURdJ5crioGof75j0G5tjmbALT9GUAmfsDCg0PZCTM29PFKYZD')

post_dict ={#'1584947051720739':'test',
			'10155918758640584':'Post Jul 29',
			'10155914635280584':'Post Jul 27',
			'10155905282520584':'Post Jul 25',
			'10155904019640584':'Post Jul 24',
			'10155900724780584':'Post Jul 23',
			'10155895580955584':'Post Jul 22',
			'10155891477275584':'Post Jul 21',
			'10155888471920584':'Post Jul 20',
			'10155877313795584':'Post Jul 17',
			'10155874422815584':'Post Jul 16',
			'10155870702815584':'Post Jul 15',
			'10155867557020584':'Post Jul 14',
			'10155864843520584':'Post Jul 13',
			'10155854676730584':'Post Jul 10'
				
			}

post_ids = post_dict.keys()

comment_hash_dict = {}
booth_sentiment = {}

booth_post_counts = {}
booth_coments_word_counts = {}

connections = []
need_update = False
app_running = False

from tornado.options import options,define
define("port",default=8005,help="server runs on this port",type=int)



class WebSocketHandler(tornado.websocket.WebSocketHandler):    
    
    def open(self):
        connections.append(self)
        polarity_list = [{'booth':post_dict[post_id],'polarity':round(booth_sentiment[post_id],2)} for post_id in post_dict.keys()]
        words_counts = [{'booth':post_dict[post_id],'commet_count':booth_post_counts[post_id],'words_per_coment':round(booth_coments_word_counts[post_id] * 1.0 /booth_post_counts[post_id])} for post_id in post_dict.keys()]
        self.write_message(dumps({"polarity_list":polarity_list,"words_counts":words_counts}))
        pass


    
    def on_close(self):
        connections.remove(self)
    
    def check_origin(self,origin):
        return True
        
class IndexPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')
        
      
    
class BoothSentimentApplication(tornado.web.Application):
    def __init__(self):
        handlers = [(r'/', IndexPageHandler),\
            (r'/monitor',WebSocketHandler),          
            (r'/static/(.*)',StaticFileHandler, {'path':'static'})]
        
        settings = {"debug":True}
        tornado.web.Application.__init__(self, handlers, **settings)
        
def __update_sentiment_scores(post_id,post_comments):
	polarity = 0.0
	posts_counts = 0
	words_counts = 0
	for data in post_comments['comments']["data"]:
		comment_blob = TextBlob(data['message'])
		polarity += comment_blob.sentiment.polarity				
		posts_counts += 1		
		words_counts += len(data['message'].split())
	booth_sentiment[post_id] = polarity
	booth_post_counts[post_id] = posts_counts
	booth_coments_word_counts[post_id] = words_counts
		
		
@gen.engine
def __run_app_engine():
	while True:
		print 'fetching data from facebook'
		all_post_comments = graph.get_objects(ids=post_ids,connection_name='comments')
		for post_id,post_comments in all_post_comments.items():
			print post_comments
			comment_hash = hashlib.md5(str(post_comments)).hexdigest()
			if post_id not in comment_hash:
				comment_hash_dict[post_id] = comment_hash
				__update_sentiment_scores(post_id,post_comments)        
				need_update = True
			elif comment_hash_dict[post_ids] != comment_hash:
				comment_hash_dict[post_ids] = comment_hash
				self.__update_sentiment_scores(post_id,post_comments)
				need_update = True
				
		if need_update:
			for conn in connections:
				polarity_list = [{'booth':post_dict[post_id],'polarity':round(booth_sentiment[post_id],2)} for post_id in post_dict.keys()]
				words_counts = [{'booth':post_dict[post_id],'commet_count':booth_post_counts[post_id],'words_per_coment':round(booth_coments_word_counts[post_id] * 1.0 /booth_post_counts[post_id])} for post_id in post_dict.keys()]
				conn.write_message(dumps({"polarity_list":polarity_list,"words_counts":words_counts}))
		need_update = False
		yield gen.Task(IOLoop.instance().add_timeout,time.time()+10)
		
		
		
		#time.sleep(20)
        
if __name__ == "__main__":
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(BoothSentimentApplication())
    http_server.listen(options.port)
    
    __run_app_engine()
    tornado.ioloop.IOLoop.instance().start()
