#!/usr/bin/env python3
"""
Generate a single-page application for the albums database.
Outputs: index.html + data.json
"""

import os
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "albums.db"
OUTPUT_DIR = "site"


def parse_json_field(value):
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [result]
    except:
        return [value] if value else []


def get_all_albums(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM albums ORDER BY album_name")
    albums = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for album in albums:
        album['artists_list'] = parse_json_field(album['artists'])
        album['tracks_list'] = parse_json_field(album.get('tracks'))
    
    return albums


def generate_data_json(albums):
    data = {
        'albums': [],
        'stats': {'total': len(albums)},
        'artists': defaultdict(list),
        'genres': defaultdict(list),
        'decades': defaultdict(list),
    }
    
    ratings = [a['rating'] for a in albums if a.get('rating')]
    data['stats']['avg_rating'] = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    for album in albums:
        album_data = {
            'id': album['id'],
            'name': album['album_name'],
            'artists': album['artists_list'],
            'genre': album.get('genre') or '',
            'year': album.get('release_year') or '',
            'rating': album.get('rating'),
            'date_added': album['date_added'][:10] if album.get('date_added') else '',
            'label': album.get('record_label') or '',
            'tracks': album['tracks_list'],
            'description': album.get('description') or '',
            'notes': album.get('personal_notes') or '',
        }
        data['albums'].append(album_data)
        
        for artist in album['artists_list']:
            if album['id'] not in data['artists'][artist]:
                data['artists'][artist].append(album['id'])
        
        if album.get('genre'):
            if album['id'] not in data['genres'][album['genre']]:
                data['genres'][album['genre']].append(album['id'])
        
        if album.get('release_year'):
            decade = f"{str(album['release_year'])[:3]}0s"
            if album['id'] not in data['decades'][decade]:
                data['decades'][decade].append(album['id'])
    
    data['stats']['artist_count'] = len(data['artists'])
    data['stats']['genre_count'] = len(data['genres'])
    
    data['artists'] = dict(data['artists'])
    data['genres'] = dict(data['genres'])
    data['decades'] = dict(data['decades'])
    
    return data


def generate_html():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paul's Albums</title>
    <style>
        :root {
            --bg: #ffffff;
            --bg-card: #f8f9fa;
            --text: #2c3e50;
            --text-muted: #7f8c8d;
            --accent: #e91e63;
            --accent-hover: #c2185b;
            --border: #e0e0e0;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Georgia, serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        .back-link {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
        }
        .back-link a { color: var(--text-muted); text-decoration: none; }
        .back-link a:hover { color: var(--accent); }
        h1 { color: var(--accent); font-size: 2.5rem; font-weight: normal; text-align: center; margin-bottom: 0.5rem; }
        .subtitle { text-align: center; color: var(--text-muted); font-style: italic; margin-bottom: 2rem; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat {
            background: var(--bg-card);
            padding: 1.25rem;
            text-align: center;
            border: 2px solid var(--border);
            border-radius: 8px;
        }
        .stat-value { font-size: 2rem; color: var(--accent); }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: -apple-system, sans-serif; }
        .nav-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid var(--border);
            padding-bottom: 1rem;
        }
        .nav-tab {
            padding: 0.5rem 1rem;
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 6px;
            cursor: pointer;
            font-family: -apple-system, sans-serif;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .nav-tab:hover, .nav-tab.active { background: var(--accent); color: white; border-color: var(--accent); }
        .search-box {
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-family: Georgia, serif;
        }
        .search-box:focus { outline: none; border-color: var(--accent); }
        .filter-section { margin-bottom: 2rem; }
        .filter-title { font-size: 1.1rem; margin-bottom: 1rem; color: var(--text); }
        .filter-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .filter-tag {
            padding: 0.4rem 0.8rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
            font-family: -apple-system, sans-serif;
            transition: all 0.2s;
        }
        .filter-tag:hover { border-color: var(--accent); color: var(--accent); }
        .filter-tag .count { color: var(--text-muted); margin-left: 0.3rem; }
        .album-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        .album-card {
            background: var(--bg-card);
            padding: 1.5rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .album-card:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(233,30,99,0.1); }
        .album-card h3 { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.5rem; font-family: -apple-system, sans-serif; }
        .album-card .artist { color: var(--text-muted); font-style: italic; font-size: 0.95rem; }
        .album-card .meta { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; font-family: -apple-system, sans-serif; }
        .album-card .rating { color: var(--accent); }
        .genre-badge { 
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            margin-top: 0.5rem;
            font-family: -apple-system, sans-serif;
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            overflow-y: auto;
            padding: 2rem;
        }
        .modal-overlay.active { display: block; }
        .modal {
            background: white;
            max-width: 700px;
            margin: 0 auto;
            border-radius: 12px;
            padding: 2rem;
            position: relative;
        }
        .modal-close {
            position: absolute;
            top: 1rem; right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }
        .modal-close:hover { color: var(--accent); }
        .modal h2 { color: var(--accent); margin-bottom: 0.5rem; font-weight: normal; }
        .modal .artist { font-style: italic; color: var(--text-muted); margin-bottom: 1rem; font-size: 1.1rem; }
        .modal .meta-row { margin: 1rem 0; }
        .modal .label { font-weight: 600; color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; font-family: -apple-system, sans-serif; }
        .modal .tracks { background: var(--bg-card); padding: 1rem; border-radius: 8px; margin: 1rem 0; }
        .modal .tracks ol { margin-left: 1.5rem; }
        .modal .tracks li { margin: 0.3rem 0; }
        
        .results-count { color: var(--text-muted); margin-bottom: 1rem; font-family: -apple-system, sans-serif; }
        footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center; font-family: -apple-system, sans-serif; }
    </style>
</head>
<body>
    <div class="back-link"><a href="https://pauls-collections.vercel.app">← All Collections</a></div>
    <h1>Paul's Albums</h1>
    <p class="subtitle">A personal music collection</p>
    
    <div class="stats" id="stats"></div>
    
    <div class="nav-tabs">
        <button class="nav-tab active" data-view="all">All Albums</button>
        <button class="nav-tab" data-view="artists">Artists</button>
        <button class="nav-tab" data-view="genres">Genres</button>
        <button class="nav-tab" data-view="decades">Decades</button>
    </div>
    
    <input type="text" class="search-box" id="search" placeholder="Search albums, artists, genres...">
    
    <div id="filters" class="filter-section" style="display:none;"></div>
    <div class="results-count" id="results-count"></div>
    <div class="album-grid" id="albums"></div>
    
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-content"></div>
        </div>
    </div>
    
    <footer>Generated <span id="timestamp"></span></footer>
    
    <script>
    let DATA = null;
    let currentView = 'all';
    let currentFilter = null;
    
    async function init() {
        const resp = await fetch('data.json');
        DATA = await resp.json();
        document.getElementById('timestamp').textContent = new Date().toLocaleDateString();
        renderStats();
        renderAlbums(DATA.albums);
        setupEventListeners();
    }
    
    function renderStats() {
        const s = DATA.stats;
        document.getElementById('stats').innerHTML = `
            <div class="stat"><div class="stat-value">${s.total}</div><div class="stat-label">Albums</div></div>
            <div class="stat"><div class="stat-value">${s.artist_count}</div><div class="stat-label">Artists</div></div>
            <div class="stat"><div class="stat-value">${s.genre_count}</div><div class="stat-label">Genres</div></div>
            <div class="stat"><div class="stat-value">${s.avg_rating || 'N/A'}</div><div class="stat-label">Avg Rating</div></div>
        `;
    }
    
    function renderAlbums(albums) {
        document.getElementById('results-count').textContent = `${albums.length} album${albums.length !== 1 ? 's' : ''}`;
        document.getElementById('albums').innerHTML = albums.map(a => `
            <div class="album-card" onclick="showAlbum(${a.id})">
                <h3>${esc(a.name)}</h3>
                <div class="artist">${esc(a.artists.join(', '))}</div>
                <div class="meta">
                    ${a.year ? `${a.year} • ` : ''}
                    ${a.rating ? `<span class="rating">${'★'.repeat(a.rating)}${'☆'.repeat(10-a.rating)}</span>` : ''}
                </div>
                ${a.genre ? `<span class="genre-badge">${esc(a.genre)}</span>` : ''}
            </div>
        `).join('');
    }
    
    function renderFilters(type) {
        let items = [];
        if (type === 'artists') items = Object.entries(DATA.artists).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'genres') items = Object.entries(DATA.genres).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'decades') items = Object.entries(DATA.decades).map(([k,v]) => [k, v.length]).sort((a,b) => b[0].localeCompare(a[0]));
        
        if (items.length === 0) {
            document.getElementById('filters').style.display = 'none';
            return;
        }
        
        document.getElementById('filters').style.display = 'block';
        document.getElementById('filters').innerHTML = `
            <div class="filter-title">${type.charAt(0).toUpperCase() + type.slice(1)} (${items.length})</div>
            <div class="filter-tags">
                ${items.map(([name, count]) => `<span class="filter-tag" data-filter="${esc(name)}">${esc(name)}<span class="count">(${count})</span></span>`).join('')}
            </div>
        `;
    }
    
    function filterAlbums(type, value) {
        let ids = [];
        if (type === 'artists') ids = DATA.artists[value] || [];
        else if (type === 'genres') ids = DATA.genres[value] || [];
        else if (type === 'decades') ids = DATA.decades[value] || [];
        
        const albums = DATA.albums.filter(a => ids.includes(a.id));
        renderAlbums(albums);
    }
    
    function searchAlbums(query) {
        const q = query.toLowerCase();
        const albums = DATA.albums.filter(a => 
            a.name.toLowerCase().includes(q) ||
            a.artists.some(x => x.toLowerCase().includes(q)) ||
            (a.genre && a.genre.toLowerCase().includes(q))
        );
        renderAlbums(albums);
    }
    
    function showAlbum(id) {
        const a = DATA.albums.find(x => x.id === id);
        if (!a) return;
        
        document.getElementById('modal-content').innerHTML = `
            <h2>${esc(a.name)}</h2>
            <div class="artist">${esc(a.artists.join(', '))}</div>
            <div class="meta-row">
                ${a.genre ? `<span class="genre-badge">${esc(a.genre)}</span>` : ''}
                ${a.year ? ` • ${a.year}` : ''}
                ${a.rating ? ` • <span class="rating">${'★'.repeat(a.rating)}${'☆'.repeat(10-a.rating)} ${a.rating}/10</span>` : ''}
            </div>
            ${a.label ? `<div class="meta-row"><span class="label">Label:</span> ${esc(a.label)}</div>` : ''}
            ${a.description ? `<div class="meta-row"><span class="label">Description</span><p>${esc(a.description)}</p></div>` : ''}
            ${a.tracks.length ? `<div class="meta-row"><span class="label">Tracks</span><div class="tracks"><ol>${a.tracks.map(t => `<li>${esc(t)}</li>`).join('')}</ol></div></div>` : ''}
            ${a.notes ? `<div class="meta-row"><span class="label">Notes:</span> ${esc(a.notes)}</div>` : ''}
            <div class="meta-row" style="color: var(--text-muted); font-size: 0.85rem;">Added: ${a.date_added}</div>
        `;
        document.getElementById('modal').classList.add('active');
    }
    
    function closeModal() {
        document.getElementById('modal').classList.remove('active');
    }
    
    function setupEventListeners() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentView = tab.dataset.view;
                currentFilter = null;
                document.getElementById('search').value = '';
                
                if (currentView === 'all') {
                    document.getElementById('filters').style.display = 'none';
                    renderAlbums(DATA.albums);
                } else {
                    renderFilters(currentView);
                    renderAlbums(DATA.albums);
                }
            });
        });
        
        document.getElementById('filters').addEventListener('click', e => {
            if (e.target.classList.contains('filter-tag')) {
                currentFilter = e.target.dataset.filter;
                filterAlbums(currentView, currentFilter);
            }
        });
        
        document.getElementById('search').addEventListener('input', e => {
            if (e.target.value) searchAlbums(e.target.value);
            else if (currentFilter) filterAlbums(currentView, currentFilter);
            else renderAlbums(DATA.albums);
        });
        
        document.getElementById('modal').addEventListener('click', e => {
            if (e.target.id === 'modal') closeModal();
        });
        
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });
    }
    
    function esc(s) { 
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); 
    }
    
    init();
    </script>
</body>
</html>'''


def generate_site():
    print("Generating albums SPA...")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    albums = get_all_albums(DB_PATH)
    print(f"Found {len(albums)} albums")
    
    data = generate_data_json(albums)
    with open(os.path.join(OUTPUT_DIR, 'data.json'), 'w') as f:
        json.dump(data, f)
    print("Generated data.json")
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(generate_html())
    print("Generated index.html")
    
    print(f"\n✓ Site generated in '{OUTPUT_DIR}/' (2 files)")


if __name__ == "__main__":
    generate_site()
