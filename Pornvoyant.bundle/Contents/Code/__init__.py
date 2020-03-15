try: #python3
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode
except: #python2
    from urllib2 import urlopen, Request
    from urllib import urlencode
from datetime import datetime
import json
import dateutil.parser as dateparser
import HTMLParser

def Start():
    #HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'
    HTTP.Headers['Accept-Encoding'] = 'gzip'

class Pornvoyant(Agent.Movies):
    name = 'Pornvoyant'
    languages = [Locale.Language.NoLanguage]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual=False):
        urlBase = 'https://xxctcg9z99.execute-api.us-east-1.amazonaws.com/dev/search/'
        sceneName=media.name

        if media.duration and media.duration>0:
            sceneDurationMinutes=int(media.duration)/1000/60

        Log("Searching for: "+sceneName)
        url=urlBase+sceneName
        # https://xxctcg9z99.execute-api.us-east-1.amazonaws.com/dev/search/SceneName?duration=13
        jsObj = urlopen(url).read()
        searchResults=json.loads(jsObj)

        if manual and not searchResults:
            # Pornvoyant searches selectively by default to help with
            # auto matching. If nothing is returned we can requery with the
            # show all trigger to broaden the search.
            Log("No results for: "+sceneName +". Rerunning with show all.")
            queryParms={'show':"all"}
            qsEncoded = urlencode(queryParms).encode('ascii')
            request = Request(url, qsEncoded)
            jsObj = urlopen(request).read()
            searchResults=json.loads(jsObj)

        if not manual:
            if len(searchResults)==1:
                searchResults[0]["score"] = 100
            elif len(searchResults)>1:
                bestScore = int(searchResults[0]["score"])
                secondBestScore = int(searchResults[1]["score"])
                if(bestScore-secondBestScore>10):
                    searchResults[0]["score"] = 100
                    searchResults= [searchResults[0]]

        for video in searchResults:
            identity=video["id"]
            title = video["Title"][0]
            site = video["Site"][0]
            displayTitle = "{0} ({1})".format(title,site) 
            if "Models" in video and len(video["Models"])>0:
                models = ",".join(video["Models"])
            
            if models:
                displayTitle = "{0} ({1}) ({2})".format(title,site,models) 
            else:
                displayTitle = "{0} ({1})".format(title,site) 

            try:
                date=dateparser().parse(video["ReleaseDate"]) 
            except Exception as ex:
                Log(ex)
                date=datetime.strptime("1900", '%Y')
                pass

            score=int(video["score"])
                        
            currResult = MetadataSearchResult(
                id=str(identity.encode('utf-8')),
                name=str(displayTitle.encode('utf-8')),
                year=str(date.year),
                lang=lang,
                score=score
            )
            if currResult not in results:
                results.Append(currResult)

    
    def update(self, metadata, media, lang, force=False):
        urlBase = 'https://xxctcg9z99.execute-api.us-east-1.amazonaws.com/dev/get/'
        videoId = metadata.id

        url=urlBase+videoId
        # https://xxctcg9z99.execute-api.us-east-1.amazonaws.com/dev/get/db0145649b9604fc
        Log("Requesting Metadata From: "+ url)
        jsObj = urlopen(url).read()
        data=json.loads(jsObj)

        # Get the date
        
        if "ReleaseDate" in data:
            try:
                Log("Trying to parse:" + data["ReleaseDate"])
                date=dateparser().parse(data["ReleaseDate"])
            except Exception as ex:
                Log(ex)
                date=None
                pass
            # Set the date and year if found.
            if date is not None:
                metadata.originally_available_at = date
                metadata.year = date.year

        # Get the title
        if "Title" in data:
            metadata.title = data["Title"][0]
        
        # Set the summary
        if "Description" in data:
            summary=data["Description"][0]
            metadata.summary = summary

        # Set series and add to collections
        metadata.collections.clear()
        if "Site" in data:
            site=data["Site"][0]
            try:
                metadata.collections.add(site)
            except:
                pass
        if "Series" in data:
            series=data["Series"]
            for currSeries in series:
                try:
                    metadata.collections.add(currSeries)
                except:
                    pass
        
        # Add the genres
        metadata.genres.clear()
        if "Genres" in data:
            genres = data["Genres"]
            for genre in genres:
                metadata.genres.add(genre)
        
        # Add the performers
        metadata.roles.clear()
        if "Models" in data:
            models=data["Models"]
            for model in models:
                # Create and populate role with actor's name
                try:
                    role = metadata.roles.new()
                    role.name=model
                    # TODO: Add actor photos as well
                    # photo="http://"+???
                    #role.photo=photo
                except:
                    pass

        # Add posters and fan art.
        if "Images" in data:
            images = data["Images"]
            for image in images:
                image=image.strip("/")
                if "http" not in image:
                    image="http://"+image
                if image not in metadata.posters.keys():
                    Log("Adding cover art from url: " + image)
                    referer = '/'.join(image.split('/')[:3])
                    Log("Requesting image using referer "+ referer)
                    metadata.posters[image]= Proxy.Media(HTTP.Request(image,headers={"Referer":referer}))
                    metadata.art[image]= Proxy.Media(HTTP.Request(image,headers={"Referer":referer}))