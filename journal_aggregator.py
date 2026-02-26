import urllib.request
import json
from datetime import datetime as dt
from datetime import timedelta
import time
import os

# --- HESION BRANDING ---
COLOR_BG = "#F2EDE4"         # Lighter touch (Background)
COLOR_CARD = "#FFFFFF"       # White cards
COLOR_TEXT = "#373535"       # Black text
COLOR_ACCENT = "#926A47"     # Accents (Links, Buttons)
COLOR_PRIMARY = "#D3C3A7"    # Gold (Borders, decorative)

# --- CONFIGURATION ---
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
    
    journals_list = sorted(list(set(a['journal'] for a in all_articles)))
    
    topics_set = set()
    for a in all_articles:
        topics_set.update(a['topics'])
    topics_list = sorted(list(topics_set))

    # HTML Structure mirrors "2 research_feed.docx" exactly
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Org Psych Research Briefing</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: {COLOR_BG};
            color: {COLOR_TEXT};
            line-height: 1.6;
            min-height: 100vh;
            padding: 2rem 1rem;
        }}

        .header-card {{
            max-width: 1200px;
            margin: 0 auto 2rem auto;
            background: white;
            padding: 2rem 1.5rem 1.5rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            border-top: 5px solid {COLOR_PRIMARY};
        }}

        .logo {{ max-width: 200px; margin-bottom: 1rem; }}

        .header-card h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            color: {COLOR_TEXT};
            margin-bottom: 0.4rem;
            letter-spacing: -0.02em;
        }}

        .header-card .tagline {{
            font-size: 0.9rem;
            color: {COLOR_ACCENT};
            font-weight: 400;
            margin-bottom: 1.25rem;
        }}

        .header-meta {{
            display: flex;
            gap: 2rem;
            justify-content: center;
            font-size: 0.8125rem;
            color: #6c757d;
            flex-wrap: wrap;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 1rem; }}

        .filters {{
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        /* Strict Row Layout from Original */
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
            font-size: 0.
