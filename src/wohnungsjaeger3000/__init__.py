import os
import sys

from wohnungsjaeger3000.scraper import WohnungsSpider, scrape_data


def main() -> None:
    if not os.getenv("MISTRAL_API_KEY"):
        print("Error: MISTRAL_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    scrape_data()


if __name__ == '__main__':
    main()
