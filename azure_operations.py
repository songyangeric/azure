import sys, os, argparse, json, re, logging
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute.models import Plan, HardwareProfile, SshConfiguration, VirtualMachineSize
from azure.mgmt.compute.models import SshPublicKey, LinuxConfiguration, OSProfile, ImageReference 
from azure.mgmt.compute.models import VirtualHardDisk, OSDisk, DataDisk, StorageProfile, ManagedDiskParameters 
from azure.mgmt.compute.models import DiskCreateOption, NetworkInterfaceReference, NetworkProfile
from azure.mgmt.compute.models import BootDiagnostics, DiagnosticsProfile, VirtualMachine 
from azure.mgmt.network.models import PublicIPAddress 
from azure.mgmt.storage.models import Kind, Sku, StorageAccountCreateParameters
from azure.storage.blob.baseblobservice import BaseBlobService

# set logging level
logger = logging.getLogger('Logging')
logger.setLevel(logging.INFO)
# stream handler
sh = logging.StreamHandler(stream = sys.stdout)
sh.setFormatter(logging.Formatter(fmt = '%(message)s'))
logger.addHandler(sh)

# VM size and capacity mapping
supported_vm_sizes = {
    '7T' : 'Standard_F4',
    '8T' : 'Standard_F4',
    '15T' : 'Standard_F8',
    '16T' : 'Standard_F8',
    '32T' : 'Standard_D4_v2',
    '96T' : 'Standard_D14_v2'
}

# storage account types
account_types = ['Storage', 'BlobStorage']
replication_types = ['Standard_LRS', 'Standard_GRS', 'Standard_RAGRS', 
        'Standard_ZRS', 'Premium_LRS']
access_tiers = ['Hot', 'Cool']

class azure_operations:
    def __init__(self, client_id, secret_key, tenant_id, subscription_id):
        if client_id and secret_key and tenant_id and subscription_id:
            self.client_id = client_id
            self.secret_key = secret_key
            self.tenant_id = tenant_id
            self.subscription_id = subscription_id
        else:
            try:
                self.client_id = os.environ['AZURE_CLIENT_ID'] 
                self.secret_key = os.environ['AZURE_SECRET_KEY'] 
                self.tenant_id = os.environ['AZURE_TENANT_ID']
                self.subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
            except Exception:
                raise ValueError('Please set client_id and tenant_id and secret_key and sucscription_id')
        
        # initialize resouce and storage management object
        try:
            credentials = ServicePrincipalCredentials(
                    client_id = self.client_id, 
                    secret = self.secret_key, 
                    tenant = self.tenant_id
                    )
        except Exception as e:
            credentials = ServicePrincipalCredentials(
                    client_id = self.client_id, 
                    secret = self.secret_key, 
                    tenant = self.tenant_id,
                    china = True
                    )
            self.inChina = True

        if self.subscription_id is not None:
            self.subscription_client = SubscriptionClient(credentials)
            self.resource_client = ResourceManagementClient(credentials, self.subscription_id)
            self.storage_client = StorageManagementClient(credentials, self.subscription_id)
            self.compute_client = ComputeManagementClient(credentials, self.subscription_id)
            self.network_client = NetworkManagementClient(credentials, self.subscription_id)
        else:
            raise ValueError('No subscription specified, please check or create a new one') 


    def print_storage_account_info(self, sa):
        logger.info('')
        logger.info('\tName: {}'.format(sa.name))
        kind = str(sa.kind)
        kind = kind.split('.')[1]
        logger.info('\tKind: {}'.format(kind))
        replication = str(sa.sku.name).split('.')[1] 
        logger.info('\tReplication: {}'.format(replication))
        logger.info('\tLocation: {}'.format(sa.location))

    def list_resource_groups(self):
        for rg in self.resource_client.resource_groups.list():
            logger.info('') 
            logger.info('\tName: {}'.format(rg.name))
            logger.info('\tLocation: {}'.format(rg.location))
    
    def list_subscriptions(self):
        for subscription in self.subscription_client.subscriptions.list():
            logger.info('\tName: {}'.format(subscription.display_name))
            logger.info('\tID: {}'.format(subscription.subscription_id))

    def create_resource_group(self, rg_name, location):
        async_create = self.resource_client.resource_groups.create_or_update(
                rg_name,
                {
                    'location' : location
                }
             )

    def delete_resource_group(self, resource_group):
        delete_rg = self.resource_client.resource_groups.delete(resource_group)
        delete_rg.wait()

    def list_storage_accounts(self, resource_group = None):
        if resource_group:
            for sa in self.storage_client.storage_accounts.list_by_resource_group(resource_group):
                self.print_storage_account_info(sa)
        else:
            for sa in self.storage_client.storage_accounts.list():
                self.print_storage_account_info(sa)

    def storage_account_within_resource_group(self, resource_group, storage_account):
        for sa in self.storage_client.storage_accounts.list_by_resource_group(resource_group):
            if sa.name == storage_account:
                return True
        return False

    def create_storage_account(self, resource_group, sa_name, account_kind = None, replication_type = None, access_tier = None):
        if account_kind is None:
            account_kind = 'Storage'
        elif account_kind not in account_types:
            raise ValueError('Invalid account kind, choose between Storage and BlobStorage')

        if replication_type is None:
            replication_type = 'Standard_LRS'
        elif replication_type not in replication_types:
            raise ValueError('Invalid replication type.')
        
        if account_kind == 'BlobStorage':
            if replication_type not in ['Standard_LRS', 'Standard_RAGRS']:
                raise ValueError('Blob storage only supports Standard_LRS or Standard_RAGRS')
            if not access_tier:
                access_tier = 'Hot'
            if access_tier not in access_tiers:
                raise ValueError('Access tier must be Hot or Cool')
        else:
            access_tier = None
        
        rg_ref = self.resource_client.resource_groups.get(resource_group)
        if rg_ref is None:
            raise ValueError('The specified resource group {} dose not exist.'.format(resource_group))
        location = rg_ref.location
        
        # check account name availability
        valid_name = self.storage_client.storage_accounts.check_name_availability(sa_name)
        if not valid_name.name_available:
            raise ValueError(valid_name.message)

        param = StorageAccountCreateParameters(sku = Sku(replication_type), kind = account_kind, location = location, access_tier = access_tier)  
        async_sa_create = self.storage_client.storage_accounts.create(resource_group, sa_name, param)
        async_sa_create.wait()

    def delete_storage_account(self, resource_group, sa_name):
        async_sa_delete = self.storage_client.storage_accounts.delete(
                              resource_group,
                              sa_name
                          )

    def get_resource_group_by_storage_account(self, storage_account):
        for sa in self.storage_client.storage_accounts.list():
            if sa.name == storage_account:
                return sa.id.split('/')[4]

    def list_storage_account_primary_key(self, storage_account, resource_group = None):
        if not resource_group:
            resource_group = self.get_resource_group_by_storage_account(storage_account)
        storage_account_keys = self.storage_client.storage_accounts.list_keys(resource_group, storage_account)
        storage_account_keys_map = {v.key_name: v.value for v in storage_account_keys.keys}
        storage_account_primary_key = storage_account_keys_map['key1']
        
        return storage_account_primary_key

    def create_storage_container(self, storage_account, container, resource_group = None):
        if re.search(r'[^-0-9a-z]', container) is not None: 
            raise ValueError('Invalid container name. Only '-', small letters and digits are allowed.')

        account_key = self.list_storage_account_primary_key(storage_account, resource_group)

        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        create_container = blob_service.create_container(container_name = container)

    def list_storage_container(self, storage_account):
        account_key = self.list_storage_account_primary_key(storage_account)

        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        containers = blob_service.list_containers()
        for container in containers:
            logger.info(container.name)

    def list_vhd_per_container(self, blob_service, storage_account, container):
        blobs = blob_service.list_blobs(container_name = container)
        for blob in blobs:
            if re.search(r'\.vhd', blob.name):
                logger.info('{}/{}/{}: {}/{}'.format(storage_account, container, blob.name, 
                       blob.properties.lease.status, blob.properties.lease.state))

    def list_vhd_per_storage_account(self, resource_group, sa_ref, container):
        if sa_ref.kind == Kind.blob_storage:
            logger.debug('Listing VHD operations will neglect Blob storage account.')
            return

        account_key = self.list_storage_account_primary_key(sa_ref.name, resource_group)

        blob_service = BaseBlobService(account_name = sa_ref.name ,account_key = account_key)
        if container:
            self.list_vhd_per_container(blob_service, sa_ref.name, container)
        else:
            containers = blob_service.list_containers()
            for container in containers:
                self.list_vhd_per_container(blob_service, sa_ref.name, container.name)

    def list_vhds(self, resource_group, storage_account, container, managed = False):
        if resource_group:
            # list all managed disks under this resource group
            managed_disk_refs = self.compute_client.disks.list_by_resource_group(resource_group)
            for managed_disk_ref in managed_disk_refs:
                if managed_disk_ref.managed_by:
                    logger.info('{}: Attached to VM {}'.format(managed_disk_ref.name, 
                          managed_disk_ref.managed_by.split('/')[-1]))
                else:
                    logger.info('{}: unlocked/available'.format(managed_disk_ref.name))
            
            storage_accounts = self.storage_client.storage_accounts.list_by_resource_group(resource_group)
        else:
            storage_accounts = self.storage_client.storage_accounts.list()
        
        if not managed:
            if storage_account:
                for sa_ref in storage_accounts:
                    if storage_account == sa_ref.name:
                        resource_group = sa_ref.id.split('/')[4]
                        self.list_vhd_per_storage_account(resource_group, sa_ref, container)
            else:
                # list unmanaged disks under all storage accounts
                for sa_ref in storage_accounts:
                    resource_group = sa_ref.id.split('/')[4]
                    self.list_vhd_per_storage_account(resource_group, sa_ref, container)

    def print_vm_info(self, resource_group, vm_obj):
        logger.info('')
        logger.info('VM UUID : {}'.format(vm_obj.vm_id))
        logger.info('VM Name : {}'.format(vm_obj.name))
        logger.info('VM Location : {}'.format(vm_obj.location))
        logger.info('VM Size : {}'.format(vm_obj.hardware_profile.vm_size))
        
        vm_size_obj = self.get_vm_size(vm_obj.location, vm_obj.hardware_profile.vm_size)
        logger.info('CPU cores : {}'.format(vm_size_obj.number_of_cores))
        logger.info('Memory size : {} GB'.format(vm_size_obj.memory_in_mb/1024))

        self.list_vm_state(resource_group, vm_obj.name)
        self.list_vm_public_ip(resource_group, vm_obj.name)
        self.list_vm_private_ip(resource_group, vm_obj.name)
        # list disks
        os_disk_ref = vm_obj.storage_profile.os_disk
        if os_disk_ref:
            logger.info('VM OS Disk : ')
            if os_disk_ref.vhd:
                logger.info('  {}'.format(os_disk_ref.vhd.uri))
            if os_disk_ref.disk_size_gb:
                logger.info('  size : {} GiB'.format(os_disk_ref.disk_size_gb))
            elif os_disk_ref.vhd:
                disk_size_gb = self.get_disk_size(os_disk_ref.vhd.uri)
                logger.info('  size : {} GiB'.format(disk_size_gb))

        data_disk_refs = vm_obj.storage_profile.data_disks
        if data_disk_refs:
            logger.info('VM Data Disk : ')
            for data_disk_ref in data_disk_refs:
                logger.info('  lun : {}'.format(data_disk_ref.lun))
                if data_disk_ref.vhd:
                    logger.info('  {}'.format(data_disk_ref.vhd.uri))
                if data_disk_ref.disk_size_gb:
                    logger.info('  size : {} GiB'.format(data_disk_ref.disk_size_gb))
                elif data_disk_ref.vhd:
                    disk_size_gb = self.get_disk_size(data_disk_ref.vhd.uri)
                    logger.info('  size : {} GiB'.format(disk_size_gb))

    def list_virtual_machines(self, resource_group, vmname = None, status = None):
        if vmname is None:
            for vm in self.compute_client.virtual_machines.list(resource_group):
                self.print_vm_info(resource_group, vm)
        else:
            vm = self.get_vm(resource_group, vmname)
            self.print_vm_info(resource_group, vm)
    
    def list_vm_size(self, resource_group, vmname):
        vm = self.get_vm(resource_group, vmname)
        vm_size = vm.hardware_profile.vm_size
        vm_size_ref = self.get_vm_size(vm.location, vm_size)
        logger.info('VM Size : {}'.format(vm_size))
        logger.info('CPU cores : {}'.format(vm_size_ref.number_of_cores))
        logger.info('Memory size : {} GB'.format(vm_size_ref.memory_in_mb/1024))

    def list_vm_state(self, resource_group, vmname):
        vm = self.get_vm(resource_group, vmname)
        state = vm.instance_view.statuses[0].display_status
        # VM may not be successfully deployed in below case
        if state == 'Provisioning succeeded':
            state = vm.instance_view.statuses[1].display_status
        logger.info('VM Status : {}'.format(state))
        return state

    def get_vm(self, resource_group, vmname, expand = 'instanceview'):
        try:
            virtual_machine = self.compute_client.virtual_machines.get(
                                  resource_group,
                                  vmname,
                                  expand  
                              ) 
        except Exception as e:
            return None 
        
        return virtual_machine
    
    # Caution: a stopped vm still charges you; to avoid this, use deallocate_vm insead
    def stop_vm(self, resource_group, vmname):
        async_vm_stop = self.compute_client.virtual_machines.power_off(
                             resource_group,
                             vmname
                        )
        async_vm_stop.wait()

    def deallocate_vm(self, resource_group, vmname):
        async_vm_deallocate = self.compute_client.virtual_machines.deallocate(
                                  resource_group, 
                                  vmname
                              )
        async_vm_deallocate.wait()

    def start_vm(self, resource_group, vmname):
        async_vm_start = self.compute_client.virtual_machines.start(
                             resource_group,
                             vmname
                         )
        async_vm_start.wait()

    def restart_vm(self, resource_group, vmname):
        async_vm_restart = self.compute_client.virtual_machines.restart(
                               resource_group,
                               vmname
                           )
        async_vm_restart.wait()

    # for a full delte, even the data disks will be deleted
    def delete_vm(self, resource_group, vmname, keep_data = False):
        vm = self.get_vm(resource_group, vmname)
        if not vm:
            return

        # Get the list of network interfaces of the VM
        nics = vm.network_profile.network_interfaces

        # Get the storage info of the VM
        os_disk = vm.storage_profile.os_disk
        data_disks = vm.storage_profile.data_disks

        async_vm_delete = self.compute_client.virtual_machines.delete(
                              resource_group,
                              vmname
                          )
        async_vm_delete.wait()

        for nic in nics:
            nic_name = nic.id.split('/')[8]
            self.delete_nic(resource_group, nic_name)
        
        # Delete the OS disk
        # unmanaged disks
        managed_disk = False
        if os_disk.vhd: 
            os_disk_uri = os_disk.vhd.uri

            os_disk_container = os_disk_uri.split('/')[3]
            os_disk_blob_name = os_disk_uri.split('/')[4]
            os_disk_storage_account_name = os_disk_uri.split('/')[2].split('.')[0]
            managed_disk = False
        # managed disks
        else:
            os_disk_blob_name = os_disk.name
            os_disk_container = None
            os_disk_storage_account_name = None
            managed_disk = True 
        
        self.delete_blob(resource_group, os_disk_storage_account_name, os_disk_container, os_disk_blob_name, managed_disk)

        # Delete all the data disks
        if not keep_data:
            managed_disk = False
            for data_disk in data_disks:
                # unmanaged disk:
                if data_disk.vhd:
                    data_disk_uri = data_disk.vhd.uri
                    data_disk_container = data_disk_uri.split('/')[3]
                    data_disk_blob_name = data_disk_uri.split('/')[4]
                    data_disk_storage_account_name = data_disk_uri.split('/')[2].split('.')[0]
                    managed_disk = False
                # managed disks
                else:
                    data_disk_blob_name = data_disk.name
                    data_disk_container = None
                    data_disk_storage_account_name = None
                    managed_disk = True 
    
                self.delete_blob(resource_group, data_disk_storage_account_name, data_disk_container, data_disk_blob_name, managed_disk)
 
    def delete_container(self, storage_account, container):
        account_key = self.list_storage_account_primary_key(storage_account)
        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        blob_service.delete_container(container_name = container)

    def delete_blob(self, resource_group, storage_account, container, blob_name, managed_disk = False):
        if not managed_disk:
            account_key = self.list_storage_account_primary_key(storage_account)
            blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
            blob_service.delete_blob(container_name = container, blob_name = blob_name)
            
            remaining_blobs = blob_service.list_blobs(container_name = container)
            if len(list(remaining_blobs)) == 0:
                delete_container = blob_service.delete_container(container_name = container)
        else:
            self.compute_client.disks.delete(resource_group, blob_name)

    def get_disk_size(self, disk_uri):
        #https://ddvestg.blob.core.windows.net/aimee-atos-test-cbj3zksbhkgme-vhds/aimee-atos-test-20170809-105218.vhd
        disk_info = disk_uri.split('/')
        storage_account = disk_info[2].split('.')[0]
        container = disk_info[-2]
        disk_name = disk_info[-1]

        account_key = self.list_storage_account_primary_key(storage_account)
        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        disk_size = blob_service.get_blob_properties(container, disk_name).properties.content_length/1024/1024/1024

        return disk_size

    def list_data_disks(self, resource_group, vmname):
        virtual_machine = self.get_vm(resource_group, vmname)
        if virtual_machine is None:
            return
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [disk for disk in data_disks if 'nvram' not in disk.name.lower()]
        for disk in data_disks:
            logger.info('')
            logger.info('LUN : {}'.format(disk.lun))
            logger.info('Disk name : {}'.format(disk.name))
            if disk.vhd:
                logger.info('VHD : {}'.format(disk.vhd.uri))
            if disk.disk_size_gb:
                logger.info('Disk size : {} GiB'.format(disk.disk_size_gb))
            else:
                disk_size_gb = self.get_disk_size(resource_group, disk.vhd.uri) 
                logger.info('Disk size : {} GiB'.format(disk_size_gb))

    def detach_data_disk(self, resource_group, vmname, disk_name):
        virtual_machine = self.get_vm(resource_group, vmname)
        if virtual_machine is None:
            return
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [disk for disk in data_disks if disk.name != disk_name]
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
                              resource_group,
                              vmname,
                              virtual_machine
                          )
        async_vm_update.wait()

    def print_vnet_info(self, vnet_obj):
         logger.info('')
         logger.info('Name : {}'.format(vnet_obj.name))
         logger.info('Location : {}'.format(vnet_obj.location))
         logger.info('AddressSpace : {}'.format(''.join(vnet_obj.address_space.address_prefixes)))

    def list_virtual_networks(self, resource_group = None, vnet_name = None):
        if resource_group:
            if vnet_name:
                try:
                    vnet = self.network_client.virtual_networks.get(resource_group, vnet_name)
                except Exception as e:
                    logger.error(e.message)
                    vnet = None
                if vnet:
                    self.print_vnet_info(vnet)
            else:
                for vnet in self.network_client.virtual_networks.list(resource_group):
                    self.print_vnet_info(vnet)
        else:
            for vnet in self.network_client.virtual_networks.list_all():
                self.print_vnet_info(vnet)


    def create_vnet(self, resource_group, location, vnet_name, addr_prefix = "10.0.0.0/16"):
        async_vnet_create = self.network_client.virtual_networks.create_or_update(
                                resource_group,
                                vnet_name,
                                {
                                    'location' : location,
                                    'address_space' : {
                                    'address_prefixes' : [addr_prefix]
                                    }
                                }
                            )
        async_vnet_create.wait()

    def delete_vnet(self, resource_group, vnet):
        async_vnet_delete = self.network_client.virtual_networks.delete(
                                resource_group,
                                vnet
                            )
        async_vnet_delete.wait()

    def print_subnet_info(self, subnet_obj):
        logger.info('')
        logger.info('Name: {}'.format(subnet_obj.name))
        logger.info('VNet: {}'.format(str(subnet_obj.id.split('/')[8])))
        logger.info('AddressSpace: {}'.format(subnet_obj.address_prefix))

    def get_subnet_info(self, resource_group, vnet, subnet = None):
        if subnet:
            try:
                subnet_obj = self.network_client.subnets.get(resource_group, vnet, subnet)
            except Exception as e:
                logger.error(e.message)
                subnet_obj = None
            if subnet_obj:
                self.print_subnet_info(subnet_obj)
        else:
            for subnet in self.network_client.subnets.list(resource_group, vnet):
                self.print_subnet_info(subnet)

    def list_subnetworks(self, resource_group = None, vnet = None, subnet = None):
        if not resource_group:
            for vnet in self.network_client.virtual_networks.list_all():
                resource_group = str(vnet.id.split('/')[4])
                vnet_name = vnet.name
                self.get_subnet_info(resource_group, vnet_name)
        elif not vnet:
            for vnet in self.network_client.virtual_networks.list(resource_group):
                vnet_name = vnet.name
                self.get_subnet_info(resource_group, vnet_name)
        else:
             self.get_subnet_info(resource_group, vnet, subnet)

    def create_subnet(self, resource_group, vnet_name, subnet_name, addr_prefix = "10.0.0.0/24"):
        async_subnet_create = self.network_client.subnets.create_or_update(
                                  resource_group,
                                  vnet_name,
                                  subnet_name,
                                  {
                                      'address_prefix' : addr_prefix 
                                  }
                              )
        async_subnet_create.wait()

    def delete_subnet(self, resource_group, vnet, subnet):
        async_subnet_delete = self.network_client.subnets.delete(
                                  resource_group,
                                  vnet,
                                  subnet
                              )
        async_subnet_delete.wait()

    def list_network_interfaces(self, resource_group):
        for nic in self.network_client.network_interfaces.list(resource_group):
            name = nic.name
            attached_vm = nic.virtual_machine
            private_ip_addr = nic.ip_configurations[0].private_ip_address
            subnet_ref = nic.ip_configurations[0].subnet
            subnet_group = '{}/{}/{}: '.format(subnet_ref.id.split('/')[8], subnet_ref.id.split('/')[10], name)
            if attached_vm:
                private_ip = '{}{} : Attached to VM {}'.format(subnet_group, private_ip_addr, attached_vm.id.split('/')[8])
            else:
                private_ip = '{}{} :  Available'.format(subnet_group, private_ip_addr)
            logger.info(private_ip)

    def list_public_ip(self, resource_group):
            public_ips = self.network_client.public_ip_addresses.list(resource_group)
            for public_ip in public_ips:
                public_ip_name = public_ip.id.split('/')[-1]
                logger.info('{} : {}'.format(public_ip_name, public_ip.ip_address))

    def list_vm_public_ip(self, resource_group, vmname, nic_names = None):
        if nic_names is None:
            nic_names = []
            vm = self.get_vm(resource_group, vmname)
            for nic_ref in vm.network_profile.network_interfaces:
                nic_names.append(nic_ref.id.split('/')[8])
        public_ips = []
        for nic_name in nic_names:
            nic = self.network_client.network_interfaces.get(resource_group, nic_name)
            ip_ref = nic.ip_configurations[0].public_ip_address
            if ip_ref is None:
                continue
            ip_group = ip_ref.id.split('/')[4]
            ip_name = ip_ref.id.split('/')[8]
            public_ip = self.network_client.public_ip_addresses.get(ip_group, ip_name)
            if public_ip.ip_address:
                public_ips.append(public_ip.ip_address)
        
        logger.info('VM Public IP : {}'.format(','.join(public_ips)))

    def list_vm_private_ip(self, resource_group, vmname, nic_names = None):
        if nic_names is None:
            nic_names = []
            vm = self.get_vm(resource_group, vmname)
            for nic_ref in vm.network_profile.network_interfaces:
                nic_names.append(nic_ref.id.split('/')[8])
        private_ips = []
        for nic_name in nic_names:
            nic = self.network_client.network_interfaces.get(resource_group, nic_name)
            private_ip_addr = nic.ip_configurations[0].private_ip_address
            subnet_ref = nic.ip_configurations[0].subnet
            subnet_group = '{}/{}: '.format(subnet_ref.id.split('/')[8], subnet_ref.id.split('/')[10])
            private_ip = '{}{}'.format(subnet_group, private_ip_addr)
            private_ips.append(private_ip)

        logger.info('VM Private IP :\n {}'.format(','.join(private_ips)))

    def create_nic(self, resource_group, vnet, subnet, location, nic_name):
        subnet_ref = self.get_subnet_by_vnet(location, vnet, subnet)
        if subnet_ref is None:
            raise ValueError("The specified subnet does not exist.")

        async_nic_create = self.network_client.network_interfaces.create_or_update(
                               resource_group,
                               nic_name,
                               {
                                   'location' : location,
                                   'ip_configurations' : [{
                                       'name' : nic_name,
                                       'subnet' : {
                                           'id' : subnet_ref.id
                                           }
                                       }]
                               }
                           )
        return async_nic_create.result()

    def delete_nic(self, resource_group, nic_list):
        nics = nic_list.split(',')
        for nic in nics:
            nic_ref = self.network_client.network_interfaces.get(resource_group, nic)
    
            public_ip = nic_ref.ip_configurations[0].public_ip_address
            
            async_nic_delete = self.network_client.network_interfaces.delete(
                                   resource_group,
                                   nic
                               )
            async_nic_delete.wait()
            
            if public_ip:
                pub_ip_name = public_ip.id.split('/')[8]
                self.delete_public_ip(resource_group, pub_ip_name)

    def delete_public_ip(self, resource_group, public_ip_name):
         async_nic_delete = self.network_client.public_ip_addresses.delete(resource_group, public_ip_name)
         async_nic_delete.wait()

    def create_public_ip(self, resource_group, vmname, static_ip = False):
        if static_ip:
            create_opt = 'Static'
        else:
            create_opt = 'Dynamic'

        vm = self.get_vm(resource_group, vmname)
        for nic_ref in vm.network_profile.network_interfaces:
            if not nic_ref.primary or nic_ref.primary:
                nic_name = nic_ref.id.split('/')[8]
                break

        nic = self.network_client.network_interfaces.get(resource_group, nic_name)
        # first create a public ip
        public_ip_obj = self.network_client.public_ip_addresses
        public_ip_param = PublicIPAddress(location = nic.location, public_ip_allocation_method = create_opt)
        async_ip_create = public_ip_obj.create_or_update(
                              resource_group, 
                              nic_name,
                              public_ip_param
                          )
        async_ip_create.wait()
        # second bind the public ip to the primary nic
        public_ip_address = public_ip_obj.get(resource_group, nic_name)
        public_ip_id = public_ip_address.id
        nic.ip_configurations[0].public_ip_address = PublicIPAddress(id = public_ip_id)
        async_nic_create = self.network_client.network_interfaces.create_or_update(
                               resource_group,
                               nic_name,
                               nic
                           )
        async_nic_create.wait()

    def get_nic(self, resource_group, nic_name):
        for nic in self.network_client.network_interfaces.list(resource_group):
            if nic.name == nic_name:
                return nic

    def get_location(self, resource_group):
        rg_ref = self.resource_client.resource_groups.get(resource_group)
        if rg_ref is None:
            raise ValueError('The specified resource group {} dose not exist.'.format(resource_group))
        # determine location
        location = rg_ref.location

        return location

    def get_vm_size(self, location, size):
        for vm_size in self.compute_client.virtual_machine_sizes.list(location):
            if vm_size.name == size:
                return vm_size
        return None

    def get_vnet_by_location(self, location, vnet_name):
        for vnet in self.network_client.virtual_networks.list_all():
            if vnet.location == location and vnet.name == vnet_name:
                return vnet
        return None

    def get_subnet_by_vnet(self, location, vnet_name, subnet_name):
        vnet_obj = self.get_vnet_by_location(location, vnet_name)
        if vnet_obj:
            resource_group = str(vnet_obj.id.split('/')[4])
            try:
                subnet_ref = self.network_client.subnets.get(resource_group, vnet_name, subnet_name)
                return subnet_ref
            except:
                return None
        return None

    def get_storage_account_by_location(self, location, storage_account):
        for sa in self.storage_client.storage_accounts.list():
            if sa.name == storage_account and sa.location == location:
                return sa
        return None

    def create_vm(self, resource_group, storage_account, location, vm_size, vmname, vnet, subnet_list, 
                  ssh_public_key = None, publisher = None, offer = None, sku = None, image = None,
                  username = None, password = None, public_ip = False, static_public_ip = False):
        # determine location
        if not location:
            location = self.get_location(resource_group) 

        # vmname check
        if re.search(r'[^-0-9A-Za-z]{5,12}', vmname) is not None:
            raise ValueError('Illegal vm name. Only digits, letters and - can be used. Name length should be 5~12')
        
        # vm check
        vm_obj = self.get_vm(resource_group, vmname)
        if vm_obj:
            raise ValueError('Illegal vm name. The specified vm already exists.')

        # offer related check
        if not publisher and not offer:
            publisher = 'dellemc'
            offer = 'dell-emc-datadomain-virtual-edition'

        # default username
        if not username:
            username = 'sysadmin'

        # authentication check 
        if not password and not ssh_public_key:
            raise ValueError('Either Password or SSH Public Key must be specified.')
        
        # size check
        if not re.search('Standard_', vm_size) or not re.search('\d+T', vm_size):
            raise ValueError('Please use either *T or Standard_* as vm size.')
        if (image and 'ddve' not in image.lower()) or publisher != 'dellemc' or offer != 'dell-emc-datadomain-virtual-edition' or 'Standard_' in vm_size:
            # check whether this size of VM exists in this location
            vm_size_obj = self.get_vm_size(location, vm_size)
            if not vm_size_obj:
                raise ValueError('VM size {} does not exist in {}'.format(vm_size, location))
        else:
            if supported_vm_sizes.get(vm_size.upper()) is None:
                raise ValueError('Wrong capacity {} provided.'.format(vm_size))
            else:
                vm_size = supported_vm_sizes[vm_size.upper()]

        # vnet check
        vnet_ref = self.get_vnet_by_location(location, vnet)
        if not vnet_ref:
            raise ValueError('Virtual network {} does not exist in location {}.'.format(vnet, location))
       
        # subnets check
        subnets = subnet_list.split(',')
        for subnet in subnets:
            subnet_ref = self.get_subnet_by_vnet(location, vnet, subnet.strip())
            if not subnet_ref:
                raise ValueError('Subnet {} does not exist.'.format(subnet))
            
        # if storage account is not specified, managed disks will be used
        if storage_account:
            if not self.get_storage_account_by_location(location, storage_account):
                raise ValueError('Storage account {} not in location {}.'.format(storage_account, location))
            # create storage container 
            container = '{}-vhds'.format(vmname)
            self.create_storage_container(storage_account, container)
        else:
            container = None

        # create nic
        nic_num = 0 
        nic_ids = []
        for subnet in subnets:
            nic_num += 1
            nic_name = vmname + '-nic{}'.format(nic_num) 
            nic_ref = self.get_nic(resource_group, nic_name)
            if not nic_ref:
                nic_ref = self.create_nic(resource_group, vnet, subnet.strip(), location, nic_name)
            else:
                if nic_ref.virtual_machine:
                    raise ValueError('NIC attached to an exsisting VM.')
            nic_ids.append(nic_ref.id)
       
        # template parameters
        try:
            parameters = self.create_vm_parameters(resource_group = resource_group, location = location, 
                             storage_account = storage_account, container = container, vm_size = vm_size, 
                             vmname = vmname, nic_ids = nic_ids, ssh_public_key = ssh_public_key, 
                             publisher = publisher, offer = offer, sku = sku, image = image,
                             username = username, password = password)
            
            # try to deploy vm with a Plan
            if publisher and offer and sku:
                plan = Plan(name = sku, publisher = publisher, product = offer)
                parameters.plan = plan 
            else:
                parameters.plan = None 

            async_vm_create = self.compute_client.virtual_machines.create_or_update(resource_group, 
                                  vmname, parameters)
            vm = async_vm_create.result()
        except Exception as e:
            # then try to deploy vm without a Plan
            parameters.plan = None 
            try:
                async_vm_create = self.compute_client.virtual_machines.create_or_update(resource_group,
                                      vmname, parameters)
                vm = async_vm_create.result()
            except Exception:
                for subnet in subnets:
                    nic_name = vmname + '-nic{}'.format(nic_num)
                    self.delete_nic(resource_group, nic_name)
                if storage_account:
                    self.delete_container(storage_account, container)
                logger.error('Failed to create vm.')
                logger.error('{}'.format(e))
                return
                 
        # add a public ip if needed
        if public_ip:
            if static_public_ip:
                self.create_public_ip(resource_group, vmname, True)
            else:
                self.create_public_ip(resource_group, vmname, False)

        # if a VM is created from a vhd converted manage disk, remove the intermediate os image
        if image and not storage_account:
            os_image = '{}-osImage'.format(vmname)
            self.compute_client.images.delete(resource_group, os_image)

        self.print_vm_info(resource_group, vm)

    def create_vm_parameters(self, resource_group, location, storage_account, container, vm_size, vmname, nic_ids, 
                             ssh_public_key, publisher, offer, sku, image, username,  password):
       
        # hardware profile 
        hardware_profile = HardwareProfile(vm_size = vm_size)
     
        # os profile
        linux_config = None
        if ssh_public_key:
            key_path = '/home/{}/.ssh/authorized_keys'.format(username)
            public_key = SshPublicKey(path = key_path, key_data = ssh_public_key)
            public_keys = [public_key]
            ssh_config = SshConfiguration(public_keys = public_keys)
            linux_config = LinuxConfiguration(disable_password_authentication = False,
                           ssh = ssh_config)
        os_profile = OSProfile(computer_name = vmname, admin_username = username, 
                     admin_password = password, linux_configuration = linux_config)
      
        image_reference = None
        if publisher and offer and sku:
            image_reference = ImageReference(publisher = publisher, offer = offer, sku = sku, version = 'latest') 
        
        # create_option: fromImage, empty, attach
        # for ddve, data disk will be created 'fromImage' if publisher/offer/sku specified
        # otherwise data disk will be created empty
        if publisher and offer and sku:
            data_create_opt = 'fromImage'
        else:
            data_create_opt = 'empty'
        # use unmanaged disks
        if storage_account:
            os_vhd_uri = 'https://{}.blob.core.windows.net/{}/{}-os.vhd'.format(storage_account, container, vmname) 
            os_vhd = VirtualHardDisk(uri = os_vhd_uri)
            source_image = None
            if image:
                source_image = VirtualHardDisk(uri = image)
            os_disk_name = '{}-osDisk'.format(vmname)
            os_disk_ref = OSDisk(create_option = 'fromImage', name = os_disk_name, vhd = os_vhd, os_type = 'Linux', image = source_image)
            
            if (image and 'ddve' not in image.lower()) or publisher != 'dellemc' or offer != 'dell-emc-datadomain-virtual-edition':
                data_disk_refs = None
            else:
                data_vhd_uri = 'https://{}.blob.core.windows.net/{}/{}-nvram.vhd'.format(storage_account, container, vmname) 
                data_vhd = VirtualHardDisk(uri = data_vhd_uri)
                data_disk_name = '{}-nvramDisk'.format(vmname)
                data_disk_ref = DataDisk(lun = 0, disk_size_gb = 10, create_option = data_create_opt, name = data_disk_name, vhd = data_vhd)
                data_disk_refs = [data_disk_ref]
            
            storage_profile = StorageProfile(image_reference = image_reference, os_disk = os_disk_ref, data_disks = data_disk_refs)
        # use managed disks
        else:
            # You need first create a managed image for your vhd
            # See more at https://github.com/Azure/azure-sdk-for-python/issues/1380
            storage_account_type = 'Standard_LRS'
            if re.search('Standard_[A-Z]S\d+', vm_size):
                storage_account_type = 'Premium_LRS'

            os_disk_ref = None
            if image:
                image_name = '{}-osImage'.format(vmname)
                async_create = self.compute_client.images.create_or_update(
                    resource_group, image_name, 
                    {
                        'location': location,
                        'storage_profile': {
                            'os_disk': {
                                'os_type': 'Linux',
                                'os_state': "Generalized",
                                'blob_uri': image,
                                'caching': "ReadWrite",
                                'storage_account_type': storage_account_type,
                            }
                        }
                    })
                managed_image_ref = async_create.result()
                image_reference = ImageReference(id = managed_image_ref.id) 
               
            if (image and 'ddve' not in image.lower()) or publisher != 'dellemc' or offer != 'dell-emc-datadomain-virtual-edition':
                data_disk_refs = None
            else:
                disk_name = '{}-nvramDisk'.format(vmname)
                data_disk_ref = DataDisk(lun = 0, disk_size_gb = 10, create_option = data_create_opt, 
                                name = disk_name, managed_disk = ManagedDiskParameters())

                data_disk_refs = [data_disk_ref]

            storage_profile = StorageProfile(image_reference = image_reference, os_disk = os_disk_ref, data_disks = data_disk_refs)

        # network profile
        nic_list = []
        primary_nic = True 
        for nic_id in nic_ids:
            if primary_nic:
                nic_ref = NetworkInterfaceReference(id = nic_id, primary = True)
                primary_nic = False
            else:
                nic_ref = NetworkInterfaceReference(id = nic_id, primary = False)
            nic_list.append(nic_ref)
      
        network_profile = NetworkProfile(network_interfaces = nic_list)

        # dianostic profile
        if storage_account:
            storage_uri = 'https://{}.blob.core.windows.net'.format(storage_account)
            boot_diagnostics = BootDiagnostics(enabled = True, storage_uri = storage_uri)
            diagnostics_profile = DiagnosticsProfile(boot_diagnostics = boot_diagnostics) 
        else:
            diagnostics_profile = None

        # build template_params 
        vm_create_params = VirtualMachine(
                           location = location,
                           os_profile = os_profile,
                           hardware_profile = hardware_profile,
                           network_profile = network_profile,
                           storage_profile = storage_profile,
                           diagnostics_profile = diagnostics_profile)

        return vm_create_params 

    def resize_vm(self, resource_group, vmname, vm_size):
        if supported_vm_sizes.get(vm_size.upper()):
            vm_size = supported_vm_sizes[vm_size.upper()]
        
        # first stop the vm 
        self.deallocate_vm(resource_group, vmname)
        # second change vm size
        vm = self.get_vm(resource_group, vmname)
        if vm:
            vm_size_obj = self.get_vm_size(vm.location, vm_size)
            if not vm_size_obj:
                raise ValueError('Wrong VM size {}'.format(vm_size))
        else:
            raise ValueError('VM {} does not exist.'.format(vmname))
        vm.hardware_profile.vm_size = vm_size
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
                               resource_group,
                               vmname,
                               vm
                          )
        async_vm_update.wait()
        # last start the vm 
        self.start_vm(resource_group, vmname)

    def attach_unmanaged_disk(self, resource_group, vm_obj, disk_name, disk_size, available_lun, existing = None):
        #make sure data disks are put under the same container with the os disk_name
        os_disk = vm_obj.storage_profile.os_disk
        disk_uri = os_disk.vhd.uri
        disk_uri = disk_uri[0:disk_uri.rfind('/')]

        if existing is not None:
            create_opt = 'attach'
            disk_uri = existing
        else:
            create_opt = 'empty'
            disk_uri = '{}/{}.vhd'.format(disk_uri, disk_name)
       
        vm_obj.storage_profile.data_disks.append(
            DataDisk(lun = available_lun, name = disk_name, disk_size_gb = disk_size,
                vhd = {
                    'uri': disk_uri 
                },
                create_option = create_opt
            )
        )
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
            resource_group, vm_obj.name, vm_obj)
        async_vm_update.wait()
    
    def attach_managed_disk(self, resource_group, vm_obj, disk_name, disk_size, available_lun, existing = None):
        if not existing:
            create_opt = 'empty'

            # use the same location where the vm is 
            location = vm_obj.location
            
            async_create = self.compute_client.disks.create_or_update(
                resource_group, disk_name, 
                {
                    'location': location,
                    'disk_size_gb': disk_size,
                    'creation_data': {
                        'create_option': 'empty'
                    }
                })
            managed_disk_ref = async_create.result()
        else:
            create_opt = 'attach'
            managed_disk_ref = self.compute_client.disks.get(resource_group, existing)
            
        vm_obj.storage_profile.data_disks.append({
            'lun': available_lun,
            'name': managed_disk_ref.name,
            'create_option': 'attach',
            'managed_disk': {
                'id': managed_disk_ref.id
            }
        })
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
            resource_group, vm_obj.name, vm_obj)
        async_vm_update.wait()


    def attach_data_disk(self, resource_group, vmname, disk_name, disk_size, existing = None):
        if (int(disk_size) < 1):
            disk_size = 1
        elif (int(disk_size) > 4095):
            disk_size = 4095

        vm = self.get_vm(resource_group, vmname)
        if not vm:
            raise ValueError('The specified VM {} does not exist.'.format(vmname))
       
        # check whether managed disks is used 
        os_disk = vm.storage_profile.os_disk
        if os_disk.managed_disk:
            managed_disk = True
        else:
            managed_disk = False

        data_disks = vm.storage_profile.data_disks
        #find an available lun
        used_luns = []
        for data_disk in data_disks:
            used_luns.append(data_disk.lun)
        for i in xrange(100):
            if i not in used_luns:
                available_lun = i
                break

        if managed_disk:
            self.attach_managed_disk(resource_group, vm, disk_name, disk_size, available_lun, existing)
        else:
            self.attach_unmanaged_disk(resource_group, vm, disk_name, disk_size, available_lun, existing)

class arg_parse:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')
        self.list_parser = self.subparsers.add_parser('list', description='list a specified resource', help='resource_group | storage_account | container | vm | vnet | subnet | nic | public_ip | vhd | vm_state | vm_size | vm_ip | vm_disk')
        self.create_parser = self.subparsers.add_parser('create', description='create a specified resource', help='resource_group | storage_account | container | vm | vnet | subnet | nic | public_ip')
        self.delete_parser = self.subparsers.add_parser('delete', description='delete a specified resource', help='resource_group | storage_account | container | vm | vnet | subnet | nic | public_ip | container | blob')
        self.start_parser = self.subparsers.add_parser('start', description='start a specified vm', help='vm')
        self.restart_parser = self.subparsers.add_parser('restart', description='restart a specified vm', help='vm')
        self.stop_parser = self.subparsers.add_parser('stop', description='stop a specified vm', help='vm')
        self.resize_parser = self.subparsers.add_parser('resize', description='resize a specified vm', help='vm')
        self.attach_parser = self.subparsers.add_parser('attach', description='attach disks to a specified vm', help='disk')
        self.detach_parser = self.subparsers.add_parser('detach', description='attach disks to a specified vm', help='disk')
    
    def add_credentials(self):
        self.parser.add_argument('-C', '--client_id', help='login via this client')
        self.parser.add_argument('-K', '--secret_key', help='login via this key')
        self.parser.add_argument('-T', '--tenant_id', help='login via this tenant')
        self.parser.add_argument('-S', '--subscription_id', help='login via this subscription id')

    def run_cmd(self):
        self.add_credentials()
        self.add_list_subcommands()
        self.add_create_subcommands()
        self.add_delete_subcommands()
        self.add_start_subcommands()
        self.add_restart_subcommands()
        self.add_stop_subcommands()
        self.add_resize_subcommands()
        self.add_attach_subcommands()
        self.add_detach_subcommands()
        
        self.parsed_args = self.parser.parse_args()

        self.azure_ops = azure_operations(self.parsed_args.client_id, self.parsed_args.secret_key, self.parsed_args.tenant_id, self.parsed_args.subscription_id)
       
        self.parsed_args.func(self.parsed_args)

    def add_list_subcommands(self):
        list_subparser = self.list_parser.add_subparsers(title='list',  help='list related resources')
        # list subscriptions
        list_subscription = list_subparser.add_parser('subscription', help='list resource groups')
        list_subscription.set_defaults(func=self.list_subscriptions)
        # list resource groups
        list_rg = list_subparser.add_parser('resource_group', help='list resource groups')
        list_rg.set_defaults(func=self.list_resource_groups)
        # list storage accounts
        list_sa = list_subparser.add_parser('storage_account', help='list storage accounts')
        list_sa.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
        list_sa.set_defaults(func=self.list_storage_accounts)
        # list storage containers
        list_sa = list_subparser.add_parser('container', help='list storage containers')
        list_sa.add_argument('-s', '--storage_account', required = True, help='list storage containers within a storage_account')
        list_sa.set_defaults(func=self.list_storage_containers)
        # list vms
        list_vm = list_subparser.add_parser('vm', help='list vms within a resource group')
        list_vm.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_vm.add_argument('-n', '--name', help='list a specific vm')
        list_vm.set_defaults(func=self.list_virtual_machines)
        # list vnets
        list_vnet = list_subparser.add_parser('vnet', help='list vnets within a resource group')
        list_vnet.add_argument('-r', '--resource_group', help='list resources wihtin this group')
        list_vnet.add_argument('-n', '--name', help='list resources wihtin this group')
        list_vnet.set_defaults(func=self.list_virtual_networks)
        # list subnets
        list_subnet = list_subparser.add_parser('subnet', help='list subnets within a resource group')
        list_subnet.add_argument('-r', '--resource_group',help='list resources wihtin this group')
        list_subnet.add_argument('-v', '--vnet', help='list resources within this vnet')
        list_subnet.add_argument('-n', '--name', help='list subnet info')
        list_subnet.set_defaults(func=self.list_subnetworks)
        # list nics
        list_nic = list_subparser.add_parser('nic', help='list nics within a resource group')
        list_nic.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_nic.set_defaults(func=self.list_network_interfaces)
        # list public ips 
        list_nic = list_subparser.add_parser('public_ip', help='list public ips within a resource group')
        list_nic.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_nic.set_defaults(func=self.list_public_ip)
        # list a vm's state
        list_state = list_subparser.add_parser('vm_state', help="list a vm's state within a resource group")
        list_state.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_state.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_state.set_defaults(func=self.list_vm_state)
        # list a vm's size
        list_size = list_subparser.add_parser('vm_size', help="list a vm's size within a resource group")
        list_size.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_size.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_size.set_defaults(func=self.list_vm_size)
        # list a vm's ip 
        list_ip = list_subparser.add_parser('vm_ip', help="list a vm's ips within a resource group")
        list_ip.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_ip.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_ip.set_defaults(func=self.list_vm_ip)
        # list a vm's data disks
        list_disk = list_subparser.add_parser('vm_disk', help="list a vm's data disks")
        list_disk.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_disk.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_disk.set_defaults(func=self.list_vm_data_disk)
        # list vhds within a storage account 
        list_vhd = list_subparser.add_parser('vhd', help="list vhds within a storage account")
        list_vhd.add_argument('-r', '--resource_group', help='list resources wihtin this group')
        list_vhd.add_argument('-s', '--storage_account', help='list vhds within this storage account')
        list_vhd.add_argument('-c', '--container', help='list vhds within this storage container')
        list_vhd.add_argument('--managed', action='store_true', help='only list manage disk')
        list_vhd.set_defaults(func=self.list_vhds)

    def add_create_subcommands(self):
        # create subcommands
        create_subparser = self.create_parser.add_subparsers(title='create',  help='create related resources')
        # create resource group
        create_rg = create_subparser.add_parser('resource_group', help='create a resource group')
        create_rg.add_argument('-n', '--name', required=True, help='create a resource group with this name')
        create_rg.add_argument('-l', '--location', required=True, help='create a resource group within this region')
        create_rg.set_defaults(func=self.create_resource_group)
        # create storage account
        create_sa = create_subparser.add_parser('storage_account', help='create a storage account')
        create_sa.add_argument('-r', '--resource_group', required=True, help='create a storage accounts within a resource group')
        create_sa.add_argument('-n', '--name', required=True, help='create a storage account with this name')
        create_sa.add_argument('-k', '--kind', help='[Storage|BlobStorage]')
        create_sa.add_argument('-t', '--type', help='[Standard_LRS|Standard_GRS|Standard_RAGRS|Standard_ZRS|Premium_LRS]')
        create_sa.add_argument('-a', '--access_tier', help='[Hot|Cool]')
        create_sa.set_defaults(func=self.create_storage_account)
        # create storage container
        create_container = create_subparser.add_parser('container', help='create a storage container')
        create_container.add_argument('-s', '--storage_account', required=True, help='create a storage container within this storage account')
        create_container.add_argument('-n', '--name', required=True, help='create a storage container with this name')
        create_container.set_defaults(func=self.create_storage_container)
        # create vm
        create_vm = create_subparser.add_parser('vm', help='create a vm within a resource group')
        create_vm.add_argument('-r', '--resource_group', required=True, help='create a vm wihtin this resource group')
        create_vm.add_argument('-s', '--storage_account', help='if not specified, managed disks will be used.')
        create_vm.add_argument('-l', '--location', help='if not specified, resource group location will be used')
        create_vm.add_argument('-c', '--vm_size', required=True, help='for ddve, please use capacity like 7T/15T; for other linux vms, standard vm size can be used')
        create_vm.add_argument('-n', '--name', required=True, help='create a vm with this name')
        create_vm.add_argument('-v', '--vnet', required=True, help='create a vm with this vnet')
        create_vm.add_argument('-e', '--subnet', required=True, help="use ',' to separate multiple subnets")
        create_vm.add_argument('-k', '--ssh_key', help='create a vm with this public ssh key')
        create_vm.add_argument('-u', '--username', help='create a vm with this username')
        create_vm.add_argument('-p', '--password', help='create a vm with login password')
        create_vm.add_argument('-P', '--publisher', help='create a vm from this publisher')
        create_vm.add_argument('-O', '--offer', help='create a vm from this offer')
        create_vm.add_argument('-S', '--sku', help='create a vm from this sku')
        create_vm.add_argument('-I', '--image', help='create a vm from customized image')
        create_vm.add_argument('--public_ip', action='store_true', help='create a vm with public ip')
        create_vm.add_argument('--static_ip', action='store_true', help='create a vm with a static ip')
        create_vm.set_defaults(func=self.create_virtual_machine)
        # create vnet
        create_vnet = create_subparser.add_parser('vnet', help='create a virtual network within a resource group')
        create_vnet.add_argument('-r', '--resource_group', required=True, help='create a vnet wihtin this group')
        create_vnet.add_argument('-n', '--name', required=True, help='create a vnet with this name')
        create_vnet.add_argument('-l', '--location', required=True, help='create a vnet within this location')
        create_vnet.add_argument('-p', '--prefix', required=True, help="address prefix like '10.0.0.1/16'")
        create_vnet.set_defaults(func=self.create_virtual_network)
        # create subnet
        create_subnet = create_subparser.add_parser('subnet', help='create a subnet within a virutal network')
        create_subnet.add_argument('-r', '--resource_group', required=True, help='create a subnet wihtin this group')
        create_subnet.add_argument('-v', '--vnet', required=True, help='create a subnet with this vnet')
        create_subnet.add_argument('-n', '--name', required=True, help='create a subnet with this name')
        create_subnet.add_argument('-p', '--prefix', required=True, help="address prefix like '10.0.0.1/24', make sure the prefix is part of the vnet prefix")
        create_subnet.set_defaults(func=self.create_subnetwork)
        # create nic
        create_nic = create_subparser.add_parser('nic', help='create a nic within a resource group')
        create_nic.add_argument('-r', '--resource_group', required=True, help='create a nic wihtin this group')
        create_nic.add_argument('-v', '--vnet', required=True, help='create a nic with this vnet')
        create_nic.add_argument('-e', '--subnet', required=True, help='create a nic with this subnet')
        create_nic.add_argument('-l', '--location', required=True, help='create a nic where the vnet is')
        create_nic.add_argument('-n', '--name', required=True, help='create a nic with this name')
        create_nic.set_defaults(func=self.create_network_interface)
        # create public ip
        create_ip = create_subparser.add_parser('public_ip', help='create a public ip for a vm')
        create_ip.add_argument('-r', '--resource_group', required=True, help='create a public ip wihtin this group')
        create_ip.add_argument('-n', '--name', required=True, help='create a public ip for this vm')
        create_ip.add_argument('-s', '--static', help='create a static ip', action='store_true')
        create_ip.set_defaults(func=self.create_public_ip)
        
    def add_delete_subcommands(self):
        # delete subcommands
        delete_subparser = self.delete_parser.add_subparsers(title='delete',  help='create related resources')
        # delete resource group
        delete_rg = delete_subparser.add_parser('resource_group', help='delete a resource group')
        delete_rg.add_argument('-n', '--name', required=True, help='delete a resource group')
        delete_rg.set_defaults(func=self.delete_resource_group)
        # delete storage account
        delete_sa = delete_subparser.add_parser('storage_account', help='delete a storage account')
        delete_sa.add_argument('-r', '--resource_group', required=True, help='delete a resource group')
        delete_sa.add_argument('-n', '--name', required=True, help='delete a storage account')
        delete_sa.set_defaults(func=self.delete_storage_account)
        # delete vm
        delete_vm = delete_subparser.add_parser('vm', help='delete a vm within a resource group')
        delete_vm.add_argument('-r', '--resource_group', required=True, help='delete a vm wihtin this resource group')
        delete_vm.add_argument('-n', '--name', required=True, help='delete a vm with this name')
        delete_vm.add_argument('--keep_data', action='store_true', help='delete a vm but keep the data disks')
        delete_vm.set_defaults(func=self.delete_virtual_machine)
        # delete vnet
        delete_vnet = delete_subparser.add_parser('vnet', help='delete a vnet within a resource group')
        delete_vnet.add_argument('-r', '--resource_group', required=True, help='delete a vnet wihtin this group')
        delete_vnet.add_argument('-n', '--name', required=True, help='delete a vnet with this name')
        delete_vnet.set_defaults(func=self.delete_virtual_network)
        # delete subnet
        delete_subnet = delete_subparser.add_parser('subnet', help='delete subnets within a resource group')
        delete_subnet.add_argument('-r', '--resource_group', required=True, help='delete a subnet wihtin this group')
        delete_subnet.add_argument('-v', '--vnet', required=True, help='delete a subnet wihtin this vnet')
        delete_subnet.add_argument('-n', '--name', required=True, help='delete a subnet with this name')
        delete_subnet.set_defaults(func=self.delete_subnetwork)
        # delete nic
        delete_nic = delete_subparser.add_parser('nic', help='delete nics within a resource group')
        delete_nic.add_argument('-r', '--resource_group', required=True, help='delete a nic wihtin this group')
        delete_nic.add_argument('-n', '--name', required=True, help='delete a nic with this name')
        delete_nic.set_defaults(func=self.delete_network_interface)
        # delete public ip 
        delete_nic = delete_subparser.add_parser('public_ip', help='delete a public ip within a resource group')
        delete_nic.add_argument('-r', '--resource_group', required=True, help='delete a nic wihtin this group')
        delete_nic.add_argument('-n', '--name', required=True, help='delete a public ip with this name')
        delete_nic.set_defaults(func=self.delete_public_ip)
        # delete container
        delete_container = delete_subparser.add_parser('container', help='delete a storage container within a storage account')
        delete_container.add_argument('-s', '--storage_account', required=True, help='delete a container within this storage account')
        delete_container.add_argument('-n', '--name', required=True, help='delete a container with this name')
        delete_container.set_defaults(func=self.delete_storage_container)
        # delete a blob 
        delete_blob = delete_subparser.add_parser('blob', help='delete a blob within a storage account')
        delete_blob.add_argument('-r', '--resource_group', required=True, help='delete a blob within this group')
        delete_blob.add_argument('-s', '--storage_account', help='delete a blob within this storage account')
        delete_blob.add_argument('-c', '--container', help='delete a blob within this container')
        delete_blob.add_argument('-n', '--name', required=True, help='delete a blob with this name')
        delete_blob.add_argument('--managed_disk', action='store_true', help='delete a managed disk')
        delete_blob.set_defaults(func=self.delete_blob)

    def add_start_subcommands(self):
        # start subcommand
        start_subparser = self.start_parser.add_subparsers(title='start', description='start a specified vm', help='vm')
        start_vm = start_subparser.add_parser('vm', help='start a vm')
        start_vm.add_argument('-r', '--resource_group', required=True, help='start a vm within this group')
        start_vm.add_argument('-n', '--name', required=True, help='start a vm with this name')
        start_vm.set_defaults(func=self.start_virtual_machine) 

    def add_stop_subcommands(self):
        # stop command
        stop_subparser = self.stop_parser.add_subparsers(title='stop', description='stop a specified vm', help='vm')
        stop_vm = stop_subparser.add_parser('vm', help='stop a vm')
        stop_vm.add_argument('-r', '--resource_group', required=True, help='stop a vm within this group')
        stop_vm.add_argument('-n', '--name', required=True, help='stop a vm with this name')
        stop_vm.set_defaults(func=self.stop_virtual_machine)

    def add_restart_subcommands(self):
        # restart subcommand
        restart_subparser = self.restart_parser.add_subparsers(title='restart', description='restart a specified vm', help='vm')
        restart_vm = restart_subparser.add_parser('vm', help='restart a vm')
        restart_vm.add_argument('-r', '--resource_group', required=True, help='restart a vm within this group')
        restart_vm.add_argument('-n', '--name', required=True, help='restart a vm with this name')
        restart_vm.set_defaults(func=self.restart_virtual_machine)

    def add_resize_subcommands(self):
        # resize command
        resize_subparser = self.resize_parser.add_subparsers(title='resize', description='resize a specified vm', help='vm')
        resize_vm = resize_subparser.add_parser('vm', help='resize a vm')
        resize_vm.add_argument('-r', '--resource_group', required=True, help='resize a vm within this group')
        resize_vm.add_argument('-n', '--name', required=True, help='resize a vm with this name')
        resize_vm.add_argument('-c', '--vm_size', required=True, help='resize a vm to this size')
        resize_vm.set_defaults(func=self.resize_virtual_machine)

    def add_attach_subcommands(self):
        # attach subcommand
        attach_subparser = self.attach_parser.add_subparsers(title='attach', description='attach a specified disk', help='disk')
        attach_disk = attach_subparser.add_parser('disk', help='attach a disk to a vm')
        attach_disk.add_argument('-r', '--resource_group', required=True, help='attach a disk to a vm within this group')
        attach_disk.add_argument('-n', '--name', required=True, help='attach a disk to a vm with this name')
        attach_disk.add_argument('-d', '--disk_name', required=True, help='attach a disk with this name')
        attach_disk.add_argument('-g', '--disk_size', required=True, help='attach a disk with this size in GiB')
        attach_disk.add_argument('-e', '--existing', help='attach an existing disk')
        attach_disk.set_defaults(func=self.attach_disk_to_vm)

    def add_detach_subcommands(self):
        # detach subcommand
        detach_subparser = self.detach_parser.add_subparsers(title='detach', description='detach a specified disk', help='disk')
        detach_disk = detach_subparser.add_parser('disk', help='detach a disk from a vm')
        detach_disk.add_argument('-r', '--resource_group', required=True, help='detach a disk to a vm within this group')
        detach_disk.add_argument('-n', '--name', required=True, help='detach a disk from a vm with this name')
        detach_disk.add_argument('-d', '--disk_name', required=True, help='detach a disk with this name')
        detach_disk.set_defaults(func=self.detach_disk_from_vm)

    def list_subscriptions(self, args):
        self.azure_ops.list_subscriptions()

    def list_resource_groups(self, args):
        self.azure_ops.list_resource_groups()
    
    def list_storage_accounts(self, args):
        self.azure_ops.list_storage_accounts(args.resource_group)
    
    def list_storage_containers(self, args):
        self.azure_ops.list_storage_container(args.storage_account)
    
    def list_virtual_machines(self, args):
        self.azure_ops.list_virtual_machines(args.resource_group, args.name)
    
    def list_virtual_networks(self, args):
        self.azure_ops.list_virtual_networks(args.resource_group, args.name)
    
    def list_subnetworks(self, args):
        if not args.resource_group:
            logger.debug('All subnets will be listed as resource group not specified.')
        self.azure_ops.list_subnetworks(args.resource_group, args.vnet, args.name)
    
    def list_network_interfaces(self, args):
        self.azure_ops.list_network_interfaces(args.resource_group)
    
    def list_vm_state(self, args):
        self.azure_ops.list_vm_state(args.resource_group, args.name)
    
    def list_vm_size(self, args):
        self.azure_ops.list_vm_size(args.resource_group, args.name)
    
    def list_public_ip(self, args):
        self.azure_ops.list_public_ip(args.resource_group)
    
    def list_vm_ip(self, args):
        self.azure_ops.list_vm_public_ip(args.resource_group, args.name)
        self.azure_ops.list_vm_private_ip(args.resource_group, args.name)

    def delete_resource_group(self, args):
        self.azure_ops.delete_resource_group(args.name)
    
    def delete_storage_account(self, args):
        self.azure_ops.delete_storage_account(args.resource_group, args.name)
    
    def delete_virtual_network(self, args):
        self.azure_ops.delete_vnet(args.resource_group, args.name)
    
    def delete_subnetwork(self, args):
        self.azure_ops.delete_subnet(args.resource_group, args.vnet, args.name)
    
    def delete_network_interface(self, args):
        self.azure_ops.delete_nic(args.resource_group, args.name)
    
    def delete_public_ip(self, args):
        self.azure_ops.delete_public_ip(args.resource_group, args.name)
    
    def delete_storage_container(self, args):
        self.azure_ops.delete_container(args.storage_account, args.name)
    
    def delete_blob(self, args):
        self.azure_ops.delete_blob(args.resource_group, args.storage_account, args.container, args.name, args.managed_disk)
    
    def delete_virtual_machine(self, args):
        self.azure_ops.delete_vm(args.resource_group, args.name, args.keep_data)
    
    def create_resource_group(self, args):
        self.azure_ops.create_resource_group(args.name, args.location)
    
    def create_storage_account(self, args):
        self.azure_ops.create_storage_account(args.resource_group, args.name, args.kind, args.type, args.access_tier)
    
    def create_storage_container(self, args):
        self.azure_ops.create_storage_container(args.storage_account, args.name)
    
    def create_virtual_network(self, args):
        self.azure_ops.create_vnet(args.resource_group, args.location, args.name, args.prefix)
    
    def create_subnetwork(self, args):
        self.azure_ops.create_subnet(args.resource_group, args.vnet, args.name, args.prefix)
    
    def create_network_interface(self, args):
        self.azure_ops.create_nic(args.resource_group, args.vnet, args.subnet, args.location, args.name)
    
    def create_virtual_machine(self, args):
        # for creating vms, publisher/offer/sku conflict with customized image
        if args.image: 
            if self.parsed_args.publisher or self.parsed_args.offer or self.parsed_args.sku:
                raise ValueError('publisher/offer/sku cannot be specified together with customized image')
            # if customized image used, the storage account where customized image located will be used
            sa_pat = re.compile('\s?https://(?P<storage_account>\w+)\..*')
            grp = sa_pat.search(args.image)
            if grp:
                storage_account = grp.group('storage_account')
                if args.storage_account and args.storage_account != storage_account:
                    raise ValueError('Please use the same storage account where your customized image is.')
            else:
                raise ValueError('Invalid image url provided.')
                
        self.azure_ops.create_vm(args.resource_group, args.storage_account, args.location, args.vm_size, args.name, args.vnet, args.subnet, args.ssh_key, args.publisher, args.offer, 
                args.sku, args.image, args.username, args.password, args.public_ip, args.static_ip)
    
    def create_public_ip(self, args):
        self.azure_ops.create_public_ip(args.resource_group, args.name, args.static)
        self.azure_ops.list_vm_public_ip(args.resource_group, args.name)
    
    def start_virtual_machine(self, args):
        self.azure_ops.start_vm(args.resource_group, args.name)
    
    def stop_virtual_machine(self, args):
        self.azure_ops.deallocate_vm(args.resource_group, args.name)
    
    def restart_virtual_machine(self, args):
        self.azure_ops.restart_vm(args.resource_group, args.name)
    
    def resize_virtual_machine(self, args):
        self.azure_ops.resize_vm(args.resource_group, args.name, args.vm_size)
    
    def list_vm_data_disk(self, args):
        self.azure_ops.list_data_disks(args.resource_group, args.name)
    
    def list_vhds(self, args):
        self.azure_ops.list_vhds(args.resource_group, args.storage_account, args.container, args.managed)

    def attach_disk_to_vm(self, args):
        self.azure_ops.attach_data_disk(args.resource_group, args.name, args.disk_name, args.disk_size, args.existing)
    
    def detach_disk_from_vm(self, args):
        self.azure_ops.detach_data_disk(args.resource_group, args.name, args.disk_name)

if __name__ == '__main__':
    try:
        ops = arg_parse()
        ops.run_cmd()
    except Exception as e:
        logger.error('{}'.format(e))
