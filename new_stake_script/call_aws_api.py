import uuid
from datetime import datetime, timezone
import time
import argparse
import re

from check_new_stake import ApiGatewayCognito


class ApiCall:
    """
    The class representing call to AWS API Gateway dedicated to the verus-notification project.
    """

    def __init__(self) -> None:
        self.api = ApiGatewayCognito(cli_logging=True)

    def post_data(self, vrsc_amount: float) -> dict:
        """
        POST data to AWS resources.
        """
        # 'txid' - random generated UUID
        # 'time' - current poch (Unix time) timestamp
        data = {
            "txid": uuid.uuid4().hex,
            "time": int(datetime.now(timezone.utc).timestamp()),
            "amount": vrsc_amount,
        }
        # API POST call
        response = self.api.call(method="post", data=data)
        # Add fake 1 sec time delay
        time.sleep(0.5)
        return response

    def get_data(self, date: dict) -> dict:
        """
        Get data for a selected time period from AWS resources.
        """
        # For current year & month use 'data = {}'
        response = self.api.call(method="get", data=date)
        return response


def validate_date(date: str) -> dict:
    """
    Validate provided date data.
    Desired format: YYYY or YYYY-MM (2021 or 2021-12).
    """
    # regex patters
    rp_year_month = re.compile("^(20[0-9]{2})-((0[1-9])|(1[0-2]))$")
    rp_year = re.compile("^(20[0-9]{2})$")
    # Match year-month object
    mo = rp_year_month.match(date)
    if mo:
        return {"year": mo.groups()[0], "month": mo.groups()[1]}
    # Match year object
    mo = rp_year.match(date)
    if mo:
        return {"year": mo.groups()[0]}
    return {}


if __name__ == "__main__":
    # Date in format 2021-12
    date_current = datetime.now(timezone.utc).strftime("%Y-%m")
    # Create parent parser
    parser_parent = argparse.ArgumentParser(
        description="The verus-notification API Gateway calling script"
    )
    # Add subparsers
    subparsers = parser_parent.add_subparsers(title="Valid HTTP methods", dest="method")
    # Create parser for 'get' method (command 'call_aws_api.py get')
    parser_get = subparsers.add_parser(
        name="get", help="get value of VRSC stakes in selected time period"
    )
    parser_get.add_argument(
        "-d",
        "--date",
        type=str,
        default=f"{date_current}",
        help=f"year or month of year (default: {date_current})",
    )
    # Create parser for 'post' method (command 'call_aws_api.py post')
    parser_post = subparsers.add_parser(
        name="post", help="post new VRSC stake with specified value"
    )
    parser_post.add_argument(
        "-v", "--value", type=float, default=12.0, help="stake value (default: 12.0)"
    )
    # Parse arguments
    args = parser_parent.parse_args()
    if args.method == "get":
        date_argument = args.date
        post_validation_date = validate_date(date=date_argument)
        if post_validation_date:
            api_response = ApiCall().get_data(date=post_validation_date)
            print(api_response)
        else:
            parser_get.error("argument -d/--date: wrong format - use: YYYY or YYYY-MM")
    elif args.method == "post":
        value_argument = args.value
        api_response = ApiCall().post_data(vrsc_amount=value_argument)
        print(api_response)
    else:
        # if no method is given, print help
        parser_parent.print_help()
        print('\n"post" method ', end="")
        parser_get.print_help()
        print('\n"get" method ', end="")
        parser_post.print_help()
