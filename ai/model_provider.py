"""
AEGIS Model Provider
Multi-backend AI provider supporting Google Gemini, OpenAI, Groq, Anthropic, Ollama,
and the built-in AEGIS Local Heuristic & Expert Engine with deep encyclopedic question answering.
"""

import os
import re
import json
import requests
from typing import Dict, Any, List, Optional
from aegis.config import SYSTEM_PHILOSOPHY

# Built-in Domain Knowledge Base for Immediate High-Accuracy Answers
ENCYCLOPEDIC_KNOWLEDGE = {
    "pok": (
        "### Pakistan-occupied Kashmir (PoK) — Overview\n\n"
        "**Pakistan-occupied Kashmir (PoK)** refers to the territory of Jammu and Kashmir under Pakistani control since 1947.\n\n"
        "#### Key Facts:\n"
        "- **Divisions**: **Azad Jammu and Kashmir (AJK)** (Capital: Muzaffarabad) and **Gilgit-Baltistan** (borders China and Ladakh).\n"
        "- **1947 Accession**: Maharaja Hari Singh legally signed the *Instrument of Accession* with India on October 26, 1947.\n"
        "- **Line of Control (LoC)**: The ceasefire boundary resulting from the 1948 war, formalised in the 1972 Simla Agreement.\n"
        "- **Indian Position**: India's Parliament unanimously resolved in 1994 that the entire region is an integral part of India."
    ),
    "kashmir": (
        "### Kashmir Region & Geopolitical Context\n\n"
        "Kashmir is a northern Himalayan region comprising Jammu, the Kashmir Valley, Ladakh, Gilgit-Baltistan, and Azad Kashmir.\n\n"
        "- **Status**: Jammu & Kashmir and Ladakh are Union Territories of India following the 2019 Reorganisation Act.\n"
        "- **Significance**: Critical geographic gateway connecting South and Central Asia."
    ),
    "why is the sky blue": (
        "### Why is the Sky Blue? (Rayleigh Scattering)\n\n"
        "The daytime sky looks blue due to **Rayleigh scattering**:\n\n"
        "1. Sunlight contains all colors of the rainbow.\n"
        "2. As sunlight travels through the atmosphere, gas molecules (Nitrogen and Oxygen) scatter shorter wavelengths (**blue and violet**) much more strongly than longer wavelengths (red and orange).\n"
        "3. Because our eyes are sensitive to blue light, the sky appears bright blue."
    ),
    "photosynthesis": (
        "### Photosynthesis\n\n"
        "**Photosynthesis** is the biological process used by plants, algae, and cyanobacteria to convert light energy into chemical energy.\n\n"
        "$$\\text{6CO}_2 + \\text{6H}_2\\text{O} + \\text{Light} \\xrightarrow{\\text{Chlorophyll}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + \\text{6O}_2$$\n\n"
        "- Plants absorb water from roots and $CO_2$ from air, synthesizing glucose and releasing oxygen."
    ),
    "ai": (
        "### Artificial Intelligence (AI)\n\n"
        "**Artificial Intelligence (AI)** is the simulation of human intelligence in machines programmed to think, learn, and reason.\n\n"
        "- **Core Branches**: Machine Learning (ML), Deep Learning, Computer Vision, and Natural Language Processing.\n"
        "- **Supervised Agents (AEGIS)**: Emphasizes user-supervised safety, where AI recommends and human authority governs all consequential actions."
    )
}

class ModelProvider:
    """Dispatches generation requests to configured LLM backends with local fallback."""

    def __init__(self, memory_manager=None):
        self.memory = memory_manager
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
        self._web_search = None

    @property
    def web_search(self):
        if self._web_search is None:
            from aegis.actions.web_search import WebSearchEngine
            self._web_search = WebSearchEngine()
        return self._web_search

    def get_active_provider(self) -> str:
        """Determines active model provider based on user settings and available keys."""
        if self.gemini_key:
            return "gemini"
        if self.groq_key:
            return "groq"
        if self.openai_key:
            return "openai"
        # Check for local LLM servers (Ollama / LM Studio)
        if self._is_local_llm_available():
            return "ollama"
        return "local"

    def _is_local_llm_available(self) -> bool:
        """Quick check if Ollama or LM Studio is running."""
        for url in [self.ollama_url, "http://localhost:1234/v1/chat/completions"]:
            try:
                r = requests.get(url.rsplit("/", 1)[0], timeout=1)
                if r.status_code < 500:
                    return True
            except Exception:
                continue
        return False

    def set_api_key(self, provider: str, key: str) -> None:
        """Dynamically updates an API key in memory."""
        provider = provider.lower()
        if provider == "gemini":
            self.gemini_key = key
            os.environ["GEMINI_API_KEY"] = key
        elif provider == "openai":
            self.openai_key = key
            os.environ["OPENAI_API_KEY"] = key
        elif provider == "groq":
            self.groq_key = key
            os.environ["GROQ_API_KEY"] = key

    def generate_response(self, prompt: str, system_context: Optional[str] = None,
                          conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generates text response using active provider with automatic fallback to local engine.
        """
        provider = self.get_active_provider()

        if provider == "gemini" and self.gemini_key:
            try:
                return self._call_gemini(prompt, system_context, conversation_history)
            except Exception as e:
                print(f"[ModelProvider] Gemini call failed ({e}), falling back to Local Engine.")

        if provider == "groq" and self.groq_key:
            try:
                return self._call_groq(prompt, system_context, conversation_history)
            except Exception as e:
                print(f"[ModelProvider] Groq call failed ({e}), falling back to Local Engine.")

        if provider == "openai" and self.openai_key:
            try:
                return self._call_openai(prompt, system_context, conversation_history)
            except Exception as e:
                print(f"[ModelProvider] OpenAI call failed ({e}), falling back to Local Engine.")

        if provider == "ollama":
            try:
                return self._call_ollama(prompt, system_context, conversation_history)
            except Exception as e:
                print(f"[ModelProvider] Ollama/LM Studio call failed ({e}), falling back to Heuristic Engine.")

        # Default: Local High-Intelligence Expert Engine
        return self._local_reasoning_engine(prompt, system_context, conversation_history)

    def _call_gemini(self, prompt: str, system_context: Optional[str], history: Optional[List[Dict]]) -> str:
        """Direct REST call to Gemini 1.5 Flash."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}

        system_instruction = system_context or SYSTEM_PHILOSOPHY
        contents = []

        if history:
            for msg in history[-6:]:
                role = "user" if msg["role"] == "user" else "model"
                if contents and contents[-1]["role"] == role:
                    contents[-1]["parts"][0]["text"] += f"\n\n{msg['content']}"
                else:
                    contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        final_text = f"System Context:\n{system_instruction}\n\nUser Request: {prompt}"
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"][0]["text"] += f"\n\n{final_text}"
        else:
            contents.append({"role": "user", "parts": [{"text": final_text}]})

        payload = {"contents": contents}
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_groq(self, prompt: str, system_context: Optional[str], history: Optional[List[Dict]]) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system_context or SYSTEM_PHILOSOPHY}]
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.3}
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_openai(self, prompt: str, system_context: Optional[str], history: Optional[List[Dict]]) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system_context or SYSTEM_PHILOSOPHY}]
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.3}
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, system_context: Optional[str], history: Optional[List[Dict]]) -> str:
        """Calls local LLM via Ollama native API or LM Studio OpenAI-compatible API."""
        system_msg = system_context or SYSTEM_PHILOSOPHY

        # Try LM Studio first (OpenAI-compatible endpoint)
        lm_studio_url = "http://localhost:1234/v1/chat/completions"
        try:
            messages = [{"role": "system", "content": system_msg}]
            if history:
                for msg in history[-6:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": prompt})

            payload = {"messages": messages, "temperature": 0.3, "stream": False}
            resp = requests.post(lm_studio_url, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

        # Fallback to Ollama native API
        payload = {
            "model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
            "prompt": f"System: {system_msg}\n\nUser: {prompt}",
            "stream": False
        }
        resp = requests.post(self.ollama_url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _local_reasoning_engine(self, prompt: str, system_context: Optional[str], history: Optional[List[Dict]]) -> str:
        """
        Direct, high-yield answers without corporate fluff or repetitive boilerplate.
        """
        lower = prompt.lower().strip()

        # Direct search context passthrough
        if system_context and "###" in system_context:
            return system_context

        # Check knowledge base
        for key, knowledge in ENCYCLOPEDIC_KNOWLEDGE.items():
            if re.search(r'\b' + re.escape(key) + r'\b', lower) or key == lower:
                return knowledge

        # Greetings & Identity
        if any(w in lower for w in ["who are you", "what is aegis", "introduce yourself", "your purpose"]):
            return (
                "I am **AEGIS** (*Assisted Executive Guidance and Intelligence System*).\n\n"
                "**Core Principle**: *\"AI assists. AI reasons. AI recommends. The user decides.\"*\n"
                "I assist with conversation, deep knowledge retrieval, media playback, system monitoring, blueprints, and file automation while keeping you in full control of all consequential actions."
            )

        if any(w in lower for w in ["hello", "hi", "hey", "good morning", "good evening"]):
            return "Hello Ayushmaan! I am ready. What would you like to do?"

        if "how do you work" in lower or "explain your architecture" in lower:
            return (
                "### AEGIS Pipeline\n\n"
                "1. **Input**: Voice, Text, Real-time Camera Object Tracking.\n"
                "2. **Understanding**: Intent parsing, entity extraction, and misconception correction.\n"
                "3. **Supervision Gate**: Evaluates action risk (Safe to Critical); requires your explicit approval for consequential operations.\n"
                "4. **Execution**: Sandboxed tool actions (Apps, Files, Blueprints, Media).\n"
                "5. **Audit**: Cryptographically logs every event with SHA-256 hashes."
            )

        # For any general question or topic: perform live knowledge synthesis
        try:
            search_result = self.web_search.search(prompt)
            if search_result and search_result.get("summary"):
                return search_result["summary"]
        except Exception as e:
            print(f"[ModelProvider Search Fallback Error]: {e}")

        clean_topic = re.sub(r'^(tell me about|what is|who is|explain|what are|how does|why is)\s*', '', prompt, flags=re.IGNORECASE).strip(" ?.")
        if clean_topic:
            return f"**{clean_topic.title()}**:\n\nRegarding {clean_topic}, you can ask me to search Google or generate an architectural blueprint."

        # Acknowledge past context if asked
        if any(w in lower for w in ["what did i just say", "what was the last thing", "do you remember", "previous", "past conversation"]):
            if history:
                last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
                if last_user:
                    return f"Yes, in our previous turns we were discussing: '{last_user}'. How can I follow up on that?"
            return "My short-term memory buffer is currently empty."

        return "I am ready Ayushmaan. Let me know what you'd like me to perform (Note: I am running on the offline heuristic engine, please configure an API key for full contextual memory)."
