import os
import subprocess

vm_whitelist = []
container_whitelist = ['ddvevhds', 'templates']
vhd_whitelist = ['AVE-7.4.1.56-disk1.vhd', 'AVE-7.4.0.242-disk1.vhd']

def execute_sync(cmd, out=None, err=None, std_in=None, **kargs):
    """
    execute command and wait for complete. Blocking other functions while subprocess is not terminated
    if cmd is a single string following bash format, shell=True must be set. See subprocess.Popen() for details.
    """
    if out is None:
        out = subprocess.PIPE
    if err is None:
        err = subprocess.PIPE
    try:
        p = subprocess.Popen(cmd, stdout=out, stderr=err, stdin=std_in, **kargs)
        while p.returncode is None:
             p.poll()
        return p
    except Exception as e:
        raise SystemError(e)

# delete unused nics
def delete_unused_nics(resource_group):
    # Fist list all available nics
    cmd = "/usr/bin/python azure_operations.py list nic -r {} | grep 'Available'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        # format: vnet/subnet/nic: ip : status
        # cc-azure/cc-priv-1/test35: 10.13.145.92 :  Available
        for line in p.stdout.readlines():
            available_nic_infos = line.split(':')
            available_nic_info = available_nic_infos[0].split('/')
            available_nic = available_nic_info[2].strip()
            # delete the nic
            cmd = "/usr/bin/python azure_operations.py delete nic -r {} -n {}".format(resource_group, available_nic)
            _p = execute_sync(cmd, shell=True)
            if _p.returncode == 0:
                print 'Successfully delete NIC {}'.format(available_nic)
            else:
                print 'Failed to delete NIC {}: {}'.format(available_nic_info[0], _p.stderr.readlines())
    else:
        raise SystemError('Fail to get NIC info.')

def read_2_lines(fd):
    while True:
        line1 = fd.readline()
        if not line1:
            break
        line2 = fd.readline()
        if not line2:
            break
        yield (line1, line2)

def delete_unused_vms(resource_group):
    cmd = "/usr/bin/python azure_operations.py list vm -r {} | egrep 'VM Name|VM Status'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        # VM Name : zrs00
        # VM Status : VM running
        for vm_info in read_2_lines(p.stdout): 
            vm_name = vm_info[0].split(':')[1].strip()
            vm_state = vm_info[1].split(':')[1].strip()
            if 'running' not in vm_state and vm_name not in vm_whitelist and 'longrun' not in vm_name.lower():
                print 'Deleting VM {}'.format(vm_name)
                cmd = "/usr/bin/python azure_operations.py delete vm -r {} -n {}".format(resource_group, vm_name)
                _p = execute_sync(cmd, shell=True)
                if _p.returncode == 0:
                    print 'VM {} successfully deleted.'.format(vm_name)
                else:
                    raise SystemError('Failed to delete VM {}: {}'.format(vm_name, _p.stderr.readlines()))
    else:
        raise SystemError('Fail to get VM info.')

def delete_unused_vhds_per_container(resource_group, storage_account, container):
    cmd = "/usr/bin/python azure_operations.py list vhd -r {} -s {} -c {}".format(resource_group, storage_account, container)
    _p = execute_sync(cmd, shell=True)
    if _p.returncode == 0:
        # ddvestg/vhds/sushilwin220170301153720.vhd: unlocked/available
        for line in _p.stdout.readlines():
            vhd_info = line.split(':')[0]
            vhd_name = vhd_info.split('/')[2].strip()
            if vhd_name in vhd_whitelist:
                print 'vhd {} is neglected'.format(vhd_name)
                continue
            vhd_state = line.split(':')[1].strip()
            if vhd_state == 'unlocked/available':
                cmd = "/usr/bin/python azure_operations.py delete vhd -r {} -s {} -c {} -n {}".format(resource_group, storage_account, container, vhd_name)
                print 'Deleting vhd {}/{}/{}'.format(storage_account, container, vhd_name)
                _p = execute_sync(cmd, shell=True)
    else:
        raise SystemError('Failed to get vhd info.')


def delete_unused_vhds_per_sa(resource_group, storage_account):
    cmd = "/usr/bin/python azure_operations.py list container -r {} -s {}".format(resource_group, storage_account)
    _p = execute_sync(cmd, shell=True)
    if _p.returncode == 0:
        for container in _p.stdout.readlines():
            container = container.strip()
            if 'bootdiagnostics-' in container:
                cmd = "/usr/bin/python azure_operations.py delete container -r {} -s {} -n {}".format(resource_group, storage_account, container)
                print 'Deleting storage container {}'.format(container)
                _p = execute_sync(cmd, shell=True)
            elif container in container_whitelist:
                print '{}/{} neglected.'.format(storage_account, container)
                continue
            else:
                delete_unused_vhds_per_container(resource_group, storage_account, container)
    else:
            raise SystemError('Failed to get storage container info.')

def delete_unused_vhds(resource_group):
    cmd = "/usr/bin/python azure_operations.py list storage_account -r {} | grep 'Name'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for sa_info in p.stdout.readlines():
            sa_name = sa_info.split(':')[1].strip()
            delete_unused_vhds_per_sa(resource_group, sa_name)
    else:
        raise SystemError('Failed to get storage account info.')


if __name__ == '__main__':
    resource_group = 'ddve-dev-rg'
    delete_unused_vms(resource_group)
    delete_unused_nics(resource_group)
    # delete_unused_vhds(resource_group)

