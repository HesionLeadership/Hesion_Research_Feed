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

def generate_html(journal_data, output_file="index.html"):
    """Generate HTML dashboard with Hesion branding and exact 2-row layout"""
    
    # Flatten articles list
    all_articles = []
    for journal in journal_data:
        all_articles.extend(journal['articles'])

    # Sort by date (newest first)
    all_articles.sort(key=lambda x: x['date'] if x['date'] else dt.min, reverse=True)

    # Get unique lists for filters
    journals_list = sorted(list(set(a['journal'] for a in all_articles)))
    topics_set = set()
    for a in all_articles:
        topics_set.update(a['topics'])
    topics_list = sorted(list(topics_set))

    total_articles = len(all_articles)
    updated_date = dt.now().strftime("%B %d, %Y")

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
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{ 
            font-family: 'Inter', sans-serif; 
            background: #f5f7fa; 
            color: var(--text); 
            line-height: 1.6;
            padding: 2rem 1rem;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; }}

        /* HEADER */
        .header-card {{
            background: var(--light);
            padding: 2rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            border-bottom: 4px solid var(--primary);
            margin-bottom: 2rem;
        }}
        .logo {{ max-width: 180px; margin-bottom: 1rem; display: block; margin-left: auto; margin-right: auto; }}
        .header-card h1 {{ font-size: 1.75rem; font-weight: 700; color: var(--text); margin-bottom: 0.4rem; }}
        .tagline {{ font-size: 0.9rem; color: var(--accent); font-weight: 600; margin-bottom: 1.25rem; }}
        .header-meta {{ display: flex; gap: 2rem; justify-content: center; font-size: 0.85rem; color: #666; }}

        /* FILTERS - EXACT ORIGINAL LAYOUT */
        .filters {{
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .filter-row {{
            display: flex;
            gap: 0.875rem;
            align-items: flex-end;
            margin-bottom: 0.875rem;
            flex-wrap: wrap;
        }}
        
        .filter-row:last-child {{ margin-bottom: 0; }}

        .filter-group {{ flex: 1; min-width: 160px; }}
        .filter-group.search {{ flex: 2; min-width: 220px; }}

        .filter-label {{
            display: block;
            font-size: 0.8125rem;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 0.4rem;
        }}

        select, input[type="text"] {{
            width: 100%;
            padding: 0.4rem 0.65rem;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 0.85rem;
            background: white;
            font-family: 'Inter', sans-serif;
        }}
        
        select:focus, input:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(146, 106, 71, 0.1);
        }}

        .checkbox-group {{
            display: flex;
            align-items: center;
            padding-top: 1.5rem; /* Aligns with input boxes */
            gap: 1.5rem;
        }}
        
        .checkbox-item {{ display: flex; align-items: center; }}
        .checkbox-item input {{ margin-right: 0.4rem; cursor: pointer; }}
        .checkbox-item label {{ font-size: 0.85rem; color: var(--text); cursor: pointer; user-select: none; }}

        .article-count {{
            text-align: center;
            padding: 0.75rem;
            background: white;
            border-radius: 8px;
            margin-bottom: 1.25rem;
            font-size: 0.85rem;
            color: #666;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        /* FEED GRID */
        .feed {{ display: flex; flex-direction: column; gap: 0.75rem; }}
        
        .article {{
            background: white;
            padding: 1rem;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid var(--primary);
            transition: transform 0.2s;
        }}
        .article:hover {{ transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}

        .article-header {{ display: flex; align-items: flex-start; gap: 0.6rem; margin-bottom: 0.5rem; }}
        .article-title {{ flex: 1; font-size: 1rem; font-weight: 700; line-height: 1.4; }}
        .article-title a {{ color: var(--text); text-decoration: none; }}
        .article-title a:hover {{ color: var(--accent); }}
        
        .oa-badge {{ 
            font-size: 0.7rem; 
            background: #e6f4ea; 
            color: #1e8e3e; 
            padding: 2px 6px; 
            border-radius: 4px; 
            font-weight: bold;
            white-space: nowrap;
        }}

        .article-meta {{ display: flex; gap: 0.75rem; margin-bottom: 0.6rem; font-size: 0.8rem; color: #666; flex-wrap: wrap; align-items: center; }}
        .journal-badge {{ 
            background: var(--primary); 
            color: white; 
            padding: 0.2rem 0.6rem; 
            border-radius: 12px; 
            font-size: 0.7rem; 
            font-weight: 600; 
        }}

        .topics {{ display: flex; gap: 0.4rem; margin-bottom: 0.6rem; flex-wrap: wrap; }}
        .topic-tag {{ 
            background: var(--light); 
            color: var(--accent); 
            padding: 0.2rem 0.5rem; 
            border-radius: 4px; 
            font-size: 0.7rem; 
            font-weight: 600; 
        }}

        .abstract {{ display: none; color: #555; font-size: 0.9rem; line-height: 1.5; margin-bottom: 0.8rem; background: #fafafa; padding: 10px; border-radius: 4px; }}
        .abstract.visible {{ display: block; }}

        .read-more {{ font-size: 0.85rem; font-weight: 600; color: var(--accent); text-decoration: none; }}
        .read-more:hover {{ text-decoration: underline; }}

        @media (max-width: 768px) {{
            .filter-row {{ flex-direction: column; align-items: stretch; }}
            .filter-group, .filter-group.search {{ width: 100%; }}
            .checkbox-group {{ padding-top: 0; margin-top: 0.5rem; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <div class="header-card">
        <img src="Hesion_logo_gold.png" alt="Hesion Logo" class="logo">
        <h1>Org Psych Research Briefing</h1>
        <div class="tagline">Your 90-day snapshot of what's new in the field</div>
        <div class="header-meta">
            <span>📊 {total_articles} articles</span>
            <span>🕐 Updated: {updated_date}</span>
        </div>
    </div>

    <div class="filters">
        <div class="filter-row">
            <div class="filter-group">
                <label class="filter-label" for="journal-filter">Filter by Journal</label>
                <select id="journal-filter" onchange="filterArticles()">
                    <option value="all">All Journals</option>
                    {''.join(f'<option value="{j}">{j}</option>' for j in journals_list)}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label" for="topic-filter">Filter by Topic</label>
                <select id="topic-filter" onchange="filterArticles()">
                    <option value="all">All Topics</option>
                    {''.join(f'<option value="{t}">{t}</option>' for t in topics_list)}
                </select>
            </div>
            <div class="filter-group">
                <label class="filter-label" for="sort-by">Sort by</label>
                <select id="sort-by" onchange="sortArticles()">
                    <option value="date-newest">Date (Newest First)</option>
                    <option value="date-oldest">Date (Oldest First)</option>
                    <option value="journal">Journal</option>
                    <option value="title">Title (A-Z)</option>
                </select>
            </div>
        </div>

        <div class="filter-row">
            <div class="filter-group search">
                <label class="filter-label" for="search">Search</label>
                <input type="text" id="search" placeholder="Search titles..." onkeyup="filterArticles()">
            </div>
            <div class="checkbox-group">
                <div class="checkbox-item">
                    <input type="checkbox" id="oa-only" onchange="filterArticles()">
                    <label for="oa-only">Open Access Only</label>
                </div>
                <div class="checkbox-item">
                    <input type="checkbox" id="show-abstracts" onchange="toggleAbstracts()">
                    <label for="show-abstracts">Show Abstracts</label>
                </div>
            </div>
        </div>
    </div>

    <div class="article-count" id="article-count">
        Showing {total_articles} articles
    </div>

    <div id="feed-container" class="feed">
"""

    for article in all_articles:
        topics_str = " ".join(article['topics'])
        oa_attr = "true" if article['is_oa'] else "false"
        oa_badge = '<span class="oa-badge">🔓 Open Access</span>' if article['is_oa'] else ''
        
        html += f"""
        <div class="article" 
             data-journal="{article['journal']}" 
             data-topics="{topics_str}" 
             data-title="{article['title'].lower()}" 
             data-oa="{oa_attr}" 
             data-date="{article['date'].timestamp()}">
            
            <div class="article-header">
                <div class="article-title">
                    <a href="{article['link']}" target="_blank">{article['title']}</a> {oa_badge}
                </div>
            </div>
            
            <div class="article-meta">
                <span class="journal-badge">{article['journal']}</span>
                <span class="authors">{article['authors']}</span>
                <span class="date">{article['date_str']}</span>
            </div>
            
            <div class="topics">
                {''.join(f'<span class="topic-tag">{t}</span>' for t in article['topics'])}
            </div>
            
            <div class="abstract">
                {article['abstract']}
            </div>
            
            <a href="{article['link']}" target="_blank" class="read-more">Read full article →</a>
        </div>
        """

    html += """
    </div>
    <div class="no-results" id="no-results" style="display: none; text-align: center; padding: 2rem; color: #666;">
        No articles match your current filters.
    </div>
</div>

<script>
    function toggleAbstracts() {
        const show = document.getElementById('show-abstracts').checked;
        document.querySelectorAll('.abstract').forEach(el => {
            el.classList.toggle('visible', show);
        });
    }

    function applySort() { return sortArticles(); } // Alias for safety

    function sortArticles() {
        const container = document.getElementById('feed-container');
        const cards = Array.from(container.children);
        const criteria = document.getElementById('sort-by').value;

        cards.sort((a, b) => {
            if (criteria === 'date-newest') return b.dataset.date - a.dataset.date;
            if (criteria === 'date-oldest') return a.dataset.date - b.dataset.date;
            if (criteria === 'journal') return a.dataset.journal.localeCompare(b.dataset.journal);
            if (criteria === 'title') return a.dataset.title.localeCompare(b.dataset.title);
        });

        cards.forEach(card => container.appendChild(card));
    }

    function filterArticles() {
        const journal = document.getElementById('journal-filter').value;
        const topic = document.getElementById('topic-filter').value;
        const search = document.getElementById('search').value.toLowerCase();
        const oaOnly = document.getElementById('oa-only').checked;
        let visibleCount = 0;

        document.querySelectorAll('.article').forEach(card => {
            const matchesJournal = journal === 'all' || card.dataset.journal === journal;
            const matchesTopic = topic === 'all' || card.dataset.topics.includes(topic);
            const matchesSearch = card.dataset.title.includes(search);
            const matchesOA = !oaOnly || card.dataset.oa === 'true';

            if (matchesJournal && matchesTopic && matchesSearch && matchesOA) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        // Update count
        const countText = visibleCount === 1 ? 'article' : 'articles';
        document.getElementById('article-count').innerText = `Showing ${visibleCount} ${countText}`;
        
        // Show/Hide "No Results"
        const noResults = document.getElementById('no-results');
        const feed = document.getElementById('feed-container');
        if (visibleCount === 0) {
            feed.style.display = 'none';
            noResults.style.display = 'block';
        } else {
            feed.style.display = 'flex';
            noResults.style.display = 'none';
        }
    }
</script>
</body>
</html>
"""
    
    with open(output_file, "w", encoding='utf-8') as f:
        f.write(html)
    print(f"HTML generated: {output_file}")

def main():
    all_articles = []
    for journal in JOURNALS:
        all_articles.extend(fetch_feed(journal))
    
    # Default sort: Newest first
    all_articles.sort(key=lambda x: x['date'], reverse=True)
    
    generate_html(all_articles)

if __name__ == "__main__":
    main()
