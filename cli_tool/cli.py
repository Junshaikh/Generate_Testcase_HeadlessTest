# cli_tool/cli.py

import os
import re
import argparse
import base64
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def clean_gherkin_output(text):
    text = re.sub(r"\*\*Scenario\s*\d*.*\*\*", "", text)
    text = re.sub(r"```gherkin", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    text = re.sub(r"Scenario\s*\d*:", "Scenario:", text)
    return text.strip()

def sanitize_filename(name):
    name = name.strip().lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name

def get_unique_filename(folder_path, base_filename):
    full_path = os.path.join(folder_path, base_filename + ".txt")
    counter = 1
    while os.path.exists(full_path):
        full_path = os.path.join(folder_path, f"{base_filename}_{counter}.txt")
        counter += 1
    return os.path.basename(full_path)

def upload_to_github(content, file_name, folder, tag=None, other_tags=None):
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name = os.getenv("GITHUB_REPO_NAME")
    branch = os.getenv("GITHUB_BRANCH", "main")
    file_path = f"{folder}/{file_name}"

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    file_url = f"https://github.com/{repo_owner}/{repo_name}/blob/{branch}/{file_path}"
    tag_msg = ""
    if tag or other_tags:
        tags = []
        if tag:
            tags.append(f"`@{tag}`")
        if other_tags:
            tags.extend([f"`@{t.strip()}`" for t in re.split(r"[,\s]+", other_tags) if t])
        tag_msg = "\n\n**Tags**: " + ", ".join(tags)

    message = f"Add test cases for `{file_name}` in `{folder}` folder.{tag_msg}\n\nPreview: {file_url}"
    encoded_content = base64.b64encode(content.encode()).decode()

    data = {
        "message": message,
        "content": encoded_content,
        "branch": branch
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f"✅ Uploaded to GitHub: {file_url}")
    else:
        print(f"❌ GitHub upload failed: {response.status_code} - {response.text}")

def main_generate_tests():
    parser = argparse.ArgumentParser(description="Generate Gherkin test cases from a requirement.")
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--squad", required=True)
    parser.add_argument("--file-name", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--other-tags", default=None)
    parser.add_argument("--background", default=None)
    parser.add_argument("--additional-background", default=None)
    parser.add_argument("--no-upload", action="store_true")

    args = parser.parse_args()

    squad = sanitize_filename(args.squad)
    base_filename = sanitize_filename(args.file_name or args.requirement)
    folder_path = f"test-cases/{squad}"
    os.makedirs(folder_path, exist_ok=True)
    final_filename = get_unique_filename(folder_path, base_filename)
    local_path = os.path.join(folder_path, final_filename)

    prompt = (
        f"You are generating test cases for a food delivery application called '{args.background}'. "
        f"Requirement: {args.requirement}\n"
        f"Additional background: {args.additional_background or 'N/A'}\n"
        "Generate clean Gherkin scenarios. Do not use markdown. Do not number scenarios."
    )

    model = genai.GenerativeModel("gemini-2.0-flash")
    test_cases = clean_gherkin_output(model.generate_content(prompt).text)

    # Add tags
    tags_line = []
    if args.tag:
        tags_line.append(f"@{args.tag}")
    if args.other_tags:
        tags_line += [f"@{t}" for t in re.split(r"[,\s]+", args.other_tags.strip()) if t]
    if tags_line:
        test_cases = " ".join(tags_line) + "\n\n" + test_cases

    with open(local_path, "w") as f:
        f.write(test_cases)
    print(f"✅ Test cases saved to {local_path}")

    if not args.no_upload:
        upload_to_github(test_cases, final_filename, f"test-cases/{squad}", args.tag, args.other_tags)

def main_generate_headless_tests():
    parser = argparse.ArgumentParser(description="Generate headless Flutter test code from a requirement.")
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--squad", required=True)
    parser.add_argument("--file-name", default=None)
    parser.add_argument("--no-upload", action="store_true")

    args = parser.parse_args()

    squad = sanitize_filename(args.squad)
    base_filename = sanitize_filename(args.file_name or args.requirement)
    folder_path = f"headless-test/{squad}"
    os.makedirs(folder_path, exist_ok=True)
    final_filename = get_unique_filename(folder_path, base_filename)
    local_path = os.path.join(folder_path, final_filename)

    prompt = (
        f"Generate headless Flutter test code for the following food delivery requirement:\n"
        f"{args.requirement}\n\n"
        f"Ensure the code is valid Dart and compatible with `flutter test`. "
        f"Do not include markdown or explanations."
    )

    model = genai.GenerativeModel("gemini-2.0-flash")
    test_code = model.generate_content(prompt).text.strip()

    with open(local_path, "w") as f:
        f.write(test_code)
    print(f"✅ Headless Flutter test saved to {local_path}")

    if not args.no_upload:
        upload_to_github(test_code, final_filename, f"headless-test/{squad}")
