module: ios_evpn_evi
short_description: Resource module to configure L2VPN EVPN EVI.
description: This module provides declarative management of L2VPN EVPN EVI on Cisco IOS network
  devices.
version_added: 1.0.0
author: Padmini Priyadarshini Sivaraj (@PadminiSivaraj)
notes:
  - Tested against Cisco IOSl2 device with Version 15.2 on VIRL.
  - Starting from v2.5.0, this module will fail when run against Cisco IOS devices that do
    not support L2VPN EVPN EVI. The offline states (C(rendered) and C(parsed)) will work as expected.
  - This module works with connection C(network_cli).
    See U(https://docs.ansible.com/ansible/latest/network/user_guide/platform_ios.html)
options:
  config:
    description: A dictionary of L2VPN Ethernet Virtual Private Network (EVPN) EVI configuration
    type: dict
    element: list
    suboptions:
      evi:
        description: EVPN instance value
        type: int
        required: True
      default_gateway:
        description: Default Gateway parameters
        type: dict
        suboptions:
          advertise:
            description: Advertise Default Gateway MAC/IP routes
            type: dict
            suboptions:
              enable:
                description: Enable advertisement of Default Gateway MAC/IP routes
                type: bool
              disable:
                description: Disable advertisement of Default Gateway MAC/IP routes
                type: bool
      ip:
        description: IP parameters
        type: dict
        suboptions:
          local_learning:
            description: IP local learning
            type: dict
            suboptions:
              enable:
                description: Enable IP local learning
                type: bool
              disable:
                description: Disable IP local learning
                type: bool
      encapsulation:
        description: EVPN encapsulation type
        type: str
        choices:
        - vxlan
        default: vxlan
      replication_type:
        description: Method for replicating BUM traffic
        type: str
        choices:
        - ingress
        - static
      route_distinguisher:
        description: EVPN Route Distinguisher
        type: str
  state:
    description:
      - The state the configuration should be left in
    type: str
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
      - rendered
      - parsed
    default: merged
