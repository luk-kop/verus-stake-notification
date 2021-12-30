#!/usr/bin/env bash

# Script can be used to fetch Cognito Access Token or to call API Gateway (with Access Token onboard)
# Get absolute paths
ENV_DIR="$(dirname "$(readlink -fm "$0")")"
ENV_FILE_PATH=${ENV_DIR}/.env-api

# Check whether $ENV_FILE_PATH exists
if [ ! -f "$ENV_FILE_PATH" ]; then
  echo
  echo "File ${ENV_FILE_PATH} not found!"
  echo
  exit 1
fi

# Load data from .env-api
# shellcheck disable=SC1090
source "$ENV_FILE_PATH"

# Declare dict for env variables from $ENV_FILE_PATH
declare -A env_var_dict
env_var_dict["NOTIFICATION_API_URL"]="$NOTIFICATION_API_URL"
env_var_dict["COGNITO_CLIENT_ID"]="$COGNITO_CLIENT_ID"
env_var_dict["COGNITO_CLIENT_SECRET"]="$COGNITO_CLIENT_SECRET"
env_var_dict["COGNITO_TOKEN_URL"]="$COGNITO_TOKEN_URL"
env_var_dict["COGNITO_CUSTOM_SCOPES"]="$COGNITO_CUSTOM_SCOPES"

# Check whether all necessary env variables are specified in $ENV_FILE_PATH file
for env_var in "${!env_var_dict[@]}"; do
  if [ -z "${env_var_dict[$env_var]}" ]; then
    echo
    echo "\"${env_var}\" variable is not specified in ${ENV_FILE_PATH} file!"
    echo
    exit 1
  fi
done

get_access_token() {
  # Declare local vars
  local cognito_api_response
  local client_data_base64
  local access_token
  # Base64 encode
  client_data_base64="$(echo -n "${COGNITO_CLIENT_ID}:${COGNITO_CLIENT_SECRET}" | openssl base64 -A)"
  cognito_api_response=$(curl --silent --request POST \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --header "Authorization: Basic ${client_data_base64}" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "scope=${COGNITO_CUSTOM_SCOPES}" \
    "$COGNITO_TOKEN_URL")
  # Check whether "access_token" key is in API response
  if [[ ! $cognito_api_response == *"access_token"* ]]; then
    return 1
  fi
  # access_token="$(echo $response | jq --raw-output '.access_token')"
  access_token="$(echo "$cognito_api_response" | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')"
  echo "$access_token"
#  return 0
}

call_api() {
  local token=$1
  local year_qp=$2
  local month_qp=$3
  echo
  echo "API Gateway response:"
  # API call with date query params
  curl --silent --get \
    --header "Authorization: ${token}" \
    --data year="${year_qp}" \
    --data month="${month_qp}" \
    "$NOTIFICATION_API_URL" | python3 -m json.tool
}

check_exit_code() {
  local status=$1
  if [[ $status != 0 ]]; then
    echo "Sorry, but something went wrong with retrieving the access token... :("
    echo
    exit 1
  fi
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
echo "2. Get Cognito Access Token and call API Gateway with GET method"
read -rp ">>> " user_choice
echo
case $user_choice in
1)
  token=$(get_access_token)
  check_exit_code $?
  echo
  echo "Cognito Access Token:"
  echo "$token"
  echo
  ;;
2)
  current_year=$(date +%Y)
  while true; do
    echo "Enter date in format YYYY-MM or YYYY [$current_year]"
    read -rp ">>> " input_date
    # Default option
    if [ -z "$input_date" ]; then
      input_date=$current_year
      break
    # Check whether input date is in desired format: YYYY or YYYY-MM
    # Allowed date range - year: 2000-2099, month: 01-12
    elif [[ $input_date =~ ^20[0-9]{2}-((0[1-9])|(1[0-2]))$ ]] || [[ $input_date =~ ^20[0-9]{2}$ ]]; then
      break
    fi
    echo "*** Error: Wrong date format - try again! ***"
    echo
  done
  # Create date array
  date_array=( $(echo "$input_date" | awk -F- '{ print $1,$2 }') )
  token=$(get_access_token)
  check_exit_code $?
  echo
  echo "Cognito Access Token:"
  echo "$token"
  call_api "$token" "${date_array[0]}" "${date_array[1]}"
  echo
  ;;
esac
