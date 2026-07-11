"""
Script generator using Claude API (Anthropic) with local fallback.
Generates YouTube video scripts with hooks, SEO metadata, and structured format.
"""

import json
import logging
import random
from typing import Dict, Optional

import config.settings as settings

logger = logging.getLogger(__name__)

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Local script templates for fallback when Claude API is not available
_LOCAL_TEMPLATES = {
    "finance_invest": {
        "hooks": [
            "Most people lose money investing. Here's what they do wrong.",
            "This simple strategy made me thousands. Let me show you how.",
            "Stop putting your money in savings. Do this instead.",
            "The #1 investing mistake that costs you thousands every year.",
        ],
        "bodies": [
            "Investing doesn't have to be complicated. The key is understanding three things: compound interest, diversification, and patience. Compound interest means your money earns money, and that money earns more money. Over 20 years, even small amounts grow exponentially. Diversification means spreading your investments across different assets so one bad investment doesn't wipe you out. And patience means staying invested through market ups and downs instead of panic selling.",
            "Here's the truth about building wealth: it's not about earning more, it's about investing what you earn. The average millionaire has seven streams of income. Start with index funds, which historically return about 10 percent per year. Then add real estate or bonds as your portfolio grows. The key is to start now, because time in the market beats timing the market.",
            "Want to know the secret that wealthy people use? They invest in assets that generate passive income. This could be dividend stocks, rental properties, or even digital products. The goal is to make money while you sleep. Start with what you have, even if it's just fifty dollars a month. The important thing is consistency, not the amount.",
        ],
        "outros": "If this helped you, hit subscribe and drop a comment with your biggest investing question. See you in the next video.",
    },
    "tech_software_biz": {
        "hooks": [
            "This free AI tool is replacing entire teams. You need to know about it.",
            "I built a SaaS in 30 days. Here's exactly how.",
            "Stop coding from scratch. Use these tools instead.",
        ],
        "bodies": [
            "The tech industry is changing faster than ever. Artificial intelligence tools are now capable of writing code, designing interfaces, and even managing projects. But here's the thing: these tools are meant to augment your skills, not replace them. The developers who thrive will be the ones who learn to work alongside AI, using it to handle repetitive tasks while focusing on creative problem-solving.",
            "Building a software business has never been more accessible. With no-code tools, cloud services, and AI assistance, you can launch a product in weeks instead of months. The key is to solve a real problem for a specific audience. Don't try to build the next Facebook. Instead, find a niche where people are willing to pay for a simple solution.",
        ],
        "outros": "Found this useful? Subscribe for more tech insights and drop your questions below. See you next time.",
    },
}

# Generic fallback
_GENERIC = {
    "hooks": [
        "This is something most people don't know about. Let me explain.",
        "Pay attention to this. It could change everything for you.",
        "Here's what nobody tells you about this topic.",
    ],
    "bodies": [
        "Let me break this down in simple terms. The key concept here is understanding the fundamentals. Once you grasp the basics, everything else falls into place. Most people overcomplicate things, but the truth is simpler than you think. Focus on the essentials, master them, and build from there. Consistency and patience are your best allies in this journey.",
        "Here's what you need to know. First, understand the landscape. Second, identify the opportunities. Third, take action. Most people get stuck at step one or two. Don't be one of them. The difference between those who succeed and those who don't is simple: execution. Start today, start small, but start.",
    ],
    "outros": "If you found this valuable, please subscribe and share it with someone who needs to hear this. Leave a comment with your thoughts. See you in the next video.",
}


class ScriptGenerator:
    """Generates video scripts via Claude API with local fallback."""

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.ANTHROPIC_API_KEY
        self.use_local = False
        if not ANTHROPIC_AVAILABLE or not key:
            logger.warning("Claude API not available, using local script generator")
            self.use_local = True
        else:
            self.client = anthropic.Anthropic(api_key=key)
            self.model = settings.ANTHROPIC_MODEL
            logger.info(f"ScriptGenerator initialized with Claude model {self.model}")

    def _generate_local(self, keyword: str, niche: str = "general",
                        duration: str = "short") -> Dict:
        """Generate a script locally without API (fallback)."""
        templates = _LOCAL_TEMPLATES.get(niche, _GENERIC)
        hook = random.choice(templates["hooks"])
        body = random.choice(templates["bodies"])
        outro = templates["outros"]

        # Build narration text
        narration = f"{hook} {body} {outro}"

        # Estimate word count for duration
        words = narration.split()
        if duration == "short":
            # Trim to ~120 words for 60s
            words = words[:120]
            narration = " ".join(words)
        else:
            # Keep full text for longer video
            narration = " ".join(words)

        title = f"How to {keyword.replace('-', ' ').title()} - Complete Guide"
        description = (
            f"Learn everything about {keyword} in this comprehensive guide. "
            f"We cover the most important strategies, tips, and insights "
            f"that will help you understand {keyword} better.\n\n"
            f"Timestamps:\n0:00 - Introduction\n0:03 - {keyword}\n"
            f"1:00 - Key Strategies\n1:30 - Final Thoughts\n\n"
            f"#{''.join(keyword.title().split())}"
        )
        tags = [keyword, f"{keyword} tips", f"how to {keyword}",
                "finance", "investing", "money", "wealth",
                "passive income", "financial freedom", "guide"]

        script = {
            "title": title,
            "description": description,
            "tags": tags,
            "hook": hook,
            "script": {
                "sections": [
                    {"type": "hook", "duration_seconds": 3,
                     "narration": hook, "visual_direction": "Dramatic opening shot"},
                    {"type": "intro", "duration_seconds": 10,
                     "narration": f"Welcome! Today we're talking about {keyword}.",
                     "visual_direction": "Title card with topic name"},
                    {"type": "body", "duration_seconds": 30,
                     "narration": body, "visual_direction": "Relevant stock footage"},
                    {"type": "outro", "duration_seconds": 10,
                     "narration": outro, "visual_direction": "Subscribe animation"},
                ]
            },
            "compliance_notes": "Financial content - add disclaimer if providing specific advice",
            "_source": "local_template",
        }

        logger.info(f"Local script generated for: {keyword}")
        return script

    def generate_script(self, keyword: str, niche: str = "general",
                        video_style: str = "faceless",
                        duration: str = "short",
                        language: str = "en") -> Dict:
        """
        Generate a complete video script with SEO metadata.

        Args:
            keyword: Target keyword/topic
            niche: Content niche
            video_style: "faceless" or "avatar_talking"
            duration: "short" (60s) or "long" (5-10min)
            language: Output language code

        Returns:
            Dict with: script, title, description, tags, hook
        """
        if self.use_local:
            return self._generate_local(keyword, niche, duration)

        duration_guide = (
            "60 seconds (short, punchy, 100-150 words)"
            if duration == "short"
            else "5-10 minutes (detailed, 1000-2000 words)"
        )

        style_guide = (
            "Visual-focused: describe scenes/images for each section. "
            "No on-screen presenter."
            if video_style == "faceless"
            else "Include presenter dialogue and stage directions."
        )

        prompt = f"""You are an expert YouTube content creator. Generate a complete video script package.

TARGET KEYWORD: {keyword}
NICHE: {niche}
DURATION: {duration_guide}
VIDEO STYLE: {video_style} — {style_guide}
LANGUAGE: {language}

Generate a JSON response with EXACTLY this structure (no extra text, just valid JSON):

{{
  "title": "SEO-optimized title (max 70 chars, includes keyword naturally, click-worthy)",
  "description": "SEO description (2-3 paragraphs, includes keyword 2-3 times, includes a call to action)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "hook": "The first 3-second hook line that grabs attention immediately",
  "script": {{
    "sections": [
      {{
        "type": "hook",
        "duration_seconds": 3,
        "narration": "The opening hook text",
        "visual_direction": "What to show on screen"
      }},
      {{
        "type": "intro",
        "duration_seconds": 10,
        "narration": "Introduction text",
        "visual_direction": "What to show on screen"
      }},
      {{
        "type": "body",
        "duration_seconds": 30,
        "narration": "Main content section",
        "visual_direction": "What to show on screen"
      }},
      {{
        "type": "outro",
        "duration_seconds": 7,
        "narration": "Closing with CTA",
        "visual_direction": "What to show on screen"
      }}
    ]
  }},
  "compliance_notes": "Any notes about content that needs disclaimer (medical, financial, etc.)"
}}

IMPORTANT RULES:
- The hook MUST create curiosity or urgency in the first 3 seconds
- Use simple, conversational language
- Include specific numbers/facts when possible
- End with a clear call to action (subscribe, like, comment)
- Every section must have a visual_direction for the video editor
- Generate ONLY valid JSON, no markdown, no extra text"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()

            # Try to extract JSON from response
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(response_text)

            logger.info(f"Script generated for keyword: {keyword}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            return {
                "title": f"Video about {keyword}",
                "description": f"A video about {keyword}",
                "tags": [keyword],
                "hook": f"Did you know about {keyword}?",
                "script": {"sections": []},
                "compliance_notes": "",
                "_parse_error": str(e),
                "_raw_response": response_text[:2000]
            }
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def generate_title_variants(self, keyword: str, count: int = 3) -> list:
        """Generate multiple title variants for A/B testing."""
        try:
            prompt = f"""Generate {count} YouTube video title variants for the keyword: "{keyword}"

Requirements:
- Each title must be under 70 characters
- Include the keyword naturally
- Use power words and curiosity gaps
- Different emotional angles (fear, curiosity, benefit)

Return ONLY a JSON array of strings, no extra text:
["Title 1", "Title 2", "Title 3"]"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]

            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to generate title variants: {e}")
            return [f"Amazing Facts About {keyword}"]
