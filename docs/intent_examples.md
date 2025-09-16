# Intent Examples

## Minimal fabric intent
```yaml
fabric:
  name: lab-fabric
  vlans:
    - id: 10
      name: lab-users
    - id: 20
      name: lab-servers
  routing_policy:
    spine_loopbacks:
      - 10.0.10.1/32
      - 10.0.10.2/32
```

## Per-device overlay
```yaml
devices:
  leaf1:
    loopback_ip: 10.0.0.1/32
    vlans:
      - 10
  leaf2:
    loopback_ip: 10.0.0.2/32
    vlans:
      - 20
```

Use these snippets when testing `/plans` or Molecule scenarios.
