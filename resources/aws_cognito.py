from typing import Union

import boto3


class CognitoUserPool:
    """
    Class represents Cognito user pool resource.
    """
    def __init__(self, name: str):
        self.name = name
        self.arn = None
        self.id = None
        self._cognito_client = boto3.client('cognito-idp')
        self.create_user_pool()

    def create_user_pool(self) -> None:
        """
        Creates Cognito user pool resource. Method is called whenever a new instance of Cognito user pool is created.
        Method creates a new user pool or assigns an ARN value to 'arn' attribute if one already exists.
        """
        user_pool = self.get_user_pool()
        if not user_pool:
            cognito_user_pool = self._cognito_client.create_user_pool(
                PoolName=self.name,
                AdminCreateUserConfig={
                    'AllowAdminCreateUserOnly': True
                },
            )
            self.arn = cognito_user_pool['UserPool']['Arn']
            self.id = cognito_user_pool['UserPool']['Id']
            print(f'The Cognito "{self.name}" user pool created')
            return
        print(f'The Cognito "{self.name}" user pool exists. Using it.')
        self.id = user_pool['Id']
        self.arn = self.get_arn()

    def get_user_pool(self) -> Union[None, dict]:
        """
        Returns Cognito user pool if exist.
        """
        user_pools_list = self._cognito_client.list_user_pools(MaxResults=60)['UserPools']
        for pool in user_pools_list:
            if pool['Name'] == self.name:
                return pool

    def get_arn(self):
        """
        Returns Cognito user pool ARN.
        """
        return self._cognito_client.describe_user_pool(UserPoolId=self.id)['UserPool']['Arn']

    def delete_user_pool(self):
        """
        Deletes Cognito user pool.
        """
        self._cognito_client.delete_user_pool(UserPoolId=self.id)
        print(f'The Cognito "{self.name}" user pool has been deleted')


if __name__ == '__main__':
    pool = CognitoUserPool(name='TestPool')
    pool.delete_user_pool()