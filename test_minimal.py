from src.tools.crossref_search import CrossrefSearch

cs = CrossrefSearch()
papers = cs.search("adults daily water intake", max_results=5)
for p in papers:
    print(f"{p['title']} ({p['year']})")