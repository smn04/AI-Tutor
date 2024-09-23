# lesson/app.py

from flask import Blueprint, render_template, request, jsonify, session
import wikipediaapi
import requests

# Create a Blueprint for the lesson module
lesson_bp = Blueprint('lesson', __name__, template_folder='templates')

def fetch_youtube_videos(search_query):
    """Fetch YouTube videos related to the search query"""
    youtube_api_key = 'AIzaSyD8ZIYTpYyDLSfi-4XFMEyGTVhHG7inqsg'  # Replace with your API key
    search_url = f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=5&q={search_query}&type=video&order=relevance&videoCaption=closedCaption&videoCategory=27&key={youtube_api_key}'

    response = requests.get(search_url)
    if response.status_code == 200:
        video_data = response.json()
        videos = []
        for item in video_data['items']:
            video_id = item['id']['videoId']
            video_title = item['snippet']['title']
            embed_url = f'https://www.youtube.com/embed/{video_id}'
            videos.append({'title': video_title, 'embed_url': embed_url})
        return videos
    else:
        return None

@lesson_bp.route('/')
def lesson_index():
    print("Executing lesson_index route")
    return render_template('learning_search.html')

@lesson_bp.route('/lesson_results', methods=['POST'])
def lesson_results():
    search_query = request.form['search_query']
    learning_style_mapping = {
        'v': 'visual',
        'a': 'visual',
        'r': 'read_write',
        'k': 'read_write'
    }
    
    user_learning_style = session['learning_style']
    learning_style=learning_style_mapping[user_learning_style]
    
    # Use Wikipedia API to fetch content
    wiki_wiki = wikipediaapi.Wikipedia('en', headers={'User-Agent': 'AITutor/1.0'})
    page = wiki_wiki.page(search_query)
    
    # Fetch content based on learning style
    if learning_style == 'read_write':
        
        # Use Pexels API to get an image related to the search query
        content = page.summary[:3000]  # Fetch up to 3000 characters
        last_full_stop_index = content.rfind('.')
        content = content[:last_full_stop_index + 1]
        pexels_api_key = 'UpOfH4AudTEoT7MpHWa8EekQZr7oV3DxUgKqIXUwZqdnYOXBtb45q8be'
        response = requests.get(f'https://api.pexels.com/v1/search?query={search_query}', headers={'Authorization': pexels_api_key})
        if response.status_code == 200:
            data = response.json()
            if 'photos' in data and data['photos']:
                image_url = data['photos'][0]['src']['medium']
            else:
                image_url = 'URL_TO_DEFAULT_IMAGE'  # URL to a default image if no image is found
        else:
            image_url = 'URL_TO_DEFAULT_IMAGE'  # URL to a default image in case of API error
        return render_template('results.html', search_query=search_query, content=content, image_url=image_url)
    elif learning_style == 'visual':
        videos = fetch_youtube_videos(search_query)
        if videos:
            return render_template('results_auditory.html', search_query=search_query, videos=videos)
        else:
            return render_template('results.html', search_query=search_query, content="No videos found")
    else:
        content = "Learning style not supported."
    
    return render_template('results.html', search_query=search_query, content=content)

