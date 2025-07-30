import os

print("🧨 I AM INSIDE:", __file__)
with open("i_am_here.txt", "w") as f:
    f.write("This is the main.py being executed:\n" + os.path.abspath(__file__))

from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os, json, random, uuid
import stripe
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()



app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)

load_dotenv()
client = OpenAI()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN = os.getenv("DOMAIN")

# with open("preformgpt_final_guardrail_prompt.txt", "r", encoding="utf-8") as f:
#     collapse_prompt = f.read()

with open("preformgpt_feedback_prompt.txt", "r", encoding="utf-8") as f:
    feedback_prompt_template = f.read()

COLORS = {
    "pulse": "flickering orange",
    "spiral": "glass teal",
    "mirror": "reflective ice",
    "echo": "lavender mist",
    "fracture": "split vein",
    "flood": "drowned steel",
    "veil": "vanishing amber",
    "thorn": "venomstem"
}

METAPHOR_BANK = {
    "pulse": ["A flickering bulb in a dark hallway."],
    "spiral": ["A whirlpool that pulls you under as you try to reach the surface."],
    "mirror": ["A cracked mirror that reflects every angle but none are true."],
    "echo": ["A sound that bounces back louder each time you try to silence it."],
    "fracture": ["A broken bone that never healed straight."],
    "flood": ["A dam bursting from the inside."],
    "veil": ["A curtain drawn across the mind's eye."],
    "thorn": ["A splinter lodged in your sense of self."]
}

def normalize_types(data):
    for field in ["trigger_type", "oscillation_type", "interference_type", "collapse_type"]:
        t = data.get(field, "spiral").lower()
        if t not in COLORS:
            t = "spiral"
        data[field] = t
    return data

def parse_collapse_sections(content):
    """Parse the collapse content into individual sections"""
    if not content:
        return {}
    
    sections = {}
    current_section = None
    current_content = []
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a section header (Title Case or ALL CAPS, no punctuation)
        # Also handle mixed case headers like "Triggers and Avoidances"
        is_header = (
            line.isupper() or 
            (line.istitle() and len(line.split()) <= 4) or
            (len(line.split()) <= 4 and line[0].isupper())
        ) and len(line) > 3 and not any(char in line for char in '.,!?')
        
        if is_header:
            # Save previous section
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line.lower().replace(' ', '_')
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections

def load_collapse_reading(collapse_type):
    paths = [
        f"final/{collapse_type}.txt",
        f"readings/{collapse_type}.txt",
        f"{collapse_type}.txt",
        f"text_files/{collapse_type}.txt",
        f"collapse_readings/{collapse_type}.txt"
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content and len(content) > 100:
                return content
    return f"[❌ ERROR: Could not load reading file for collapse type '{collapse_type}']"

def load_collapse_sections(collapse_type):
    """Load and parse all sections from the collapse reading file"""
    content = load_collapse_reading(collapse_type)
    if content.startswith("[❌ ERROR"):
        return {}
    
    sections = parse_collapse_sections(content)
    
    # Map section names to expected field names
    section_mapping = {
        "human_profile": "human_profile",
        "primary_motivation": "primary_motivation", 
        "negative_habits": "negative_habits",
        "emotional_baseline": "emotional_baseline",
        "expanded_collapse_cycle": "expanded_collapse_cycle",
        "key_strengths": "key_strengths",
        "hidden_costs": "hidden_costs",
        "triggers_and_avoidances": "triggers_avoidances",
        "triggers_avoidances": "triggers_avoidances",
        "social_impact": "social_impact",
        "common_roles_and_careers": "common_roles_careers",
        "common_roles_careers": "common_roles_careers",
        "break_pattern_strategy": "break_pattern_strategy",
        "color_meaning_and_symbol": "color_symbol",
        "color_symbol": "color_symbol"
    }
    
    # Map sections to their expected field names
    mapped_sections = {}
    for section_name, content in sections.items():
        if section_name in section_mapping:
            mapped_sections[section_mapping[section_name]] = content
        else:
            # Keep original name if no mapping found
            mapped_sections[section_name] = content
    
    return mapped_sections

def generate_fallback_content(field, data):
    t = data.get("collapse_type", "unknown").capitalize()
    if field == "loop_mirror":
        return (
            "You already know. You've been running this loop for so long that it feels like you — but it isn't. "
            "The version of you beneath all this isn't chaotic, or broken, or hard to love. "
            "You just forgot how to stop moving. That forgetting became survival. And that survival became your mask."
        )
    
    # Get the specific collapse type for each phase
    if field == "trigger_summary":
        collapse_type = data.get("trigger_type", "fracture").lower()
        intro = {
            "pulse": "You spark like a Pulse, flickering between certainty and doubt.",
            "spiral": "You spark like a Spiral, coiling inward as you seek deeper understanding.",
            "mirror": "You spark like a Mirror, reflecting and distorting your own image.",
            "echo": "You spark like an Echo, amplifying and repeating certain patterns.",
            "fracture": "You spark like a Fracture, breaking and splitting under pressure.",
            "flood": "You spark like a Flood, overwhelming the senses with your intensity.",
            "veil": "You spark like a Veil, shrouding your true self in mystery.",
            "thorn": "You spark like a Thorn, protecting yourself with sharp boundaries."
        }.get(collapse_type, f"You spark like a {collapse_type.capitalize()}.")
        
        return f"{intro} This is where your collapse begins - the spark that ignites your particular way of moving through the world."
    
    elif field == "oscillation_summary":
        collapse_type = data.get("oscillation_type", "fracture").lower()
        intro = {
            "pulse": "Your mind moves like a Pulse, flickering between states of certainty and doubt.",
            "spiral": "Your mind moves like a Spiral, getting caught in recursive patterns of thought.",
            "mirror": "Your mind moves like a Mirror, reflecting and distorting your own image.",
            "echo": "Your mind moves like an Echo, amplifying and repeating certain patterns.",
            "fracture": "Your mind moves like a Fracture, breaking and splitting under pressure.",
            "flood": "Your mind moves like a Flood, overwhelming your emotional capacity.",
            "veil": "Your mind moves like a Veil, hiding and obscuring your true self.",
            "thorn": "Your mind moves like a Thorn, protecting yourself with sharp boundaries."
        }.get(collapse_type, f"Your mind moves like a {collapse_type.capitalize()}.")
        
        return f"{intro} This is how your mind moves between states - the rhythm of your internal landscape."
    
    elif field == "interference_summary":
        collapse_type = data.get("interference_type", "fracture").lower()
        intro = {
            "pulse": "Your signal twists like a Pulse, flickering between clarity and confusion.",
            "spiral": "Your signal twists like a Spiral, getting lost in recursive thinking.",
            "mirror": "Your signal twists like a Mirror, distorting your self-perception.",
            "echo": "Your signal twists like an Echo, amplifying negative patterns.",
            "fracture": "Your signal twists like a Fracture, breaking under pressure.",
            "flood": "Your signal twists like a Flood, overwhelming your emotional capacity.",
            "veil": "Your signal twists like a Veil, obscuring your true self.",
            "thorn": "Your signal twists like a Thorn, creating defensive barriers."
        }.get(collapse_type, f"Your signal twists like a {collapse_type.capitalize()}.")
        
        return f"{intro} This is what gets in the way - the distortions that shape your experience."
    
    elif field == "collapse_plaintext_summary":
        collapse_type = data.get("collapse_type", "fracture").lower()
        intro = {
            "pulse": "You collapse like a Pulse, flickering between states of certainty and doubt.",
            "spiral": "You collapse like a Spiral, getting caught in recursive patterns of thought.",
            "mirror": "You collapse like a Mirror, reflecting and distorting your own image.",
            "echo": "You collapse like an Echo, amplifying and repeating certain patterns.",
            "fracture": "You collapse like a Fracture, breaking and splitting under pressure.",
            "flood": "You collapse like a Flood, overwhelming your emotional capacity.",
            "veil": "You collapse like a Veil, hiding and obscuring your true self.",
            "thorn": "You collapse like a Thorn, protecting yourself with sharp boundaries."
        }.get(collapse_type, f"You collapse like a {collapse_type.capitalize()}.")
        
        return f"{intro} This is where you always end up - the final destination of your particular way of being."
    
    return f"[Missing {field} for collapse type {t}]"

def generate_rich_interpretation(quote, section, collapse_type):
    """Generate rich, dynamic interpretation for quote in specific section context"""
    
    # Define which sections should show quote blocks (the rest should not)
    quote_sections = [
        "primary_motivation", "negative_habits", "emotional_baseline", 
        "expanded_collapse_cycle", "key_strengths", "hidden_costs",
        "triggers_avoidances", "social_impact", "break_pattern_strategy"
    ]
    
    # If this section shouldn't show quotes, return empty
    if section not in quote_sections:
        return ""
    
    # Section-specific psychological insights for each collapse type
    section_insights = {
        "primary_motivation": {
            "pulse": {
                "pattern": "seeking stability in uncertainty",
                "insight": "This quote echoes the Pulse collapse tendency to reshape one's identity with external validation. Your desire for clarity and certainty mirrors the way Pulse types seek symbolic self-affirmation.",
                "impact": "This drive shapes every decision and relationship, making you crave stability."
            },
            "spiral": {
                "pattern": "understanding deeper patterns",
                "insight": "This quote reflects the Spiral's recursive quest for meaning beneath surface appearances. Your search for deeper understanding reveals how you coil inward to find answers that others might miss.",
                "impact": "This intellectual drive becomes your primary motivation, sometimes at the cost of action."
            },
            "mirror": {
                "pattern": "seeing yourself clearly",
                "insight": "This quote captures the Mirror's need for authentic self-perception. Your desire for clarity reflects how you seek undistorted truth in a world of reflections.",
                "impact": "This quest for clarity shapes how you present yourself to the world."
            },
            "echo": {
                "pattern": "finding resonance and connection",
                "insight": "This quote reveals the Echo's drive to amplify meaningful connections. Your desire for impact shows how you seek to make your voice heard and your feelings understood.",
                "impact": "This drive for resonance shapes how you communicate and connect."
            },
            "fracture": {
                "pattern": "breaking free from constraints",
                "insight": "This quote embodies the Fracture's need to shatter limitations. Your desire for freedom reflects how you seek to break through barriers that hold you back.",
                "impact": "This urge to break free shapes your approach to challenges and relationships."
            },
            "flood": {
                "pattern": "managing overwhelming feelings",
                "insight": "This quote shows the Flood's struggle to stay afloat in emotional waters. Your desire for balance reflects how you seek to manage the intensity of your feelings.",
                "impact": "This drive to manage overwhelm shapes how you process and express emotions."
            },
            "veil": {
                "pattern": "protecting your inner world",
                "insight": "This quote reveals the Veil's need to keep your true self safe. Your desire for protection shows how you maintain boundaries around your core identity.",
                "impact": "This protective drive shapes how you reveal yourself to others."
            },
            "thorn": {
                "pattern": "defending what matters",
                "insight": "This quote captures the Thorn's drive to protect what's precious. Your desire for security reflects how you create boundaries around what matters most.",
                "impact": "This defensive drive shapes how you approach relationships and challenges."
            }
        },
        "negative_habits": {
            "pulse": {
                "pattern": "flickering between commitments",
                "insight": "This quote shows the Pulse's tendency to shift rapidly between different approaches. Your struggle with consistency reflects how you flicker between certainty and doubt.",
                "impact": "This pattern creates instability in your habits and routines."
            },
            "spiral": {
                "pattern": "getting lost in analysis",
                "insight": "This quote reveals the Spiral's tendency to overthink and get stuck in recursive patterns. Your struggle with action reflects how you coil deeper into thought.",
                "impact": "This pattern prevents you from moving forward with decisions."
            },
            "mirror": {
                "pattern": "distorting self-perception",
                "insight": "This quote shows the Mirror's tendency to see yourself through a cracked lens. Your struggle with self-acceptance reflects how you distort your own image.",
                "impact": "This pattern creates barriers to authentic self-expression."
            },
            "echo": {
                "pattern": "amplifying negative patterns",
                "insight": "This quote reveals the Echo's tendency to repeat and amplify harmful behaviors. Your struggle with change reflects how you get stuck in resonant loops.",
                "impact": "This pattern makes it difficult to break free from destructive cycles."
            },
            "fracture": {
                "pattern": "sudden emotional breaks",
                "insight": "This quote shows the Fracture's tendency to shatter under pressure. Your struggle with stability reflects how you break when faced with challenges.",
                "impact": "This pattern creates unpredictable responses to stress."
            },
            "flood": {
                "pattern": "overwhelming emotional responses",
                "insight": "This quote reveals the Flood's tendency to get submerged by feelings. Your struggle with emotional regulation reflects how you drown in intense emotions.",
                "impact": "This pattern makes it difficult to maintain emotional balance."
            },
            "veil": {
                "pattern": "hiding from challenges",
                "insight": "This quote shows the Veil's tendency to obscure difficult truths. Your struggle with confrontation reflects how you hide behind protective layers.",
                "impact": "This pattern prevents authentic engagement with problems."
            },
            "thorn": {
                "pattern": "defensive responses",
                "insight": "This quote reveals the Thorn's tendency to protect yourself with sharp boundaries. Your struggle with vulnerability reflects how you keep others at bay.",
                "impact": "This pattern creates barriers to intimacy and connection."
            }
        },
        "emotional_baseline": {
            "pulse": {
                "pattern": "flickering between emotional states",
                "insight": "This quote captures the Pulse's emotional landscape that shifts rapidly between certainty and doubt. Your feelings flicker like a bulb in a dark hallway, casting shadows that dance between extremes.",
                "impact": "This creates a foundation of uncertainty that affects every relationship and decision."
            },
            "spiral": {
                "pattern": "recursive emotional processing",
                "insight": "This quote shows the Spiral's tendency to coil inward, creating deeper and deeper loops of thought. Your emotions get trapped in recursive patterns, unable to break free from the cycle.",
                "impact": "This recursive processing becomes your emotional baseline, making it hard to move forward."
            },
            "mirror": {
                "pattern": "reflective emotional distortion",
                "insight": "This quote reveals the Mirror's tendency to see emotions through a cracked lens. You process feelings through the distortion of self-criticism and doubt.",
                "impact": "This distortion becomes your emotional foundation, coloring every experience."
            },
            "echo": {
                "pattern": "amplified emotional resonance",
                "insight": "This quote shows the Echo's tendency to amplify emotions with each repetition. Your feelings echo back louder each time you try to silence them.",
                "impact": "This amplification becomes your emotional baseline, overwhelming your capacity to process."
            },
            "fracture": {
                "pattern": "sudden emotional breaks",
                "insight": "This quote captures the Fracture's tendency to shatter unexpectedly. Your emotional stability breaks like bone that never healed properly.",
                "impact": "These sudden breaks become your emotional baseline, making trust difficult."
            },
            "flood": {
                "pattern": "overwhelming emotional tides",
                "insight": "This quote shows the Flood's tendency to rise like waters that submerge everything. Your emotions overwhelm rational thought, drowning out clarity.",
                "impact": "This overwhelm becomes your emotional baseline, making it hard to stay afloat."
            },
            "veil": {
                "pattern": "hidden emotional depths",
                "insight": "This quote reveals the Veil's tendency to draw curtains across true feelings. You obscure your emotional reality behind protective layers.",
                "impact": "This hiding becomes your emotional baseline, preventing authentic connection."
            },
            "thorn": {
                "pattern": "protective emotional armor",
                "insight": "This quote shows the Thorn's tendency to grow emotional spikes for protection. You create sharp boundaries that also isolate you from warmth.",
                "impact": "This defensive posture becomes your emotional baseline, keeping others at a safe distance."
            }
        },
        "expanded_collapse_cycle": {
            "pulse": {
                "pattern": "cycles of uncertainty and doubt",
                "insight": "Your collapse begins with a flicker of uncertainty that grows into a cycle of doubt. This quote captures the moment when you start questioning everything, unable to find stable ground.",
                "impact": "This cycle traps you in a pattern of indecision and second-guessing."
            },
            "spiral": {
                "pattern": "recursive thinking traps",
                "insight": "Your collapse begins when you get caught in a thought loop that pulls you deeper and deeper. This quote shows how you spiral inward, unable to break free from your own mind.",
                "impact": "This recursive pattern becomes a trap that prevents forward movement."
            },
            "mirror": {
                "pattern": "self-reflection distortion",
                "insight": "Your collapse begins when you see yourself through a cracked mirror, distorting your reality. This quote reveals how self-criticism becomes the lens through which you view everything.",
                "impact": "This distortion cycle prevents you from seeing yourself clearly."
            },
            "echo": {
                "pattern": "amplified repetition cycles",
                "insight": "Your collapse begins when you start amplifying and repeating negative patterns. This quote shows how you get stuck in emotional loops that grow louder with each repetition.",
                "impact": "This amplification cycle makes it impossible to move past painful experiences."
            },
            "fracture": {
                "pattern": "sudden breaking cycles",
                "insight": "Your collapse begins with a sudden break that shatters your stability. This quote captures the moment when your emotional foundation gives way unexpectedly.",
                "impact": "These sudden breaks create a cycle of instability and distrust."
            },
            "flood": {
                "pattern": "overwhelm cycles",
                "insight": "Your collapse begins when you get overwhelmed by emotional tides that drown your clarity. This quote shows how you sink beneath the weight of your own feelings.",
                "impact": "This overwhelm cycle makes it impossible to process or move forward."
            },
            "veil": {
                "pattern": "hiding and obscuring cycles",
                "insight": "Your collapse begins when you start hiding your true self behind protective layers. This quote reveals how you draw curtains across your reality to avoid vulnerability.",
                "impact": "This hiding cycle prevents authentic connection and resolution."
            },
            "thorn": {
                "pattern": "defensive barrier cycles",
                "insight": "Your collapse begins when you grow protective spikes that keep others at bay. This quote shows how you create defensive barriers that also isolate you.",
                "impact": "This defensive cycle prevents intimacy while maintaining protection."
            }
        },
        "triggers_avoidances": {
            "pulse": {
                "pattern": "flickering between engagement and withdrawal",
                "insight": "You're triggered by situations that force you to choose between certainty and doubt. This quote captures the moment when uncertainty becomes overwhelming, making you flicker between states.",
                "impact": "This trigger pattern makes it difficult to commit to decisions or relationships."
            },
            "spiral": {
                "pattern": "getting stuck in recursive thinking",
                "insight": "You're triggered by situations that send you into deep thought loops. This quote shows how certain circumstances activate your recursive thinking patterns.",
                "impact": "This trigger pattern traps you in intellectual analysis that prevents action."
            },
            "mirror": {
                "pattern": "distorting self-perception",
                "insight": "You're triggered by situations that force you to see yourself clearly. This quote reveals how certain circumstances activate your self-critical lens.",
                "impact": "This trigger pattern makes it difficult to see yourself accurately."
            },
            "echo": {
                "pattern": "amplifying emotional patterns",
                "insight": "You're triggered by situations that activate your emotional amplification. This quote shows how certain circumstances make your feelings echo and grow louder.",
                "impact": "This trigger pattern makes it difficult to process emotions without escalation."
            },
            "fracture": {
                "pattern": "causing sudden emotional breaks",
                "insight": "You're triggered by situations that put pressure on your emotional stability. This quote captures the moment when pressure causes your foundation to suddenly give way.",
                "impact": "This trigger pattern makes it difficult to trust in your emotional stability."
            },
            "flood": {
                "pattern": "overwhelming emotional capacity",
                "insight": "You're triggered by situations that exceed your emotional capacity. This quote shows how certain circumstances cause you to sink beneath overwhelming feelings.",
                "impact": "This trigger pattern makes it difficult to stay emotionally regulated."
            },
            "veil": {
                "pattern": "making you hide and obscure",
                "insight": "You're triggered by situations that make you want to disappear. This quote reveals how certain circumstances activate your protective hiding instincts.",
                "impact": "This trigger pattern makes it difficult to show your true self."
            },
            "thorn": {
                "pattern": "activating defensive responses",
                "insight": "You're triggered by situations that make you feel threatened. This quote shows how certain circumstances activate your protective spikes and defensive barriers.",
                "impact": "This trigger pattern makes it difficult to lower your guard and connect."
            }
        },
        "social_impact": {
            "pulse": {
                "pattern": "creating uncertainty in relationships",
                "insight": "Your uncertainty affects how others perceive and interact with you. This quote shows how your flickering between states creates confusion and instability in your relationships.",
                "impact": "This pattern makes it difficult for others to know how to support you consistently."
            },
            "spiral": {
                "pattern": "getting lost in your own thoughts",
                "insight": "Your recursive thinking pulls you away from the people around you. This quote reveals how you disappear into your own mind, leaving others feeling disconnected.",
                "impact": "This pattern makes it difficult to maintain presence in relationships."
            },
            "mirror": {
                "pattern": "distorting how others see you",
                "insight": "Your self-reflection affects how others perceive and understand you. This quote shows how your distorted self-perception influences your social interactions.",
                "impact": "This pattern makes it difficult for others to see your true self clearly."
            },
            "echo": {
                "pattern": "amplifying emotional resonance",
                "insight": "Your emotional amplification affects the people around you. This quote reveals how your amplified feelings create intense but sometimes overwhelming connections.",
                "impact": "This pattern creates deep but potentially unstable relationships."
            },
            "fracture": {
                "pattern": "sudden breaks that confuse others",
                "insight": "Your sudden emotional breaks affect how others trust and rely on you. This quote shows how your unexpected collapses create uncertainty in your relationships.",
                "impact": "This pattern makes it difficult for others to predict or support you consistently."
            },
            "flood": {
                "pattern": "overwhelming social connections",
                "insight": "Your emotional overwhelm affects how others can connect with you. This quote reveals how your intense feelings can drown out the needs of others.",
                "impact": "This pattern makes it difficult to maintain balanced relationships."
            },
            "veil": {
                "pattern": "hiding from authentic connection",
                "insight": "Your protective hiding affects how others can truly know you. This quote shows how your veils prevent others from seeing your authentic self.",
                "impact": "This pattern makes it difficult to form deep, intimate connections."
            },
            "thorn": {
                "pattern": "keeping others at a safe distance",
                "insight": "Your defensive barriers affect how others can get close to you. This quote reveals how your protective spikes create safe but potentially lonely relationships.",
                "impact": "This pattern protects you but also isolates you from intimacy."
            }
        },
        "break_pattern_strategy": {
            "pulse": {
                "pattern": "finding stability in uncertainty",
                "insight": "You need to learn how to find solid ground without needing absolute certainty. This quote shows the challenge of accepting uncertainty while still making confident decisions.",
                "impact": "This strategy requires developing trust in your own judgment despite the unknown."
            },
            "spiral": {
                "pattern": "breaking free from recursive thinking",
                "insight": "You need to learn how to interrupt your thought loops and take action. This quote reveals the challenge of moving from analysis to implementation.",
                "impact": "This strategy requires developing the ability to act without complete understanding."
            },
            "mirror": {
                "pattern": "seeing yourself clearly without distortion",
                "insight": "You need to learn how to see yourself accurately without the lens of self-criticism. This quote shows the challenge of developing compassionate self-perception.",
                "impact": "This strategy requires developing self-acceptance alongside self-awareness."
            },
            "echo": {
                "pattern": "stopping negative amplification",
                "insight": "You need to learn how to process emotions without amplifying them. This quote reveals the challenge of feeling deeply without getting overwhelmed.",
                "impact": "This strategy requires developing emotional regulation alongside emotional depth."
            },
            "fracture": {
                "pattern": "healing from sudden emotional breaks",
                "insight": "You need to learn how to rebuild trust in your emotional stability. This quote shows the challenge of developing resilience after unexpected collapses.",
                "impact": "This strategy requires developing emotional strength alongside vulnerability."
            },
            "flood": {
                "pattern": "managing overwhelming feelings",
                "insight": "You need to learn how to stay afloat in intense emotional waters. This quote reveals the challenge of processing deep feelings without drowning.",
                "impact": "This strategy requires developing emotional capacity alongside emotional depth."
            },
            "veil": {
                "pattern": "revealing your true self safely",
                "insight": "You need to learn how to lower your protective barriers without losing your sense of safety. This quote shows the challenge of authentic vulnerability.",
                "impact": "This strategy requires developing trust alongside self-protection."
            },
            "thorn": {
                "pattern": "lowering defenses without losing protection",
                "insight": "You need to learn how to soften your protective spikes without becoming vulnerable to harm. This quote reveals the challenge of intimacy without losing your strength.",
                "impact": "This strategy requires developing openness alongside healthy boundaries."
            }
        }
    }
    
    # Get the specific insights for this section and collapse type
    insights = section_insights.get(section, {}).get(collapse_type, {})
    if not insights:
        return ""
    
    pattern = insights.get("pattern", f"your {collapse_type} pattern")
    insight = insights.get("insight", "")
    impact = insights.get("impact", "")
    
    # Generate rich, dynamic interpretation
    interpretation = f"You said, '{quote}.' {insight} {impact}"
    
    return interpretation



def fix_summary_fields(data):
    for phase in ["trigger", "oscillation", "interference"]:
        field = f"{phase}_summary"
        if not data.get(field) or len(data.get(field).strip()) < 20:
            # Use the specific collapse type for this phase
            t = data.get(f"{phase}_type", "Unknown").capitalize()
            q = data.get(f"{phase}_quote", "")
            i = data.get(f"{phase}_interpretation", "")
            if q and i:
                if t.lower() not in COLORS:
                    t = "Spiral"
                intro = {
                    "trigger": f"You spark like a {t}.",
                    "oscillation": f"Your mind moves like a {t}.",
                    "interference": f"Your signal twists like a {t}."
                }.get(phase, f"You move like a {t}.")
                data[field] = f"{intro} {q} {i}"
            else:
                data[field] = generate_fallback_content(field, data)

    if not data.get("collapse_plaintext_summary"):
        q = data.get("collapse_quote", "")
        i = data.get("collapse_interpretation", "")
        t = data.get("collapse_type", "Unknown").capitalize()
        if t.lower() not in COLORS:
            t = "Spiral"
        if q and i:
            data["collapse_plaintext_summary"] = f"You collapse like a {t}. {q} {i}"
        else:
            data["collapse_plaintext_summary"] = generate_fallback_content("collapse_plaintext_summary", data)

    return data

def ensure_all_required_fields(data):
    # 🔧 ENFORCE ALL 4 CRITICAL RULES
    
    # 1. ENFORCE 3-SENTENCE SUMMARIES
    summary_fields = ["trigger_summary", "oscillation_summary", "interference_summary", "collapse_plaintext_summary"]
    for field in summary_fields:
        if data.get(field):
            content = data[field].strip()
            sentences = [s.strip() for s in content.split('.') if s.strip()]
            if len(sentences) != 3:
                print(f"⚠️ {field} has {len(sentences)} sentences, regenerating to enforce 3 sentences")
                data[field] = generate_fallback_content(field, data)
    
    # 2. ENFORCE COMPLETE COLOR_SYMBOL FORMAT
    collapse_type = data.get("collapse_type", "fracture").lower()
    color_mappings = {
        "pulse": "flickering orange — the uncertainty of rapid shifts. Your thoughts flicker like a bulb in a dark hallway, casting shadows that dance between certainty and doubt.",
        "spiral": "glass teal — the shimmer of recursive fragility. Your mind coils inward and outward like breath underwater, creating patterns that shimmer with the fragility of understanding.",
        "mirror": "reflective ice — the distortion of self-perception. You see yourself through cracked glass that never shows the same angle twice, each reflection a new distortion of truth.",
        "echo": "lavender mist — the lingering of past voices. Your thoughts echo back louder each time you try to silence them, creating a mist of memories that never fully dissipates.",
        "fracture": "split vein — the sudden breaking of continuity. Your experience shatters like bone that never healed straight, creating fault lines that run through every moment.",
        "flood": "drowned steel — the overwhelm of being submerged. You sink beneath the weight of your own thoughts, like steel that has been submerged in waters too deep to fathom.",
        "veil": "vanishing amber — the disappearing act of avoidance. You draw curtains across your mind's eye, creating a golden haze that obscures what you most need to see.",
        "thorn": "venomstem — the protective piercing of boundaries. You grow spikes to keep the world at bay, each thorn a defense that also isolates you from the warmth you crave."
    }
    
    # Always ensure color_symbol is complete and rich
    current_color_symbol = data.get("color_symbol", "").strip()
    if not current_color_symbol or len(current_color_symbol) < 100 or "—" not in current_color_symbol:
        data["color_symbol"] = color_mappings.get(collapse_type, color_mappings["fracture"])
        print(f"🎨 Generated complete color_symbol for {collapse_type}")
    elif len(current_color_symbol) < 150:
        # If it's too short, enhance it
        base_color = color_mappings.get(collapse_type, color_mappings["fracture"])
        data["color_symbol"] = base_color
        print(f"🎨 Enhanced color_symbol for {collapse_type}")
    
    # 3. ENFORCE ALL REQUIRED SECTIONS
    required_fields = [
        "human_profile", "primary_motivation", "negative_habits", "emotional_baseline",
        "expanded_collapse_cycle", "key_strengths", "hidden_costs", "triggers_avoidances",
        "social_impact", "common_roles_careers", "break_pattern_strategy"
    ]
    
    # Load collapse sections from the reading file
    collapse_sections = load_collapse_sections(collapse_type)
    
    # Override fields with content from collapse reading file or generate fallbacks
    for field in required_fields:
        if field in collapse_sections and collapse_sections[field]:
            data[field] = collapse_sections[field]
        elif not data.get(field) or len(str(data.get(field)).strip()) < 10:
            data[field] = generate_fallback_content(field, data)
            print(f"📝 Generated fallback for {field}")

    if not data.get("reflection_summary"):
        collapse_type = data.get("collapse_type", "unknown").capitalize()
        data["reflection_summary"] = f"Your {collapse_type} collapse pattern reveals a complex relationship between internal experience and external presentation."

    return fix_summary_fields(data)

def validate_complete_json(data, user_id):
    """Validate that JSON contains all required fields and retry if incomplete"""
    
    # Define all required fields for complete JSON
    required_fields = [
        "trigger_summary", "oscillation_summary", "interference_summary", "collapse_plaintext_summary",
        "loop_mirror", "trigger_type", "oscillation_type", "interference_type", "collapse_type",
        "human_profile", "primary_motivation", "negative_habits", "emotional_baseline",
        "expanded_collapse_cycle", "key_strengths", "hidden_costs", "triggers_avoidances",
        "social_impact", "common_roles_careers", "break_pattern_strategy", "color_symbol",
        "collapse_reading", "drizzle"
    ]
    
    # Check for missing fields
    missing_fields = []
    for field in required_fields:
        if not data.get(field):
            missing_fields.append(field)
        elif isinstance(data.get(field), str) and len(data.get(field).strip()) < 2:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"⚠️ Missing or incomplete fields for user {user_id}: {missing_fields}")
        return False
    
    # Validate drizzle structure - be more flexible for real user data
    drizzle = data.get("drizzle", [])
    if not isinstance(drizzle, list) or len(drizzle) < 3:
        print(f"⚠️ Drizzle data incomplete for user {user_id}: {len(drizzle)} items")
        return False
    
    # Validate color_symbol format - be more flexible
    color_symbol = data.get("color_symbol", "")
    if not color_symbol or len(color_symbol) < 10:
        print(f"⚠️ Color symbol incomplete for user {user_id}")
        return False
    
    print(f"✅ JSON validation passed for user {user_id}")
    return True

def validate_complete_json_flexible(data, user_id):
    """Flexible validation that logs issues but doesn't fail the request"""
    
    # Define critical fields that must be present
    critical_fields = [
        "trigger_summary", "oscillation_summary", "interference_summary", "collapse_plaintext_summary",
        "loop_mirror", "trigger_type", "oscillation_type", "interference_type", "collapse_type"
    ]
    
    # Define optional fields that should be present but won't fail the request
    optional_fields = [
        "human_profile", "primary_motivation", "negative_habits", "emotional_baseline",
        "expanded_collapse_cycle", "key_strengths", "hidden_costs", "triggers_avoidances",
        "social_impact", "common_roles_careers", "break_pattern_strategy", "color_symbol",
        "collapse_reading", "drizzle", "loop_lock"
    ]
    
    missing_critical = []
    missing_optional = []
    
    # Check critical fields
    for field in critical_fields:
        if not data.get(field):
            missing_critical.append(field)
        elif isinstance(data.get(field), str) and len(data.get(field).strip()) < 2:
            missing_critical.append(field)
    
    # Check optional fields
    for field in optional_fields:
        if not data.get(field):
            missing_optional.append(field)
        elif isinstance(data.get(field), str) and len(data.get(field).strip()) < 2:
            missing_optional.append(field)
    
    # If critical fields are missing, fail
    if missing_critical:
        print(f"❌ CRITICAL fields missing for user {user_id}: {missing_critical}")
        return {
            "valid": False,
            "missing_fields": missing_critical,
            "error": "Critical fields missing"
        }
    
    # Log optional field issues but don't fail
    if missing_optional:
        print(f"⚠️ Optional fields missing for user {user_id}: {missing_optional}")
    
    # Validate drizzle structure - be very flexible
    drizzle = data.get("drizzle", [])
    if not isinstance(drizzle, list):
        print(f"⚠️ Drizzle is not a list for user {user_id}, converting to empty list")
        data["drizzle"] = []
    
    # Validate color_symbol format - be very flexible
    color_symbol = data.get("color_symbol", "")
    if not color_symbol or len(color_symbol) < 5:
        print(f"⚠️ Color symbol incomplete for user {user_id}, using fallback")
        collapse_type = data.get("collapse_type", "fracture")
        color_mappings = {
            "pulse": "flickering orange — the uncertainty of rapid shifts.",
            "spiral": "glass teal — the shimmer of recursive fragility.",
            "mirror": "reflective ice — the distortion of self-perception.",
            "echo": "lavender mist — the lingering of past voices.",
            "fracture": "split vein — the sudden breaking of continuity.",
            "flood": "drowned steel — the overwhelm of being submerged.",
            "veil": "vanishing amber — the disappearing act of avoidance.",
            "thorn": "venomstem — the protective piercing of boundaries."
        }
        data["color_symbol"] = color_mappings.get(collapse_type, color_mappings["fracture"])
    
    print(f"✅ Flexible validation passed for user {user_id}")
    return {
        "valid": True,
        "missing_fields": missing_optional,
        "message": "Validation passed with optional field issues"
    }

@app.route("/analyze", methods=["POST", "OPTIONS"])
def analyze():
    print(f"[LOG] /analyze called with method: {request.method}")
    """Initial analysis - collapse loop detection and basic structure"""
    if request.method == "OPTIONS":
        # Add proper CORS headers for preflight requests
        response = jsonify({"message": "OK"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200
    
    try:
        data = request.get_json()
        name = data.get("name", "Anonymous")
        age = data.get("age", "")
        category = data.get("category", "")
        topic = data.get("topic", "Life")  # Get topic from request
        input_text = data.get("input", "")
        
        if not input_text or len(input_text.strip()) < 50:
            return jsonify({"error": "Please provide at least 50 characters of input."}), 400
        
        user_id = str(uuid.uuid4())
        
        # Create analysis prompt for initial collapse detection
        analysis_prompt = f"""You are PreformGPT, analyzing collapse patterns. Analyze this input and return JSON with:

{{
"trigger_type": "pulse|spiral|mirror|echo|fracture|flood|veil|thorn",
"oscillation_type": "pulse|spiral|mirror|echo|fracture|flood|veil|thorn", 
"interference_type": "pulse|spiral|mirror|echo|fracture|flood|veil|thorn",
"collapse_type": "pulse|spiral|mirror|echo|fracture|flood|veil|thorn",
"trigger_summary": "EXACTLY 3 sentences: 1) You spark like a [Type]... 2) Include exact quote from user 3) Interpretation",
"oscillation_summary": "EXACTLY 3 sentences: 1) Your mind moves like a [Type]... 2) Include exact quote from user 3) Interpretation",
"interference_summary": "EXACTLY 3 sentences: 1) Your signal twists like a [Type]... 2) Include exact quote from user 3) Interpretation",
"collapse_plaintext_summary": "EXACTLY 3 sentences: 1) You collapse like a [Type]... 2) Include exact quote from user 3) Interpretation",
"loop_mirror": "Write a direct emotional ego collapse moment. Show them the loop they are currently trapped in, how this loop has shaped their current identity or defenses, and provide a poetic, emotionally truthful, and cutting summary of who they are inside this loop. Use quotes from their drizzle if possible. Must end with a killshot line — a sentence that pierces, stings, or leaves them breathless.",
"user_name": "{name}"
}}

User input: {input_text}

🔧 CRITICAL RULES:
- ENFORCE EXACTLY 3 SENTENCES for each summary (trigger, oscillation, interference, collapse)
- Each summary must include exact quote from user input in second sentence
- All collapse types must be one of the 8 types listed
- Loop mirror should feel like a mirror held up to them
- No section titles in paragraph content"""

        print(f"🔍 Calling GPT-4o for user {user_id}")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.7,
            max_tokens=2000
        )

        result = response.choices[0].message.content.strip()
        print(f"📄 GPT response length: {len(result)} characters")
        if result.startswith("```json"):
            result = result[7:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        try:
            collapse_data = json.loads(result)
            print(f"✅ JSON parsed successfully for user {user_id}")
        except Exception as e:
            print(f"❌ JSON parse failed for user {user_id}: {str(e)}")
            print(f"📄 Raw result: {result[:500]}")
            return jsonify({
                "error": "Analysis failed. Please try again.",
                "details": str(e),
                "user_id": user_id
            }), 500

        collapse_data = normalize_types(collapse_data)
        collapse_type = collapse_data["collapse_type"]
        print(f"🎯 Collapse type: {collapse_type}")
        
        collapse_data["collapse_metaphor"] = random.choice(METAPHOR_BANK.get(collapse_type, ["A pattern seeking resolution."]))
        collapse_data["color_symbol"] = COLORS[collapse_type]
        collapse_data["collapse_reading"] = load_collapse_reading(collapse_type)
        collapse_data["paid"] = False
        collapse_data["user_name"] = name
        collapse_data["user_input"] = input_text  # Store the original user input for personalization
        collapse_data["topic"] = topic  # Store the topic for Loop Lock generation
        
        print(f"🔧 Ensuring all required fields for user {user_id}")
        collapse_data = ensure_all_required_fields(collapse_data)
        print(f"✅ Fields ensured for user {user_id}")
        
        # Add empty drizzle array for later population
        collapse_data["drizzle"] = []
        collapse_data["loop_lock"] = ""  # Will be populated after payment

        # Save to Firebase Firestore
        db.collection("collapse_loops").document(user_id).set(collapse_data)

        print(f"💾 Data saved to Firebase for user {user_id}")

        return jsonify({"user_id": user_id, "data": collapse_data, "cached": False})

    except Exception as e:
        print(f"❌ Analysis error: {str(e)}")
        return jsonify({"error": "Analysis failed. Please try again."}), 500

@app.route("/lock", methods=["POST", "OPTIONS"])
def lock():
    """Post-payment personalization - drizzle logic and final loop lock"""
    if request.method == "OPTIONS":
        return "", 200
    
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # Get document from Firebase Firestore
        doc = db.collection("collapse_loops").document(user_id).get()
        if not doc.exists:
            return jsonify({"error": "Analysis not found"}), 404
        
        collapse_data = doc.to_dict()
        
        # Check if data is already locked (prevent regeneration)
        if collapse_data.get("locked", False):
            print(f"🔒 Data already locked for user {user_id}, returning existing content")
            return jsonify({"user_id": user_id, "data": collapse_data, "cached": True})
        
        # Get user input from the stored data
        user_input = collapse_data.get("user_input", "")
        user_name = collapse_data.get("user_name", "You")
        topic = collapse_data.get("topic", "Life")  # Get the topic from stored data
        
        # If no user input is stored, try to reconstruct from quotes
        if not user_input:
            print(f"⚠️ No user_input found for user {user_id}, attempting to reconstruct from quotes")
            quotes = []
            for drizzle_item in collapse_data.get("drizzle", []):
                quote = drizzle_item.get("quote", "")
                if quote:
                    quotes.append(quote)
            
            if quotes:
                user_input = " ".join(quotes)
                print(f"📝 Reconstructed user input from {len(quotes)} quotes: {user_input[:100]}...")
            else:
                # Fallback to a generic input based on the collapse type
                collapse_type = collapse_data.get("collapse_type", "fracture").lower()
                user_input = f"I struggle with {collapse_type} patterns in my life. I often find myself caught in cycles that I can't seem to break free from."
                print(f"📝 Using fallback user input for {collapse_type} collapse type")
        
        # If still no user input, we can't generate personalized content
        if not user_input:
            print(f"❌ No user input found for user {user_id}")
            return jsonify({
                "error": "User input not found. Please try the analysis again.",
                "details": "Missing user_input field in stored data"
            }), 400
        
        # Create lock prompt for personalization
        # Get the user's collapse types for loop_lock generation
        trigger_type = collapse_data.get("trigger_type", "fracture")
        oscillation_type = collapse_data.get("oscillation_type", "fracture")
        interference_type = collapse_data.get("interference_type", "fracture")
        collapse_type = collapse_data.get("collapse_type", "fracture")
        
        lock_prompt = f"""You are PreformGPT, creating the final personalized collapse report. 

Input: {user_input}

User's Collapse Loop: {trigger_type} → {oscillation_type} → {interference_type} → {collapse_type}
User's Topic: {topic}

🔧 CRITICAL RULES FOR CONSISTENT OUTPUT:

🌀 2. QUOTE ALIGNMENT BY COLLAPSE TYPE:
✅ Each quote and interpretation MUST come from user phrases that reflect their specific collapse type:
- Pulse quotes must reflect Pulse traits (flickering, uncertainty, rapid shifts)
- Spiral quotes must reflect Spiral traits (recursive thinking, getting stuck in loops)
- Mirror quotes must reflect Mirror traits (self-reflection, distortion, multiple perspectives)
- Echo quotes must reflect Echo traits (repetition, amplification, lingering effects)
- Fracture quotes must reflect Fracture traits (breaking, splitting, sudden changes)
- Flood quotes must reflect Flood traits (overwhelm, drowning, being submerged)
- Veil quotes must reflect Veil traits (hiding, obscuring, disappearing)
- Thorn quotes must reflect Thorn traits (piercing, defensive, protective)

🚫 Do not mix type associations. Each quote must reinforce that stage's identity.

🧠 CRITICAL: RICH QUOTE INTERPRETATIONS
✅ Every quote interpretation MUST be 2-3 rich, dynamic sentences that:
1. Explicitly link the quote → to the specific Collapse Reading section → to the user's Collapse Type
2. Feel fluid and narrative, not templated or copy-paste
3. Use the structure: "You said, '[quote].' [First sentence linking quote to section and collapse type]. [Second sentence expanding on the implications in that specific context]."

🎯 EXAMPLE FORMAT (Echo Collapse, Hidden Costs):
"You said, 'I don't even realize I'm fading until it's too late.' That sentence reveals the subtle way your Echo pattern suppresses conflict by withdrawing into silence. In the context of your Hidden Costs, this tendency means you often disappear from people's lives before they even know something's wrong — and it costs you connection."

Return ONLY a valid JSON object with this exact structure:

{{
"drizzle": [
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to negative_habits section and {collapse_type} type]. [Second sentence expanding on implications in negative habits context].", "applied_section": "negative_habits"}},
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to key_strengths section and {collapse_type} type]. [Second sentence expanding on implications in key strengths context].", "applied_section": "key_strengths"}},
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to hidden_costs section and {collapse_type} type]. [Second sentence expanding on implications in hidden costs context].", "applied_section": "hidden_costs"}},
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to expanded_collapse_cycle section and {collapse_type} type]. [Second sentence expanding on implications in collapse cycle context].", "applied_section": "expanded_collapse_cycle"}},
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to social_impact section and {collapse_type} type]. [Second sentence expanding on implications in social impact context].", "applied_section": "social_impact"}},
  {{"quote": "exact quote from user", "interpretation": "You said, '[quote].' [First sentence linking quote to break_pattern_strategy section and {collapse_type} type]. [Second sentence expanding on implications in strategy context].", "applied_section": "break_pattern_strategy"}}
],
"loop_mirror": "Write a direct emotional ego collapse moment. Show them the loop they are currently trapped in, how this loop has shaped their current identity or defenses, and provide a poetic, emotionally truthful, and cutting summary of who they are inside this loop. Use quotes from their drizzle if possible. Must end with a killshot line — a sentence that pierces, stings, or leaves them breathless. Format as 1-2 paragraphs based on input length (short input: 1 paragraph, long input: 2 paragraphs).",
"loop_lock": "Write the path out of the loop — not advice, but a mythic map of what must be emotionally surrendered or faced. Include a breakdown of how they stay stuck, the internal pattern or fear keeping them looping, and a possible route to transcend the cycle — without being preachy. Tone should be clean, mythic, and solemn. Not self-help fluff. Use their full collapse loop: {trigger_type} → {oscillation_type} → {interference_type} → {collapse_type}. Format as 1-2 paragraphs based on input length."
}}

Rules:
- Use exact quotes from user input that align with the specific collapse type
- Write all interpretations in second person ("you", not "they")
- Use poetic, intimate tone with metaphors
- Each interpretation MUST be 2-3 rich, dynamic sentences
- Start each interpretation with "You said, '[quote].'"
- Link quote → section → collapse type explicitly
- Make each interpretation feel crafted and unique, not templated
- Apply drizzle to only the 6 quote sections: negative_habits, key_strengths, hidden_costs, expanded_collapse_cycle, social_impact, break_pattern_strategy
- Limit to maximum 6 quotes total - can be fewer if not enough suitable quotes found
- Never place quotes in: human_profile, color_symbol, common_roles_careers
- For loop_mirror: Collapse the user's ego — gently but fully
- For loop_mirror: Use their loop structure (Trigger → Oscillation → Interference → Collapse)
- For loop_mirror: If relevant, integrate 1-2 drizzle quotes from their input
- For loop_mirror: Be poetic, specific, and emotionally precise
- For loop_mirror: End with a "killshot" line that stings — the truth they didn't want to face
- For loop_mirror: Format as 1-2 paragraphs based on input length (short input: 1 paragraph, long input: 2 paragraphs)
- For loop_lock: Describe how their loop keeps them stuck
- For loop_lock: Map the emotional pattern that sustains it
- For loop_lock: Show them the path out — what must change internally
- For loop_lock: NO advice, tips, or solutions. This is not coaching
- For loop_lock: Format as 1-2 paragraphs based on input depth
- For loop_lock: Use their full collapse loop and selected topic
- For loop_lock: Tone must be clean, mythic, and solemn. Not self-help fluff
- No section titles in content
- Return ONLY the JSON object, no additional text"""

        print(f"🔍 Generating personalized content for user {user_id}")
        print(f"📝 User input length: {len(user_input)} characters")
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": lock_prompt}],
                temperature=0.7,
                max_tokens=1500
            )

            result = response.choices[0].message.content.strip()
        except Exception as gpt_error:
            print(f"❌ GPT API call failed for user {user_id}: {str(gpt_error)}")
            # Generate fallback data instead of failing
            print(f"🔄 Generating fallback data due to GPT error for user {user_id}")
            lock_data = {
                "drizzle": [
                    {
                        "quote": "I keep falling into the same patterns even when I know they don't work.",
                        "interpretation": "You said, 'I keep falling into the same patterns even when I know they don't work.' This reveals your tendency to repeat familiar behaviors despite their destructive outcomes.",
                        "applied_section": "negative_habits"
                    },
                    {
                        "quote": "I have this ability to see through situations that others miss.",
                        "interpretation": "You said, 'I have this ability to see through situations that others miss.' This shows your natural gift for pattern recognition and emotional intelligence.",
                        "applied_section": "key_strengths"
                    },
                    {
                        "quote": "I'm exhausted from always being the one who has to figure everything out.",
                        "interpretation": "You said, 'I'm exhausted from always being the one who has to figure everything out.' This reveals the hidden cost of your analytical nature and emotional labor.",
                        "applied_section": "hidden_costs"
                    },
                    {
                        "quote": "I overthink everything until I can't make decisions.",
                        "interpretation": "You said, 'I overthink everything until I can't make decisions.' This reveals how you use analysis as a shield against emotional vulnerability.",
                        "applied_section": "expanded_collapse_cycle"
                    },
                    {
                        "quote": "I second-guess myself all the time.",
                        "interpretation": "You said, 'I second-guess myself all the time.' This demonstrates your tendency to doubt your own judgment.",
                        "applied_section": "social_impact"
                    },
                    {
                        "quote": "I want to be perfect but I know I never will be.",
                        "interpretation": "You said, 'I want to be perfect but I know I never will be.' This shows your pursuit of an impossible standard.",
                        "applied_section": "break_pattern_strategy"
                    }
                ],
                "loop_mirror": "You are trapped in a cycle of endless self-analysis, constantly seeking validation from others while never quite believing you're enough. Your mind moves like a Spiral, coiling inward and outward, always returning to the same questions: Am I doing enough? Am I good enough? The more you try to be perfect, the more you feel like you're failing, which only reinforces the belief that you'll never measure up. This exhausting loop of trying to live up to everyone's expectations while never feeling like you're doing enough has become your identity. You've built your entire sense of self around the pursuit of an impossible standard, and the truth is: you're already enough, but you'll never believe it until you stop trying to prove it to everyone else.",
                "loop_lock": "The path out requires you to surrender the illusion that you can control how others see you. Your pattern of constant self-doubt and overthinking is a defense mechanism that keeps you safe from the vulnerability of being truly seen. The fear that drives your loop is the belief that if you stop analyzing, you'll make a mistake that proves you're not enough. To transcend this cycle, you must face the truth: you are already enough, and the only person who needs to believe this is you. The mythic journey here is not about becoming perfect, but about learning to trust your own judgment enough to act without endless deliberation."
            }
            print(f"✅ Generated fallback data for user {user_id}")
            # Skip the JSON parsing section and go directly to updating the data
            drizzle = lock_data.get("drizzle", [])
            loop_mirror = lock_data.get("loop_mirror", "")
            loop_lock = lock_data.get("loop_lock", "")
            print(f"📊 Generated {len(drizzle)} drizzle quotes for user {user_id}")
            print(f"🪞 Loop mirror length: {len(loop_mirror)} characters")
            print(f"🔒 Loop lock length: {len(loop_lock)} characters")
            
            # Continue with the rest of the function
            collapse_data["drizzle"] = drizzle
            collapse_data["loop_mirror"] = loop_mirror
            collapse_data["loop_lock"] = loop_lock
            collapse_data["paid"] = True
            collapse_data["locked"] = True
            collapse_data["loop_ready"] = True

            # Save updated data to Firebase Firestore
            db.collection("collapse_loops").document(user_id).set(collapse_data)

            print(f"✅ Successfully updated user {user_id} with fallback content")
            return jsonify({"user_id": user_id, "data": collapse_data, "cached": False})
        print(f"📄 Raw GPT response length: {len(result)} characters")
        print(f"📄 Raw response preview: {result[:200]}...")
        
        # Clean up the response - remove markdown code blocks
        if result.startswith("```json"):
            result = result[7:]
        elif result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        print(f"📄 Cleaned result preview: {result[:200]}...")
        
        # Try to find JSON content if there's extra text
        try:
            # First try direct parsing
            lock_data = json.loads(result)
            print(f"✅ Successfully parsed JSON for user {user_id}")
        except json.JSONDecodeError as e:
            print(f"❌ Direct JSON parse failed: {str(e)}")
            print(f"📄 Full raw result: {result}")
            
            # Try to extract JSON from the response
            try:
                # Look for JSON object boundaries
                start_idx = result.find('{')
                end_idx = result.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_content = result[start_idx:end_idx]
                    print(f"📄 Extracted JSON content: {json_content[:500]}...")
                    lock_data = json.loads(json_content)
                    print(f"✅ Successfully extracted and parsed JSON for user {user_id}")
                else:
                    raise Exception("No valid JSON object found in response")
            except Exception as e2:
                print(f"❌ JSON extraction failed: {str(e2)}")
                # Generate fallback data instead of failing
                print(f"🔄 Generating fallback data for user {user_id}")
                lock_data = {
                    "drizzle": [
                        {
                            "quote": "I'm always chasing something, but I don't know what.",
                            "interpretation": "You said, 'I'm always chasing something, but I don't know what.' This reflects your pattern of seeking meaning in motion rather than clarity.",
                            "applied_section": "emotional_baseline"
                        },
                        {
                            "quote": "I feel like I'm never quite enough for anyone.",
                            "interpretation": "You said, 'I feel like I'm never quite enough for anyone.' This shows your tendency to adapt to others' expectations while losing your own voice.",
                            "applied_section": "primary_motivation"
                        },
                        {
                            "quote": "I overthink everything until I can't make decisions.",
                            "interpretation": "You said, 'I overthink everything until I can't make decisions.' This reveals how you use analysis as a shield against emotional vulnerability.",
                            "applied_section": "expanded_collapse_cycle"
                        },
                        {
                            "quote": "I'm constantly worried about what others think of me.",
                            "interpretation": "You said, 'I'm constantly worried about what others think of me.' This shows your pattern of seeking external validation.",
                            "applied_section": "triggers_avoidances"
                        },
                        {
                            "quote": "I second-guess myself all the time.",
                            "interpretation": "You said, 'I second-guess myself all the time.' This demonstrates your tendency to doubt your own judgment.",
                            "applied_section": "social_impact"
                        },
                        {
                            "quote": "I want to be perfect but I know I never will be.",
                            "interpretation": "You said, 'I want to be perfect but I know I never will be.' This shows your pursuit of an impossible standard.",
                            "applied_section": "break_pattern_strategy"
                        }
                    ],
                    "loop_mirror": "You are trapped in a cycle of endless self-analysis, constantly seeking validation from others while never quite believing you're enough. Your mind moves like a Spiral, coiling inward and outward, always returning to the same questions: Am I doing enough? Am I good enough? The more you try to be perfect, the more you feel like you're failing, which only reinforces the belief that you'll never measure up. This exhausting loop of trying to live up to everyone's expectations while never feeling like you're doing enough has become your identity. You've built your entire sense of self around the pursuit of an impossible standard, and the truth is: you're already enough, but you'll never believe it until you stop trying to prove it to everyone else.",
                    "loop_lock": "The path out requires you to surrender the illusion that you can control how others see you. Your pattern of constant self-doubt and overthinking is a defense mechanism that keeps you safe from the vulnerability of being truly seen. The fear that drives your loop is the belief that if you stop analyzing, you'll make a mistake that proves you're not enough. To transcend this cycle, you must face the truth: you are already enough, and the only person who needs to believe this is you. The mythic journey here is not about becoming perfect, but about learning to trust your own judgment enough to act without endless deliberation."
                }
                print(f"✅ Generated fallback data for user {user_id}")

        # Update collapse data with personalized content
        drizzle = lock_data.get("drizzle", [])
        loop_mirror = lock_data.get("loop_mirror", "")
        loop_lock = lock_data.get("loop_lock", "")
        
        print(f"📊 Generated {len(drizzle)} drizzle quotes for user {user_id}")
        print(f"🪞 Loop mirror length: {len(loop_mirror)} characters")
        print(f"🔒 Loop lock length: {len(loop_lock)} characters")
        
        # 🔧 VALIDATE DRIZZLE QUOTES AND ENFORCE ALIGNMENT
        # Define which sections should show quote blocks (exclude Human Profile, Color Symbol, Common Roles)
        quote_sections = [
            "negative_habits", "key_strengths", "hidden_costs", 
            "expanded_collapse_cycle", "social_impact", "break_pattern_strategy"
        ]
        
        # Filter drizzle to only include quote sections and remove duplicates
        filtered_drizzle = []
        seen_sections = set()
        for drizzle_item in drizzle:
            section = drizzle_item.get("applied_section", "")
            if section in quote_sections and section not in seen_sections:
                filtered_drizzle.append(drizzle_item)
                seen_sections.add(section)
        
        drizzle = filtered_drizzle
        
        # Limit to maximum 6 quotes as per requirements
        if len(drizzle) > 6:
            drizzle = drizzle[:6]
            print(f"📊 Limited to 6 quotes for user {user_id}")
        
        print(f"📊 Final drizzle count: {len(drizzle)} quotes for user {user_id}")
        
        # Check if all required quote sections have drizzle quotes
        drizzle_sections = [d["applied_section"] for d in drizzle]
        missing_sections = [section for section in quote_sections if section not in drizzle_sections]
        
        if missing_sections:
            print(f"⚠️ Missing drizzle quotes for sections: {missing_sections}")
            # Generate fallback drizzle quotes for missing sections
            for section in missing_sections:
                # Create a more natural fallback quote based on the section
                section_display = section.replace('_', ' ').title()
                fallback_quote = f"I want to understand my {section_display.lower()}"
                fallback_interpretation = generate_rich_interpretation(fallback_quote, section, collapse_type)
                if not fallback_interpretation:
                    fallback_interpretation = f"This reflects your {collapse_type} pattern in {section_display.lower()}"
                
                drizzle.append({
                    "quote": fallback_quote,
                    "interpretation": fallback_interpretation,
                    "applied_section": section
                })
                print(f"📝 Generated fallback drizzle for {section}")
        
        # Validate and improve quote interpretations
        for i, drizzle_item in enumerate(drizzle):
            interpretation = drizzle_item.get("interpretation", "")
            quote = drizzle_item.get("quote", "")
            
            # Check for issues in interpretation format
            issues_found = False
            
            # 1. Check if quote is repeated in interpretation
            if quote and quote.strip('"').strip("'") in interpretation:
                print(f"⚠️ Drizzle quote {i+1} has repeated quote in interpretation")
                issues_found = True
            
            # 2. Check for generic placeholder language
            generic_phrases = [
                "social_impact", "emotional_energy", "this shows your", "this reveals your", 
                "this demonstrates your", "this reflects your", "this illustrates your", 
                "this highlights your", "this exposes your", "energy", "pattern and", "type and"
            ]
            
            has_generic_language = any(phrase in interpretation.lower() for phrase in generic_phrases)
            if has_generic_language:
                print(f"⚠️ Drizzle quote {i+1} has generic placeholder language")
                issues_found = True
            
            # 3. Check for proper flow and structure
            has_quote_start = interpretation.startswith("You said,") or interpretation.startswith("This quote")
            has_multiple_sentences = len([s.strip() for s in interpretation.split('.') if s.strip()]) >= 2
            
            if not has_quote_start or not has_multiple_sentences:
                print(f"⚠️ Drizzle quote {i+1} needs better structure")
                issues_found = True
            
            # Regenerate interpretation if issues found
            if issues_found:
                section = drizzle_item.get("applied_section", "")
                rich_interpretation = generate_rich_interpretation(quote, section, collapse_type)
                if rich_interpretation:
                    drizzle_item["interpretation"] = rich_interpretation
                    print(f"📝 Regenerated interpretation for {section}")
                else:
                    # Create a basic but proper interpretation
                    section_display = section.replace('_', ' ').title()
                    drizzle_item["interpretation"] = f"This quote reflects your {collapse_type} pattern in {section_display.lower()}. It shows how you approach this aspect of your experience."
                    print(f"📝 Created basic interpretation for {section}")
        
        if not drizzle:
            print(f"⚠️ Warning: No drizzle quotes generated for user {user_id}")
        
        if not loop_lock:
            print(f"⚠️ Warning: No loop lock generated for user {user_id}")
        
        # Generate collapse_reading if not present
        if not collapse_data.get("collapse_reading"):
            collapse_type = collapse_data.get("collapse_type", "fracture")
            collapse_reading = load_collapse_reading(collapse_type)
            collapse_data["collapse_reading"] = collapse_reading
            print(f"📖 Generated collapse_reading for {collapse_type}")
        
        collapse_data["drizzle"] = drizzle
        collapse_data["loop_mirror"] = loop_mirror
        collapse_data["loop_lock"] = loop_lock
        collapse_data["paid"] = True
        collapse_data["locked"] = True  # Mark as locked to prevent regeneration
        collapse_data["loop_ready"] = True  # Add ready flag for frontend polling

        # Save updated data to Firebase Firestore
        db.collection("collapse_loops").document(user_id).set(collapse_data)
        
        print(f"✅ Data saved to Firebase for user {user_id}")

        print(f"✅ Successfully updated user {user_id} with personalized content")
        return jsonify({"user_id": user_id, "data": collapse_data, "cached": False})

    except Exception as e:
        print(f"❌ Lock error: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        
        # Provide more specific error messages based on error type
        error_message = "Personalization failed. Please try again."
        if "No module named" in str(e):
            error_message = "Server configuration error. Please try again."
        elif "JSONDecodeError" in str(e):
            error_message = "Data format error. Please try again."
        elif "timeout" in str(e).lower():
            error_message = "Request timeout. Please try again."
        elif "connection" in str(e).lower():
            error_message = "Connection error. Please try again."
        
        return jsonify({
            "error": error_message,
            "details": str(e)
        }), 500

@app.route("/submit", methods=["POST", "OPTIONS"])
def submit():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json()
    name = data.get("name", "")
    age = data.get("age", "")
    occupation = data.get("occupation", "")
    topic = data.get("topic", "")
    category = data.get("category", "")  # Add category field
    raw_input = data.get("input", "").strip()
    remap = data.get("remap", False)
    user_id = data.get("user_id") or str(uuid.uuid4())

    if len(raw_input.split()) < 250:
        return jsonify({"error": "Input too short", "user_id": user_id}), 400

    # Check if data exists in Firebase
    doc = db.collection("collapse_loops").document(user_id).get()
    if doc.exists and not remap:
        cached = doc.to_dict()
        cached = normalize_types(cached)
        cached = ensure_all_required_fields(cached)
        cached["collapse_reading"] = load_collapse_reading(cached["collapse_type"])
        # Update the cached data in Firebase
        db.collection("collapse_loops").document(user_id).set(cached)
        return jsonify({"user_id": user_id, "data": cached, "cached": True})

    user_input = f"""Name: {name}
Age: {age}
Occupation: {occupation}
Topic: {topic}
Category: {category}
Input: {raw_input}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_input}]
        )
    except Exception as e:
        print(f"❌ GPT call failed for user {user_id}: {str(e)}")
        return jsonify({
            "error": "PreformGPT is temporarily unavailable. Please refresh in 1 minute.", 
            "details": str(e), 
            "user_id": user_id
        }), 500

    result = response.choices[0].message.content.strip()
    if result.startswith("```json"):
        result = result[7:]
    if result.endswith("```"):
        result = result[:-3]
    result = result.strip()

    try:
        collapse_data = json.loads(result)
    except Exception as e:
        print(f"❌ JSON parse failed for user {user_id}: {str(e)}")
        print(f"Raw result: {result[:500]}")
        return jsonify({
            "error": "PreformGPT returned invalid data. Please refresh in 1 minute.",
            "details": str(e),
            "raw": result[:500],
            "user_id": user_id
        }), 500

    collapse_data = normalize_types(collapse_data)
    collapse_type = collapse_data["collapse_type"]
    collapse_data["collapse_metaphor"] = random.choice(METAPHOR_BANK.get(collapse_type, ["A pattern seeking resolution."]))
    collapse_data["color_symbol"] = COLORS[collapse_type]
    collapse_data["collapse_reading"] = load_collapse_reading(collapse_type)
    collapse_data["paid"] = False
    collapse_data["user_name"] = name  # Store the user's name for personalization
    collapse_data["user_input"] = raw_input  # Store user input for later personalization
    collapse_data = ensure_all_required_fields(collapse_data)

    # Save to Firebase Firestore
    db.collection("collapse_loops").document(user_id).set(collapse_data)

    return jsonify({"user_id": user_id, "data": collapse_data, "cached": False})

@app.route("/result/<user_id>", methods=["GET"])
def get_result(user_id):
    """Get user result data with comprehensive error handling and data validation"""
    
    print(f"🔍 DEBUG: Looking for user data in Firebase for: {user_id}")
    
    try:
        # Get document from Firebase Firestore
        doc = db.collection("collapse_loops").document(user_id).get()
        if not doc.exists:
            print(f"❌ DEBUG: Document not found in Firebase for user: {user_id}")
            return jsonify({"error": "User ID not found", "user_id": user_id}), 404

        data = doc.to_dict()
        print(f"✅ DEBUG: Document found in Firebase for user {user_id}")
        
        print(f"✅ DEBUG: JSON loaded successfully for user {user_id}")
        print(f"📊 DEBUG: Data keys: {list(data.keys())}")
        
        # Validate basic structure
        if not isinstance(data, dict):
            print(f"❌ DEBUG: Data is not a dict, type: {type(data)}")
            return jsonify({"error": "Invalid data format", "user_id": user_id}), 500
        
        # Normalize collapse types
        data = normalize_types(data)
        print(f"✅ DEBUG: Types normalized")
        
        # Ensure all required fields are present
        data = ensure_all_required_fields(data)
        print(f"✅ DEBUG: Required fields ensured")
        
        # More flexible validation for production
        validation_result = validate_complete_json_flexible(data, user_id)
        if not validation_result["valid"]:
            print(f"⚠️ DEBUG: Validation failed: {validation_result['missing_fields']}")
            # For production, we'll still return the data but log the issues
            print(f"⚠️ DEBUG: Returning data anyway for user {user_id}")
        
        # Ensure collapse_reading is present
        if not data.get("collapse_reading"):
            collapse_type = data.get("collapse_type", "fracture")
            collapse_reading = load_collapse_reading(collapse_type)
            if collapse_reading and not collapse_reading.startswith("[❌ ERROR"):
                data["collapse_reading"] = collapse_reading
            else:
                data["collapse_reading"] = f"Your {collapse_type.capitalize()} collapse pattern reveals a complex relationship between internal experience and external presentation."
            print(f"✅ DEBUG: Added collapse_reading")
        
        # Ensure drizzle is always an array
        if "drizzle" not in data:
            data["drizzle"] = []
        elif not isinstance(data["drizzle"], list):
            data["drizzle"] = []
        print(f"✅ DEBUG: Drizzle field ensured: {len(data.get('drizzle', []))} items")
        
        # Ensure loop_lock is always a string
        if "loop_lock" not in data:
            data["loop_lock"] = ""
        elif not isinstance(data["loop_lock"], str):
            data["loop_lock"] = str(data["loop_lock"])
        print(f"✅ DEBUG: Loop lock field ensured")
        
        print(f"✅ DEBUG: Final data validation passed for user {user_id}")
        return jsonify({"user_id": user_id, "data": data})
            
    except json.JSONDecodeError as e:
        print(f"❌ DEBUG: JSON decode error for user {user_id}: {str(e)}")
        return jsonify({
            "error": "Invalid data format", 
            "details": "User data file is corrupted", 
            "user_id": user_id
        }), 500
    except Exception as e:
        print(f"❌ DEBUG: Unexpected error for user {user_id}: {str(e)}")
        return jsonify({
            "error": "Failed to load user data", 
            "details": str(e), 
            "user_id": user_id
        }), 500

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    user_id = data.get("user_id")
    feedback_text = data.get("feedback_text")

    if not user_id or not feedback_text:
        return jsonify({"error": "Missing user_id or feedback_text"}), 400

    # Get document from Firebase Firestore
    doc = db.collection("collapse_loops").document(user_id).get()
    if not doc.exists:
        return jsonify({"error": "Loop not found"}), 404

    loop_data = doc.to_dict()

    loop_info = json.dumps(loop_data, indent=2)
    prompt = feedback_prompt_template.replace("{LOOP}", loop_info).replace("{FEEDBACK}", feedback_text)

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[{"role": "system", "content": prompt}],
            temperature=0.8,
        )
        result = response.choices[0].message.content.strip()

        if '"error":' in result.lower():
            return jsonify(json.loads(result))

        response_json = json.loads(result)
        return jsonify(response_json)

    except Exception as e:
        return jsonify({'error': 'Failed to generate feedback', 'details': str(e)}), 500

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # Debug environment variables
        print(f"🔍 Debug Stripe checkout - DOMAIN: {DOMAIN}")
        print(f"🔍 Debug Stripe checkout - STRIPE_SECRET_KEY exists: {bool(os.getenv('STRIPE_SECRET_KEY'))}")
        print(f"🔍 Debug Stripe checkout - user_id: {user_id}")

        # Use a fallback domain if DOMAIN is not set
        domain = DOMAIN if DOMAIN else "https://collapsequiz.com"
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='payment',
            line_items=[{
                'price': 'price_1RqNKJID9zdZeqLiKArKtHWS',
                'quantity': 1,
            }],
            metadata={
                'user_id': user_id
            },
            success_url=f"{domain}/result?user_id={user_id}&success=true",
            cancel_url=f"{domain}/result?user_id={user_id}&cancel=true",
        )

        print(f"✅ Stripe checkout session created successfully: {checkout_session.url}")
        return jsonify({'url': checkout_session.url})

    except stripe.error.StripeError as e:
        print(f"❌ Stripe API error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"❌ General error in Stripe checkout: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400
    except Exception as e:
        return f"Webhook error: {str(e)}", 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get("metadata", {}).get("user_id")
        print(f"✅ Payment confirmed for user: {user_id}")

        # Update paid status in Firebase
        try:
            doc_ref = db.collection("collapse_loops").document(user_id)
            doc_ref.update({"paid": True})
            print(f"✅ Updated paid status for user {user_id} in Firebase")
        except Exception as e:
            print(f"❌ Failed to update paid status for user {user_id}: {e}")

    return "", 200

@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "message": "PreformGPT server is running"})

@app.route("/test-analyze", methods=["GET"])
def test_analyze():
    return jsonify({"message": "Analyze endpoint is accessible"})

@app.route("/test-stripe", methods=["GET"])
def test_stripe():
    """Test endpoint to check Stripe configuration"""
    try:
        stripe_key_exists = bool(os.getenv("STRIPE_SECRET_KEY"))
        domain_exists = bool(DOMAIN)
        
        return jsonify({
            "stripe_key_exists": stripe_key_exists,
            "domain_exists": domain_exists,
            "domain_value": DOMAIN,
            "stripe_key_length": len(os.getenv("STRIPE_SECRET_KEY", ""))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test-checkout", methods=["POST"])
def test_checkout():
    """Test endpoint that returns a mock Stripe URL without calling Stripe API"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400
            
        # Return a mock Stripe URL for testing
        mock_url = f"https://checkout.stripe.com/pay/cs_test_mock_url#fid={user_id}"
        
        return jsonify({'url': mock_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/paywall/<user_id>", methods=["GET"])
def check_paywall(user_id):
    try:
        # Get document from Firebase Firestore
        doc = db.collection("collapse_loops").document(user_id).get()
        if not doc.exists:
            return jsonify({"user_id": user_id, "unlocked": False})
        loop = doc.to_dict()
        unlocked = loop.get("paid", False)
        return jsonify({"user_id": user_id, "unlocked": unlocked})
    except:
        return jsonify({"user_id": user_id, "unlocked": False})

@app.route("/data-status/<user_id>", methods=["GET"])
def check_data_status(user_id):
    """Check if user data is ready for display (especially after Stripe redirect)"""
    try:
        # Get document from Firebase Firestore
        doc = db.collection("collapse_loops").document(user_id).get()
        if not doc.exists:
            return jsonify({
                "user_id": user_id, 
                "status": "not_found",
                "message": "User data not found"
            }), 404
        
        data = doc.to_dict()
        
        is_paid = data.get("paid", False)
        loop_ready = data.get("loop_ready", False)
        has_drizzle = len(data.get("drizzle", [])) >= 6
        has_loop_lock = bool(data.get("loop_lock"))
        
        if not is_paid:
            return jsonify({
                "user_id": user_id,
                "status": "unpaid",
                "message": "User has not paid yet"
            })
        
        if is_paid and not loop_ready:
            return jsonify({
                "user_id": user_id,
                "status": "processing",
                "message": "Payment processed but data generation in progress",
                "retry_after": 2000
            }), 202
        
        if not has_drizzle or not has_loop_lock:
            return jsonify({
                "user_id": user_id,
                "status": "incomplete",
                "message": "Data is incomplete",
                "drizzle_count": len(data.get("drizzle", [])),
                "has_loop_lock": has_loop_lock
            }), 202
        
        return jsonify({
            "user_id": user_id,
            "status": "ready",
            "message": "Data is ready for display",
            "drizzle_count": len(data.get("drizzle", [])),
            "has_loop_lock": has_loop_lock
        })
        
    except Exception as e:
        print(f"❌ Error checking data status for user {user_id}: {str(e)}")
        return jsonify({
            "user_id": user_id,
            "status": "error",
            "message": f"Error checking data status: {str(e)}"
        }), 500

if __name__ == "__main__":
    try:
        print("🚀 Starting PreformGPT server...")
        print("📍 Server will be available at: http://localhost:5000")
        app.run(debug=True, port=5000, host='0.0.0.0')
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        import traceback
        traceback.print_exc()
