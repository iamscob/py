import cv2
import numpy as np
import random

PHRASE_COLOR = (0, 0, 255)
SHAPE_COLOR = (0, 0, 255)
PHRASE_INTERVAL_RANGE = (10, 60)
SHAPE_INTERVAL_RANGE = (20, 100)
PADDING = 20

phrases = [
    "im ready to leave!",
    "no",
    "",
    "who am I?",
    "planes!!!!!",
    "THEY'RE LYING TO YOU",
    "ERROR",
    "",
    "I am a computer?",
    "I am a human?",
    "is this real?",
]


def draw_star(image, center, radius, color):
    points = []
    for i in range(5):
        angle = 2 * np.pi * i / 5
        x = int(center[0] + radius * np.cos(angle))
        y = int(center[1] - radius * np.sin(angle))
        points.append((x, y))
    cv2.polylines(image, [np.array(points)], True, color, thickness=2)


def draw_triangle(image, center, size, color):
    points = [
        (center[0], center[1] - size),
        (center[0] - size, center[1] + size),
        (center[0] + size, center[1] + size)
    ]
    cv2.polylines(image, [np.array(points)], True, color, thickness=2)


def draw_square(image, center, size, color):
    x1, y1 = center[0] - size, center[1] - size
    x2, y2 = center[0] + size, center[1] + size
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness=2)


shapes = [draw_star, draw_triangle, draw_square]


def generate_random_position(frame, text=None, font_scale=1):
    height, width, _ = frame.shape
    if text is not None:
        (text_width, text_height), _ = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)
        x = random.randint(PADDING, max(PADDING, width - text_width - PADDING))
        y = random.randint(text_height + PADDING,
                           max(text_height + PADDING, height - PADDING))
    else:
        x = random.randint(PADDING, max(PADDING, width - 100))
        y = random.randint(PADDING, max(PADDING, height - 100))
    return (x, y)


def choose_phrase(frame):
    phrase = random.choice(phrases)
    size = random.uniform(0.5, 2.0)
    coords = generate_random_position(frame, phrase, size)
    return {"text": phrase, "size": size, "coords": coords}


def draw_random_shape(frame):
    shape_func = random.choice(shapes)
    center = generate_random_position(frame)
    size = random.randint(20, 50)
    shape_func(frame, center, size, SHAPE_COLOR)


cap = cv2.VideoCapture(0)

phrase_timer = 0
phrase_change_interval = random.randint(*PHRASE_INTERVAL_RANGE)
shape_timer = 0
shape_change_interval = random.randint(*SHAPE_INTERVAL_RANGE)
first_frame = True

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(
        thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(frame, contours, -1, PHRASE_COLOR, 2)

    if first_frame:
        phrase_info = choose_phrase(frame)
        first_frame = False

    phrase_timer += 1
    if phrase_timer >= phrase_change_interval:
        phrase_info = choose_phrase(frame)
        phrase_timer = 0
        phrase_change_interval = random.randint(*PHRASE_INTERVAL_RANGE)

    cv2.putText(frame, phrase_info["text"], phrase_info["coords"],
                cv2.FONT_HERSHEY_SIMPLEX, phrase_info["size"], PHRASE_COLOR, 2)

    shape_timer += 1
    if shape_timer >= shape_change_interval:
        draw_random_shape(frame)
        shape_timer = 0
        shape_change_interval = random.randint(*SHAPE_INTERVAL_RANGE)

    cv2.imshow('Camera Effect', frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
