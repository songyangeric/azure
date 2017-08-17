import sys, os, subprocess, re, argparse, logging

vm_whitelist = []
container_whitelist = ['ddvevhds', 'templates']
vhd_whitelist = ['AVE-7.4.1.56-disk1.vhd', 'AVE-7.4.0.242-disk1.vhd', 'AVE-7.5.0.183-disk1.vhd', 'AVE-7.4.1.56-disk1.vhd']

# set logging level
logger = logging.getLogger('Logging')
logger.setLevel(logging.INFO)
# stream handler
sh = logging.StreamHandler(stream = sys.stdout)
sh.setFormatter(logging.Formatter(fmt = '%(message)s'))
logger.addHandler(sh)

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
                logger.info('NIC {} successfully deleted.'.format(available_nic))
            else:
                logger.error('Failed to delete NIC {}: {}'.format(available_nic_info[0], _p.stderr.readlines()))

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
            if 'running' not in vm_state and vm_name not in vm_whitelist and 'longrun' not in vm_name.lower() and '-lr' not in vm_name.lower():
                cmd = "/usr/bin/python azure_operations.py delete vm -r {} -n {}".format(resource_group, vm_name)
                _p = execute_sync(cmd, shell=True)
                if _p.returncode == 0:
                    logger.info('VM {} successfully deleted.'.format(vm_name))
                else:
                    logger.error('Failed to delete VM {}: {}'.format(vm_name, _p.stderr.readlines()))

def delete_unused_container_per_sa(resource_group, storage_account):
    cmd = "/usr/bin/python azure_operations.py list container -r {} -s {}".format(resource_group, storage_account)
    _p = execute_sync(cmd, shell=True)
    if _p.returncode == 0:
        for container in _p.stdout.readlines():
            container = container.strip()
            if 'bootdiagnostics-' in container:
                cmd = "/usr/bin/python azure_operations.py delete container -r {} -s {} -n {}".format(resource_group, storage_account, container)
                _p = execute_sync(cmd, shell=True)
                if _p.returncode == 0:
                    logger.info('Storage container {} successfully deleted.'.format(container))

def delete_unused_vhds(resource_group):
    cmd = "/usr/bin/python azure_operations.py list storage_account -r {} | grep 'Name'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for sa_info in p.stdout.readlines():
            sa_name = sa_info.split(':')[1].strip()
            delete_unused_container_per_sa(resource_group, sa_name)
    
    cmd = "/usr/bin/python azure_operations.py list vhd -r {} | grep 'unlocked/available'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for disk_info in p.stdout.readlines():
            disk_uri = disk_info.split(':')[0].strip()
            disk_path = disk_uri.split('/')
            if len(disk_path) == 1:
                sa_name = None 
                container = None 
                disk_name = disk_path[0]
            else:
                sa_name = disk_path[0]
                container = disk_path[1]
                disk_name = disk_path[2]
            delete_unused_vhd(resource_group, sa_name, container, disk_name)

def delete_unused_vhd(resource_group, storage_account, container, disk_name):
    if not storage_account and not container:
        # delete managed disks
        cmd = "/usr/bin/python azure_operations.py delete blob -r {} -n {} --managed_disk".format(resource_group, disk_name)
        p = execute_sync(cmd, shell=True)
        if p.returncode != 0:
            logger.error('Failed to delete vhd {} : {}'.format(disk_name, p.stderr.readlines()))
        else:
            logger.info('Managed disk {} successfully deleted.'.format(disk_name))
    else:
        # delete unmanaged disks
        if disk_name in vhd_whitelist or container in container_whitelist:
            return
        cmd = "/usr/bin/python azure_operations.py delete blob -r {} -s {} -c {} -n {}".format(resource_group, storage_account, container, disk_name)
        p = execute_sync(cmd, shell=True)
        if p.returncode != 0:
            logger.error('Failed to delete vhd {} : {}'.format(disk_name, p.stderr.readlines()))
        else:
            logger.info('Unmanaged disk {} successfully deleted.'.format(disk_name))

def delete_unused_public_ips(resource_group):
    cmd = "/usr/bin/python azure_operations.py list public_ip -r {} | grep 'None'".format(resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for ip_info in p.stdout.readlines():
            public_ip_name = ip_info.split(':')[0].strip()
            cmd = "/usr/bin/python azure_operations.py delete public_ip -r {} -n {}".format(resource_group, public_ip_name)
            _p = execute_sync(cmd, shell=True)
            if _p.returncode != 0:
                logger.error('Failed to delete public ip {} : {}'.format(public_ip_name, p.stderr.readlines()))
            else:
                logger.info('Public ip {} successfully deleted.'.format(public_ip_name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--resource_group', required = True, help='delete resources from this group')
    parsed_args = parser.parse_args()

    #delete_unused_vms(parsed_args.resource_group)
    delete_unused_nics(parsed_args.resource_group)
    #delete_unused_vhds(parsed_args.resource_group)
    delete_unused_public_ips(parsed_args.resource_group)
    

