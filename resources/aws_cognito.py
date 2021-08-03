from typing import List, Dict

import boto3


class CognitoUserPool:
    """
    Class represents Cognito user pool resource.
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self._cognito_client = boto3.client('cognito-idp')

    def create_resource(self) -> None:
        """
        Creates Cognito user pool resource in AWS cloud.
        """
        if not self._check_exist():
            self._cognito_client.create_user_pool(
                PoolName=self.name,
                AdminCreateUserConfig={
                    'AllowAdminCreateUserOnly': True
                },
                UserPoolTags={
                    'Project': 'verus-notification'
                }
            )
            print(f'The Cognito "{self.name}" user pool created.')
            return
        print(f'The Cognito "{self.name}" user pool exists. Using it.')

    @property
    def id(self) -> str:
        """
        Returns user pool id.
        """
        for pool in self._user_pools:
            if pool['Name'] == self.name:
                return pool['Id']
        return ''

    @property
    def arn(self) -> str:
        """
        Returns Cognito user pool ARN.
        """
        pool_id = self.id
        if pool_id:
            try:
                return self._cognito_client.describe_user_pool(UserPoolId=pool_id)['UserPool']['Arn']
            except AttributeError:
                pass
        return ''

    def _check_exist(self) -> bool:
        """
        Checks if Cognito user pool resource with specified name already exist.
        """
        return True if self.id else False

    @property
    def _user_pools(self) -> list:
        """
        Returns list of already created Cognito user pools.
        """
        return self._cognito_client.list_user_pools(MaxResults=60)['UserPools']

    @property
    def domain(self) -> str:
        """
        Domain for Cognito user pool.
        Domain will be assigned to user pool resource with CognitoUserPoolDomain class instance.
        """
        try:
            return self._cognito_client.describe_user_pool(UserPoolId=self.id)['UserPool']['Domain']
        except KeyError:
            return ''

    @property
    def resource_servers(self) -> list:
        """
        Returns list of resource_servers associated with Cognito user pools.
        """
        try:
            return self._cognito_client.list_resource_servers(UserPoolId=self.id,
                                                              MaxResults=50)['ResourceServers']
        except self._cognito_client.exceptions.ResourceNotFoundException:
            return []

    def delete_resource(self) -> None:
        """
        Deletes Cognito user pool in AWS cloud.
        """
        if self._check_exist():
            try:
                self._cognito_client.delete_user_pool(UserPoolId=self.id)
                print(f'The Cognito user pool "{self.name}" has been deleted')
            except self._cognito_client.exceptions.InvalidParameterException as err:
                print(err.response['Error']['Message'])
            return
        print(f'The Cognito user pool "{self.name}" does not exist')


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

    @property
    def scope_identifiers(self) -> list:
        """
        Returns list of scope identifiers in format 'identifier/scope_name'.
        """
        return [f'{self.id}/{scope["ScopeName"]}'for scope in self._scopes]

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
        try:
            return self._cognito_client.list_resource_servers(UserPoolId=self.user_pool_id,
                                                              MaxResults=50)['ResourceServers']
        except self._cognito_client.exceptions.ResourceNotFoundException:
            return []

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


class CognitoUserPoolClient:
    """
    Class represents domain for Cognito user pool client.
    """
    def __init__(self, name: str, user_pool_id: str, scopes: list) -> None:
        self.name = name
        self.user_pool_id = user_pool_id
        self.scopes = scopes
        self._cognito_client = boto3.client('cognito-idp')

    def create_resource(self) -> None:
        """
        Creates Cognito user pool client resource in AWS cloud.
        """
        if not self._check_exist():
            self._cognito_client.create_user_pool_client(
                ClientName=self.name,
                UserPoolId=self.user_pool_id,
                GenerateSecret=True,
                AllowedOAuthFlows=['client_credentials'],
                AllowedOAuthScopes=self.scopes
            )
            print(f'The Cognito user pool client "{self.name}" created')
            return
        print(f'The Cognito user pool client "{self.name}" exists. Using it.')

    @property
    def _user_pool_clients(self) -> list:
        """
        Returns list of already created Cognito user pool clients.
        """
        try:
            return self._cognito_client.list_user_pool_clients(MaxResults=60,
                                                               UserPoolId=self.user_pool_id)['UserPoolClients']
        except self._cognito_client.exceptions.ResourceNotFoundException:
            return []

    @property
    def id(self) -> str:
        """
        Returns user pool client id.
        """
        for client in self._user_pool_clients:
            if client['ClientName'] == self.name:
                return client['ClientId']
        return ''

    @property
    def secret(self) -> str:
        """
        Returns user pool client secret.
        """
        if self._check_exist():
            user_pool_client = self._cognito_client.describe_user_pool_client(UserPoolId=self.user_pool_id,
                                                                              ClientId=self.id)
            return user_pool_client['UserPoolClient']['ClientSecret']
        else:
            return ''

    def _check_exist(self) -> bool:
        """
        Checks if Cognito user pool client resource with specified name already exist.
        Assign 'id' attribute if user pool client exist.
        """
        result = True if self.id else False
        return result

    def delete_resource(self) -> None:
        """
        Deletes Cognito user pool client in AWS cloud.
        """
        if self._check_exist():
            self._cognito_client.delete_user_pool_client(UserPoolId=self.user_pool_id,
                                                         ClientId=self.id)
            print(f'The Cognito user pool client "{self.name}" has been deleted')
            return
        print(f'The Cognito user pool client "{self.name}" does not exist')


class CognitoResources:
    """
    Class represents all Cognito related resources used in verus-notification project.
    During object initialization, new AWS resources are created or existing resources are used.
    """
    def __init__(self, user_pool_name: str, resource_server_scopes: List[Dict], pool_domain: str,
                 name_prefix: str) -> None:
        self.name_prefix = name_prefix
        self.scopes = resource_server_scopes
        self.pool_domain = pool_domain
        # Cognito user pool instantiation
        self.user_pool = CognitoUserPool(name=user_pool_name)
        self.user_pool.create_resource()
        # Cognito resource server instantiation
        self.resource_server = CognitoResourceServer(name=f'{self.name_prefix}-resource-server',
                                                     identifier=f'{self.name_prefix}-id',
                                                     user_pool_id=self.user_pool.id)
        for scope in resource_server_scopes:
            self.resource_server.add_scope(name=scope['name'], description=scope['description'])
        self.resource_server.create_resource()
        # Cognito user pool domain instantiation
        self.domain = CognitoUserPoolDomain(domain_prefix=self.pool_domain, user_pool_id=self.user_pool.id)
        self.domain.create_resource()
        # Cognito user pool client instantiation
        self.user_pool_client = CognitoUserPoolClient(name='verus-cli-wallet',
                                                      user_pool_id=self.user_pool.id,
                                                      scopes=self.resource_server.scope_identifiers)
        self.user_pool_client.create_resource()

    def create(self) -> None:
        """
        Creates all Cognito related resources. Method can be used to recreate Cognito resources after deletion.
        """
        self.user_pool.create_resource()
        self.update_user_pool_id()
        self.resource_server.create_resource()
        self.domain.create_resource()
        self.user_pool_client.create_resource()

    def delete(self) -> None:
        """
        Deletes all Cognito related resources.
        """
        self.user_pool_client.delete_resource()
        self.domain.delete_resource()
        self.resource_server.delete_resource()
        self.user_pool.delete_resource()

    def update_user_pool_id(self) -> None:
        """
        Updates user pool id.
        """
        new_id = self.user_pool.id
        self.resource_server.user_pool_id = new_id
        self.domain.user_pool_id = new_id
        self.user_pool_client.user_pool_id = new_id

    @property
    def client_credentials(self) -> dict:
        """
        Returns Cognito User Pool Client credentials (Client ID & Client SECRET).
        """
        return {
            'client_id': self.user_pool_client.id,
            'client_secret': self.user_pool_client.secret
        }

    @property
    def token_url(self) -> str:
        """
        Returns Cognito token URL.
        """
        if self.user_pool.id:
            region = boto3.client('cognito-idp').meta.region_name
            return f'https://{self.domain.domain}.auth.{region}.amazoncognito.com/oauth2/token'
        return ''


def main() -> None:
    """
    Main function - example of use CognitoResources class
    """
    scopes = [
        {
            'name': 'api-read',
            'description': 'Read access to the API'
         }
    ]
    resources = CognitoResources(user_pool_name='TestVerusPool',
                                 resource_server_scopes=scopes,
                                 pool_domain='verus-test-12345',
                                 name_prefix='verus-api')
    print(resources.client_credentials)
    print(resources.token_url)
    resources.delete()


if __name__ == '__main__':
    main()


