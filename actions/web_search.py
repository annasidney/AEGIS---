"""
AEGIS Web Search & Comprehensive Question Answering Engine
Fetches real, factual, detailed answers from Wikipedia, DuckDuckGo, and deep encyclopedic knowledge.
Features query normalization, concept resolution, Wikipedia user agent header, auto_suggest=False, and multi-paragraph synthesis.
"""

import urllib.parse
import urllib.request
import re
import requests
import wikipedia
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple

# Set proper user agent for Wikipedia API
wikipedia.set_user_agent("AEGIS-Assistant/1.0 (https://github.com/ayush/aegis; contact@aegis.ai)")

# Acronym & Direct Concept Normalization
ACRONYM_MAP = {
    "pok": "Pakistan-administered Kashmir",
    "p.o.k.": "Pakistan-administered Kashmir",
    "p.o.k": "Pakistan-administered Kashmir",
    "pakistan occupied kashmir": "Pakistan-administered Kashmir",
    "kashmir": "Kashmir conflict",
    "loc": "Line of Control",
    "lac": "Line of Actual Control",
    "isro": "Indian Space Research Organisation",
    "drdo": "Defence Research and Development Organisation",
    "nasa": "NASA",
    "ai": "Artificial Intelligence",
    "ml": "Machine Learning",
    "llm": "Large Language Model",
    "dna": "DNA",
    "rna": "RNA",
    "sih": "Smart India Hackathon",
    "gdp": "Gross Domestic Product",
    "who": "World Health Organization",
    "un": "United Nations",
    "nato": "NATO"
}

# Scientific & Common Question to Encyclopedic Concept Resolver
QUESTION_CONCEPT_MAP = {
    "sky blue": "Diffuse sky radiation",
    "why is the sky blue": "Diffuse sky radiation",
    "why is sky blue": "Diffuse sky radiation",
    "why sky is blue": "Diffuse sky radiation",
    "why do leaves turn green": "Chlorophyll",
    "how do airplanes fly": "Lift (force)",
    "how planes fly": "Lift (force)",
    "airplanes fly": "Lift (force)",
    "how airplane flies": "Lift (force)",
    "how do birds fly": "Bird flight",
    "what causes rain": "Rain",
    "how rain is formed": "Water cycle",
    "photosynthesis": "Photosynthesis",
    "gravity": "Gravity",
    "black hole": "Black hole",
    "black holes": "Black hole",
    "quantum computing": "Quantum computing",
    "quantum computer": "Quantum computing",
    "artificial intelligence": "Artificial intelligence",
    "machine learning": "Machine learning",
    "dna": "DNA",
    "prime minister of india": "Prime Minister of India",
    "president of india": "President of India",
    "president of the united states": "President of the United States",
    "president of usa": "President of the United States",
    "taj mahal": "Taj Mahal",
    "solar system": "Solar System",
    "internet": "Internet",
    "blockchain": "Blockchain",
    "computer": "Computer",
    "python programming": "Python (programming language)"
}

# Built-in Deep Encyclopedic Knowledge Base for Instant Rich Responses
DEEP_KNOWLEDGE_BASE = {
    "pok": (
        "### Pakistan-occupied Kashmir (PoK) — Comprehensive Overview\n\n"
        "**Pakistan-occupied Kashmir (PoK)** refers to the portion of the erstwhile princely state of Jammu and Kashmir "
        "that has been under Pakistani administrative control since 1947.\n\n"
        "#### Key Administrative Divisions:\n"
        "1. **Azad Jammu and Kashmir (AJK)**: The southern strip adjacent to Punjab and Khyber Pakhtunkhwa, with its capital at **Muzaffarabad**.\n"
        "2. **Gilgit-Baltistan**: The northern mountainous region bordering China, Afghanistan, and India's Ladakh, historically known as the Northern Areas.\n\n"
        "#### Historical & Geopolitical Context:\n"
        "- **1947 Accession**: Following the partition of India, tribal militias backed by the Pakistani military invaded Kashmir. "
        "Maharaja Hari Singh signed the *Instrument of Accession* with the Union of India on October 26, 1947.\n"
        "- **Line of Control (LoC)**: The 1948-49 Indo-Pakistani War led to a UN-mediated ceasefire line, designated as the **Line of Control (LoC)** after the 1972 Simla Agreement.\n"
        "- **Indian Position**: India maintains that the entirety of Jammu and Kashmir (including PoK and Gilgit-Baltistan) is an integral part of India.\n"
        "- **Strategic Importance**: PoK borders China and hosts key infrastructure of the **China-Pakistan Economic Corridor (CPEC)**, particularly through Gilgit-Baltistan to the Karakoram Highway."
    ),
    "sih": (
        "### Smart India Hackathon (SIH)\n\n"
        "**Smart India Hackathon (SIH)** is a premier nationwide initiative organized by the Ministry of Education's Innovation Cell (MIC), "
        "AICTE, and the Government of India to provide students a platform to solve pressing problems of ministries, departments, and industries.\n\n"
        "- **Format**: Includes Software and Hardware editions with 36-hour non-stop coding sprints.\n"
        "- **Impact**: Fosters world-class innovation, product design, and startup incubation among young Indian innovators."
    ),
    "why is the sky blue": (
        "### Why is the Sky Blue? (Rayleigh Scattering)\n\n"
        "The sky appears blue because of a physical phenomenon called **Rayleigh scattering**:\n\n"
        "1. **Sunlight Composition**: Sunlight appears white, but it is a combination of all the colors of the visible light spectrum.\n"
        "2. **Atmospheric Scattering**: When sunlight penetrates Earth's atmosphere, it collides with nitrogen and oxygen gas molecules. Light waves with shorter wavelengths—specifically **blue and violet**—scatter in all directions much more readily than longer wavelengths (red, yellow, and orange).\n"
        "3. **Human Eye Sensitivity**: Although violet light scatters even more than blue light, human eyes are significantly more sensitive to blue frequencies, causing us to perceive the daytime sky as bright blue."
    ),
    "how do airplanes fly": (
        "### How Airplanes Fly (Aerodynamics & Four Forces)\n\n"
        "Airplanes stay in the air through the interaction of **four fundamental aerodynamic forces**:\n\n"
        "1. **Lift**: Produced by the airplane's wings (airfoils). Air travels faster over the curved upper surface of the wing than below it, producing lower pressure on top (Bernoulli's principle) and an upward reaction force (Newton's 3rd Law).\n"
        "2. **Weight (Gravity)**: The downward force pulling the airplane toward Earth.\n"
        "3. **Thrust**: The forward mechanical propulsion generated by jet engines or propellers.\n"
        "4. **Drag**: The aerodynamic friction and air resistance resisting the forward movement.\n\n"
        "**Principle of Flight**: When **Lift exceeds Weight**, the aircraft climbs; when **Thrust exceeds Drag**, it accelerates forward."
    ),
    "photosynthesis": (
        "### Photosynthesis — Biological Mechanism\n\n"
        "**Photosynthesis** is the biochemical process by which green plants, algae, and cyanobacteria convert light energy into chemical energy stored in glucose.\n\n"
        "$$\\text{6CO}_2 + \\text{6H}_2\\text{O} + \\text{Light} \\xrightarrow{\\text{Chlorophyll}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + \\text{6O}_2$$\n\n"
        "#### Key Stages:\n"
        "- **Light-Dependent Reactions**: Occur in the thylakoid membranes of chloroplasts, splitting water ($H_2O$) to generate ATP, NADPH, and releasing oxygen ($O_2$).\n"
        "- **Calvin Cycle (Light-Independent)**: Occurs in the stroma, using ATP and NADPH to convert carbon dioxide ($CO_2$) into sugars (glucose)."
    ),
    "gravity": (
        "### Gravity (Gravitational Force)\n\n"
        "**Gravity** is a fundamental natural force by which all things with mass or energy are attracted toward one another.\n\n"
        "- **Newtonian Physics**: Describes gravity as an attractive force: $F = G \\frac{m_1 m_2}{r^2}$.\n"
        "- **Einstein's General Relativity**: Modern physics defines gravity not as a conventional force, but as the curvature of **spacetime** caused by the uneven distribution of mass and energy."
    ),
    "quantum computing": (
        "### Quantum Computing\n\n"
        "**Quantum Computing** is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems too complex for classical computers.\n\n"
        "- **Qubits**: Unlike classical bits (0 or 1), qubits can exist in **superposition** (both 0 and 1 simultaneously).\n"
        "- **Entanglement**: Allows qubits to be correlated with each other, enabling exponential computational speedups for cryptography, material science, and optimization."
    ),
    "black hole": (
        "### Black Holes\n\n"
        "A **black hole** is a region of spacetime where gravity is so strong that nothing—no particles or even electromagnetic radiation such as light—can escape from it.\n\n"
        "- **Event Horizon**: The boundary surrounding a black hole beyond which nothing can return.\n"
        "- **Singularity**: The point of infinite density at the center.\n"
        "- **Formation**: Most stellar-mass black holes form when massive stars collapse at the end of their lifecycle in a supernova explosion."
    )
}

def get_youtube_video_url(query: str) -> Tuple[str, str, str]:
    """
    Extracts the clean song name and fetches the direct top YouTube video URL and video ID.
    Returns: (clean_song_name, watch_url, video_id)
    """
    clean = re.sub(r'^(play|song|music|put on|listen to)\s*', '', query, flags=re.IGNORECASE)
    clean = re.sub(r'\s*(in youtube|on youtube|from youtube|video|song|track|lyrics)\s*$', '', clean, flags=re.IGNORECASE)
    clean = clean.strip(" '\"`") or "music"

    encoded = urllib.parse.quote_plus(clean)
    try:
        req = urllib.request.Request(
            f"https://www.youtube.com/results?search_query={encoded}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
        if vids:
            for vid in vids:
                if len(vid) == 11:
                    return clean, f"https://www.youtube.com/watch?v={vid}", vid
    except Exception as e:
        print(f"[YouTube Video Scrape Error]: {e}")

    # Fallback to search query page
    return clean, f"https://www.youtube.com/results?search_query={encoded}", ""


class WebSearchEngine:
    """Retrieves real-time knowledge and answers from Wikipedia, DuckDuckGo, and deep knowledge bases."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AEGIS-Executive/1.0"
        }

    def clean_question_text(self, text: str) -> str:
        """Strips filler question words to isolate core subject."""
        cleaned = re.sub(
            r'^(tell me about|what is|what are|what was|what were|who is|who was|who were|why is|why are|why does|why do|how do|how does|how is|how can|how to|where is|where are|when did|when was|explain|describe|give info on|search wikipedia for|search wikipedia|search for|search|lookup|look up|google|define|meaning of)\s*',
            '',
            text.strip(),
            flags=re.IGNORECASE
        )
        return cleaned.strip(" ?.")

    def normalize_query(self, query: str) -> str:
        """Maps query to normalized encyclopedic concept."""
        clean = query.strip().lower().rstrip("?. ")

        # Check question concept map
        for q_pattern, concept in QUESTION_CONCEPT_MAP.items():
            if q_pattern in clean or clean in q_pattern:
                return concept

        # Direct acronym match
        if clean in ACRONYM_MAP:
            return ACRONYM_MAP[clean]

        for acr, expansion in ACRONYM_MAP.items():
            pattern = r'\b' + re.escape(acr) + r'\b'
            if re.search(pattern, clean):
                clean = re.sub(pattern, expansion, clean)

        return self.clean_question_text(clean)

    def search(self, query: str, limit: int = 4) -> Dict[str, Any]:
        """
        Performs a deep search: Knowledge Base -> Direct Concept -> Wikipedia (auto_suggest=False) -> DuckDuckGo.
        """
        raw_clean = query.strip().lower().rstrip("?. ")
        normalized_q = self.normalize_query(query)
        core_topic = self.clean_question_text(query)

        # 1. Check Deep Knowledge Base for instant high-accuracy match
        for key, knowledge_text in DEEP_KNOWLEDGE_BASE.items():
            if key == raw_clean or key in raw_clean or raw_clean in key or key == normalized_q.lower():
                return {
                    "query": query,
                    "status": "success",
                    "results": [{
                        "title": f"AEGIS Knowledge Base: {key.upper()}",
                        "snippet": knowledge_text[:200] + "...",
                        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(normalized_q)}"
                    }],
                    "summary": knowledge_text
                }

        results: List[Dict[str, str]] = []
        wiki_summary = None
        wiki_title = None

        # 2. Try Wikipedia with auto_suggest=False to prevent title corruption
        candidates_to_try = [normalized_q, core_topic, query]
        
        for cand in candidates_to_try:
            if not cand or wiki_summary:
                break
            try:
                # Direct summary attempt with auto_suggest=False
                wiki_summary = wikipedia.summary(cand, auto_suggest=False, sentences=4)
                wiki_title = cand
                results.append({
                    "title": f"Wikipedia: {cand}",
                    "snippet": wiki_summary,
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(cand)}"
                })
                break
            except wikipedia.exceptions.DisambiguationError as e:
                for opt in e.options[:3]:
                    try:
                        wiki_summary = wikipedia.summary(opt, auto_suggest=False, sentences=4)
                        wiki_title = opt
                        results.append({
                            "title": f"Wikipedia: {opt}",
                            "snippet": wiki_summary,
                            "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(opt)}"
                        })
                        break
                    except Exception:
                        continue
                if wiki_summary:
                    break
            except Exception:
                pass

        # If direct lookup failed, try search candidates
        if not wiki_summary:
            try:
                wiki_search = wikipedia.search(normalized_q, results=3)
                if wiki_search:
                    for candidate in wiki_search:
                        if candidate.lower() in ["pok pok", "mee pok", "pok", "bok choy"] and "pok" in raw_clean:
                            continue
                        try:
                            wiki_summary = wikipedia.summary(candidate, auto_suggest=False, sentences=4)
                            wiki_title = candidate
                            results.append({
                                "title": f"Wikipedia: {candidate}",
                                "snippet": wiki_summary,
                                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(candidate)}"
                            })
                            break
                        except Exception:
                            continue
            except Exception as e:
                print(f"[WebSearchEngine] Wikipedia search warning: {e}")

        # 3. DuckDuckGo Search for web snippets
        try:
            search_term = normalized_q if normalized_q != query else query
            encoded_query = urllib.parse.quote_plus(search_term)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            resp = requests.get(url, headers=self.headers, timeout=6)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                web_results = soup.find_all("div", class_="result__body", limit=limit)
                for r in web_results:
                    title_elem = r.find("a", class_="result__a")
                    snippet_elem = r.find("a", class_="result__snippet")
                    if title_elem and snippet_elem:
                        link = title_elem.get("href", "")
                        if "uddg=" in link:
                            link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                        results.append({
                            "title": title_elem.get_text().strip(),
                            "snippet": snippet_elem.get_text().strip(),
                            "url": link
                        })
        except Exception as e:
            print(f"[WebSearchEngine] DuckDuckGo search warning: {e}")

        # 4. Synthesize Answer
        if wiki_summary:
            summary_text = f"### {wiki_title.title()}\n\n{wiki_summary}\n\n"
            if len(results) > 1:
                summary_text += "#### Verified References:\n"
                for r in results[1:4]:
                    summary_text += f"- **[{r['title']}]({r['url']})**: {r['snippet']}\n"
            return {
                "query": query,
                "status": "success",
                "results": results,
                "summary": summary_text.strip()
            }

        if results:
            summary_text = f"### Briefing: {query.title()}\n\n"
            for r in results[:3]:
                summary_text += f"- **[{r['title']}]({r['url']})**\n  {r['snippet']}\n\n"
            return {
                "query": query,
                "status": "success",
                "results": results,
                "summary": summary_text.strip()
            }

        # Direct informative fallback
        return {
            "query": query,
            "status": "partial",
            "results": [{
                "title": f"Search: {query.title()}",
                "snippet": f"Web results for {query}",
                "url": f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            }],
            "summary": (
                f"### {core_topic.title()}\n\n"
                f"**Information on {core_topic.title()}**:\n"
                f"For this query, you can explore live citations and articles directly on [Google](https://www.google.com/search?q={urllib.parse.quote(query)}) "
                f"or [Wikipedia](https://en.wikipedia.org/wiki/Special:Search?search={urllib.parse.quote(normalized_q)})."
            )
        }
