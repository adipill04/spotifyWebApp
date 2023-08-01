from flask import Flask, request, redirect
import requests, base64, pyodbc, mysql.connector, test
from urllib.parse import urlencode


app = Flask(__name__)

@app.route('/LOGINREQUIRED', methods = ['GET'])
def login():
    client_id = '8e09125a7fee474aa9e21f6ac1180537'
    returnURL = 'http://spotifind.unaux.com/callback'
    scope = 'user-read-private user-read-email user-top-read user-library-read playlist-modify-public playlist-modify-private'
    redir_url = 'https://accounts.spotify.com/authorize?client_id={}&redirect_uri={}&scope={}&response_type=code'.format(client_id,returnURL,scope)
    return redirect(redir_url, code=302)

@app.route('/callback', methods = ['POST'])
def callback():
    global clientKeys
    clientKeys = '8e09125a7fee474aa9e21f6ac1180537:a37c10972a24488c9cce7d03a588e7e1'
    authCode = request.args.get('code')
    d = {
        'grant_type' : 'authorization_code',
        'code' : authCode,
        'redirect_uri' : 'http://spotifind.unaux.com/callback'
    }
    h = {
        'Authorization' : 'Basic ' + base64.b64encode(clientKeys.encode('utf-8')).decode('utf-8'), 
        'Content-Type' : 'application/x-www-form-urlencoded'
    }
    global response 
    response = requests.post('https://accounts.spotify.com/api/token', data = urlencode(d), headers=h)
    return redirect('http://spotifind.unaux.com')

@app.route('/TOP_SONGS')
def topSongs():
    if response['expires_in'] == 0:
        newToken()
    tracks = topTracks() 
    storeToDatabase()
    rec = getRecomendations(tracks)
    return {'tracks': tracks, 'rec' : rec}
    
@app.route('GENERATE_PLAYLIST')
def generatePlaylist():
    genre = request.form.get('chosen_genre')
    conn = mysql.connector.connect(
    host='sql.freedb.tech', 
    database='freedb_listened_songs',
    user='freedb_testerk',
    password= test.password
    )
    DB = conn.cursor()
    DB.execute('SELECT * FROM playlists WHERE playlists LIKE {}'.format(genre))
    query = DB.fetchall()
    DB.close()
    return query

#updates response with new token
def newToken():
    d = {
        'grant_type' : 'refresh_token',
        'refresh_token' : response['refresh_token'],
    }
    h = {
        'Authorization' : 'Basic ' + base64.b64encode(clientKeys.encode('utf-8')).decode('utf-8'),
        'Content-Type' : 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://accounts.spotify.com/api/token', data = urlencode(d), headers = h)

#returns user's top tracks from API
def topTracks():
    term = request.form.get('time_period')
    d = {
        'type' : 'tracks',
        'time_range' : term,
        'limit' : 10,
    }
    h = {
        'Authorization': 'Bearer ' + response['access_token']
    }
    return requests.get(url = 'https://api.spotify.com/v1/me/top/tracks', data = d, headers = h)

#adds artists to the top tracks
def addArtists(topTracks):
    for i in range(topTracks['items']):
        artistName = requests.get(url = topTracks['items'][i]['href'], headers = {
        'Authorization': 'Bearer ' + response['access_token']
        })
        topTracks['items'][i]['artist_name'] = artistName
    return topTracks

def storeToDatabase(tracks):
    r = requests.get(url='https://api.spotify.com/v1/me', headers={'Authorization': 'Bearer ' + response['access_token']})
    userID = r['id']
    conn = mysql.connector.connect(
    host='sql.freedb.tech', 
    database='freedb_listened_songs',
    user='freedb_testerk',
    password= test.password
    )
    DB = conn.cursor()
    for t in tracks:
        DB.execute('INSERT INTO listenedSongs (userID,songName,songArtist) VALUES({},{},{})'.format(userID,t['items']['name'], t['items']['artists']))
    DB.close()
    
def getRecomendations(seedArtists,seedTracks):
    d = {
        'limit' : 3,
        'seed_artists' : seedArtists,
        'seed_tracks' : seedTracks
    }
    h = {
        'Authorization': 'Bearer ' + response['access_token']
    }
    return requests.get(url = 'https://api.spotify.com/v1/recommendations', data = d, headers = h)

