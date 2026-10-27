import os, time, json, cv2, requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ---------- CONFIG (edit these) ----------
API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-3.8-flash"       # check AI Studio for the current fast model name
ESP_URL = "http://192.168.4.1"   # default address of an ESP8266 in access-point mode
CAMERA_INDEX = 0                 # change after running test_camera.py
MIN_CONFIDENCE = 0.60            # below this, item goes to General Waste
CYCLE_TIMEOUT = 60               # max seconds to wait for a sort cycle

COMMANDS = {
    "Plastic": 1,         # Top Left
    "Metal": 2,           # Top Right
    "Paper": 3,           # Mid Left
    "Small E-Waste": 4,   # Mid Right
    "Food Waste": 5,      # Bottom Left
    "General Waste": 6,   # Bottom Right
}

PROMPT = """You are the vision system of an automatic waste-sorting bin.
Look at the single item shown and classify it into exactly one category:

- Plastic: bottles, containers, plastic bags, wrappers, cups, utensils
- Metal: aluminum/steel cans, foil, metal lids
- Paper: paper, cardboard, newspaper, paper cups/boxes (clean and dry)
- Small E-Waste: batteries, cables, earphones, chargers, small electronics
- Food Waste: fruit/vegetable scraps, leftovers, peels, bones
- General Waste: anything else, mixed/soiled materials, tissue, multi-material items
- Empty: no item is visible

If the item is mixed material or you are unsure, choose General Waste.
Return the category, a confidence from 0 to 1, and a short item name."""

SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(COMMANDS.keys()) + ["Empty"]},
        "confidence": {"type": "number"},
        "item": {"type": "string"},
    },
    "required": ["category", "confidence", "item"],
}

client = genai.Client(api_key=API_KEY)


def classify(frame):
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    image_part = types.Part.from_bytes(data=buf.tobytes(), mime_type="image/jpeg")
    resp = client.models.generate_content(
        model=MODEL,
        contents=[image_part, PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_level="LOW"),
        ),
    )
    return json.loads(resp.text)


def send_command(n):
    try:
        r = requests.get(f"{ESP_URL}/cmd", params={"c": n}, timeout=5)
        return r.ok
    except requests.RequestException as e:
        print("Could not reach ESP8266:", e)
        return False


def wait_until_idle():
    start = time.time()
    while time.time() - start < CYCLE_TIMEOUT:
        try:
            if requests.get(f"{ESP_URL}/status", timeout=3).text.strip() == "idle":
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    print("Click the camera window first.  SPACE = classify & sort | Q = quit")
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        cv2.imshow("SEGBIN Camera", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        if key == ord(" "):
            result = classify(frame)
            print(result)
            cat, conf = result["category"], result["confidence"]

            if cat == "Empty":
                print("Nothing detected.\n")
                continue
            if conf < MIN_CONFIDENCE:
                print(f"Low confidence ({conf:.2f}), using General Waste")
                cat = "General Waste"

            n = COMMANDS[cat]
            print(f"-> {cat} (command {n})")
            if send_command(n):
                wait_until_idle()
                print("Ready for next item.\n")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()