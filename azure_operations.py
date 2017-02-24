import sys, os, argparse, json, re
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.compute.models import DataDisk
from azure.mgmt.compute.models import VirtualHardDisk
from azure.mgmt.resource.resources.models import DeploymentMode
from azure.mgmt.network.models import PublicIPAddress
from azure.mgmt.storage.models.sku import Sku
from azure.mgmt.storage.models.storage_account_create_parameters import StorageAccountCreateParameters

# VM size and capacity mapping
supported_vm_sizes = {
    '4T' : 'Standard_D2_v2',
    '8T' : 'Standard_F4',
    '16T' : 'Standard_F8',
}
# storage account types
account_types = ['Standard_LRS', 'Standard_GRS', 'Standard_RAGRS', 
    'Standard_ZRS', 'Premium_LRS']

class azure_operations:

    def __init__(self, client, key, tenant, subscription_id):
        self.client_id = client
        self.secret_key = key
        self.tenant_id = tenant
        self.subscription_id = subscription_id

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

    def list_resource_groups(self):
        for rg in self.resource_client.resource_groups.list():
            self.print_item(rg)

    def list_resources(self, resource_group):
        for resource in self.resource_client.resource_groups.list_resources(resource_group):
            self.print_item(resource)       

    def create_resource_group(self, rg_name, region):
        async_create = self.resource_client.resource_groups.create_or_update(
            rg_name,
            {
                'location' : region
            }
        )

    def delete_resource_group(self, resource_group):
        delete_done = self.resource_client.resource_groups.delete(resource_group)
        delete_done.wait()
        if resource_group in self.resource_client.resource_groups.list():
            raise SystemError('Failed to delete resource group %s' % resource_group)

    def list_storage_accounts(self, resource_group = None):
        if resource_group is not None:
            for sa in self.storage_client.storage_accounts.list_by_resource_group(resource_group):
                self.print_item(sa)
        else:
            for sa in self.storage_client.storage_accounts.list():
                self.print_item(sa)

    def create_storage_account(self, resource_group, sa_name, region, account_type):
        if account_type is None:
            account_type = 'Standard_LRS'
        elif account_type not in account_types:
            raise ValueError('Invalid account type.')

        # check account name availability
        valid_name = self.storage_client.storage_accounts.check_name_availability(sa_name)
        if not valid_name.name_available:
            raise ValueError(valid_name.message)
        param = StorageAccountCreateParameters(sku = Sku(account_type), kind = 'Storage', location = region)  
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

    def print_vm_info(self, resource_group, vm_obj):
        print ''
        print 'VM UUID : {}'.format(vm_obj.vm_id)
        print 'VM ID : {}'.format(vm_obj.id)
        print 'VM Name : {}'.format(vm_obj.name)
        print 'VM Size : {}'.format(vm_obj.hardware_profile.vm_size)
        print 'VM Status : {}'.format(self.list_vm_state(resource_group, vm_obj.name))
        print 'VM Pulbic IP: {}'.format(self.list_vm_public_ip(resource_group, vm_obj.name))
        print 'VM Private IP: {}'.format(self.list_vm_private_ip(resource_group, vm_obj.name))

    def list_virtual_machines(self, resource_group, vmname = None):
        if vmname is None:
            for vm in self.compute_client.virtual_machines.list(resource_group):
                self.print_vm_info(resource_group, vm)
        else:
            vm = self.get_vm(resource_group, vmname)
            self.print_vm_info(resource_group, vm)

    def list_vm_state(self, resource_group, vmname):
        vm = self.get_vm(resource_group, vmname)
        state = vm.instance_view.statuses[1].display_status
        return state

    def get_vm(self, resource_group, vmname, expand = 'instanceview'):
        virtual_machine = self.compute_client.virtual_machines.get(
            resource_group,
            vmname,
            expand  
        )    
        if virtual_machine is None:
            print 'No virtual machine named %s found.' % vmname
        return virtual_machine

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

    def stop_vm(self, resource_group, vmname):
        async_vm_stop = self.compute_client.virtual_machines.power_off(
            resource_group,
            vmname
        )
        async_vm_stop.wait()

    def delete_vm(self, resource_group, vmname):
        async_vm_delete = self.compute_client.virtual_machines.delete(
            resource_group,
            vmname
        )
        async_vm_delete.wait()

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

    def create_vnet(self, resource_group, region, vnet_name, addr_prefix = "10.0.0.0/16"):
        async_vnet_create = self.network_client.virtual_networks.create_or_update(
                resource_group,
                vnet_name,
                {
                    'location' : region,
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
            self.print_item(nic)

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
            public_ips.append(public_ip.ip_address)

        return public_ips

    def list_vm_private_ip(self, resource_group, vmname, nic_names = None):
        if nic_names is None:
            nic_names = []
            vm = self.get_vm(resource_group, vmname)
            for nic_ref in vm.network_profile.network_interfaces:
                nic_names.append(nic_ref.id.split('/')[8])
        private_ips = []
        for nic_name in nic_names:
            nic = self.network_client.network_interfaces.get(resource_group, nic_name)
            private_ip = nic.ip_configurations[0].private_ip_address
            private_ips.append(private_ip)

        return private_ips

    def create_nic(self, resource_group, vnet, subnet, region, nic_name):
        subnet_ref = self.network_client.subnets.get(resource_group, vnet, subnet)
        if subnet_ref is None:
            raise ValueError("The specified subnet does not exist.")

        async_nic_create = self.network_client.network_interfaces.create_or_update(
            resource_group,
            nic_name,
            {
                'location' : region,
                'ip_configurations' : [{
                    'name' : nic_name,
                    'subnet' : {
                        'id' : subnet_ref.id
                    }
                }]
            }
        )
        async_nic_create.wait()

    def delete_nic(self, resource_group, nic):
        async_nic_delete = self.network_client.network_interfaces.delete(
            resource_group,
            nic
        )
        async_nic_delete.wait()

    def create_public_ip(self, resource_group, vmname, static_ip):
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

    def parse_vm_parameters(nics, vm_reference):
        return {
                'location' : vm_reference['loc'],
                'os_profile' : {
                    'computer_name' : vm_reference['name'],
                    'admin_username' : vm_reference['username'],
                    'admin_password' : vm_reference['password'],
                    },
                'hardware' : {
                    'vm_size' : vm_reference['vm_size'],
                    },
                'storage_profile' : {
                    'image_reference' : {
                        'publisher' : vm_reference['publisher'],
                        'offer' : vm_reference['offer'],
                        'sku' : vm_reference['sku'],
                        'version' : vm_reference['version'],
                        },
                    'os_disk' : {
                        'name' : vm_reference['name'] + '_osdisk',
                        'caching' : 'None',
                        'create_option' : 'fromimage',
                        'vhd' : {
                            'uri' : 'https://%s.blob.core.windows.net/vhds/%s.vhd' % (
                                vm_reference['sa'],
                                vm_reference['template']
                                )
                            }
                        },
                    },
                'network_profile' : {
                    'network_interfaces' : [{
                        'id' : nics[0].id
                        }, 
                        {
                            'id' : nics[1].id
                            }]
                        },
                }

    def create_vm(self, resource_group, storage_account, location, vm_size, template_file, vmname, vnet, subnet_list, ssh_key_file = None, os_uri = None):
        public_ssh_key = None
        if ssh_key_file:
            with open(ssh_key_file, 'r') as pub_ssh_file_fd:
                public_ssh_key = pub_ssh_file_fd.read()

        template = None
        if not os.path.exists(template_file):
            raise ValueError('Template {} does not exist.'.format(template_file))
        with open(template_file, 'r') as template_file_fd:
            template = json.load(template_file_fd)
    
        #vmname check
        if re.search(r'[^-0-9A-Za-z]', vmname) is not None:
            raise ValueError('Illegal vm name. Only digits, letters and - can be used.')

        # subnets check
        subnets = subnet_list.split(',')
        if len(subnets) != 2:
            raise ValueError('Two subnets are needed to create a vm')
        subnet_ref = self.network_client.subnets.get(resource_group, vnet, subnets[0])
        if subnet_ref is None:
            raise ValueError('Subnet {} does not exist.'.format(subnet[0]))
        subnet_ref = self.network_client.subnets.get(resource_group, vnet, subnets[1])
        if subnet_ref is None:
            raise ValueError('Subnet {} does not exist.'.format(subnet[1]))
        # vnet check
        vnet_ref = self.network_client.virtual_networks.get(resource_group, vnet)
        if vnet_ref is None:
            raise ValueError('Virtual network {} does not exist.'.format(vnet))

        if os_uri is None:
            raise ValueError('OSDisk does not exist.')

        if supported_vm_sizes.get(vm_size.upper()) is None:
            raise ValueError('Wrong capacity {} provided.'.format(vm_size))
        else:
            vm_size = supported_vm_sizes[vm_size.upper()]

        parameters = {
            #'sshKeyData' : public_ssh_key,
            'storageAccountName' : storage_account,
            'location' : location,
            'vmSize' : vm_size,
            'vmName' : vmname,
            'virtualNetworkName' : vnet,
            'subnetName1' : subnets[0],
            'subnetName2' : subnets[1],
            'adminUsername' : 'sysadmin',
            'adminPassword' : 'Asdfgh123!',
            'os_uri' : os_uri
        }
        parameters = {k : {'value': v} for k, v in parameters.items()}

        deployment_properties = {
            'mode' : DeploymentMode.incremental,
            'template' : template,
            'parameters' : parameters
        }
        async_vm_create = self.resource_client.deployments.create_or_update(
                resource_group,
                vmname,
                deployment_properties
        )
        async_vm_create.wait()

    def upgrade_vm(self, resource_group, vmname, vm_size):
        if supported_vm_sizes.get(vm_size.upper()) is None:
            raise ValueError('Wrong capacity {} provided.'.format(vm_size))
        else:
            vm_size = supported_vm_sizes[vm_size.upper()]

        vm = self.get_vm(resource_group, vmname)
        vm.hardware_profile.vm_size = vm_size
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
            resource_group,
            vmname,
            vm
        )
        async_vm_update.wait()

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

        data_disks.append(DataDisk(
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
        vm_status = vm.instance_view.statuses[1].display_status

def parse_params():
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--client_id', required=True, help='login via this client')
    parser.add_argument('-k', '--key', required=True, help='login via this key')
    parser.add_argument('-t', '--tenant_id', required=True, help='login via this tenant')
    parser.add_argument('-s', '--subscription', required=True, help='login via this subscription id')

    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')

    # list subcommands
    parser_list = subparsers.add_parser('list', description='list specified resources', help='resource_group | storage_account | vm | vnet | subnet | nic | vm_state | vm_ip | vm_disk')
    list_subparser = parser_list.add_subparsers(title='list',  help='list related resources')
    # list resource groups
    list_rg = list_subparser.add_parser('resource_group', help='list resource groups')
    list_rg.set_defaults(func=list_resource_groups)
    # list all resources within a resource group
    list_re = list_subparser.add_parser('resource', help='list all resources')
    list_re.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
    list_re.set_defaults(func=list_resources)
    # list storage accounts
    list_sa = list_subparser.add_parser('storage_account', help='list storage accounts')
    list_sa.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
    list_sa.set_defaults(func=list_storage_accounts)
    # list vms
    list_vm = list_subparser.add_parser('vm', help='list vms within a resource group')
    list_vm.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_vm.add_argument('-n', '--name', help='list a specific vm')
    list_vm.set_defaults(func=list_virtual_machines)
    # list vnets
    list_vnet = list_subparser.add_parser('vnet', help='list vnets within a resource group')
    list_vnet.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_vnet.set_defaults(func=list_virtual_networks)
    # list subnets
    list_subnet = list_subparser.add_parser('subnet', help='list subnets within a resource group')
    list_subnet.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_subnet.add_argument('-v', '--vnet', required=True, help='list resources wihtin this vnet')
    list_subnet.set_defaults(func=list_subnetworks)
    # list nics
    list_nic = list_subparser.add_parser('nic', help='list nics within a resource group')
    list_nic.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_nic.set_defaults(func=list_network_interfaces)
    # list a vm's state
    list_state = list_subparser.add_parser('vm_state', help="list a vm's state within a resource group")
    list_state.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_state.add_argument('-n', '--name', required=True, help='list a specific vm')
    list_state.set_defaults(func=list_vm_state)
    # list a vm's ip 
    list_ip = list_subparser.add_parser('vm_ip', help="list a vm's state within a resource group")
    list_ip.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_ip.add_argument('-n', '--name', required=True, help='list a specific vm')
    list_ip.set_defaults(func=list_vm_ip)
    # list a vm's data disks
    list_disk = list_subparser.add_parser('vm_disk', help="list a vm's data disks")
    list_disk.add_argument('-r', '--resource_group', required=True, help='list resources wihtin this group')
    list_disk.add_argument('-n', '--name', required=True, help='list a specific vm')
    list_disk.set_defaults(func=list_vm_data_disk)

    # create subcommands
    parser_create = subparsers.add_parser('create', description='create a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic | public_ip')
    create_subparser = parser_create.add_subparsers(title='create',  help='create related resources')
    # create resource group
    create_rg = create_subparser.add_parser('resource_group', help='create a resource group')
    create_rg.add_argument('-n', '--name', required=True, help='create a resource group with this name')
    create_rg.add_argument('-l', '--location', required=True, help='create a resource group within this region')
    create_rg.set_defaults(func=create_resource_group)
    # create storage account
    create_sa = create_subparser.add_parser('storage_account', help='create a storage account')
    create_sa.add_argument('-r', '--resource_group', required=True, help='create a storage accounts within a resource group')
    create_sa.add_argument('-n', '--name', required=True, help='create a storage account with this name')
    create_sa.add_argument('-l', '--location', required=True, help='create a storage account within this region')
    create_sa.add_argument('-t', '--type', help='create a storage account with this type')
    create_sa.set_defaults(func=create_storage_account)
    # create vm
    create_vm = create_subparser.add_parser('vm', help='create vms within a resource group')
    create_vm.add_argument('-r', '--resource_group', required=True, help='create a vm wihtin this resource group')
    create_vm.add_argument('-s', '--storage_account', required=True, help='create a vm wiht this storage account')
    create_vm.add_argument('-l', '--location', required=True, help='create a vm in this region')
    create_vm.add_argument('-c', '--vm_size', required=True, help='create a vm with this size')
    create_vm.add_argument('-n', '--name', required=True, help='create a vm with this name')
    create_vm.add_argument('-t', '--template', required=True, help='create a vm with this template')
    create_vm.add_argument('-v', '--vnet', required=True, help='create a vm with this vnet')
    create_vm.add_argument('-e', '--subnet', required=True, help='create a vm with 2 subnets')
    create_vm.add_argument('-p', '--ssh_key', help='create a vm with this ssh key')
    create_vm.add_argument('-o', '--os_uri', required=True, help='create a vm with this root disk')
    create_vm.set_defaults(func=create_virtual_machine)
    # create vnet
    create_vnet = create_subparser.add_parser('vnet', help='create vnets within a resource group')
    create_vnet.add_argument('-r', '--resource_group', required=True, help='create a vnet wihtin this group')
    create_vnet.add_argument('-n', '--name', required=True, help='create a vnet with this name')
    create_vnet.add_argument('-l', '--location', required=True, help='create a vnet within this location')
    create_vnet.add_argument('-p', '--prefix', required=True, help='create a vnet with this address prefix')
    create_vnet.set_defaults(func=create_virtual_network)
    # create subnet
    create_subnet = create_subparser.add_parser('subnet', help='create subnets within a resource group')
    create_subnet.add_argument('-r', '--resource_group', required=True, help='create a subnet wihtin this group')
    create_subnet.add_argument('-v', '--vnet', required=True, help='create a subnet with this vnet')
    create_subnet.add_argument('-n', '--name', required=True, help='create a subnet with this name')
    create_subnet.add_argument('-p', '--prefix', required=True, help='create a subnet with this address prefix')
    create_subnet.set_defaults(func=create_subnetwork)
    # create nic
    create_nic = create_subparser.add_parser('nic', help='create nics within a resource group')
    create_nic.add_argument('-r', '--resource_group', required=True, help='create a nic wihtin this group')
    create_nic.add_argument('-v', '--vnet', required=True, help='create a nic with this vnet')
    create_nic.add_argument('-e', '--subnet', required=True, help='create a nic with this subnet')
    create_nic.add_argument('-l', '--location', required=True, help='create a nic within this location')
    create_nic.add_argument('-n', '--name', required=True, help='create a nic with this name')
    create_nic.set_defaults(func=create_network_interface)
    # create public ip
    create_ip = create_subparser.add_parser('public_ip', help='create a public ip for a vm')
    create_ip.add_argument('-r', '--resource_group', required=True, help='create a public ip wihtin this group')
    create_ip.add_argument('-n', '--name', required=True, help='create a public ip for this vm')
    create_ip.add_argument('-s', '--static', help='create a static ip', action='store_true')
    create_ip.set_defaults(func=create_public_ip)

    # delete subcommands
    parser_delete = subparsers.add_parser('delete', description='delete a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic')
    delete_subparser = parser_delete.add_subparsers(title='delete',  help='create related resources')
    # delete resource group
    delete_rg = delete_subparser.add_parser('resource_group', help='delete a resource group')
    delete_rg.add_argument('-n', '--name', required=True, help='delete a resource group')
    delete_rg.set_defaults(func=delete_resource_group)
    # delete storage account
    delete_sa = delete_subparser.add_parser('storage_account', help='delete a storage account')
    delete_sa.add_argument('-r', '--resource_group', required=True, help='delete a resource group')
    delete_sa.add_argument('-n', '--name', required=True, help='delete a storage account')
    delete_sa.set_defaults(func=delete_storage_account)
    # delete vm
    delete_vm = delete_subparser.add_parser('vm', help='delete vms within a resource group')
    delete_vm.add_argument('-r', '--resource_group', required=True, help='delete a vm wihtin this resource group')
    delete_vm.add_argument('-n', '--name', required=True, help='delete a vm with this name')
    delete_vm.set_defaults(func=delete_virtual_machine)
    # delete vnet
    delete_vnet = delete_subparser.add_parser('vnet', help='delete vnets within a resource group')
    delete_vnet.add_argument('-r', '--resource_group', required=True, help='delete a vnet wihtin this group')
    delete_vnet.add_argument('-n', '--name', required=True, help='delete a vnet with this name')
    delete_vnet.set_defaults(func=delete_virtual_network)
    # delete subnet
    delete_subnet = delete_subparser.add_parser('subnet', help='delete subnets within a resource group')
    delete_subnet.add_argument('-r', '--resource_group', required=True, help='delete a subnet wihtin this group')
    delete_subnet.add_argument('-v', '--vnet', required=True, help='delete a subnet wihtin this vnet')
    delete_subnet.add_argument('-n', '--name', required=True, help='delete a subnet with this name')
    delete_subnet.set_defaults(func=delete_subnetwork)
    # delete nic
    delete_nic = delete_subparser.add_parser('nic', help='delete nics within a resource group')
    delete_nic.add_argument('-r', '--resource_group', required=True, help='delete a nic wihtin this group')
    delete_nic.add_argument('-n', '--name', required=True, help='delete a nic with this name')
    delete_nic.set_defaults(func=delete_network_interface)

    # start subcommand
    parser_start = subparsers.add_parser('start', description='start a specified vm', help='vm')
    start_subparser = parser_start.add_subparsers(title='start', description='start a specified vm', help='vm')
    start_vm = start_subparser.add_parser('vm', help='start a vm')
    start_vm.add_argument('-r', '--resource_group', required=True, help='start a vm within this group')
    start_vm.add_argument('-n', '--name', required=True, help='start a vm with this name')
    start_vm.set_defaults(func=start_virtual_machine) 

    # restart subcommand
    parser_restart = subparsers.add_parser('restart', description='restart a specified vm', help='vm')
    restart_subparser = parser_restart.add_subparsers(title='restart', description='restart a specified vm', help='vm')
    restart_vm = restart_subparser.add_parser('vm', help='restart a vm')
    restart_vm.add_argument('-r', '--resource_group', required=True, help='restart a vm within this group')
    restart_vm.add_argument('-n', '--name', required=True, help='restart a vm with this name')
    restart_vm.set_defaults(func=restart_virtual_machine)

    # stop command
    parser_stop = subparsers.add_parser('stop', description='stop a specified vm', help='vm')
    stop_subparser = parser_stop.add_subparsers(title='stop', description='stop a specified vm', help='vm')
    stop_vm = stop_subparser.add_parser('vm', help='stop a vm')
    stop_vm.add_argument('-r', '--resource_group', required=True, help='stop a vm within this group')
    stop_vm.add_argument('-n', '--name', required=True, help='stop a vm with this name')
    stop_vm.set_defaults(func=stop_virtual_machine)

    # shutdown command
    parser_stop = subparsers.add_parser('shutdown', description='stop a specified vm', help='vm')
    stop_subparser = parser_stop.add_subparsers(title='shutdown', description='stop a specified vm', help='vm')
    stop_vm = stop_subparser.add_parser('vm', help='stop a vm')
    stop_vm.add_argument('-r', '--resource_group', required=True, help='stop a vm within this group')
    stop_vm.add_argument('-n', '--name', required=True, help='stop a vm with this name')
    stop_vm.set_defaults(func=shutdown_virtual_machine)
    
    # upgrade command
    parser_upgrade = subparsers.add_parser('upgrade', description='upgrade specified vm', help='vm')
    upgrade_subparser = parser_upgrade.add_subparsers(title='upgrade', description='upgrade a specified vm', help='vm')
    upgrade_vm = upgrade_subparser.add_parser('vm', help='upgrade a vm')
    upgrade_vm.add_argument('-r', '--resource_group', required=True, help='upgrade a vm within this group')
    upgrade_vm.add_argument('-n', '--name', required=True, help='upgrade a vm with this name')
    upgrade_vm.add_argument('-c', '--vm_size', required=True, help='upgrade a vm to this size')
    upgrade_vm.set_defaults(func=upgrade_virtual_machine)

    # attach subcommand
    parser_attach = subparsers.add_parser('attach', description='attach disks to a specified vm', help='disk')
    attach_subparser = parser_attach.add_subparsers(title='attach', description='attach a specified disk', help='disk')
    attach_disk = attach_subparser.add_parser('disk', help='attach a disk to a vm')
    attach_disk.add_argument('-r', '--resource_group', required=True, help='attach a disk to a vm within this group')
    attach_disk.add_argument('-n', '--name', required=True, help='attach a disk to a vm with this name')
    attach_disk.add_argument('-d', '--disk_name', required=True, help='attach a disk with this name')
    attach_disk.add_argument('-g', '--disk_size', required=True, help='attach a disk with this size in GiB')
    attach_disk.add_argument('-e', '--existing', help='attach an existing disk')
    attach_disk.set_defaults(func=attach_disk_to_vm)

    # detach subcommand
    parser_detach = subparsers.add_parser('detach', description='detach disks from a specified vm', help='disk')
    detach_subparser = parser_detach.add_subparsers(title='detach', description='detach a specified disk', help='disk')
    detach_disk = detach_subparser.add_parser('disk', help='detach a disk from a vm')
    detach_disk.add_argument('-r', '--resource_group', required=True, help='detach a disk to a vm within this group')
    detach_disk.add_argument('-n', '--name', required=True, help='detach a disk from a vm with this name')
    detach_disk.add_argument('-d', '--disk_name', required=True, help='detach a disk with this name')
    detach_disk.set_defaults(func=detach_disk_from_vm)

    args = parser.parse_args()
    args.func(args)

    return args

def list_resources(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_resources(args.resource_group)

def list_resource_groups(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_resource_groups()

def list_storage_accounts(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_storage_accounts(args.resource_group)

def list_virtual_machines(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_virtual_machines(args.resource_group, args.name)

def list_virtual_networks(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_virtual_networks(args.resource_group)

def list_subnetworks(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_subnetworks(args.resource_group, args.vnet)

def list_network_interfaces(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_network_interfaces(args.resource_group)

def list_vm_state(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    state = azure_ops.list_vm_state(args.resource_group, args.name)
    print ''
    print 'VM name : {}'.format(args.name)
    print 'VM state : {}'.format(state)

def list_vm_ip(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    public_ips = azure_ops.list_vm_public_ip(args.resource_group, args.name)
    private_ips = azure_ops.list_vm_private_ip(args.resource_group, args.name)
    print ''
    print 'VM name : {}'.format(args.name)
    print 'Public ip : {}'.format(public_ips)
    print 'Private ip : {}'.format(private_ips)

def delete_resource_group(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_resource_group(args.name)

def delete_storage_account(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_storage_account(args.resource_group, args.name)

def delete_virtual_network(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_vnet(args.resource_group, args.name)

def delete_subnetwork(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_subnet(args.resource_group, args.vnet, args.name)

def delete_network_interface(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_nic(args.resource_group, args.name)

def delete_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.delete_vm(args.resource_group, args.name)

def create_resource_group(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_resource_group(args.name, args.location)

def create_storage_account(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_storage_account(args.resource_group, args.name, args.location, args.type)

def create_virtual_network(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_vnet(args.resource_group, args.location, args.name, args.prefix)

def create_subnetwork(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_subnet(args.resource_group, args.vnet, args.name, args.prefix)

def create_network_interface(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_nic(args.resource_group, args.vnet, args.subnet, args.location, args.name)

def create_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_vm(args.resource_group, args.storage_account, args.location, args.vm_size, args.template, args.name, args.vnet, args.subnet, args.ssh_key, args.os_uri)

def create_public_ip(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.create_public_ip(args.resource_group, args.name, args.static)
    public_ip = azure_ops.list_vm_public_ip(args.resource_group, args.name)
    print 'Pulbic ip : {}'.foramt(public_ip)

def start_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.start_vm(args.resource_group, args.name)

def stop_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.deallocate_vm(args.resource_group, args.name)

def shutdown_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.stop_vm(args.resource_group, args.name)

def restart_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.restart_vm(args.resource_group, args.name)

def upgrade_virtual_machine(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.upgrade_vm(args.resource_group, args.name, args.vm_size)

def list_vm_data_disk(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.list_data_disks(args.resource_group, args.name)

def attach_disk_to_vm(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription)
    azure_ops.attach_data_disk(args.resource_group, args.name, args.disk_name, args.disk_size, args.existing)

def detach_disk_from_vm(args):
    azure_ops = azure_operations(args.client_id, args.key, args.tenant_id, args.subscription) 
    azure_ops.detach_data_disk(args.resource_group, args.name, args.disk_name)


if __name__ == '__main__':
    try:
        args = parse_params()
    except Exception as e:
        print '{}'.format(e)
