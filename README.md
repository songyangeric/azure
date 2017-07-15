About environment setup: Please read EnvSetUp.html about how to setup your test environment.

Before all operations, it is recommended to set the environment variables below:

export AZURE_CLIENT_ID=
export AZURE_TENANT_ID=
export AZURE_SECRET_KEY=
export AZURE_SUBSCRIPTION_ID=

Otherwise, you need to specify ALL the optional arguments. For each operation, you need to use command like:

azure_operations.py -c CLIENT_ID -k SECRET_KEY -t TENANT_ID -s SUBSCRIPTION_ID {list,create,delete,start,restart,stop,resize,attach,detach}...

usage: azure_operations.py [-h] [-c CLIENT_ID] [-k SECRET_KEY] [-t TENANT_ID]
                           [-s SUBSCRIPTION_ID]
                           {list,create,delete,start,restart,stop,resize,attach,detach}
                           ...

optional arguments:
  -h, --help            show this help message and exit
  -c CLIENT_ID, --client_id CLIENT_ID
                        login via this client
  -k SECRET_KEY, --secret_key SECRET_KEY
                        login via this key
  -t TENANT_ID, --tenant_id TENANT_ID
                        login via this tenant
  -s SUBSCRIPTION_ID, --subscription_id SUBSCRIPTION_ID
                        login via this subscription id

subcommands:
  valid subcommands

  {list,create,delete,start,restart,stop,resize,attach,detach}
                        additional help
    list                resource_group | storage_account | vm | vnet | subnet
                        | nic | vm_state | vm_ip | vm_disk
    create              resource_group | storage_account | container | vm |
                        vnet | subnet | nic | public_ip
    delete              resource_group | storage_account | container | vm |
                        vnet | subnet | nic | container | blob
    start               vm
    restart             vm
    stop                vm
    resize              vm
    attach              disk
    detach              disk

How to create a vm:

usage: azure_operations.py create vm [-h] -r RESOURCE_GROUP -s STORAGE_ACCOUNT
                                     -c VM_SIZE -n NAME -v VNET -e SUBNET
                                     [-k SSH_KEY] [-u USERNAME] [-p PASSWORD]
                                     [-P PUBLISHER] [-O OFFER] [-S SKU]
                                     [--public_ip] [--static_ip]

optional arguments:
  -h, --help            show this help message and exit
  -r RESOURCE_GROUP, --resource_group RESOURCE_GROUP
                        create a vm wihtin this resource group
  -s STORAGE_ACCOUNT, --storage_account STORAGE_ACCOUNT
                        create a vm wiht this storage account
  -c VM_SIZE, --vm_size VM_SIZE
                        create a vm with this size
  -n NAME, --name NAME  create a vm with this name
  -v VNET, --vnet VNET  create a vm with this vnet
  -e SUBNET, --subnet SUBNET
                        create a vm with 2 subnets
  -k SSH_KEY, --ssh_key SSH_KEY
                        create a vm with this ssh key
  -u USERNAME, --username USERNAME
                        create a vm with this username
  -p PASSWORD, --password PASSWORD
                        create a vm with login password
  -P PUBLISHER, --publisher PUBLISHER
                        create a vm from this publisher
  -O OFFER, --offer OFFER
                        create a vm from this offer
  -S SKU, --sku SKU     create a vm from this sku
  --public_ip           create a vm with public ip
  --static_ip           create a vm with a static ip


How to delete a VM:

usage: azure_operations.py delete vm [-h] -r RESOURCE_GROUP -n NAME

optional arguments:
  -h, --help            show this help message and exit
  -r RESOURCE_GROUP, --resource_group RESOURCE_GROUP
                        delete a vm wihtin this resource group
  -n NAME, --name NAME  delete a vm with this name
