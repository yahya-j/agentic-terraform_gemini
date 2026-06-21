# agentic-terraform_gemini

# Étape 1 — Créer la clé API Gemini
export GEMINI_API_KEY=AIzaSy...
echo 'export GEMINI_API_KEY=AIzaSy...' >> ~/.bashrc

# Étape 2 — Installer le SDK
pip install google-genai

# Étape 3 — Smoke test isolé (même logique que pour Groq)
Voulez-vous que je vous prépare directement le script test_gemini.py et la version adaptée de LLMClient, 
ou préférez-vous d'abord confirmer que la clé fonctionne avec un test minimal avant qu'on touche au pipeline ?

###################################################################################################################################
# Résultat Test :
=== Test 1 : appel simple ===
The absolute minimal `azurerm` provider block is one with no arguments, relying on default authentication mechanisms:

```terraform
provider "azurerm" {}
```

**Explanation:**

This works because the `azurerm` provider is designed to automatically pick up credentials from:

1.  **Azure CLI:** If you've run `az login` and are authenticated, Terraform will use those credentials.
2.  **Environment Variables:** If you've set variables like `ARM_SUBSCRIPTION_ID`, `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, etc.
3.  **Managed Identity:** If running on an Azure VM, App Service, Function App, etc., with a Managed Identity enabled.

It will use the default subscription configured by your chosen authentication method.

=== Test 2 : appel avec historique de conversation ===
Okay, let's create an Ubuntu VM with 4 CPUs on Azure using Pulumi and the `azure-native` provider.

An Azure VM requires several interconnected resources:

1.  **Resource Group**: A logical container for your Azure resources.
2.  **Virtual Network (VNet)**: Provides network connectivity for your Azure resources.
3.  **Subnet**: A range of IP addresses within a VNet.
4.  **Public IP Address**: Allows internet-facing communication to the VM.
5.  **Network Security Group (NSG)**: Acts as a virtual firewall for your VM, controlling inbound and outbound traffic (e.g., allowing SSH).
6.  **Network Interface (NIC)**: Connects the VM to the VNet and associates the public IP and NSG.
7.  **Virtual Machine (VM)**: The actual compute instance.

---

### Prerequisites:

1.  **Pulumi CLI installed**: [Install Pulumi](https://www.pulumi.com/docs/get-started/install/)
2.  **Azure CLI installed and configured**: [Install Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
    *   Log in to Azure: `az login`
    *   Set your desired subscription: `az account set --subscription "Your Subscription Name or ID"`
3.  **Python 3 installed**: [Python Downloads](https://www.python.org/downloads/)
4.  **SSH Key Pair**: You'll need an SSH public key to securely access your VM. If you don't have one, generate it:
    ```bash
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure-key
    # This creates ~/.ssh/azure-key (private) and ~/.ssh/azure-key.pub (public)
    ```
    You will copy the **content** of `~/.ssh/azure-key.pub` into the Pulumi program.

---

### Pulumi Project Setup:

1.  **Create a new Pulumi project**:
    ```bash
    mkdir azure-ubuntu-vm
    cd azure-ubuntu-vm
    pulumi new azure-python
    ```
    Follow the prompts:
    *   `project name`: `azure-ubuntu-vm`
    *   `description`: `An Ubuntu VM with 4 CPUs on Azure`
    *   `stack name`: `dev` (default)
    *   `Azure region`: `eastus` (or your preferred region, e.g., `westus2`, `westeurope`)

2.  **Install Azure Native provider**:
    The `azure-python` template might use the older `azure` provider. We want `azure-native` for the latest features and direct API mapping.
    ```bash
    pip install pulumi-azure-native
    # You can also remove pulumi-azure if you won't be using it:
    # pip uninstall pulumi-azure
    ```

---

### `__main__.py` Code:

Replace the contents of your `__main__.py` file with the following:

```python
import pulumi
import pulumi_azure_native as azure_native

# --- Configuration Variables ---
# You can customize these values
resource_group_name = "ubuntu-4cpu-rg"
location = "eastus"  # Or your preferred Azure region
vm_name = "ubuntu-4cpu-vm"
admin_username = "azureuser"

# IMPORTANT: Replace this with the actual content of your SSH public key.
# For example, if you generated it with `ssh-keygen -f ~/.ssh/azure-key`,
# copy the content of `~/.ssh/azure-key.pub` here.
# It should look something like "ssh-rsa AAAAB3NzaC..."
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... your_public_key_content_here ... your_email@example.com"


# --- Azure Resource Creation ---

# 1. Create an Azure Resource Group
resource_group = azure_native.resources.ResourceGroup(
    resource_group_name,
    resource_group_name=resource_group_name,
    location=location,
)

# 2. Create a Virtual Network
vnet = azure_native.network.VirtualNetwork(
    f"{vm_name}-vnet",
    resource_group_name=resource_group.name,
    location=location,
    address_space=azure_native.network.AddressSpaceArgs(
        address_prefixes=["10.0.0.0/16"],
    ),
    opts=pulumi.ResourceOptions(parent=resource_group)
)

# 3. Create a Subnet
subnet = azure_native.network.Subnet(
    f"{vm_name}-subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
    opts=pulumi.ResourceOptions(parent=vnet)
)

# 4. Create a Public IP Address for the VM
public_ip = azure_native.network.PublicIPAddress(
    f"{vm_name}-public-ip",
    resource_group_name=resource_group.name,
    location=location,
    public_ip_allocation_method="Static", # Static IP for consistency
    sku=azure_native.network.PublicIPAddressSkuArgs(
        name="Standard", # Standard SKU for better features like availability zones (though not used here directly)
    ),
    opts=pulumi.ResourceOptions(parent=resource_group)
)

# 5. Create a Network Security Group (NSG) to allow SSH access
nsg = azure_native.network.NetworkSecurityGroup(
    f"{vm_name}-nsg",
    resource_group_name=resource_group.name,
    location=location,
    security_rules=[
        azure_native.network.SecurityRuleArgs(
            name="SSH",
            priority=1000,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_port_range="*",
            destination_port_range="22", # Allow SSH on port 22
            source_address_prefix="0.0.0.0/0", # WARNING: Allows SSH from any IP. Restrict this to your IP for production.
            destination_address_prefix="*",
        )
    ],
    opts=pulumi.ResourceOptions(parent=resource_group)
)

# 6. Create a Network Interface (NIC) for the VM
nic = azure_native.network.NetworkInterface(
    f"{vm_name}-nic",
    resource_group_name=resource_group.name,
    location=location,
    ip_configurations=[
        azure_native.network.NetworkInterfaceIPConfigurationArgs(
            name=f"{vm_name}-ipconfig",
            subnet=azure_native.network.SubnetArgs(id=subnet.id),
            private_ip_allocation_method="Dynamic",
            public_ip_address=azure_native.network.PublicIPAddressArgs(id=public_ip.id),
        )
    ],
    network_security_group=azure_native.network.NetworkSecurityGroupArgs(id=nsg.id),
    opts=pulumi.ResourceOptions(parent=resource_group)
)

# 7. Create the Virtual Machine
vm = azure_native.compute.VirtualMachine(
    vm_name,
    resource_group_name=resource_group.name,
    location=location,
    hardware_profile=azure_native.compute.HardwareProfileArgs(
        # VM size for 4 CPUs.
        # You can list available sizes with: `az vm list-sizes --location <region> --query "[?numberOfCores==`4`].name"`
        vm_size="Standard_D4s_v3", # This size typically has 4 vCPUs and 16 GiB RAM
    ),
    os_profile=azure_native.compute.OSProfileArgs(
        computer_name=vm_name,
        admin_username=admin_username,
        linux_configuration=azure_native.compute.LinuxConfigurationArgs(
            disable_password_authentication=True, # We're using SSH keys
            ssh=azure_native.compute.SshConfigurationArgs(
                public_keys=[
                    azure_native.compute.SshPublicKeyArgs(
                        path=f"/home/{admin_username}/.ssh/authorized_keys",
                        key_data=ssh_public_key,
                    )
                ]
            ),
        ),
    ),
    storage_profile=azure_native.compute.StorageProfileArgs(
        image_reference=azure_native.compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="UbuntuServer",
            sku="20.04-LTS", # Using Ubuntu 20.04 LTS. You could use "18.04-LTS" or "22.04-LTS"
            version="latest",
        ),
        os_disk=azure_native.compute.OSDiskArgs(
            create_option="FromImage",
            managed_disk=azure_native.compute.ManagedDiskParametersArgs(
                storage_account_type="Standard_LRS", # Standard HDD. Use "Premium_LRS" for SSD.
            ),
        ),
    ),
    network_profile=azure_native.compute.NetworkProfileArgs(
        network_interfaces=[
            azure_native.compute.NetworkInterfaceReferenceArgs(
                id=nic.id,
                primary=True,
            )
        ],
    ),
    opts=pulumi.ResourceOptions(parent=resource_group)
)

# --- Outputs ---
# Export the public IP address and an SSH command to easily connect to the VM
pulumi.export("public_ip", public_ip.ip_address)
pulumi.export("ssh_command", pulumi.Output.concat(f"ssh -i ~/.ssh/azure-key {admin_username}@", public_ip.ip_address))

```

---

### Deployment Steps:

1.  **Review and Update `ssh_public_key`**: Make sure you've replaced `"ssh-rsa AAAAB3NzaC..."` with the actual content of your `~/.ssh/azure-key.pub` file. This is crucial for SSH access.

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Preview the deployment**:
    ```bash
    pulumi up
    ```
    Pulumi will show you a preview of the resources that will be created. Confirm by typing `yes`.

4.  **Connect to your VM**:
    Once the deployment is complete, Pulumi will output the public IP address and an SSH command.
    Example output:
    ```
    Outputs:
        public_ip: "20.123.45.67"
        ssh_command: "ssh -i ~/.ssh/azure-key azureuser@20.123.45.67"
    ```
    Use the `ssh_command` to connect to your new Ubuntu VM:
    ```bash
    ssh -i ~/.ssh/azure-key azureuser@20.123.45.67
    ```
    (Remember to replace `~/.ssh/azure-key` with the path to your actual private key if it's different).

5.  **Clean up (optional)**:
    If you want to destroy all the resources created by Pulumi, run:
    ```bash
    pulumi destroy
    ```
    Confirm by typing `yes`.

This setup provides a fully functional Ubuntu VM on Azure with 4 CPUs, accessible via SSH, using best practices for network configuration.

=== Métadonnées utiles ===
Tokens utilisés : cache_tokens_details=None cached_content_token_count=None candidates_token_count=2712 candidates_tokens_details=None prompt_token_count=33 prompt_tokens_details=[ModalityTokenCount(
  modality=<MediaModality.TEXT: 'TEXT'>,
  token_count=33
)] thoughts_token_count=2996 tool_use_prompt_token_count=None tool_use_prompt_tokens_details=None total_token_count=5741 traffic_type=None

######################################################################################################################################################""
# Résultat Main.py

[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 1/6
[TerraformValidator] Code Terraform valide !

                    provider "azurerm" {
                        features {}
                    }

                    resource "azurerm_resource_group" "rg" {
                        name     = "vms-rg"
                        location = "westeurope"
                    }

                    resource "azurerm_virtual_network" "vnet" {
                        name                = "vms-vnet"
                        resource_group_name = azurerm_resource_group.rg.name
                        location            = azurerm_resource_group.rg.location
                        address_space       = ["10.0.0.0/16"]
                    }

                    resource "azurerm_subnet" "subnet" {
                        name                 = "vms-subnet"
                        resource_group_name  = azurerm_resource_group.rg.name
                        virtual_network_name = azurerm_virtual_network.vnet.name
                        address_prefixes     = ["10.0.1.0/24"]
                    }

                    resource "azurerm_public_ip" "public_ip" {
                        count               = 3
                        name                = "vm-public-ip-${count.index}"
                        resource_group_name = azurerm_resource_group.rg.name
                        location            = azurerm_resource_group.rg.location
                        allocation_method   = "Static"
                        sku                 = "Standard"
                        zones               = [count.index + 1]
                    }

                    resource "azurerm_network_interface" "nic" {
                        count               = 3
                        name                = "vm-nic-${count.index}"
                        resource_group_name = azurerm_resource_group.rg.name
                        location            = azurerm_resource_group.rg.location
                        ip_configuration {
                            name                          = "internal"
                            subnet_id                     = azurerm_subnet.subnet.id
                            private_ip_address_allocation = "Dynamic"
                            public_ip_address_id          = azurerm_public_ip.public_ip[count.index].id
                        }
                    }

                    resource "azurerm_linux_virtual_machine" "vm" {
                        count               = 3
                        name                = "vm-${count.index}"
                        resource_group_name = azurerm_resource_group.rg.name
                        location            = azurerm_resource_group.rg.location
                        size                = "Standard_E16s_v5" # 16 vCPUs, 128 GiB RAM
                        admin_username      = "adminuser"
                        network_interface_ids = [azurerm_network_interface.nic[count.index].id]
                        zone                = "${count.index + 1}"

                        admin_ssh_key {
                            username   = "adminuser"
                            public_key = tls_private_key.ssh_key.public_key_openssh
                        }

                        os_disk {
                            caching              = "ReadWrite"
                            storage_account_type = "Standard_LRS"
                        }

                        source_image_reference {
                            publisher = "Canonical"
                            offer     = "0001-com-ubuntu-server-jammy"
                            sku       = "22_04-lts"
                            version   = "latest"
                        }
                    }

                    resource "tls_private_key" "ssh_key" {
                        algorithm = "RSA"
                        rsa_bits  = 4096
                    }

                    output "public_ips" {
                        value = azurerm_public_ip.public_ip[*].ip_address
                    }
#################################################################################################################################################
# Début Niveau 1 : Ajout OVH
Traceback (most recent call last):
  File "/mnt/c/Users/janna/projects/agentic-terraform_gemini/main.py", line 25, in <module>
    PseudoRAG(),
    ~~~~~~~~~^^
  File "/mnt/c/Users/janna/projects/agentic-terraform_gemini/steps.py", line 224, in __init__
    self.corpus["provider"].append(key)
                                   ^^^
NameError: name 'key' is not defined

==> Problème Indentation
# Vérification de syntaxe avant de tester
python -c "import ast; ast.parse(open('steps.py').read())" && echo "Syntaxe OK"

###################################################################################################################################################
# Étape 2 — Une fois corrigé, le test de détection isolé
cat > test_pseudorag.py << 'EOF'
from steps import PseudoRAG

rag = PseudoRAG()

prompts = [
    "Deploy a VM on OVH Cloud in Strasbourg",
    "Create a Kubernetes cluster on OVHcloud",
    "Spin up a GCP Compute Engine instance",
    "Deploy 3 VMs on Azure",
    "Create an S3 bucket on AWS",
]

for p in prompts:
    messages, retry, meta = rag.get_messages([], p, {})
    print(f"Prompt: {p}")
    print(f"→ {messages[-1]['content']}\n")
EOF

python test_pseudorag.py
Ce test ne fait aucun appel API — uniquement du TF-IDF local, donc gratuit et instantané. Il vérifie que chaque prompt déclenche bien le bon bloc provider.
########################################################################################################################################################
Prompt: Deploy a VM on OVH Cloud in Strasbourg
→ terraform {
  required_providers {
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.34"
    }
  }
}

provider "ovh" {
  endpoint = "ovh-eu"
}

Prompt: Create a Kubernetes cluster on OVHcloud
→ terraform {
  required_providers {
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.34"
    }
  }
}

provider "ovh" {
  endpoint = "ovh-eu"
}

Prompt: Spin up a GCP Compute Engine instance
→ provider "google" {
  project = "my-project-id"
  region  = "europe-west1"
}

Prompt: Deploy 3 VMs on Azure
→ provider "azurerm" {
  features {}
}

Prompt: Create an S3 bucket on AWS
→ provider "aws" {
  region = "eu-west-3"
}

###########################################################################################################################################""
# Étape 3 — Test bout en bout avec un vrai appel LLM
Changez temporairement le prompt :
user_prompt = "Deploy a single VM on OVH Cloud with 4GB RAM in the Gravelines datacenter"

[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 1/6
[TerraformValidator] terraform validate a échoué :
The provider ovh/ovh does not support resource type "ovh_cloud_project_instance".
[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 2/6
[TerraformValidator] terraform validate a échoué :
The provider ovh/ovh does not support resource type "ovh_cloud_project_instance_v2".
[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 3/6
[TerraformValidator] terraform validate a échoué :
The provider ovh/ovh does not support resource type "ovh_cloud_project_instance".
[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 4/6
[TerraformValidator] terraform validate a échoué :
The provider ovh/ovh does not support data source "ovh_cloud_project_image".
[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 5/6
[TerraformValidator] terraform validate a échoué :
The provider ovh/ovh does not support resource type "ovh_cloud_project_instance".
[SecurityValidator] Aucun problème de sécurité détecté.
[TerraformValidator] Tentative 6/6
[TerraformValidator] Nombre max de retries atteint. Abandon.
=== Dernier Code généré ===
terraform {
  required_providers {
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.34"
    }
  }
}

provider "ovh" {
  endpoint = "ovh-eu"
}

# Data source to get the OVH Cloud Project
data "ovh_cloud_project" "my_project" {
  service_name = "your_ovh_cloud_project_id" # Replace with your OVH Cloud Project ID
}

# Data source to get the desired flavor (s1-2 for 4GB RAM)
data "ovh_cloud_project_flavor" "s1_2_flavor" {
  service_name = data.ovh_cloud_project.my_project.service_name
  region       = "GRA"
  name         = "s1-2" # This flavor provides 4GB RAM
}

# Resource to deploy the instance
resource "ovh_cloud_project_instance_v2" "example_vm" {
  service_name = data.ovh_cloud_project.my_project.service_name
  name         = "my-ovh-vm"
  region       = "GRA"
  flavor_name  = data.ovh_cloud_project_flavor.s1_2_flavor.name
  image_name   = "Ubuntu 22.04" # Use image_name directly
  # Make sure "Ubuntu 22.04" is the exact name of the image in your OVH region.
  # You might need to check the OVH UI or CLI for exact image names.

  # Optional: For SSH key authentication
  # ssh_key_id = "your_ssh_key_id" # Replace with an existing SSH key ID in your project or create one with ovh_cloud_project_ssh_key
}
