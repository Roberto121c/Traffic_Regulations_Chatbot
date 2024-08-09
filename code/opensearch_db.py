import boto3
import json
from botocore.exceptions import ClientError
import time 

from constants import DOMAIN_NAME, IAM_USER, AWS_ACCOUNT, ADMIN_USER, ADMIN_PASSWORD, AWS_REGION

client = boto3.client('opensearch', region_name=AWS_REGION)

domain_name = DOMAIN_NAME

# Verify id domain exists
def domain_exists(domain_name):
    try:
        response = client.describe_domain(DomainName=domain_name)
        return True, response['DomainStatus']['Endpoint']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False, None
        else:
            raise e

exists, endpoint = domain_exists(domain_name)

if exists:
    print(f"El dominio ya existe. El endpoint es: {endpoint}")
else:
    # Defining an access policy to allow only my user to access 
    access_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": IAM_USER
                },
                "Action": "es:*",
                "Resource": f"arn:aws:es:us-east-1:{AWS_ACCOUNT}:domain/{domain_name}/*"
            }
        ]
    }

    # We need the policy as Json
    access_policy_json = json.dumps(access_policy)

    # Creating the domain with granular access
    # Test, sometimes granular access is not required and can interfere with the access policy 
    # If that is the case you can eliminate advanced security, just be sure to not give anonymous access
    response = client.create_domain(
        DomainName=domain_name,
        EngineVersion='OpenSearch_2.5',
        ClusterConfig={
            'InstanceType': 't3.small.search',
            'InstanceCount': 1,
            'DedicatedMasterEnabled': False,
            'ZoneAwarenessEnabled': False,
        },
        EBSOptions={
            'EBSEnabled': True,
            'VolumeType': 'gp2',
            'VolumeSize': 10, 
        },
        AccessPolicies=access_policy_json,
        NodeToNodeEncryptionOptions={
            'Enabled': True
        },
        EncryptionAtRestOptions={
            'Enabled': True
        },
        AdvancedSecurityOptions={
            'Enabled': True,
            'InternalUserDatabaseEnabled': True,
            'MasterUserOptions': {
                'MasterUserName': ADMIN_USER,
                'MasterUserPassword': ADMIN_PASSWORD
            }
        },
        DomainEndpointOptions={
        'EnforceHTTPS': True  # Needed for Advanced security
    }
    )

    print("Dominio en proceso de creación...")

    # Verify that the domain is in creation stage, it takes time
    status = client.describe_domain(DomainName=domain_name)
    while status['DomainStatus']['Processing']:
        print("El dominio todavía se está procesando. Espera un momento...")
        time.sleep(30) # Wait 30 second before verify again
        status = client.describe_domain(DomainName=domain_name)

    # Get the endpoing
    endpoint = status['DomainStatus']['Endpoint']
    print(f"Tu dominio de OpenSearch está listo y el endpoint es: {endpoint}")
