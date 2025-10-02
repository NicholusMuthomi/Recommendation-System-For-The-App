import pickle
import pandas as pd
import streamlit as st
import requests
from datetime import datetime
from functools import lru_cache
import numpy as np

# Configuration
TMDB_API_KEY = "3c6714d4a34bc290692198aa8fc4c87a"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
PROFILE_BASE_URL = "https://image.tmdb.org/t/p/w185"
DEFAULT_POSTER = "https://via.placeholder.com/500x750?text=No+Poster+Available"
DEFAULT_PROFILE = "https://via.placeholder.com/185x278?text=No+Image+Available"

# Set page config
st.set_page_config(
    page_title=" Movie Recommender System",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    data = fetch_data(url)
    if data and 'poster_path' in data and data['poster_path']:
        return f"{POSTER_BASE_URL}{data['poster_path']}"
    return DEFAULT_POSTER


@st.cache_data(ttl=3600)
def fetch_cast_images(cast_id):
    url = f"https://api.themoviedb.org/3/person/{cast_id}?api_key={TMDB_API_KEY}"
    data = fetch_data(url)
    if data and 'profile_path' in data and data['profile_path']:
        return f"{PROFILE_BASE_URL}{data['profile_path']}"
    return DEFAULT_PROFILE

@st.cache_data(ttl=3600)
def fetch_movie_details(movie_id):
    # Fetch basic movie info
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    data = fetch_data(url)
    if not data:
        return None

    # Fetch credits
    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}"
    credits_data = fetch_data(credits_url)
    if not credits_data:
        credits_data = {'cast': [], 'crew': []}

    # Process crew
    crew_details = {
        'Director': [],
        'Producer': [],
        'Screenplay': [],
        'Director of Photography': [],
        'Editor': [],
        'Sound': [],
        'Production Design': [],
        'Casting': [],
        'Costume Design': [],
        'Original Music Composer': []
    }
    
    for member in credits_data.get('crew', []):
        job = member.get('job', '')
        name = member.get('name', '')
        
        if job == 'Director':
            crew_details['Director'].append(name)
        elif job == 'Producer':
            crew_details['Producer'].append(name)
        elif job in ['Screenplay', 'Writer']:
            crew_details['Screenplay'].append(name)
        elif job in ['Director of Photography', 'Cinematography']:
            crew_details['Director of Photography'].append(name)
        elif job == 'Editor':
            crew_details['Editor'].append(name)
        elif 'Sound' in job:
            crew_details['Sound'].append(name)
        elif job == 'Production Design':
            crew_details['Production Design'].append(name)
        elif job == 'Casting':
            crew_details['Casting'].append(name)
        elif job == 'Costume Design':
            crew_details['Costume Design'].append(name)
        elif job == 'Original Music Composer':
            crew_details['Original Music Composer'].append(name)
    
    # Process cast with images
    cast_details = []
    for actor in credits_data.get('cast', [])[:5]:  # Top 5 cast members
        cast_details.append({
            'id': actor.get('id'),
            'name': actor.get('name', 'N/A'),
            'character': actor.get('character', 'N/A'),
            'profile_path': actor.get('profile_path')
        })
    
    return {
        'budget': data.get('budget', 'N/A'),
        'popularity': data.get('popularity', 'N/A'),
        'runtime': data.get('runtime', 'N/A'),
        'revenue': data.get('revenue', 'N/A'),
        'production_companies': [company['name'] for company in data.get('production_companies', [])],
        'production_countries': [country['name'] for country in data.get('production_countries', [])],
        'origin_country': data.get('origin_country', ['N/A']),
        'genres': [genre['name'] for genre in data.get('genres', [])],
        'homepage': data.get('homepage', 'N/A'),
        'overview': data.get('overview', 'No overview available'),
        'tagline': data.get('tagline', 'No tagline available'),
        'status': data.get('status', 'N/A'),
        'release_date': data.get('release_date', 'N/A'),
        'vote_average': data.get('vote_average', 'N/A'),
        'vote_count': data.get('vote_count', 'N/A'),
        'imdb_id': data.get('imdb_id', 'N/A'),
        'crew': crew_details,
        'cast': cast_details,
        'poster_path': data.get('poster_path')
    }

@st.cache_data(ttl=3600)
def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommendations = []
    
    for i in distances[1:6]:  # Top 5 recommendations
        movie_id = movies.iloc[i[0]].movie_id
        details = fetch_movie_details(movie_id)
        if details:
            recommendations.append({
                'title': movies.iloc[i[0]].title,
                'poster': f"{POSTER_BASE_URL}{details['poster_path']}" if details['poster_path'] else DEFAULT_POSTER,
                'details': details
            })
    
    return recommendations

@st.cache_data(ttl=3600)
def fetch_movie_reviews(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/reviews?api_key={TMDB_API_KEY}"
    data = fetch_data(url)
    if not data or 'results' not in data:
        return []
    return data['results']

# UI Components

def display_movie_details(movie_title, details):
    # CSS for the movie details section
    st.markdown("""
    <style>
    .movie-hero {
        background: linear-gradient(135deg, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 100%);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 30px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .movie-title-section {
        text-align: center;
        margin-bottom: 30px;
        padding: 20px;
        background: linear-gradient(135deg, #E50914 0%, #B81D24 100%);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .movie-title-main {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    .movie-meta {
        color: rgba(255, 255, 255, 0.8);
        font-size: 1.1rem;
        display: flex;
        justify-content: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    
    .rating-section {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin: 20px 0;
        flex-wrap: wrap;
    }
    
    .rating-card {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        padding: 15px 20px;
        text-align: center;
        min-width: 120px;
        backdrop-filter: blur(10px);
    }
    
    .rating-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 5px;
    }
    
    .rating-value {
        color: #FFD700;
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    .rating-extra {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.8rem;
        margin-top: 2px;
    }
    
    .tagline {
        color: ##E50914;
        font-size: 1.2rem;
        font-style: italic;
        text-align: center;
        margin: 20px 0;
        padding: 15px;
        background: rgba(100, 181, 246, 0.1);
        border-radius: 10px;
        border-left: 4px solid ##E50914;
    }
    
    .overview {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1rem;
        line-height: 1.6;
        margin: 20px 0;
        padding: 20px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .genre-section {
        margin: 20px 0;
        text-align: center;
    }
    
    .genre-tag {
        display: inline-block;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        margin: 5px;
        transition: all 0.3s ease;
    }
    
    .genre-tag:hover {
        background: rgba(246, 100, 100, 0.2);
        border-color: #E50914;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    
    .stat-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        margin-bottom: 5px;
        font-weight: 500;
    }
    
    .stat-value {
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
    }
    
    .action-buttons {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin: 20px 0;
        flex-wrap: wrap;
    }
    
    .action-btn {
        display: inline-block;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        margin: 5px;
        transition: all 0.3s ease;
    }
    
    .action-btn:hover {
        text-decoration: none;
        color: white;
    }
    
    .action-btn.secondary {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .action-btn.secondary:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    
    @media (max-width: 768px) {
        .movie-title-main {
            font-size: 2rem;
        }
        
        .movie-meta {
            flex-direction: column;
            gap: 10px;
        }
        
        .rating-section {
            flex-direction: column;
            align-items: center;
        }
        
        .stats-grid {
            grid-template-columns: 1fr;
        }
        
        .action-buttons {
            flex-direction: column;
            align-items: center;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Format data
    runtime_str = f"{details['runtime']} min" if details['runtime'] != 'N/A' else "N/A"
    budget_str = f"${details['budget']:,}" if details['budget'] != 'N/A' and details['budget'] > 0 else "N/A"
    revenue_str = f"${details['revenue']:,}" if details['revenue'] != 'N/A' and details['revenue'] > 0 else "N/A"
    release_year = details['release_date'][:4] if details['release_date'] != 'N/A' else "N/A"
    
    # Main container
    st.markdown('<div class="movie-hero">', unsafe_allow_html=True)
    
    # Title section
    st.markdown(f"""
    <div class="movie-title-section">
        <h1 class="movie-title-main">{movie_title}</h1>
        <div class="movie-meta">
            <span>{release_year}</span>
            <span>•</span>
            <span>{details['status']}</span>
            <span>•</span>
            <span>{runtime_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for poster and info
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display poster
        poster_url = f"{POSTER_BASE_URL}{details['poster_path']}" if details['poster_path'] else DEFAULT_POSTER
        st.image(poster_url, use_container_width=True)
    
    with col2:
        # Ratings section
        st.markdown(f"""
        <div class="rating-section">
            <div class="rating-card">
                <div class="rating-label">IMDB Rating</div>
                <div class="rating-value">⭐ {details['vote_average']}/10</div>
                <div class="rating-extra">{details['vote_count']:,} votes</div>
            </div>
            <div class="rating-card">
                <div class="rating-label">Popularity</div>
                <div class="rating-value">📈 {details['popularity']:.0f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Tagline
        if details['tagline'] != 'No tagline available':
            st.markdown(f'<div class="tagline">"{details["tagline"]}"</div>', unsafe_allow_html=True)
        
        # Overview
        st.markdown(f'<div class="overview">{details["overview"]}</div>', unsafe_allow_html=True)
        
        # Genres
        if details['genres']:
            genre_html = ''.join([f'<span class="genre-tag">{genre}</span>' for genre in details['genres']])
            st.markdown(f'<div class="genre-section">{genre_html}</div>', unsafe_allow_html=True)
    
    # Stats section
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">💰 Budget</div>
            <div class="stat-value">{budget_str}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">💵 Revenue</div>
            <div class="stat-value">{revenue_str}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">📅 Release Date</div>
            <div class="stat-value">{details['release_date']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">⏱️ Runtime</div>
            <div class="stat-value">{runtime_str}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">🌍 Origin</div>
            <div class="stat-value">{', '.join(details['origin_country'])}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">🏢 Production</div>
            <div class="stat-value">{', '.join(details['production_companies'][:2]) if details['production_companies'] else 'N/A'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    imdb_url = f"https://www.imdb.com/title/{details['imdb_id']}/" if details['imdb_id'] != 'N/A' else "#"
    homepage_url = details['homepage'] if details['homepage'] != 'N/A' else "#"
    
    st.markdown(f"""
    <div class="action-buttons">
        <a href="{imdb_url}" class="action-btn" target="_blank">
            ▶️ Watch Trailer
        </a>
        <a href="{homepage_url}" class="action-btn secondary" target="_blank">
            🌐 Official Site
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    
    # Close reviews section
    st.markdown('</div>', unsafe_allow_html=True)

def display_cast(cast_details):
    cast_css = """
    <style>
    .cast-crew-section {
        margin: 40px 0;
        padding: 0;
        background: transparent;
    }
    
    .tabs-container {
        margin-bottom: 30px;
    }
    
    .tabs-nav {
        display: flex;
        gap: 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 4px;
        margin-bottom: 30px;
    }
    
    .tab-button {
        flex: 1;
        padding: 12px 20px;
        background: transparent;
        color: rgba(255, 255, 255, 0.7);
        border: none;
        border-radius: 6px;
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
    }
    
    .tab-button.active {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        font-weight: 600;
    }
    
    .tab-button:hover {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.9);
    }
    
    .cast-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 20px;
        margin: 0;
        padding: 0;
    }
    
    .cast-member {
        text-align: center;
        background: transparent;
        padding: 0;
    }
    
    .cast-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
    }
    
    .cast-name {
        color: white;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 4px;
        line-height: 1.2;
        text-align: center;
    }
    
    .cast-character {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.8rem;
        font-style: normal;
        line-height: 1.2;
        margin: 0;
        text-align: center;
    }
    
    .cast-placeholder {
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.4);
        font-size: 2.5rem;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .cast-grid {
            grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
            gap: 15px;
        }
        
        .cast-name {
            font-size: 0.85rem;
        }
        
        .cast-character {
            font-size: 0.75rem;
        }
        
        .tab-button {
            padding: 10px 16px;
            font-size: 0.9rem;
        }
    }
    
    @media (max-width: 480px) {
        .cast-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        
        .cast-name {
            font-size: 0.8rem;
        }
        
        .cast-character {
            font-size: 0.7rem;
        }
        
        .tab-button {
            padding: 8px 12px;
            font-size: 0.85rem;
        }
    }
    </style>
    """
    
    st.markdown(cast_css, unsafe_allow_html=True)
    
    if not cast_details:
        st.info("Cast information is not available for this movie.")
        return
    
    # Main cast container
    st.markdown('<div class="cast-section">', unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="cast-header">
        <h2 class="cast-title">
             Main Cast
        </h2>
        <p class="cast-subtitle">
            Meet the talented actors who brought this story to life
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if not cast_details:
        st.info("Cast information is not available for this movie.")
        return
    
    # Create columns for cast members
    cols = st.columns(5, gap="medium")
    
    for i, actor in enumerate(cast_details[:5]):  # Show top 5 cast members
        with cols[i]:
            # Profile image with fallback
            if actor.get('profile_path'):
                profile_url = f"{PROFILE_BASE_URL}{actor['profile_path']}"
            else:
                profile_url = DEFAULT_PROFILE
            
            # Create a container for styling
            with st.container():
                # Display profile image
                st.image(profile_url, use_container_width=True)
                
                # Actor name with styling
                st.markdown(f"""
                <div style="
                    text-align: center;
                    margin: 10px 0;
                    padding: 15px;
                    background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 15px;
                    backdrop-filter: blur(15px);
                    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
                ">
                    <div style="
                        color: white;
                        font-size: 1.1rem;
                        font-weight: bold;
                        margin-bottom: 8px;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
                    ">
                        {actor.get('name', 'N/A')}
                    </div>
                    <div style="
                        color: rgba(255, 255, 255, 0.8);
                        font-size: 0.9rem;
                        font-style: italic;
                        padding: 6px 10px;
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                    ">
                        as {actor.get('character', 'N/A')}
                    </div>
                    <div style="
                        margin-top: 10px;
                        display: inline-block;
                        background: linear-gradient(135deg, #d61a1a 0%, #d61a1a 100%);
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 0.7rem;
                        font-weight: bold;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    ">
                        Main Cast
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Additional cast info in an expander
    if len(cast_details) > 12:
        with st.expander(f"View all {len(cast_details)} cast members", expanded=False):
            # Create a more detailed view for remaining cast
            remaining_cast = cast_details[12:]
            
            # Display remaining cast in a grid
            remaining_html = '<div class="cast-grid">'
            
            for actor in remaining_cast:
                if actor.get('profile_path'):
                    profile_url = f"{PROFILE_BASE_URL}{actor['profile_path']}"
                    image_content = f'<img src="{profile_url}" class="cast-image" alt="{actor.get("name", "N/A")}" />'
                else:
                    image_content = '<div class="cast-placeholder">👤</div>'
                
                remaining_html += f'''
                <div class="cast-member">
                    <div class="cast-image-wrapper">
                        {image_content}
                    </div>
                    <div class="cast-name">{actor.get('name', 'N/A')}</div>
                    <div class="cast-character">{actor.get('character', 'N/A')}</div>
                </div>
                '''
            
            remaining_html += '</div>'
            st.markdown(remaining_html, unsafe_allow_html=True)

def display_crew(crew_details):
    """Minimal and clean crew display"""

    st.markdown("""
    <style>
    .crew-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .crew-title {
        color: white;
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 20px;
        text-align: center;
        padding-bottom: 10px;
        border-bottom: 2px solid rgba(255, 255, 255, 0.2);
    }
    
    .crew-department {
        margin: 15px 0;
        padding: 12px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        border-left: 3px solid #667eea;
    }
    
    .department-name {
        color: #667eea;
        font-weight: bold;
        font-size: 1rem;
        margin-bottom: 8px;
    }
    
    .crew-members {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.9rem;
        line-height: 1.4;
    }
    
    .no-crew {
        color: rgba(255, 255, 255, 0.6);
        text-align: center;
        font-style: italic;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    st.markdown('<div class="crew-container">', unsafe_allow_html=True)
    
    # Simple header
    st.markdown('<h3 class="crew-title"> Crew</h3>', unsafe_allow_html=True)
    
    # Check if we have crew data
    has_crew = any(members for members in crew_details.values())
    
    if not has_crew:
        st.markdown('<div class="no-crew">No crew information available</div>', unsafe_allow_html=True)
    else:
        # Display each department with crew members
        for department, members in crew_details.items():
            if members:  # Only show departments with crew members
                st.markdown(f"""
                <div class="crew-department">
                    <div class="department-name">{department}</div>
                    <div class="crew-members">{', '.join(members)}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def display_recommendations(recommendations):
    st.markdown("""
    <style>
    .recommendations-section {
        margin: 40px 0;
        padding: 30px;
        background: linear-gradient(135deg, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 100%);
        border-radius: 20px;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
    }
    
    .recommendations-header {
        text-align: center;
        margin-bottom: 30px;
        padding: 20px;
        background: linear-gradient(135deg, #E50914 0%, #B81D24 100%);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
                
    
    .recommendations-title {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
    }
    
    .recommendations-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-top: 10px;
        font-style: italic;
    }
    
    .movie-card-simple {
        background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .movie-card-simple:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
        border-color: rgba(102, 126, 234, 0.5);
    }
    
    .movie-title-simple {
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        text-align: center;
    }
    
    .movie-meta-simple {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 10px 0;
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 0.9rem;
    }
    
    .movie-rating-simple {
        color: #FFD700;
        font-weight: bold;
    }
    
    .movie-year-simple {
        color: rgba(255, 255, 255, 0.8);
        background: rgba(255, 255, 255, 0.1);
        padding: 4px 8px;
        border-radius: 10px;
    }
    
    .movie-overview-simple {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.9rem;
        line-height: 1.4;
        margin: 10px 0;
    }
    
    .movie-genres-simple {
        margin: 10px 0;
        text-align: center;
    }
    
    .genre-pill-simple {
        display: inline-block;
        background: rgba(102, 126, 234, 0.3);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
        border: 1px solid rgba(102, 126, 234, 0.4);
    }
    
    .movie-actions-simple {
        display: flex;
        gap: 10px;
        justify-content: center;
        margin-top: 15px;
    }
    
    .action-link-simple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .action-link-simple:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        text-decoration: none;
        color: white;
    }
    
    .action-link-simple.secondary {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .action-link-simple.secondary:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main recommendations container
    st.markdown('<div class="recommendations-section">', unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="recommendations-header">
        <h2 class="recommendations-title">
            🍿 Recommended Movies
        </h2>
        <p class="recommendations-subtitle">
           See what to watch after this movie
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create movie cards using Streamlit columns and components
    st.markdown("###  What to Watch Next")
    
    cols = st.columns(5, gap="medium")
    
    for i, movie in enumerate(recommendations):
        with cols[i]:
            # Display movie poster
            st.image(movie['poster'], use_container_width=True)
            
            # Movie title
            st.markdown(f"**{movie['title']}**")
            
            # Movie rating and year
            release_year = movie['details']['release_date'][:4] if movie['details']['release_date'] != 'N/A' else "N/A"
            st.markdown(f"⭐ {movie['details']['vote_average']}/10 • {release_year}")
            
            # Genres (first 2)
            if movie['details']['genres']:
                genres_text = " • ".join(movie['details']['genres'][:2])
                st.caption(f"{genres_text}")
            
            # Show details in expander
            with st.expander("More Details"):
                # Overview
                st.write("**Overview:**")
                overview = movie['details']['overview']
                if len(overview) > 200:
                    overview = overview[:200] + "..."
                st.write(overview)
                
                # Additional info
                runtime_str = f"{movie['details']['runtime']} min" if movie['details']['runtime'] != 'N/A' else "N/A"
                budget_str = f"${movie['details']['budget']:,}" if movie['details']['budget'] != 'N/A' and movie['details']['budget'] > 0 else "N/A"
                
                st.write(f"**Runtime:** {runtime_str}")
                st.write(f"**Budget:** {budget_str}")
                st.write(f"**Status:** {movie['details']['status']}")
                
                # Tagline
                if movie['details']['tagline'] != 'No tagline available':
                    st.info(f"*\"{movie['details']['tagline']}\"*")
                
                # Action buttons
                imdb_url = f"https://www.imdb.com/title/{movie['details']['imdb_id']}/" if movie['details']['imdb_id'] != 'N/A' else "#"
                homepage_url = movie['details']['homepage'] if movie['details']['homepage'] != 'N/A' else "#"
                
                col1, col2 = st.columns(2)
                with col1:
                    if movie['details']['imdb_id'] != 'N/A':
                        st.markdown(f"[▶️ Trailer]({imdb_url})")
                with col2:
                    if movie['details']['homepage'] != 'N/A':
                        st.markdown(f"[🌐 Website]({homepage_url})")

def display_reviews(reviews):
    st.markdown("""
    <style>
    .reviews-section {
        margin: 40px 0;
        padding: 0;
        background: transparent;
    }
    
    .reviews-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 30px;
        padding: 0;
    }
    
    .reviews-title {
        color: white;
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0;
        text-align: left;
    }
    
    .reviews-count {
        color: rgba(255, 255, 255, 0.7);
        font-size: 1rem;
        margin: 0;
    }
    
    .rating-overview {
        display: flex;
        align-items: center;
        gap: 40px;
        margin-bottom: 30px;
        padding: 25px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .rating-score-section {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    
    .rating-number {
        color: white;
        font-size: 3.5rem;
        font-weight: 700;
        margin: 0;
        line-height: 1;
    }
    
    .rating-stars {
        display: flex;
        gap: 3px;
        margin-bottom: 8px;
    }
    
    .star {
        color: #FFD700;
        font-size: 1.4rem;
    }
    
    .star.empty {
        color: rgba(255, 255, 255, 0.2);
    }
    
    .rating-text {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.85rem;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    .review-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
    }
    
    .review-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.15);
    }
    
    .review-header-info {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 15px;
    }
    
    .reviewer-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .reviewer-info {
        flex: 1;
    }
    
    .reviewer-name {
        color: white;
        font-weight: 600;
        font-size: 0.95rem;
        margin: 0 0 3px 0;
    }
    
    .review-date {
        color: rgba(255, 255, 255, 0.5);
        font-size: 0.75rem;
        margin: 0;
    }
    
    .review-rating {
        display: flex;
        align-items: center;
        gap: 5px;
        color: #FFD700;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .review-content {
        color: rgba(255, 255, 255, 0.85);
        line-height: 1.6;
        font-size: 0.9rem;
        margin: 0;
    }
    
    .no-reviews {
        text-align: center;
        padding: 50px 20px;
        color: rgba(255, 255, 255, 0.5);
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .no-reviews h4 {
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 10px;
        font-weight: 600;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .rating-overview {
            flex-direction: column;
            gap: 20px;
            text-align: center;
            padding: 20px;
        }
        
        .reviews-header {
            flex-direction: column;
            gap: 15px;
            align-items: flex-start;
        }
        
        .rating-number {
            font-size: 2.8rem;
        }
        
        .rating-score-section {
            gap: 15px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Calculate ratings
    if reviews:
        ratings = [review.get('author_details', {}).get('rating', 0) for review in reviews 
                  if review.get('author_details', {}).get('rating') is not None]
        
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            rating_count = len(reviews)
        else:
            avg_rating = 0
            rating_count = 0
    else:
        avg_rating = 0
        rating_count = 0
    
    # Reviews section container
    st.markdown('<div class="reviews-section">', unsafe_allow_html=True)
    
    # Header with title
    st.markdown(f"""
    <div class="reviews-header">
        <div>
            <h2 class="reviews-title">Reviews</h2>
            <p class="reviews-count">{rating_count}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Rating overview section
    stars_html = ""
    for i in range(1, 6):
        if i <= avg_rating/2:  # Convert 10-point scale to 5-point for display
            stars_html += '<span class="star">★</span>'
        else:
            stars_html += '<span class="star empty">★</span>'
    
    st.markdown(f"""
    <div class="rating-overview">
        <div class="rating-score-section">
            <h1 class="rating-number">{avg_rating:.1f}</h1>
            <div>
                <div class="rating-stars">{stars_html}</div>
                <p class="rating-text">{rating_count} ratings</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Rating distribution bar chart
    if reviews and ratings:
        rating_counts = {i: 0 for i in range(1, 11)}
        for rating in ratings:
            if 1 <= rating <= 10:
                rating_counts[int(rating)] += 1
        
    # Featured reviews section
    st.markdown('<div class="featured-reviews-section">', unsafe_allow_html=True)
    st.markdown('<h3 class="featured-title">Featured reviews</h3>', unsafe_allow_html=True)
    
    # Filter and sort reviews
    valid_reviews = [r for r in reviews if r.get('content') and r.get('author_details', {}).get('rating') is not None]
    
    if not valid_reviews:
        st.markdown("""
        <div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.7);">
            <h4>No featured reviews available</h4>
            <p>Be the first to write a review for this movie!</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sort by rating and take top reviews
    featured_reviews = sorted(valid_reviews, 
                             key=lambda x: x['author_details']['rating'], 
                             reverse=True)[:2]
    
    # Display reviews with new styling
    for review in featured_reviews[:6]:  # Show top 6 reviews
        author = review.get('author', 'Anonymous')
        rating = review.get('author_details', {}).get('rating', 0)
        content = review.get('content', 'No content available')
        created_at = review.get('created_at', '')
        
        # Format date
        if created_at:
            try:
                date_obj = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                formatted_date = date_obj.strftime('%B %d, %Y')
            except:
                formatted_date = created_at
        else:
            formatted_date = "Date not available"
        
        # Truncate content
        if len(content) > 5000:
            content_display = content[:5000] + "..."
        else:
            content_display = content
        
        # Get first letter of author name for avatar
        avatar_letter = author[0].upper() if author and author != 'Anonymous' else 'A'
        
        # Create star rating for individual review
        review_stars = ""
        for i in range(1, 6):
            if i <= rating/2:  # Convert 10-point scale to 5-point
                review_stars += '★'
            else:
                review_stars += '☆'
        
        st.markdown(f"""
        <div class="review-card">
            <div class="review-header-info">
                <div class="reviewer-avatar">{avatar_letter}</div>
                <div class="reviewer-info">
                    <h4 class="reviewer-name">{author}</h4>
                    <p class="review-date">{formatted_date}</p>
                </div>
                <div class="review-rating">
                    <span>{review_stars}</span>
                </div>
            </div>
            <p class="review-content">{content_display}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    

# Main App
def main():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Netflix+Sans:wght@300;400;500;700&display=swap');
        
        .stApp {
            background: #141414;
            color: white;
            font-family: 'Netflix Sans', 'Helvetica Neue', Arial, sans-serif;
        }
        
        /* Netflix-style header */
        .netflix-header {
            background: linear-gradient(180deg, rgba(0,0,0,0.7) 10%, transparent);
            padding: 20px 0;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }
        
        .netflix-logo {
            color: #E50914;
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        /* Hero section */
        .hero-section {
            background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.8)), 
                        url('https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80');
            background-size: cover;
            background-position: center;
            height: 80vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-top: 80px;
            position: relative;
        }
        
        .hero-content {
            max-width: 800px;
            padding: 40px;
            background: rgba(0,0,0,0.6);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .hero-title {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #E50914, #FF6B6B);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .hero-subtitle {
            font-size: 1.3rem;
            margin-bottom: 30px;
            color: rgba(255,255,255,0.9);
            line-height: 1.6;
        }
        
        /* Search section */
        .search-section {
            background: rgba(0,0,0,0.8);
            padding: 40px;
            border-radius: 15px;
            margin: 40px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .search-title {
            color: white;
            font-size: 2rem;
            font-weight: 600;
            text-align: center;
            margin-bottom: 30px;
        }
        
        /* Netflix-style buttons */
        .netflix-btn {
            background: #E50914;
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 4px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .netflix-btn:hover {
            background: #F40612;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
        }
        
        /* Trending section */
        .trending-section {
            margin: 60px 0;
            padding: 40px;
            background: rgba(0,0,0,0.6);
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .section-title {
            color: white;
            font-size: 2.2rem;
            font-weight: 600;
            margin-bottom: 30px;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 0;
            width: 60px;
            height: 4px;
            background: #E50914;
            border-radius: 2px;
        }
        
        /* Movie cards */
        .movie-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .movie-card {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.1);
            cursor: pointer;
        }
        
        .movie-card:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border-color: rgba(255,255,255,0.3);
        }
        
        .movie-poster {
            width: 100%;
            height: 300px;
            object-fit: cover;
        }
        
        .movie-info {
            padding: 15px;
        }
        
        .movie-title {
            color: white;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 8px;
            line-height: 1.3;
        }
        
        .movie-rating {
            color: #FFD700;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }
        
        .movie-year {
            color: rgba(255,255,255,0.7);
            font-size: 0.9rem;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .hero-title {
                font-size: 2.5rem;
            }
            
            .hero-subtitle {
                font-size: 1.1rem;
            }
            
            .movie-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }
        }
        
        /* Hide Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #141414;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #E50914;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #F40612;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Netflix-style header
    st.markdown("""
    <div class="netflix-header">
        <h1 class="netflix-logo">MOVIEFLIX</h1>
    </div>
    """, unsafe_allow_html=True)

    # Hero section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-content">
            <h1 class="hero-title">Discover Your Next Favorite Movie</h1>
            <p class="hero-subtitle">
                Explore thousands of movies with our recommendation system. 
                Find hidden gems, trending movies and personalised suggestions just for you.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    global movies, similarity
    movies = pickle.load(open('movie_list.pkl', 'rb'))
    # Load compressed similarity matrix from .npz file
    data = np.load("similarity.npz")
    similarity_uint8 = data["similarity"]
    similarity = similarity_uint8.astype(np.float32) / 255
    
    # Search section
    st.markdown("""
    <div class="search-section">
        <h2 class="search-title">Find Your Perfect Movie</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Create columns for better layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Movie selection with search
        selected_movie = st.selectbox(
            "Type or select a movie from the dropdown",
            movies['title'].values,
            index=0,
            key="movie_select",
            help="Start typing to search for movies"
        )
        
        # Netflix-style search button
        search_clicked = st.button('Get Recommendations', key="recommend_btn", use_container_width=True)
    
    # Trending Movies Section (show popular movies from dataset)
    st.markdown("""
    <div class="trending-section">
        <h2 class="section-title">🔥 Trending Now</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Display some popular movies as trending
    trending_movies = movies.sample(n=10).reset_index(drop=True)  # Random sample for demo
    
    # Create movie grid
    cols = st.columns(5)
    for i, (_, movie) in enumerate(trending_movies.head(5).iterrows()):
        with cols[i]:
            movie_details = fetch_movie_details(movie.movie_id)
            if movie_details:
                poster_url = f"{POSTER_BASE_URL}{movie_details['poster_path']}" if movie_details['poster_path'] else DEFAULT_POSTER
                
                # Movie card with hover effect
                st.markdown(f"""
                <div class="movie-card" onclick="">
                    <img src="{poster_url}" class="movie-poster" alt="{movie.title}">
                    <div class="movie-info">
                        <div class="movie-title">{movie.title[:25]}{'...' if len(movie.title) > 25 else ''}</div>
                        <div class="movie-rating">⭐ {movie_details['vote_average']}/10</div>
                        <div class="movie-year">{movie_details['release_date'][:4] if movie_details['release_date'] != 'N/A' else 'N/A'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Show second row of trending movies
    cols2 = st.columns(5)
    for i, (_, movie) in enumerate(trending_movies.tail(5).iterrows()):
        with cols2[i]:
            movie_details = fetch_movie_details(movie.movie_id)
            if movie_details:
                poster_url = f"{POSTER_BASE_URL}{movie_details['poster_path']}" if movie_details['poster_path'] else DEFAULT_POSTER
                
                st.markdown(f"""
                <div class="movie-card">
                    <img src="{poster_url}" class="movie-poster" alt="{movie.title}">
                    <div class="movie-info">
                        <div class="movie-title">{movie.title[:25]}{'...' if len(movie.title) > 25 else ''}</div>
                        <div class="movie-rating">⭐ {movie_details['vote_average']}/10</div>
                        <div class="movie-year">{movie_details['release_date'][:4] if movie_details['release_date'] != 'N/A' else 'N/A'}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Process search results
    if search_clicked:
        with st.spinner('Finding perfect matches for you...'):
            recommendations = recommend(selected_movie)
            
            # Get selected movie details
            selected_index = movies[movies['title'] == selected_movie].index[0]
            selected_id = movies.iloc[selected_index].movie_id
            selected_details = fetch_movie_details(selected_id)
            
            if selected_details:
                # Featured Movie Section
                st.markdown("""
                <div class="trending-section">
                    <h2 class="section-title">🎯 Featured Movie</h2>
                </div>
                """, unsafe_allow_html=True)
                
                display_movie_details(selected_movie, selected_details)
                
                # Recommendations Section
                if recommendations:
                    st.markdown("""
                    <div class="trending-section">
                        <h2 class="section-title">🍿 Recommended For You</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    display_recommendations(recommendations)
                    
                    # Cast & Crew Section
                    display_cast(selected_details['cast'])
                    
                    # User Reviews Section
                    reviews = fetch_movie_reviews(selected_id)
                    if reviews:
                        display_reviews(reviews)
                    else:
                        st.markdown("""
                        <div class="reviews-section">
                            <div class="reviews-header">
                                <div>
                                    <h2 class="reviews-title">Reviews</h2>
                                    <p class="reviews-count">0</p>
                                </div>
                            </div>
                            
                            <div class="no-reviews">
                                <h4>No reviews yet</h4>
                                <p>Be the first to share your thoughts about this movie</p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("🚫 No recommendations found. Please try another movie.")
            else:
                st.error("❌ Failed to fetch movie details. Please try again later.")
    
    # Footer
    st.markdown("""
    <div style="
        margin-top: 80px;
        padding: 40px;
        text-align: center;
        background: rgba(0,0,0,0.8);
        border-top: 1px solid rgba(255,255,255,0.1);
    ">
        <h3 style="color: #E50914; margin-bottom: 20px;">MOVIEFLIX</h3>
        <p style="color: rgba(255,255,255,0.7); margin: 0;">
            Built on Streamlit with  TMDB API  • Movie Recommendation System
        </p>
        <p style="color: rgba(255,255,255,0.5); margin: 10px 0 0 0; font-size: 0.9rem;">
            © 2025 MovieFlix. Discover your next favorite movie.
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":

    main()
