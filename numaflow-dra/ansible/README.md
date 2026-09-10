# What's this?

A set of Ansible scripts to automate the installation steps of AICP Numaflow PoC.

# How to use

The minimum ansible-core version required by this repository is **2.16**, determined by the collections listed in `requirements.yml`. The steps below walk you through installing the latest non-EOL version that satisfies this requirement.

## 1. Install Ansible into your control node

Follow the [official installation guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html). The guide covers both pipx installation and Ansible installation.

### 1-1. Install pipx

The official guide uses pipx to install Ansible. Install pipx first by following the [pipx installation guide](https://pipx.pypa.io/latest/how-to/install-pipx.html).

### 1-2. Install Ansible

Check the Python version on both your control node and managed nodes:

```
$ python3 --version
```

Then determine which Ansible package to install by following these references:

1. [ansible-core support matrix](https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html#ansible-core-support-matrix) — find the ansible-core versions compatible with your Python version.
2. [Ansible community changelogs](https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html#ansible-community-changelogs) — find the Ansible community package version that bundles the ansible-core version you need (>= 2.16).

Install via pipx following the [official guide > Installing Ansible](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html#pipx-install):

```
$ pipx install --include-deps ansible==<version>
$ ansible --version
```

## 2. Configure your inventory

Copy the template file to your own one (say `inventory/stg.yml`) in the following way:

```
$ cp inventory/inventory.yml.template inventory/stg.yml
```

Then edit `inventory/stg.yml` in order to build your inventory.

Set `python_ver` to the latest Python version that can run the latest Ansible version satisfying the requirements. This is the Python version that will be installed on the managed nodes in later steps.

## 3. Setup your login

On every managed node ("hosts"), do the following steps:

- Create the user described in `ansible_user`.
- Configure `/etc/sudoers` in order that the user can run sudo without typing password.
- Add your SSH public key to the user's `~/.ssh/authorized_keys` in order that you can login to the node without typing password.

## 4. (Optional) Cache the passphrase of your SSH key

If your SSH key has a passphrase, you can cache it in the following way:

```
$ eval `ssh-agent` && ssh-add ~/.ssh/id_your_ssh_key
```

## 5. Test your SSH connection to the managed nodes

```
$ ansible -i inventory/stg.yml -e ansible_python_interpreter=/usr/bin/python3 -m ping all
```

## 6. Setup a virtualenv on every managed node

### 6-1. Install Python to managed nodes

The virtualenv will be used by Ansible as its Python interpreter on managed nodes.

```
$ ansible-playbook -i inventory/stg.yml -e ansible_python_interpreter=/usr/bin/python3 site-common-setup-python-venv.yml
$ ansible -i inventory/stg.yml -m ping all
```

### 6-2. Verify the Python version used by Ansible

Confirm that the Python version and interpreter path match what you specified in `python_ver`:

```
$ ansible --version
$ ansible -i inventory/stg.yml -m setup -a "filter=ansible_python_version" all
```

## 7. Upgrade Ansible to the required version on your control node

If the Ansible version installed in step 1-2 does not yet satisfy the requirements (ansible-core >= 2.16), upgrade it now. Use the same references as step 1-2 to find the appropriate version.

```
$ pipx upgrade --include-injected ansible
```

If upgrading does not give you the required version, reinstall with a specific version:

```
$ pipx install --include-deps --force ansible==<version>
```

## 8. Install additional requirements from Ansible Galaxy

```
$ ansible-galaxy collection install -r requirements.yml
```

## 9. Edit and confirm variables

See **vars-stg.yml** and edit values if you need.

## 10. Run the root playbook to install AICP Numaflow PoC

```
$ ansible-playbook -i inventory/stg.yml -e @vars-stg.yml site-stg-dci-poc.yml
```

Re-run the command until the results have no "changed".

That's all.
