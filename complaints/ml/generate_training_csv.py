import csv
import random
from pathlib import Path


ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
CSV_PATH = ARTIFACTS_DIR / "complaints_training_data.csv"
TARGET_ROWS = 100_000


DEPARTMENT_TEMPLATES = {
    "MC-PWD": [
        "huge potholes on the main road near {landmark}",
        "road surface broken and unsafe for vehicles at {landmark}",
        "footpath is damaged and people are tripping at {landmark}",
    ],
    "MC-WATER": [
        "no water supply since {days} days in {area}",
        "dirty contaminated water coming from tap in {area}",
        "very low water pressure in taps at {area}",
    ],
    "MC-SWM": [
        "garbage not collected for {days} days in {area}",
        "dustbin overflowing and bad smell near {landmark}",
        "no street cleaning happening around {area}",
    ],
    "MC-HEALTH": [
        "mosquito breeding due to stagnant water near {landmark}",
        "dispensary not functioning properly in {area}",
        "dirty public toilet not cleaned at {landmark}",
    ],
    "MC-SEWER": [
        "open manhole very dangerous at {landmark}",
        "sewer water overflowing on road in {area}",
        "drainage blocked causing waterlogging near {landmark}",
    ],
    "STATE-ELEC": [
        "frequent power cuts in my locality {area}",
        "transformer making noise and sparking near {landmark}",
        "electricity bill seems wrong and very high for {area}",
    ],
    "STATE-PHED": [
        "village water scheme not working in {area}",
        "handpump water contaminated and not safe in {area}",
    ],
    "STATE-PWD": [
        "highway full of potholes near {landmark}",
        "bridge has visible cracks and looks unsafe at {landmark}",
    ],
    "POLICE-TRAF": [
        "traffic signal not working at {landmark} junction",
        "illegal parking blocking road near {landmark}",
    ],
    "MC-FIRE": [
        "fire safety violation noticed in building at {landmark}",
        "fire hydrant not working near {landmark}",
    ],
    "DIST-HEALTH": [
        "government hospital staff not available at {landmark}",
        "ambulance not coming on time in {area}",
    ],
    "STATE-POLL": [
        "factory releasing toxic smoke and pollution near {area}",
        "construction dust causing breathing problem at {landmark}",
    ],
    "STATE-FCS": [
        "ration shop not giving full quantity in {area}",
        "pds shop closed for many days at {landmark}",
    ],
    "POLICE-LOCAL": [
        "loud noise at night disturbing area around {area}",
        "chain snatching incident reported near {landmark}",
    ],
    "JUD-CONS": [
        "billing dispute with service provider in {area}",
        "internet provider not resolving service issue in {area}",
    ],
    "DIST-REV": [
        "property tax calculation seems wrong for house in {area}",
        "name not updated in land records at {landmark}",
    ],
    "MC-TP": [
        "illegal encroachment on government land at {landmark}",
        "building constructed without permission in {area}",
    ],
    "MC-PARK": [
        "park lights not working in {area}",
        "playground equipment broken at {landmark}",
    ],
}


PRIORITY_WEIGHTS = {
    "LOW": 1,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 2,
}


AREAS = [
    "Sector 10",
    "Sector 21",
    "Green Park Colony",
    "Old City",
    "New Market Area",
    "Industrial Area",
    "Railway Station Road",
    "Bus Stand Area",
    "Civil Lines",
    "University Road",
]

LANDMARKS = [
    "main square",
    "bus stand",
    "railway station",
    "city hospital",
    "market chowk",
    "school gate",
    "temple crossing",
    "mall entrance",
    "bridge corner",
    "police station",
]


def sample_priority() -> str:
    choices = list(PRIORITY_WEIGHTS.keys())
    weights = list(PRIORITY_WEIGHTS.values())
    return random.choices(choices, weights=weights, k=1)[0]


def generate_row() -> dict:
    dept_code = random.choice(list(DEPARTMENT_TEMPLATES.keys()))
    template = random.choice(DEPARTMENT_TEMPLATES[dept_code])
    area = random.choice(AREAS)
    landmark = random.choice(LANDMARKS)
    days = random.randint(1, 10)

    text = template.format(area=area, landmark=landmark, days=days)

    # Add slight natural variation
    prefixes = [
        "",
        "urgent: ",
        "request: ",
        "please resolve soon: ",
        "serious issue: ",
    ]
    suffixes = [
        "",
        " this is causing lot of inconvenience.",
        " people are facing many problems.",
        " kindly take immediate action.",
        " situation is getting worse.",
    ]

    if random.random() < 0.5:
        text = random.choice(prefixes) + text
    if random.random() < 0.7:
        text = text + random.choice(suffixes)

    priority = sample_priority()

    return {
        "text": text,
        "department_code": dept_code,
        "priority": priority,
    }


def generate_csv(rows: int = TARGET_ROWS) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["text", "department_code", "priority"]
        )
        writer.writeheader()
        for i in range(rows):
            writer.writerow(generate_row())
            if (i + 1) % 10_000 == 0:
                print(f"Generated {i + 1} / {rows} rows...")

    print(f"CSV written to {CSV_PATH} with {rows} rows.")


if __name__ == "__main__":
    generate_csv()

