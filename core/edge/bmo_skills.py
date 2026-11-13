#!/usr/bin/env python3
"""
BMO Edge Compute — Skill Handler
=================================
Handles local skills (time, weather, device status, memory lookups)
before falling back to the DGX Spark Ollama backend for full LLM inference.

Usage:
    from bmo_skills import BMOSkillRouter
    router = BMOSkillRouter()
    response = router.handle("what time is it")

Deploy:
    scp -r bmo-edge/ saweephd@BMO:~/bmo-edge/
    ssh BMO 'cd ~/bmo-edge && python3 bmo_skills.py'
"""

import json, os, re, subprocess, time, datetime, urllib.request, urllib.error
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent
MEMORY_FILE = BASE_DIR / "bmo_memory.json"
CONFIG_FILE = BASE_DIR / "bmo_config.json"

DEFAULT_CONFIG = {
    "spark_host": "192.168.1.2", "spark_port": 11434,
    "default_model": "gpt-oss:20b", "fallback_model": "gemma4:31b",
    "openweather_api_key": "", "weather_lat": "", "weather_lon": "",
    "weather_units": "imperial", "ollama_timeout": 120,
    "ping_targets": {
        "Spark 1 (spark-827b)": "192.168.1.2",
        "Spark 2 (spark-7b10)": "192.168.1.30",
        "Home Assistant": "192.168.1.69",
        "Crowncorbi NAS": "192.168.1.24",
        "Teri (OpenClaw)": "192.168.1.93",
        "Orbi Router": "192.168.1.52",
        "FiOS Gateway": "192.168.1.1",
    },
}


def _load_json(path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Text matching helpers
# ---------------------------------------------------------------------------
_LEAD_INS = (
    "hey bmo", "bmo", "ok", "okay", "so", "um", "uh", "and", "please",
    "can you tell me about", "can you tell me", "could you tell me about",
    "do you know about", "do you know who", "do you know what", "do you know",
    "tell me about", "tell me", "what about", "how about",
    "who is", "who's", "whos", "who are", "what is", "what's", "whats", "what are",
    "where is", "where's", "wheres",
)
_ARTICLES = ("the", "a", "an", "my", "our", "your", "stan's", "stans")


def normalize_text(text):
    """Lower-case, drop punctuation except apostrophes, collapse spaces."""
    t = re.sub(r"[^a-z0-9' ]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", t).strip()


def direct_subject(normalized_query):
    """What a direct question is about: "who is rose" -> "rose".

    Strips lead-ins ("hey bmo", "tell me about") and articles from the front,
    repeatedly.  Returns what is left, which may be the whole query."""
    q = normalized_query
    changed = True
    while changed and q:
        changed = False
        for lead in sorted(_LEAD_INS + _ARTICLES, key=len, reverse=True):
            if q == lead:
                return ""
            if q.startswith(lead + " "):
                q = q[len(lead) + 1:]
                changed = True
                break
    return q


def key_matches(key, normalized_query, subject=None):
    k = normalize_text(key)
    if not k:
        return False
    if " " in k:
        return re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", normalized_query) is not None
    if subject is None:
        subject = direct_subject(normalized_query)
    return subject == k


def apply_aliases(text, aliases):
    """Replace the spellings speech to text produces with the real name.

    ``aliases`` maps the real spelling to a list of variants, for example
    {"Mazzee": ["maisie", "mazie"]}.  Whole words only, any letter case."""
    out = str(text)
    for canonical, variants in (aliases or {}).items():
        for variant in sorted(variants, key=len, reverse=True):
            out = re.sub(r"(?<![A-Za-z0-9])" + re.escape(variant) + r"(?![A-Za-z0-9])",
                         canonical, out, flags=re.IGNORECASE)
    return out


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
class Skills:

    @staticmethod
    def time_now():
        return datetime.datetime.now().strftime("It's %I:%M %p on %A, %B %d, %Y.")

    @staticmethod
    def date_today():
        return datetime.date.today().strftime("%A, %B %d, %Y")

    @staticmethod
    def weather(config, query=""):
        """Current weather and today's (or tomorrow's) forecast, as one spoken line.

        Uses Open-Meteo, which needs no account or key; only weather_lat and
        weather_lon must be set in bmo_config.json.  Returns None when the
        location is not set or the lookup fails, so the question goes on to
        the model instead of BMO reading out a configuration error."""
        lat, lon = config.get("weather_lat", ""), config.get("weather_lon", "")
        if not lat or not lon:
            return None
        imperial = config.get("weather_units", "imperial") == "imperial"
        url = ("https://api.open-meteo.com/v1/forecast"
               f"?latitude={lat}&longitude={lon}"
               "&current=temperature_2m,apparent_temperature,weather_code"
               "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
               f"&temperature_unit={'fahrenheit' if imperial else 'celsius'}"
               "&timezone=auto&forecast_days=2")
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            return Skills.describe_weather(data, tomorrow="tomorrow" in query.lower())
        except Exception as e:
            print(f"[SKILL] weather lookup failed: {e}")
            return None

    WEATHER_CODES = {
        0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy",
        51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle",
        57: "freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
        66: "freezing rain", 67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
        77: "snow grains", 80: "light showers", 81: "showers", 82: "heavy showers",
        85: "snow showers", 86: "heavy snow showers", 95: "thunderstorms",
        96: "thunderstorms with hail", 99: "thunderstorms with hail",
    }

    @staticmethod
    def describe_weather(data, tomorrow=False):
        codes = Skills.WEATHER_CODES
        daily = data["daily"]
        i = 1 if tomorrow else 0
        high, low = round(daily["temperature_2m_max"][i]), round(daily["temperature_2m_min"][i])
        sky = codes.get(daily["weather_code"][i], "mixed weather")
        rain = daily.get("precipitation_probability_max", [None, None])[i]
        rain_part = f", with a {round(rain)} percent chance of rain or snow" if rain is not None and rain >= 20 else ""
        if tomorrow:
            return f"Tomorrow looks {sky}, with a high of {high} and a low of {low} degrees{rain_part}."
        now = data["current"]
        temp, feels = round(now["temperature_2m"]), round(now["apparent_temperature"])
        feels_part = f", feels like {feels}" if abs(feels - temp) >= 3 else ""
        return (f"Right now it is {temp} degrees{feels_part} and {codes.get(now['weather_code'], 'mixed')}. "
                f"Today: {sky}, high {high}, low {low}{rain_part}.")

    @staticmethod
    def ping_device(host, name=""):
        label = name or host
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", host],
                capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                match = re.search(r"time[=<]([\d.]+)", result.stdout)
                ms = match.group(1) if match else "?"
                return f"{label} is ONLINE ({ms} ms)"
            return f"{label} is OFFLINE"
        except Exception:
            return f"{label} is OFFLINE (timeout)"

    @staticmethod
    def ping_all(config):
        targets = config.get("ping_targets", {})
        if not targets:
            return "No ping targets configured."
        return "\n".join(Skills.ping_device(ip, name) for name, ip in targets.items())

    @staticmethod
    def system_status():
        lines = []
        try:
            with open("/proc/uptime") as f:
                s = float(f.read().split()[0])
            lines.append(f"Uptime: {int(s // 3600)}h {int((s % 3600) // 60)}m")
        except Exception:
            pass
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                lines.append(f"CPU Temp: {int(f.read().strip()) / 1000:.1f}\u00b0C")
        except Exception:
            pass
        try:
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    p = line.split()
                    if p[0] in ("MemTotal:", "MemAvailable:"):
                        mem[p[0]] = int(p[1]) // 1024
            total = mem.get("MemTotal:", 0)
            avail = mem.get("MemAvailable:", 0)
            lines.append(f"Memory: {total - avail}MB / {total}MB ({avail}MB free)")
        except Exception:
            pass
        try:
            r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            d = r.stdout.strip().split("\n")[-1].split()
            lines.append(f"Disk: {d[2]} used / {d[1]} total ({d[4]} full)")
        except Exception:
            pass
        return "\n".join(lines) if lines else "Could not read system status."

    @staticmethod
    def calculate(expression):
        """Safe arithmetic evaluator using ast — no eval(), no builtins access."""
        import ast, operator
        clean = expression.strip()
        # Allowed binary operators
        ops = {
            ast.Add: operator.add, ast.Sub: operator.sub,
            ast.Mult: operator.mul, ast.Div: operator.truediv,
            ast.Mod: operator.mod, ast.Pow: operator.pow,
            ast.USub: operator.neg, ast.UAdd: operator.pos,
        }
        def _eval(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in ops:
                left, right = _eval(node.left), _eval(node.right)
                # Block ridiculous exponents that could OOM the Pi
                if isinstance(node.op, ast.Pow) and (abs(left) > 1e6 or abs(right) > 100):
                    raise ValueError("exponent too large")
                return ops[type(node.op)](left, right)
            if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
                return ops[type(node.op)](_eval(node.operand))
            raise ValueError(f"unsupported expression: {ast.dump(node)}")
        try:
            tree = ast.parse(clean, mode='eval')
            result = _eval(tree.body)
            return f"{clean} = {result}"
        except Exception as e:
            return f"Cannot calculate '{clean}': {e}"

    @staticmethod
    def memory_lookup(query, memory):
        """Answer from household memory, or None to let the model handle it.

        Matching is on whole words.  A multi-word key ("wifi password",
        "hurt finn") matches wherever it appears.  A single-word key ("rose",
        "work", "van") matches only when the question is a direct ask about it
        ("who is Rose?", "tell me about the van").  Before this rule, "how does
        that work" returned Stan's job and "advance" matched "van"."""
        q = normalize_text(query)
        subject = direct_subject(q)
        for key, value in memory.get("quick_answers", {}).items():
            if key_matches(key, q, subject):
                return value
        for fact in memory.get("facts", []):
            if any(key_matches(kw, q, subject) for kw in fact.get("keywords", [])):
                return fact.get("answer", "")
        return None

    @staticmethod
    def memory_add(key, value, memory, path):
        memory.setdefault("quick_answers", {})[key] = value
        _save_json(path, memory)
        return f"Remembered: '{key}' \u2192 '{value}'"

    @staticmethod
    def memory_list(memory):
        lines = ["=== Quick Answers ==="]
        for k, v in memory.get("quick_answers", {}).items():
            lines.append(f"  {k}: {v}")
        facts = memory.get("facts", [])
        lines.append(f"\n=== Facts ({len(facts)} entries) ===")
        for f in facts[:10]:
            lines.append(f"  [{', '.join(f.get('keywords', []))}] \u2192 {f.get('answer', '')[:80]}")
        if len(facts) > 10:
            lines.append(f"  ... and {len(facts) - 10} more")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Intent Classifier
# ---------------------------------------------------------------------------
class IntentClassifier:
    PATTERNS = {
        "time":       r"\b(what time|current time|time is it|the time)\b",
        "date":       r"\b(what date|today'?s date|what day|date today)\b",
        "weather":    r"\b(weather|temperature|forecast|how hot|how cold)\b",
        "ping_all":   r"\b(network status|all devices|device status|ping all|everything online|what'?s online)\b",
        "ping_one":   r"\b(is .+ online|ping |check .+ status|is .+ up|is .+ running)\b",
        "system":     r"\b(system status|bmo status|your temp|cpu temp|your memory)\b",
        "calculate":  r"\b(calculate|what is \d|compute|math|how much is)\b",
        "memory_add": r"\b(remember that|remember:|save this|store this)\b",
        "memory_list": r"\b(what do you (remember|know)|show memory|list memory|your memory)\b",
        "memory_q":   r"\b(what'?s the|where is|who is|what is my|tell me the|tell me about)\b",
    }

    @classmethod
    def classify(cls, text):
        for intent, pattern in cls.PATTERNS.items():
            if re.search(pattern, text.lower().strip()):
                return intent
        return None


# ---------------------------------------------------------------------------
# Spark LLM Fallback
# ---------------------------------------------------------------------------
class SparkLLM:
    def __init__(self, host, port, model, timeout=120):
        self.host, self.port, self.model, self.timeout = host, port, model, timeout

    def chat(self, user_message, system_prompt=""):
        url = f"http://{self.host}:{self.port}/api/chat"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        payload = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
            return data.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            return f"Spark is unreachable: {e}"
        except Exception as e:
            return f"LLM error: {e}"


# ---------------------------------------------------------------------------
# Main Router
# ---------------------------------------------------------------------------
class BMOSkillRouter:
    def __init__(self, config_path=CONFIG_FILE, memory_path=MEMORY_FILE):
        self.config_path, self.memory_path = config_path, memory_path
        if not config_path.exists():
            _save_json(config_path, DEFAULT_CONFIG)
        self.config = _load_json(config_path, DEFAULT_CONFIG)
        if not memory_path.exists():
            _save_json(memory_path, self._default_memory())
        self.memory = _load_json(memory_path, self._default_memory())
        self.spark = SparkLLM(
            self.config["spark_host"], self.config["spark_port"],
            self.config["default_model"], self.config.get("ollama_timeout", 120))

    @staticmethod
    def _default_memory():
        return {
            "owner": {"name": "Stan", "spouse": "Rosita"},
            "quick_answers": {
                "wifi password": "Check the sticker on the Orbi router (RBK863S)",
                "nas ip": "Crowncorbi NAS is at 192.168.1.24:5000",
                "home assistant": "Home Assistant is at homeassistant.local:8123 (ODROID-M1 at 192.168.1.69)",
                "spark 1": "Spark 1 (spark-827b) at 192.168.1.2",
                "spark 2": "Spark 2 (spark-7b10) at 192.168.1.30",
                "teri": "Teri (OpenClaw) at 192.168.1.93 on trekpi",
            },
            "facts": [],
        }

    def handle(self, user_input):
        start = time.time()
        intent = IntentClassifier.classify(user_input)

        if intent == "time":
            return self._r("skill", Skills.time_now(), start)
        if intent == "date":
            return self._r("skill", Skills.date_today(), start)
        if intent == "weather":
            return self._r("skill", Skills.weather(self.config, user_input), start)
        if intent == "ping_all":
            return self._r("skill", Skills.ping_all(self.config), start)

        if intent == "ping_one":
            q = user_input.lower()
            for name, ip in self.config.get("ping_targets", {}).items():
                # extract keywords from target name like "Crowncorbi NAS" or "Spark 1 (spark-827b)"
                terms = re.split(r"[(),]+", name.lower())
                terms = [t.strip() for t in terms if t.strip()]
                words = name.lower().replace("(", " ").replace(")", " ").split()
                all_terms = terms + [w for w in words if len(w) > 2]
                if any(t in q for t in all_terms):
                    return self._r("skill", Skills.ping_device(ip, name), start)
            return self._r("skill", Skills.ping_all(self.config), start)

        if intent == "system":
            return self._r("skill", Skills.system_status(), start)

        if intent == "calculate":
            expr = re.sub(r"(calculate|compute|what is|how much is)", "", user_input, flags=re.I).strip()
            return self._r("skill", Skills.calculate(expr), start)

        if intent == "memory_add":
            m = re.search(r"remember(?:\s+that)?\s*:?\s*(.+?)\s+(?:is|=|\u2192)\s+(.+)", user_input, re.I)
            if m:
                return self._r("skill", Skills.memory_add(
                    m.group(1).strip(), m.group(2).strip(), self.memory, self.memory_path), start)
            return self._r("skill", "Usage: 'remember that [key] is [value]'", start)

        if intent == "memory_list":
            return self._r("skill", Skills.memory_list(self.memory), start)

        # Memory lookup (for memory_q intent or any unmatched query)
        mem = Skills.memory_lookup(user_input, self.memory)
        if mem:
            return self._r("memory", mem, start)

        # Spark LLM fallback (only used by standalone CLI mode)
        owner = self.memory.get("owner", {}).get("name", "the user")
        now = datetime.datetime.now().strftime("%I:%M %p, %A %B %d %Y")
        sys_prompt = f"You are BMO, a helpful home AI assistant for {owner}. Be concise and friendly. Current time: {now}."
        return self._r("spark", self.spark.chat(user_input, sys_prompt), start)

    def normalize(self, user_input):
        """Fix names that speech to text commonly misspells (see apply_aliases)."""
        return apply_aliases(user_input, self.memory.get("aliases"))

    def try_handle(self, user_input):
        """Skill-only mode: returns a response string if a local skill or memory
        match exists, or None if the query should be sent to the upstream LLM
        path (the agent's existing Spark/streaming code in core/llm.py).

        This separates the local skill router from the standalone CLI's
        Spark fallback so we don't have two parallel Spark code paths.
        """
        intent = IntentClassifier.classify(user_input)
        if intent in ("time", "date", "weather", "ping_all", "ping_one",
                      "system", "calculate", "memory_add", "memory_list"):
            result = self.handle(user_input)
            return result.get("response")
        # memory_q or no intent — try the deterministic memory lookup
        mem = Skills.memory_lookup(user_input, self.memory)
        if mem:
            return mem
        return None

    @staticmethod
    def _r(source, response, start):
        return {"source": source, "response": response, "latency_ms": round((time.time() - start) * 1000, 1)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    router = BMOSkillRouter()
    print("BMO Edge Compute \u2014 Type 'quit' to exit\n")
    while True:
        try:
            user = input("You: ").strip()
            if user.lower() in ("quit", "exit", "q"):
                break
            result = router.handle(user)
            print(f"\nBMO [{result['source'].upper()} | {result['latency_ms']}ms]: {result['response']}\n")
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
