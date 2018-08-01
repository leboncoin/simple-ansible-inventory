#!/usr/bin/env python

import logging
import os
import argparse
import yaml
import json
import re
import copy
import textwrap

"""
Project repo
https://github.com/leboncoin/simple-ansible-inventory

For further details about Ansible best practices including directory layout, see
https://docs.ansible.com/ansible/2.5/user_guide/playbooks_best_practices.html

For further details about developing Ansible inventory, see
http://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html
"""

INVENTORY_SCRIPT_NAME = "SimpleAnsibleInventory"
INVENTORY_SCRIPT_VERSION = 1.0
LOGGER = None
INVENTORY_FILE_REGEX_PATTERN = ".*\.y[a]?ml"
INVENTORY_FILE_HEADER_SIZE = 28
INVENTORY_FILE_HEADER = "---\n#### YAML inventory file"
INVENTORY_FILE_ENV_VAR = "ANSIBLE_YAML_INVENTORY"
ACCEPTED_REGEX = r"\[(?:(?:[\d]+-[\d]+|[\d]+)+,?)+\]"


def build_meta_header(host, meta_header):
    """
    Progressively build the meta header host by host

    :param host: current host to add to meta header
    :type host: dict
    :param meta_header: meta header to build
    :type meta_header: dict
    :return:
    """
    # If found host doesn't exists in dict, we create it
    if host['host'] not in meta_header['hostvars']:
        meta_header['hostvars'][host['host']] = dict()
    # Browsing and adding all vars found for host
    if 'hostvars' in host:
        for hostvar in host['hostvars']:
            meta_header['hostvars'][host['host']][hostvar] = \
                host['hostvars'][hostvar]
    # Return new meta_header version containing new host
    return meta_header


def build_groups(host, partial_inventory):
    """
    Progressively build groups conf host by host

    :param host: current host to add to meta header
    :type host: dict
    :param partial_inventory: Only contains _meta header
    :type partial_inventory: dict
    :return: filled inventory
    """
    # check if 'all' group exists, if no, create it
    if 'all' not in partial_inventory:
        partial_inventory['all'] = dict()
        partial_inventory['all']['hosts'] = list()
        partial_inventory['all']['vars'] = dict()
        partial_inventory['all']['children'] = list()
    # If groups section doesn't exists return inventory without modification
    if 'groups' not in host:
        return partial_inventory
    # For each group of the host
    for group in host['groups']:
        # If groups doesn't already exists, creating it
        if group not in partial_inventory:
            partial_inventory[group] = dict()
            partial_inventory[group]['hosts'] = list()
            partial_inventory[group]['vars'] = dict()
            partial_inventory[group]['children'] = list()
            # add group to 'all' group if not already in
            if group not in partial_inventory['all']['children']:
                partial_inventory['all']['children'].append(group)
        partial_inventory[group]['hosts'].append(host['host'])
    return partial_inventory


def get_int_interval(from_int, to_int):
    """
    Return a list of all integers between two integers

    :param from_int: start from
    :type from_int: int
    :param to_int: end at
    :type to_int: int
    :return: list(int)
    """
    LOGGER.debug("Calculating int interval between " + str(from_int) +
                 " and " + str(to_int))
    return [str(value) for value in range(from_int, to_int + 1)]


def all_string_from_pattern(input_string, matching_part):
    """
    Return a list of all string matching the input string containing a pattern

    :param input_string: input string containing pattern
    :type input_string: str
    :param matching_part: pattern extracted from hostname
    :type matching_part: str
    :return: str
    """
    # Transform matched pattern to a list of ranges
    regex_found = matching_part.group(0).replace("[", "").replace("]", "").split(',')
    possibilities = list()
    # let's fill all ranges
    for pattern in regex_found:
        split_range = pattern.split('-')
        int_1 = int(split_range[0])
        int_possibilities = [int_1]
        if len(split_range) == 2:
            int_1 = min(int_1, int(split_range[1]))
            int_2 = max(int(split_range[0]), int(split_range[1]))
            int_possibilities = get_int_interval(int_1, int_2)
        LOGGER.debug("Possibilities: " + str(int_possibilities))
        for possibility in int_possibilities:
            possibilities.append(
                input_string[:matching_part.start(0)] +
                str(possibility) +
                input_string[matching_part.end(0):]
            )
    return possibilities


def patterning_hosts(regex_found, host, filled_pattern_host_list):
    """
    Function used recursively to fill all patterns in hostname

    :param regex_found: re.match object
    :type regex_found: re.match()
    :param host: host read in conf
    :type host: dict
    :param filled_pattern_host_list: list containing all hosts
                                     with all patterns filled
    :type filled_pattern_host_list: list
    :return:
    """
    LOGGER.debug("Processing regex " + str(regex_found.group(0)) +
                 " found in host name: " + host['host'])
    # For each hostname possibility with first pattern
    for patterned_host in all_string_from_pattern(host['host'], regex_found):
        # Checking if there is still another pattern left in hostname
        regex_found = re.search(ACCEPTED_REGEX, patterned_host)
        # build a new host with the hostname
        new_host = dict(host)
        new_host['host'] = patterned_host
        # If hostname still containing pattern, call itself
        if regex_found:
            patterning_hosts(regex_found, new_host, filled_pattern_host_list)
        # If no pattern left, append host to list
        else:
            filled_pattern_host_list.append(new_host)


def get_inventory_recursively(raw_conf):
    """
    Build and return the inventory

    :param raw_conf: Raw configuration loaded from yml configuration file
    :type raw_conf: dict
    :return: dict
    """
    LOGGER.debug("Building full inventory from loaded YAML(s)")
    inventory = dict()
    meta_header = dict()
    meta_header['hostvars'] = dict()
    # Browsing all hosts
    for host in raw_conf['hosts']:
        LOGGER.debug("Processing host entry " + str(host))
        filled_pattern_host_list = list()
        regex_found = re.search(ACCEPTED_REGEX, host['host'])
        # If no regex pattern, directly add the host
        if not regex_found:
            filled_pattern_host_list.append(host)
        # Else fill all patterns
        else:
            patterning_hosts(regex_found, host, filled_pattern_host_list)
        LOGGER.debug("Host(s) generated from this host entry: " +
                     str([hn['host'] for hn in filled_pattern_host_list]))
        for filled_pattern_host in filled_pattern_host_list:
            # Complete meta header for each host
            meta_header = build_meta_header(filled_pattern_host, meta_header)
            inventory = build_groups(filled_pattern_host, inventory)
    inventory['_meta'] = meta_header
    return inventory


def find_inventory_files():
    """
    find the inventory file in sub folders

    :return: string
    """
    if INVENTORY_FILE_ENV_VAR in os.environ:
        LOGGER.debug("env VAR " + INVENTORY_FILE_ENV_VAR + " found")
        return [os.environ[INVENTORY_FILE_ENV_VAR]]
    inventory_files = list()
    LOGGER.debug("Looking for inventory files")
    # script py path
    script_path = os.path.realpath(__file__)
    inventories_path = os.path.dirname(script_path)
    # walking through script folder looking for yaml files
    for root, dirnames, filenames in os.walk(inventories_path):
        LOGGER.debug("All files found: " + str(filenames))
        for file in [f for f in filenames if re.search(INVENTORY_FILE_REGEX_PATTERN, f)]:
            # if file beginning match header
            with open(os.path.join(root, file), 'r') as fd:
                if fd.read(INVENTORY_FILE_HEADER_SIZE) == INVENTORY_FILE_HEADER:
                    inventory_files.append(os.path.join(root, file))
    return inventory_files


def list_all_hosts():
    """
    Build the dictionary containing all hosts

    :return: dict
    """
    LOGGER.debug("listing all hosts")
    raw_confs_list = list()
    # Load all configuration files
    inventory_files = find_inventory_files()
    LOGGER.debug("Inventory files found: " + str(inventory_files))
    # If no inventory files found, return empty inventory
    if not len(inventory_files):
        return {"_meta": {"hostvars": {}}, "all": {"children": ["ungrouped"]}}
    for inventory_file in inventory_files:
        with open(inventory_file, 'r') as fd:
            LOGGER.debug("Loading file: " + inventory_file)
            raw_confs_list.append(yaml.load(fd))
    # Copy first conf loaded to another object
    raw_conf = copy.deepcopy(raw_confs_list[0])
    # Delete first conf loaded
    raw_confs_list.pop(0)
    # Append all others conf to the first one by merging dictionaries
    LOGGER.debug("Merging files if needed")
    for conf in raw_confs_list:
        for key, value in conf.items():
            raw_conf.setdefault(key, []).extend(value)
    inventory = get_inventory_recursively(raw_conf)
    LOGGER.debug("Inventory found: " + str(inventory))
    return inventory


def create_logger():
    """
    Create a logger instance

    :return: logger instance
    """
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def parse_arguments():
    """
    Initialize the parser, flags list is mandatory

    :return: parsed arguments
    """
    epilog = '''
    By default the script will walk in script folder and in all its subfolders
    looking for inventory files.
    If a filename match the regex
        %s
    and if the first %d
        %s
    the file will be considered as an inventory file

    If the environment variable INVENTORY_FILE_ENV_VAR is found, the only
    inventory file read will be the file specified in the environment
    variable.
    ''' % (str(INVENTORY_FILE_REGEX_PATTERN),
           INVENTORY_FILE_HEADER_SIZE,
           INVENTORY_FILE_HEADER.replace('\n', '\n\t'))
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="YAML Ansible inventory script loader",
        epilog=textwrap.dedent(epilog)
    )
    parser.add_argument('--list',
                        action='store_true',
                        help="display all loaded inventory")
    parser.add_argument('--host',
                        nargs=1,
                        help="display vars for specified host")
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="enable verbose mode")
    parser.add_argument('-V', '--version',
                        action='store_true',
                        help="display inventory script version and exit")
    return parser.parse_args()


if __name__ == "__main__":
    LOGGER = create_logger()
    parsed_arguments = parse_arguments()
    if parsed_arguments.verbose:
        LOGGER.setLevel(logging.DEBUG)
        for hdlr in LOGGER.handlers:
            hdlr.setLevel(logging.DEBUG)
    if parsed_arguments.version:
        LOGGER.debug("version flag found")
        print(INVENTORY_SCRIPT_NAME + " v" +  str(INVENTORY_SCRIPT_VERSION))
    elif parsed_arguments.list:
        LOGGER.debug("list flag found")
        print(json.dumps(list_all_hosts()))
    elif parsed_arguments.host:
        LOGGER.debug("host flag found")
        print(json.dumps(dict()))
