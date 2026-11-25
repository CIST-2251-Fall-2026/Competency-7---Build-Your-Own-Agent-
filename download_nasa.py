import requests
from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path

# NASA pages required for the assignment
pages = {
    "solar_system": "https://science.nasa.gov/solar-system/solar-system-facts/",
    "mercury": "https://science.nasa.gov/mercury/facts/",
    "venus": "https://science.nasa.gov/venus/facts/",
    "earth": "https://science.nasa.gov/earth/facts/",
    "mars": "https://science.nasa.gov/mars/facts/",
    "jupiter": "https://science.nasa.gov/jupiter/facts/",
    "saturn": "https://science.nasa.gov/saturn/facts/",
    "uranus": "https://science.nasa.gov/uranus/facts/",
    "neptune": "https://science.nasa.gov/neptune/facts/"
}

# Create the folder where articles will be saved
folder = Path("nasa_docs")
folder.mkdir(exist_ok=True)

# Download each NASA article
for name, url in pages.items():
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unnecessary website elements
        for element in soup.select(
            "nav, footer, header, script, style, aside, form"
        ):
            element.decompose()

        # Find the main article content
        article = soup.find("article") or soup.find("main")

        if article is None:
            print(f"Could not find article: {name}")
            continue

        title = soup.title.get_text(strip=True) if soup.title else name
        text = article.get_text(separator="\n", strip=True)

        # Save the article with its source information
        content = (
            f"# {title}\n\n"
            f"Source: {url}\n"
            f"Retrieved: {date.today()}\n\n"
            f"{text}\n"
        )

        file_path = folder / f"{name}.md"
        file_path.write_text(content, encoding="utf-8")

        print(f"Saved: {file_path}")

    except requests.RequestException as error:
        print(f"Error downloading {name}: {error}")

print("NASA article download finished!")