SHELL := /bin/bash
EE_IMAGE ?= netintent-ops-ee:latest
ENV ?= lab

.PHONY: ee lint molecule plan apply

ee:
	ansible-builder build -v 3 -t $(EE_IMAGE) -f infra/ansible-builder/execution-environment.yml

lint:
	pre-commit run --all-files

molecule:
	molecule test -s base

plan:
	ANSIBLE_CONFIG=ansible/ansible.cfg ansible-runner run 	  ansible 	  --inventory ansible/inventories/$(ENV)/hosts.yml 	  --playbook playbooks/plan.yml 	  --cmdline "--check --diff" 	  --process-isolation 	  --container-image $(EE_IMAGE)

apply:
	ANSIBLE_CONFIG=ansible/ansible.cfg ansible-runner run 	  ansible 	  --inventory ansible/inventories/$(ENV)/hosts.yml 	  --playbook playbooks/apply.yml 	  --process-isolation 	  --container-image $(EE_IMAGE)
