import boto3
from typing import List, Union
from dataclasses import dataclass

from resources.aws_policy_document import PolicyStatement, PolicyDocumentCustom
from resources.aws_cognito import CognitoUserPool, CognitoResources


class ApiGateway:
    """
    Class represents API Gateway resource. If a API Gateway with the specified name already exists, it is used.
    The API Gateway is publicly accessible and invokes Lambda function.
    """
    def __init__(self, name: str, lambda_arn: str):
        self.name = name
        self.lambda_arn = lambda_arn
        self.id = None
        self.source_arn = None
        self.url = None
        self.api_endpoint = 'stake'
        self._api_client = boto3.client('apigateway')
        self._account_id = boto3.client('sts').get_caller_identity()['Account']
        self.create_api()

    def create_api(self) -> None:
        """
        Creates API Gateway resource. Method is called whenever a new instance of ApiGateway is created.
        Method can also be used to recreate API Gateway resource after deleting it with 'delete_api' method.
        """
        if not self.check_api_exist():
            resource_policy = self.create_policy()

            api = self._api_client.create_rest_api(
                name=self.name,
                description='Invoke Lambda function to publish a msg to SNS topic when new stake appears in Verus wallet.',
                apiKeySource='HEADER',
                endpointConfiguration={
                    'types': ['REGIONAL'],
                },
                policy=resource_policy,
                tags={
                    'Project': 'verus-notification'
                },
            )
            self.id = api['id']
            # Create resource 'stake'
            # Get parent id - root resource (path '/')
            root_id = self.get_root_resource_id()
            resource = self._api_client.create_resource(
                restApiId=self.id,
                parentId=root_id,
                pathPart=self.api_endpoint
            )
            resource_id = resource['id']
            # Put method to resource
            self._api_client.put_method(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                authorizationType='NONE'
            )
            # Put method response
            self._api_client.put_method_response(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                statusCode='200',
            )
            # Put method integration
            lambda_uri = f'arn:aws:apigateway:{self._api_client.meta.region_name}:' \
                         f'lambda:path/2015-03-31/functions/{self.lambda_arn}/invocations'
            # NOTE: For Lambda integrations, you must use the HTTP method of POST for the integration request
            # (integrationHttpMethod) or this will not work
            self._api_client.put_integration(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                type='AWS',
                integrationHttpMethod='POST',
                uri=lambda_uri,
                connectionType='INTERNET',
            )
            # Put method integration response
            self._api_client.put_integration_response(
                restApiId=self.id,
                resourceId=resource_id,
                httpMethod='GET',
                statusCode='200',
                selectionPattern='',
                contentHandling='CONVERT_TO_TEXT'
            )
            self.source_arn = f'arn:aws:execute-api:{self._api_client.meta.region_name}:' \
                              f'{self._account_id}:{self.id}/*/GET/{self.api_endpoint}'
            # Create deployment
            self._api_client.create_deployment(
                restApiId=self.id,
                stageName='vrsc'
            )
            # Create API URL
            self.url = f'https://{self.id}.execute-api.{self._api_client.meta.region_name}.amazonaws.com' \
                       f'/vrsc/{self.api_endpoint}'
            print(f'API Gateway {self.name} created')

    def check_api_exist(self) -> bool:
        """
        Checks whether a API with the given name already exists.
        If API already exists - assign existed API id to 'id' attribute.
        """
        apis_list = self._api_client.get_rest_apis()['items']
        for api in apis_list:
            if api['name'] == self.name:
                print(f'API Gateway {self.name} exist. Using it.')
                self.id = api['id']
                self.url = f'https://{self.id}.execute-api.{self._api_client.meta.region_name}.' \
                           f'amazonaws.com/vrsc/{self.api_endpoint}'
                self.source_arn = f'arn:aws:execute-api:{self._api_client.meta.region_name}:' \
                                  f'{self._account_id}:{self.id}/*/GET/{self.api_endpoint}'
                return True
        return False

    @property
    def authorizers(self) -> list:
        """
        Returns list of already created API Gateway Authorizers.
        """
        try:
            return self._api_client.get_authorizers(limit=50,
                                                    restApiId=self.id)['items']
        except self._api_client.exceptions.NotFoundException:
            return []

    def put_method(self, method: dict, method_response: bool = True) -> None:
        """
        Add method to existing resource.
        """
        # Put method to resource
        self._api_client.put_method(**method)
        if method_response:
            # Remove unnecessary keys
            allowed_keys = ['restApiId', 'resourceId', 'httpMethod']
            for key in method.keys():
                if key not in allowed_keys:
                    del method[key]
            method['statusCode'] = '200'
            # Put method response
            self._api_client.put_method_response(**method)

    def get_root_resource_id(self) -> str:
        """
        Returns parent id (root resource - path '/').
        """
        resources = self._api_client.get_resources(restApiId=self.id)
        resource_items = resources['items']
        for item in resource_items:
            if item['path'] == '/':
                # return root resource id
                return item['id']

    def create_policy(self):
        """
        Creates resource-based policy for API Gateway endpoint
        """
        policy = PolicyDocumentCustom()
        policy_statement = PolicyStatement(effect='Allow',
                                           actions='execute-api:Invoke',
                                           resources='execute-api:/*',
                                           principals='*')
        policy_statement.add_condition(condition_operator='IpAddress',
                                       condition_key='aws:SourceIp',
                                       condition_value=['0.0.0.0/0'])
        policy.add_statement(policy_statement)
        return policy.get_json()

    def delete_authorizers(self):
        """
        Deletes all API Gateway Authorizer resources associated with API.
        """
        for auth in self.authorizers:
            auth.delete_resource()

    def delete_api(self):
        """
        Deletes API Gateway.
        """
        self.delete_authorizers()
        self._api_client.delete_rest_api(restApiId=self.id)
        print(f'The API Gateway {self.name} has been deleted')


class ApiGatewayAuthorizer:
    """
    Class represents API Gateway Authorizer resource.
    """
    def __init__(self, name: str, api_id: str, providers: List[CognitoUserPool], auth_type: str) -> None:
        self.api_id = api_id
        self.name = name
        self.providers = providers
        self.auth_type = auth_type
        self._auth_client = boto3.client('apigateway')

    def create_resource(self) -> None:
        """
        Creates API Gateway Authorizer resource in AWS cloud.
        """
        if not self._check_exist():
            self._auth_client.create_authorizer(
                restApiId=self.api_id,
                name=self.name,
                type=self.auth_type,
                providerARNs=[provider.arn for provider in self.providers],
                identitySource='method.request.header.Authorization',
            )
            print(f'The API Gateway Authorizer "{self.name}" created')
            return
        print(f'The API Gateway Authorizer "{self.name}" exists. Using it.')

    @property
    def auth_type(self) -> str:
        """
        Returns auth_type attribute
        """
        return self._auth_type

    @auth_type.setter
    def auth_type(self, new_type) -> str:
        """
        Sets auth_type attribute and makes simple input validation.
        """
        allowed_types = ['TOKEN', 'REQUEST', 'COGNITO_USER_POOLS']
        if new_type not in allowed_types:
            raise AttributeError(f'Wrong auth_type value. The allowed auth_type values: {", ".join(allowed_types)}')
        self._auth_type = new_type

    @property
    def id(self) -> str:
        """
        Returns API Gateway Authorizer id.
        """
        for auth in self._authorizers:
            if auth['name'] == self.name:
                return auth['id']
        return ''

    @property
    def _authorizers(self) -> list:
        """
        Returns list of already created API Gateway Authorizers.
        """
        try:
            return self._auth_client.get_authorizers(limit=50,
                                                     restApiId=self.api_id)['items']
        except self._auth_client.exceptions.NotFoundException:
            return []

    def _check_exist(self) -> bool:
        """
        Checks if API Gateway Authorizer resource with specified name already exist.
        Assign 'id' attribute if user pool client exist.
        """
        result = True if self.id else False
        return result

    def delete_resource(self) -> None:
        """
        Deletes API Gateway Authorizer in AWS cloud.
        """
        if self._check_exist():
            self._auth_client.delete_authorizer(restApiId=self.api_id,
                                                authorizerId=self.id)
            print(f'The API Gateway Authorizer "{self.name}" has been deleted')
            return
        print(f'The API Gateway Authorizer "{self.name}" does not exist')


@dataclass
class ApiMethod:
    """
    Class represents API Gateway HTTP method.
    """
    http_method: str
    api_id: str
    resource_id: str
    authorizer: Union[None, ApiGatewayAuthorizer] = None

    @property
    def data(self) -> dict:
        """
        Returns properly prepared HTTP method statement for boto3 usage.
        """
        method_data = {
            'restApiId': self.api_id,
            'resourceId': self.resource_id,
            'httpMethod': self.http_method
        }
        if self.authorizer:
            method_data['authorizationType'] = self.authorizer.auth_type
            method_data['authorizerId'] = self.authorizer.id
            # TODO: change below!!!
            resource_srv = self.authorizer.providers[0].resource_servers[0]
            resource_srv_scopes = resource_srv['Scopes']
            resource_srv_identifier = resource_srv['Identifier']
            method_data['authorizationScopes'] = [f'{resource_srv_identifier}/{scope["ScopeName"]}'for scope in resource_srv_scopes]
        else:
            method_data['authorizationType'] = 'NONE'
        return method_data


class ApiResources:
    """
    Class represents all API Gateway related resources used in verus-notification project.
    """
    def __init__(self, api_name: str, lambda_arn: str, user_pool: Union[CognitoUserPool, None] = None):
        self.api_name = api_name
        self.lambda_arn = lambda_arn
        self.api = ApiGateway(name=api_name, lambda_arn=lambda_arn)
        if user_pool:
            self.authorizer = ApiGatewayAuthorizer(name='VerusApiAuthBoto3',
                                                   api_id=self.api.id,
                                                   providers=[user_pool],
                                                   auth_type='COGNITO_USER_POOLS')

    def create(self):
        pass

    def delete(self):
        pass


def main() -> None:
    """
    Main function - example of use
    """
    # Add existed Lambda ARN
    lambda_arn = 'arn:aws:lambda:eu-west-1:390700395495:function:my-function'

    scopes = [
        {
            'name': 'api-read',
            'description': 'Read access to the API'
        }
    ]
    cognito_resources = CognitoResources(user_pool_name='UserPool4Tests',
                                         resource_server_scopes=scopes,
                                         pool_domain='verus-test-12345',
                                         name_prefix='verus-api')

    api = ApiGateway(name='ApiGateway4Tests', lambda_arn=lambda_arn)
    authorizer = ApiGatewayAuthorizer(name='Authorizer4Tests',
                                      api_id=api.id,
                                      providers=[cognito_resources.user_pool],
                                      auth_type='COGNITO_USER_POOLS')
    authorizer.create_resource()

    # Delete resources
    authorizer.delete_resource()
    api.delete_api()
    cognito_resources.delete()
    # method = ApiMethod(http_method='GET', api_id=api.id, resource_id='12345', authorizer=authorizer)
    # print(method.data)


if __name__ == '__main__':
    main()