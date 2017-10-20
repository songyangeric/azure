import sys, os, subprocess, re, argparse, logging
from azure.mgmt.resource import SubscriptionClient

# check whether azure_operations.py exist
module_path = os.path.realpath(__file__)
module_dir = os.path.dirname(module_path)
azure_module_path = '{}/azure_operations.py'.format(module_dir)
if not os.path.exists(azure_module_path):
    raise SystemError('No azure_operations.py found')

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
def delete_unused_nics(resource_group, delete = False):
    # Fist list all available nics
    cmd = "/usr/bin/python {} list nic -r {} | grep 'Available'".format(azure_module_path, resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        # format: vnet/subnet/nic: ip : status
        # cc-azure/cc-priv-1/test35: 10.13.145.92 :  Available
        for line in p.stdout.readlines():
            available_nic_infos = line.split(':')
            available_nic_info = available_nic_infos[0].split('/')
            available_nic = available_nic_info[2].strip()
            # delete the nic
            if delete:
                cmd = "/usr/bin/python {} delete nic -r {} -n {}".format(azure_module_path, resource_group, available_nic)
                _p = execute_sync(cmd, shell=True)
                if _p.returncode == 0:
                    logger.info('NIC {} successfully deleted.'.format(available_nic))
                else:
                    logger.error('Failed to delete NIC {}: {}'.format(available_nic_info[0], _p.stderr.readlines()))
            else:
                logger.info('Unused NIC: {}'.format(available_nic))

def read_2_lines(fd):
    while True:
        line1 = fd.readline()
        if not line1:
            break
        line2 = fd.readline()
        if not line2:
            break
        yield (line1, line2)

def delete_unused_vms(resource_group, delete = False):
    cmd = "/usr/bin/python {} list vm -r {} | egrep 'VM Name|VM Status'".format(azure_module_path, resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        # VM Name : zrs00
        # VM Status : VM running
        for vm_info in read_2_lines(p.stdout): 
            vm_name = vm_info[0].split(':')[1].strip()
            vm_state = vm_info[1].split(':')[1].strip()
            if 'running' not in vm_state and vm_name not in vm_whitelist and 'longrun' not in vm_name.lower() and '-lr' not in vm_name.lower():
                if delete:
                    cmd = "/usr/bin/python {} delete vm -r {} -n {}".format(azure_module_path, resource_group, vm_name)
                    _p = execute_sync(cmd, shell=True)
                    if _p.returncode == 0:
                        logger.info('VM {} successfully deleted.'.format(vm_name))
                    else:
                        logger.error('Failed to delete VM {}: {}'.format(vm_name, _p.stderr.readlines()))
                else:
                    logger.info('Unused VM: {}'.format(vm_name))

def delete_unused_vhds(resource_group, delete = False):
    cmd = "/usr/bin/python {} list vhd -r {} --managed | grep 'unlocked/available'".format(azure_module_path, resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for disk_info in p.stdout.readlines():
            disk_name = disk_info.split(':')[0].strip()
            if delete:
                delete_unused_vhd(resource_group, None, None, disk_name, delete)
            else:
                logger.info('Unused Disk: {}'.format(disk_name))
    
    cmd = "/usr/bin/python {} list storage_account -r {} | egrep 'Name|Kind'".format(azure_module_path, resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for sa_info in read_2_lines(p.stdout):
            sa_name = sa_info[0].split(':')[1].strip()
            sa_type = sa_info[1].split(':')[1].strip()
            #logger.info('{}:{}'.format(sa_name,sa_type))
            # ignore 'praveenltr' for a workaround
            if sa_type == 'blob_storage':
                continue
    
            cmd = "/usr/bin/python {} list container -s {}".format(azure_module_path, sa_name)
            p = execute_sync(cmd, shell=True)
            for container_info in p.stdout.readlines():
                container_info = container_info.strip()
                if re.search('[0-9a-z]{16}-[0-9a-z]{16}-[cdm]0', container_info):
                    logger.error('Wrong Usage: {}/{}'.format(sa_name, container_info))
                    if delete:
                        cmd = "/usr/bin/python {} delete container -s {} -n {}".format(azure_module_path, sa_name, container_info)
                        _p = execute_sync(cmd, shell=True)
                        if _p.returncode == 0:
                            logger.info('Storage container {} successfully deleted.'.format(container_info))
                elif 'bootdiagnostics-' in container_info:
                    if delete:
                        cmd = "/usr/bin/python {} delete container -s {} -n {}".format(azure_module_path, sa_name, container_info)
                        _p = execute_sync(cmd, shell=True)
                        if _p.returncode == 0:
                            logger.info('Storage container {} successfully deleted.'.format(container_info))
                    else:
                        logger.info('Unused Container: {}/{}'.format(sa_name, container_info))
                else:
                    cmd = "/usr/bin/python {} list vhd -s {} -c {} | grep 'unlocked/available'".format(azure_module_path, sa_name, container_info)
                    _p = execute_sync(cmd, shell=True)
                    if _p.returncode == 0:
                        for disk_info in p.stdout.readlines():
                            disk_uri = disk_info.split(':')[0].strip()
                            disk_path = disk_uri.split('/')
                            disk_name = disk_path[2]
                            if delete:
                                delete_unused_vhd(resource_group, sa_name, container_info, disk_name, delete)
                            else: 
                                logger.info('Unused VHD: {}/{}/{}'.format(sa_name, container_info, disk_name))

def delete_unused_vhd(resource_group, storage_account, container, disk_name, delete = False):
    if not storage_account and not container:
        # delete managed disks
        if not delete:
            return
        cmd = "/usr/bin/python {} delete blob -r {} -n {} --managed_disk".format(azure_module_path, resource_group, disk_name)
        p = execute_sync(cmd, shell=True)
        if p.returncode != 0:
            logger.error('Failed to delete vhd {} : {}'.format(disk_name, p.stderr.readlines()))
        else:
            logger.info('Managed disk {} successfully deleted.'.format(disk_name))
    else:
        # delete unmanaged disks
        if disk_name in vhd_whitelist or container in container_whitelist:
            return
        if not delete:
            logger.info('Unused VHD: {}/{}/{}'.format(storage_account, container, disk_name))
            return
        cmd = "/usr/bin/python {} delete blob -r {} -s {} -c {} -n {}".format(azure_module_path, resource_group, storage_account, container, disk_name)
        p = execute_sync(cmd, shell=True)
        if p.returncode != 0:
            logger.error('Failed to delete vhd {} : {}'.format(disk_name, p.stderr.readlines()))
        else:
            logger.info('Unmanaged disk {} successfully deleted.'.format(disk_name))

def delete_unused_public_ips(resource_group, delete = False):
    cmd = "/usr/bin/python {} list public_ip -r {} | grep 'None'".format(azure_module_path, resource_group)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for ip_info in p.stdout.readlines():
            public_ip_name = ip_info.split(':')[0].strip()
            if delete:
                cmd = "/usr/bin/python {} delete public_ip -r {} -n {}".format(azure_module_path, resource_group, public_ip_name)
                _p = execute_sync(cmd, shell=True)
                if _p.returncode != 0:
                    logger.error('Failed to delete public ip {} : {}'.format(public_ip_name, p.stderr.readlines()))
                else:
                    logger.info('Public ip {} successfully deleted.'.format(public_ip_name))
            else:
                logger.info('Unused public ip: {}'.format(public_ip_name))


def delete_unused_resources(subscription, resource_group = None, delete = False):
    if not resource_group:
        cmd = "/usr/bin/python {} list resource_group | grep 'Name'".format(azure_module_path)
        p = execute_sync(cmd, shell=True)
        for rg_info in p.stdout.readlines():
            rg_name = rg_info.split(':')[1].strip()
            # list unused vms
            delete_unused_vms(rg_name, delete)
            # list unused vhds
            delete_unused_vhds(rg_name, delete)
            # list unused nics
            delete_unused_nics(rg_name, delete)
            # list unused public ips
            delete_unused_public_ips(rg_name, delete)
    else:
        # list unused vms
        delete_unused_vms(resource_group, delete)
        # list unused vhds
        delete_unused_vhds(resource_group, delete)
        # list unused nics
        delete_unused_nics(resource_group, delete)
        # list unused public ips
        delete_unused_public_ips(resource_group, delete)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-S', '--subscription', help='delete resources from this subscription')
    parser.add_argument('-r', '--resource_group', help='delete resources from this group')
    parser.add_argument('--delete', action='store_true', help='delete resources from this group')
    parsed_args = parser.parse_args()

    subscription_map = {}
    cmd = "/usr/bin/python {} list subscription".format(azure_module_path)
    p = execute_sync(cmd, shell=True)
    if p.returncode == 0:
        for sub_info in read_2_lines(p.stdout): 
            sub_name = sub_info[0].split(':')[1].strip()
            sub_id = sub_info[1].split(':')[1].strip()
            subscription_map[sub_id] = sub_name
    
    if not parsed_args.subscription:
            for (sub_id, sub_name) in subscription_map.items(): 
                os.environ['AZURE_SUBSCRIPTION_ID'] = sub_id
                logger.info('')
                logger.info('Subscription: {} - {}'.format(sub_id, sub_name))
                delete_unused_resources(sub_id, parsed_args.resource_group, parsed_args.delete)
    else:
        os.environ['AZURE_SUBSCRIPTION_ID'] = parsed_args.subscription
        logger.info('Subscription: {} - {}'.format(parsed_args.subscription, subscription_map[parsed_args.subscription]))
        delete_unused_resources(parsed_args.subscription, parsed_args.resource_group, parsed_args.delete) 


