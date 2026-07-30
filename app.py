from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return {"status": "Lalo Backend is live and running!"}

@app.route("/api/fetch", methods=["POST"])
def fetch_media():
    data = request.json or {}
    url = data.get("url")
    
    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400

    try:
        ydl_opts = {
            'format': 'best',
            'skip_download': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            title = info.get('title', 'video')
            uploader = info.get('uploader', 'User')
            thumbnail = info.get('thumbnail', '')
            
        return jsonify({
            "success": True,
            "data": {
                "video_url": video_url,
                "audio_url": video_url,
                "video_ext": "mp4",
                "audio_ext": "mp3",
                "title": title,
                "uploader": uploader,
                "thumbnail": thumbnail,
                "http_headers": info.get('http_headers', {})
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/proxy", methods=["POST", "GET"])
def proxy_media():
    if request.method == "GET":
        target_url = request.args.get("url")
        headers = {}
    else:
        req_data = request.json or {}
        target_url = req_data.get("url")
        headers = req_data.get("headers", {})

    if not target_url:
        return "No URL provided", 400

    try:
        resp = requests.get(target_url, headers=headers, stream=True, timeout=15)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]

        return Response(generate(), status=resp.status_code, headers=response_headers)
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True)
