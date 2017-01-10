import sys, os
import argparse
import json
from azure.common.credentials import UserPassCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient

class azure_operations:
    
    def __init__(self, username, passwd, subscription_id):
        self.username = username
        self.passwd = passwd
        self.subscription_id = subscription_id
#        self.resource_group = resource_group
#        self.region = region
#        in_china = False
#        if regin.index('china') != -1:
#            in_china = True
#        self.storage_account = storage_account
#        self.vmname = vmname
         
        # initialize resouce and storage management object
        try:
            credentials = UserPassCredentials("songyang@songyangeric.partner.onmschina.cn", "Passw0rd")
        except Exception as e:
            credentials = UserPassCredentials("songyang@songyangeric.partner.onmschina.cn", "Passw0rd", china=True)
            self.inChina = True

        if self.subscription_id is not None:
            self.resource_client = ResourceManagementClient(credentials, subscription_id)
            self.storage_client = StorageManagementClient(credentials, subscription_id)
            self.compute_client = ComputeManagementClient(credentials, subscription_id)
            self.network_client = NetworkManagementClient(credentials, subscription_id)
        else:
            raise ValueError('No subscription specified, please check or create a new one') 
    
    def print_item(self, item):
        print '\tName: %s' % item.name
        print '\tId: %s' % item.id
        print '\tLocation: %s' % item.location
        print '\tTags: %s' % item.tags
    
    def list_resource_groups(self):
        for rg in self.resource_client.resource_groups.list():
            print_item(rg)

    def list_resources(self, resource_group):
        for resource in self.resource_client.resource_groups.list_resources(resource_group):
            print_item(resource)       

    def create_resouce_group(self, rg_name, region):
        async_create = self.resource_client.resource_groups.create_or_update(
            rg_name,
            {
                'location' : region,
            }
        )
   #     asycn_create.wait()
    
    def delete_resource_group(self, resource_group):
        delete_done = self.resource_client.resource_groups.delete(resource_group)
        delete_done.wait()
        if resource_group in self.resource_client.resource_groups.list():
            raise SystemError('Failed to delete resource group %s' % resource_group)

    def list_storage_accounts(self, resource_group = None):
        if resource_group is not None:
            for sa in self.storage_client.storage_accounts.list_by_resource_group(
                resource_group):
                print_item(sa)
        else:
            for sa in self.storage_client.storage_accounts.list():
                print_item(sa)

    def create_storage_account(self, resource_group, sa_name, region, type = 'Standard_LRS'):
        async_sa_create = self.storage_client.storage_accounts.create(
            resouce_group,
            sa_name, 
            {
                'location' : region,
                account_type : type,
            }
        )
        async_sa_create.wait()

    def delete_storage_account(self, resource_group, sa_name):
        async_sa_delete = self.storage_client.storage_accounts.delete(
            resource_group,
            sa_name
        )
        async_sa_delete.wait()

    def list_virtual_machines(self, resource_group):
        for vm in self.compute_client.virtual_machines.list():
            print_item(vm)

    def get_vm(self, resource_group, vmname):
        virtual_machine = self.compute_client.virtual_machines.get(
            resource_group,
            vmname,
        )    
        if virtual_machine is None:
            print 'No virtual machine named %s found.' % vmname
        return virtual_machine

    def deallocate_vm(self, resource_group, vmname):
        async_vm_deallocate = self.compute_client.virtual_machines.deallocate(
            resource_group, 
            vmname)
        async_vm_deallocate.wait()

    def start_vm(self, resource_group, vmname):
        async_vm_start = self.compute_client.virtual_machines.start(
            resource_group,
            vmname)
        async_vm_start.wait()

    def restart_vm(self, resource_group, vmname):
        async_vm_restart = self.compute_client.virtual_machines.restart(
            resource_group,
            vmname)
        async_vm_restart.wait()

    def stop_vm(self, resource_group, vmname):
        async_vm_stop = self.compute_client.virtual_machines.power_off(
            resource_group,
            vmname)
        async_vm_stop.wait()

    def delete_vm(self, resource_group, vmname):
        async_vm_delete = self.compute_client.virtual_machines.delete(
            resource_group,
            vmname)
        async_vm_delete.wait()

    def list_data_disks(self, resource_group, vmname):
        virtual_machine = self.get_vm(resource_group, vmname)
        if virtual_machine is None:
            return
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [disk for disk in data_disks if disk.name.index('nvram') == -1]
        for disk in data_disks:
            print_item(disk)

    def detach_data_disk(self, resource_group, vmname, disk_name):
        virtual_machine = self.get_vm(resource_group, vmname)
        if virtual_machine is None:
            return
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [disk for disk in data_disks if disk.name != disk_name]
        async_vm_update = compute_client.virtual_machines.create_or_update(
            resource_group,
            vmname,
            virtual_machine
        )
        virtual_machine = async_vm_update.result()

    def list_virtual_networks(self, resource_group):
        for vnet in self.network_client.virtual_networks.list():
            print_item(vnet)

    def create_vnet(self, resource_group, region, vnet_name):
        async_vnet_create = self.network_client.virtual_networks.create_or_update(
            resource_group,
            vnet_name,
            {
                'location' : region,
                'address_space' : {
                    'address_prefixes' : ['10.0.0.0/16']
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

    def list_subnetworks(self, resource_group):
        for subnet in self.network_client.subnets.list():
            print_item(subnet)

    def create_subnet(self, resource_group, vnet_name, subnet_name):
        async_subnet_create = self.network_client.subnets.create_or_update(
            resource_group,
            vnet_name,
            subnet_name,
            {
                'address_prefix' : '10.0.0.0./24'
            }
        )
        subnet = async_subnet_create.result()
        return subnet
     
    def delete_subnet(self, resource_group, subnet):
        async_subnet_delete = self.network_client.subnets.delete(
            resource_group,
            subnet
        )
        async_subnet_delete.wait()

    def list_network_interfaces(self, resource_group):
        for nic in self.network_client.network_interfaces.list():
            print_item(nic)

    def create_nic(self, resource_group, region, subnet, nic_name):
        async_nic_create = self.network_client.network_interfaces.create_or_update(
            resource_group,
            nic_name,
            {
                'location' : region,
                'ip_configureation' : [{
                    'name' : nic_name,
                    'subnet' : {
                        'id' : subnet.id
                    }
                }]
            }
        )
        nic = async_nic_create.result()
        return nic
    
    def delete_nic(self, resource_group, nic):
        async_nic_delete = self.network_client.network_interfaces.delete(
            resource_group,
            nic
        )
        async_nic_delete.wait()

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
                    'caching' : 'none',
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

    def create_vm(self, vm_reference):
        vm_parameters = self.parse_vm_parameters(nics, vm_reference)
        public_ssh_key = none
        with open(vm_reference['ssh_key'], 'r') as pub_ssh_file_fd:
            public_ssh_key = pub_ssh_file_fd.read()
        template = none
        with open(vm_reference['template'], 'r') as template_file_fd:
            template = json.load(template_file_fd)
        async_vm_create = self.compute_client.virtual_machines.create_or_update(
            vm_reference['rg'], vm_referenc['name'], vm_parameters)
        async_vm_create.wait()

    def attach_data_disk(self, resource_group, region, vmname, disk_name, disk_size):
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
            resource_group,
            vmname,
            {
                'location' : region,
                'storage_profile' : {
                    'data_disks' : [{
                        'name' : disk_name,
                        'disk_size_gb' : disk_size,
                        'vhd' : {
                            'uri' : 'http://%s.blob.core.windows.net/vhds/%s.vhd' %(sa, disk_name)
                        },
                        'create_option' : 'empty'
                    }]
                }
            }
        )
        async_vm_update.wait()

def usage():
    help = '''
           -u/--username <username> -p/--password <password> -b/--subscription <subscription id>

           --- list subcommands ---
           list resouce_group
           list storage_account
           list vm -r/--resource_group <resource group name>
           list vnet -r/--resource_group <resource group name>
           list subnet -r/--resource_group <resource group name>
           list nic -r/--resource_group <resource group name>

           --- create subcommands ---
           create resource_group -r/--resource_group <resource group name>
           create storage_account -s/--storage_account <storage account name>
           create vm -r/--resource_group <resource group name> -s/--storage_account <storage account name> -t/--template <vm image> -c/--vm_size <vm size> -n/--name <vm name> 
           create vnet -r/--resource_group <resource group name> -n/--name <vnet name>
           create subnet -r/--resource_group <resource group name> -v/--vnet <vnet name> -n/--name <subnet name>
           create nic -r/--resource_group <resource group name> -e/--subnet <subnet> -n/--name <nic name>

           --- delete subcommands ---
           delete resource_group -r/--resource_group <resource group name>
           delete storage_account -s/--storage_account <storage account name>
           delete vm -r/--resource_group <resource group name> -n/--name <vm name> 
           delete vnet -r/--resource_group <resource group name> -n/--name <vnet name>
           delete subnet -r/--resource_group <resource group name> -n/--name <subnet name>
           delete nic -r/--resource_group <resource group name> -n/--name <nic name>
          
           ___ start subcommand ---
           start vm -r/--resource_group <resource group name> -n/--name <vm name>
           --- restart subcommand ---
           restart vm -r/--resource_group <resource group name> -n/--name <vm name> 
           
           --- stop subcommand ---
           stop vm -r/--resource_group <resource group name> -n/--name <vm name> 
           
           --- upgrade subcommand ---
           upgrade vm -r/--resource_group <resource group name> -n/--name <vm name> -c/--vm_size <vm size>
           
           --- attach subcommand ---
           attach disk -r/--resource_group <resource group name> -n/--name <vm name> -d/--disk_name <disk name> -b/--disk_size <disk size> -y/--disk_type <disk type>

           --- detach subcommand ---
           detach disk -r/--resource_group <resource group name> -n/--name <vm name> -d/--disk_name <disk name>

           ''' 
    print 'usage: python {}\n {}'.format(sys.argv[0], help) 

def parse_params():
    parser = argparse.argumentparser()
    
    parser.add_argument('-u', '--username', required=true, help='login via this username')
    parser.add_argument('-p', '--password', required=true, help='login via this password')
    parser.add_argument('-b', '--subscription', required=true, help='login via this subscription id')
   
    subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')
   
    # list subcommands
    parser_list = subparsers.add_parser('list', description='list specified resources', help='resource_group | storage_account | vm | vnet | subnet | nic')
    list_subparser = parser_list.add_subparsers(title='list',  help='list related resources')
    # list resource groups
    list_rg = list_subparser.add_parser('resource_group', help='list resource groups')
    list_rg.set_defaults(func=list_resource_groups)
    # list storage accounts
    list_sa = list_subparser.add_parser('storage_account', help='list storage accounts')
    list_sa.add_argument('-r', '--resource_group', help='list storage accounts within a resource group')
    list_sa.set_defaults(func=list_storage_accounts)
    # list vms
    list_vm = list_subparser.add_parser('vm', help='list vms within a resource group')
    list_vm.add_argument('-r', '--resource_group', required=true, help='list resources wihtin this group')
    list_vm.set_defaults(func=list_virtual_machines)
    # list vnets
    list_vnet = list_subparser.add_parser('vnet', help='list vnets within a resource group')
    list_vnet.add_argument('-r', '--resource_group', required=true, help='list resources wihtin this group')
    list_vnet.set_defaults(func=list_virtual_networks)
    # list subnets
    list_subnet = list_subparser.add_parser('subnet', help='list subnets within a resource group')
    list_subnet.add_argument('-r', '--resource_group', required=true, help='list resources wihtin this group')
    list_subnet.set_defaults(func=list_subnetworks)
    # list nics
    list_nic = list_subparser.add_parser('nic', help='list nics within a resource group')
    list_nic.add_argument('-r', '--resource_group', required=true, help='list resources wihtin this group')
    list_nic.set_defaults(func=list_network_interfaces)
    
    # create subcommands
    parser_create = subparsers.add_parser('create', description='create a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic')
    create_subparser = parser_create.add_subparsers(title='create',  help='create related resources')
    # create resource group
    create_rg = create_subparser.add_parser('resource_group', help='create a resource group')
    create_rg.set_defaults(func=create_resource_group)
    # create storage account
    create_sa = create_subparser.add_parser('storage_account', help='create a storage account')
    create_sa.add_argument('resource_group', help='create a storage accounts within a resource group')
    create_sa.set_defaults(func=create_storage_account)
    # create vm
    create_vm = create_subparser.add_parser('vm', help='create vms within a resource group')
    create_vm.add_argument('-r', '--resource_group', required=true, help='create a vm wihtin this resource group')
    create_vm.add_argument('-s', '--storage_account', required=true, help='create a vm wiht this storage account')
    create_vm.add_argument('-l', '--location', required=true, help='create a vm in this region')
    create_vm.add_argument('-c', '--vm_size', required=true, help='create a vm with this size')
    create_vm.add_argument('-n', '--vm_name', required=true, help='create a vm with this name')
    create_vm.add_argument('-t', '--template', required=true, help='create a vm with this template')
    create_vm.add_argument('-v', '--vnet', help='create a vm with this vnet')
    create_vm.add_argument('-e', '--subnet', help='create a vm with this subnet')
    create_vm.add_argument('-i', '--nic', help='create a vm with this nic')
    create_vm.set_defaults(func=create_virtual_machine)
    # create vnet
    create_vnet = create_subparser.add_parser('vnet', help='create vnets within a resource group')
    create_vnet.add_argument('-r', '--resource_group', help='create a vnet wihtin this group')
    create_vnet.add_argument('-n', '--name',  help='create a vnet with this name')
    create_vnet.set_defaults(func=create_virtual_network)
    # create subnet
    create_subnet = create_subparser.add_parser('subnet', help='create subnets within a resource group')
    create_subnet.add_argument('-r', '--resource_group', help='create a subnet wihtin this group')
    create_subnet.add_argument('-v', '--vnet', help='create a subnet with this vnet')
    create_subnet.add_argument('-n', '--name', help='create a subnet with this name')
    create_subnet.set_defaults(func=create_subnetwork)
    # create nic
    create_nic = create_subparser.add_parser('nic', help='create nics within a resource group')
    create_nic.add_argument('-t', '-subnet', help='create a nic with this subnet')
    create_nic.add_argument('-n', '--name', help='create a nic with this name')
    create_nic.set_defaults(func=create_network_interface)

    # delete subcommands
    parser_delete = subparsers.add_parser('delete', description='delete a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic')
    delete_subparser = parser_delete.add_subparsers(title='delete',  help='create related resources')
    # delete resource group
    delete_rg = delete_subparser.add_parser('resource_group', help='delete a resource group')
    delete_rg.add_argument('-r', '--resource_group', help='delete a resource group')
    delete_rg.set_defaults(func=delete_resource_group)
    # delete storage account
    delete_sa = delete_subparser.add_parser('storage_account', help='delete a storage account')
    delete_sa.add_argument('-s', '--storage_account', help='delete a storage account')
    delete_sa.set_defaults(func=delete_storage_account)
    # delete vm
    delete_vm = delete_subparser.add_parser('vm', help='delete vms within a resource group')
    delete_vm.add_argument('-r', '--resource_group', help='delete a vm wihtin this resource group')
    delete_vm.add_argument('-n', '--vm_name', help='delete a vm with this name')
    delete_vm.set_defaults(func=delete_virtual_machine)
    # delete vnet
    delete_vnet = delete_subparser.add_parser('vnet', help='delete vnets within a resource group')
    delete_vnet.add_argument('-r', '--resource_group', help='delete a vnet wihtin this group')
    delete_vnet.add_argument('-n', '--name',  help='delete a vnet with this name')
    delete_vnet.set_defaults(func=delete_virtual_network)
    # delete subnet
    delete_subnet = delete_subparser.add_parser('subnet', help='delete subnets within a resource group')
    delete_subnet.add_argument('-r', '--resource_group', help='delete a subnet wihtin this group')
    delete_subnet.add_argument('-n', '--name', help='delete a subnet with this name')
    delete_subnet.set_defaults(func=delete_subnetwork)
    # delete nic
    delete_nic = delete_subparser.add_parser('nic', help='delete nics within a resource group')
    delete_nic.add_argument('-n', '--name', help='delete a nic with this name')
    delete_nic.set_defaults(func=delete_network_interface)

    # start subcommand
    parser_start = subparsers.add_parser('start', description='start a specified vm', help='vm')
    start_subparser = parser_start.add_subparsers(title='start', description='start a specified vm', help='vm')
    start_vm = start_subparser.add_parser('vm', help='start a vm')
    start_vm.add_argument('-r', '--resource_group', help='start a vm within this group')
    start_vm.add_argument('-n', '--name', help='start a vm with this name')
    start_vm.set_defaults(func=start_virtual_machine) 

    # restart subcommand
    parser_restart = subparsers.add_parser('restart', description='restart a specified vm', help='vm')
    restart_subparser = parser_restart.add_subparsers(title='restart', description='restart a specified vm', help='vm')
    restart_vm = restart_subparser.add_parser('vm', help='restart a vm')
    restart_vm.add_argument('-r', '--resource_group', help='restart a vm within this group')
    restart_vm.add_argument('-n', '--name', help='restart a vm with this name')
    restart_vm.set_defaults(func=restart_virtual_machine)

    # stop command
    parser_stop = subparsers.add_parser('stop', description='stop a specified vm', help='vm')
    stop_subparser = parser_stop.add_subparsers(title='stop', description='stop a specified vm', help='vm')
    stop_vm = stop_subparser.add_parser('vm', help='stop a vm')
    stop_vm.add_argument('-r', '--resource_group', help='stop a vm within this group')
    stop_vm.add_argument('-n', '--name', help='stop a vm with this name')
    stop_vm.set_defaults(func=stop_virtual_machine)

    # upgrade command
    parser_upgrade = subparsers.add_parser('upgrade', description='upgrade specified vm', help='vm')
    upgrade_subparser = parser_upgrade.add_subparsers(title='upgrade', description='upgrade a specified vm', help='vm')
    upgrade_vm = upgrade_subparser.add_parser('vm', help='upgrade a vm')
    upgrade_vm.add_argument('-c', '--vm_size', help='upgrade a vm to this size')
    upgrade_vm.set_defaults(func=upgrade_virtual_machine)

    # attach subcommand
    parser_attach = subparsers.add_parser('attach', description='attach disks to a specified vm', help='disk')
    attach_subparser = parser_attach.add_subparsers(title='attach', description='attach a specified disk', help='disk')
    attach_disk = attach_subparser.add_parser('disk', help='attach a disk to a vm')
    attach_disk.add_argument('-r', '--resource_group', help='attach a disk to a vm within this group')
    attach_disk.add_argument('-n', '--name', help='attach a disk to a vm with this name')
    attach_disk.add_argument('-c', '--disk_size', help='attach a disk with this size')
    attach_disk.add_argument('-y', '--disk_type', help='attach a disk with this type')
    attach_disk.add_argument('-d', '--disk_name', help='attach a disk with this name')
    attach_disk.set_defaults(func=attach_disk_to_vm)

    # detach subcommand
    parser_detach = subparsers.add_parser('detach', description='detach disks from a specified vm', help='disk')
    detach_subparser = parser_detach.add_subparsers(title='detach', description='detach a specified disk', help='disk')
    detach_disk = detach_subparser.add_parser('disk', help='detach a disk from a vm')
    detach_disk.add_argument('-r', '--resource_group', help='detach a disk to a vm within this group')
    detach_disk.add_argument('-n', '--name', help='detach a disk from a vm with this name')
    detach_disk.add_argument('-d', '--disk_name', help='detach a disk with this name')
    detach_disk.set_defaults(func=detach_disk_from_vm)

    args = parser.parse_args()
    args.func(args)

    return args

def list_resource_groups(args):
    print 'list resource groups'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_resource_groups()

def list_storage_accounts(args):
    print 'list storage accounts'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_storage_accounts(args.resource_group)

def list_virtual_machines(args):
    print 'list virtual machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_virtual_machines(args.resource_group)

def list_virtual_networks(args):
    print 'list virtual networks'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_virtual_networks(args.resource_group)

def list_subnetworks(args):
    print 'list subnets'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_subnetworks(args.resource_group)

def list_network_interfaces(args):
    print 'list nics'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.list_network_interfaces(args.resource_group)

def delete_resource_group(args):
    print 'delete resource group'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_resource_group(args.resource_group)

def delete_storage_account(args):
    print 'delete storage account'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_storage_account(args.resource_group, args.stoarge_account)

def delete_virtual_network(args):
    print 'delete virtual network'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_vnet(args.resource_group, args.vnet)

def delete_subnetwork(args):
    print 'delete subnet'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_subnet(args.resource_group, args.subnet)

def delete_network_interface(args):
    print 'delete nic'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_nic(args.resource_group, args.nic)

def delete_virtual_machine(args):
    print 'delete_virtual_machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.delete_vm(args.resource_group, args.name)

def create_resource_group(args):
    print 'create_resource_group'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_resource_group(args.resource_group)

def create_storage_account(args):
    print 'create storage_account'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_storage_account(args.resource_group, args.storage_account)

def create_virtual_network(args):
    print 'create virtual network'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_vnet(args.resource_group, args.vnet)

def create_subnetwork(args):
    print 'create subnet'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_vnet(args.resource_group, args.vnet, args.subnet)

def create_network_interface(args):
    print 'create network interface'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_nic(args.resource_group, args.region, args.subnet, args.nic)
 
def create_virtual_machine(args):
    print 'create_virtual_machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.create_vm(args.resource_group, args.region, args.vm_size, args.nic)

def start_virtual_machine(args):
    print 'start_virtual_machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.start_vm(args.resource_group, args.name)

def stop_virtual_machine(args):
    print 'stop_virtual_machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.deallocate_vm(args.resource_group, args.name)

def restart_virtual_machine(args):
    print 'restart_virtual_machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.restart_vm(args.resource_group, args.name)

def upgrade_virtual_machine(args):
    print 'upgrade virtual machine'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.upgrade_vm(args.resource_group, args.name, args.vm_size)

def attach_disk_to_vm(args):
    print 'attach_disk_to_vm'
    azure_ops = azure_operations(args.username, args.password, args.subscription)
    azure_ops.attach_data_disk(args.resource_group, args.region, args.name, args.disk_name, args.disk_size)

def detach_disk_from_vm(args):
    print 'detach_disk_from_vm'
    azure_ops = azure_operations(args.username, args.password, args.subscription) 
    azure_ops.detach_data_disk(args.resource_group, args.name, args.disk_name)



if __name__ == '__main__':
    try:
        args = parse_params()
    except Exception as e:
   #     usage()
        print '{}'.format(e)
   #azure_ops = azure_operations() 
