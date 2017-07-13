from azure_operations import azure_operations 

tenant_id = '715dbce8-032b-4494-b3d5-c24e4c46c8f8'
client_id = 'b21c3431-3772-4939-948b-1a32b8745ca6'
secret_key = '6tNYXZaCbPKijsGjcq3ZHN7SNLwse4gCQ6jFsaZqsJg='
subscription_id = '56183da2-b1d8-49cd-9ade-d24b928f7452'

ssh_public_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCyYNyPI1QjpmWbDjbTqkqe7qi3wc97K5JpygX9EeLNEY3VQqzAJsfHwvxkPnyOqKiYXOV3johwQKiZct2/1MUEpd8MvMCaDhlzyf7OrJ7DNgI5P8Ilh/dhCxe6W0crlWcG6UE+ldHzbRrphhMzdt2CNJ3nh/gLGMpQGASHtCJZrXzUHCqu/vivfdm6Zy2bbsNYeCdbJ6MJwaQ2FnKUhGAyeDi7SdsXb+kizokL6J5dJHKDhIJY2lNfF5jclpkoM694wvfSupe+Zz4tx7EVlxDi2BtLrwRSiRWtTIsXYGiyz2Wx3AWzxPGSkLLqBEk0AacWsGba4hElLiAa31NZI5mt dd_user@Jumpbox2' 
username = 'sysadmin'
password = 'Abcd12345678?'
publisher = 'Canonical'
offer = 'UbuntuServer'
sku = '16.04.0-LTS'

new_rg = "test_rg"
location = "eastus"
new_sa = "songe1testsa"
new_container = "test-container"
new_vnet = "test_vnet"
new_vnet_prefix = "10.1.0.0/16"
new_subnet = "test_subnet"
new_subnets = [new_subnet, new_subnet]
new_subnet_prefix = "10.1.0.0/24"
new_nic = "test_nic"
new_data_disk = 'new_data_disk'
new_data_disk_size = 30
new_vm_size = '8T'
size_for_resize_op = '16T'


if __name__ == '__main__':

    try:
        azure_ops = azure_operations(tenant_id = tenant_id, client_id = client_id, secret_key = secret_key, subscription_id = subscription_id)
        # create commands
        azure_ops.create_resource_group(new_rg, location)
        azure_ops.create_storage_account(new_rg, new_sa, location, account_type = 'BlobStorage', replication_type = "Standard_LRS", access_tier = 'Hot')
        azure_ops.create_storage_container(new_rg, new_sa, new_container)
        azure_ops.create_vnet(new_rg, location, new_vnet, new_vnet_prefix)
        azure_ops.create_subnet(new_rg, new_vnet, new_subnet, new_subnet_prefix)
        azure_ops.create_nic(new_rg, new_vnet, new_subnet, location, new_nic)
       
        azure_ops.create_vm(new_rg, new_sa, new_vm_size, new_vm_name, new_vnet, new_subnets, ssh_public_key, publisher, offer, sku, username, password) 
        azure_ops.create_public_ip(new_rg, new_vm_name, static_ip = True)
        
        # attach disk
        azure_ops.attach_data_disk(new_rg, new_vm_name, new_data_disk, new_data_disk_size) 
        
        # list commands
        azure_ops.list_resources(new_rg)
        
        azure_ops.list_storage_accounts(new_rg)
        azure_ops.list_storage_account_primary_key(new_rg, new_sa)
        
        azure_ops.list_network_interfaces(new_rg)
        
        azure_ops.list_virtual_machines(new_rg)
        azure_ops.list_virtual_machines(new_rg, new_vm_name)
        azure_ops.list_vm_state(new_rg, new_vm_name)
        azure_ops.list_vm_size(new_rg, new_vm_name)
        azure_ops.list_vm_private_ip(new_rg, new_vm_name)
        azure_ops.list_vm_public_ip(new_rg, new_vm_name)
        azure_ops.list_data_disks(new_rg, new_vm_name)
    
        # resize vm 
        azure_ops.resize_vm(resource_group, new_vm_name, size_for_resize_op)
        
        # delete commands
        azure_ops.delete_vm(resource_group, new_vm_name)

        azure_ops.delete_subnet(new_rg, new_vnet, new_subnet)
        azure_ops.delete_vnet(new_rg, new_vnet)
        
        azure_ops.delete_storage_account(new_rg, new_sa)

        azure_ops.delete_resource_group(new_rg)

    except Exception as e:
        print '{}'.format(e)
