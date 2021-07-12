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

    def create_resource(self) -> None:
        """
        Creates Cognito user pool resource or
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

    def delete_resource(self):
        """
        Deletes Cognito user pool.
        """
        self._cognito_client.delete_user_pool(UserPoolId=self.id)
        print(f'The Cognito "{self.name}" user pool has been deleted')


class CognitoResourceServer:
    """
    Class represents Cognito resource server resource.
    """
    def __init__(self, name: str, identifier: str, user_pool_id: str) -> None:
        self.name = name
        self.id = identifier
        self.user_pool_id = user_pool_id
        self._scopes = []
        self._cognito_client = boto3.client('cognito-idp')

    def add_scope(self, name: str, description: str) -> None:
        """
        Adds scope to resource server.
        """
        scope = {
            'ScopeName': name,
            'ScopeDescription': description
        }
        self._scopes.append(scope)

    def create_resource(self) -> None:
        """
        Creates Cognito resource server resource.
        """
        if not self._check_exist():
            self._cognito_client.create_resource_server(
                UserPoolId=self.user_pool_id,
                Identifier=self.id,
                Name=self.name,
                Scopes=self._scopes
            )
            print(f'The Cognito resource server "{self.name}" created')
            return
        print(f'The Cognito resource server "{self.name}" exists. Using it.')

    def get_resource_server(self) -> Union[None, dict]:
        """
        Returns Cognito resource server if exist.
        """
        for server in self._resource_servers:
            if server['Name'] == self.name:
                return server

    def _check_exist(self) -> bool:
        """
        Check if resource with specified Identifier exist.
        """
        for server in self._resource_servers:
            if server['Identifier'] == self.id:
                return True
        return False

    @property
    def _resource_servers(self) -> list:
        """
        Returns list of already created Cognito resource servers for specific user pool.
        """
        return self._cognito_client.list_resource_servers(UserPoolId=self.user_pool_id,
                                                          MaxResults=50)['ResourceServers']

    def delete_resource(self) -> None:
        """
        Deletes Cognito resource server.
        """
        if self._check_exist():
            self._cognito_client.delete_resource_server(UserPoolId=self.user_pool_id,
                                                        Identifier=self.id)
            print(f'The Cognito resource server "{self.name}" has been deleted')
            return
        print(f'The Cognito resource server "{self.name}" does not exist')


if __name__ == '__main__':
    pool = CognitoUserPool(name='TestPool')
    pool.create_resource()
    resource_srv = CognitoResourceServer(name='verus-api-resource-server',
                                         identifier='verus-api',
                                         user_pool_id=pool.id)
    resource_srv.add_scope(name='api-read',
                           description='Read access to the API')
    resource_srv.create_resource()
    resource_srv.delete_resource()
    pool.delete_resource()
