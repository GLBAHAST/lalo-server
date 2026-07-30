from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

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
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Crucial for Vercel: skip_download avoids filesystem and timeout issues
        ydl_opts = {
            'format': 'best',
            'skip_download': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            title = info.get('title', 'video')
            
        return jsonify({
            "success": True,
            "title": title,
            "download_url": video_url
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
