import os

import requests


async def analyze_report_with_openai(report, image_urls=[]):
    openai_api_key = os.getenv("OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {openai_api_key}"}

    messages = [{"role": "user", "content": [{"type": "text", "text": report}]}]
    for url in image_urls:
        messages[0]["content"].append({"type": "image_url", "image_url": {"url": url}})

    data = {"model": "gpt-4-vision-preview", "messages": messages, "max_tokens": 2000}

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=data
    )
    if response.status_code == 200:
        response_data = response.json()
        return (
            response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return "Не вдалося проаналізувати звіт."
