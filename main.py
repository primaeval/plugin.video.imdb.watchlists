from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re
import HTMLParser
import requests
import random

from datetime import datetime,timedelta
import time
import urllib
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
        all = [i['const'] for i in imdb_items]
        #log(all)
        #log(len(all))
        got = [i for i in imdb_titles]
        #log(got)
        #log(len(got))
        missing = set(all) - set(got)
        #log(len(missing))
        
        if missing:
            #log(missing)
            ids = list(missing)
            url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
            #log(url)
            r = requests.get(url)
            html = r.text
            imdb = json.loads(html)
            #log(imdb)
            #imdb_titles2 = imdb['titles']
            #log(imdb)
            #log(imdb_titles2)
            #imdb_titles.update(imdb_titles2)
            for imdb_title in imdb:
               imdb_titles[imdb_title] = imdb[imdb_title]['title']
            #log(imdb_titles)
        #return
        for imdb_title in imdb_titles:
            #log(imdb_title)
            imdb_data = imdb_titles[imdb_title]
            title = '-'
            year = ''
            try:
                primary = imdb_data['primary']
                title = primary['title']
                #log(title)
                year = primary['year'][0]
                #log(year)
            except:
                pass
                
            type = ''
            try:
                type = imdb_data['type']
                #log(type)
            except:
                pass
                
            plot = ''
            try:
                #log("XXX")
                plot = imdb_data['plot']
                #log(plot)
                plot = HTMLParser.HTMLParser().unescape(plot.decode('utf-8'))
                #log(plot)
            except:
                pass
                

            
            cast = []
            try:
                credits = imdb_data['credits']
                director = credits['director']
                cast.append(director[0]['name'])
            except:
                pass
            try:
                credits = imdb_data['credits']
                stars = credits['star']              
                for star in stars:
                    cast.append(star['name'])
            except:
                pass
            #log(cast)
            
            thumbnail = 'DefaultFolder.png'
            try:
                poster = imdb_data['poster']
                #log(poster)
                thumbnail = poster['url']
            except:
                pass
            #log(thumbnail)
            
            rating = ''
            votes = ''
            try:
                ratings = imdb_data['ratings']
                rating = ratings['rating']
                votes = ratings['votes']
            except:
                pass
            #log(rating)
            #log(votes)
    
            genres = []
            certificate = '-'
            runtime = ''
            try:
                metadata = imdb_data['metadata']
                genres = metadata['genres']
                certificate = metadata['certificate']
                runtime = metadata['runtime']
            except:
                pass
            #log(genres)
            #log(certificate)
            
            if type == "series":
                meta_url = "plugin://plugin.video.meta/tv/search_term/%s/1" % urllib.quote_plus(title.encode("utf8"))
            else:
                meta_url = 'plugin://plugin.video.meta/movies/play/imdb/%s/select' % imdb_title

            context_items = []
            try:
                if type == 'featureFilm' and xbmcaddon.Addon('plugin.video.couchpotato_manager'):
                    context_items.append(
                    ('Add to Couch Potato', "XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add-by-id/%s)" % (imdb_title)))
            except:
                pass
            try:
                if type == 'series' and xbmcaddon.Addon('plugin.video.sickrage'):
                    context_items.append(
                    ('Add to Sickrage', "XBMC.RunPlugin(plugin://plugin.video.sickrage?action=addshow&&show_name=%s)" % (urllib.quote_plus(title.encode("utf8")))))
            except:
                pass
            ''' #TODO
            try:
                if xbmcaddon.Addon('plugin.program.super.favourites'):
                    context_items.append(
                    ('iSearch', "XBMC.RunPlugin(plugin://plugin.program.super.favourites?mode=0&keyword=%s)" % (urllib.quote_plus(title.encode("utf8")))))
            except:
                pass                
            '''
            item = {
                'label': title,
                'path': meta_url,
                'thumbnail': thumbnail,
                'info': {'title': title, 'genre': ','.join(genres),'code': imdb_title,
                'year':year,'rating':rating,'plot': plot,
                'mpaa': certificate,'cast': cast,'duration': runtime, 'votes': votes},
                'context_menu': context_items,
                'replace_context_menu': False,
            }
            #log(context_items)
            #item.add_context_menu_items(context_items)
            items.append(item)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_UNSORTED)            
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)
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
