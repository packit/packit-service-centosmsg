IMAGE ?= docker.io/usercont/packit-service-centosmsg:dev
CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
ANSIBLE_PYTHON ?= /usr/bin/python3
AP ?= ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)

build: files/install-deps.yaml files/recipe.yaml
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

# run 'make build' first
run:
	$(CONTAINER_ENGINE) run --rm \
		-v $(CURDIR)/packit_service_centosmsg:/usr/local/lib/python3.8/site-packages/packit_service_centosmsg:ro,Z \
		-v $(CURDIR)/secrets:/secrets:ro,Z \
		-e LOG_LEVEL=DEBUG \
		$(IMAGE)
