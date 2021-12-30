import uuid
from datetime import datetime
import time
import argparse
import re

from check_new_stake import ApiGatewayCognito


class ApiCall:
    """
    The class representing call to AWS API Gateway dedicated to the verus-notification project.
    """

    def __init__(self):
        self.api = ApiGatewayCognito(cli_logging=True)

    def post_data(self, vrsc_amount: float):
        """
        POST data to AWS resources.
        """
        # 'txid' - random generated UUID
        # 'time' - current poch (Unix time) timestamp
        data = {
            'txid': uuid.uuid4().hex,
            'time': int(datetime.utcnow().timestamp()),
            'amount': vrsc_amount
        }
        # API POST call
        self.api.call(method='post', data=data)
        # Add fake 1 sec time delay
        time.sleep(1)

    def get_data(self, date: dict):
        """
        Get data for a selected time period from AWS resources.
        """
        # For current year & month use 'data = {}'
        self.api.call(method='get', data=date)


def validate_date(date: str) -> dict:
    """
    Validate provided date data.
    Desired format: YYYY or YYYY-MM (2021 or 2021-12).
    """
    # regex patters
    rp_year_month = re.compile('^(20[0-9]{2})-((0[1-9])|(1[0-2]))$')
    rp_year = re.compile('^(20[0-9]{2})$')
    # Match year-month object
    mo = rp_year_month.match(date)
    if mo:
        return {
            'year': mo.groups()[0],
            'month': mo.groups()[1]
        }
    # Match year object
    mo = rp_year.match(date)
    if mo:
        return {
            'year': mo.groups()[0]
        }
    return {}


if __name__ == '__main__':
    # Date in format 2021-12
    date_current = datetime.utcnow().strftime('%Y-%m')
    # Create parent parser
    parser_parent = argparse.ArgumentParser(description='The verus-notification API Gateway calling script')
    # Add subparsers
    subparsers = parser_parent.add_subparsers(title='Valid HTTP methods', dest='method')
    # Create parser for 'get' method (command 'call_aws_api.py get')
    parser_get = subparsers.add_parser(name='get',
                                       help=f'get value of VRSC stakes in selected time period')
    parser_get.add_argument('-d',
                            '--date',
                            type=str,
                            default=f'{date_current}',
                            help=f'year or month of year (default: {date_current})')
    # Create parser for 'post' method (command 'call_aws_api.py post')
    parser_post = subparsers.add_parser(name='post', help='post new VRSC stake with specified value')
    parser_post.add_argument('-v',
                             '--value',
                             type=float,
                             default=12.0,
                             help='stake value (default: 12.0)')
    # Parse arguments
    args = parser_parent.parse_args()
    if args.method == 'get':
        date_argument = args.date
        post_validation_date = validate_date(date=date_argument)
        if post_validation_date:
            ApiCall().get_data(date=post_validation_date)
        else:
            parser_get.error('argument -d/--date: wrong format - use: YYYY or YYYY-MM')
    elif args.method == 'post':
        value_argument = args.value
        ApiCall().post_data(vrsc_amount=value_argument)
    else:
        # if no method is given, print help
        parser_parent.print_help()
        print('\n"post" method ', end='')
        parser_get.print_help()
        print('\n"get" method ', end='')
        parser_post.print_help()
