import sys, os, subprocess, re, argparse, logging

# check whether azure_operations.py exist
module_path = os.path.realpath(__file__)
module_dir = os.path.dirname(module_path)
azure_module_path = '{}/azure_operations.py'.format(module_dir)
if not os.path.exists(azure_module_path):
    raise SystemError('No azure_operations.py found')

from azure_operations import *

vm_whitelist = []
container_whitelist = ['ddvevhds', 'templates', 'ddveimgs']
#container_whitelist = []
vhd_whitelist = ['AVE-7.4.0.242-disk1.vhd', 'AVE-7.5.0.183-disk1.vhd', 'AVE-7.4.1.56-disk1.vhd']


# set logging level
logger = logging.getLogger('Logging')
logger.setLevel(logging.INFO)
# stream handler
# sh = logging.StreamHandler(stream = sys.stdout)
# sh.setFormatter(logging.Formatter(fmt = '%(message)s'))
# logger.addHandler(sh)

class delete_op:
    def __init__(self):
        self.azure_ops = azure_operations(client_id = os.environ['AZURE_CLIENT_ID'],
                secret_key = os.environ['AZURE_SECRET_KEY'],
                tenant_id = os.environ['AZURE_TENANT_ID'])

    # delete unused nics
    def delete_unused_nics(self, resource_group, delete = False):
        
        for nic in self.azure_ops.network_client.network_interfaces.list(resource_group):
            name = nic.name
            attached_vm = nic.virtual_machine
            if not attached_vm:
                if not delete:
                    logger.info('Unused NIC: {}'.format(name))
                else:
                    self.azure_ops.delete_nic(resource_group, name)
                    logger.info('NIC {} successfully deleted.'.format(name))
    
    def delete_unused_vms(self, resource_group, delete = False):
        
        for vm_ref in self.azure_ops.compute_client.virtual_machines.list(resource_group):
            vm = self.azure_ops.get_vm(resource_group, vm_ref.name)

            state = vm.instance_view.statuses[0].display_status
            # VM may not be successfully deployed in below case
            if state == 'Provisioning succeeded':
                state = vm.instance_view.statuses[1].display_status

            if 'running' in state:
                continue
            if '-lr' in vm.name or '-longrun' in vm.name:
                continue
            if vm.name in vm_whitelist:
                continue

            if not delete:
                logger.info('Unused VM: {}'.format(vm.name))
            else:
                self.azure_ops.delete_vm(resource_group, vm.name)
                logger.info('VM {} successfully deleted.'.format(vm.name))
    
    def delete_unused_vhds(self, resource_group, delete = False):

        # managed disks
        for managed_disk_ref in self.azure_ops.compute_client.disks.list_by_resource_group(resource_group):
            disk_name = managed_disk_ref.name
            logger.debug(disk_name)
            if managed_disk_ref.managed_by:
                continue
            if not delete:
                logger.info('Unused Disk: {}'.format(disk_name))
            else:
                self.azure_ops.compute_client.disks.delete(resource_group, disk_name)
                logger.info('Managed disk {} successfully deleted.'.format(disk_name))

        # unmanaged disks
        # hierarchy: storage account/container/vhd
        storage_accounts = self.azure_ops.storage_client.storage_accounts.list_by_resource_group(resource_group)
        for storage_account in storage_accounts:
            if storage_account.kind == Kind.blob_storage:
                logger.debug('Listing VHD operations will neglect Blob storage account {}.'.format(storage_account.name))
                continue

            # get storage account keys
            storage_account_keys = self.azure_ops.storage_client.storage_accounts.list_keys(resource_group, storage_account.name)
            storage_account_keys_map = {v.key_name: v.value for v in storage_account_keys.keys}
            storage_account_primary_key = storage_account_keys_map['key1']

            blob_service = BaseBlobService(account_name = storage_account.name ,account_key = storage_account_primary_key)
            for container_ref in blob_service.list_containers():
                container = container_ref.name
                if container in container_whitelist:
                    continue
                elif re.search('[0-9a-z]{16}-[0-9a-z]{16}-[cdm]0', container):
                    if delete:
                        blob_service.delete_container(container_name = container)
                        logger.info('Storage container {} successfully deleted.'.format(container))
                    else:
                        logger.error('Wrong Usage: {}/{}'.format(storage_account.name, container))
                elif 'bootdiagnostics-' in container:
                    if delete:
                        blob_service.delete_container(container_name = container)
                        logger.info('Storage container {} successfully deleted.'.format(container))
                    else:
                        logger.info('Unused Container: {}/{}'.format(storage_account.name, container))
                else:
                    blobs = blob_service.list_blobs(container_name = container)
                    for blob in blobs:
                        if re.search(r'\.vhd', blob.name):
                            if blob.properties.lease.status == 'unlocked' and blob.properties.lease.state == 'available':
                                if blob.name in vhd_whitelist:
                                    continue
                                if delete:
                                    delete_ops.azure_ops.delete_blob(resource_group, storage_account.name, container, blob.name)
                                    logger.info('Unmanaged disk {} successfully deleted.'.format(disk_name))
                                else:
                                    logger.info('Unused VHD: {}/{}/{}'.format(storage_account.name, container, blob.name))

    def delete_unused_public_ips(self, resource_group, delete = False):

        for public_ip in self.azure_ops.network_client.public_ip_addresses.list(resource_group):
            public_ip_name = public_ip.id.split('/')[-1]
            public_ip_addr = public_ip.ip_address
            if public_ip_addr:
                continue
            if not delete:
                logger.info('Unused public ip: {}'.format(public_ip_name))
            else:
                self.azure_ops.delete_public_ip(resource_group, public_ip_name)
                logger.info('Public ip {} successfully deleted.'.format(public_ip_name))
    
    def delete_unused_resources(self, resource_group = None, delete = False):
        if not resource_group:
            for resource_group in self.azure_ops.resource_client.resource_groups.list():
                rg_name = resource_group.name
                
                # list unused vms
                self.delete_unused_vms(rg_name, delete)
                # list unused vhds
                self.delete_unused_vhds(rg_name, delete)
                # list unused nics
                self.delete_unused_nics(rg_name, delete)
                # list unused public ips
                self.delete_unused_public_ips(rg_name, delete)

                logger.info('')
        else:
            # list unused vms
            self.delete_unused_vms(resource_group, delete)
            # list unused vhds
            self.delete_unused_vhds(resource_group, delete)
            # list unused nics
            self.delete_unused_nics(resource_group, delete)
            # list unused public ips
            self.delete_unused_public_ips(resource_group, delete)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-S', '--subscription', help='delete resources from this subscription')
    parser.add_argument('-r', '--resource_group', help='delete resources from this group')
    parser.add_argument('--delete', action='store_true', help='delete resources from this group')
    parsed_args = parser.parse_args()

    # First check whether environmental variables are set
    try:
        os.environ['AZURE_CLIENT_ID']
        os.environ['AZURE_SECRET_KEY']
        os.environ['AZURE_TENANT_ID']
    except:
        raise SystemError("Please set environmental variables for Service Principal first.")

    delete_ops = delete_op()
    # Get all subscriptions
    subscription_map = {}
    for subscription in delete_ops.azure_ops.subscription_client.subscriptions.list():
        subscription_map[subscription.subscription_id] = subscription.display_name

    if not parsed_args.subscription:
        for (sub_id, sub_name) in subscription_map.items(): 
            # Subscription for Azure Marketplace 
            if str(sub_id) == '1919bdd0-d66c-4699-8c08-a134883a985a':
                continue
            os.environ['AZURE_SUBSCRIPTION_ID'] = str(sub_id)
            logger.info('')
            logger.info('Subscription: {} - {}'.format(sub_id, sub_name))
            delete_ops.azure_ops.init_clients(str(sub_id))
            delete_ops.delete_unused_resources(parsed_args.resource_group, parsed_args.delete)
    else:
        os.environ['AZURE_SUBSCRIPTION_ID'] = parsed_args.subscription
        logger.info('Subscription: {} - {}'.format(parsed_args.subscription, subscription_map[parsed_args.subscription]))
        delete_ops.azure_ops.init_clients(parsed_args.subscription)
        delete_ops.delete_unused_resources(parsed_args.resource_group, parsed_args.delete)
