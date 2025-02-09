import json
import requests
from bs4 import BeautifulSoup
import boto3
import os
from openai import OpenAI

# AWS SNS setup
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "test")
sns_client = boto3.client("sns")

# List of websites to scrape
urls = {
    "Reuters AI News": "https://www.reuters.com/technology/artificial-intelligence/",
    "PR Newswire": "https://www.prnewswire.com/news-releases/",
    "LinkedIn Jobs": "https://www.linkedin.com/company/openai/jobs/",
}

# Get search terms as a comma-separated string from the environment,
# then split into a list. Defaults to "Germany, Munich" if not set.
search_terms_str = os.environ.get("SEARCH_TERMS", "Germany, Munich")
SEARCH_TERMS = [term.strip() for term in search_terms_str.split(",")]

# Define the main term to always search for.
MAIN_SEARCH_TERM = os.environ.get("MAIN_SEARCH_TERM")

# OpenAI Platform API Key
openai_api_key = os.environ["OPENAI_API_KEY"]

# Updated headers with the provided user-agent string and additional headers.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def send_sns_notification(subject, message):
    if os.environ.get("LOCAL_ENV"):
        print("⚠️ Running in local env, skipping sending sns notification ...")
        return
    sns_client.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject=subject)


def scrape_reuters_ai_news(url):
    """
    Scrape Reuters AI News page.
    Returns True if the page text contains the main term 'e.g: OpenAI, Amazon'
    and any of the search terms.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(
                f"⚠️ Failed to fetch Reuters AI News (Status Code: {response.status_code})"
            )
            return False
        soup = BeautifulSoup(response.text, "html.parser")
        text_content = " ".join(
            [elem.get_text() for elem in soup.find_all(["p", "h1", "h2", "h3"])]
        )
        # Only flag as updated if both the main term and one of the search terms are present.
        return MAIN_SEARCH_TERM in text_content and any(
            term in text_content for term in SEARCH_TERMS
        )
    except Exception as e:
        print(f"⚠️ Error scraping Reuters AI News: {e}")
        return False


def scrape_pr_newswire(url):
    """
    Scrape the PR Newswire page.
    Returns True if the page text contains the main term 'e.g: OpenAI, Amazon'
    and any of the search terms.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(
                f"⚠️ Failed to fetch PR Newswire (Status Code: {response.status_code})"
            )
            return False
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()
        return MAIN_SEARCH_TERM in page_text and any(
            term in page_text for term in SEARCH_TERMS
        )
    except Exception as e:
        print(f"⚠️ Error scraping PR Newswire: {e}")
        return False


def scrape_linkedin_jobs(url):
    """
    Scrape the LinkedIn Jobs page.
    Returns True if the page text contains the main term 'e.g: OpenAI, Amazon'
    and any of the search terms.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(
                f"⚠️ Failed to fetch LinkedIn Jobs (Status Code: {response.status_code})"
            )
            return False
        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text()
        return MAIN_SEARCH_TERM in page_text and any(
            term in page_text for term in SEARCH_TERMS
        )
    except Exception as e:
        print(f"⚠️ Error scraping LinkedIn Jobs: {e}")
        return False


def get_quote_of_the_day(apikey: str):
    client = OpenAI(api_key=apikey)

    # Create the chat completion with the required parameters
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant that provides inspiring and thoughtful quotes for people searching for jobs in the field of AI in the OpenAI Company.",
            },
            {
                "role": "user",
                "content": f"Can you give me the quote of the day to help me keep motivated while waiting for a new job location opening in: {search_terms_str}?",
            },
        ],
        temperature=0.7,
    )

    # Extract and return the assistant's reply
    return response.choices[0].message.content


def lambda_handler(event, context):
    new_updates = []

    # Mapping of site names to their respective scraping functions.
    scrape_functions = {
        "Reuters AI News": scrape_reuters_ai_news,
        "PR Newswire": scrape_pr_newswire,
        "LinkedIn Jobs": scrape_linkedin_jobs,
    }

    # Create a display string for the main term and search terms.
    search_terms_display = ", ".join([MAIN_SEARCH_TERM] + SEARCH_TERMS)

    for site, url in urls.items():
        try:
            updated = scrape_functions[site](url)
            if updated:
                message = f"✅ {site} has new content mentioning {search_terms_display}!\n🔗 {url}"
                new_updates.append(message)
        except Exception as e:
            print(f"⚠️ Error scraping {site}: {e}")

    # Send SNS notification based on the new_updates list.
    if new_updates:
        subject = (
            f"🚀 {MAIN_SEARCH_TERM} Careers update found for {search_terms_display} location(s)!"
        )
        message = "\n\n".join(new_updates)
        print(message)
        send_sns_notification(subject, message)
    else:
        subject = (
            f"😢 No updates on {MAIN_SEARCH_TERM} Careers for location(s): {search_terms_display}!"
        )
        quote_of_the_day = get_quote_of_the_day(openai_api_key)
        message = (
            f"No updates found for {search_terms_display} in OpenAI location(s).... "
            f"but nevertheless here your daily quote: {quote_of_the_day}"
        )
        print(message)
        send_sns_notification(subject, message)

    return {
        "statusCode": 200,
        "body": json.dumps(f"Scraping completed. Found {len(new_updates)} updates!"),
    }


# For local testing:
if __name__ == "__main__":
    event = {}  # Simulated event
    context = None  # Mock context
    result = lambda_handler(event, context)
    print(result)
