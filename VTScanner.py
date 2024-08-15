import hashlib
import argparse
from time import sleep
from pathlib import Path
from pprint import pprint
import requests
import os
import pandas as pd

try:
    from key import API_KEY
except:
    API_KEY = "Enter API Key"


HEADERS = {"x-apikey": API_KEY}


def hash_it(file, algorithm):
    '''
    Returns hash of the file provided

    :param file: file to hash (type: str/pathlib obj) :param algorithm: algorithm to
    to use for hashing (valid algorithms: sha1 | sha256 | md5) (type: str)
    :return: file hash (type: str)
    '''
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise Exception(
            "Incompatible hash algorithm used. Choose from: sha256 | sha1 | md5")

    with open(file, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def vt_get_data(f_hash):
    '''
    The function gets the data against the file hash provided
    from the virustotal api

    :param f_hash: sha256 of the file to scan with virustotal
    :return: requests.models.Response
    '''
    url = f"https://www.virustotal.com/api/v3/files/{f_hash}"
    while True:
        response = requests.get(url, headers=HEADERS)
        if error_handle(response):
            break
    return response


def vt_post_files(file, url="https://www.virustotal.com/api/v3/private/files"):
    '''
    The function uploads a file to virustotal
    for analysis and returns the response from the
    virustotal api

    :param file: file to upload for analysis :param url: url to upload
    file to (use for files larger than 32MB) :return: requests.models.Response
    '''
    with open(file, "rb") as f:
        file_bin = f.read()
    print("UPLOADING")
    upload_package = {"file": (file.name, file_bin)}
    while True:
        response = requests.post(url, headers=HEADERS, files=upload_package)
        if error_handle(response):
            break
    return response


def vt_get_analyses(response):
    '''
    The function returns the file hash of the uploaded file
    once the analysis of the uploaded file is available

    :param response: requests.models.Response
    :return: sha256 of the previously uploaded file (type: str)
    '''
    _id = response.json().get("data").get("id")
    url = f"https://www.virustotal.com/api/v3/private/analyses/{_id}"
    print(f"ID: {_id}")
    while True:
        print("WAITING FOR ANALYSIS REPORT")
        sleep(60)
        while True:
            response = requests.get(url, headers=HEADERS)
            if error_handle(response):
                break
        if response.json().get("data").get("attributes").get("status") == "completed":
            f_hash = response.json().get("meta").get("file_info").get("sha256")
            return f_hash


def vt_get_upload_url():
    '''
    The function returns a url to upload files larger than 32MB
    to the virustotal api
    '''
    url = "https://www.virustotal.com/api/v3/private/files/upload_url"
    while True:
        response = requests.get(url, headers=HEADERS)
        if error_handle(response):
            break
    return response.json()["data"]


def error_handle(response):
    '''
    The function returns True if there are no errors
    and returns False otherwise

    :param response: requests.models.Response
    :return: bool
    '''
    if response.status_code == 429:
        print("WAITING")
        sleep(60)
    if response.status_code == 401:
        raise Exception("Invalid API key")
    elif response.status_code not in (200, 404, 429):
        raise Exception(response.status_code)
    else:
        return True
    return False

def parse_response(response):
    '''
    The function extracts useful information from the respose JSON file
    and return it in JSON format.

    :param response: requests.models.Response
    :return: parsed data as json/dict
    '''
    json_obj = response.json().get("data").get("attributes")
    
    output = {}

    output["name"] = json_obj.get("meaningful_name")
    output["stats"] = json_obj.get("last_analysis_stats")
    output["engine_detected"] = {}

    for engine in json_obj.get("last_analysis_results").keys():
        if json_obj.get("last_analysis_results").get(engine).get("category") != "undetected":
            output.get("engine_detected")[engine] = {}
            output.get("engine_detected")[engine]["category"] = json_obj.get(
                "last_analysis_results").get(engine).get("category")
            output.get("engine_detected")[engine]["result"] = json_obj.get(
                "last_analysis_results").get(engine).get("result")
            
    output["permission_details"] = {}
    
    permission_details = json_obj.get("androguard", {}).get("permission_details")
    if permission_details:
        for permission in permission_details.keys():
            output["permission_details"][permission] = {}
            output["permission_details"][permission]["permission_type"] = permission_details[permission].get("permission_type")
            output["permission_details"][permission]["short_description"] = permission_details[permission].get("short_description")
            output["permission_details"][permission]["full_description"] = permission_details[permission].get("full_description")


    output["votes"] = json_obj.get("total_votes")
    output["hash"] = {"sha1": json_obj.get(
        "sha1"), "sha254": json_obj.get("sha256")}
    output["size"] = json_obj.get("size")
    return output

def bar(parsed_response):
    '''
    The function returns a bar to visually represent the engine
    detection.

    :param parsed_response: parsed dict/json from parse_response() function
    :return: bar (type: str)
    '''
    total = 72
    undetected = parsed_response.get("stats").get("undetected")
    data = f"{'@'*undetected}{' '*(total-undetected)}"
    bar = bar = f"+{'-'*total}+\n|{data}| {undetected}/{total} did not detect\n+{'-'*total}+"
    bar = bar = f"{undetected}/{total} did not detect"
    return bar

def response_to_excel(parsed_responses, output_file, permission_file):
    data_list = []
    permissions_list = []
    seen_permissions = set()  # Set to track unique permissions

    for parsed_response in parsed_responses:
        data = {}

        data["name"] = parsed_response.get("name")
        data["size"] = parsed_response.get("size")
        data["sha1"] = parsed_response.get("hash").get("sha1")
        
        if parsed_response.get("stats"):
            for key, value in parsed_response.get("stats").items():
                data[key] = value
                
        if parsed_response.get("permission_details"):
            permissions = []
            for key, value in parsed_response.get("permission_details").items():
                permissions.append(key)
                # Add a new dictionary for each permission detail
                if key not in seen_permissions:
                    seen_permissions.add(key)
                    permission_data = {
                        "permission": key,
                        "permission_type": value.get("permission_type"),
                        "short_description": value.get("short_description"),
                        "full_description": value.get("full_description")
                    }
                    permissions_list.append(permission_data)

            data["permission_details"] = '\n'.join(permissions)
        
        data_list.append(data)

    # Create DataFrames from the lists
    df = pd.DataFrame(data_list)
    df2 = pd.DataFrame(permissions_list)

    # Write DataFrames to Excel files
    df.to_excel(output_file, index=False)
    df2.to_excel(permission_file, index=False)

######################################SCRIPT######################################
def main():
    
    parser = argparse.ArgumentParser(description="scan your files with virustotal")
    parser.add_argument("path", action="store", nargs=1, help="file or directory to scan")
    parser.add_argument("output", action="store", nargs=1, help="output Excel file")
    parser.add_argument("output2", action="store", nargs=1, help="permissions Excel file")

    parsed_arg = parser.parse_args()
    path = Path(parsed_arg.path[0])

    response_list = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = [path / f for f in os.listdir(path) if (path / f).is_file()]
    else:
        raise Exception("Path is neither a file nor a directory")

    for file in files:
        
        print("Getting data for: ", file)

        if not file.exists():
            raise Exception(f"File not found: {file}")

        # calculate file hash
        f_hash = hash_it(file, "sha256")

        # get file data against the file hash
        response = vt_get_data(f_hash)

        if response.status_code == 404:

            if file.stat().st_size > 32000000:
                # for files larger than 32MB
                response = vt_get_data(vt_get_analyses(
                    vt_post_files(file, vt_get_upload_url())))
            else:
                # for small files
                response = vt_get_data(vt_get_analyses(vt_post_files(file)))

        if response.status_code == 200:
            # parse and print response
            parsed_response = parse_response(response)

            response_list.append(parsed_response)
        else:
            raise Exception(response.status_code)

    output_file = Path(parsed_arg.output[0])
    permission_file = Path(parsed_arg.output2[0])
    response_to_excel(response_list, output_file, permission_file)

if __name__ == "__main__":
    main()