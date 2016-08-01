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
import zipfile
import StringIO

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

def get_tvdb_id(imdb_id):
    tvdb_url = "http://thetvdb.com//api/GetSeriesByRemoteID.php?imdbid=%s" % imdb_id
    r = requests.get(tvdb_url)
    tvdb_html = r.text
    tvdb_id = ''
    tvdb_match = re.search(r'<seriesid>(.*?)</seriesid>', tvdb_html, flags=(re.DOTALL | re.MULTILINE))
    if tvdb_match:
        tvdb_id = tvdb_match.group(1)
    return tvdb_id

@plugin.route('/rss/<url>/<type>')
def rss(url,type):
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

    return list_titles(imdb_titles,type)

@plugin.route('/watchlist/<url>/<type>')
def watchlist(url,type):
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
        return list_titles(imdb_titles,type)

def list_titles(imdb_titles,list_type):
    if plugin.get_setting('export') == 'true':
        try: xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
        except: pass
        try: xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
        except: pass
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

        if type == "series": #TODO episode
            meta_url = "plugin://plugin.video.imdb.watchlists/meta_tvdb/%s/%s" % (imdb_title,urllib.quote_plus(title.encode("utf8")))
        elif type == "featureFilm":
            meta_url = 'plugin://plugin.video.meta/movies/play/imdb/%s/library' % imdb_title
        log(title)
        log(type)
        log(meta_url)
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
        if list_type == "tv":
            if type == "series": #TODO episode
                items.append(item)
        elif list_type == "movies":
            if type == "featureFilm":
                items.append(item)
        else:
            items.append(item)

        if plugin.get_setting('export') == 'true':
            if type == "series":
                folder = "TV"
                log('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s' % imdb_title)
                try: xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s' % imdb_title)
                except: log("XXX")
            else:
                folder = "Movies"
                f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/%s/%s.strm' % (folder,imdb_title), "wb")

                f.write(meta_url.encode("utf8"))
                f.close()
                f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/%s/%s.nfo' % (folder,imdb_title), "wb")
                str = "http://www.imdb.com/title/%s/" % imdb_title
                f.write(str.encode("utf8"))
                f.close()


    plugin.add_sort_method(xbmcplugin.SORT_METHOD_UNSORTED)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)
    return items

@plugin.route('/meta_tvdb/<imdb_id>/<title>')
def meta_tvdb(imdb_id,title):
    tvdb_id = get_tvdb_id(imdb_id)
    meta_url = "plugin://plugin.video.meta/tv/tvdb/%s" % tvdb_id

    item ={'label':title, 'path':meta_url, 'thumbnail': get_icon_path('meta')}
    #TODO launch into Meta seasons view
    return [item]
    
@plugin.route('/update_tv')
def update_tv():
    root = 'special://profile/addon_data/plugin.video.imdb.watchlists/TV'
    dirs, files = xbmcvfs.listdir(root)
    for imdb_id in dirs:
        tvdb_id = get_tvdb_id(imdb_id)
        meta_url = "plugin://plugin.video.meta/tv/tvdb/%s" % tvdb_id
        f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s/tvshow.nfo' % imdb_id,"wb")
        str = "http://thetvdb.com/index.php?tab=series&id=%s" % tvdb_id
        f.write(str.encode("utf8"))
        f.close()
        url = 'http://thetvdb.com/api/77DDC569F4547C45/series/%s/all/en.zip' % tvdb_id
        results = requests.get(url)
        data = results.content
        try:
            zip = zipfile.ZipFile(StringIO.StringIO(data))
            z = zip.open('en.xml')
            xml = z.read()
        except:
            continue
        match = re.compile(
            '<Episode>.*?<id>(.*?)</id>.*?<EpisodeNumber>(.*?)</EpisodeNumber>.*?<SeasonNumber>(.*?)</SeasonNumber>.*?</Episode>',
            flags=(re.DOTALL | re.MULTILINE)
            ).findall(xml)
        for id,episode,season in match:
            f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s/S%02dE%02d.strm' % (imdb_id,int(season),int(episode)),"wb")
            str = "plugin://plugin.video.meta/tv/play/%s/%d/%d/library" % (tvdb_id,int(season),int(episode))
            f.write(str.encode("utf8"))
            f.close()    

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

@plugin.route('/category/<type>')
def category(type):
    if type == "all":
        icon = "favourites"
    elif type == "movies":
        icon = "movies"
    else:
        icon = "tv"
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
            'path': plugin.url_for(route, url=watchlists[watchlist], type=type),
            'thumbnail':get_icon_path(icon),
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

@plugin.route('/')
def index():

    items = []
    items.append(
    {
        'label': "All",
        'path': plugin.url_for('category', type="all"),
        'thumbnail':get_icon_path('favourites'),
    })
    items.append(
    {
        'label': "Movies",
        'path': plugin.url_for('category', type="movies"),
        'thumbnail':get_icon_path('movies'),
    })
    items.append(
    {
        'label': "TV",
        'path': plugin.url_for('category', type="tv"),
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
    if plugin.get_setting('export') == 'true':    
        items.append(
        {
            'label': "Update TV Shows",
            'path': plugin.url_for('update_tv'),
            'thumbnail':get_icon_path('settings'),
        })    
    return items

if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)
