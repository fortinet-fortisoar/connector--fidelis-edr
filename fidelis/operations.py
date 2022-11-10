""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """

import validators, requests, json
import base64
from connectors.core.connector import get_logger, ConnectorError

logger = get_logger('fidelis')

error_msgs = {
    400: 'Bad/Invalid Request',
    401: 'Unauthorized: Invalid credentials',
    403: 'Access Denied',
    404: 'Not Found',
    500: 'Internal Server Error',
    503: 'Service Unavailable'
}


class Fidelis(object):
    def __init__(self, config):
        self.server_url = config.get('server', '')
        if not self.server_url.startswith('https://'):
            self.server_url = 'https://' + self.server_url
        if not self.server_url.endswith('/'):
            self.server_url += '/'
        self.username = config.get('username')
        self.password = config.get('password')
        self.verify_ssl = config.get('verify_ssl')

    def make_api_call(self, endpoint=None, method='GET', data=None, params=None):
        try:
            url = self.server_url + 'endpoint/api/' + endpoint
            token = self.get_authorisation_token()
            headers = {'Authorization': "bearer " + token, 'Content-Type': 'application/json'}
            response = requests.request(method, url, params=params, data=data, headers=headers, verify=self.verify_ssl)
            if response.ok:
                return response.json()
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
        try:
            url = self.server_url + 'endpoint/api/authenticate?Username=' + self.username + '&Password=' + self.password
            b64_credential = base64.b64encode((self.username + ":" + self.password).encode('utf-8')).decode()
            headers = {'Authorization': "Basic " + b64_credential, 'Content-Type': 'application/json'}
            response = requests.request('GET', url, headers=headers, verify=self.verify_ssl)
            return json.loads(response.content)['data']['token']
        except Exception as err:
            logger.exception(str(err))
            raise ConnectorError(str(err))


def _check_health(config, params):
    fa = Fidelis(config)
    try:
        response = fa.get_alerts(config, params)
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
    # return fa.make_api_call(endpoint='alerts/getalertsV2', params=params)
    return fa.make_api_call(endpoint=endpoint, params=params)


def get_endpoints(config, params):
    fa = Fidelis(config)
    endpoint = 'endpoints/v2/' + str(params.get('startIndex')) + '/' + str(params.get('count')) + '/' + params.get(
        'sort')
    return fa.make_api_call(endpoint=endpoint)


def get_endpoints_by_name(config, params):
    fa = Fidelis(config)
    data = [params.get('nameArray')]
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
    endpoint = 'playbooks/PlaybooksAndScripts?' + 'filterType=' + str(
        params.get('filterType')) + '&platformFilter=' + str(
        params.get('platformFilter')) + '&sort=' + str(params.get('sort')) + '&skip=' + str(
        params.get('skip')) + '&take=' + str(params.get('take'))
    return fa.make_api_call(endpoint=endpoint)


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
    params = get_params(params)
    return fa.make_api_call(endpoint='packages/' + params.get('scriptID') + "?type=File")


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
    data = get_params(params)
    params = get_params(params)
    return fa.make_api_call(endpoint='packages/' + params.get('scriptPackageId') + '/execute', method='POST',
                            data=json.dumps(data))


def script_job_results(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='jobresults/' + params.get('jobResultID'))


def create_task(config, params):
    fa = Fidelis(config)
    params = get_params(params)
    return fa.make_api_call(endpoint='jobs/createTask', params=params)


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
