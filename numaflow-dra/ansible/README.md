# What's this?

A set of Ansible scripts to automate the installation steps of AICP Numaflow PoC.

# How to use

## 1. Install Ansible into your control node

Follow the [official installation guide](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html).

## 2. Install additional requirements from Ansible Galaxy

```
$ ansible-galaxy collection install -r requirements.yml
```

## 3. Configure your inventory

Copy the template file to your own one (say `inventory/stg.yml`) in the following way:

```
$ cp inventory/inventory.yml.template inventory/stg.yml
```

Then edit `inventory/stg.yml` in order to build your inventory.

## 4. Setup your login

On every your managed node (&quot;hosts&quot;), do the following steps:

- Create the user described in `ansible_user`.
- Configure `/etc/sudoers` in order that the user can run sudo without typing password.
- Add your SSH public key to the user's `~/.ssh/authorized_keys` in order that you can login to the node without typing  password.

## 5. (Optional) Cache the passphrase of your SSH key

If your SSH key has a passphrase, you can cache it in the following way:

```
$ eval `ssh-agent`
$ ssh-add ~/.ssh/id_your_ssh_key
```

## 6. Test your SSH connection to the managed nodes

```
$ ansible -i inventory/stg.yml -e ansible_python_interpreter=/usr/bin/python3 -m ping all
```

## 7. Setup a virtualenv on every managed node

The virtualenv will be used by Ansible.

```
$ ansible-playbook -i inventory/stg.yml -e ansible_python_interpreter=/usr/bin/python3 site-common-setup-python-venv.yml
$ ansible -i inventory/stg.yml -m ping all
```

## 8. Edit and confirm variables

See **vars-stg.yml** and edit values if you need.

## 9. Run the root playbook to install AICP Numaflow PoC

```
$ ansible-playbook -i inventory/stg.yml -e @vars-stg.yml site-stg-dci-poc.yml
```

Re-run the command until the results have no &quot;changed&quot;.

That's all.
