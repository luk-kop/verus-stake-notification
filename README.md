# Verus stake notification

[![Python 3.8.5](https://img.shields.io/badge/python-3.8.5-blue.svg)](https://www.python.org/downloads/release/python-377/)
[![Boto3](https://img.shields.io/badge/Boto3-1.17.78-blue.svg)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
[![Terraform](https://img.shields.io/badge/Terraform-0.14.9-blueviolet.svg)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

> The **Verus stake notification** is an application that monitors the state of your **Verus Coin (VRSC)** cryptocurrency wallet.
> If you "win the" block, the application will inform you of a staking reward (new stake) that have appeared in your Verus CLI wallet.

## Features
* The `aws_environment.py` script allows you to build or destroy dedicated environment in the AWS Cloud. The AWS resources created will send an email to a selected address if there is a new stake in the wallet.
* The AWS resources are deployed with AWS SDK for Python (Boto3).  
* The `check_new_stake.py` can be run at regular intervals on the machine running the Verus wallet (with cronjob or systemd timer). If a new stake arrives, the script calls the API Gateway in AWS Cloud.
* Orphan stakes and new transactions (transferring cryptocurrency from/to wallet) are not counted.
* The email address to be notified of a new stake is stored in `.env` file (`EMAIL_TO_NOTIFY`).
* The new stake is also added to the Amazon DynamoDB table (with timestamp and stake value).  
* Access to the API Gateway can be limited to a selected ip address (Verus wallet public ip address):
  - To limit access to specific public ip address - set `WALLET_PUBLIC_IP='your-public-ip-address'` in `.env` file;
  - To leave the API Gateway open to the public - set `WALLET_PUBLIC_IP=''` in `.env` file.
* The API Gateway URL is added to `.env` file during AWS environment build (`NOTIFICATION_API_URL`). This URL is called up by the `check_new_stake.py` script when it detects a new stake.

## Project architecture
![Project architecture](./images/project_architecture.jpg)

## Getting Started

Below instructions will get you a copy of the project running on your local machine.

### Requirements
Python third party packages:
* [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
* [python-dotenv](https://pypi.org/project/python-dotenv/)
* [pytest](https://docs.pytest.org/en/6.2.x/)
* [psutil](https://pypi.org/project/psutil/)

Other prerequisites:
* The **Verus Coin (VRSC) CLI wallet** running on some Linux distribution. You can find appropriate wallet binaries on Verus Coin (VRSC) project website - [Verus wallet](https://verus.io/wallet/command-wallet).
* The AWS account.  
* Before using scripts, you need to set up authentication credentials for your AWS account (with programmatic access) using either the IAM Management Console or the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-linux.html) tool.
* The [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) tool must be installed for deploy AWS resources using it (optional).
* The `virtualenv` package already installed on the OS level.

## Build and run the application
The project creation process should be divided into two phases:
1. Deployment of the AWS resources (infrastructure) with `boto3` package or `Terraform` tool.
2. Setup script for monitoring the Verus wallet.

In both phases we will use the `virtualenv` tool to build the application.

1. Clone git repository to user home directory and enter `verus-stake-notification` directory.
   ```bash
   git clone https://github.com/luk-kop/verus-stake-notification.git
   cd verus-stake-notification/
   ```

2. Run following commands in order to create virtual environment and install the required packages.
    ```bash
    $ virtualenv venv
    # or 
    $ python3 -m venv venv
    $ source venv/bin/activate
    (venv) $ pip install -r requirements.txt
    ```

3. Before running the application you should create `.env` file in the root application directory (`verus-stake-notification`).
   The best solution is to copy the existing example file `.env-example` and edit the necessary data.
    ```bash
    (venv) $ cp .env-example .env
    ```
   
4. Build the AWS resources. You can choose one of two options:
   * Deployment with `boto3` package:
      ```bash
      (venv) $ python boto3_resources.py build
      ```
     >**Note:** I realize that using `boto3` to build the AWS infrastructure can be tricky and there are dedicated tools for this, but I did it for self-education purposes.
   
   * Deployment with `Terraform` tool:
      ```bash
      (venv) $ python terraform_resources.py build
      # For more options use:
      (venv) $ python terraform_resources.py -h
      ```
   
5. Once the AWS resources are properly deployed, you should add a cronjob on the host with the Verus wallet running to check the status of the wallet every 20 minutes.
   ```bash
    (venv) $ crontab -e
    ```
   Add below line to `crontab` (please change your username accordingly):
   ```bash
   */20 * * * * /home/user/verus-stake-notification/venv/bin/python /home/user/verus-stake-notification/check_new_stake.py
   ```

6. To remove all project's AWS resources use below command.
   * Deployment with `boto3` package:
      ```bash
      (venv) $ python aws_environment.py destroy
      ```
   * Deployment with `Terraform` tool:
      ```bash
      (venv) $ python terraform_resources.py destroy
      ```