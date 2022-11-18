""" Copyright start
  Copyright (C) 2008 - 2022 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

import requests, json
import base64, os
from connectors.cyops_utilities.builtins import  upload_file_to_cyops
from django.conf import settings
from connectors.core.connector import get_logger, ConnectorError

logger = get_logger('fidelis-edr')

error_msgs = {
    400: 'Bad/Invalid Request',
    401: 'Unauthorized: Invalid credentials',
    403: 'Access Denied',
    404: 'Not Found',
    500: 'Internal Server Error',
    503: 'Service Unavailable'
}

PLATFORM_FILTER = {
    "All": 0,
    "Windows": 1,
    "Mac": 2,
    "Linux": 3
}


def str_to_list_for_stings(input_str):
    if isinstance(input_str, str) and len(input_str) > 0:
        return [x.strip() for x in input_str.split(',')]
    elif isinstance(input_str, list):
        return input_str
    elif isinstance(input_str, int):
        return [input_str]
    else:
        return []


class Fidelis(object):
    def __init__(self, config):
        self.server_url = config.get('server', '').strip('/')
        if not self.server_url.startswith('https://') and not self.server_url.startswith('http://'):
            self.server_url = 'https://' + self.server_url
        self.username = config.get('username')
        self.password = config.get('password')
        self.verify_ssl = config.get('verify_ssl')

    def make_api_call(self, endpoint=None, method='GET', data=None, params=None, headers=None, login_flag=False):
        try:
            url = self.server_url + '/endpoint/api/' + endpoint
            if not login_flag:
                token = self.get_authorisation_token()
            if not headers:
                headers = {'Authorization': "bearer " + token, 'Content-Type': 'application/json'}
            response = requests.request(method, url, params=params, data=data, headers=headers, verify=self.verify_ssl)
            if response.ok:
                if 'json' in response.headers.get('Content-Type'):
                    return response.json()
                elif response.headers.get('Content-Type') == 'application/octet-stream':
                    file_name = response.headers.get('content-disposition').split('filename=')[-1]
                    return response.content, file_name
                else:
                    return response.content
            else:
                logger.error(response.text)
                raise ConnectorError({'status_code': response.status_code, 'message': response.reason})
        except requests.exceptions.SSLError:
            raise ConnectorError('SSL certificate validation failed')
        except requests.exceptions.ConnectTimeout:
            raise ConnectorError('The request timed out while trying to connect to the server')
        except requests.exceptions.ReadTimeout:
            raise ConnectorError('The server did not send any data in the allotted amount of time')
        except requests.exceptions.ConnectionError:
            raise ConnectorError('Invalid endpoint or credentials')
        except Exception as err:
            logger.exception(str(err))
            raise ConnectorError(str(err))

    def get_authorisation_token(self):
        url = 'authenticate?Username=' + self.username + '&Password=' + self.password
        b64_credential = base64.b64encode((self.username + ":" + self.password).encode('utf-8')).decode()
        headers = {'Authorization': "Basic " + b64_credential, 'Content-Type': 'application/json'}
        response = self.make_api_call(endpoint=url, headers=headers, login_flag=True)
        if response.get('data'):
            return response.get('data').get('token')
        else:
            logger.exception(str(response))
            raise ConnectorError(str(response.get('error', '')))


def _check_health(config):
    fa = Fidelis(config)
    try:
        response = fa.get_authorisation_token()
        if response:
            logger.info('connector available')
            return True
    except Exception as e:
        raise ConnectorError('{0}'.format(e))


def get_params(params):
    params = {k: v for k, v in params.items() if v is not None and v != ''}
    return params


def get_alerts(config, params):
    fa = Fidelis(config)
    endpoint = 'alerts/getalertsV2'
    params = get_params(params)
    return fa.make_api_call(endpoint=endpoint, params=params)


def get_endpoints(config, params):
    fa = Fidelis(config)
    endpoint = 'endpoints/v2/' + str(params.get('startIndex')) + '/' + str(params.get('count')) + '/' + params.get(
        'sort')
    return fa.make_api_call(endpoint=endpoint)


def get_endpoints_by_name(config, params):
    fa = Fidelis(config)
    data = str_to_list_for_stings(params.get('nameArray'))
    return fa.make_api_call(endpoint='endpoints/endpointidsbyname', method='POST', data=json.dumps(data))


def delete_endpoint(config, params):
    fa = Fidelis(config)
    return fa.make_api_call(endpoint='endpoints/delete/' + params.get('endpointID'), method='DELETE')


def get_playbooks(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='playbooks/Playbooks', params=params)


def get_playbooks_scripts(config, params):
    fa = Fidelis(config)
    endpoint = 'playbooks/PlaybooksAndScripts'
    param_dict = {
        'filterType': 1 if params.get('filterType') == '1 - Playbooks' else 0,
        'platformFilter': PLATFORM_FILTER.get(params.get('platformFilter'), 0),
        'sort': params.get('sort', ''),
        'take': params.get('take', ''),
        'skip': params.get('skip', ''),
        'isManagementRequest': True
    }
    param_dict = {k: v for k, v in param_dict.items() if v is not None and v != '' and v != []}
    return fa.make_api_call(endpoint=endpoint, params=param_dict)


def get_playbooks_detail(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='playbooks/PlaybookDetail', params=params)


def get_api_info(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='product-info', params=params)


def get_script_packages(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='packages', params=params)


def get_script_packages_file(config, params):
    fa = Fidelis(config)
    response, file_name = fa.make_api_call(endpoint='packages/' + params.get('scriptID') + "?type=File")
    if response:
        path = os.path.join(settings.TMP_FILE_ROOT, file_name)
        logger.debug("Path: {0}".format(path))
        with open(path, 'wb') as fp:
            fp.write(response)
        attach_response = upload_file_to_cyops(file_path=file_name, filename=file_name,
                                               name=file_name, create_attachment=True)
        return attach_response


def get_script_packages_manifest(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='packages/' + params.get('scriptID') + "?type=Manifest")


def get_script_packages_metadata(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='packages/' + params.get('scriptID') + '?type=Metadata')


def get_script_packages_template(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='packages/' + params.get('scriptID') + '?type=Template')


def execute_script_package(config, params):
    fa = Fidelis(config)
    data = {
        'timeoutInSeconds': params.get('timeoutInSeconds'),
        'scriptPackageId': params.get('scriptPackageId'),
        'hosts': str_to_list_for_stings(params.get('hosts')),
        'integrationOutputs': str_to_list_for_stings(params.get('integrationOutputs')),
        'questions': params.get('questions', {})
    }
    return fa.make_api_call(endpoint='packages/' + params.get('scriptPackageId') + '/execute', method='POST',
                            data=json.dumps(data))


def script_job_results(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='jobresults/' + params.get('jobResultID'))


def create_task(config, params):
    fa = Fidelis(config)
    body = {
        "packageId": params.get('packageId'),
        "endpoints": str_to_list_for_stings(params.get('endpoints')),
        "isPlaybook": 'true' if params.get('isplaybook') == 'Playbook' else 'false'
    }
    return fa.make_api_call(endpoint='jobs/createTask', method='POST', data=json.dumps(body))


operations = {
    'get_alerts': get_alerts,
    'get_endpoints': get_endpoints,
    'get_endpoints_by_name': get_endpoints_by_name,
    'delete_endpoint': delete_endpoint,
    'get_playbooks': get_playbooks,
    'get_playbooks_scripts': get_playbooks_scripts,
    'get_playbooks_detail': get_playbooks_detail,
    'get_api_info': get_api_info,
    'get_script_packages': get_script_packages,
    'get_script_packages_file': get_script_packages_file,
    'get_script_packages_manifest': get_script_packages_manifest,
    'get_script_packages_metadata': get_script_packages_metadata,
    'get_script_packages_template': get_script_packages_template,
    'execute_script_package': execute_script_package,
    'script_job_results': script_job_results,
    'create_task': create_task
}
