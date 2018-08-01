# Simple Ansible Inventory

The idea is to keep an Ansible inventory simple, clean and easily readable.
Each host will only have to be written one time and you'll not have to define each group before using it.

## How to use

`./simple-ansible-inventory.py --list`

To work properly, `simple-ansible-inventory.py` needs inventory file(s) to read.
There's two possibilities :
 * By default, `simple-ansible-inventory.py` will look in its folder and in all of its subfolder for inventory yaml file(s)
 * If the environment variable `ANSIBLE_YAML_INVENTORY` is defined, `simple-ansible-inventory.py` will attempt to read the inventory file in the environment variable and only this one

## Directory layout

The directory layout followed is given by the Ansible best pratices.
https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html#directory-layout

## Inventory files

You can find inventory file examples in [`inventory_file_1.yml`](inventory_file_1.yml) and [`inventory_file_2.yml`](inventory_file_2.yml)

An inventory file is a yaml file starting with the following header
```yaml
---
#### YAML inventory file
```

In this inventory file, you only define hosts and groups associated to this host.
There's no group definition, a group is automatically created when associated to an host.

Example:

If you define the following host
```yaml
hosts:
  - host: luke-01.example.com
    groups: [group_1, datacenter_1]
```

- the host `luke-01.example.com` will be created
- groups `group_1` and `datacenter_1` will be created
- groups `group_1` and `datacenter_1` will be associated to the host `luke-01.example.com`

## Group vars

Following Ansible best practices, all group vars have to be defined in the `group_vars` folder.
If you want to create the variable `group: Rebels` for the group `group_1`, you have to create the file [`group_vars/group_1.yml`](group_vars/group_1.yml) with the following content:

```yaml
---
group: Rebels
```

## Host vars

There's two possibilities to define host vars

1. In the inventory file
2. In the `host_vars` folder (following Ansible best practices)


### In the inventory file

If you want to create the variable `lightsaber: blue` for the host `obi-wan-02.example.com`, you have to set `hostvars` for the host in the inventory file:

```yaml
- host: obi-wan-02.example.com
  hostvars:
    lightsaber: blue
  groups: [group_1, datacenter_1]
```

### In the `host_vars` folder (following Ansible best practices)

Following Ansible best practices, host vars have to be defined in the `host_vars` folder.
If you want to create the variable `force_side: Sith` for the host `darth-vader-01.example.com`, you have to create the file [`host_vars/darth-vader-01.example.com1.yml`](group_vars/darth-vader-01.example.com.yml) with the following content:

```yaml
---
force_side: Sith
```


## And that's it !