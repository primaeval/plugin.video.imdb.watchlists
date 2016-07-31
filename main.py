from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re

import requests
import random

from datetime import datetime,timedelta
import time
#import urllib
#import HTMLParser
import xbmcplugin
#import xml.etree.ElementTree as ET
#import sqlite3
import os
#import shutil
#from rpc import RPC
from types import *

plugin = Plugin()
big_list_view = False

def log(x):
    xbmc.log(repr(x))
    
def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")    

@plugin.route('/watchlist/<url>')
def watchlist(url):
    url = 'http://www.imdb.com/user/ur24041325/watchlist'
    r = requests.get(url)
    html = r.text
    #log(html)
    items = []
    match = re.search(r'IMDbReactInitialState\.push\(({.*?})\);',html)
    if match:
        data = match.group(1)
        #log(data)
        import json
        imdb = json.loads(data)
        #log(imdb)
        imdb_list = imdb['list']
        imdb_items = imdb_list['items']
        #for imdb_item in imdb_items:
            #log(imdb_item)
        imdb_titles = imdb['titles']
        for imdb_title in imdb_titles:
            #log(imdb_title)
            imdb_data = imdb_titles[imdb_title]
            primary = imdb_data['primary']
            title = primary['title']
            log(title)
            year = primary['year'][0]
            log(year)
            
            type = imdb_data['type']
            log(type)
            
            plot = imdb_data['plot']
            log(plot)
            credits = imdb_data['credits']
            stars = credits['star']
            
            cast = []
            try:
                director = credits['director']
                cast.append(director[0]['name'])
            except:
                pass
            try:
                for star in stars:
                    cast.append(star['name'])
            except:
                pass
            log(cast)
            
            thumbnail = ''
            try:
                poster = imdb_data['poster']
                #log(poster)
                thumbnail = poster['url']
            except:
                pass
            log(thumbnail)
            
            rating = ''
            votes = ''
            try:
                ratings = imdb_data['ratings']
                rating = ratings['rating']
                votes = ratings['votes']
            except:
                pass
            log(rating)
            log(votes)
    
            genres = []
            certificate = ''
            try:
                metadata = imdb_data['metadata']
                genres = metadata['genres']
                certificate = metadata['certificate']
            except:
                pass
            log(genres)
            log(certificate)
            
            items.append({'label':title,'thumbnail':thumbnail})
            
    return items
    
    


@plugin.route('/')
def index():
    items = [
    {
        'label': 'Watchlist',
        'path': plugin.url_for('watchlist', url="http://www.imdb.com/user/ur24041325/watchlist"),
        'thumbnail':get_icon_path('tv'),
    },
    ]
    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)