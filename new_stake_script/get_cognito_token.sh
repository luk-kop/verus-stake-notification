#!/usr/bin/env bash

# Script can be used to fetch Cognito Access Token or to call API Gateway (with Access Token onboard)
env_file_path=".env-api"

# Check whether $env_file_path exists
if [ ! -f "$env_file_path" ]; then
  echo
  echo "File $env_file_path not found!"
  echo
  exit 1
fi

# Load data from .env-api
source $env_file_path

# Declare dict for env variables from $env_file_path
declare -A env_var_dict
env_var_dict["NOTIFICATION_API_URL"]="$NOTIFICATION_API_URL"
env_var_dict["COGNITO_CLIENT_ID"]="$COGNITO_CLIENT_ID"
env_var_dict["COGNITO_CLIENT_SECRET"]="$COGNITO_CLIENT_SECRET"
env_var_dict["COGNITO_TOKEN_URL"]="$COGNITO_TOKEN_URL"
env_var_dict["COGNITO_OAUTH_LIST_OF_SCOPES"]="$COGNITO_OAUTH_LIST_OF_SCOPES"

# Check whether all necessary env variables are specified in $env_file_path file
for env_var in "${!env_var_dict[@]}"; do
  if [ -z ${env_var_dict[$env_var]} ]; then
    echo
    echo "\"${env_var}\" variable is not specified in $env_file_path file!"
    echo
    exit 1
  fi
done

get_access_token() {
  # Base64 encode
  local client_data_base64="$(echo -n "$COGNITO_CLIENT_ID:$COGNITO_CLIENT_SECRET" | openssl base64)"

  local response=$(curl --silent --request POST \
    --header 'Content-Type: application/x-www-form-urlencoded' \
    --header "Authorization: Basic $(echo $client_data_base64)" \
    --data-urlencode 'grant_type=client_credentials' \
    --data-urlencode "scope=$(echo $COGNITO_OAUTH_LIST_OF_SCOPES)" \
    $COGNITO_TOKEN_URL)
#  local access_token="$(echo $response | jq --raw-output '.access_token')"
local access_token="$(echo $response | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')"
  echo $access_token
}

call_api() {
  local token=$1
  echo
  echo "API Gateway response:"
  curl --silent --header "Authorization: $(echo $token)" $NOTIFICATION_API_URL | python3 -m json.tool
  echo
}

echo '
   ________                                         __  _
  / ____/ /_  ____  ____  ________     ____  ____  / /_(_)___  ____
 / /   / __ \/ __ \/ __ \/ ___/ _ \   / __ \/ __ \/ __/ / __ \/ __ \
/ /___/ / / / /_/ / /_/ (__  )  __/  / /_/ / /_/ / /_/ / /_/ / / / /
\____/_/ /_/\____/\____/____/\___/   \____/ .___/\__/_/\____/_/ /_/
                                         /_/
'
echo "1. Get Cognito Access Token"
echo "2. Get Cognito Access Token and call API Gateway"
echo
read -p ">>> " user_choice
echo
case $user_choice in
1)
  token=$(get_access_token)
  echo "Cognito Access Token:"
  echo $token
  echo
  ;;
2)
  token=$(get_access_token)
  echo "Cognito Access Token:"
  echo $token
  call_api $token
  echo
  ;;
esac
