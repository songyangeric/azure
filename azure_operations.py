import sys, os, argparse, json, re
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
import azure.mgmt.compute.models
import azure.mgmt.network.models 
import azure.mgmt.storage.models
from azure.mgmt.network.models import PublicIPAddress
from azure.mgmt.storage.models.sku import Sku
from azure.mgmt.storage.models.storage_account_create_parameters import StorageAccountCreateParameters
from azure.storage.blob.baseblobservice import BaseBlobService

# VM size and capacity mapping
supported_vm_sizes = {
    '7T' : 'Standard_F4',
    '8T' : 'Standard_F4',
    '15T' : 'Standard_F8',
    '16T' : 'Standard_F8',
    '32T' : 'Standard_D4_v2',
    '96T' : 'Standard_D15_v2'
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
            self.client_id = os.environ['AZURE_CLIENT_ID'] 
            self.secret_key = os.environ['AZURE_SECRET_KEY'] 
            self.tenant_id = os.environ['AZURE_TENANT_ID']
            self.subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']

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
            self.resource_client = ResourceManagementClient(credentials, self.subscription_id)
            self.storage_client = StorageManagementClient(credentials, self.subscription_id)
            self.compute_client = ComputeManagementClient(credentials, self.subscription_id)
            self.network_client = NetworkManagementClient(credentials, self.subscription_id)
        else:
            raise ValueError('No subscription specified, please check or create a new one') 

    def print_item(self, item):
        print '' 
        print '\tName: %s' % item.name
        print '\tId: %s' % item.id
        print '\tLocation: %s' % item.location

    def print_storage_account_info(self, sa):
        print ''
        print '\tName: {}'.format(sa.name)
        kind = str(sa.kind)
        kind = kind.split('.')[1]
        print '\tKind: {}'.format(kind)
        replication = str(sa.sku.name).split('.')[1] 
        print '\tReplication: {}'.format(replication)
        print '\tLocation: {}'.format(sa.location)

    def list_resource_groups(self):
        for rg in self.resource_client.resource_groups.list():
            self.print_item(rg)

    def list_resources(self, resource_group):
        for resource in self.resource_client.resource_groups.list_resources(resource_group):
            self.print_item(resource)       

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

    def create_storage_account(self, resource_group, sa_name, location, account_type = None, replication_type = None, access_tier = None):
        if account_type is None:
            account_type = 'Storage'
        elif account_type not in account_types:
            raise ValueError('Invalid account type')

        if replication_type is None:
            replication_type = 'Standard_LRS'
        elif replication_type not in replication_types:
            raise ValueError('Invalid replication type.')
        
        if account_type == 'BlobStorage':
            if replication_type not in ['Standard_LRS', 'Standard_RAGRS']:
                raise ValueError('Blob storage only supports Standard_LRS or Standard_RAGRS')
            if access_tier not in access_tiers:
                raise ValueError('You must specify access tier for Blob Storage account')
        else:
            access_tier = None
        
        # check account name availability
        valid_name = self.storage_client.storage_accounts.check_name_availability(sa_name)
        if not valid_name.name_available:
            raise ValueError(valid_name.message)

        param = StorageAccountCreateParameters(sku = Sku(replication_type), kind = account_type, location = location, access_tier = access_tier)  
        async_sa_create = self.storage_client.storage_accounts.create(
                              resource_group,
                              sa_name,
                              param
                          )
        async_sa_create.wait()

    def delete_storage_account(self, resource_group, sa_name):
        async_sa_delete = self.storage_client.storage_accounts.delete(
                              resource_group,
                              sa_name
                          )

    def list_storage_account_primary_key(self, resource_group, storage_account):
        storage_account_keys = self.storage_client.storage_accounts.list_keys(resource_group, storage_account)
        storage_account_keys_map = {v.key_name: v.value for v in storage_account_keys.keys}
        storage_account_primary_key = storage_account_keys_map['key1']
        
        return storage_account_primary_key

    def create_storage_container(self, resource_group, storage_account, container):
        if re.search(r'[^-0-9a-z]', container) is not None: 
            raise ValueError('Invalid container name. Only '-', small letters and digits are allowed.')

        account_key = self.list_storage_account_primary_key(resource_group, storage_account)

        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        create_container = blob_service.create_container(container_name = container)

    def list_storage_container(self, resource_group, storage_account):
        account_key = self.list_storage_account_primary_key(resource_group, storage_account)

        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        containers = blob_service.list_containers()
        for container in containers:
            print container.name

    def list_vhd_per_container(self, blob_service, storage_account, container):
        blobs = blob_service.list_blobs(container_name = container)
        for blob in blobs:
            if re.search(r'\.vhd', blob.name):
                print '{}/{}/{}: {}/{}'.format(storage_account, container, blob.name, 
                       blob.properties.lease.status, blob.properties.lease.state)

    def list_vhd_per_storage_account(self, resource_group, storage_account, container):
        account_key = self.list_storage_account_primary_key(resource_group, storage_account)

        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        if container:
            self.list_vhd_per_container(blob_service, storage_account, container)
        else:
            containers = blob_service.list_containers()
            for container in containers:
                self.list_vhd_per_container(blob_service, storage_account, container.name)

    def list_vhds(self, resource_group, storage_account, container):
        if storage_account is None:
            storage_accounts = self.storage_client.storage_accounts.list_by_resource_group(resource_group)
            for storage_account in storage_accounts:
                self.list_vhd_per_storage_account(resource_group, storage_account.name)
        else:
            self.list_vhd_per_storage_account(resource_group, storage_account, container)

    def print_vm_info(self, resource_group, vm_obj):
        print ''
        print 'VM UUID : {}'.format(vm_obj.vm_id)
        print 'VM Name : {}'.format(vm_obj.name)
        print 'VM Size : {}'.format(vm_obj.hardware_profile.vm_size)
        self.list_vm_state(resource_group, vm_obj.name)
        self.list_vm_public_ip(resource_group, vm_obj.name)
        self.list_vm_private_ip(resource_group, vm_obj.name)
        os_disk_ref = vm_obj.storage_profile.os_disk
        if os_disk_ref.vhd:
            print 'VM OS Disk : '
            print '  {}'.format(os_disk_ref.vhd.uri)
        data_disk_refs = vm_obj.storage_profile.data_disks
        if data_disk_refs:
            print 'VM Data Disk : '
            for data_disk_ref in data_disk_refs:
                if data_disk_ref.vhd:
                    print '  {}'.format(data_disk_ref.vhd.uri)
                print '  lun : {}'.format(data_disk_ref.lun)
                print '  size : {} GiB'.format(data_disk_ref.disk_size_gb) 
            

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
        print 'VM Size : {}'.format(vm_size)
        
    def list_vm_state(self, resource_group, vmname):
        vm = self.get_vm(resource_group, vmname)
        state = vm.instance_view.statuses[0].display_status
        # VM may not be successfully deployed in below case
        if state == 'Provisioning succeeded':
            state = vm.instance_view.statuses[1].display_status
        print 'VM Status : {}'.format(state)
        return state

    def get_vm(self, resource_group, vmname, expand = 'instanceview'):
        try:
            virtual_machine = self.compute_client.virtual_machines.get(
                                  resource_group,
                                  vmname,
                                  expand  
                              ) 
        except Exception as e:
            virtual_machine = None
        
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
        os_disk_uri = os_disk.vhd.uri

        os_disk_container = os_disk_uri.split('/')[3]
        os_disk_blob_name = os_disk_uri.split('/')[4]
        os_disk_storage_account_name = os_disk_uri.split('/')[2].split('.')[0]
        
        self.delete_blob(resource_group, os_disk_storage_account_name, os_disk_container, os_disk_blob_name)

        # Delete all the data disks
        if not keep_data:
            for data_disk in data_disks:
                data_disk_uri = data_disk.vhd.uri
                data_disk_container = data_disk_uri.split('/')[3]
                data_disk_blob_name = data_disk_uri.split('/')[4]
                data_disk_storage_account_name = data_disk_uri.split('/')[2].split('.')[0]
    
                self.delete_blob(resource_group, data_disk_storage_account_name, data_disk_container, data_disk_blob_name)
 
    def delete_container(self, resource_group, storage_account, container):
        account_key = self.list_storage_account_primary_key(resource_group, storage_account)
        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        blob_service.delete_container(container_name = container)

    def delete_blob(self, resource_group, storage_account, container, blob_name):
        account_key = self.list_storage_account_primary_key(resource_group, storage_account)
        blob_service = BaseBlobService(account_name = storage_account ,account_key = account_key)
        blob_service.delete_blob(container_name = container, blob_name = blob_name)
        
        remaining_blobs = blob_service.list_blobs(container_name = container)
        if len(list(remaining_blobs)) == 0:
            delete_container = blob_service.delete_container(container_name = container)

    def list_data_disks(self, resource_group, vmname):
        virtual_machine = self.get_vm(resource_group, vmname)
        if virtual_machine is None:
            return
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [disk for disk in data_disks if 'nvram' not in disk.name.lower()]
        for disk in data_disks:
            print ''
            print 'LUN : {}'.format(disk.lun)
            print 'Disk name : {}'.format(disk.name)
            print 'VHD : {}'.format(disk.vhd.uri)
            print 'Disk size in GiB: {}'.format(disk.disk_size_gb)

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

    def list_virtual_networks(self, resource_group):
        for vnet in self.network_client.virtual_networks.list(resource_group):
            self.print_item(vnet)

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

    def list_subnetworks(self, resource_group, vnet):
        for subnet in self.network_client.subnets.list(resource_group, vnet):
            print '' 
            print '\tName: %s' % subnet.name
            print '\tId: %s' % subnet.id

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
            print private_ip

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
        
        print 'VM Public IP : {}'.format(','.join(public_ips))

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

        print 'VM Private IP :\n {}'.format(','.join(private_ips))

    def create_nic(self, resource_group, vnet, subnet, location, nic_name):
        subnet_ref = self.network_client.subnets.get(resource_group, vnet, subnet)
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
                async_nic_delete = self.network_client.public_ip_addresses.delete(resource_group, pub_ip_name)
                async_nic_delete.wait()


    def create_public_ip(self, resource_group, vmname, static_ip = False):
        if static_ip:
            create_opt = 'Static'
        else:
            create_opt = 'Dynamic'

        vm = self.get_vm(resource_group, vmname)
        for nic_ref in vm.network_profile.network_interfaces:
            if nic_ref.primary:
                nic_name = nic_ref.id.split('/')[8]
                break

        nic = self.network_client.network_interfaces.get(resource_group, nic_name)
        # first create a public ip
        public_ip_obj = self.network_client.public_ip_addresses
        async_ip_create = public_ip_obj.create_or_update(
                              resource_group, 
                              nic_name,
                              PublicIPAddress(location = nic.location, public_ip_allocation_method = create_opt)
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

    def create_vm(self, resource_group, storage_account, vm_size, vmname, vnet, subnet_list, ssh_public_key = None, publisher = None, offer = None, sku = None, username = None, password = None, public_ip = False, static_public_ip = False):
        rg_ref = self.resource_client.resource_groups.get(resource_group)
        if rg_ref is None:
            raise ValueError('The specified resource group {} dose not exist.'.format(resource_group))
        # determine location
        location = rg_ref.location

        if not self.storage_account_within_resource_group(resource_group, storage_account):
            raise ValueError('Storage account {} not in resource group {}.'.format(storage_account, resource_group))

        # vmname check
        if re.search(r'[^-0-9A-Za-z]', vmname) is not None:
            raise ValueError('Illegal vm name. Only digits, letters and - can be used.')
        
        # vm check
        vm_obj = self.get_vm(resource_group, vmname)
        if vm_obj:
            raise ValueError('Illegal vm name. The specified vm already exists.')

        # offer related check
        if publisher is None:
            publisher = 'dellemc'

        if offer is None:
            offer = 'dell-emc-datadomain-virtual-edition'

        if sku is None:
            raise ValueError('SKU must be specified.')

        # default username
        if username is None:
            username = 'sysadmin'

        # authentication check 
        if password is None and ssh_public_key is None:
            raise ValueError('Either Password or SSH Public Key must be specified.')
        
        # size check
        if supported_vm_sizes.get(vm_size.upper()) is None:
            raise ValueError('Wrong capacity {} provided.'.format(vm_size))
        else:
            vm_size = supported_vm_sizes[vm_size.upper()]

        # vnet check
        vnet_ref = self.network_client.virtual_networks.get(resource_group, vnet)
        if vnet_ref is None:
            raise ValueError('Virtual network {} does not exist.'.format(vnet))
       
        # subnets check
        subnets = subnet_list.split(',')
        for subnet in subnets:
            subnet_ref = self.network_client.subnets.get(resource_group, vnet, subnet.strip())
            if subnet_ref is None:
                raise ValueError('Subnet {} does not exist.'.format(subnet))
            
        # create nic
        nic_num = 1
        nic_ids = []
        for subnet in subnets:
            nic_name = vmname + '-nic{}'.format(nic_num) 
            nic_ref = self.create_nic(resource_group, vnet, subnet.strip(), location, nic_name)
            nic_id = nic_ref.id
            nic_ids.append(nic_id)
            nic_num += 1
        
        # create storage container 
        container = '{}-vhds'.format(vmname)
        self.create_storage_container(resource_group, storage_account, container)
       
        # template parameters
        try:
            parameters = self.create_vm_parameters(location = location, storage_account = storage_account,
                              container = container, vm_size = vm_size, vmname = vmname, 
                              nic_ids = nic_ids, ssh_public_key = ssh_public_key, 
                              publisher = publisher, offer = offer, sku = sku,
                              username = username, password = password, need_plan = True)
        
            async_vm_create = self.compute_client.virtual_machines.create_or_update(
                                  resource_group,
                                  vmname,
                                  parameters
                              )
            async_vm_create.wait()
        except Exception:
            parameters = self.create_vm_parameters(location = location, storage_account = storage_account, 
                              container = container, vm_size = vm_size, vmname = vmname, 
                              nic_ids = nic_ids, ssh_public_key = ssh_public_key, 
                              publisher = publisher, offer = offer, sku = sku,
                              username = username, password = password, need_plan = False)
            try:
                async_vm_create = self.compute_client.virtual_machines.create_or_update(
                                      resource_group,
                                      vmname,
                                      parameters
                                  )
                async_vm_create.wait()
            except Exception:
               for subnet in subnets:
                   nic_name = vmname + '-nic{}'.format(nic_num)
                   self.delete_nic(resource_group, nic_name)
               self.delete_container(resource_group, storage_account, container)
                 
        # add a public ip if needed
        if public_ip:
            if static_public_ip:
                self.create_public_ip(resource_group, vmname, True)
            else:
                self.create_public_ip(resource_group, vmname, False)

    def create_vm_parameters(self, location, storage_account, container, vm_size, vmname, 
                             nic_ids, ssh_public_key, publisher, offer, sku, username, password, need_plan = True):
        plan = None
        if need_plan:
            plan = azure.mgmt.compute.models.Plan(name = sku, publisher = publisher, product = offer)
       
        # hardware profile 
        hardware_profile = azure.mgmt.compute.models.HardwareProfile(vm_size = vm_size)
     
        # os profile
        linux_config = None
        if ssh_public_key:
            key_path = '/home/{}/.ssh/authorized_keys'.format(username)
            public_key = azure.mgmt.compute.models.SshPublicKey(path = key_path, key_data = ssh_public_key)
            public_keys = [public_key]
            ssh_config = azure.mgmt.compute.models.SshConfiguration(public_keys = public_keys)
            linux_config = azure.mgmt.compute.models.LinuxConfiguration(disable_password_authentication = False,
                           ssh = ssh_config)
        os_profile = azure.mgmt.compute.models.OSProfile(computer_name = vmname, admin_username = username, 
                     admin_password = password, linux_configuration = linux_config)
        
        image_ref = azure.mgmt.compute.models.ImageReference(publisher = publisher, offer = offer,
                    sku = sku, version = 'latest') 
        
        # create_option: fromImage, empty, attach  
        os_vhd_uri = 'https://{}.blob.core.windows.net/{}/{}-os.vhd'.format(storage_account, container, vmname) 
        os_vhd = azure.mgmt.compute.models.VirtualHardDisk(uri = os_vhd_uri)
        os_disk_ref = azure.mgmt.compute.models.OSDisk(create_option = 'fromImage', name = 'osDisk', vhd = os_vhd)
        
        data_vhd_uri = 'https://{}.blob.core.windows.net/{}/{}-nvram.vhd'.format(storage_account, container, vmname) 
        data_vhd = azure.mgmt.compute.models.VirtualHardDisk(uri = data_vhd_uri)
        data_disk_ref = azure.mgmt.compute.models.DataDisk(lun = 0, disk_size_gb = 10, create_option = 'empty', name = 'nvramDisk', vhd = data_vhd)
        data_disk_refs = [data_disk_ref]
        
        storage_profile = azure.mgmt.compute.models.StorageProfile(image_reference = image_ref, os_disk = os_disk_ref,
                          data_disks = data_disk_refs)
        # network profile
        nic_list = []
        primary_nic = True 
        for nic_id in nic_ids:
            if primary_nic:
                nic_ref = azure.mgmt.compute.models.NetworkInterfaceReference(id = nic_id, primary = True)
                primary_nic = False
            else:
                nic_ref = azure.mgmt.compute.models.NetworkInterfaceReference(id = nic_id, primary = False)
            nic_list.append(nic_ref)
      
        network_profile = azure.mgmt.compute.models.NetworkProfile(network_interfaces = nic_list)

        # dianostic profile
        storage_uri = 'https://{}.blob.core.windows.net'.format(storage_account)
        boot_diagnostics = azure.mgmt.compute.models.BootDiagnostics(enabled = True, storage_uri = storage_uri)
        diagnostics_profile = azure.mgmt.compute.models.DiagnosticsProfile(boot_diagnostics = boot_diagnostics) 

        # build template_params 
        vm_create_params = azure.mgmt.compute.models.VirtualMachine(
                           plan = plan,
                           location = location,
                           os_profile = os_profile,
                           hardware_profile = hardware_profile,
                           network_profile = network_profile,
                           storage_profile = storage_profile,
                           diagnostics_profile = diagnostics_profile)

        return vm_create_params 

    def resize_vm(self, resource_group, vmname, vm_size):
        if supported_vm_sizes.get(vm_size.upper()) is None:
            raise ValueError('Wrong capacity {} provided.'.format(vm_size))
        else:
            vm_size = supported_vm_sizes[vm_size.upper()]
        
        # first stop the vm 
        self.deallocate_vm(resource_group, vmname)
        # second change vm size
        vm = self.get_vm(resource_group, vmname)
        vm.hardware_profile.vm_size = vm_size
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
                               resource_group,
                               vmname,
                               vm
                          )
        async_vm_update.wait()
        # last start the vm 
        self.start_vm(resource_group, vmname)

    def attach_data_disk(self, resource_group, vmname, disk_name, disk_size, existing = None):
        if (int(disk_size) < 1):
            disk_size = 1
        elif (int(disk_size) > 1023):
            disk_size = 1023

        vm = self.get_vm(resource_group, vmname)
        #make sure data disks are put under the same container with the os disk_name
        os_disk = vm.storage_profile.os_disk
        disk_uri = os_disk.vhd.uri
        disk_uri = disk_uri[0:disk_uri.rfind('/')]

        if existing is not None:
            create_opt = 'attach'
            disk_uri = existing
        else:
            create_opt = 'empty'
            disk_uri = '{}/{}.vhd'.format(disk_uri, disk_name)

        data_disks = vm.storage_profile.data_disks
        #find an available lun
        used_luns = []
        for data_disk in data_disks:
            used_luns.append(data_disk.lun)
        for i in range(100):
            if i not in used_luns:
                available_lun = i
                break

        data_disks.append(azure.mgmt.compute.models.DataDisk(
                       lun = available_lun,
                       name = disk_name, 
                       disk_size_gb = disk_size,
                       vhd = {
                           'uri': disk_uri 
                           },
                       create_option = create_opt
                       )
                  )
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
                               resource_group,
                               vmname,
                               vm
                          )
        async_vm_update.wait()

    def get_vm_state(self, resource_group, vmname):
        vm = self.compute_client.virtual_machines.get_with_instance_view(resource_group, vmname).virtual_machine
        vm_status = vm.instance_view.statuses[1].display_state

class arg_parse:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')
        self.list_parser = self.subparsers.add_parser('list', description='list a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic | vm_state | vm_ip | vm_disk')
        self.create_parser = self.subparsers.add_parser('create', description='create a specified resource', help='resource_group | storage_account | container | vm | vnet | subnet | nic | public_ip')
        self.delete_parser = self.subparsers.add_parser('delete', description='delete a specified resource', help='resource_group | storage_account | container | vm | vnet | subnet | nic | container | blob')
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
        # list resource groups
        list_rg = list_subparser.add_parser('resource_group', help='list resource groups')
        list_rg.set_defaults(func=self.list_resource_groups)
        # list all resources within a resource group
        list_re = list_subparser.add_parser('resource', help='list all resources')
        list_re.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
        list_re.set_defaults(func=self.list_resources)
        # list storage accounts
        list_sa = list_subparser.add_parser('storage_account', help='list storage accounts')
        list_sa.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
        list_sa.set_defaults(func=self.list_storage_accounts)
        # list storage containers
        list_sa = list_subparser.add_parser('container', help='list storage containers')
        list_sa.add_argument('-r', '--resource_group', help='list storage containers within a resource group')
        list_sa.add_argument('-s', '--storage_account', help='list storage containers within a storage_account')
        list_sa.set_defaults(func=self.list_storage_containers)
        # list vms
        list_vm = list_subparser.add_parser('vm', help='list vms within a resource group')
        list_vm.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_vm.add_argument('-n', '--name', help='list a specific vm')
        list_vm.set_defaults(func=self.list_virtual_machines)
        # list vnets
        list_vnet = list_subparser.add_parser('vnet', help='list vnets within a resource group')
        list_vnet.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_vnet.set_defaults(func=self.list_virtual_networks)
        # list subnets
        list_subnet = list_subparser.add_parser('subnet', help='list subnets within a resource group')
        list_subnet.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_subnet.add_argument('-v', '--vnet', required=True, help='list resources wihtin this vnet')
        list_subnet.set_defaults(func=self.list_subnetworks)
        # list nics
        list_nic = list_subparser.add_parser('nic', help='list nics within a resource group')
        list_nic.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_nic.set_defaults(func=self.list_network_interfaces)
        # list a vm's state
        list_state = list_subparser.add_parser('vm_state', help="list a vm's state within a resource group")
        list_state.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_state.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_state.set_defaults(func=self.list_vm_state)
        # list a vm's ip 
        list_ip = list_subparser.add_parser('vm_ip', help="list a vm's state within a resource group")
        list_ip.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_ip.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_ip.set_defaults(func=self.list_vm_ip)
        # list a vm's data disks
        list_disk = list_subparser.add_parser('vm_disk', help="list a vm's data disks")
        list_disk.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_disk.add_argument('-n', '--name', required=True, help='list a specific vm')
        list_disk.set_defaults(func=self.list_vm_data_disk)
        # list vhds within a storage account 
        list_disk = list_subparser.add_parser('vhd', help="list vhds within a storage account")
        list_disk.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
        list_disk.add_argument('-s', '--storage_account', help='list vhds within this storage account')
        list_disk.add_argument('-c', '--container', help='list vhds within this storage container')
        list_disk.set_defaults(func=self.list_vhds)

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
        create_sa.add_argument('-l', '--location', required=True, help='create a storage account within this region')
        create_sa.add_argument('-t', '--type', help='create a storage account with this type')
        create_sa.set_defaults(func=self.create_storage_account)
        # create storage container
        create_container = create_subparser.add_parser('container', help='create a storage container')
        create_container.add_argument('-r', '--resource_group', required=True, help='create a storage container within this resource group')
        create_container.add_argument('-s', '--storage_account', required=True, help='create a storage container within this storage account')
        create_container.add_argument('-n', '--name', required=True, help='create a storage container with this name')
        create_container.set_defaults(func=self.create_storage_container)
        # create vm
        create_vm = create_subparser.add_parser('vm', help='create vms within a resource group')
        create_vm.add_argument('-r', '--resource_group', required=True, help='create a vm wihtin this resource group')
        create_vm.add_argument('-s', '--storage_account', required=True, help='create a vm wiht this storage account')
        create_vm.add_argument('-c', '--vm_size', required=True, help='create a vm with this size')
        create_vm.add_argument('-n', '--name', required=True, help='create a vm with this name')
        create_vm.add_argument('-v', '--vnet', required=True, help='create a vm with this vnet')
        create_vm.add_argument('-e', '--subnet', required=True, help='create a vm with 2 subnets')
        create_vm.add_argument('-k', '--ssh_key', help='create a vm with this ssh key')
        create_vm.add_argument('-u', '--username', help='create a vm with this username')
        create_vm.add_argument('-p', '--password', help='create a vm with login password')
        create_vm.add_argument('-P', '--publisher', help='create a vm from this publisher')
        create_vm.add_argument('-O', '--offer', help='create a vm from this offer')
        create_vm.add_argument('-S', '--sku', help='create a vm from this sku')
        create_vm.add_argument('--public_ip', action='store_true', help='create a vm with public ip')
        create_vm.add_argument('--static_ip', action='store_true', help='create a vm with a static ip')
        create_vm.set_defaults(func=self.create_virtual_machine)
        # create vnet
        create_vnet = create_subparser.add_parser('vnet', help='create vnets within a resource group')
        create_vnet.add_argument('-r', '--resource_group', required=True, help='create a vnet wihtin this group')
        create_vnet.add_argument('-n', '--name', required=True, help='create a vnet with this name')
        create_vnet.add_argument('-l', '--location', required=True, help='create a vnet within this location')
        create_vnet.add_argument('-p', '--prefix', required=True, help='create a vnet with this address prefix')
        create_vnet.set_defaults(func=self.create_virtual_network)
        # create subnet
        create_subnet = create_subparser.add_parser('subnet', help='create subnets within a resource group')
        create_subnet.add_argument('-r', '--resource_group', required=True, help='create a subnet wihtin this group')
        create_subnet.add_argument('-v', '--vnet', required=True, help='create a subnet with this vnet')
        create_subnet.add_argument('-n', '--name', required=True, help='create a subnet with this name')
        create_subnet.add_argument('-p', '--prefix', required=True, help='create a subnet with this address prefix')
        create_subnet.set_defaults(func=self.create_subnetwork)
        # create nic
        create_nic = create_subparser.add_parser('nic', help='create nics within a resource group')
        create_nic.add_argument('-r', '--resource_group', required=True, help='create a nic wihtin this group')
        create_nic.add_argument('-v', '--vnet', required=True, help='create a nic with this vnet')
        create_nic.add_argument('-e', '--subnet', required=True, help='create a nic with this subnet')
        create_nic.add_argument('-l', '--location', required=True, help='create a nic within this location')
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
        delete_vm = delete_subparser.add_parser('vm', help='delete vms within a resource group')
        delete_vm.add_argument('-r', '--resource_group', required=True, help='delete a vm wihtin this resource group')
        delete_vm.add_argument('-n', '--name', required=True, help='delete a vm with this name')
        delete_vm.add_argument('--keep_data', action='store_true', help='delete a vm but keep the data disks')
        delete_vm.set_defaults(func=self.delete_virtual_machine)
        # delete vnet
        delete_vnet = delete_subparser.add_parser('vnet', help='delete vnets within a resource group')
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
        # delete container
        delete_container = delete_subparser.add_parser('container', help='delete container within a storage account')
        delete_container.add_argument('-s', '--storage_account', required=True, help='delete a container within this storage account')
        delete_container.add_argument('-r', '--resource_group', required=True, help='delete a container within this group')
        delete_container.add_argument('-n', '--name', required=True, help='delete a container with this name')
        delete_container.set_defaults(func=self.delete_storage_container)
        # delete a page blob 
        delete_blob = delete_subparser.add_parser('blob', help='delete a blob within a storage account')
        delete_blob.add_argument('-r', '--resource_group', required=True, help='delete a page blob within this group')
        delete_blob.add_argument('-s', '--storage_account', required=True, help='delete a page blob within this storage account')
        delete_blob.add_argument('-c', '--container', required=True, help='delete a page blob within this container')
        delete_blob.add_argument('-n', '--name', required=True, help='delete a blob with this name')
        delete_blob.set_defaults(func=self.delete_page_blob)

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

    def list_resources(self, args):
        self.azure_ops.list_resources(args.resource_group)
    
    def list_resource_groups(self, args):
        self.azure_ops.list_resource_groups()
    
    def list_storage_accounts(self, args):
        self.azure_ops.list_storage_accounts(args.resource_group)
    
    def list_storage_containers(self, args):
        self.azure_ops.list_storage_container(args.resource_group, args.storage_account)
    
    def list_virtual_machines(self, args):
        self.azure_ops.list_virtual_machines(args.resource_group, args.name)
    
    def list_virtual_networks(self, args):
        self.azure_ops.list_virtual_networks(args.resource_group)
    
    def list_subnetworks(self, args):
        self.azure_ops.list_subnetworks(args.resource_group, args.vnet)
    
    def list_network_interfaces(self, args):
        self.azure_ops.list_network_interfaces(args.resource_group)
    
    def list_vm_state(self, args):
        state = self.azure_ops.list_vm_state(args.resource_group, args.name)
    
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
    
    def delete_storage_container(self, args):
        self.azure_ops.delete_container(args.resource_group, args.storage_account, args.name)
    
    def delete_page_blob(self, args):
        self.azure_ops.delete_blob(args.resource_group, args.storage_account, args.container, args.name)
    
    def delete_virtual_machine(self, args):
        self.azure_ops.delete_vm(args.resource_group, args.name, args.keep_data)
    
    def create_resource_group(self, args):
        self.azure_ops.create_resource_group(args.name, args.location)
    
    def create_storage_account(self, args):
        self.azure_ops.create_storage_account(args.resource_group, args.name, args.location, args.type)
    
    def create_storage_container(self, args):
        self.azure_ops.create_storage_container(args.resource_group, args.storage_account, args.name)
    
    def create_virtual_network(self, args):
        self.azure_ops.create_vnet(args.resource_group, args.location, args.name, args.prefix)
    
    def create_subnetwork(self, args):
        self.azure_ops.create_subnet(args.resource_group, args.vnet, args.name, args.prefix)
    
    def create_network_interface(self, args):
        self.azure_ops.create_nic(args.resource_group, args.vnet, args.subnet, args.location, args.name)
    
    def create_virtual_machine(self, args):
        self.azure_ops.create_vm(args.resource_group, args.storage_account, args.vm_size, args.name, args.vnet, args.subnet, args.ssh_key, args.publisher, args.offer, args.sku, args.username, args.password, args.public_ip, args.static_ip)
    
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
        self.azure_ops.list_vhds(args.resource_group, args.storage_account, args.container)
    
    def attach_disk_to_vm(self, args):
        self.azure_ops.attach_data_disk(args.resource_group, args.name, args.disk_name, args.disk_size, args.existing)
    
    def detach_disk_from_vm(self, args):
        self.azure_ops.detach_data_disk(args.resource_group, args.name, args.disk_name)

if __name__ == '__main__':
    try:
        ops = arg_parse()
        ops.run_cmd()
    except Exception as e:
        print '{}'.format(e)
