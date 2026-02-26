import urllib.request
import json
from datetime import datetime as dt
from datetime import timedelta
import time
import os

# --- HESION BRANDING COLORS ---
COLOR_BG = "#F2EDE4"         # Light background
COLOR_TEXT = "#373535"       # Black text
COLOR_ACCENT = "#926A47"     # Dark Gold/Brown (Links, Buttons)
COLOR_PRIMARY = "#D3C3A7"    # Gold (Borders)

# --- JOURNALS LIST ---
JOURNALS = [
    {"name": "Academy of Management Journal", "issn": "0001-4273"},
    {"name": "Academy of Management Review", "issn": "0363-7425"},
    {"name": "Administrative Science Quarterly", "issn": "0001-8392"},
    {"name": "European Journal of Work and Organizational Psychology", "issn": "1359-432X"},
    {"name": "Group & Organization Management", "issn": "1059-6011"},
    {"name": "Human Performance", "issn": "0895-9285"},
    {"name": "Human Resource Development Quarterly", "issn": "1044-8004"},
    {"name": "Human Resource Management", "issn": "1099-050X"},
    {"name": "Industrial and Organizational Psychology: Perspectives on Science and Practice", "issn": "1754-9426"},
    {"name": "International Journal of Selection and Assessment", "issn": "0965-075X"},
    {"name": "Journal of Applied Psychology", "issn": "0021-9010"},
    {"name": "Journal of Business and Psychology", "issn": "1573-353X"},
    {"name": "Journal of Management", "issn": "0149-2063"},
    {"name": "Journal of Managerial Psychology", "issn": "0268-3946"},
    {"name": "Journal of Occupational Health Psychology", "issn": "1076-8998"},
    {"name": "Journal of Occupational and Organizational Psychology", "issn": "2044-8325"},
    {"name": "Journal of Organizational Behavior", "issn": "1099-1379"},
    {"name": "Journal of Personnel Psychology", "issn": "1866-5888"},
    {"name": "Organization Science", "issn": "1047-7039"},
    {"name": "Organizational Psychology Review", "issn": "2041-3866"},
    {"name": "Personnel Psychology", "issn": "1744-6570"},
    {"name": "The Leadership Quarterly", "issn": "1048-9843"},
    {"name": "Work & Stress", "issn": "1464-5335"}
]

def fetch_feed(journal, max_articles=20):
    try:
        print(f"Fetching {journal['name']}...")
        ninety_days_ago = dt.now() - timedelta(days=90)
        date_filter = ninety_days_ago.strftime("%Y-%m-%d")
        
        base_url = f"https://api.crossref.org/journals/{journal['issn']}/works"
        params = f"?rows={max_articles}&filter=from-online-pub-date:{date_filter}&sort=published&order=desc"
        url = base_url + params
        
        req = urllib.request.Request(url, headers={'User-Agent': 'HesionResearchFeed/1.0'})
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            
        articles = []
        if 'message' in data and 'items' in data['message']:
            for item in data['message']['items']:
                pub_date = None
                date_str = "Date unavailable"
                
                # Try multiple date fields
                for date_field in ['published-online', 'published-print', 'published']:
                    if date_field in item and 'date-parts' in item[date_field]:
                        parts = item[date_field]['date-parts'][0]
                        if parts:
                            year = parts[0]
                            month = parts[1] if len(parts) > 1 else 1
                            day = parts[2] if len(parts) > 2 else 1
                            pub_date = dt(year, month, day)
                            date_str = pub_date.strftime("%B %d, %Y")
                            break
                
                if not pub_date or pub_date < ninety_days_ago:
                    continue

                authors = []
                if 'author' in item:
                    for author in item['author'][:3]:
                        if 'family' in author:
                            authors.append(author['family'])
                author_str = ", ".join(authors) if authors else "Unknown Author"

                doi = item.get('DOI', '')
                link = f"https://doi.org/{doi}" if doi else item.get('URL', '')
                
                abstract = item.get('abstract', '')
                if abstract:
                    abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<p>', '').replace('</p>', '').replace('<jats:title>', '').replace('</jats:title>', '')
                
                title = item.get('title', ['No Title'])[0]
                topics = extract_topics(title, abstract)

                is_oa = False
                if 'license' in item:
                    for lic in item['license']:
                        if 'creative-commons' in lic.get('URL', ''):
                            is_oa = True

                articles.append({
                    "title": title,
                    "link": link,
                    "authors": author_str,
                    "date": pub_date,
                    "date_str": date_str,
                    "journal": journal['name'],
                    "topics": topics,
                    "abstract": abstract,
                    "is_oa": is_oa
                })
        return articles
    except Exception as e:
        print(f"Error fetching {journal['name']}: {e}")
        return []

def extract_topics(title, abstract):
    text = (title + " " + (abstract or "")).lower()
    keywords = {
        'AI Technology': ['artificial intelligence', ' ai ', 'algorithm', 'technology'],
        'OCB': ['ocb', 'citizenship behavior', 'helping', 'prosocial'],
        'Creativity': ['creativity', 'innovation', 'creative', 'idea'],
        'Culture': ['culture', 'climate', 'norms'],
        'Diversity': ['diversity', 'inclusion', 'equity', 'minority', 'gender', 'race'],
        'Job Design': ['job design', 'job crafting', 'autonomy', 'workload'],
        'Justice': ['justice', 'fairness', 'equity'],
        'Leadership': ['leadership', 'leader', 'supervisor', 'manager', 'lmx'],
        'Meta-Analysis': ['meta-analysis', 'meta analysis', 'quantitative review'],
        'Motivation': ['motivation', 'engagement', 'determination'],
        'Performance': ['performance', 'productivity', 'effectiveness'],
        'Personality': ['personality', 'traits', 'big five'],
        'Remote Work': ['remote', 'telework', 'virtual', 'hybrid', 'work from home'],
        'Selection': ['selection', 'hiring', 'recruitment', 'assessment'],
        'Teams': ['team', 'group', 'collaboration'],
        'Training': ['training', 'development', 'learning'],
        'Turnover': ['turnover', 'retention', 'attrition', 'quit'],
        'Well-Being': ['well-being', 'wellbeing', 'health', 'stress', 'burnout']
    }
    
    found = []
    for topic, keys in keywords.items():
        if any(k in text for k in keys):
            found.append(topic)
    return found[:4]

def generate_html(all_articles):
    total_articles = len(all_articles)
    updated_date = dt.now().strftime("%B %d, %Y")
    
    journals_list = sorted([j['name'] for j in JOURNALS])
    
    topics_set = set()
    for a in all_articles:
        topics_set.update(a['topics'])
    topics_list = sorted(list(topics_set))

    # --- HTML GENERATION ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Org Psych Research Briefing</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: {COLOR_BG};
            color: {COLOR_TEXT};
            line-height: 1.6;
            padding: 2rem 1rem;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; }}

        /* HEADER */
        .header-card {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            border-top: 6px solid {COLOR_PRIMARY};
            margin-bottom: 2rem;
        }}
        .logo {{ max-width: 200px; margin-bottom: 1rem; }}
        h1 {{ font-size: 1.75rem; font-weight: 700; color: {COLOR_TEXT}; margin: 0 0 0.5rem 0; }}
        .tagline {{ font-size: 0.9rem; color: {COLOR_ACCENT}; font-weight: 600; margin-bottom: 1rem; }}
        .meta {{ color: #666; font-size: 0.85rem; }}

        /* FILTERS - ORIGINAL 2-ROW LAYOUT */
        .filters {{
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        /* Row 1: Dropdowns */
        .filter-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            align-items: flex-end;
            flex-wrap: wrap;
        }}
        .filter-row:last-child {{ margin-bottom: 0; }}

        .filter-group {{ flex: 1; min-width: 180px; }}
        
        /* Specific sizing for Search to be wider in Row 2 */
        .filter-group.search {{ flex: 2; min-width: 220px; }}

        .label {{ display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 0.3rem; color: {COLOR_TEXT}; }}
        
        select, input[type="text"] {{
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 0.85rem;
            font-family: inherit;
        }}
        
        select:focus, input:focus {{
            outline: none;
            border-color: {COLOR_ACCENT};
            box-shadow: 0 0 0 3px rgba(146, 106, 71, 0.1);
        }}

        .checkbox-group {{
            display: flex;
            align-items: center;
            padding-top: 1.6rem; /* Push down to align with search box */
        }}
        
        .checkbox-group input {{ margin-right: 0.5rem; cursor: pointer; }}
        .checkbox-group label {{ font-size: 0.85rem; cursor: pointer; }}

        .count-bar {{ text-align: center; color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}

        /* FEED ITEMS */
        .feed {{ display: flex; flex-direction: column; gap: 1rem; }}
        
        .article {{
            background: white;
            padding: 1.25rem;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid {COLOR_PRIMARY};
            transition: transform 0.15s;
        }}
        .article:hover {{ transform: translateY(-2px); }}

        .article-title {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 0.5rem; line-height: 1.4; }}
        .article-title a {{ color: {COLOR_TEXT}; text-decoration: none; }}
        .article-title a:hover {{ color: {COLOR_ACCENT}; }}

        .article-meta {{ font-size: 0.8rem; color: #666; margin-bottom: 0.8rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }}
        
        .journal-badge {{ 
            background: {COLOR_ACCENT}; color: white; padding: 2px 8px; 
            border-radius: 10px; font-weight: 600; font-size: 0.75rem; 
        }}

        .topics {{ display: flex; gap: 0.5rem; margin-bottom: 0.8rem; flex-wrap: wrap; }}
        .topic {{ background: #f0f0f0; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; }}

        .abstract {{ display: none; background: #fafafa; padding: 1rem; border-radius: 4px; font-size: 0.9rem; color: #555; margin-bottom: 1rem; }}
        .abstract.visible {{ display: block; }}

        .read-link {{ color: {COLOR_ACCENT}; font-weight: 600; text-decoration: none; font-size: 0.85rem; }}
        .read-link:hover {{ text-decoration: underline; }}

        @media (max-width: 768px) {{
            .filter-row {{ flex-direction: column; align-items: stretch; }}
            .checkbox-group {{ padding-top: 0; margin-top: 0.5rem; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <div class="header-card">
        <img src="logo.svg" alt="Hesion Logo" class="logo">
        <h1>Org Psych Research Briefing</h1>
        <div class="tagline">Your 90-day snapshot of what's new in the field</div>
        <div class="meta">
            📊 {total_articles} Articles | 🕐 Updated: {updated_date}
        </div>
    </div>

    <div class="filters">
        <div class="filter-row">
            <div class="filter-group">
                <span class="label">Filter by Journal</span>
                <select id="journalFilter" onchange="runFilter()">
                    <option value="all">All Journals</option>
                    {''.join(f'<option value="{j}">{j}</option>' for j in journals_list)}
                </select>
            </div>
            <div class="filter-group">
                <span class="label">Filter by Topic</span>
                <select id="topicFilter" onchange="runFilter()">
                    <option value="all">All Topics</option>
                    {''.join(f'<option value="{t}">{t}</option>' for t in topics_list)}
                </select>
            </div>
            <div class="filter-group">
                <span class="label">Sort By</span>
                <select id="sortBy" onchange="runSort()">
                    <option value="newest">Date (Newest First)</option>
                    <option value="oldest">Date (Oldest First)</option>
                    <option value="journal">Journal Name</option>
                    <option value="title">Title (A-Z)</option>
                </select>
            </div>
        </div>

        <div class="filter-row">
    <div class="filter-group search">
        <span class="label">Search</span>
        <input type="text" id="searchInput" placeholder="Keywords..." onkeyup="runFilter()">
    </div>
    <div style="display: flex; align-items: center; gap: 1rem; padding-top: 1.6rem;">
        <div class="checkbox-group" style="padding-top: 0;">
            <input type="checkbox" id="oaCheck" onchange="runFilter()">
            <label for="oaCheck">Open Access Only</label>
        </div>
        <div class="checkbox-group" style="padding-top: 0;">
            <input type="checkbox" id="abstractCheck" onchange="toggleAbstracts()">
            <label for="abstractCheck">Show Abstracts</label>
        </div>
    </div>
</div>
    </div>

    <div class="count-bar" id="countDisplay">Showing {total_articles} articles</div>

    <div id="feed" class="feed">
"""
    
    for article in all_articles:
        topics_str = " ".join(article['topics'])
        oa_val = "true" if article['is_oa'] else "false"
        oa_icon = '🔓' if article['is_oa'] else ''
        
        html += f"""
        <div class="article" 
             data-journal="{article['journal']}" 
             data-topics="{topics_str}" 
             data-title="{article['title'].lower()}" 
             data-date="{article['date'].timestamp()}"
             data-oa="{oa_val}">
             
            <div class="article-title">
                <a href="{article['link']}" target="_blank">{article['title']}</a> {oa_icon}
            </div>
            
            <div class="article-meta">
                <span class="journal-badge">{article['journal']}</span>
                <span>{article['authors']}</span>
                <span>{article['date_str']}</span>
            </div>
            
            <div class="topics">
                {''.join(f'<span class="topic">{t}</span>' for t in article['topics'])}
            </div>
            
            <div class="abstract">
                {article['abstract']}
            </div>
            
            <a href="{article['link']}" target="_blank" class="read-link">Read Full Article →</a>
        </div>
        """

    html += """
    </div>
    <div id="noResults" style="display:none; text-align:center; padding:2rem; color:#666;">
        No articles match your current filters.
    </div>
</div>

<script>
    function toggleAbstracts() {
        const show = document.getElementById('abstractCheck').checked;
        document.querySelectorAll('.abstract').forEach(el => el.classList.toggle('visible', show));
    }

    function runSort() {
        const feed = document.getElementById('feed');
        const cards = Array.from(feed.children);
        const type = document.getElementById('sortBy').value;

        cards.sort((a, b) => {
            if (type === 'newest') return b.dataset.date - a.dataset.date;
            if (type === 'oldest') return a.dataset.date - b.dataset.date;
            if (type === 'journal') return a.dataset.journal.localeCompare(b.dataset.journal);
            if (type === 'title') return a.dataset.title.localeCompare(b.dataset.title);
        });
        cards.forEach(card => feed.appendChild(card));
    }

    function runFilter() {
        const journal = document.getElementById('journalFilter').value;
        const topic = document.getElementById('topicFilter').value;
        const search = document.getElementById('searchInput').value.toLowerCase();
        const oa = document.getElementById('oaCheck').checked;
        
        let count = 0;
        
        document.querySelectorAll('.article').forEach(card => {
            const matchJ = journal === 'all' || card.dataset.journal === journal;
            const matchT = topic === 'all' || card.dataset.topics.includes(topic);
            const matchS = card.dataset.title.includes(search);
            const matchOA = !oa || card.dataset.oa === 'true';
            
            if (matchJ && matchT && matchS && matchOA) {
                card.style.display = 'block';
                count++;
            } else {
                card.style.display = 'none';
            }
        });
        
        document.getElementById('countDisplay').innerText = `Showing ${count} articles`;
        document.getElementById('feed').style.display = count === 0 ? 'none' : 'flex';
        document.getElementById('noResults').style.display = count === 0 ? 'block' : 'none';
    }
</script>
</body>
</html>
"""
    
    with open("index.html", "w", encoding='utf-8') as f:
        f.write(html)
    print("HTML generated successfully.")

def main():
    all_articles = []
    for journal in JOURNALS:
        all_articles.extend(fetch_feed(journal))
    all_articles.sort(key=lambda x: x['date'], reverse=True)
    generate_html(all_articles)

if __name__ == "__main__":
    main()
