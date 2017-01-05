import sys, os, argparse

from azure.common.credentials import UserPassCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource import StorageManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network import NetworkManagementClient

class azure_operations(username, passwd, subscription_id, resource_group, region, storage_account):
    
    def __init__(self, username, passwd, subscription_id, resource_group, region, storage_account, vmname):
        self.username = username
        self.passwd = passwd
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.region = region
        in_china = False
        if regin.index('china') != -1:
            in_china = True
        self.storage_account = storage_account
        self.vmname = vmname
        # 
         
        # initialize resouce and storage management object
        try:
            credentials = UserPassCredentials("songyang@songyangeric.partner.onmschina.cn", "Passw0rd", china = in_china)
        except Exception as e:
            raise SystemError('Failed to login due to %s' % e)

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

    def create_vnet(self, resource_group, region, vnet_name):
        async_vnet_create = slef.network_client.virtual_networks.create_or_update(
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
                    'name' : vm_reference['name'] + '_osDisk',
                    'caching' : 'None',
                    'create_option' : 'fromImage',
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
                        'create_option' : 'Empty'
                    }]
                }
            }
        )
        async_vm_update.wait()

class azure_deploy():

    def __init__():
        pass

def usage():
    print ''' python %s 
          ''' sys.argv[0]
