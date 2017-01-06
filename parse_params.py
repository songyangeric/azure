import argparse

parser = argparse.ArgumentParser()
#group = parser.add_mutually_exclusive_group()
#group.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')
#group.add_argument('-q', '--quiet', help='decrease output verbosity', action='store_true')

subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')

# list subcommands
parser_list = subparsers.add_parser('list', description='list specified resources', help='resource_group | storage_account | vm | vnet | subnet | nic')
list_subparser = parser_list.add_subparsers(title='list',  help='list related resources')
#list resource groups
list_rg = list_subparser.add_parser('resource_group', help='list resource groups')
#list storage accounts
list_sa = list_subparser.add_parser('storage_account', help='list storage accounts')
list_sa.add_argument('resource_group', help='list storage accounts within a resource group')
#list vms
list_vm = list_subparser.add_parser('vm', help='list vms within a resource group')
list_vm.add_argument('resource_group', help='list resources wihtin this group')
#list vnets
list_vnet = list_subparser.add_parser('vnet', help='list vnets within a resource group')
list_vnet.add_argument('resource_group', help='list resources wihtin this group')
#list subnets
list_subnet = list_subparser.add_parser('subnet', help='list subnets within a resource group')
list_subnet.add_argument('resource_group', help='list resources wihtin this group')
#list nics
list_nic = list_subparser.add_parser('nic', help='list nics within a resource group')
list_nic.add_argument('resource_group', help='list resources wihtin this group')

# create subcommands
parser_create = subparsers.add_parser('create', description='create a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic')
create_subparser = parser_create.add_subparsers(title='create',  help='create related resources')
#create resource group
create_rg = create_subparser.add_parser('resource_group', help='create a resource group')
#create storage account
create_sa = create_subparser.add_parser('storage_account', help='create a storage account')
create_sa.add_argument('resource_group', help='create a storage accounts within a resource group')
#create vm
create_vm = create_subparser.add_parser('vm', help='create vms within a resource group')
create_vm.add_argument('-r', '--resource_group', help='create a vm wihtin this resource group')
create_vm.add_argument('-s', '--storage_account', help='create a vm wiht this storage account')
create_vm.add_argument('-l', '--location', help='create a vm in this region')
create_vm.add_argument('-c', '--vm_size', help='create a vm with this size')
create_vm.add_argument('-n', '--vm_name', help='create a vm with this name')
create_vm.add_argument('-t', '--template', help='create a vm with this template')
create_vm.add_argument('-v', '--vnet', help='create a vm with this vnet')
create_vm.add_argument('-e', '--subnet', help='create a vm with this subnet')
create_vm.add_argument('-i', '--nic', help='create a vm with this nic')
#create vnet
create_vnet = create_subparser.add_parser('vnet', help='create vnets within a resource group')
create_vnet.add_argument('-r', '--resource_group', help='create a vnet wihtin this group')
create_vnet.add_argument('-n', '--name',  help='create a vnet with this name')
#create subnet
create_subnet = create_subparser.add_parser('subnet', help='create subnets within a resource group')
create_subnet.add_argument('-r', '--resource_group', help='create a subnet wihtin this group')
create_subnet.add_argument('-v', '--vnet', help='create a subnet with this vnet')
create_subnet.add_argument('-n', '--name', help='create a subnet with this name')
#create nic
create_nic = create_subparser.add_parser('nic', help='create nics within a resource group')
create_nic.add_argument('-t', '-subnet', help='create a nic with this subnet')
create_nic.add_argument('-n', '--name', help='create a nic with this name')

# delete subcommands
parser_delete = subparsers.add_parser('delete', description='delete a specified resource', help='resource_group | storage_account | vm | vnet | subnet | nic')
delete_subparser = parser_delete.add_subparsers(title='delete',  help='create related resources')
#delete resource group
delete_rg = delete_subparser.add_parser('resource_group', help='delete a resource group')
delete_rg.add_argument('-r', '--resource_group', help='delete a resource group')
#delete storage account
delete_sa = delete_subparser.add_parser('storage_account', help='delete a storage account')
delete_sa.add_argument('-s', '--storage_account', help='delete a storage account')
#delete vm
delete_vm = delete_subparser.add_parser('vm', help='delete vms within a resource group')
delete_vm.add_argument('-r', '--resource_group', help='delete a vm wihtin this resource group')
delete_vm.add_argument('-n', '--vm_name', help='delete a vm with this name')
#delete vnet
delete_vnet = delete_subparser.add_parser('vnet', help='delete vnets within a resource group')
delete_vnet.add_argument('-r', '--resource_group', help='delete a vnet wihtin this group')
delete_vnet.add_argument('-n', '--name',  help='delete a vnet with this name')
#delete subnet
delete_subnet = delete_subparser.add_parser('subnet', help='delete subnets within a resource group')
delete_subnet.add_argument('-r', '--resource_group', help='delete a subnet wihtin this group')
delete_subnet.add_argument('-n', '--name', help='delete a subnet with this name')
#delete nic
delete_nic = delete_subparser.add_parser('nic', help='delete nics within a resource group')
delete_nic.add_argument('-n', '--name', help='delete a nic with this name')

# restart subcommand
parser_restart = subparsers.add_parser('restart', description='restart a specified vm', help='vm')
restart_subparser = parser_restart.add_subparsers(title='restart', description='restart a specified vm', help='vm')
restart_vm = restart_subparser.add_parser('vm', help='restart a vm')
restart_vm.add_argument('-r', '--resource_group', help='restart a vm within this group')
restart_vm.add_argument('-n', '--name', help='restart a vm with this name')

# stop command
parser_stop = subparsers.add_parser('stop', description='stop a specified vm', help='vm')
stop_subparser = parser_stop.add_subparsers(title='stop', description='stop a specified vm', help='vm')
stop_vm = stop_subparser.add_parser('vm', help='stop a vm')
stop_vm.add_argument('-r', '--resource_group', help='stop a vm within this group')
stop_vm.add_argument('-n', '--name', help='stop a vm with this name')

# upgrade command
parser_upgrade = subparsers.add_parser('upgrade', description='upgrade specified vm', help='vm')
upgrade_subparser = parser_upgrade.add_subparsers(title='upgrade', description='upgrade a specified vm', help='vm')
upgrade_vm = upgrade_subparser.add_parser('vm', help='upgrade a vm')
upgrade_vm.add_argument('-c', '--vm_size', help='upgrade a vm to this size')

# attach subcommand
parser_attach = subparsers.add_parser('attach', description='attach disks to a specified vm', help='disk')
attach_subparser = parser_attach.add_subparsers(title='attach', description='attach a specified disk', help='disk')
attach_disk = attach_subparser.add_parser('disk', help='attach a disk to a vm')
attach_disk.add_argument('-r', '--resource_group', help='attach a disk to a vm within this group')
attach_disk.add_argument('-n', '--name', help='attach a disk to a vm with this name')
attach_disk.add_argument('-c', '--disk_size', help='attach a disk with this size')
attach_disk.add_argument('-y', '--disk_type', help='attach a disk with this type')
attach_disk.add_argument('-d', '--disk_name', help='attach a disk with this name')

# detach subcommand
parser_detach = subparsers.add_parser('detach', description='detach disks from a specified vm', help='disk')
detach_subparser = parser_detach.add_subparsers(title='detach', description='detach a specified disk', help='disk')
detach_disk = detach_subparser.add_parser('disk', help='detach a disk from a vm')
detach_disk.add_argument('-r', '--resource_group', help='detach a disk to a vm within this group')
detach_disk.add_argument('-n', '--name', help='detach a disk from a vm with this name')
detach_disk.add_argument('-d', '--disk_name', help='detach a disk with this name')
#
args = parser.parse_args()

