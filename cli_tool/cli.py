import os
import re
import google.generativeai as genai
import requests
import base64
import argparse
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
        combined_tags = []
        if tag:
            combined_tags.append(f"`@{tag}`")
        if other_tags:
            extra_tags = re.split(r"[,\s]+", other_tags.strip())
            combined_tags.extend([f"`@{t}`" if not t.startswith("@") else f"`{t}`" for t in extra_tags if t])
        tag_msg = "\n\n**Tags**: " + ", ".join(combined_tags)

    message = f"Add test for `{file_name}` in `{folder}` folder.{tag_msg}\n\nPreview: {file_url}"
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
        print(f"❌ Failed to upload file: {response.status_code} - {response.text}")

def generate_test_cases(requirement, squad, custom_filename=None, skip_upload=False, tag=None, other_tags=None, additional_background=None):
    squad = sanitize_filename(squad)
    suggested_filename = sanitize_filename(requirement)
    base_filename = sanitize_filename(custom_filename) if custom_filename else suggested_filename
    folder_path = f"test-cases/{squad}"
    os.makedirs(folder_path, exist_ok=True)

    final_filename = get_unique_filename(folder_path, base_filename)
    local_path = os.path.join(folder_path, final_filename)

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        f"You are an experienced QA tester for the Talabat food application.\n"
        f"Generate clean Gherkin test cases for the following requirement:\n"
        f"\"{requirement}\"\n"
    )
    if additional_background:
        prompt += f"\nAdditional context: {additional_background}\n"

    prompt += "Output should only contain plain Gherkin format. Do not use markdown or scenario numbers."

    response = model.generate_content(prompt)
    test_cases_raw = response.text
    test_cases = clean_gherkin_output(test_cases_raw)

    # Add tags if needed
    tags_line = []
    if tag:
        tags_line.append(f"@{tag}")
    if other_tags:
        extra_tags = re.split(r"[,\s]+", other_tags.strip())
        tags_line.extend([t if t.startswith("@") else f"@{t}" for t in extra_tags if t])
    if tags_line:
        test_cases = " ".join(tags_line) + "\n\n" + test_cases

    with open(local_path, "w") as file:
        file.write(test_cases)

    print(f"✅ Test cases saved to {local_path}")

    if not skip_upload:
        upload_to_github(test_cases, final_filename, f"test-cases/{squad}", tag, other_tags)
    else:
        print("⚠️ Skipping GitHub upload (--no-upload enabled)")

def generate_headless_flutter_tests(requirement, squad, custom_filename=None, skip_upload=False, tag=None, other_tags=None, additional_background=None):
    squad = sanitize_filename(squad)
    suggested_filename = sanitize_filename(requirement)
    base_filename = sanitize_filename(custom_filename) if custom_filename else suggested_filename
    folder_path = f"headless-test/{squad}"
    os.makedirs(folder_path, exist_ok=True)

    final_filename = get_unique_filename(folder_path, base_filename)
    local_path = os.path.join(folder_path, final_filename)

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = (
        f"You are an expert Flutter automation engineer. Based on the Talabat food application, "
        f"generate headless Flutter integration test code in Dart for this requirement:\n"
        f"\"{requirement}\"\n"
    )
    if additional_background:
        prompt += f"\nAdditional context: {additional_background}\n"

    prompt += "Only return clean Dart code. Do not include markdown, explanations, or extra formatting."

    response = model.generate_content(prompt)
    test_code = response.text.strip()

    with open(local_path, "w") as file:
        file.write(test_code)

    print(f"✅ Headless Flutter test saved to {local_path}")

    if not skip_upload:
        upload_to_github(test_code, final_filename, f"headless-test/{squad}", tag, other_tags)
    else:
        print("⚠️ Skipping GitHub upload (--no-upload enabled)")

def main():
    parser = argparse.ArgumentParser(description="Generate Gherkin test cases from a requirement.")
    parser.add_argument("--requirement", "-r", required=True, help="Requirement description")
    parser.add_argument("--squad", "-s", required=True, help="Squad name (e.g., squad-auth)")
    parser.add_argument("--file-name", "-f", help="Custom file name", default=os.getenv("FILE_NAME"))
    parser.add_argument("--tag", "-t", help="Priority tag (e.g., P0, P1)", default=os.getenv("TAG"))
    parser.add_argument("--other-tags", help="Other tags (e.g., smoke, login)", default=os.getenv("OTHER_TAGS"))
    parser.add_argument("--additional-background", help="Additional background like login status", default=os.getenv("ADDITIONAL_BACKGROUND"))
    parser.add_argument("--no-upload", action="store_true", default=os.getenv("NO_UPLOAD") == "true")

    args = parser.parse_args()
    generate_test_cases(args.requirement, args.squad, args.file_name, args.no_upload, args.tag, args.other_tags, args.additional_background)

def main_generate_headless_tests():
    parser = argparse.ArgumentParser(description="Generate headless Flutter test code from a requirement.")
    parser.add_argument("--requirement", "-r", required=True, help="Requirement description")
    parser.add_argument("--squad", "-s", required=True, help="Squad name (e.g., squad-auth)")
    parser.add_argument("--file-name", "-f", help="Custom file name", default=os.getenv("FILE_NAME"))
    parser.add_argument("--tag", "-t", help="Priority tag (e.g., P0, P1)", default=os.getenv("TAG"))
    parser.add_argument("--other-tags", help="Other tags (e.g., smoke, login)", default=os.getenv("OTHER_TAGS"))
    parser.add_argument("--additional-background", help="Additional background like login status", default=os.getenv("ADDITIONAL_BACKGROUND"))
    parser.add_argument("--no-upload", action="store_true", default=os.getenv("NO_UPLOAD") == "true")

    args = parser.parse_args()
    generate_headless_flutter_tests(args.requirement, args.squad, args.file_name, args.no_upload, args.tag, args.other_tags, args.additional_background)
