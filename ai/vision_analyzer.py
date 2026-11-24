"""
AEGIS Vision & Multimodal Module
Analyzes images, diagrams, documents, and live camera frame captures.
Supports Client-Side COCO-SSD Neural Detections, Gemini Vision API, and Local PIL Inspection.
"""

import io
import os
import base64
import requests
from typing import Dict, Any, Optional, List
from PIL import Image, ImageStat

class VisionAnalyzer:
    """Multimodal vision processor for AEGIS."""

    def __init__(self, model_provider=None):
        self.provider = model_provider

    def analyze_image(self, base64_image_data: str, user_question: Optional[str] = None,
                      detected_objects: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Processes camera frames or uploaded images alongside neural object detections.
        """
        width, height = 640, 480
        format_name = "JPEG"
        brightness = 120.0
        mode = "RGB"

        # 1. Parse Image if base64 provided
        if base64_image_data and len(base64_image_data) > 30:
            try:
                clean_b64 = base64_image_data.split(",", 1)[1] if "," in base64_image_data else base64_image_data
                image_bytes = base64.b64decode(clean_b64)
                image = Image.open(io.BytesIO(image_bytes))
                width, height = image.size
                format_name = image.format or "JPEG"
                mode = image.mode
                stat = ImageStat.Stat(image)
                brightness = sum(stat.mean[:3]) / 3.0 if len(stat.mean) >= 3 else stat.mean[0]
            except Exception as e:
                print(f"[VisionAnalyzer Error] PIL image decode error: {e}")

        # 2. Extract Client-Side Object Detections (COCO-SSD)
        obj_str = ""
        analysis_text = ""
        if detected_objects and len(detected_objects) > 0:
            object_counts = {}
            for obj in detected_objects:
                label = obj.get("class", "object")
                object_counts[label] = object_counts.get(label, 0) + 1

            obj_summary_list = [f"**{count} {label.title()}**" for label, count in object_counts.items()]
            obj_str = ", ".join(obj_summary_list)
            
            analysis_text = (
                f"### 👁️ Real-Time Camera Scene Recognition\n\n"
                f"I am actively monitoring your camera view. Currently detected in frame:\n"
                f"- **Recognized Elements**: {obj_str}\n"
                f"- **Scene Resolution**: `{width} × {height}` ({format_name})\n"
                f"- **Lighting Quality**: `{'Optimal' if brightness > 90 else 'Low light'}` (Luminance: {brightness:.1f}/255)\n\n"
                f"**Detailed Visual Assessment**:\n"
                f"The camera captures {obj_str} in active visual perspective. "
                f"{'Addressing question: ' + user_question if user_question else 'Vision tracking is live and responsive.'}"
            )

        # 3. Try Gemini Vision if API key is active for a much better, rich conversational description
        gemini_key = os.environ.get("GEMINI_API_KEY") or (self.provider.gemini_key if self.provider else "")
        if gemini_key and base64_image_data:
            try:
                question = user_question or "Describe what you see in this camera view concisely."
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                clean_b64 = base64_image_data.split(",", 1)[1] if "," in base64_image_data else base64_image_data
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": f"You are AEGIS Vision System. Analyze this camera frame. Address the user directly. {question}"},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": clean_b64
                                }
                            }
                        ]
                    }]
                }
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
                if resp.status_code == 200:
                    ai_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "source": "Gemini 1.5 Flash Vision",
                        "dimensions": f"{width}x{height}",
                        "format": format_name,
                        "brightness": round(brightness, 1),
                        "detected_objects": detected_objects,  # preserve bounding box data for UI
                        "analysis": f"### 👁️ Visual Intelligence Analysis\n\n{ai_text}"
                    }
            except Exception as e:
                print(f"[VisionAnalyzer] Gemini vision error: {e}")

        # If Gemini failed or isn't configured, but we have COCO-SSD data, return that
        if analysis_text:
            return {
                "source": "AEGIS Neural Vision (COCO-SSD)",
                "dimensions": f"{width}x{height}",
                "format": format_name,
                "brightness": round(brightness, 1),
                "detected_objects": detected_objects,
                "analysis": analysis_text
            }

        # 4. Fallback Local Visual Assessment
        return {
            "source": "AEGIS Local Vision Engine",
            "dimensions": f"{width}x{height}",
            "format": format_name,
            "brightness": round(brightness, 1),
            "analysis": (
                f"### 👁️ Camera Visual Inspection\n\n"
                f"- **Resolution**: `{width} × {height}`\n"
                f"- **Format**: `{format_name}` (`{mode}` mode)\n"
                f"- **Scene Illumination**: `{'Optimal / Well-lit' if brightness > 100 else 'Dimly Lit'}`\n"
                f"- **Status**: Camera frame captured. To enable instant live bounding-box object detection, activate the **Vision & Camera** tab."
            )
        }
