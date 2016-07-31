from xbmcswift2 import Plugin
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import re
import HTMLParser
import requests
#import random
#from datetime import datetime,timedelta
#import time
import urllib
#import HTMLParser
import xbmcplugin
#import xml.etree.ElementTree as ET
#import sqlite3
import os
#import shutil
#from rpc import RPC
from types import *
#import sys
#xbmc.log(repr(sys.argv))

plugin = Plugin()

if plugin.get_setting('english') == 'true':
    headers={'Accept-Language' : 'en',"X-Forwarded-For": "8.8.8.8"}
else:
    headers={}


big_list_view = False

def log(x):
    xbmc.log(repr(x))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

@plugin.route('/rss/<url>')
def rss(url):
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.text

    match = re.compile(
        '<link>http://www\.imdb\.com/title/(.*?)/</link>'
        ).findall(html)
    ids = match

    if not ids:
        return
    url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
    r = requests.get(url, headers=headers)
    html = r.text

    import json
    imdb = json.loads(html)
    imdb_titles = {}
    for imdb_title in imdb:
       imdb_titles[imdb_title] = imdb[imdb_title]['title']

    return list_titles(imdb_titles)

@plugin.route('/watchlist/<url>')
def watchlist(url):
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.text

    match = re.search(r'IMDbReactInitialState\.push\(({.*?})\);',html)
    if match:
        data = match.group(1)
        import json
        imdb = json.loads(data)
        imdb_list = imdb['list']
        imdb_items = imdb_list['items']
        imdb_titles = imdb['titles']
        all = [i['const'] for i in imdb_items]
        got = [i for i in imdb_titles]
        missing = set(all) - set(got)
        if missing:
            ids = list(missing)
            url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
            r = requests.get(url, headers=headers)
            html = r.text
            imdb = json.loads(html)
            for imdb_title in imdb:
               imdb_titles[imdb_title] = imdb[imdb_title]['title']
            return list_titles(imdb_titles)

def list_titles(imdb_titles):
    items = []
    for imdb_title in imdb_titles:
        imdb_data = imdb_titles[imdb_title]
        title = '-'
        year = ''
        try:
            primary = imdb_data['primary']
            title = primary['title']
            year = primary['year'][0]
        except:
            pass
        type = ''
        try:
            type = imdb_data['type']
        except:
            pass
        plot = ''
        try:
            plot = imdb_data['plot']
            plot = HTMLParser.HTMLParser().unescape(plot.decode('utf-8'))
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
        thumbnail = 'DefaultFolder.png'
        try:
            poster = imdb_data['poster']
            thumbnail = poster['url']
        except:
            pass
        rating = ''
        votes = ''
        try:
            ratings = imdb_data['ratings']
            rating = ratings['rating']
            votes = ratings['votes']
        except:
            pass
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
        items.append(item)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_UNSORTED)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)
    return items

@plugin.route('/add_watchlist')
def add_watchlist():
    dialog = xbmcgui.Dialog()
    url = dialog.input('Enter Watchlist Url', type=xbmcgui.INPUT_ALPHANUM)
    if url:
        name = dialog.input('Enter Watchlist Name', type=xbmcgui.INPUT_ALPHANUM)
        if name:
            watchlists = plugin.get_storage('watchlists')
            watchlists[name] = url

@plugin.route('/remove_watchlist')
def remove_watchlist():
    watchlists = plugin.get_storage('watchlists')
    names = sorted([w for w in watchlists])
    dialog = xbmcgui.Dialog()
    index = dialog.select('Select Watchlist to Remove', names)
    if index >= 0:
        name = names[index]
        del watchlists[name]

@plugin.route('/')
def index():
    watchlists = plugin.get_storage('watchlists')
    items = []
    for watchlist in sorted(watchlists):
        if 'rss.imdb' in watchlists[watchlist]:
            route = 'rss'
        else:
            route = 'watchlist'
        items.append(
        {
            'label': watchlist,
            'path': plugin.url_for(route, url=watchlists[watchlist]),
            'thumbnail':get_icon_path('tv'),
        })
    items.append(
    {
        'label': "Add Watchlist",
        'path': plugin.url_for('add_watchlist'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Remove Watchlist",
        'path': plugin.url_for('remove_watchlist'),
        'thumbnail':get_icon_path('settings'),
    })
    return items

if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)
