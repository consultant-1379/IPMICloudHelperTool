from os.path import realpath, join
from os.path import dirname
from unittest import TestCase

from mock import Mock, patch, MagicMock

from ipmitool import IPMICloudAdapter
import ipmitool


# noinspection PyUnusedLocal
class TestIPMICloudAdapter(TestCase):
    def setUp(self):
        pass

    def mock_curl(self, exec_process, gateway_host,
                  pod='https://pod.athtem.eei.ericsson.se/'):
        def side_effect(command):
            if ' '.join(command).endswith('gateway_hostname'):
                return gateway_host
            elif ' '.join(command).endswith(gateway_host):
                return pod

        exec_process.side_effect = side_effect

    def mock_curl_failure(self, exec_process, gateway_host):
        def side_effect(command):
            if ' '.join(command).endswith('gateway_hostname'):
                return gateway_host
            elif ' '.join(command).endswith(gateway_host):
                raise IOError(9, 'TEST IOError')

        exec_process.side_effect = side_effect

    def mock_node(self, hostname, model_id, ilo_address):
        json_data = open(join(dirname(realpath(__file__)), 'node.json')).read()
        json_data = json_data.replace('@@HOSTNAME@@', hostname)
        json_data = json_data.replace('@@MODELID@@', model_id)
        json_data = json_data.replace('@@ILOADDRESS@@', ilo_address)
        return json_data

    def mock_find_nodes(self, exec_process, node_data):
        def findse(command):
            nodes = ''
            for nd in node_data:
                nodes += self.mock_node(*nd)
            return nodes

        exec_process.side_effect = findse

    @patch('ipmitool.exec_process')
    def test_get_vm_name(self, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '1.1.1.222')])

        vmname = ipmitool.get_vm_name('1.1.1.222')
        self.assertEquals('vm1', vmname)

        self.assertRaises(ValueError, ipmitool.get_vm_name, '1.1.1.1')

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_set_poweroff(self, mock_urlopen, mock_request, exec_process):
        self.mock_find_nodes(exec_process,
                             [('a1', 'a1', '1.1.1.42')])
        with patch('ipmitool.get_spp_pod') as get_spp_pod:
            get_spp_pod.return_value = 'https://atvcloud3/'
            self.adapter = IPMICloudAdapter('1.1.1.42')

            return_code = self.adapter.set_poweroff()
            mock_request.assert_called_once_with(
                'https://atvcloud3/Vms/'
                'poweroff_api/vm_name:a1.xml')
            self.assertEquals(0, return_code)

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_set_poweron(self, mock_urlopen, mock_request, exec_process):
        self.mock_find_nodes(exec_process,
                             [('cloud-svc-1', 'cloud-svc-1', '1.1.1.42')])
        with patch('ipmitool.get_spp_pod') as get_spp_pod:
            get_spp_pod.return_value = 'https://atvcloud3/'
            self.adapter = IPMICloudAdapter('1.1.1.42')
            mocked_sleep = patch('ipmitool.time.sleep')
            mocked_sleep.return_value = 0
            mocked_sleep.start()

            return_code = self.adapter.set_poweron()
            mock_request.has_calls([
                'https://atvcloud3/Vms/'
                'poweron_api/vm_name:ms-1.xml',
                'https://10.42.34.189/Vms/boot_devices:hd/vm_name:ms-1.xml'])
            mocked_sleep.stop()
            self.assertEquals(0, return_code)

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_set_bootdev_pxe(self, mock_urlopen, mock_request, exec_process):
        self.mock_find_nodes(exec_process,
                             [('cloud-svc-1', 'cloud-svc-1', '1.1.1.42')])
        with patch('ipmitool.get_spp_pod') as get_spp_pod:
            get_spp_pod.return_value = 'https://atvcloud3/'
            self.adapter = IPMICloudAdapter('1.1.1.42')

            return_code = self.adapter.set_bootdev_pxe()
            mock_request.assert_called_once_with(
                'https://atvcloud3/Vms/'
                'set_boot_device_api/boot_devices:net/vm_name:cloud-svc-1.xml')
            self.assertEquals(0, return_code)

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_set_bootdev_hd(self, mock_urlopen, mock_request, exec_process):
        self.mock_find_nodes(exec_process, [('ms-1', 'ms-1', '1.1.1.42')])
        with patch('ipmitool.get_spp_pod') as get_spp_pod:
            get_spp_pod.return_value = 'https://atvcloud3/'
            self.adapter = IPMICloudAdapter('1.1.1.42')

            return_code = self.adapter.set_bootdev_hd()
            mock_request.assert_called_once_with(
                'https://atvcloud3/Vms/'
                'set_boot_device_api/boot_devices:hd/vm_name:ms-1.xml')
            self.assertEquals(0, return_code)

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_http_error(self, mock_urlopen, mock_request, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '1.1.1.222')])

        class MockHttpError(Exception):
            def __init__(self):
                self.code = 404
                self.read = lambda: 'foo'

        mock_exception = MockHttpError
        mock_urlopen.side_effect = mock_exception
        try:
            actual_httperror = ipmitool.urllib2.HTTPError
            ipmitool.urllib2.HTTPError = mock_exception

            self.adapter = IPMICloudAdapter('1.1.1.222')
            return_code = self.adapter.set_bootdev_hd()
            self.assertEquals(1, return_code)
        finally:
            ipmitool.urllib2.HTTPError = actual_httperror
            pass

    @patch('ipmitool.exec_process')
    @patch('ipmitool.urllib2.Request')
    @patch('ipmitool.urllib2.urlopen')
    def test_url_error(self, mock_urlopen, mock_request, exec_process):
        class MockUrlError(Exception):
            def __init__(self):
                # Yes, in URLError args == reason
                self.reason = self.args = '[Errno 110] Connection timed out'

        mock_exception = MockUrlError
        mock_urlopen.side_effect = mock_exception
        try:
            actual_urlerror = ipmitool.urllib2.URLError
            ipmitool.urllib2.URLError = mock_exception

            self.mock_find_nodes(exec_process, [('ms-1', 'ms-1', '1.1.1.42')])
            with patch('ipmitool.get_spp_pod') as get_spp_pod:
                get_spp_pod.return_value = 'https://atvcloud3/'
                self.adapter = IPMICloudAdapter('1.1.1.42')
                return_code = self.adapter.set_bootdev_hd()
                self.assertEquals(1, return_code)
        finally:
            ipmitool.urllib2.URLError = actual_urlerror
            pass

    @patch('ipmitool.exec_process')
    @patch('ipmitool.IPMICloudAdapter.set_bootdev_pxe')
    def test_run_cmd_bootdev_pxe(self, mock_method, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='bootdev', arg='pxe')
        mock_method.return_value = 0
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(0, self.adapter.run_cmd(mock_args))
        self.assertTrue(mock_method.called_once_with())

    @patch('ipmitool.exec_process')
    @patch('ipmitool.IPMICloudAdapter.set_bootdev_hd')
    def test_run_cmd_bootdev_disk(self, mock_method, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='bootdev', arg='disk')
        mock_method.return_value = 0
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(0, self.adapter.run_cmd(mock_args))
        self.assertTrue(mock_method.called_once_with())

    @patch('ipmitool.exec_process')
    @patch('__builtin__.print')
    @patch('ipmitool.IPMICloudAdapter.set_poweroff')
    def test_run_cmd_poweroff(self, mock_method, mock_print, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='power', arg='off')
        mock_method.return_value = 0
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(0, self.adapter.run_cmd(mock_args))
        self.assertTrue(mock_method.called_once_with())
        mock_print.has_calls("Chassis Power Control: Down/Off")

    @patch('ipmitool.exec_process')
    @patch('__builtin__.print')
    @patch('ipmitool.IPMICloudAdapter.set_poweron')
    def test_run_cmd_poweron(self, mock_method, mock_print, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='power', arg='on')
        mock_method.return_value = 0
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(0, self.adapter.run_cmd(mock_args))
        self.assertTrue(mock_method.called_once_with())
        mock_print.has_calls("Chassis Power Control: Up/On")

    @patch('ipmitool.exec_process')
    def test_run_cmd_power_bad_arg(self, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='power', arg='foo')
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(1, self.adapter.run_cmd(mock_args))

    @patch('ipmitool.exec_process')
    def test_run_cmd_bootdev_bad_dev(self, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='bootdev', arg='foo')
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(1, self.adapter.run_cmd(mock_args))

    @patch('ipmitool.exec_process')
    def test_run_cmd_bad_subcmd(self, exec_process):
        self.mock_find_nodes(exec_process, [('vm1', 'vm1', '15.16.17.43')])
        mock_args = Mock(command='chassis', subcmd='foo', arg='bar')
        self.adapter = IPMICloudAdapter('15.16.17.43')
        self.assertEquals(1, self.adapter.run_cmd(mock_args))

    @patch('ipmitool.IPMICloudAdapter')
    @patch('ipmitool.sys.exit')
    def test_main_function(self, mock_exit, mock_adapter):
        try:
            actual_argv = ipmitool.sys.argv
            ipmitool.sys.argv = ('ipmitool', '-H', '192.168.42.42', '-I',
                                 'lanplus', '-U', 'root', 'chassis',
                                 'power', 'on')

            ipmitool.run_ipmitool()
            mock_adapter.assert_called_once_with('192.168.42.42')
        finally:
            ipmitool.sys.argv = actual_argv

    @patch('ipmitool.exec_process')
    def test_get_spp_pod(self, exec_process):
        self.mock_curl(exec_process, 'atvts1234')

        pod = ipmitool.get_spp_pod()
        self.assertEquals('https://pod.athtem.eei.ericsson.se/', pod)

        self.mock_curl(exec_process, 'atvts1234', pod='')
        self.assertRaises(ValueError, lambda: ipmitool.get_spp_pod())

        self.mock_curl_failure(exec_process, 'atvts1234')
        self.assertRaises(IOError, lambda: ipmitool.get_spp_pod(retry_wait=1))

    @patch('ipmitool.exec_process')
    def test_curl(self, exec_process):

        self.error_code = 0
        return_string = 'returned'

        def side_effect(command):
            if self.error_code:
                try:
                    raise IOError(self.error_code)
                finally:
                    self.error_code = 0
            else:
                return return_string

        exec_process.side_effect = side_effect
        output = ipmitool.curl('http://url.com')
        self.assertEquals(return_string, output)

        self.error_code = 1
        self.assertRaises(IOError, ipmitool.curl, 'http://url.com')

        self.error_code = 6
        exec_process.call_count = 0
        with patch('ipmitool.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=file)
            output = ipmitool.curl('http://url.com')
            self.assertEquals(return_string, output)
            self.assertEquals(2, exec_process.call_count)
