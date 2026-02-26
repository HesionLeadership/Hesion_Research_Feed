import urllib.request
import json
from datetime import datetime as dt
from datetime import timedelta
import time
import os

# --- CONFIGURATION ---
# Hesion Branding Colors
COLOR_PRIMARY = "#D3C3A7"    # Gold/Tan
COLOR_LIGHT = "#F2EDE4"      # Light background
COLOR_ACCENT = "#926A47"     # Darker accent
COLOR_TEXT = "#373535"       # Black text

# Journal Configuration (ISSN lookup for CrossRef)
JOURNALS = [
    {"name": "Academy of Management Journal", "issn": "0001-4273"},
    {"name": "Academy of Management Review", "issn": "0363-7425"},
    {"name": "Administrative Science Quarterly", "issn": "0001-8392"},
    {"name": "European Journal of Work and Organizational Psychology", "issn": "1359-432X"},
    {"name": "Group & Organization Management", "issn": "1059-6011"},
    {"name": "Human Performance", "issn": "0895-9285"},
    {"name": "Human Resource Development Quarterly", "issn": "1044-8004"},
    {"name": "Human Resource Management", "issn": "1099-050X"},
    {"name": "Ind. and Org. Psychology: Perspectives on Science and Practice", "issn": "1754-9426"},
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
    """Fetch recent articles from CrossRef API"""
    try:
        print(f"Fetching {journal['name']}...")
        ninety_days_ago = dt.now() - timedelta(days=90)
        date_filter = ninety_days_ago.strftime("%Y-%m-%d")
        
        # CrossRef API URL
        base_url = f"https://api.crossref.org/journals/{journal['issn']}/works"
        params = f"?rows={max_articles}&filter=from-online-pub-date:{date_filter}&sort=published&order=desc"
        url = base_url + params
        
        req = urllib.request.Request(url, headers={'User-Agent': 'HesionResearchFeed/1.0 (mailto:admin@hesion.com)'})
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            
        articles = []
        if 'message' in data and 'items' in data['message']:
            for item in data['message']['items']:
                # Date parsing logic
                pub_date = None
                date_str = "Date unavailable"
                date_parts = item.get('published-online', {}).get('date-parts', [[]])[0]
                if not date_parts:
                    date_parts = item.get('published-print', {}).get('date-parts', [[]])[0]
                
                if date_parts:
                    year = date_parts[0]
                    month = date_parts[1] if len(date_parts) > 1 else 1
                    day = date_parts[2] if len(date_parts) > 2 else 1
                    pub_date = dt(year, month, day)
                    date_str = pub_date.strftime("%B %d, %Y")
                
                if not pub_date or pub_date < ninety_days_ago:
                    continue

                # Authors
                authors = []
                if 'author' in item:
                    for author in item['author'][:3]:
                        if 'family' in author:
                            authors.append(author['family'])
                author_str = ", ".join(authors) if authors else "Unknown Author"

                # Link
                doi = item.get('DOI', '')
                link = f"https://doi.org/{doi}" if doi else item.get('URL', '')
                
                # Abstract & Title
                abstract = item.get('abstract', '')
                # Clean up abstract XML tags if present
                abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<p>', '').replace('</p>', '')
                title = item.get('title', ['No Title'])[0]

                # Topics
                topics = extract_topics(title, abstract)

                # Open Access Check
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
    
    # Specific Hesion Topics mapping
    keywords = {
        'AI Technology': ['artificial intelligence', ' ai ', 'algorithm', 'technology', 'automation'],
        'OCB': ['ocb', 'citizenship behavior', 'helping', 'prosocial'],
        'Creativity': ['creativity', 'innovation', 'creative', 'idea generation'],
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
    return found[:4] # Return top 4 found

def generate_html(all_articles):
    total_articles = len(all_articles)
    updated_date = dt.now().strftime("%B %d, %Y")
    
    # Sort for filters
    journals_list = sorted(list(set(a['journal'] for a in all_articles)))
    
    # Extract unique topics
    topics_set = set()
    for a in all_articles:
        topics_set.update(a['topics'])
    topics_list = sorted(list(topics_set))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Org Psych Research Briefing | Hesion</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {COLOR_PRIMARY};
            --light: {COLOR_LIGHT};
            --accent: {COLOR_ACCENT};
            --text: {COLOR_TEXT};
        }}
        body {{ font-family: 'Inter', sans-serif; background: #f8f9fa; color: var(--text); margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        /* Header Styling */
        .header {{ 
            background: var(--light); 
            padding: 2rem; 
            border-radius: 12px; 
            text-align: center; 
            border-bottom: 4px solid var(--accent);
            margin-bottom: 2rem;
        }}
        .logo {{ max-width: 200px; margin-bottom: 1rem; }}
        h1 {{ color: var(--text); margin: 0; font-size: 2rem; }}
        .subtitle {{ color: var(--accent); font-weight: 600; margin-top: 0.5rem; }}
        .stats {{ margin-top: 1rem; font-size: 0.9rem; color: #666; }}
        
        /* Controls Styling - UPDATED FOR 2-ROW LAYOUT */
        .controls {{ 
            background: white; 
            padding: 1.5rem; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            margin-bottom: 2rem;
        }}
        .control-row {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .control-row:last-child {{ margin-bottom: 0; }}
        
        .control-group {{ flex: 1; min-width: 200px; }}
        .search-group {{ flex: 3; min-width: 300px; }}
        .checkbox-group {{ 
            display: flex; 
            align-items: center; 
            gap: 1.5rem; 
            padding-top: 1.5rem; /* Aligns checkboxes with input text */
        }}

        label {{ display: block; font-size: 0.8rem; font-weight: 700; margin-bottom: 0.3rem; color: var(--accent); }}
        select, input[type="text"] {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; box-sizing: border-box; }}
        input[type="checkbox"] {{ cursor: pointer; }}
        .checkbox-label {{ cursor: pointer; font-size: 0.9rem; color: var(--text); }}
        
        /* Grid Styling */
        .feed {{ display: grid; gap: 1.5rem; }}
        .article-card {{ 
            background: white; 
            padding: 1.5rem; 
            border-radius: 8px; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            border-left: 5px solid var(--primary);
            transition: transform 0.2s;
        }}
        .article-card:hover {{ transform: translateY(-2px); }}
        .article-meta {{ font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; display: flex; justify-content: space-between; flex-wrap: wrap; }}
        .journal-tag {{ background: var(--primary); color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: 600; }}
        .article-title {{ font-size: 1.1rem; font-weight: 700; color: var(--text); text-decoration: none; display: block; margin-bottom: 0.5rem; }}
        .article-title:hover {{ color: var(--accent); }}
        .topics {{ margin-top: 0.5rem; }}
        .topic-badge {{ background: var(--light); color: var(--accent); font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; margin-right: 5px; }}
        .abstract {{ display: none; margin-top: 1rem; font-size: 0.9rem; line-height: 1.5; color: #555; background: #f9f9f9; padding: 10px; border-radius: 4px; }}
        .abstract.visible {{ display: block; }}
        .read-btn {{ display: inline-block; margin-top: 1rem; color: var(--accent); font-weight: 600; text-decoration: none; font-size: 0.9rem; }}
        .oa-badge {{ color: green; font-weight: bold; font-size: 0.8rem; margin-left: 5px; }}
        
        @media (max-width: 768px) {{
            .control-row {{ flex-direction: column; gap: 0.5rem; }}
            .checkbox-group {{ padding-top: 0; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <img src="Hesion_logo_gold.png" alt="Hesion Leadership Consulting" class="logo">
        <h1>Org Psych Research Briefing</h1>
        <div class="subtitle">Your 90-day snapshot of what’s new in the field</div>
        <div class="stats">
            {total_articles} Articles | Last Updated: {updated_date}
        </div>
    </div>

    <div class="controls">
        <div class="control-row">
            <div class="control-group">
                <label>Filter by Journal</label>
                <select id="journalFilter" onchange="applyFilters()">
                    <option value="all">All Journals</option>
                    {''.join(f'<option value="{j}">{j}</option>' for j in journals_list)}
                </select>
            </div>
            <div class="control-group">
                <label>Filter by Topic</label>
                <select id="topicFilter" onchange="applyFilters()">
                    <option value="all">All Topics</option>
                    {''.join(f'<option value="{t}">{t}</option>' for t in topics_list)}
                </select>
            </div>
            <div class="control-group">
                <label>Sort By</label>
                <select id="sortBy" onchange="applySort()">
                    <option value="newest">Date (Newest First)</option>
                    <option value="oldest">Date (Oldest First)</option>
                    <option value="journal">Journal Name</option>
                    <option value="title">Title (A-Z)</option>
                </select>
            </div>
        </div>

        <div class="control-row">
            <div class="search-group">
                <label>Search</label>
                <input type="text" id="searchInput" placeholder="Keywords..." onkeyup="applyFilters()">
            </div>
            <div class="checkbox-group">
                <div>
                    <input type="checkbox" id="oaCheck" onchange="applyFilters()">
                    <span class="checkbox-label" onclick="document.getElementById('oaCheck').click()">Open Access Only</span>
                </div>
                <div>
                    <input type="checkbox" id="abstractCheck" onchange="toggleAbstracts()">
                    <span class="checkbox-label" onclick="document.getElementById('abstractCheck').click()">Show Abstracts</span>
                </div>
            </div>
        </div>
    </div>

    <div class="feed" id="feedGrid">
"""
    
    for article in all_articles:
        topics_str = " ".join(article['topics'])
        oa_class = "oa-true" if article['is_oa'] else "oa-false"
        oa_badge = '<span class="oa-badge">🔓 Open Access</span>' if article['is_oa'] else ''
        
        html += f"""
        <div class="article-card" 
             data-journal="{article['journal']}" 
             data-topics="{topics_str}" 
             data-title="{article['title'].lower()}" 
             data-date="{article['date'].timestamp()}"
             data-oa="{str(article['is_oa']).lower()}">
            
            <div class="article-meta">
                <span class="journal-tag">{article['journal']}</span>
                <span>{article['date_str']}</span>
            </div>
            
            <a href="{article['link']}" target="_blank" class="article-title">{article['title']} {oa_badge}</a>
            <div style="font-size: 0.9rem; font-style: italic;">{article['authors']}</div>
            
            <div class="topics">
                {''.join(f'<span class="topic-badge">{t}</span>' for t in article['topics'])}
            </div>
            
            <div class="abstract">
                <strong>Abstract:</strong><br>
                {article['abstract'][:600]}...
            </div>
            
            <a href="{article['link']}" target="_blank" class="read-btn">Read Full Article →</a>
        </div>
        """

    html += """
    </div>
</div>

<script>
    function toggleAbstracts() {
        const show = document.getElementById('abstractCheck').checked;
        document.querySelectorAll('.abstract').forEach(el => {
            el.classList.toggle('visible', show);
        });
    }

    function applySort() {
        const grid = document.getElementById('feedGrid');
        const cards = Array.from(grid.children);
        const criteria = document.getElementById('sortBy').value;

        cards.sort((a, b) => {
            if (criteria === 'newest') return b.dataset.date - a.dataset.date;
            if (criteria === 'oldest') return a.dataset.date - b.dataset.date;
            if (criteria === 'journal') return a.dataset.journal.localeCompare(b.dataset.journal);
            if (criteria === 'title') return a.dataset.title.localeCompare(b.dataset.title);
        });

        cards.forEach(card => grid.appendChild(card));
    }

    function applyFilters() {
        const journal = document.getElementById('journalFilter').value;
        const topic = document.getElementById('topicFilter').value;
        const search = document.getElementById('searchInput').value.toLowerCase();
        const oaOnly = document.getElementById('oaCheck').checked;

        document.querySelectorAll('.article-card').forEach(card => {
            const matchesJournal = journal === 'all' || card.dataset.journal === journal;
            const matchesTopic = topic === 'all' || card.dataset.topics.includes(topic);
            const matchesSearch = card.dataset.title.includes(search);
            const matchesOA = !oaOnly || card.dataset.oa === 'true';

            if (matchesJournal && matchesTopic && matchesSearch && matchesOA) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
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
    
    # Default sort: Newest first
    all_articles.sort(key=lambda x: x['date'], reverse=True)
    
    generate_html(all_articles)

if __name__ == "__main__":
    main()
