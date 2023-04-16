import requests
import datetime
import json

# Initialize bearer_token to None
bearer_token = None

# Main function to handle power management
def handler(context, inputs):
    global bearer_token
    
    # Retrieve bearer_token from vraauth function
    bearer_token = vraauth(inputs)
    
    # Obtain resource IDs with the "powersave" tag
    resource_ids = get_resource_ids_with_powersave_tag(bearer_token, inputs)
    
    # Determine the current time
    current_time = datetime.datetime.now().time()
    print(f"Current time is {current_time}")
    
    # Define power on and power off window
    power_on_end = datetime.time(hour=16)
    power_off_start = datetime.time(hour=16)

    # Check if the current time is before or after 16:00, then power on or off resources accordingly
    if current_time < power_on_end:
        send_to_slack("POWERSAVE: Current time is within the power on window, powering on resources", inputs)
        power_on_resources(resource_ids, inputs, bearer_token)
    elif current_time >= power_off_start:
        send_to_slack("POWERSAVE: Current time is within the power off window, powering off resources", inputs)
        power_off_resources(resource_ids, inputs, bearer_token)
    else:
        print("No action needed")


# Function to send a message to a Slack channel
def send_to_slack(message, inputs):
    # Slack webhook URL
    webhook_url = inputs["slack_webhook_url"]

    # Slack message payload
    payload = {
        "text": message
    }

    # Send the message to Slack using the requests library
    response = requests.post(
        webhook_url, data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )

    # Raise an error if the response status code is not 200 OK
    if response.status_code != 200:
        raise ValueError(
            f'Request to Slack returned an error {response.status_code}, the response is:\n{response.text}'
        )


# Function to power off resources
def power_off_resources(resource_ids, inputs, bearer_token):
    # vRA API URL
    url = inputs["vra_url"]
    # vRA API headers with bearer token
    vraheaders = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "Bearer " + bearer_token
    }
    # Loop through each resource ID and power it off
    with requests.Session() as session:
        for resource_id in resource_ids:
            # vRA API payload to power off the resource
            payload = {
                "actionId": "Cloud.vSphere.Machine.Shutdown",
                "inputs": {},
                "reason": "Power Off"
            }
            # Send the power off request to vRA using the requests library
            resp = session.post(f"{url}/deployment/api/resources/{resource_id}/requests", headers=vraheaders, json=payload, verify=False)
            try:
                # Raise an error if the response status code is not 200 OK
                resp.raise_for_status()
                # Send a message to Slack to inform that the resource is being powered off
                send_to_slack(f"POWERSAVE: Power off successfully called for resource ID: {resource_id}", inputs)
            except requests.exceptions.HTTPError as err:
                # If the status code is 400, log the error and continue to the next resource
                if err.response.status_code == 400:
                    print(f"Power off failed for resource ID {resource_id}: {err}. Is it already powered off?", inputs)
                else:
                    # If the status code is not 400, raise the error
                    raise


# Function to power on resources
def power_on_resources(resource_ids, inputs, bearer_token):
    # vRA API URL
    url = inputs["vra_url"]
    # vRA API headers with bearer token
    vraheaders = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "Bearer " + bearer_token
    }
    # Loop through each resource ID and power it on
    with requests.Session() as session:
        for resource_id in resource_ids:
            # vRA API payload to power on the resource
            payload = {
                "actionId": "Cloud.vSphere.Machine.PowerOn",
                "inputs": {},
                "reason": "Power On"
            }
            # Send the power on request to vRA using the requests library
            resp = session.post(f"{url}/deployment/api/resources/{resource_id}/requests", headers=vraheaders, json=payload, verify=False)
            try:
                # Raise an error if the response status code is not 200 OK
                resp.raise_for_status()
                # Send a message to Slack to inform that the resource is being powered on
                send_to_slack(f"POWERSAVE: Power on successfully called for resource ID: {resource_id}", inputs)
            except requests.exceptions.HTTPError as err:
                # If the status code is 400, log the error and continue to the next resource
                if err.response.status_code == 400:
                    print(f"Power on failed for resource ID {resource_id}: {err}. Is it already powered on?", inputs)
                else:
                    # If the status code is not 400, raise the error
                    raise



# Function to get resource IDs with "powersave" tag
def get_resource_ids_with_powersave_tag(bearer_token, inputs):
    # vRA API URL
    url = inputs["vra_url"]
    # vRA API headers with bearer token
    vraheaders = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "Bearer " + bearer_token
    }
    # Initialize an empty list to store the resource IDs
    resource_ids = []
    # Use a session to make multiple requests to the vRA API
    with requests.Session() as session:
        # Make a GET request to the /deployments endpoint to get deployments where resourceTypes=Cloud.vSphere.Machine and tags:powersave=true
        resp = session.get(f"{url}/deployment/api/resources/?resourceTypes=Cloud.vSphere.Machine&tags=powersave:true", headers=vraheaders, verify=False)
        # Raise an error if the response status code is not 200 OK
        resp.raise_for_status()
        # Get the content of the response and loop through each deployment
        json_resp = resp.json()
        # extract the IDs from the JSON object
        resource_ids = [item["id"] for item in json_resp["content"]]
        # print the IDs
        #print(f"Resource IDs are: {resource_ids}")
        return resource_ids


# Function to get bearer token for vRA API
def vraauth(inputs):
    # vRA API URL
    url = inputs["vra_url"]
    # vRA login credentials
    vralogin = {
        "username": inputs["vra_username"],
        "password": inputs["vra_password"],
        "domain": inputs['vra_domain']
    }
    # vRA API headers
    vraheaders = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    # Use a session to make multiple requests to the vRA API
    with requests.Session() as session:
        # Make a POST request to the /csp/gateway/am/api/login?access_token endpoint to get a refresh token
        resp = session.post(f"{url}/csp/gateway/am/api/login?access_token", json=vralogin, headers=vraheaders, verify=False)
        # Raise an error if the response status code is not 200 OK
        resp.raise_for_status()
        # Get the refresh token from the response
        refresh_token = {"refreshToken": resp.json()['refresh_token']}
        # Make a POST request to the /iaas/api/login endpoint to get a bearer token
        resp = session.post(f"{url}/iaas/api/login", json=refresh_token, headers=vraheaders, verify=False)
        # Raise an error if the response status code is not 200 OK
        resp.raise_for_status()
        # Get the bearer token from the response and return it
        bearer_token = resp.json()['token']
        return bearer_token
