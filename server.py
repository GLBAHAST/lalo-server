import os

import json

from flask import Flask, request, jsonify, Response

from flask_cors import CORS

import yt_dlp

import requests



app = Flask(__name__)

CORS(app)



@app.route('/api/fetch', methods=['POST'])

def fetch_media():

    data = request.get_json()

    if not data or 'url' not in data:

        return jsonify({'error': 'URL is required'}), 400



    url = data['url']

    

    # --- TIKTOK SPECIFIC LOGIC (Using TikWM API for reliability) ---

    if 'tiktok.com' in url.lower():

        try:

            tikwm_url = 'https://www.tikwm.com/api/?url=' + url + '&hd=1'

            resp = requests.get(tikwm_url, timeout=10).json()

            if resp.get('code') == 0 and resp.get('data'):

                td = resp['data']

                

                # Helper for URLs

                def get_url(path):

                    if not path: return ''

                    if path.startswith('http'): return path

                    return 'https://www.tikwm.com' + path



                # Build unified response format

                response_data = {

                    'id': td.get('id', ''),

                    'title': td.get('title', ''),

                    'description': td.get('title', ''),

                    'thumbnail': get_url(td.get('cover', '')),

                    'duration': td.get('duration', 0),

                    'uploader': td.get('author', {}).get('unique_id', ''),

                    'extractor': 'tiktok',

                    'view_count': td.get('play_count', 0),

                    'like_count': td.get('digg_count', 0),

                    'comment_count': td.get('comment_count', 0),

                    'repost_count': td.get('share_count', 0),

                    

                    'video_url': get_url(td.get('hdplay') or td.get('play')),

                    'video_ext': 'mp4',

                    'video_width': 1080 if td.get('hdplay') else 720,

                    'video_height': 1920 if td.get('hdplay') else 1280,

                    

                    'audio_url': get_url(td.get('music')) if td.get('music') else None,

                    'audio_ext': 'mp3',

                    'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

                }

                return jsonify({'success': True, 'data': response_data})

        except Exception as e:

            print("TikWM Error:", e)

            # If it fails, let it fall through to yt-dlp as a backup

            pass



    # --- OTHER PLATFORMS (YouTube, Instagram, etc) using yt-dlp ---

    ydl_opts = {

        'quiet': True,

        'no_warnings': True,

        'extract_flat': False,

        'skip_download': True,

    }



    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=False)

            

            # Helper to safely get best format

            def get_best_format(formats, ext_filter=None, vcodec_filter=None, acodec_filter=None):

                best_f = None

                for f in formats:

                    if ext_filter and f.get('ext') != ext_filter: continue

                    if vcodec_filter and f.get('vcodec') == vcodec_filter: continue

                    if acodec_filter and f.get('acodec') == acodec_filter: continue

                    

                    if not best_f:

                        best_f = f

                    elif (f.get('width') or 0) > (best_f.get('width') or 0):

                        best_f = f

                return best_f



            formats = info.get('formats', [])

            

            # Video with Audio (often mp4)

            best_video = None

            # Some platforms (like YT) separate video and audio, so we might need formats that have both

            video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']

            if video_formats:

                best_video = max(video_formats, key=lambda f: f.get('width', 0) or 0, default=None)

            

            if not best_video:

                # Fallback to any video format if combined is not found easily

                best_video = max([f for f in formats if f.get('vcodec') != 'none'], key=lambda f: f.get('width', 0) or 0, default=None)



            # Audio only

            audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']

            best_audio = max(audio_formats, key=lambda f: f.get('abr', 0) or 0, default=None) if audio_formats else None



            # Standardize response

            response_data = {

                'id': info.get('id', ''),

                'title': info.get('title', ''),

                'description': info.get('description', ''),

                'thumbnail': info.get('thumbnail', ''),

                'duration': info.get('duration', 0),

                'uploader': info.get('uploader', ''),

                'extractor': info.get('extractor_key', '').lower(),

                'view_count': info.get('view_count', 0),

                'like_count': info.get('like_count', 0),

                'comment_count': info.get('comment_count', 0),

                'repost_count': info.get('repost_count', 0), # mapping for share count

                

                'video_url': best_video.get('url') if best_video else info.get('url'),

                'video_ext': best_video.get('ext') if best_video else info.get('ext', 'mp4'),

                'video_width': best_video.get('width') if best_video else info.get('width', 0),

                'video_height': best_video.get('height') if best_video else info.get('height', 0),

                

                'audio_url': best_audio.get('url') if best_audio else None,

                'audio_ext': best_audio.get('ext') if best_audio else None,

                'http_headers': info.get('http_headers', {}),

            }

            

            return jsonify({'success': True, 'data': response_data})



    except Exception as e:

        return jsonify({'error': str(e)}), 500



@app.route('/api/proxy', methods=['GET', 'POST'])

def proxy_download():

    if request.method == 'POST':

        data = request.get_json() or {}

        url = data.get('url')

        headers = data.get('headers', {})

    else:

        url = request.args.get('url')

        headers = {}



    if not url:

        return jsonify({'error': 'URL is required'}), 400

        

    # Optional: we can add standard headers if missing

    if 'User-Agent' not in headers:

        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'



    try:

        # In case tikwm gives a relative URL, ensure it's absolute

        if url.startswith('/'):

            url = 'https://www.tikwm.com' + url

            

        req = requests.get(url, headers=headers, stream=True, timeout=15)

        

        # Forward the stream to the client

        def generate():

            for chunk in req.iter_content(chunk_size=65536):

                if chunk:

                    yield chunk



        # Pass important headers back to client (like content-length)

        resp_headers = {}

        if 'content-length' in req.headers:

            resp_headers['Content-Length'] = req.headers['content-length']

        if 'content-type' in req.headers:

            resp_headers['Content-Type'] = req.headers['content-type']

            

        return Response(generate(), headers=resp_headers, status=req.status_code)

        

    except Exception as e:

        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)