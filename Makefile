METAL_DEPLOYMENT_BASE_VERSION := latest

.PHONY: test-local
test-local:
	docker pull ghcr.io/metal-stack/metal-deployment-base:latest
	docker run --rm -it -v $(PWD):/work -w /work ghcr.io/metal-stack/metal-deployment-base:latest make test

.PHONY: test
test:
	python3 -m pip install --upgrade pip
	python3 -m pip install mock metal_python metal-stack-api
	./test.sh

.PHONY: run-test-example
run-test-example:
	docker run --rm -it \
		-v $(PWD):/metal-modules:ro \
		-w /metal-modules \
		--network host \
		ghcr.io/metal-stack/metal-deployment-base:$(METAL_DEPLOYMENT_BASE_VERSION) /bin/bash -ce \
		  "ansible-galaxy install --ignore-errors -r example-requirements.yaml && ansible-playbook example.yaml -v"

.PHONY: run-v2-test-example
run-v2-test-example:
	docker build -f Dockerfile.test --build-arg METAL_DEPLOYMENT_BASE_VERSION=$(METAL_DEPLOYMENT_BASE_VERSION) -t metal-ansible-modules .
	docker run --rm -it \
		-e METAL_APIV2_TOKEN=$(shell kubectl --context kind-metal-control-plane get secret -n metal-control-plane metal-apiserver-admin-token -o jsonpath='{.data.admin_editor_token}' | base64 -d) \
		-v $(PWD):/metal-modules:ro \
		-w /metal-modules \
		--network host \
		metal-ansible-modules /bin/bash -ce \
		  "ansible-playbook example_v2.yaml -vvv"
