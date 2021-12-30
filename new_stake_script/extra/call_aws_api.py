import uuid
from datetime import datetime
import time

from new_stake_script.check_new_stake import ApiGatewayCognito


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

    def get_data(self, year: str = '', month: str = ''):
        """
        Get data for a selected time period from AWS resources.
        """
        data = {}
        if year:
            data['year'] = year
        if month:
            data['month'] = year
        # For current year & month use 'data = {}'
        self.api.call(method='get', data=data)


if __name__ == '__main__':
    ApiCall().post_data(vrsc_amount=11)