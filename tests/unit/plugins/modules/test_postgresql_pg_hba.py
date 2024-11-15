# -*- coding: utf-8 -*-

# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import sys
import pytest


if sys.version_info[0] == 3:
    from plugins.modules.postgresql_pg_hba import tokenize, TokenizerException, handle_address_field, \
        handle_netmask_field, handle_db_and_user_strings, PgHbaRuleValueError, PgHbaValueError, parse_auth_options
elif sys.version_info[0] == 2:
    from ansible_collections.community.postgresql.plugins.modules.postgresql_pg_hba import tokenize, \
        TokenizerException, handle_address_field, handle_netmask_field, handle_db_and_user_strings, \
        PgHbaRuleValueError, PgHbaValueError, parse_auth_options


def test_tokenize():
    assert tokenize('one two three') == ["one", "two", "three"]
    assert tokenize(' one two three ') == ["one", "two", "three"]
    assert tokenize(' "one two" "three" ') == ['"one two"', '"three"']
    assert tokenize('"one" two three') == ['"one"', 'two', 'three']
    assert tokenize('"one two" three') == ['"one two"', "three"]
    assert tokenize('one="two three" four') == ['one="two three"', "four"]
    assert tokenize('"one two"') == ['"one two"']
    assert tokenize('"one"') == ['"one"']
    with pytest.raises(TokenizerException, match="Unterminated quote"):
        tokenize('one="two three four')
    with pytest.raises(TokenizerException, match="Unterminated quote"):
        tokenize('one two"')


def test_handle_db_and_user_strings():
    assert handle_db_and_user_strings("a,b,c") == "a,b,c"
    assert handle_db_and_user_strings("c,b,a") == "a,b,c"
    assert handle_db_and_user_strings('"c,b,a"') == '"c,b,a"'
    assert handle_db_and_user_strings("all") == "all"
    assert handle_db_and_user_strings('"all"') == '"all"'


def test_handle_address_field():
    # it seems that test breaks for Python 2.7 and in 2024, I'm not going to work around that
    # if you still run 2.7, that is your problem
    try:
        import ipaddress
    except ImportError:
        return
    ipaddress.ip_address("0.0.0.0")  # otherwise flake complains
    assert handle_address_field("1.2.3.4") == ("1.2.3.4", "IPv4", -1)
    assert handle_address_field("1.0.0.0/8") == ("1.0.0.0", "IPv4", 8)
    assert handle_address_field('"1.0.0.0/8"') == ("1.0.0.0", "IPv4", 8)
    assert handle_address_field("ffff::") == ("ffff::", "IPv6", -1)
    assert handle_address_field("ffff::/16") == ("ffff::", "IPv6", 16)
    assert handle_address_field('"ffff::/16"') == ("ffff::", "IPv6", 16)
    assert handle_address_field("host.example.com") == ("host.example.com", "hostname", -1)
    assert handle_address_field('"host.example.com"') == ('"host.example.com"', "hostname", -1)
    assert handle_address_field("samehost") == ("samehost", "hostname", -1)

    with pytest.raises(PgHbaValueError, match=".* has host bits set"):
        handle_address_field("1.2.3.4/8")
    with pytest.raises(PgHbaValueError, match=".* has host bits set"):
        handle_address_field("ffff::/8")

    with pytest.raises(PgHbaValueError, match=".* is neither a valid IP address, network, hostname or keyword"):
        handle_address_field("host.example.com:1234")
    with pytest.raises(PgHbaValueError, match=".* is neither a valid IP address, network, hostname or keyword"):
        handle_address_field("1.2.3.4/33")
    with pytest.raises(PgHbaValueError, match=".* is neither a valid IP address, network, hostname or keyword"):
        handle_address_field("1234:ffff::/129")


def test_handle_netmask_field():
    # it seems that test breaks for Python 2.7 and in 2024, I'm not going to work around that
    # if you still run 2.7, that is your problem
    try:
        import ipaddress
    except ImportError:
        return
    ipaddress.ip_address("0.0.0.0")  # otherwise flake complains
    assert handle_netmask_field("255.255.255.0") == ("255.255.255.0", "IPv4", 24)
    assert handle_netmask_field('"255.255.255.0"') == ("255.255.255.0", "IPv4", 24)
    assert handle_netmask_field("ffff:ffff::") == ("ffff:ffff::", "IPv6", 32)
    assert handle_netmask_field('"ffff:ffff::"') == ("ffff:ffff::", "IPv6", 32)
    assert handle_netmask_field('hello', raise_not_valid=False) == ("", "invalid", -1)

    with pytest.raises(PgHbaValueError, match=".* is not a valid netmask"):
        handle_netmask_field("255.0.0.0/8")
    with pytest.raises(PgHbaValueError, match=".* is not a valid netmask"):
        handle_netmask_field("ffff::/16")
    with pytest.raises(PgHbaValueError, match=".* is not a valid netmask"):
        handle_netmask_field("1:2.3.4")
    with pytest.raises(PgHbaValueError, match="IP mask .* is invalid .*"):
        handle_netmask_field("255.255.0.255")
    with pytest.raises(PgHbaValueError, match="IP mask .* is invalid .*"):
        handle_netmask_field("ffff:ffff::ffff")


def test_parse_auth_options():
    assert parse_auth_options(["key=value"]) == {"key": "value"}
    assert parse_auth_options(["key1=value1", "key2=value2"]) == {"key1": "value1", "key2": "value2"}
    assert parse_auth_options(["key=value=with=equal=signs"]) == {"key": "value=with=equal=signs"}
    assert (parse_auth_options(['radiusservers="server1,server2"', 'radiussecrets="""secret one"",""secret two"""'])
            == {'radiusservers': '"server1,server2"', 'radiussecrets': '"""secret one"",""secret two"""'})
    with pytest.raises(PgHbaRuleValueError, match="Found invalid option"):
        parse_auth_options(["notkeyvalue"])
    with pytest.raises(PgHbaRuleValueError, match="The rule contains two options with the same key"):
        parse_auth_options(["key=value", "key=value2"])
