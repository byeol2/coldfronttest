import json
import logging

import ldap.filter
from coldfront.core.user.utils import UserSearch
from coldfront.core.utils.common import import_from_settings
from ldap3 import Connection, Server, Tls, get_config_parameter, set_config_parameter

logger = logging.getLogger(__name__)


class LDAPUserSearch(UserSearch):
    search_source = 'LDAP'

    def __init__(self, user_search_string, search_by):
        super().__init__(user_search_string, search_by)
        self.LDAP_SERVER_URI = import_from_settings('LDAP_USER_SEARCH_SERVER_URI')
        self.LDAP_USER_SEARCH_BASE = import_from_settings('LDAP_USER_SEARCH_BASE')
        self.LDAP_BIND_DN = import_from_settings('LDAP_USER_SEARCH_BIND_DN', None)
        self.LDAP_BIND_PASSWORD = import_from_settings('LDAP_USER_SEARCH_BIND_PASSWORD', None)
        self.LDAP_CONNECT_TIMEOUT = import_from_settings('LDAP_USER_SEARCH_CONNECT_TIMEOUT', 2.5)
        self.LDAP_USE_SSL = import_from_settings('LDAP_USER_SEARCH_USE_SSL', True)
        self.LDAP_USE_TLS = import_from_settings("LDAP_USER_SEARCH_USE_TLS", False)
        self.LDAP_PRIV_KEY_FILE = import_from_settings('LDAP_USER_SEARCH_PRIV_KEY_FILE', None)
        self.LDAP_CERT_FILE = import_from_settings('LDAP_USER_SEARCH_CERT_FILE', None)
        self.LDAP_CACERT_FILE = import_from_settings('LDAP_USER_SEARCH_CACERT_FILE', None)
        self.ATTRIBUTE_MAP = import_from_settings('LDAP_USER_SEARCH_ATTRIBUTE_MAP', {
                                                      "username": "uid",
                                                      "last_name": "sn",
                                                      "first_name": "givenName",
                                                      "email": "mail",
                                                  })
        self.MAPPING_CALLBACK = import_from_settings('LDAP_USER_SEARCH_MAPPING_CALLBACK', self.parse_ldap_entry)

        tls = None
        if self.LDAP_USE_TLS:
            tls = Tls(
                local_private_key_file=self.LDAP_PRIV_KEY_FILE,
                local_certificate_file=self.LDAP_CERT_FILE,
                ca_certs_file=self.LDAP_CACERT_FILE,
            )

        self.server = Server(self.LDAP_SERVER_URI, use_ssl=self.LDAP_USE_SSL, connect_timeout=self.LDAP_CONNECT_TIMEOUT, tls=tls)
        self.conn = Connection(self.server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True)

    def parse_ldap_entry(search_source, attribute_map, entry):
        entry_dict = json.loads(entry.entry_to_json()).get('attributes')

        user_dict = {'source': search_source}
        for user_attr, ldap_attr in attribute_map:
            user_dict[user_attr] = entry_dict.get(ldap_attr)[0] if entry_dict.get(ldap_attr) else ''

        return user_dict

    def search_a_user(self, user_search_string=None, search_by='all_fields'):
        size_limit = 50
        ldap_attrs = list(self.ATTRIBUTE_MAP.values())
        attrs = get_config_parameter("ATTRIBUTES_EXCLUDED_FROM_CHECK")
        attrs.extend(ldap_attrs)
        set_config_parameter("ATTRIBUTES_EXCLUDED_FROM_CHECK", attrs)
        if user_search_string and search_by == 'all_fields':
            filter = ldap.filter.filter_format(
                f"(|({ldap_attrs[0]}=*%s*)({ldap_attrs[1]}=*%s*)({ldap_attrs[2]}=*%s*)({ldap_attrs[3]}=*%s*))",
                [user_search_string] * 4)
        elif user_search_string and search_by == 'username_only':
            filter = ldap.filter.filter_format(f"({self.ATTRIBUTE_MAP['username']}=%s)",
                                               [user_search_string])
            size_limit = 1
        else:
            filter = '(objectclass=person)'

        searchParameters = {'search_base': self.LDAP_USER_SEARCH_BASE,
                            'search_filter': filter,
                            'attributes': ldap_attrs,
                            'size_limit': size_limit}
        logger.debug(f"search params:{searchParameters}")
        self.conn.search(**searchParameters)
        users = []
        logger.debug(self.conn.result)
        for idx, entry in enumerate(self.conn.entries, 1):
            entry_dict = json.loads(entry.entry_to_json()).get('attributes')
            logger.debug(f"Entry dict: {entry_dict}")
            user_dict = self.MAPPING_CALLBACK(self.search_source, self.ATTRIBUTE_MAP, entry_dict)
            users.append(user_dict)
        logger.info("LDAP user search for %s found %s results", user_search_string, len(users))
        return users
