from datetime import datetime,timedelta
from types import *
from xbmcswift2 import Plugin
from xbmcswift2 import actions
import HTMLParser
import StringIO
import json
import os
import re
import requests
import sys
import time
import urllib
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import xbmcplugin
import zipfile
from collections import OrderedDict
#xbmc.log(repr(sys.argv))
from trakt import Trakt

plugin = Plugin()

if plugin.get_setting('english') == 'true':
    headers={
    'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; rv:48.0) Gecko/20100101 Firefox/48.0',
    'Accept-Language' : 'en',
    "X-Forwarded-For": "8.8.8.8"}
else:
    headers={}


big_list_view = False

def log(x):
    xbmc.log(repr(x),xbmc.LOGERROR)

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

@plugin.route('/ls_list/<url>/<type>/<export>')
def ls_list(url,type,export):
    #log(url)
    list_type = type
    big_list_view = True
    ids = []
    r = requests.get(url, headers=headers)
    html = r.text
    #log(html)
    match = re.compile(
        '<div class="lister-item.*?href="/title/(tt[0-9]*)',
        flags=(re.DOTALL | re.MULTILINE)
        ).findall(html)
    ids = ids + match
    ids = list(OrderedDict.fromkeys(ids))
    #log(ids)
    order = ids
    list_items = html.split('<div class="lister-item ')
    data = {}
    for list_item in list_items:
        #log(list_item)
        temp_data = {}
        #if not re.search(r'^(odd|even)">',list_item):
        #    continue

        img_url = ''
        #<img alt="Go North"\nclass="loadlate"\nloadlate="https://images-na.ssl-images-amazon.com/images/M/MV5BMjE4Mjg0MjgzOV5BMl5BanBnXkFtZTgwMjU3NDc4MDI@._V1_UX140_CR0,0,140,209_AL_.jpg"
        img_match = re.search(r'"(https://images-na.ssl-images-amazon.com/images.*?)"', list_item, flags=(re.DOTALL | re.MULTILINE))
        if img_match:
            img = img_match.group(1)
            img_url = re.sub(r'U[XY].*_.jpg','SX344_.jpg',img) #NOTE 344 is Confluence List View width
        #log(img_url)
        temp_data['thumbnail'] = img_url
        title = ''
        imdbID = ''
        year = ''
        #<a href="/title/tt4649466/?ref_=ttls_li_tt"\n>Kingsman: The Golden Circle</a>
        title_match = re.search(r'<a.*?href="/title/(tt[0-9]*)/\?ref_=ttls_li_tt.*?>(.*?)</a>', list_item, flags=(re.DOTALL | re.MULTILINE))
        if title_match:
            imdbID = title_match.group(1)
            title = title_match.group(2)
        temp_data['title'] = HTMLParser.HTMLParser().unescape(title.decode('utf-8'))

        #<span class="lister-item-year text-muted unbold">(2017)</span>
        type = 'featureFilm'
        title_match = re.search(r'<span class="lister-item-year.*?>\((.*?)\)</span>', list_item, flags=(re.DOTALL | re.MULTILINE))
        if title_match:
            year = title_match.group(1)
            if year.endswith("Series"):
                type = "series"
                year = year[0:4]

        temp_data['year'] = year
        temp_data['type'] = type

        #<div class="rating rating-list" data-auth="xxx" id="tt0338013|imdb|8.3|8.3|list" data-ga-identifier="list"\n title="Users rated this 8.3/10 (665,741 votes) - click stars to rate">
        rating = ''
        votes = ''
        rating_match = re.search(r'title="Users rated this (.+?)/10 \((.+?) votes\)', list_item, flags=(re.DOTALL | re.MULTILINE))
        if rating_match:
            rating = rating_match.group(1)
            votes = rating_match.group(2)
            votes = re.sub(',','',votes)
        temp_data['rating'] = rating
        temp_data['votes'] = votes
        #<div class="item_description">A pair of childhood friends and neighbors fall for each other's sons. <span>(112 mins.)</span></div>
        plot = ''
        runtime = 0
        plot_match = re.search(r'<div class="item_description">(.*?)<span>\((.*?) mins\.\)</span></div>', list_item, flags=(re.DOTALL | re.MULTILINE))
        if plot_match:
            plot = plot_match.group(1).strip()
            runtime = plot_match.group(2)
        temp_data['plot'] = plot
        temp_data['runtime'] = int(runtime) * 60

        #TODO
        temp_data['cast'] = []
        temp_data['genres'] = []
        #TODO or can't do
        temp_data['certificate'] = ''

        #log(imdbID)
        #log(temp_data)
        data[imdbID] = temp_data

    #<a class="flat-button lister-page-next next-page" href="/list/ls068584810/?sort=listorian:asc&page=2">
    new_url = ''
    '''

    match = re.search(
        '<div class="pagination">(.*?)</div>',
        html,
        flags=(re.DOTALL | re.MULTILINE)
        )
    if match:
        match = re.search(
            '<a href="([^"]*?)">Next&nbsp;&raquo;</a>',
            match.group(1),
            flags=(re.DOTALL | re.MULTILINE)
        )
        if match:
            old_url = url.split('?')[0]
            new_url = "%s%s" % (old_url,match.group(1))

    '''
    match = re.search(
        'class=".*?lister-page-next.*?href="(.*?)"',
        html,
        flags=(re.DOTALL | re.MULTILINE)
        )
    if match:
        new_url = match.group(1)
        new_url = "http://www.imdb.com" + new_url
        #log(url)
        #log(new_url)
    if not ids:
        return
    #log("YYY")
    #log(data)
    #log(order)
    items = make_list(data,order,list_type,export)
    if new_url:
        path = plugin.url_for(ls_list, url=new_url, type=list_type, export=export)
        items.append(
        {
            'label': "[COLOR orange]Next Page >>[/COLOR]",
            'path': path,
            'thumbnail':get_icon_path('settings'),
        })

    if export == "True":
        return (new_url,items)
    else:
        return items

@plugin.route('/rss/<url>/<type>/<export>')
def rss(url,type,export):
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

    imdb = json.loads(html)
    imdb_ids = {}
    for imdb_id in imdb:
       imdb_ids[imdb_id] = imdb[imdb_id]['title']
    ids.reverse()
    return list_titles(imdb_ids,ids,type,export)

@plugin.route('/watchlist/<url>/<type>/<export>')
def watchlist(url,type,export):
    #log("XXX")
    #log(url)
    big_list_view = True
    r = requests.get(url, headers=headers)
    html = r.text
    #log(html)
    match = re.search(r'IMDbReactInitialState\.push\(({.*?})\);',html)
    if match:
        data = match.group(1)
        #log(data)
        imdb = json.loads(data)
        #log(imdb)
        imdb_list = imdb['list']
        imdb_items = imdb_list['items']
        imdb_ids = imdb['titles']
        all = [i['const'] for i in imdb_items]
        got = [i for i in imdb_ids]
        missing = set(all) - set(got)
        if missing:
            ids = list(missing)
            url = 'http://www.imdb.com/title/data?ids=%s' % ','.join(ids)
            r = requests.get(url, headers=headers)
            html = r.text
            imdb = json.loads(html)
            for imdb_id in imdb:
               imdb_ids[imdb_id] = imdb[imdb_id]['title']
        return list_titles(imdb_ids,all,type,export)

@plugin.route('/movie_search/<url>/<type>/<export>')
def movie_search(url,type,export):
    count = 0
    while url:
        html = requests.get(url,headers=headers).content
        matches = re.findall('<a href="/title/(tt[0-9]*)/\?ref_=adv_li_tt"\n>(.*?)</a>\n    <span class="lister-item-year text-muted unbold">\((.*?)\)</span>',html,flags=(re.DOTALL | re.MULTILINE))
        for match in matches:
            imdb_id = match[0]
            type = "movie"
            title = match[1]
            year = match[2]
            add_to_library(imdb_id, type, urllib.quote_plus(title), year)
        match = re.search('<a href="(.*?)&ref_=adv_nxt"',html)
        if match:
            url = "http://www.imdb.com/search/title" + match.group(1)
        count = count + 1
        if count >= int(plugin.get_setting('search.pages')):
            break

def list_titles(imdb_ids,order,list_type,export):
    data = {}
    for imdb_id in order:
        temp_data = {}
        imdb_data = imdb_ids[imdb_id]
        temp_data['title'] = '-'
        temp_data['year'] = ''
        try:
            primary = imdb_data['primary']
            temp_data['title'] = primary['title']
            temp_data['year'] = primary['year'][0]
        except:
            pass
        temp_data['type'] = ''
        try:
            temp_data['type'] = imdb_data['type']
        except:
            pass
        temp_data['plot'] = ''
        try:
            plot = imdb_data['plot']
            temp_data['plot'] = HTMLParser.HTMLParser().unescape(plot.decode('utf-8'))
        except:
            pass
        temp_data['cast'] = []
        try:
            credits = imdb_data['credits']
            director = credits['director']
            temp_data['cast'].append(director[0]['name'])
        except:
            pass
        try:
            credits = imdb_data['credits']
            stars = credits['star']
            for star in stars:
                temp_data['cast'].append(star['name'])
        except:
            pass
        temp_data['thumbnail'] = 'DefaultFolder.png'
        try:
            poster = imdb_data['poster']
            temp_data['thumbnail'] = poster['url']
        except:
            pass
        temp_data['rating'] = ''
        temp_data['votes'] = ''
        try:
            ratings = imdb_data['ratings']
            temp_data['rating'] = ratings['rating']
            temp_data['votes'] = ratings['votes']
        except:
            pass
        temp_data['genres'] = []
        temp_data['certificate'] = '-'
        temp_data['runtime'] = ''
        try:
            metadata = imdb_data['metadata']
            temp_data['genres'] = metadata['genres']
            temp_data['certificate'] = metadata['certificate']
            temp_data['runtime'] = metadata['runtime']
        except:
            pass
        data[imdb_id] = temp_data

    return make_list(data,order,list_type,export)

def on_token_refreshed(response):
    plugin.set_setting( "authorization", json.dumps(response))

def authenticate():
    dialog = xbmcgui.Dialog()
    pin = dialog.input('Open a web browser at %s' % Trakt['oauth'].pin_url(), type=xbmcgui.INPUT_ALPHANUM)
    if not pin:
        return False
    authorization = Trakt['oauth'].token_exchange(pin, 'urn:ietf:wg:oauth:2.0:oob')
    if not authorization:
        return False
    plugin.set_setting( "authorization", json.dumps(authorization))
    return True


@plugin.route('/add_to_trakt_watchlist/<type>/<imdb_id>/<title>')
def add_to_trakt_watchlist(type,imdb_id,title):
    Trakt.configuration.defaults.app(
        id=8835
    )
    Trakt.configuration.defaults.client(
        id="aa1c239000c56319a64014d0b169c0dbf03f7770204261c9edbe8ae5d4e50332",
        secret="250284a95fd22e389b565661c98d0f33ac222e9d03c43b5931e03946dbf858dc"
    )
    Trakt.on('oauth.token_refreshed', on_token_refreshed)
    if not plugin.get_setting('authorization'):
        if not authenticate():
            return
    authorization = json.loads(plugin.get_setting('authorization'))
    with Trakt.configuration.oauth.from_response(authorization, refresh=True):
        result = Trakt['sync/watchlist'].add({
            type: [
                {
                    'ids': {
                        'imdb': imdb_id
                    }
                }
            ]
        })
        dialog = xbmcgui.Dialog()
        dialog.notification("Trakt: add to watchlist",title)

@plugin.route('/add_to_trakt_collection/<type>/<imdb_id>/<title>')
def add_to_trakt_collection(type,imdb_id,title):
    Trakt.configuration.defaults.app(
        id=8835
    )
    Trakt.configuration.defaults.client(
        id="aa1c239000c56319a64014d0b169c0dbf03f7770204261c9edbe8ae5d4e50332",
        secret="250284a95fd22e389b565661c98d0f33ac222e9d03c43b5931e03946dbf858dc"
    )
    Trakt.on('oauth.token_refreshed', on_token_refreshed)
    if not plugin.get_setting('authorization'):
        if not authenticate():
            return
    authorization = json.loads(plugin.get_setting('authorization'))
    with Trakt.configuration.oauth.from_response(authorization, refresh=True):
        result = Trakt['sync/collection'].add({
            type: [
                {
                    'ids': {
                        'imdb': imdb_id
                    }
                }
            ]
        })
        if type == "shows":
            result = Trakt['sync/history'].add({
                type: [
                    {
                        'ids': {
                            'imdb': imdb_id
                        }
                    }
                ]
            })
        dialog = xbmcgui.Dialog()
        dialog.notification("Trakt: add to collection",title)

def make_list(imdb_ids,order,list_type,export):
    if export == "True":
        xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
        xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    items = []
    for imdb_id in order:
        if plugin.get_setting('hide_duplicates') == "true" and existInKodiLibrary(imdb_id):
            continue
        imdb_data = imdb_ids[imdb_id]
        title = imdb_data['title']
        year = imdb_data['year']
        type = imdb_data['type']
        plot = imdb_data['plot']
        cast = imdb_data['cast']
        thumbnail = imdb_data['thumbnail']
        rating = imdb_data['rating']
        votes = imdb_data['votes']
        genres = imdb_data['genres']
        certificate = imdb_data['certificate']
        runtime = imdb_data['runtime']

        meta_url = ''
        if type == "series": #TODO episode
            trakt_type = 'shows'
            meta_url = "plugin://plugin.video.imdb.watchlists/meta_tvdb/%s/%s" % (imdb_id,urllib.quote_plus(title.encode("utf8")))
        elif type == "featureFilm":
            trakt_type = 'movies'
            meta_url = 'plugin://%s/movies/play/imdb/%s/library' % (plugin.get_setting('catchup.plugin').lower(),imdb_id)
        context_items = []
        try:
            if xbmcaddon.Addon('plugin.program.super.favourites'):
                context_items.append(
                ('iSearch', 'ActivateWindow(%d,"plugin://%s/?mode=%d&keyword=%s",return)' % (10025,'plugin.program.super.favourites', 0, urllib.quote_plus(title.encode("utf8")))))
        except:
            pass
        context_items.append(
        ('Add to Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_to_library', imdb_id=imdb_id, type=type, title=urllib.quote_plus(title.encode("utf8")), year=year))))
        context_items.append(
        ('Delete from Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for('delete_from_library', imdb_id=imdb_id, type=type))))
        context_items.append(('Add to Trakt Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_to_trakt_watchlist', type=trakt_type, imdb_id=imdb_id, title=title.encode("utf8")))))
        context_items.append(('Add to Trakt Collection', 'XBMC.RunPlugin(%s)' % (plugin.url_for('add_to_trakt_collection', type=trakt_type, imdb_id=imdb_id, title=title.encode("utf8")))))
        try:
            if type == 'featureFilm' and xbmcaddon.Addon('plugin.video.couchpotato_manager'):
                context_items.append(
                ('Add to Couch Potato', "XBMC.RunPlugin(plugin://plugin.video.couchpotato_manager/movies/add-by-id/%s)" % (imdb_id)))
        except:
            pass
        try:
            if type == 'series' and xbmcaddon.Addon('plugin.video.sickrage'):
                context_items.append(
                ('Add to Sickrage', "XBMC.RunPlugin(plugin://plugin.video.sickrage?action=addshow&&show_name=%s)" % (urllib.quote_plus(title.encode("utf8")))))
        except:
            pass

        item = {
            'label': title,
            'path': meta_url,
            'thumbnail': thumbnail,
            'info': {'title': title, 'genre': ','.join(genres),'code': imdb_id,
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

        if export == "True":
            add_to_library(imdb_id, type, title, year)

    plugin.set_content('movies')
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_UNSORTED)
    plugin.add_sort_method(xbmcplugin.SORT_METHOD_TITLE)
    return items

movieDict = {}
showDict = {}
def existInKodiLibrary(id, season="1", episode="1"):
    global movieDict
    global showDict
    result = False
    if 'tt' in id:
        # Movies
        if not movieDict:
            query = {
                'jsonrpc': '2.0',
                'id': 0,
                'method': 'VideoLibrary.GetMovies',
                'params': {
                    'properties': ['imdbnumber', 'file']
                }
            }
            response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
            movieDict = dict(
                (movie['imdbnumber'], movie['file'])
                for movie in response.get('result', {}).get('movies', [])
            )
        if movieDict.has_key(id):
            result = True
    else:
        # TV Shows
        if not showDict:
            query = {
                'jsonrpc': '2.0',
                'id': 0,
                'method': 'VideoLibrary.GetTVShows',
                'params': {
                    'properties': ['imdbnumber', 'file', 'season', 'episode']
                }
            }
            response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))
            showDict = dict(
                (show['imdbnumber'] + "-" + str(show['season']) + "-" + str(show['episode']), show['file'])
                for show in response.get('result', {}).get('tvshows', [])
            )
        if showDict.has_key(id + "-" + str(season) + "-" + str(episode)):
            result = True
    return result

@plugin.route('/add_to_library/<imdb_id>/<type>/<title>/<year>')
def add_to_library(imdb_id,type,title,year):
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    if type == "series":
        try: xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s' % imdb_id)
        except: pass
        update_tv_series(imdb_id)
    else:
        if plugin.get_setting('duplicates') == "false" and existInKodiLibrary(imdb_id):
            pass
        else:
            f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.strm' % (imdb_id), "wb")
            movie_library_url = plugin.get_setting('movie.library.url')
            meta_url = plugin.get_setting('movie.library')
            if movie_library_url == "true" and meta_url:
                meta_url = meta_url.replace("%Y",year)
                meta_url = meta_url.replace("%I",imdb_id)
                meta_url = meta_url.replace("%T",title)
            else:
                meta_url = 'plugin://%s/movies/play/imdb/%s/library' % (plugin.get_setting('catchup.plugin').lower(),imdb_id)
            f.write(meta_url.encode("utf8"))
            f.close()
            f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.nfo' % (imdb_id), "wb")
            str = "http://www.imdb.com/title/%s/" % imdb_id
            f.write(str.encode("utf8"))
            f.close()

@plugin.route('/delete_from_library/<imdb_id>/<type>')
def delete_from_library(imdb_id,type):
    if type == "series":
        tv_dir = 'special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s' % imdb_id
        dirs, files = xbmcvfs.listdir(tv_dir)
        for file in files:
            xbmcvfs.delete("%s/%s" % (tv_dir,file))
        xbmcvfs.rmdir(dir)
    else:
        f = 'special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.strm' % (imdb_id)
        xbmcvfs.delete(f)
        f = 'special://profile/addon_data/plugin.video.imdb.watchlists/Movies/%s.nfo' % (imdb_id)
        xbmcvfs.delete(f)

@plugin.route('/meta_tvdb/<imdb_id>/<title>')
def meta_tvdb(imdb_id,title):
    tvdb_id = get_tvdb_id(imdb_id)
    meta_url = "plugin://%s/tv/tvdb/%s" % (plugin.get_setting('catchup.plugin').lower(),tvdb_id)

    item ={'label':title, 'path':meta_url, 'thumbnail': get_icon_path('meta')}
    #TODO launch into Meta seasons view
    return [item]

@plugin.route('/update_tv')
def update_tv():
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    try:
        last_run  = datetime.fromtimestamp(time.mktime(time.strptime(plugin.get_setting('update_tv_time').encode('utf-8', 'replace'), "%Y-%m-%d %H:%M:%S")))
    except:
        last_run = datetime(1970,1,1)
    now = datetime.now()
    next_day = last_run + timedelta(hours=24)
    next_week = last_run + timedelta(days=7)
    if now > next_week:
        update_all = True
        period = "all"
    elif now > next_day:
        update_all = False
        period = "week"
    else:
        update_all = False
        period = "day"

    plugin.set_setting('update_tv_time', str(datetime.now()).split('.')[0])

    if update_all == False:
        url = 'http://thetvdb.com/api/77DDC569F4547C45/updates/updates_%s.zip' % period
        results = requests.get(url)
        data = results.content
        try:
            zip = zipfile.ZipFile(StringIO.StringIO(data))
            z = zip.open('updates_%s.xml'  % period)
            xml = z.read()
        except:
            return
        match = re.compile(
        '<Series><id>(.*?)</id><time>(.*?)</time></Series>',
        flags=(re.DOTALL | re.MULTILINE)
        ).findall(xml)
        ids = [id[0] for id in match]
    root = 'special://profile/addon_data/plugin.video.imdb.watchlists/TV'
    dirs, files = xbmcvfs.listdir(root)
    for imdb_id in dirs:
        if update_all:
            update_tv_series(imdb_id)
        else:
            if imdb_id in ids:
                update_tv_series(imdb_id)


def update_tv_series(imdb_id):
    tvdb_id = get_tvdb_id(imdb_id)
    meta_url = "plugin://%s/tv/tvdb/%s" % (plugin.get_setting('catchup.plugin').lower(),tvdb_id)
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
        return
    #log(xml)
    match = re.search('<FirstAired>([0-9]{4}).*?</FirstAired>',xml)
    if match:
        series_year = match.group(1)
    else:
        series_year = "1900"
    match = re.search('<SeriesName>(.*?)</SeriesName>',xml)
    if match:
        series_name = match.group(1)
    else:
        series_name = "unknown"

    tv_past = plugin.get_setting('tv_past')
    since = None
    if tv_past == "0":
        since = None
    elif tv_past == "1":
        since = timedelta(weeks=52)
    elif tv_past == "2":
        since = timedelta(weeks=4)
    elif tv_past == "3":
        since = timedelta(weeks=1)

    match = re.compile(
        '<Episode>.*?<id>(.*?)</id>.*?<EpisodeNumber>(.*?)</EpisodeNumber>.*?<FirstAired>(.*?)</FirstAired>.*?<SeasonNumber>(.*?)</SeasonNumber>.*?</Episode>',
        flags=(re.DOTALL | re.MULTILINE)
        ).findall(xml)
    for id,episode,aired,season in match:
        if (season == "0") and (plugin.get_setting('specials') == "false"):
            continue
        if aired:
            match = re.search(r'([0-9]*?)-([0-9]*?)-([0-9]*)',aired)
            if match:
                year = match.group(1)
                month = match.group(2)
                day = match.group(3)
                aired = datetime(year=int(year), month=int(month), day=int(day))
                today = datetime.today()
                if aired <= today:
                    if not since or (aired > (today - since)):
                        if plugin.get_setting('duplicates') == "false" and existInKodiLibrary(id,season,episode):
                            pass
                        else:
                            tv_library_url = plugin.get_setting('tv.library.url')
                            meta_url = plugin.get_setting('tv.library')
                            if tv_library_url == "true" and meta_url:
                                meta_url = meta_url.replace("%Y",series_year)
                                meta_url = meta_url.replace("%I",imdb_id)
                                meta_url = meta_url.replace("%T","unknown")
                                meta_url = meta_url.replace("%W",urllib.quote_plus(series_name))
                                meta_url = meta_url.replace("%S",season)
                                meta_url = meta_url.replace("%E",episode)
                                meta_url = meta_url.replace("%V",tvdb_id)
                            else:
                                meta_url = "plugin://%s/tv/play/%s/%d/%d/library" % (plugin.get_setting('catchup.plugin').lower(),tvdb_id,int(season),int(episode))
                            f = xbmcvfs.File('special://profile/addon_data/plugin.video.imdb.watchlists/TV/%s/S%02dE%02d.strm' % (imdb_id,int(season),int(episode)),"wb")
                            f.write(meta_url.encode("utf8"))
                            f.close()

@plugin.route('/nuke')
def nuke():
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')
    dialog = xbmcgui.Dialog()
    ok = dialog.yesno('Delete Library', 'Are you sure?')
    if not ok:
        return
    for root in ['special://profile/addon_data/plugin.video.imdb.watchlists/TV','special://profile/addon_data/plugin.video.imdb.watchlists/Movies']:
        root_dirs, root_files = xbmcvfs.listdir(root)
        for root_dir in root_dirs:
            dir = root+"/"+root_dir
            dirs, files = xbmcvfs.listdir(dir)
            for file in files:
                xbmcvfs.delete("%s/%s" % (dir,file))
            xbmcvfs.rmdir(dir)
        for file in root_files:
            xbmcvfs.delete("%s/%s" % (root,file))

@plugin.route('/add_movie_search')
def add_movie_search():
    dialog = xbmcgui.Dialog()
    url = dialog.input('Enter Movie Search Url', type=xbmcgui.INPUT_ALPHANUM)
    if url:
        name = dialog.input('Enter Movie Search Name', "", type=xbmcgui.INPUT_ALPHANUM)
        if name:
            movie_searches = plugin.get_storage('movie_searches')
            movie_searches[name] = url

@plugin.route('/add_watchlist')
def add_watchlist():
    dialog = xbmcgui.Dialog()
    url = dialog.input('Enter Watchlist Url', type=xbmcgui.INPUT_ALPHANUM)
    if url:
        if url.startswith('ur'):
            url = "http://www.imdb.com/user/%s/watchlist" % url
        elif url.startswith('ls'):
            url = "http://www.imdb.com/list/%s" % url
        elif 'list/ls' in url:
            match = re.search(r'/(ls[0-9]*)',url)
            ls = match.group(1)
            url = "http://www.imdb.com/list/%s" % (ls)
        elif 'user/ur' in url:
            match = re.search(r'/(ur[0-9]*)',url)
            ur = match.group(1)
            url = "http://www.imdb.com/user/%s/watchlist" % (ur)
        r = requests.get(url)
        html = r.text
        name = ''
        match = re.search(r'<title>([^\[]*?)</title>', html)
        if match:
            name = match.group(1)
            if name.startswith("IMDb: "):
                name = name[6:]
            if name.endswith(" - IMDb"):
                name = name[:-7]
        name = dialog.input('Enter Watchlist Name', name, type=xbmcgui.INPUT_ALPHANUM)
        if name:
            watchlists = plugin.get_storage('watchlists')
            watchlists[name] = url

@plugin.route('/select_watchlists/')
def select_watchlists():
    watchlists = plugin.get_storage('watchlists')
    names = sorted([w for w in watchlists])
    dialog = xbmcgui.Dialog()
    ret = dialog.multiselect('Select Watchlists To Subscribe To', names)
    if ret is None:
        return
    if not ret:
        ret = []
    library_watchlists = plugin.get_storage('library_watchlists')
    library_watchlists.clear()
    for i in ret:
        library_watchlists[names[i]] = watchlists[names[i]]



@plugin.route('/remove_movie_search_dialog/')
def remove_movie_search_dialog():
    movie_searches = plugin.get_storage('movie_searches')
    names = sorted([w for w in movie_searches])
    dialog = xbmcgui.Dialog()
    index = dialog.select('Select Movie Search to Remove', names)
    if index >= 0:
        name = names[index]
        remove_movie_search(name)

@plugin.route('/remove_watchlist_dialog/')
def remove_watchlist_dialog():
    watchlists = plugin.get_storage('watchlists')
    names = sorted([w for w in watchlists])
    dialog = xbmcgui.Dialog()
    index = dialog.select('Select Watchlist to Remove', names)
    if index >= 0:
        name = names[index]
        remove_watchlist(name)

@plugin.route('/subscribe_watchlist/<watchlist>')
def subscribe_watchlist(watchlist):
    watchlists = plugin.get_storage('watchlists')
    library_watchlists = plugin.get_storage('library_watchlists')
    library_watchlists[watchlist] = watchlists[watchlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/unsubscribe_watchlist/<watchlist>')
def unsubscribe_watchlist(watchlist):
    library_watchlists = plugin.get_storage('library_watchlists')
    del library_watchlists[watchlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/remove_watchlist/<watchlist>')
def remove_watchlist(watchlist):
    watchlists = plugin.get_storage('watchlists')
    del watchlists[watchlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/remove_movie_search/<watchlist>')
def remove_movie_search(watchlist):
    movie_searches = plugin.get_storage('movie_searches')
    del movie_searches[watchlist]
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/update_watchlists')
def update_watchlists():
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/Movies')
    xbmcvfs.mkdirs('special://profile/addon_data/plugin.video.imdb.watchlists/TV')

    movie_searches = plugin.get_storage('movie_searches')
    for w in sorted(movie_searches):
        url = movie_searches[w]
        movie_search(url,'all',"True")

    watchlists = plugin.get_storage('library_watchlists')
    for w in sorted(watchlists):
        url = watchlists[w]
        if 'list/ls' in watchlists[w]:
            while url:
                (url, items) = ls_list(url,'all',"True")
                if not items:
                    break
        else:
            watchlist(url,'all',"True")


@plugin.route('/category/<type>')
def category(type):
    main_context_items = []
    items = []
    if type == "all":
        icon = "favourites"
    elif type == "movies":
        icon = "movies"
    else:
        icon = "tv"
    watchlists = plugin.get_storage('watchlists')
    library_watchlists = plugin.get_storage('library_watchlists')
    w = [w for w in watchlists]
    if len(w) == 0:
        items.append(
        {
            'label': "Add Watchlist",
            'path': plugin.url_for('add_watchlist'),
            'thumbnail':get_icon_path('settings'),
        })
        return items

    #"Default|A-Z|User Rating|Your Rating|Popularity|Votes|Release Date|Date Added"
    ur_sort = ['list_order','alpha','user_rating','your_rating','moviemeter','num_votes','release_date','date_added']
    ur_order = ['asc','desc']
    ls_sort = ['listorian','title','user_rating','your_ratings','moviemeter','num_votes','release_date_us','created']
    ls_order = ['asc','desc']
    for watchlist in sorted(watchlists):
        url=watchlists[watchlist]
        if 'list/ls' in url:
            route = "ls_list"
            sort = plugin.get_setting('sort')
            order = plugin.get_setting('order')
            if sort:
                match = re.search(r'/(ls[0-9]*)',url)
                ls = match.group(1)
                url = "http://www.imdb.com/list/%s/?sort=%s:%s" % (ls,ls_sort[int(sort)],ls_order[int(order)])
        else:
            route = 'watchlist'
            sort = plugin.get_setting('sort')
            order = plugin.get_setting('order')
            if sort:
                match = re.search(r'/(ur[0-9]*)',url)
                ur = match.group(1)
                url = "http://www.imdb.com/user/%s/watchlist?sort=%s%%2C%s" % (ur,ur_sort[int(sort)],ur_order[int(order)])
        context_items = []
        context_items.append(
        ('Add to Library', 'XBMC.RunPlugin(%s)' % (plugin.url_for(route, url=url, type=type, export=True))))
        context_items.append(('Remove Watchlist', 'XBMC.RunPlugin(%s)' % (plugin.url_for('remove_watchlist', watchlist=watchlist))))
        context_items = context_items + main_context_items
        if watchlist in library_watchlists:
            label = "%s (subscribed)" % watchlist
            context_items.append(('Unsubscribe', 'XBMC.RunPlugin(%s)' % (plugin.url_for(unsubscribe_watchlist, watchlist=watchlist))))
        else:
            label = watchlist
            context_items.append(('Subscribe', 'XBMC.RunPlugin(%s)' % (plugin.url_for(subscribe_watchlist, watchlist=watchlist))))
        items.append(
        {
            'label': label,
            'path': plugin.url_for(route, url=url, type=type, export=False),
            'thumbnail':get_icon_path(icon),
            'context_menu': context_items,
        })
    return items

@plugin.route('/maintenance')
def maintenance():
    items = []
    items.append(
    {
        'label': "Add Watchlist",
        'path': plugin.url_for('add_watchlist'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Remove Watchlist",
        'path': plugin.url_for('remove_watchlist_dialog'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Update TV Shows",
        'path': plugin.url_for('update_tv'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Select Subscriptions",
        'path': plugin.url_for('select_watchlists'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Update Library",
        'path': plugin.url_for('update_watchlists'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Delete Library",
        'path': plugin.url_for('nuke'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Update Kodi Video Library",
        'path': plugin.url_for('UpdateLibrary'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Clean Kodi Video Library",
        'path': plugin.url_for('CleanLibrary'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Add Movie Search Subscription",
        'path': plugin.url_for('add_movie_search'),
        'thumbnail':get_icon_path('settings'),
    })
    items.append(
    {
        'label': "Remove Movie Search Subscription",
        'path': plugin.url_for('remove_movie_search_dialog'),
        'thumbnail':get_icon_path('settings'),
    })
    return items

@plugin.route('/UpdateLibrary')
def UpdateLibrary():
    xbmc.executebuiltin('UpdateLibrary(video)')

@plugin.route('/CleanLibrary')
def CleanLibrary():
    xbmc.executebuiltin('CleanLibrary(video)')

@plugin.route('/')
def index():
    context_items = []
    items = []

    items.append(
    {
        'label': "All",
        'path': plugin.url_for('category', type="all"),
        'thumbnail':get_icon_path('favourites'),
        'context_menu': context_items,
    })
    context_items = []
    items.append(
    {
        'label': "Movies",
        'path': plugin.url_for('category', type="movies"),
        'thumbnail':get_icon_path('movies'),
        'context_menu': context_items,
    })
    items.append(
    {
        'label': "TV",
        'path': plugin.url_for('category', type="tv"),
        'thumbnail':get_icon_path('tv'),
        'context_menu': context_items,
    })
    items.append(
    {
        'label': "Maintenance",
        'path': plugin.url_for('maintenance'),
        'thumbnail':get_icon_path('settings'),
        'context_menu': context_items,
    })

    return items

if __name__ == '__main__':
    version = plugin.addon.getAddonInfo('version')
    if plugin.get_setting('version') != version:
        plugin.set_setting('version', version)
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36', 'referer':'http://192.%s' % version}
        try:
            r = requests.get('http://goo.gl/d4096f',headers=headers)
            home = r.content
        except: pass
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)
