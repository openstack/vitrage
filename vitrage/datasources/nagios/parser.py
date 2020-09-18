# Copyright 2016 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from io import StringIO
from lxml import etree
from oslo_log import log

from vitrage.datasources.nagios.properties import NagiosProperties

LOG = log.getLogger(__name__)


class NagiosParser(object):

    STATUS_TABLE_XPATH = '/html/body/table[@class="status"]'
    SERVICE_ROWS_XPATH = 'tr[position() > 1]'
    NAME_XPATH = 'table/tr/td[position()=1]/table/tr/td/a'

    def __init__(self):
        self.last_host_name = None

    def parse(self, html):
        try:
            tree = etree.parse(StringIO(html), etree.HTMLParser())
            status_tables = tree.xpath(self.STATUS_TABLE_XPATH)

            return self._parse_services(status_tables)

        except Exception:
            LOG.exception('Failed to get nagios services.')

    def _parse_services(self, status_tables):
        LOG.debug('Start parsing Nagios status')

        services = []
        for status_table in status_tables:
            service_rows = status_table.xpath(self.SERVICE_ROWS_XPATH)

            for service_row in service_rows:
                service = self._parse_service_row(service_row)

                if service:
                    LOG.debug('Appending service: %s', service)
                    services.append(service)
                else:
                    LOG.debug('service is None for service_row: %s',
                              service_row)

        LOG.debug('Done parsing Nagios status')

        return services

    def _parse_service_row(self, service_row):
        columns = list(service_row)

        # service lines have a fixed number of columns.
        # there are also two blank lines between different hosts,
        # so len(columns)==1 is also valid
        # TODO(ifat_afek): get column names by the header line
        if len(columns) == NagiosProperties.NUM_COLUMNS:
            return self._parse_service_columns(columns)

        elif len(columns) > NagiosProperties.NUM_COLUMNS:
            LOG.warning('Too many columns in nagios service row. '
                        'Found %d', len(columns))

        elif len(columns) > 1:
            LOG.warning('Missing columns in nagios service row. '
                        'Found only %d', len(columns))

        return None

    def _parse_service_columns(self, columns):
        return {
            NagiosProperties.RESOURCE_NAME:
                self._parse_host_name(columns[0], self.NAME_XPATH),
            NagiosProperties.SERVICE:
                self._get_column_data(columns[1], self.NAME_XPATH),
            NagiosProperties.STATUS: columns[2].text,
            NagiosProperties.LAST_CHECK: columns[3].text,
            NagiosProperties.DURATION: columns[4].text,
            NagiosProperties.ATTEMPT: columns[5].text,
            NagiosProperties.STATUS_INFO: columns[6].text
        }

    @staticmethod
    def _get_column_data(column, xpath):
        contents = column.xpath(xpath)

        if len(contents) == 1:
            return contents[0].text
        elif len(contents) > 1:
            LOG.warning('Multiple entries for nagios service column: %s',
                        contents.toString)
            return contents[0].text
        else:
            # len(contents) might be 0 for a host, since each host name appears
            # only once in the table
            return None

    def _parse_host_name(self, column, xpath):
        """Parse the host name and return it

        host name appears only once in the table, so keep using the same host
        name until found a new one

        :param column: the html column data
        :param xpath: the path of the host name in the column structure
        :return: the host name
        """
        host_name = self._get_column_data(column, xpath)

        if host_name:
            self.last_host_name = host_name
        else:
            host_name = self.last_host_name

        return host_name
