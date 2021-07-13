import boto3


class CognitoUserPool:
    """
    Class represents Cognito user pool resource.
    """
    def __init__(self, name: str):
        self.name = name
        self._cognito_client = boto3.client('cognito-idp')
        if self._check_exist():
            self.arn = self.get_arn()
        else:
            self.arn, self.id = None, None

    def create_resource(self) -> None:
        """
        Creates Cognito user pool resource in AWS cloud.
        """
        if not self._check_exist():
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

    def _check_exist(self) -> bool:
        """
        Checks if Cognito user pool resource with specified name already exist.
        Assign 'id' attribute if pool exist.
        """
        for pool in self._user_pools:
            if pool['Name'] == self.name:
                self.id = pool['Id']
                return True
        return False

    @property
    def _user_pools(self) -> list:
        """
        Returns list of already created Cognito user pools.
        """
        return self._cognito_client.list_user_pools(MaxResults=60)['UserPools']

    def get_arn(self):
        """
        Returns Cognito user pool ARN.
        """
        return self._cognito_client.describe_user_pool(UserPoolId=self.id)['UserPool']['Arn']

    def delete_resource(self):
        """
        Deletes Cognito user pool in AWS cloud.
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
        Creates Cognito resource server resource in AWS cloud.
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
        Deletes Cognito resource server in AWS cloud.
        """
        if self._check_exist():
            self._cognito_client.delete_resource_server(UserPoolId=self.user_pool_id,
                                                        Identifier=self.id)
            print(f'The Cognito resource server "{self.name}" has been deleted')
            return
        print(f'The Cognito resource server "{self.name}" does not exist')


class CognitoUserPoolDomain:
    """
    Class represents domain for Cognito user pool.
    """
    def __init__(self, domain_prefix: str, user_pool_id: str) -> None:
        self.domain = domain_prefix
        self.user_pool_id = user_pool_id
        self._cognito_client = boto3.client('cognito-idp')

    def create_resource(self) -> None:
        """
        Creates Cognito user pool domain resource in AWS cloud.
        """
        try:
            self._cognito_client.create_user_pool_domain(
                Domain=self.domain,
                UserPoolId=self.user_pool_id,
            )
            print(f'The Cognito user pool domain "{self.domain}" created')
        except self._cognito_client.exceptions.InvalidParameterException as err:
            print(err.response['Error']['Message'])

    def delete_resource(self) -> None:
        """
        Deletes Cognito user pool domain in AWS cloud.
        """
        try:
            self._cognito_client.delete_user_pool_domain(UserPoolId=self.user_pool_id,
                                                         Domain=self.domain)
            print(f'The Cognito user pool domain "{self.domain}" has been deleted')
        except self._cognito_client.exceptions.InvalidParameterException as err:
            print(err.response['Error']['Message'])


if __name__ == '__main__':
    pool = CognitoUserPool(name='TestPool')
    pool.create_resource()
    resource_srv = CognitoResourceServer(name='verus-api-resource-server',
                                         identifier='verus-api',
                                         user_pool_id=pool.id)
    resource_srv.add_scope(name='api-read',
                           description='Read access to the API')
    resource_srv.create_resource()

    domain = CognitoUserPoolDomain(domain_prefix='verus-test123', user_pool_id=pool.id)
    domain.create_resource()

    domain.delete_resource()
    resource_srv.delete_resource()
    pool.delete_resource()
