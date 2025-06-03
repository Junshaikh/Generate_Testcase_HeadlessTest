# cli.py
import os
import re
import google.generativeai as genai
import requests
import base64
import argparse
from dotenv import load_dotenv
load_dotenv()

# Load Gemini API key from environment
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

def generate_test_cases(requirement, squad, custom_filename=None, tag=None, other_tags=None, skip_upload=False):
    squad = sanitize_filename(squad)
    suggested_filename = sanitize_filename(requirement)
    base_filename = sanitize_filename(custom_filename) if custom_filename else suggested_filename
    folder_path = f"test-cases/{squad}"
    os.makedirs(folder_path, exist_ok=True)

    final_filename = get_unique_filename(folder_path, base_filename)
    local_path = os.path.join(folder_path, final_filename)

    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = (
        f"Generate functional software test cases in clean Gherkin format for this requirement: {requirement}.\n"
        f"Do NOT add any labels like Scenario 1/2 or markdown formatting such as ```gherkin. Only clean Gherkin."
    )
    response = model.generate_content(prompt)
    test_cases_raw = response.text
    test_cases = clean_gherkin_output(test_cases_raw)

    tags_line = f"@{tag}" if tag else ""
    if other_tags:
        tags_line += " " + " ".join(t.strip() for t in other_tags.split(","))
    if tags_line.strip():
        test_cases = f"{tags_line.strip()}\n\n" + test_cases

    with open(local_path, "w") as file:
        file.write(test_cases)

    print("\n📦 Sample Output from AI (for {}):\n\n{}".format(requirement, test_cases))
    print(f"\n✅ Test cases saved to {local_path}")

    if not skip_upload:
        upload_to_github(test_cases, final_filename, squad)
    else:
        print("⚠️ Skipping GitHub upload (--no-upload enabled)")

def upload_to_github(content, file_name, squad):
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name = os.getenv("GITHUB_REPO_NAME", "Generate_Testcase_HeadlessTest")
    file_path = f"test-cases/{squad}/{file_name}"
    branch = os.getenv("GITHUB_BRANCH", "main")

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json"
    }

    file_url = f"https://github.com/{repo_owner}/{repo_name}/blob/{branch}/{file_path}"
    message = f"Add test cases for `{file_name}` in `{squad}` squad.\n\nPreview: {file_url}"
    encoded_content = base64.b64encode(content.encode()).decode()

    data = {
        "message": message,
        "content": encoded_content,
        "branch": branch
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print(f"✅ Test case uploaded to GitHub: {file_url}")
    else:
        print(f"❌ Failed to upload file: {response.status_code} - {response.text}")

def main():
    parser = argparse.ArgumentParser(description="Generate Gherkin test cases from a requirement.")
    parser.add_argument("--requirement", "-r", help="Requirement description", default=os.getenv("REQUIREMENT"))
    parser.add_argument("--squad", "-s", help="Squad name (e.g., squad-auth)", default=os.getenv("SQUAD"))
    parser.add_argument("--filename", "-f", help="Custom file name", default=os.getenv("FILENAME"))
    parser.add_argument("--tag", help="Primary tag (e.g., P0, P1)", default=os.getenv("TAG"))
    parser.add_argument("--other-tags", help="Other tags (e.g., @smoke,@login)", default=os.getenv("OTHER_TAGS"))
    parser.add_argument("--no-upload", action="store_true", default=os.getenv("NO_UPLOAD") == "true")

    args = parser.parse_args()
    generate_test_cases(
        args.requirement,
        args.squad,
        args.filename,
        args.tag,
        args.other_tags,
        skip_upload=args.no_upload
    )

if __name__ == "__main__":
    main()
