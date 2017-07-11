from azure_operations import azure_operations 

tenant_id = '715dbce8-032b-4494-b3d5-c24e4c46c8f8'
client_id = 'b21c3431-3772-4939-948b-1a32b8745ca6'
secret_key = '6tNYXZaCbPKijsGjcq3ZHN7SNLwse4gCQ6jFsaZqsJg='
subscription_id = '56183da2-b1d8-49cd-9ade-d24b928f7452'

resource_group = 'solution-test'
storage_account = 'songe1test'
vm_name = 'songe1-benchmark-jumpbox'
new_vm_name = 'test-vm'
vm_size = '8T'  # ---> 'Standard_F4'
virtual_net = 'songe1-benchmark-test'
subnet_list = 'songe1-benchmark-subnet,songe1-benchmark-subnet'
ssh_public_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCyYNyPI1QjpmWbDjbTqkqe7qi3wc97K5JpygX9EeLNEY3VQqzAJsfHwvxkPnyOqKiYXOV3johwQKiZct2/1MUEpd8MvMCaDhlzyf7OrJ7DNgI5P8Ilh/dhCxe6W0crlWcG6UE+ldHzbRrphhMzdt2CNJ3nh/gLGMpQGASHtCJZrXzUHCqu/vivfdm6Zy2bbsNYeCdbJ6MJwaQ2FnKUhGAyeDi7SdsXb+kizokL6J5dJHKDhIJY2lNfF5jclpkoM694wvfSupe+Zz4tx7EVlxDi2BtLrwRSiRWtTIsXYGiyz2Wx3AWzxPGSkLLqBEk0AacWsGba4hElLiAa31NZI5mt dd_user@Jumpbox2' 
username = 'sysadmin'
password = 'Abcd12345678?'
publisher = 'Canonical'
offer = 'UbuntuServer'
sku = '16.04.0-LTS'


if __name__ == '__main__':

    try:
        azure_ops = azure_operations(tenant_id = tenant_id, client_id = client_id, secret_key = secret_key, subscription_id = subscription_id)
        # list commands
    #    azure_ops.list_resource_groups() 
    #    azure_ops.list_resources(resource_group)
    #    
    #    azure_ops.list_storage_accounts()
    #    accounts = azure_ops.list_storage_accounts(resource_group)
    #    azure_ops.list_storage_account_primary_key(resource_group, storage_account)
    #    
    #    azure_ops.list_network_interfaces(resource_group)
    #    
    #    azure_ops.list_virtual_machines(resource_group)
    #    azure_ops.list_virtual_machines(resource_group, vm_name)
    #    azure_ops.list_vm_state(resource_group, vm_name)
    #    azure_ops.list_vm_size(resource_group, vm_name)
    #    azure_ops.list_vm_private_ip(resource_group, vm_name)
    #    azure_ops.list_vm_public_ip(resource_group, vm_name)
    #    azure_ops.list_data_disks(resource_group, vm_name)
    
        # create commands
        new_rg = "test_rg"
        location = "eastus"
        new_sa = "songe1testsa"
        new_container = "test-container"
        new_vnet = "test_vnet"
        new_vnet_prefix = "10.1.0.0/16"
        new_subnet = "test_subnet"
        new_subnet_prefix = "10.1.0.0/24"
        new_nic = "test_nic"
    
        # azure_ops.create_resource_group(new_rg, location)
        # azure_ops.create_storage_account(new_rg, new_sa, location, account_type = 'BlobStorage', replication_type = "Standard_LRS", access_tier = 'Hot')
        # azure_ops.create_storage_container(new_rg, new_sa, new_container)
        # azure_ops.create_vnet(new_rg, location, new_vnet, new_vnet_prefix)
        # azure_ops.create_subnet(new_rg, new_vnet, new_subnet, new_subnet_prefix)
        # azure_ops.create_nic(new_rg, new_vnet, new_subnet, location, new_nic)
       
        azure_ops.create_vm(resource_group, storage_account, vm_size, new_vm_name, virtual_net, subnet_list, ssh_public_key, publisher, offer, sku, username, password) 
        # stop command 
        azure_ops.deallocate_vm(resource_group, vm_name)
        # start command
        # azure_ops.start_vm(resource_group, vm_name)
        # restart command 
        # azure_ops.restart_vm(resource_group, vm_name)
        # resize command 
        # azure_ops.resize_vm(resource_group, vm_name, new_size)
        # delete commands

    except Exception as e:
        print '{}'.format(e)
