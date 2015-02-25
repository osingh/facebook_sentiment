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

graph = facebook.GraphAPI(access_token='CAACEdEose0cBAIwTKtAJxOhaho25FEWO9LGHNlessqTdTzQ2y1BCIZCZB6tVCVJAnIMa0T1QaEJFvL7JMZB1VUZBNZAZCfoqJ6W2uaz50dVZAoUvG1rES7ietMHUGi37wZBechYzjq8dDuyDCPPaBiolT1imuZAZCONu7f9il8ILFZB7Ik5QlqZBR2PmpnvkV5VbKbXpWK7cZAJeOnyOVQ0tzMGZAyQWYVmcOS2DgZD')

post_dict ={#'1584947051720739':'test',
			'1584996468382464':'Analytics',
			'1584990068383104':'Security Testing 1',
			'1584989881716456':'Security Testing 2',
			'1584989795049798':'Mobility',
			'1584987728383338':'Performance Testing',
			'1584987611716683':'Midas',
			'1584986875050090':'Mineraltree',
			'1584986735050104':'DEVOPS',
			'1584986205050157':'CRM Projects',
			'1584985755050202':'Continuous Delivery',
			'1584983858383725':'CRYSTAL SKI',
			'1585233051692139':'ZeOmega',
			'1585240381691406':'Engagement Junction',
			'1585243798357731': 'NoMov'
				
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
